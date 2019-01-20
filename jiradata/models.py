# pylint: disable=no-member
from datetime import date, timedelta

import pandas as pd
from django.db import models as md
from django_pandas.io import read_frame
from monthdelta import monthdelta, monthmod

from timing import Timing


class JiraModel(md.Model):
    '''
    Базовый класс для всех моделей для чтения данных из Jira
    Должна быть настроена БД с алиасом 'jira'
    '''
    class Meta():
        managed = False
        abstract = True
        default_permissions = ('view',)

    class JiraManager(md.Manager):
        def get_queryset(self):
            return super().get_queryset().using('jira')

    # замена менеджера по умолчанию
    objects = JiraManager()


class BudgetCustomField:
    '''
    Класс методов получения номера и строки бюджета из кастомного поля бюджета проекта
    '''
    # id кастомного поля бюджета в Jira
    # TODO: может быть параметром настройки
    id = 10700

    def __init__(self, id=None):
        self._issueid = id

    def get_issueid(self):
        # метод, возвращающий id запроса должен быть переопределен в дочерних классах
        return self._issueid

    def budget_id_name(self):
        cfv = CustomfieldValue.objects.filter(
            issue=self.get_issueid(),
            customfield=BudgetCustomField.id
        ).first()

        # id и имя бюджета проекта
        return (
            cfv.value() if cfv else None,
            cfv.option_value() if cfv else None
        )

    def budget_id(self):
        return self.budget_id_name()[0]
    budget_id.short_description = 'ID бюджета'

    def budget_name(self):
        return self.budget_id_name()[1]
    budget_name.short_description = 'Бюджет проекта'

#
#  Модели JIRA
#


class JiraUser(JiraModel):
    '''
    Пользователь JIRA
    '''
    class Meta(JiraModel.Meta):
        db_table = 'cwd_user'
        verbose_name = 'пользователь'
        verbose_name_plural = 'пользователи'

    id = md.DecimalField('ID', primary_key=True, max_digits=18, decimal_places=0)
    directory_id = md.DecimalField('ID', max_digits=18, decimal_places=0)
    user_name = md.CharField('Пользователь', max_length=255, db_column='lower_user_name')
    active = md.DecimalField('Проект', max_digits=9, decimal_places=0)
    created_date = md.DateTimeField('Дата создания')
    updated_date = md.DateTimeField('Дата изменения')
    first_name = md.CharField('Фамилия', max_length=255)
    last_name = md.CharField('Имя', max_length=255)
    email_address = md.CharField('E-Mail', max_length=255, db_column='lower_email_address')

    def __str__(self):
        return f'{self.first_name} {self.last_name}'


class JiraIssue(JiraModel, BudgetCustomField):
    '''
    Запрос JIRA
    '''
    class Meta(JiraModel.Meta):
        db_table = 'jiraissue'
        verbose_name = 'запрос'
        verbose_name_plural = 'запросы'

    id = md.DecimalField('ID', primary_key=True, max_digits=18, decimal_places=0)
    issuenum = md.DecimalField('Номер', max_digits=18, decimal_places=0)
    project = md.DecimalField('Проект', max_digits=18, decimal_places=0)
    reporter = md.CharField('Заявитель', max_length=255)
    assignee = md.CharField('Исполнитель', max_length=255)
    creator = md.CharField('Создатель', max_length=255)
    summary = md.CharField('Запрос', max_length=255)
    description = md.TextField('Описание запроса')
    priority = md.CharField('Приоритет', max_length=255)
    resolution = md.CharField('Резолюция', max_length=255)
    issuestatus = md.CharField('Статус', max_length=255)
    created = md.DateTimeField('Дата создания')
    updated = md.DateTimeField('Дата изменения')
    duedate = md.DateTimeField('Дата завершения')
    resolutiondate = md.DateTimeField('Дата резолюции')
    timespent = md.DecimalField('Затраченное время, c', max_digits=18, decimal_places=0)

    def hours(self):
        return (self.timespent or 0) / 3600
    hours.short_description = 'Затраченное время, ч'

    def get_issueid(self):
        return self.id

    def __str__(self):
        return f'{self.issuenum}'


