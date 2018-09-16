from django.db import models as md              # pylint: disable=no-member

# Create your models here.


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
    hire_date = md.DateField('Дата приема на работу')
    # если fire_date == None -- значит сейчас работает
    fire_date = md.DateField('Дата увольнения', null=True, blank=True, default=None)
    is_fulltime = md.BooleanField('Работает полный день?', default=True)
    business_k = md.FloatField('Коэффициент участия в бизнесе', default=0.5)

    def full_name(self):
        return f'{self.last_name} {self.first_name} {self.sur_name}'.rstrip()

    def salary(self):
        try:
            s = self.salary_set.latest().amount # pylint: disable=no-member
        except Salary.DoesNotExist:             # pylint: disable=no-member
            s = None
        return s

    def info(self):
        return f'{self.full_name()} ({self.id}), дата приема: {self.hire_date}, оклад: {self.salary()}'  # pylint: disable=no-member

    def __str__(self):
        return self.full_name()


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
        return f'{self.employee.full_name()}, оклад: {self.amount} р., изменен {self.start_date}'


class Project(md.Model):
    '''
    Проект бизнеса
    '''
    class Meta():
        verbose_name = 'проект'
        verbose_name_plural = 'проекты'
        get_latest_by = 'start_date'
        ordering = ('start_date', 'short_name')

    # Статусы проекта
    INITIAL = "IN"
    OPENED = 'OP'
    CLOSING = 'CL'
    CLOSED = 'CD'
    # Выбор статусов
    PLOJECT_STATE_CHOICES = (
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

    business = md.CharField('Бизнес', max_length=20)
    short_name = md.CharField('Сокращенное название', max_length=40, primary_key=True)
    full_name = md.CharField('Полное название', max_length=200)
    head = md.ForeignKey(Employee, on_delete=md.SET_DEFAULT, blank=True, default=None, 
                         verbose_name='Руководитель')
    start_date = md.DateField('Дата начала')
    # если None -- значит проект сейчас исполняется
    finish_date = md.DateField('Дата окончания', blank=True, default=None)
    state = md.CharField('Статус проекта', max_length=2, 
                                default=INITIAL, choices=PLOJECT_STATE_CHOICES)
    budget_state = md.CharField('Состояние бюджета', max_length=2, 
                                default=BUDGET_NONE, choices=BUDGET_STATE_CHOICES)


class Role(md.Model):
    '''
    Проектная роль
    '''

class Workgroup(md.Model):
    '''
    Рабочая группа проекта
    '''


class Booking(md.Model):
    ''' 
    Загрузка сотрудников в проектах
    '''
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

    member = md.ForeignKey(Employee, on_delete=md.CASCADE)
    project = md.ForeignKey(Project, on_delete=md.CASCADE)
    month = md.DateField('Месяц загрузки')  # число месяца игнорируется
    # от 0 до 1 и более (1 = 100% -- полная загрузка)
    load = md.FloatField('Коэффициент загрузки')
    #version = md.IntegerField('Версия корректировки')
    state = md.CharField('Статус данных о загрузке', max_length=2,
                         default=DRAFT, choices=BOOKING_STATE_CHOICES)
