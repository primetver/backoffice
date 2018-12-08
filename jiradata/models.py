from django.db import models as md


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


class Worklog(JiraModel):
    '''
    Журнал учета работ
    '''
    class Meta(JiraModel.Meta):
        db_table = 'worklog'
        verbose_name = 'запись о работе'
        verbose_name_plural = 'записи о выполнении работ'
        
        
    id = md.DecimalField('ID', primary_key=True, max_digits=18, decimal_places=0)
    issueid = md.DecimalField('Issue', max_digits=18, decimal_places=0)
    author = md.CharField('Создал', max_length=255)
    worklogbody = md.TextField('Содержание работ')
    created = md.DateTimeField('Дата создания')
    updateauthor = md.CharField('Изменил', max_length=255)
    updated = md.DateTimeField('Дата изменения')
    startdate = md.DateTimeField('Дата выполнения работ')
    timeworked = md.DecimalField('Затраченное время, c', max_digits=18, decimal_places=0)

    def hours(self):
        return self.timeworked / 3600
    hours.admin_order_field = 'timeworked'
    hours.short_description = 'Затраченное время, ч'
        
    def __str__(self):
        return f'{self.startdate:%d.%m.%Y} {self.author} {self.worklogbody} {self.hours()} ч.'


class CustomfieldValue(JiraModel):
    '''
    Значения пользовательских полей
    '''
    class Meta(JiraModel.Meta):
        db_table = 'customfieldvalue'
        verbose_name = 'запись о работе'
        verbose_name_plural = 'записи о выполнении работ'
        
        
    id = md.DecimalField('ID', primary_key=True, max_digits=18, decimal_places=0)
    issue = md.DecimalField('Issue', max_digits=18, decimal_places=0)
    customfield = md.DecimalField('Customfield', max_digits=18, decimal_places=0)
    parentkey = md.CharField('Parentkey', max_length=255)
    stringvalue = md.CharField('Stringvalue', max_length=255)
    numbervalue = md.DecimalField('Numbervalue', max_digits=18, decimal_places=0)
    textvalue = md.TextField('Textvalue')
    datevalue = md.DateTimeField('Datevalue')
    valuetype = md.CharField('Valuetype', max_length=255)
            
    def __str__(self):
        return f'{self.stringvalue or ""}{self.numbervalue or ""}{self.textvalue or ""}{self.datevalue or ""}'