class Worklog(JiraModel, BudgetCustomField):
    '''
    Журнал учета работ
    '''
    class Meta(JiraModel.Meta):
        db_table = 'worklog'
        verbose_name = 'запись о работе'
        verbose_name_plural = 'записи о выполнении работ'

    id = md.DecimalField('ID', primary_key=True, max_digits=18, decimal_places=0)
    issueid = md.ForeignKey(JiraIssue, db_column='issueid', on_delete=md.CASCADE, verbose_name='Запрос')
    #issueid = md.DecimalField('ID Запроса', max_digits=18, decimal_places=0)
    author = md.CharField('Создал', max_length=255)
    worklogbody = md.TextField('Содержание работ')
    created = md.DateTimeField('Дата создания')
    updateauthor = md.CharField('Изменил', max_length=255)
    updated = md.DateTimeField('Дата изменения')
    startdate = md.DateTimeField('Дата выполнения работ')
    timeworked = md.DecimalField('Затраченное время, c', max_digits=18, decimal_places=0)

    def hours(self):
        return (self.timeworked or 0) / 3600
    hours.short_description = 'Затраченное время, ч'

    def issue(self):
        issue = JiraIssue.objects.filter(id=self.issueid).get()
        return issue.summary

    def get_issueid(self):
        return self.issueid

    def __str__(self):
        return f'{self.startdate:%d.%m.%Y} {self.author} {self.worklogbody or ""} {self.hours()} ч.'


class Customfield(JiraModel):
    '''
    Определение пользовательских полей
    '''
    class Meta(JiraModel.Meta):
        db_table = 'customfield'
        verbose_name = 'определение пользовательского поля'
        verbose_name_plural = 'определения пользовательских полей'

    id = md.DecimalField('ID', primary_key=True, max_digits=18, decimal_places=0)
    customfieldtypekey = md.CharField('Ключ типа поля', max_length=255)
    customfieldsearcherkey = md.CharField('Ключ поиска', max_length=255)
    cfname = md.CharField('Наименование поля', max_length=255)
    description = md.TextField('Описание поля')
    defaultvalue = md.CharField('Значение по умолчанию', max_length=255)
    fieldtype = md.DecimalField('Тип поля', max_digits=18, decimal_places=0)
    project = md.DecimalField('Проект', max_digits=18, decimal_places=0)
    issuetype = md.CharField('Тип запроса', max_length=255)

    def __str__(self):
        return self.cfname


class CustomfieldValue(JiraModel):
    '''
    Значения пользовательских полей
    '''
    class Meta(JiraModel.Meta):
        db_table = 'customfieldvalue'
        verbose_name = 'значение пользовательского поля'
        verbose_name_plural = 'значения пользовательских полей'

    id = md.DecimalField('ID', primary_key=True, max_digits=18, decimal_places=0)
    issue = md.DecimalField('Запрос', max_digits=18, decimal_places=0)
    customfield = md.DecimalField('Пользовательское поле', max_digits=18, decimal_places=0)
    parentkey = md.CharField('Родительской ключ', max_length=255)
    stringvalue = md.CharField('Строковое значение', max_length=255)
    numbervalue = md.DecimalField('Числовое значение', max_digits=18, decimal_places=0)
    textvalue = md.TextField('Текстовое значение')
    datevalue = md.DateTimeField('Значение даты и времени')
    valuetype = md.CharField('Тип значения', max_length=255)

    def value(self):
        # значение может быть в одном из полей, соответствующих типу значения
        return self.numbervalue or self.stringvalue or self.datevalue or self.textvalue

    def option_value(self):
        # возврат значения опции, если определена, иначе значения поля
        value = self.value()
        option = CustomfieldOption.objects.filter(id=value).first().customvalue
        return option or value

    def __str__(self):
        return str(self.option_value())


