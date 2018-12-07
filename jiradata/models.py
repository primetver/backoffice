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
    issueid = md.DecimalField('Issue ID', max_digits=18, decimal_places=0)
    author = md.CharField('Создал', max_length=255)
    worklogbody = md.TextField('Содержание')
    created = md.DateTimeField('Дата создания')
    updateauthor = md.CharField('Обновил', max_length=255)
    updated = md.DateTimeField('Дата обновления')
    startdate = md.DateTimeField('Дата выполнения работ')
    timeworked = md.DecimalField('Затраченное время, c', max_digits=18, decimal_places=0)
        
    def __str__(self):
        return f'{self.updated} {self.updateauthor} {self.worklogbody} {self.timeworked} c'