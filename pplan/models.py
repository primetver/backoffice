from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models as md  # pylint: disable=no-member
from django.utils import timezone
from phonenumber_field.modelfields import PhoneNumberField

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

    def occupied(self):
        return self.employee_set.exclude(fire_date__lt=timezone.now().date()).count()   # pylint: disable=no-member
        #return Employee.objects.filter(position__division__id=self.id).count()  # pylint: disable=no-member
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

    def occupied(self):
        return self.employee_set.exclude(fire_date__lt=timezone.now().date()).count()   # pylint: disable=no-member
        # return Employee.objects.filter(position__position_name__id=self.id).count()   # pylint: disable=no-member
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

    def occupied(self):
        return Employee.objects.filter(division__name=self.division,            # pylint: disable=no-member
            position__name=self.position).exclude(fire_date__lt=timezone.now().date()).count()
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
    business_k = md.FloatField('Коэффициент участия в бизнесе', default=0.5)
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
            s = self.salary_set.latest().amount # pylint: disable=no-member
        except Salary.DoesNotExist:             # pylint: disable=no-member
            s = None
        return s
    salary.short_description = 'Текущий оклад'

    def if_fired(self):
        return self.fire_date < timezone.now().date()

    def info(self):
        return f'{self.full_name()} ({self.id}), дата приема: {self.hire_date}, оклад: {self.salary()}'  # pylint: disable=no-member

    def __str__(self):
        return self.full_name()

    def clean(self):
        # validation against staffing table 
        if self.position is None or self.division is None:
            return
        try:
            table_position = StaffingTable.objects.get(division=self.division, position=self.position)  # pylint: disable=no-member
            # vacant positions + employee already in the same position > 0
            if table_position.vacant() + Employee.objects.filter(                                       # pylint: disable=no-member
                id=self.id, division=self.division, position=self.position).count() > 0:                # pylint: disable=no-member
                return
            raise ValidationError(f'Для подразделения {self.division} все должности {self.position} уже заняты в штатном расписании.')
        except StaffingTable.DoesNotExist:  # pylint: disable=no-member
            raise ValidationError(f'Для подразделения {self.division} нет должности {self.position} в штатном расписании.')
        

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
    amount = md.IntegerField('Оклад')
    start_date = md.DateField('Дата изменения')

    def __str__(self):
        return f'{self.employee}, оклад: {self.amount} р., изменен {self.start_date:%d.%m.%Y}'


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

    def lead(self):
        try:
            s = self.projectmember_set.get(role__is_lead=True).employee.full_name()    # pylint: disable=no-member
        except ProjectMember.DoesNotExist:                  # pylint: disable=no-member
            s = 'Не указан'
        except ProjectMember.MultipleObjectsReturned:       # pylint: disable=no-member
            s = 'Несколько руководителей?'
        return s
    lead.short_description = 'Руководитель'

    def member_count(self):
        return self.projectmember_set.count()               # pylint: disable=no-member
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
    start_date = md.DateField('Дата включения в рабочую группу')

    def __str__(self):
        return f'{self.project}, {self.employee}, {self.role}'


class Booking(md.Model):
    ''' 
    Загрузка участника в месяце
    '''
    class Meta():
        verbose_name = 'данные загрузки'
        verbose_name_plural = 'данные загрузки'
        ordering = ('project_member', 'month')
        unique_together = (('project_member', 'month', 'state'),)

    # Статусы версии
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
    month = md.DateField('Месяц загрузки')          # число месяца игнорируется
    load = md.FloatField('Процент загрузки', default=100)    # от 0 до 100 и более (100% -- полная загрузка)
    #version = md.IntegerField('Версия корректировки')
    state = md.CharField('Статус данных о загрузке', max_length=2,
                         default=DRAFT, choices=BOOKING_STATE_CHOICES)

    def __str__(self):
        return f'{self.project_member}, загрузка {self.month:%m.%Y} составляет {self.load}%'
