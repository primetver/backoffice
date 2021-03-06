# pylint: disable=no-member
from datetime import timedelta

from django_pandas.io import read_frame

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models as md
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django_pandas.io import read_frame
from monthdelta import monthdelta, monthmod
from phonenumber_field.modelfields import PhoneNumberField

from .datautils import today, tomorrow, volume, workdays
from .proxy_perm_create import proxy_perm_create

import itertools as it

# Create your models here.

class Division(md.Model):
    '''
    Подразделение
    '''
    class Meta():
        verbose_name = 'подразделение'
        verbose_name_plural = 'подразделения'
        ordering = ('name',)
        
    name = md.CharField('Подразделение', max_length=40, unique=True)
    full_name = md.TextField('Полное название')
    head = md.OneToOneField('Employee', null=True, blank=True, on_delete=md.SET_NULL,
        verbose_name='Руководитель', related_name='headed')
    
    # pylint: disable=no-member
    def occupied(self):
        return self.employee_set.exclude(fire_date__lt=today()).count()
        #return Employee.objects.filter(position__division__id=self.id).count()
    occupied.short_description = 'Работает сотрудников'

    def __str__(self):
        return self.name

class Position(md.Model):
    '''
    Должность (без привязки к подразделениям)
    '''
    class Meta():
        verbose_name = 'должность'
        verbose_name_plural = 'должности'
        ordering = ('name',)

    name = md.CharField('Наименование должности', max_length=200, unique=True)

    # pylint: disable=no-member
    def occupied(self):
        return self.employee_set.exclude(fire_date__lt=today()).count()
        # return Employee.objects.filter(position__position_name__id=self.id).count()
        # return sum(p.occupied() for p in self.position_set.all())   -- more slowly!
    occupied.short_description = 'Работает сотрудников'

    def __str__(self):
        return self.name


class StaffingTable(md.Model):
    '''
    Штатное расписание
    '''
    class Meta():
        verbose_name = 'позиция штатного расписанию'
        verbose_name_plural = 'позиции штатного расписания'
        unique_together = (('position', 'division'),)
        ordering = ('division', 'position')

    division = md.ForeignKey(Division, on_delete=md.CASCADE, verbose_name='Подразделение')
    position = md.ForeignKey(Position, on_delete=md.PROTECT, verbose_name='Должность')
    count = md.IntegerField('Число позиций', default=1, validators=[MinValueValidator(0)])       

    # pylint: disable=no-member
    def occupied(self):
        return Employee.working.filter(
            division__name=self.division,
            position__name=self.position
            ).count()
    occupied.short_description = 'Работает сотрудников'

    def vacant(self):
        return self.count - self.occupied()
    vacant.short_description = 'Вакансий'

    def __str__(self):
        return f'{self.division.name}, {str(self.position.name).lower()}'


