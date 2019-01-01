from datetime import date, timedelta
from decimal import Decimal

from django.contrib import admin
from django.utils import timezone
from monthdelta import monthdelta, monthmod

from workdays.utils import workhours

from .models import (BudgetCustomField, Customfield, CustomfieldOption,
                     JiraIssue, JiraUser, Worklog, WorklogReport,
                     WorklogSummary)

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
    list_display = ('issuenum', 'budget_name', 'summary',
                    'creator', 'assignee', 'created', 'updated', 'hours')
    list_filter = ('creator', 'assignee')
    date_hierarchy = 'updated'


@admin.register(Worklog)
class WorklogAdmin(JiraAdmin):
    '''
    Журнал работ
    '''
    list_display = ('id', 'budget_name', 'updated',
                    'updateauthor', 'worklogbody', 'startdate', 'hours')
    list_filter = ('updateauthor',)
    date_hierarchy = 'startdate'


@admin.register(Customfield)
class CustomfieldAdmin(JiraAdmin):
    '''
    Определения пользовательских полей
    '''
    list_display = ('cfname', 'description')


#
# Представления отчетов
#

def get_selected_year(request):
    '''
    Выбранный или текущий год
    '''
    try:
        selected = int(request.GET.get('year'))
        year = date(selected, 1, 1).year
    except:
        year = None
    return year or timezone.now().year


def get_selected_budget(request):
    '''
    Выбранный бюджет
    '''
    return request.GET.get('budget')


class BaseReportAdmin(JiraAdmin):
    '''
    Базовый класс для представлений отчетов
    '''

    # Число колонок в отчете
    COLUMNS = 12

    # Начальный год за который имеет смысл смотреть выборку данных
    # TODO: параметр настройки
    START_YEAR = 2014


    class ReportListFilter(admin.SimpleListFilter):
        # Замена функции выбора, так чтобы значение по умолнянию вместо "Все" было "Текущий"
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

    # Фильтр отображения по годам
    class YearFilter(ReportListFilter):
        # Human-readable title which will be displayed in the
        # right admin sidebar just above the filter options.
        title = 'Данные за год'

        # Parameter for the filter that will be used in the URL query.
        parameter_name = 'year'

        def lookups(self, request, model_admin):
            qs = model_admin.get_queryset(request).order_by('startdate').filter(
                startdate__year__gte=BaseReportAdmin.START_YEAR
            )

            # ограничение диапазона данными по себе, если нет прав смотреть по всем
            if not request.user.has_perm('jiradata.view_all'):
                qs = qs.filter(author=request.user.username)

            try:
                first_year = qs.first().startdate.year
                last_year = qs.last().startdate.year
                return ((year, year) for year in range(first_year, last_year + 1))
            except (AttributeError):
                return ()

        def queryset(self, request, queryset):
            # Фильтр по выбранному году
            year = get_selected_year(request)
            return queryset.filter(startdate__year=year)

    # Фильтр отображения по пользователям Jira
    class UserFilter(ReportListFilter):
        # Human-readable title which will be displayed in the
        # right admin sidebar just above the filter options.
        title = 'Сотрудники'

        # Parameter for the filter that will be used in the URL query.
        parameter_name = 'user'

        # формирование перечня пользователей в зависимости от прав
        def lookups(self, request, model_admin):
            # перечень для выбора доступен только с правом jiradata.view_all
            if request.user.has_perm('jiradata.view_all'):
                # Выбор года для ограничения списка пользователей
                year = get_selected_year(request)

                qs = model_admin.get_queryset(
                    request).filter(startdate__year=year)
                users = qs.values_list('author', flat=True).distinct()
                return ((user, JiraUser.objects.filter(user_name=user).first() or user) for user in users)
            return ()

        def queryset(self, request, queryset):
             # не фильтруем, фильтр вычисляется в changelist_view()
            return queryset

    # Фильтр отображения по бюджетам проектов
    class BudgetFilter(admin.SimpleListFilter):
        # Human-readable title which will be displayed in the
        # right admin sidebar just above the filter options.
        title = 'Бюджеты'

        # Parameter for the filter that will be used in the URL query.
        parameter_name = 'budget'

        # формирование перечня бюджетов в зависимости от года
        def lookups(self, request, model_admin):
            # выбор года для ограничения списка бюджетов
            year = get_selected_year(request)
            qs = model_admin.get_queryset(
                request).filter(startdate__year=year)

            # ограничение списка бюджетов только теми, по которым решал задачи пользователь
            if not request.user.has_perm('jiradata.view_all'):
                qs = qs.filter(author__exact=request.user.username)

            issues = qs.values_list('issueid', flat=True).distinct()
            return (BudgetCustomField(issueid).budget_id_name() for issueid in issues)

        def queryset(self, request, queryset):
             # не фильтруем, фильтр вычисляется в changelist_view()
            return queryset

    list_display_links = None
    list_filter = (YearFilter,)


