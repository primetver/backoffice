# pylint: disable=no-member
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models as md
from django.db.models.signals import post_save
from django.dispatch import receiver
from django_pandas.io import read_frame
from monthdelta import monthdelta, monthmod
from phonenumber_field.modelfields import PhoneNumberField

from .datautils import today, tomorrow, volume, workdays

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
        verbose_name='Руководитель', related_name='subordinate')
    
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
        verbose_name = 'должности'
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
        verbose_name = 'должность по штатному расписанию'
        verbose_name_plural = 'должности по штатному расписанию'
        unique_together = (('position', 'division'),)
        ordering = ('division', 'position')

    division = md.ForeignKey(Division, on_delete=md.CASCADE, verbose_name='Подразделение')
    position = md.ForeignKey(Position, on_delete=md.PROTECT, verbose_name='Должность')
    count = md.IntegerField('Число позиций', default=1, validators=[MinValueValidator(0)])       

    # pylint: disable=no-member
    def occupied(self):
        return Employee.objects.filter(division__name=self.division,
            position__name=self.position).exclude(fire_date__lt=today()).count()
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

    last_name = md.CharField('Фамилия', max_length=200, db_index=True)
    first_name = md.CharField('Имя', max_length=200)
    sur_name = md.CharField('Отчество', max_length=200, blank=True)
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

    # pylint: disable=no-member
    def salary(self):
        try:
            s = self.salary_set.latest().amount 
        except Salary.DoesNotExist: 
            s = None
        return s
    salary.short_description = 'Текущий оклад'

    def if_fired(self):
        return self.fire_date < today()

    def info(self):
        return f'{self.full_name()} ({self.id}), дата приема: {self.hire_date}, оклад: {self.salary()}'

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
    
    # pylint: disable=no-member
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
    doctype = md.CharField('Тип документа', max_length=2, 
        default=RF, choices=DOCTYPE_CHOICES)
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
        (BUDGET_NONE, 'Бюджет планируется'),
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

    # pylint: disable=no-member
    def lead(self):
        try:
            s = self.projectmember_set.get(role__is_lead=True).employee.full_name() 
        except ProjectMember.DoesNotExist:
            s = 'Не указан'
        except ProjectMember.MultipleObjectsReturned: 
            s = 'Несколько руководителей?'
        return s
    lead.short_description = 'Руководитель'

    def member_count(self):
        return self.projectmember_set.count()
    member_count.short_description = 'Число участников'

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
    
    # pylint: disable=no-member
    def start_date(self):
        return self._start_date_for_state(Booking.PLAN)
    start_date.short_description = 'Дата начала'

    def finish_date(self):
        return self._finish_date_for_state(Booking.PLAN)
    finish_date.short_description = 'Дата окончания'

    def volume(self):
        return self._volume_for_state(Booking.PLAN)
    volume.short_description = 'Объем, чел.дн'

    def percent(self):
        try:
            return self.volume() / workdays(self.start_date(), self.finish_date()) * 100
        except TypeError:
            return 0
    percent.short_description = 'Загрузка, %'

    def __str__(self):
        start   = self.start_date()
        finish  = self.finish_date()
        if start and finish:
            load = f' с {start:%d.%m.%Y} по {finish:%d.%m.%Y}, объем {self.volume()} чел.дн., {self.percent()}%'
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
    DRAFT = 'DR'
    PLAN = 'PL'
    FACT = 'FA'
    # Перечень статусов
    BOOKING_STATE_CHOICES = (
        (DRAFT, 'Черновик'),
        (PLAN, 'Планируемое участие'),
        (FACT, 'Фактическое участие')
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
        объем {volume(wd, self.load):2f} чел.дн.'


class MonthBooking(md.Model):
    ''' 
    Месячная загрузка участника проекта

    Данная модель заполняется автоматически
    '''
    class Meta():
        verbose_name = 'месячная загрузка'
        verbose_name_plural = 'данные месячной загрузки'
        ordering = ()
    
    booking = md.ForeignKey(Booking, on_delete=md.CASCADE, verbose_name='Запись по загрузке')
    month = md.DateField('Месяц') # число месяца всегда должно быть == 1
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
        return f'{self.load:.2f}%'
    load_str.short_description = 'Загрузка %'

    def volume_str(self):
        return f'{self.volume:.2f}'
    volume_str.short_description = 'Трудоемкость, чел.дн'

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

'''
class EmployeeBooking(Employee):
 
    Сводная загрузка сотрудника

    Прокси модель

    class Meta():
        verbose_name = 'статистика загрузки сотрудника'
        verbose_name_plural = 'статистика загрузки сотрудников'
        proxy = True
    
    def booking(self, month_from=None, count=24):
        month_from = month_from if month_from else today().replace(day=1) - monthdelta(count // 2)
        month_generator = (month_from + monthdelta(i) for i in range(count))

        return list(MonthBooking.objects.filter(booking__project_member__employee=self, 
            month=month).aggregate(load=md.Sum('load'), volume=md.Sum('volume')) for month in month_generator)
    booking.short_description = 'Загрузка, объем'
'''

class EmployeeBooking(Employee):
    ''' 
    Сводная загрузка сотрудника

    Прокси модель, расчет с помощью pandas
    '''
    class Meta():
        verbose_name = 'статистика загрузки сотрудника'
        verbose_name_plural = 'статистика загрузки сотрудников'
        proxy = True
    
    def booking(self, month_list=None):
        month_list = month_list if month_list else [ today().replace(day=1) ]
        
        qs = MonthBooking.objects.filter(
            booking__project_member__employee=self, 
            month__range=(month_list[0], month_list[-1])
        )

        df = read_frame(qs, fieldnames=['load', 'volume'], index_col='month').groupby('month').sum()

        return [ 
            {
                'load':df.load.get(month, 0),
                'volume':df.volume.get(month, 0)
            } for month in month_list 
        ]