class Employee(md.Model):
    '''
    Сотрудник компании
    '''
    class Meta():
        verbose_name = 'сотрудник'
        verbose_name_plural = 'сотрудники'
        ordering = ('last_name', 'first_name')

    class Manager(md.Manager):
        # поиск сотрудника по объекту пользователя
        def by_user(self, user):
            return self.filter(user__exact=user).first()
    
    class WorkingManager(Manager):
        def get_queryset(self):
            return super().get_queryset().exclude(fire_date__lt=today())

    # замена менеджера по умолчанию
    objects = Manager()
    working = WorkingManager()

    last_name = md.CharField('Фамилия', max_length=200, db_index=True)
    first_name = md.CharField('Имя', max_length=200)
    sur_name = md.CharField('Отчество', max_length=200, blank=True)
    user = md.OneToOneField(User, null=True, blank=True, on_delete=md.SET_NULL, verbose_name='Логин пользователя')
    division = md.ForeignKey(Division, null=True, on_delete=md.CASCADE, verbose_name='Подразделение')  
    position = md.ForeignKey(Position, null=True, on_delete=md.PROTECT, verbose_name='Занимаемая должность')
    hire_date = md.DateField('Дата приема на работу')
    # если fire_date == None -- значит сейчас работает
    fire_date = md.DateField('Дата увольнения', null=True, blank=True, default=None)
    is_3d = md.BooleanField('Участник системы 3D ?', default=False)
    business_k = md.FloatField('Коэффициент участия в бизнесе', default=0.5, 
        validators=[MinValueValidator(0), MaxValueValidator(1)])
    birthday = md.DateField('День рождения', null=True, blank=True, default=None)
    local_phone = md.CharField('Внутренний номер', max_length=10, blank=True)
    work_phone = PhoneNumberField('Телефон корпоративный', blank=True)
    mobile_phone = PhoneNumberField('Телефон мобильный', blank=True)

    def full_name(self):
        return f'{self.last_name} {self.first_name} {self.sur_name}'.rstrip()
    full_name.admin_order_field = 'last_name'
    full_name.short_description = 'ФИО'

    def salary(self):
        try:
            s = self.salary_set.latest().amount 
        except Salary.DoesNotExist: 
            s = None
        return s
    salary.short_description = 'Текущий оклад'

    def headed_division(self):
        return Division.objects.filter(head__exact=self).first()
    headed_division.short_description = 'Возглавляемое подразделение'

    def subordinates(self):
        hd_div = self.headed_division()
        # кроме уволенных
        return Employee.working.filter(division__exact=hd_div) if hd_div else ()
    subordinates.short_description = 'Подчиненные'

    def is_fired(self):
        return self.fire_date < today()

    def __str__(self):
        return self.full_name()

    def clean(self):
        self._validate_position()
        self._validate_fire_date()
        self._validate_birthday()

    def _validate_position(self):
        if self.position is None or self.division is None:
            return
        try:
            table_position = StaffingTable.objects.get(division=self.division, position=self.position) 
            # vacant positions + employee already in the same position > 0
            if table_position.vacant() + Employee.objects.filter(
                id=self.id, division=self.division, position=self.position).count() > 0:
                return
            raise ValidationError(f'Для подразделения {self.division} все должности {self.position} уже заняты в штатном расписании.')
        except StaffingTable.DoesNotExist:
            raise ValidationError(f'Для подразделения {self.division} нет должности {self.position} в штатном расписании.')

    def _validate_fire_date(self):
        try:
            if self.fire_date < self.hire_date:
                raise ValidationError(f'Дата увольнения {self.fire_date:%d.%m.%Y} не может быть ранее \
                даты приема на работу {self.hire_date:%d.%m.%Y}')
        except TypeError: pass

    def _validate_birthday(self):
        try:
            if self.birthday > self.fire_date:
                raise ValidationError(f'Дата рождения {self.birthday:%d.%m.%Y} не может быть позднее \
                даты увольнения {self.fire_date:%d.%m.%Y}')
        except TypeError: pass
        try:
            if self.birthday > self.hire_date:
                raise ValidationError(f'Дата рождения {self.birthday:%d.%m.%Y} не может быть позднее \
                даты приема на работу {self.hire_date:%d.%m.%Y}, нельзя родиться на работе ;)')
        except TypeError: pass

        

class Salary(md.Model):
    '''
    Оклад сотрудника
    '''
    class Meta():
        verbose_name = 'оклад'
        verbose_name_plural = 'оклады'
        get_latest_by = 'start_date'
        ordering = ('-start_date', 'employee')
        unique_together = (('employee', 'start_date'),)

    employee = md.ForeignKey(Employee, on_delete=md.CASCADE, verbose_name='Сотрудник')
    amount = md.IntegerField('Оклад', validators=[MinValueValidator(1)])
    start_date = md.DateField('Дата изменения')

    def __str__(self):
        return f'{self.employee}, оклад: {self.amount} р., изменен {self.start_date:%d.%m.%Y}'
    
    def clean(self):
        # validate salary dates
        if self.start_date < self.employee.hire_date:               
            raise ValidationError(f'Дата изменения оклада {self.start_date:%d.%m.%Y} не может быть ранее даты \
            приема на работу {self.employee.hire_date:%d.%m.%Y}.') 
        try:
            if self.start_date >= self.employee.fire_date:
                raise ValidationError(f'Дата изменения оклада {self.start_date:%d.%m.%Y} не может совпадать или быть позднее даты \
                увольнения {self.employee.fire_date:%d.%m.%Y}.')
        except TypeError: pass


