from django.contrib import admin

from .models import (JiraIssue, Worklog, Customfield)

# Register your models here.

class JiraAdmin(admin.ModelAdmin):
    '''
    Доступ только для чтения
    '''
    def has_add_permission(self, request, extra_context=None): return False
    def has_change_permission(self, request, extra_context=None): return False
    def has_delete_permission(self, request, extra_context=None): return False


@admin.register(JiraIssue)
class JiraIssueAdmin(JiraAdmin):
    '''
    Запросы Jira
    '''
    list_display = ('issuenum', 'budget_name', 'summary', 'creator', 'assignee', 'created', 'updated', 'hours')
    list_filter = ('creator', 'assignee')
    date_hierarchy = 'updated'


@admin.register(Worklog)
class WorklogAdmin(JiraAdmin):
    '''
    Журнал работ
    '''
    list_display = ('id', 'budget_name', 'updated', 'updateauthor', 'worklogbody', 'startdate', 'hours')
    list_filter = ('updateauthor',)
    date_hierarchy = 'startdate'


@admin.register(Customfield)
class CustomfieldAdmin(JiraAdmin):
    '''
    Определения пользовательских полей
    '''
    list_display = ('cfname', 'description')