@admin.register(WorklogSummary)
class WorklogSummaryAdmin(BaseReportAdmin):
    '''
    Сводный отчет о месячной фактической загрузке сотрудников
    '''

    change_list_template = 'admin/workload_summary_change_list.html'
    
    list_filter = (
        BaseReportAdmin.YearFilter,
        BaseReportAdmin.BudgetFilter
    )

    # Отображение списка пользователей и месячной загруженности
    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(
            request,
            extra_context=extra_context
        )

        try:
            cl = response.context_data['cl']
            qs = cl.queryset
        except (AttributeError, KeyError):
            return response

        # выбранный диапазон месяцев
        year = get_selected_year(request)
        month_list = [date(year, 1+i, 1) for i in range(BaseReportAdmin.COLUMNS)]

        # список норм рабочего времени
        month_norma = [Decimal(
            workhours(m, m + monthdelta(1) - timedelta(days=1))) for m in month_list]

        # перечень бюджетов из набора данных или выбранный бюджет
        budget = get_selected_budget(request)
        if budget:
            budget_names = [CustomfieldOption.objects.filter(id=budget).first().customvalue]
        else:
            issues = qs.values_list('issueid', flat=True).distinct()
            budget_names = [BudgetCustomField(issueid).budget_name() for issueid in issues]

        response.context_data['months'] = month_list
        response.context_data['summary'] = qs.get_workload(month_list, budget, month_norma)
        response.context_data['budgets'] = budget_names

        return response


@admin.register(WorklogReport)
class WorklogReportAdmin(BaseReportAdmin):
    '''
    Отчет о месячной фактической загрузке сотрудника в проектах
    '''

    change_list_template = 'admin/workload_user_change_list.html'

    list_filter = (
        BaseReportAdmin.YearFilter,
        BaseReportAdmin.UserFilter
    )

    # Отображение списка бюджетов и месячной загруженности по выбранному сотруднику
    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(
            request,
            extra_context=extra_context
        )
        try:
            # извлечение данных запроса
            cl = response.context_data['cl']
            qs = cl.queryset
        except (AttributeError, KeyError, ValueError):
            return response

        # пользователь из параметров фильтра или текущий
        user = cl.get_filters_params().get('user', request.user.username)

        # проверка прав на просмотр указанного в запросе сотрудникa
        if not request.user.has_perm('jiradata.view_all') and user != request.user.username:
            return response

        # выбранный диапазон месяцев
        year = get_selected_year(request)
        month_list = [date(year, 1+i, 1) for i in range(BaseReportAdmin.COLUMNS)]
           
        # список норм рабочего времени
        month_norma = [Decimal(
            workhours(m, m + monthdelta(1) - timedelta(days=1))) for m in month_list]

        response.context_data['months'] = month_list
        response.context_data['member'] = JiraUser.objects.filter(user_name=user).first()
        response.context_data['summary'], response.context_data['total'] = qs.get_workload(
            month_list, user, month_norma)
        response.context_data['norma'] = month_norma

        return response