class Passport(md.Model):
    '''
    Паспортные данные
    '''
    class Meta():
        verbose_name = 'паспорт'
        verbose_name_plural = 'паспортные данные'
        ordering = ('-is_valid', 'issue_date')

    RF = 'RF'
    INTER = 'IN'
    DOCTYPE_CHOICES = (
        (RF, 'Российский паспорт'),
        (INTER, 'Заграничный паспорт'),
    )
    
    employee = md.ForeignKey(Employee, on_delete=md.CASCADE, verbose_name='Сотрудник')
    doctype = md.CharField('Тип документа', max_length=2, default=RF, choices=DOCTYPE_CHOICES)
    series = md.CharField('Серия', max_length=20)
    number = md.CharField('Номер', max_length=20)
    issue_date = md.DateField('Дата выдачи')
    issuer = md.CharField('Кем выдан', max_length=200)
    registered = md.TextField('Зарегистрирован', null=True, blank=True)
    is_valid = md.BooleanField('Действителен', default=True)


class Business(md.Model):
    '''
    Бизнес
    '''
    class Meta():
        verbose_name = 'бизнес'
        verbose_name_plural = 'бизнесы'

    name = md.CharField('Название', max_length=20, unique=True)
    lead = md.CharField('Руководитель', max_length=200)

    def __str__(self):
        return self.name

class Project(md.Model):
    '''
    Проект бизнеса
    '''
    class Meta():
        verbose_name = 'проект'
        verbose_name_plural = 'проекты'
        get_latest_by = 'start_date'
        ordering = ('start_date', 'short_name')
        unique_together = (('business', 'short_name'),)

    # Статусы проекта
    INITIAL = "IN"
    OPENED = 'OP'
    CLOSING = 'CL'
    CLOSED = 'CD'
    # Выбор статусов
    PROJECT_STATE_CHOICES = (
        (INITIAL, 'Проект планируется'),
        (OPENED, 'Проект открыт'),
        (CLOSING, 'Проект в стадии закрытия'),
        (CLOSED, 'Проект закрыт')
    )

    # Статусы бюджета
    BUDGET_NONE = 'NO'
    BUDGET_PROJECT = 'PR'
    BUDGET_APPROVED = 'AP'
    # Выбор статусов
    BUDGET_STATE_CHOICES = (
        (BUDGET_NONE, 'Бюджет отсутствует'),
        (BUDGET_PROJECT, 'Бюджет согласуется'),
        (BUDGET_APPROVED, 'Бюджет утвержден')
    )

    business = md.ForeignKey(Business, on_delete=md.CASCADE, verbose_name='Бизнес')
    short_name = md.CharField('Сокращенное название', max_length=40, db_index=True)
    full_name = md.TextField('Полное название')
    start_date = md.DateField('Дата начала')
    # если None -- значит проект сейчас исполняется
    finish_date = md.DateField('Дата окончания', blank=True, default=None)
    state = md.CharField('Статус проекта', max_length=2, 
                                default=INITIAL, choices=PROJECT_STATE_CHOICES)
    budget_state = md.CharField('Состояние бюджета', max_length=2, 
                                default=BUDGET_NONE, choices=BUDGET_STATE_CHOICES)

    def lead(self):
        try:
            s = self.projectmember_set.get(role__is_lead=True).employee.full_name() 
        except ProjectMember.DoesNotExist:
            s = 'Не указан'
        except ProjectMember.MultipleObjectsReturned: 
            s = 'Несколько руководителей?'
        return s
    lead.short_description = 'Руководитель'

    # трудозатраты в чел.дн. считаются из объема месячной загрузки всех участниклов проекта
    def volume(self):
        volume = MonthBooking.objects.filter(
            booking__project_member__project=self).aggregate(md.Sum('volume'))['volume__sum']
        return volume or 0
    volume.short_description = 'Трудоемкость, чел.дн.'

    def volume_str(self):
        return f'{self.volume():n}'
    volume_str.short_description = volume.short_description

    # трудозатраты в чел.мес. считаются из % месячной загрузки всех участников проекта 
    def month_volume(self):
        volume = MonthBooking.objects.filter(
            booking__project_member__project=self).aggregate(md.Sum('load'))['load__sum']
        return volume / 100 or 0
    month_volume.short_description = 'Трудоемкость, чел.мес.'

    def month_volume_str(self):
        return f'{self.month_volume():n}'
    month_volume_str.short_description = month_volume.short_description

    def member_count(self):
        return self.projectmember_set.count()
    member_count.short_description = 'Участников'

    def __str__(self):
        return f'{self.business}, {self.short_name}'
    __str__.admin_order_field = 'short_name'
    __str__.short_description = 'Проект'