class CustomfieldOption(JiraModel):
    '''
    Опции пользовательских полей
    '''
    class Meta(JiraModel.Meta):
        db_table = 'customfieldoption'
        verbose_name = 'опция пользовательского поля'
        verbose_name_plural = 'опции пользовательских полей'

    id = md.DecimalField('ID', primary_key=True, max_digits=18, decimal_places=0)
    customfield = md.DecimalField('Пользовательское поле', max_digits=18, decimal_places=0)
    sequence = md.DecimalField('Последовательный номер', max_digits=18, decimal_places=0)
    customvalue = md.CharField('Значение', max_length=255)
    optiontype = md.CharField('Тип значения', max_length=60)
    disabled = md.CharField('Не активно', max_length=60)

    def __str__(self):
        return self.customvalue

#
# Модели отчетов
#


class WorklogSummary(Worklog):
    ''' 
    Прокси-модель для сводного отчета о фактической загрузке
    '''
    class Meta():
        proxy = True
        verbose_name = 'фактическая загрузка по месяцам'
        verbose_name_plural = 'отчет о фактической загрузке по месяцам'
        default_permissions = ('view',)
        permissions = (
            ("view_all", "Просмотр любого бюджета"),
        )


class WorklogReport(Worklog):
    ''' 
    Прокси-модель для отчета о фактической загрузке сотрудника
    '''
    class Meta():
        proxy = True
        verbose_name = 'фактическая загрузка по сотруднику'
        verbose_name_plural = 'отчет о фактической загрузке по сотруднику'
        default_permissions = ('view',)
        permissions = (
            ("view_all", "Просмотр любого сотрудника"),
        )


class WorklogIssues(Worklog):
    ''' 
    Прокси-модель для отчета о затратах времени по задачам 
    '''
    class Meta():
        proxy = True
        verbose_name = 'затраты времени по задаче'
        verbose_name_plural = 'отчет о затратах времени по задачам'
        default_permissions = ('view',)
        permissions = (
            ("view_all", "Просмотр любого сотрудника"),
        )

    class Manager(JiraModel.JiraManager):
        def get_queryset(self):
            return super().get_queryset() \
                .values('issueid__issuenum', 'issueid__summary', 'issueid__reporter', 'issueid__created') \
                .annotate(hours=md.Sum('timeworked') / 3600)

    # замена менеджера по умолчанию
    objects = Manager()


#
# Аналитика
#

  
# получить фрейм названий бюджетов, индекс id запроса
def df_issue_budget():
    # перечень идентификаторов запросов с назначенными бюджетами 
    df = read_frame(
        CustomfieldValue.objects.filter(customfield=BudgetCustomField.id),
        fieldnames=('stringvalue',),
        index_col='issue',
        coerce_float=True,
        verbose=False
    )
    df['budget_id'] = df['stringvalue'].map(float)
    del df['stringvalue']
    # перечень всех названий бюджетов
    opts = read_frame(
        CustomfieldOption.objects.filter(customfield=BudgetCustomField.id),
        fieldnames=('customvalue',),
        index_col='id',
        coerce_float=True,
        verbose=False
    ).rename(columns={'customvalue': 'budget'})
    
    return df.merge(opts, left_on='budget_id', right_index=True)


