from django.db import models as md

# Create your models here.

class Employee(md.Model):
    '''
    Работник
    '''
    first_name = md.CharField('Имя', max_length=200)
    sur_name = md.CharField('Отчество', max_length=200, blank=True)
    last_name = md.CharField('Фамилия', max_length=200)
    hire_date = md.DateField('Дата приема на работу')
    fire_date = md.DateField('Дата увольнения', null=True, blank=True, default=None)  # если None -- значит сейчас работает
    is_fulltime = md.BooleanField('Работает полный день?', default=True)
    business_k = md.FloatField('Коэффициент участия в бизнесе', default=0.5)

    def __str__(self):
        return f'{self.first_name} {self.last_name}'

class Salary(md.Model):
    '''
    Оклад
    '''
    employee = md.ForeignKey(Employee, on_delete=md.CASCADE)
    amount = md.IntegerField('Оклад', default=0)
    start_date = md.DateField('Дата изменения')
    
class Project(md.Model):
    '''
    Проект
    '''
    # Статусы бюджета
    BUDGET_NONE = 'NO'
    BUDGET_PROJECT = 'PR'
    BUDGET_APPROVED = 'AP'
    # Перечень статусов
    BUDGET_STATE_CHOICES = (
        (BUDGET_NONE, 'Не создан'),
        (BUDGET_PROJECT, 'Проект согласуется'),
        (BUDGET_APPROVED, 'Утвержден')
    )

    short_name = md.CharField('Сокращенное название проекта', max_length=40, primary_key=True)
    full_name = md.CharField('Полное название проекта', max_length=200)
    business = md.CharField('Бизнес', max_length=20)
    head = md.ForeignKey(Employee, on_delete=md.SET_DEFAULT, blank=True, default=None)
    start_date = md.DateField('Дата начала проекта')
    finish_date = md.DateField('Дата окончания проекта', blank=True, default=None)  # если None -- значит проект сейчас исполняется
    budget_state = md.CharField('Статус бюджета', max_length=2, default=BUDGET_NONE, choices=BUDGET_STATE_CHOICES)

class Booking(md.Model):
    ''' 
    Участие в проектах
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
    month = md.DateField('Месяц загрузки') # число месяца игнорируется
    load = md.FloatField('Коэффициент загрузки') # от 0 до 1 и более (1 = 100% -- полная загрузка)
    #version = md.IntegerField('Версия корректировки') 
    state = md.CharField('Статус данных о загрузке', max_length=2, default=DRAFT, choices=BOOKING_STATE_CHOICES)