class Role(md.Model):
    '''
    Проектная роль
    '''
    class Meta():
        verbose_name = 'проектная роль'
        verbose_name_plural = 'проектные роли'

    role = md.CharField('Роль', max_length=40, unique=True)
    descr = md.TextField('Описание роли', blank=True)
    is_lead = md.BooleanField('Руководитель проекта?', default=False)

    def __str__(self):
        return self.role

class ProjectMember(md.Model):
    '''
    Участник проекта
    '''
    class Meta():
        verbose_name = 'участник проекта'
        verbose_name_plural = 'участники проектов'
        ordering = ('project', '-role__is_lead', 'employee')
        unique_together = (('project', 'employee'),)

    project = md.ForeignKey(Project, on_delete=md.CASCADE, verbose_name='Проект')
    employee = md.ForeignKey(Employee, on_delete=md.CASCADE, verbose_name='Сотрудник')
    role = md.ForeignKey(Role, on_delete=md.PROTECT, verbose_name='Роль в проекте')
    
    def start_date(self):
        return self._start_date_for_state(Booking.PLAN)
    start_date.short_description = 'Дата начала'

    def finish_date(self):
        return self._finish_date_for_state(Booking.PLAN)
    finish_date.short_description = 'Дата окончания'

    def month_count(self):
        # SqlLite do not support distinct on fields
        month_list = MonthBooking.objects.filter(booking__project_member=self).values_list('month', flat=True)
        return len(set(month_list))
    month_count.short_description = 'Месяцев'

    def volume(self):
        return self._volume_for_state(Booking.PLAN)
    volume.short_description = 'Объем, чел.дн'

    def volume_str(self):
        return f'{self.volume():n}'
    volume_str.short_description = volume.short_description

    def percent(self):
        try:
            return self.volume() / workdays(self.start_date(), self.finish_date()) * 100
        except (TypeError, ZeroDivisionError):
            return 0
    percent.short_description = 'Загрузка, %'

    def percent_str(self):
        return f'{self.percent():n}'
    percent_str.short_description = percent.short_description

    def load(self):
        '''
        Среднемесячная загрузка
        '''
        load = MonthBooking.objects.filter(
            booking__project_member=self).aggregate(md.Avg('load'))['load__avg']
        return load or 0
    load.short_description = 'Средн.мес., %'

    def load_str(self):
        return f'{self.load():n}'
    load_str.short_description = load.short_description

    def __str__(self):
        start   = self.start_date()
        finish  = self.finish_date()
        if start and finish:
            load = f' с {start:%d.%m.%Y} по {finish:%d.%m.%Y}, объем {self.volume_str()} чел.дн., {self.load_str()}%'
        else:
            load = ''
        return f'{self.project}, {self.employee}, {self.role}{load}'

    def _start_date_for_state(self, state):
        try:
            s = Booking.objects.filter(project_member=self, state=state).order_by('start_date')[0].start_date
        except IndexError:
            s = None
        return s

    def _finish_date_for_state(self, state):
        try:
            s = Booking.objects.filter(project_member=self, state=state).order_by('-finish_date')[0].finish_date
        except IndexError:
            s = None
        return s

    def _volume_for_state(self, state):
        booking = Booking.objects.filter(project_member=self, state=state)
        return sum(volume(workdays(b.start_date, b.finish_date), b.load) for b in booking)
        

