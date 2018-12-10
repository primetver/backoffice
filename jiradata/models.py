from django.db import models as md

budget_customfield = 10700


class JiraModel(md.Model):
    '''
    Базовый класс для всех моделей для чтения данных из Jira
    Должна быть настроена БД с алиасом 'jira'
    '''
    class Meta():
        managed = False
        abstract = True

    class JiraManager(md.Manager):
        def get_queryset(self):
            return super().get_queryset().using('jira') 
    
    # замена менеджера по умолчанию
    objects = JiraManager()


class JiraIssue(JiraModel):
    '''
    Запрос JIRA
    '''
    class Meta(JiraModel.Meta):
        db_table = 'jiraissue'
        verbose_name = 'запрос Jira'
        verbose_name_plural = 'запросы Jira'
        
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
                    
    def __str__(self):
        return f'{self.issuenum}'


class Worklog(JiraModel):
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
        return issue.issuenum

    def customfield_value(self, customfield):
        value = CustomfieldValue.objects.filter(issue=self.issueid, customfield=customfield).get()
        return value.value()

    def budget(self):
        return self.customfield_value(budget_customfield)
        
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
        self.numbervalue or self.stringvalue or self.datevalue or self.textvalue
            
    def __str__(self):
        return str(self.value())
    