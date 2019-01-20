from datetime import date, timedelta

from django.contrib import admin, messages
from django.utils import timezone
from monthdelta import monthdelta, monthmod

from workdays.utils import workhours

from .models import (BudgetCustomField, Customfield, CustomfieldOption,
                     JiraIssue, JiraUser, Worklog, WorklogReport,
                     WorklogSummary, WorklogFrame)

from timing import Timing

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

def get_year_param(admin, request):
    '''
    Выбранный или текущий год
    '''
    try:
        selected = int(request.GET.get('year'))
        year = date(selected, 1, 1).year
    except:
        admin.message_user(request, f'Указан ошибочный год, будет использован текущий', messages.ERROR)
        year = None
    return year or timezone.now().year


def get_budget_param(admin, request):
    '''
    Выбранный бюджет
    '''
    budget_id = request.GET.get('budget')
    if budget_id not in request.budget_id_list:
        admin.message_user(request, f'Указан ошибочный бюджет, выберите бюджет из фильтра', messages.ERROR)
        return None
    return budget_id


class BaseReportAdmin(JiraAdmin):
    '''
    Базовый класс для представлений отчетов
    '''

    # Число колонок в отчете
    COLUMNS = 12

    # Раскраска значений
    COLORS = {
        'blue':  'color:#4542f4',
        'green': 'color:#03941b',
        'red':   'color:#c51616'
    }

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
            # не фильтруем, фильтр вычисляется в changelist_view()
            return queryset

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
                year = get_year_param(model_admin, request)

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

        # формирование перечня бюджетов из загруженного набора данных
        def lookups(self, request, model_admin):
            worklogframe = request.worklogframe

            # ограничение набора данных только теми, по которым решал задачи пользователь
            if not request.user.has_perm('jiradata.view_all'):
                worklogframe = worklogframe.filter(author=request.user.username)
            
            # список бюджетов из набора
            budget_list = worklogframe.budget_list()
            # сохраняем список идентификаторов бюджетов (первые элементы списка последовательстей)
            request.budget_id_list = list(zip(*budget_list))[0]

            return budget_list

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

    # Отображение списка пользователей и месячной загруженности за выбранный год
    def changelist_view(self, request, extra_context=None):
        timing = Timing('CLV')
        timingsum = Timing('SUM')

        # выбранный диапазон месяцев
        year = get_year_param(self, request)
        month_list = [date(year, 1+i, 1) for i in range(BaseReportAdmin.COLUMNS)]
        
        qs = self.get_queryset(request).filter(
            startdate__range=(month_list[0], month_list[-1] + monthdelta(1))
        )

        # загрузка и сохранение в request журнала работ за год
        # (оптимизация для предотвращения необходимости повторной загрузки фрейма в фильтрах)
        worklogframe = WorklogFrame().load(qs)
        request.worklogframe = worklogframe

        timing.log()

        # заполнение фильтров в базовом классе
        response = super().changelist_view(
            request,
            extra_context=extra_context
        )

        try:
            cl = response.context_data['cl']
            qs = cl.queryset
        except (AttributeError, KeyError):
            return response

        # фильтрация по выбранному бюджету
        budget = get_budget_param(self, request)
        if budget:
            worklogframe = worklogframe.filter(budget_id=budget)
        
        # перечень названий бюджетов из отфильтрованного набора данных
        # (вторые элементы в списке последовательностей - названия бюджетов)
        project_list = list(zip(*worklogframe.budget_list()))[1]
        # список норм рабочего времени
        month_norma = [workhours(m, m + monthdelta(1) - timedelta(days=1)) for m in month_list]

        timing.log()

        response.context_data['months'] = month_list
        response.context_data['summary'] = worklogframe.aggr_month_user(month_list, month_norma)
        response.context_data['projects'] = project_list

        timing.log()
        timingsum.log()

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
        t0 = Timing('USER')

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
        year = get_year_param(self, request)
        month_list = [date(year, 1+i, 1) for i in range(BaseReportAdmin.COLUMNS)]
           
        # список норм рабочего времени
        month_norma = [workhours(m, m + monthdelta(1) - timedelta(days=1)) for m in month_list]

        # Загрузка данных и расчет статистик
        qs = qs.filter(
            startdate__range=(month_list[0], month_list[-1] + monthdelta(1)),
            author=user
        )
        worklogframe = WorklogFrame().load(qs)

        response.context_data['months'] = month_list
        response.context_data['member'] = JiraUser.objects.filter(user_name=user).first()
        response.context_data['summary'], response.context_data['total'] = worklogframe.aggr_month_budget(month_list, month_norma)
        response.context_data['norma'] = month_norma

        t0.log()

        return response