class Booking(md.Model):
    ''' 
    Загрузка участника проекта
    '''
    class Meta():
        verbose_name = 'данные загрузки'
        verbose_name_plural = 'данные загрузки'
        ordering = ('project_member', 'start_date')

    # Статусы
    #DRAFT = 'DR'
    PLAN = 'PL'
    #FACT = 'FA'
    # Перечень статусов
    BOOKING_STATE_CHOICES = (
    #    (DRAFT, 'Черновик'),
        (PLAN, 'Планируемое участие'),
    #    (FACT, 'Фактическое участие')
    )

    project_member = md.ForeignKey(ProjectMember, on_delete=md.CASCADE, verbose_name='Участник проекта')
    start_date = md.DateField('Начало загрузки', default=today)             
    finish_date = md.DateField('Окончание загрузки', default=tomorrow)
    load = md.FloatField('Процент загрузки', default=0, 
        validators=[MinValueValidator(0), MaxValueValidator(100)])    # от 0 до 100 (100% -- полная загрузка)
    state = md.CharField('Статус данных о загрузке', max_length=2,
        default=PLAN, choices=BOOKING_STATE_CHOICES)

    def __str__(self):
        wd = workdays(self.start_date, self.finish_date)
        return f'Загрузка c {self.start_date:%d.%m.%Y} по {self.finish_date:%d.%m.%Y}, {wd} раб.дн., {self.load}%, \
        объем {volume(wd, self.load):n} чел.дн.'


class MonthBooking(md.Model):
    ''' 
    Базовая модель для хранения данных о плановой загрузке сотрудников по месяцам

    Данная модель заполняется автоматически, см. update_month_booking
    '''
    class Meta():
        verbose_name = 'плановая загрузка за месяц'
        verbose_name_plural = 'данные плановой загрузки по месяцам'
        unique_together = (('booking', 'month'),)
    
    booking = md.ForeignKey(Booking, on_delete=md.CASCADE, verbose_name='Запись по загрузке')
    month = md.DateField('Месяц', db_index=True) # число месяца всегда должно быть == 1
    days = md.IntegerField('Участие, дней')
    load = md.FloatField('Загрузка, %', default=0) 
    volume = md.FloatField('Объем, чел.дн.', default=0)

    def project(self):
        return self.booking.project_member.project
    project.short_description = 'Проект'
        
    def member(self):    
        return self.booking.project_member.employee
    member.short_description = 'Участник'

    def month_str(self):
        return f'{self.month:%m.%Y}'
    month_str.short_description = 'Месяц'

    def load_str(self):
        return f'{self.load:n}'
    load_str.short_description = 'Загрузка %'

    def volume_str(self):
        return f'{self.volume:n}'
    volume_str.short_description = 'Объем, чел.дн'

    def __str__(self):
        return f'Месяц: {self.month_str()}: {self.days} дней, {self.load_str()}, {self.volume_str()} чел.дн.'

    def clean(self):
        # validate salary dates
        raise ValidationError('Данные месячной загрузки рассчитываются автоматически и\
        не могут быть добавлены или отредактированы вручную. Вернитесь к просмотру данных.')

