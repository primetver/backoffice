# pylint: disable=no-member
from datetime import date, timedelta

import pandas as pd
from django.db import models as md
from django_pandas.io import read_frame
from monthdelta import monthdelta, monthmod


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
    #issueid = md.ForeignKey(JiraIssue, db_column='issueid', on_delete=md.DO_NOTHING, verbose_name='Запрос')
    issueid = md.DecimalField('ID Запроса', max_digits=18, decimal_places=0)
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
# Отчеты
#

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

    class Manager(md.Manager):
        def get_queryset(self):
            return WorklogReport.QuerySet(self.model, using='jira')

    # замена менеджера по умолчанию
    objects = Manager()

    class QuerySet(md.QuerySet):
        '''
        Дополненный класс запроса для вывода агрегированных затрат времени по пользователю
        '''
        # Формирование набора данных  
        def get_workload(self, month_list, user, month_hours=None):
             # фильтрация запроса по времени и пользователю
            qs = self.filter(
                startdate__range=(month_list[0], month_list[-1]+monthdelta(1)), 
                author=user
            )

            # чтение журнала работ во фрейм
            df = read_frame(
                qs,
                fieldnames=[
                    'startdate',
                    'timeworked'            
                ],
                index_col = 'issueid'
            )
            if df.empty: return [], None

            # извлекаем уникальный массив задач
            issues = df.index.unique()
            # создаем фрейм названий бюджетов для задач
            bdf = pd.DataFrame(
                ( BudgetCustomField(issueid).budget_name() for issueid in issues ),
                index=issues,
                columns=['budget'])
            # объединение в один
            wdf = pd.merge(df, bdf, left_index=True, right_index=True)
            
            # рассчитываем требуемые для отчета колонки
            wdf['month'] = wdf['startdate'].map(lambda x: date(year=x.year, month=x.month, day=1))
            wdf['hours'] =  wdf['timeworked'] / 3600
            
            # рассчет процента загрузки, если передана карта нормы рабочих часов по месяцам
            # -1% если норма для месяца отсутствует (признак ошибки)
            if month_hours:
                wdf['load'] = wdf.apply(
                    (lambda x: x['hours'] / month_hours.get(x['month'], -x['hours']*100) * 100),
                    asix=1
                )

            del wdf['startdate']; del wdf['timeworked']

            # агрегирование по бюджетам и месяцам, получаем фрейм с иерархическим индексом: проект, месяц
            month_worklog = wdf.groupby(['budget', 'month']).sum()

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

