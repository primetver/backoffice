from datetime import date, timedelta

from django.contrib import admin
from django.utils import timezone
from monthdelta import monthdelta, monthmod

from .models import Customfield, JiraIssue, JiraUser, Worklog, WorklogReport

COLUMNS = 18

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



@admin.register(WorklogReport)
class WorklogReportAdmin(JiraAdmin):
    '''
    Отчет о месячной фактической загрузке сотрудника в проектах
    '''
    change_list_template = 'admin/workload_user_change_list.html'

    class ReportListFilter(admin.SimpleListFilter):
        # Замена функции выбора, так чтобы значение по умолчанию вместо "Все" было "Текущий"
        def choices(self, changelist):
            yield {
                'selected': self.value() is None,
                'query_string': changelist.get_query_string(remove=[self.parameter_name]),
                'display': 'Текущий',
            }
            for lookup, title in self.lookup_choices:
                yield {
                    'selected': self.value() == str(lookup),
                    'query_string': changelist.get_query_string({self.parameter_name: lookup}),
                    'display': title,
                }

    # Фильтр отображения по пользователям Jira 
    class UserFilter(ReportListFilter):
        # Human-readable title which will be displayed in the
        # right admin sidebar just above the filter options.
        title = 'Сотрудники'

        # Parameter for the filter that will be used in the URL query.
        parameter_name = 'user'

        # формирование перечня сотрудников в зависимости от прав
        def lookups(self, request, model_admin):
            if request.user.has_perm('jiradata.view_all'):
                users = JiraUser.objects.filter(active=1)
                return ( (user.user_name, str(user)) for user in users )
            return ()
            
        def queryset(self, request, queryset):
             # не фильтруем, фильтр вычисляется в changelist_view()
            return queryset
    
    # Фильтр отображения по годам
    class YearFilter(ReportListFilter):
        # Human-readable title which will be displayed in the
        # right admin sidebar just above the filter options.
        title = 'Данные за год'

        # Parameter for the filter that will be used in the URL query.
        parameter_name = 'year'

        def lookups(self, request, model_admin):
            qs = model_admin.get_queryset(request).order_by('startdate')
            
            # ограничение диапазона данными по себе, если нет прав смотреть по всем
            if not request.user.has_perm('jiradata.view_all'):
                qs = qs.filter(author=request.user.username)

            try:
                first_year = qs.first().startdate.year
                last_year = qs.last().startdate.year
                return ( (year, year) for year in range(first_year, last_year + 1) )
            except (AttributeError):
                return ()

        def queryset(self, request, queryset):
            # не фильтруем, фильтр вычисляется в changelist_view()    
            return queryset
    

    list_display_links = None
    list_filter = (
        YearFilter,
        UserFilter
    )
    
    # Отображение списка бюджетов и месячной загруженности по выбранному сотруднику
    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(
            request,
            extra_context=extra_context
        )

        # pylint: disable=no-member
        request.user.username
        
        try:
            # извлечение данных запроса
            cl = response.context_data['cl']
            qs = cl.queryset
            year = cl.get_filters_params().get("year")
            # пользователь из параметров фильтра или текущий
            user = cl.get_filters_params().get('user', request.user.username)
        
            # проверка прав на просмотр указанного в запросе сотрудникa
            if not request.user.has_perm('jiradata.view_all') and user != request.user.username:
                return response
            
            # проверка параметра year
            if year:
                month_from = date(int(year), 1, 1)
            else:
                date_from = timezone.now() - monthdelta(COLUMNS-1)
                month_from = date(date_from.year, date_from.month, 1)

            month_list = [month_from + monthdelta(i) for i in range(COLUMNS)]
        except (AttributeError, KeyError, ValueError):
            return response

        response.context_data['months'] = month_list
        response.context_data['member'] = JiraUser.objects.filter(user_name=user).first()
        response.context_data['summary'], response.context_data['total'] = qs.get_workload(month_list, user)
        
        return response