@receiver(post_save, sender=Booking)
def update_month_booking(sender, instance, **kwargs):
    '''
    Обновление данных о месячной загрузке в связанной таблице MonthBooking
    '''
    # disable the handler during fixture loading
    if kwargs['raw']:
        return
        
    # удаление старых данных
    MonthBooking.objects.filter(booking=instance).delete()

    # округление начального и конечного месяца участия в проекте до 1 числа
    start_month = instance.start_date.replace(day=1)
    end_month = instance.finish_date.replace(day=1)
    
    # месяцы, в которых нужно отразить нагрузку 
    month_generator = (start_month + monthdelta(i) for i in range(monthmod(start_month, end_month)[0].months + 1))

    for month in month_generator:
        # последнее число месяца
        monthtail = month + monthdelta(1) - timedelta(1)

        start = month if instance.start_date < month else instance.start_date
        finish = monthtail if instance.finish_date > monthtail else instance.finish_date

        days = workdays(start, finish)                              # число запланированных рабочих дней в месяце 
        vol = volume(days, instance.load)                           # трудоемкость работ в месяце
        load = days / workdays(month, monthtail) * instance.load    # нагрузка за месяц

        # заполнение таблицы помесячной загрузки
        month_booking = MonthBooking(
            booking=instance,
            month=month,
            days=days,
            load=load,
            volume=vol)
        month_booking.save()


class MonthBookingSummary(MonthBooking):
    ''' 
    Прокси-модель для сводного отчета о загрузке сотрудников по месяцам
    '''
    class Meta():
        proxy = True
        verbose_name = 'загрузка по месяцам'
        verbose_name_plural = 'отчет о загрузке по месяцам'

    class Manager(md.Manager):
        def get_queryset(self):
            return MonthBookingSummary.QuerySet(self.model, using=self._db)

    # замена менеджера по умолчанию
    objects = Manager()

    class QuerySet(md.QuerySet):
        '''
        Дополненный класс запроса для вывода загруженности по месяцам
        '''
        # Формирование набора данных по месяцам
        def get_booking(self, month_list):
            # чтение запроса в фрейм
            df = read_frame(
                self,
                fieldnames=[
                    'booking__project_member__employee',
                    'month',
                    'load',
                    'volume'
                ]
            )
            if df.empty: return []

            # агрегирование по сотрудникам и месяцам, получаем фрейм с иерархическим индексом
            month_booking = df.groupby(['booking__project_member__employee', 'month']).sum()

            # результат - генератор последовательности словарей с полями: 
            #   - сотрудник, 
            #   - список помесячных записей о его загрузке для каждого месяца из переданного списка
            #     (отсутствующие данные заполняются нулями)
            return (
                {
                    'name': e,
                    # сбрасываем индекс по сотруднику, переиндексируем по списку месяцев, выводим в список словарей
                    'booking': booking.reset_index(level=0, drop=True).reindex(month_list, fill_value=0).to_dict('records')
                    # это замена примерно следующего кода:
                    # [
                    #    {
                    #        'load':booking.ix[e].load.get(month, 0),
                    #        'volume':booking.ix[e].volume.get(month, 0)
                    #    } for month in month_list
                    # ]
                } for e, booking in month_booking.groupby(level='booking__project_member__employee')
            )


