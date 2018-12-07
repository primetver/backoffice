from django.contrib import admin

from .models import (Worklog)

# Register your models here.

@admin.register(Worklog)
class WorklogAdmin(admin.ModelAdmin):
    '''
    Журнал работ
    '''
    def has_add_permission(self, request, extra_context=None): return False
    def has_change_permission(self, request, extra_context=None): return False
    def has_delete_permission(self, request, extra_context=None): return False

    list_display = ('issueid', 'updated', 'updateauthor', 'worklogbody', 'startdate', 'timeworked')
    list_filter = ('updateauthor',)
    date_hierarchy = 'startdate'