class WorklogFrame:
    '''
    Класс для анализа данных журнала работ с помощью pandas
    '''
    def __init__(self, df=pd.DataFrame()):
        self.df = df

    # Загрузка фрейма из запроса с заданными колонками
    # возвращается копия объекта с загруженными данными
    def load(self, qs):
        df = read_frame(
            qs,
            fieldnames=(
                'author',
                'startdate',
                'timeworked'
            ),
            index_col='issueid',
            coerce_float=True,
            verbose=False
        )
        # обогащение id и названиями бюджетов
        df = df.merge(df_issue_budget(), left_index=True, right_index=True)
        
        return WorklogFrame(df)

    # Фильтрация по заданному значению
    # возвращается копия объекта с отфильтрованнымми данными
    def filter(self, budget_id=None, author=None):
        df = self.df
        if budget_id:
            df = df[df['budget_id'] == budget_id]
        if author:
            df = df[df['author'] == author]
        
        return WorklogFrame(df)

    # Подготовка фрейма - расчет требуемых для агрегации колонок
    # должен быть выполнен перед агрегацией
    def _prepare(self, month_list=None, month_norma=None):
        df = self.df
        # расчет статистик
        df['month'] = df['startdate'].map(lambda x: date(year=x.year, month=x.month, day=1))
        df['hours'] = df['timeworked'] / 3600
        del df['startdate']
        del df['timeworked']
        
        # если переданы нормы рабочего времени по месяцам
        if month_list and month_norma:
            df_norma = pd.DataFrame(month_norma, index=month_list, columns=['norma'])
            df = df.merge(df_norma, left_on='month', right_index=True)
            # расчет % загрузки по нормативу рабочих часов в месяц
            df['load'] = df['hours'] / df['norma'] * 100
            del df['norma']

    # Обогащение реальными именами пользователей  
    def _add_name(self):
        userdf = read_frame(
            JiraUser.objects.all(),
            fieldnames=(
                'first_name',
                'last_name'
            ),
            index_col='user_name'
        )
        userdf['name'] = userdf['first_name'] + ' ' + userdf['last_name']
        self.df = self.df.merge(userdf, left_on='author', right_index=True)
    
    # Агрегация по месяцам и пользователям
    def aggr_month_user(self, month_list, month_norma=None):
        # расчет статистик
        if 'month' not in self.df.columns:
            self._prepare(month_list, month_norma)

        # добавление имен пользователей    
        if 'name' not in self.df.columns:
            self._add_name()

        # агрегирование по сотрудникам и месяцам, получаем фрейм с иерархическим индексом: сотрудник, месяц
        month_worklog = self.df.groupby(['name', 'month']).sum()

        # результат генератор последовательности словарей с полями:
        #   - сотрудник,
        #   - список помесячных записей о загрузке для каждого месяца из переданного списка
        #     (отсутствующие данные заполняются нулями)
        return (
            {
                'name': name,
                # сбрасываем индекс по сотрудникам, переиндексируем по заданному списку месяцев, выводим в список словарей
                'workload': worklog.reset_index(level=0, drop=True).reindex(month_list, fill_value=0).to_dict('records')
            } for name, worklog in month_worklog.groupby(level='name')
        )

    # Агрегация по месяцам и бюджетам
    def aggr_month_budget(self, month_list, month_norma=None):
        # расчет статистик
        if 'month' not in self.df.columns:
            self._prepare(month_list, month_norma)

        # агрегирование по бюджетам и месяцам, получаем фрейм с иерархическим индексом: проект, месяц
        month_worklog = self.df.groupby(['budget', 'month']).sum()

        # результат -- кортеж:
        # 1) генератор последовательности словарей с полями:
        #   - бюджет,
        #   - список помесячных записей о загрузке для каждого месяца из переданного списка
        #     (отсутствующие данные заполняются нулями)
        # 2) итоговая строка
        return (
            (
                {
                    'project': p,
                    # сбрасываем индекс по бюджетам, переиндексируем по заданному списку месяцев, выводим в список словарей
                    'workload': worklog.reset_index(level=0, drop=True).reindex(month_list, fill_value=0).to_dict('records')
                } for p, worklog in month_worklog.groupby(level='budget')
            ),
            {
                # дополнительная итоговая строка
                'workload': month_worklog.groupby('month').sum().reindex(month_list, fill_value=0).to_dict('records')
            }
        )

    # Получить список id и имен бюджетов
    def budget_list(self):
        df_budgets = self.df[['budget_id', 'budget']].drop_duplicates().sort_values('budget')
        return df_budgets.values.tolist()
    
    # Получить список логинов и реальных имен пользователей
    def user_list(self):
        if 'name' not in self.df.columns:
            self._add_name()

        df_budgets = self.df[['author', 'name']].drop_duplicates().sort_values('name')
        return df_budgets.values.tolist()