class ProjectBooking(MonthBooking):
    ''' 
    Прокси-модель для отчета о загрузке сотрудников по проектам
    '''
    class Meta():
        proxy = True
        verbose_name = 'загрузка по проектам'
        verbose_name_plural = 'отчет о загрузке по проектам'

    class Manager(md.Manager):
        def get_queryset(self):
            return ProjectBooking.QuerySet(self.model, using=self._db)

    # замена менеджера по умолчанию
    objects = Manager()

    class QuerySet(md.QuerySet):
        '''
        Дополненный класс запроса для вывода загруженности по проектам
        '''
        # Формирование набора данных по проектам с возможностью вывода данных по выплатам за указанный месяц
        def get_booking(self, projects, salary_month=None):
            # чтение запроса в фрейм
            df = read_frame(
                self,
                fieldnames=[
                    'booking__project_member__employee',
                    'booking__project_member__project__short_name',
                    'load',
                    'volume',            
                ],
                index_col = 'booking__project_member__employee__id'
            )
            if df.empty: return []

            if salary_month:
                # чтение данных по з/п, выбор актуальных на заданный месяц
                sdf = read_frame(
                    # pylint: disable=no-member
                    Salary.objects.filter(start_date__lte=salary_month),
                    fieldnames=[
                        'employee__id',
                        'employee__business_k',
                        'amount'
                    ]
                ).groupby(['employee__id']).first()

                # обогащение набора данных и расчет оплаты в соответствии с загрузкой
                df = df.join(sdf)
                df['cost'] =  df['load'] * df['amount'] * df['employee__business_k'] / 100

                # удаление ненужного столбца
                del df['amount'], df['employee__business_k']

            # агрегирование по сотрудникам и проектам, получаем фрейм с иерархическим индексом
            project_booking = df.groupby([
                'booking__project_member__employee', 
                'booking__project_member__project__short_name']).sum()
            
            # результат - генератор последовательности словарей с полями: 
            #   - сотрудник, 
            #   - список записей о его загрузке для каждого проекта из переданного списка
            #     (отсутствующие данные заполняются нулями),
            #   - запись о суммарной загрузке
            return (
                {
                    'name': e,
                    # сбрасываем индекс по сотруднику, 
                    # переиндексируем по списку проектов, выводим в список словарей
                    'booking': booking.reset_index(level=0, drop=True).reindex(projects, fill_value=0).to_dict('records'),
                    'total': booking.sum().to_dict()
                } for e, booking in project_booking.groupby(level='booking__project_member__employee')
            )


class MonthBookingEmployee(MonthBooking):
    ''' 
    Прокси-модель для отчета о загрузке выбранного сотрудника
    '''
    class Meta():
        proxy = True
        verbose_name = 'загрузка по сотруднику'
        verbose_name_plural = 'отчет о загрузке по сотруднику'
        permissions = (
            ("view_all", "Просмотр любого сотрудника"),
        )

    class Manager(md.Manager):
        def get_queryset(self):
            return MonthBookingEmployee.QuerySet(self.model, using=self._db)

    # замена менеджера по умолчанию
    objects = Manager()

    class QuerySet(md.QuerySet):
        '''
        Дополненный класс запроса для вывода загруженности по сотруднику
        '''
        # Формирование набора данных по сотруднику 
        def get_booking(self, month_list, employee_id):
            # фильтрация запроса
            qs = self.filter(
                month__range=(month_list[0], month_list[-1]), 
                booking__project_member__employee__id=employee_id
            )

            # чтение запроса в фрейм
            df = read_frame(
                qs,
                fieldnames=[
                    'booking__project_member__project__short_name',
                    'month',
                    'load',
                    'volume',            
                ],
            )
            if df.empty: return [], None

            # агрегирование по проектам и месяцам, получаем фрейм с иерархическим индексом: проект, месяц
            month_booking = df.groupby(['booking__project_member__project__short_name', 'month']).sum()

            # результат -- кортеж:
            # 1) генератор последовательности словарей с полями: 
            #   - проект, 
            #   - список помесячных записей о загрузке для каждого месяца из переданного списка
            #     (отсутствующие данные заполняются нулями)
            # 2) итоговая строка 
            return (
                (
                    {
                        'project': p,
                        # сбрасываем индекс по проектам, переиндексируем по списку месяцев, выводим в список словарей
                        'booking': booking.reset_index(level=0, drop=True).reindex(month_list, fill_value=0).to_dict('records')
                    } for p, booking in month_booking.groupby(level='booking__project_member__project__short_name')
                ),
                {
                    # дополнительная итоговая строка 
                    'booking': month_booking.groupby('month').sum().reindex(month_list, fill_value=0).to_dict('records')
                }
            )
