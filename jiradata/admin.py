from datetime import date, timedelta

from django.contrib import admin, messages
from django.utils import timezone
from monthdelta import monthdelta, monthmod

from workdays.utils import workhours, today, last_weekend

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

def get_year_param(request):
    '''
    Выбранный или текущий год
    '''
    try:
        selected = int(request.GET.get('year'))
        year = date(selected, 1, 1).year
    except (TypeError, ValueError):
        year = None
    return year or timezone.now().year


def get_budget_param(request):
    '''
    Выбранный бюджет
    '''
    try:
        budget_id = float(request.GET.get('budget'))
        if budget_id not in request.budget_id_list:
            budget_id = -1 # fake id
    except TypeError:
        return None     # none get
    except ValueError:
        return -1       # conversion error
    return budget_id

def get_user_param(request):
    '''
    Выбранный или текущий пользователь
    '''
    try:
        user_id = request.GET.get('user')
        if user_id not in request.user_id_list:
            user_id = None
    except (AttributeError, TypeError, ValueError):
        user_id = None
    return user_id or request.user.username

def get_slice_param(request):
    '''
    Дата окончания среза данных
    '''
    flag = request.GET.get('sl')
    if flag == 'today':
        return today()
    elif flag == 'week':
        return last_weekend()
    else: 
        return None


def calc_month_norma(month_list, stop_date=None):
    '''
    Рассчитать список норм времени (опционально - по сегоднящний день)
    '''
    stop_date = stop_date or month_list[-1] + monthdelta(1)
    return [ 
        workhours(
            min(m, stop_date),
            min(m + monthdelta(1) - timedelta(days=1), stop_date)
        ) for m in month_list
    ]

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
    
    # Фильтр среза данных
    class SliceFilter(admin.SimpleListFilter):
        # Human-readable title which will be displayed in the
        # right admin sidebar just above the filter options.
        title = 'Срез данных'

        # Parameter for the filter that will be used in the URL query.
        parameter_name = 'sl'

        def lookups(self, request, model_admin):
            return (
                ('week', 'Предыдущая неделя'),
                ('today', 'Сегодня')
            )

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
            # список пользователей из набора
            user_list = request.worklogframe.user_list()
            # сохраняем список логинов пользователей (первые элементы списка последовательстей)
            try:
                request.user_id_list = tuple(zip(*user_list))[0]
            except IndexError:
                request.user_id_list = ()
            return user_list

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
            # список бюджетов из набора
            budget_list = request.worklogframe.budget_list()
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
        BaseReportAdmin.SliceFilter,
        BaseReportAdmin.YearFilter,
        BaseReportAdmin.BudgetFilter
    )

    # Отображение списка пользователей и месячной загруженности по выбранному бюджету
    def changelist_view(self, request, extra_context=None):
        t = Timing('WorklogSummary')

        # выбранный диапазон месяцев
        year = get_year_param(request)
        month_list = [date(year, 1+i, 1) for i in range(BaseReportAdmin.COLUMNS)]
        stop_date = get_slice_param(request)
        last_date = month_list[-1] + monthdelta(1)
        if stop_date and stop_date > last_date:
            # сброс параметра, если выбран набор данных в прошлом
            stop_date = None
        
        qs = self.get_queryset(request).filter(
            startdate__range=(
                month_list[0],
                stop_date or last_date
            )
        )

        # загрузка и сохранение в request журнала работ за год
        # (оптимизация для предотвращения необходимости повторной загрузки фрейма в фильтрах)
        worklogframe = WorklogFrame().load(qs)
        # ограничение набора данных только теми, по которым решал задачи пользователь
        if not request.user.has_perm('jiradata.view_all'):
            worklogframe = worklogframe.filter(author=request.user.username)

        request.worklogframe = worklogframe
        rows = worklogframe.rows() 

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
        budget = get_budget_param(request)
        if budget:
            worklogframe = worklogframe.filter(budget_id=budget)

        # перечень названий бюджетов из отфильтрованного набора данных
        # (вторые элементы в списке последовательностей - названия бюджетов)
        try:
            project_list = tuple(zip(*worklogframe.budget_list()))[1]
        except IndexError:
            project_list = ()
        # список норм рабочего времени
        month_norma = calc_month_norma(month_list, stop_date=stop_date)

        seconds = t.step()

        response.context_data['months'] = month_list
        response.context_data['summary'] = worklogframe.aggr_month_user(month_list, month_norma)
        response.context_data['projects'] = project_list
        response.context_data['norma'] = month_norma
        response.context_data['slice'] = stop_date
        response.context_data['year'] = year
        response.context_data['stat'] = f'{rows} строк обработано за {seconds:.2} c'

        return response


@admin.register(WorklogReport)
class WorklogReportAdmin(BaseReportAdmin):
    '''
    Отчет о месячной фактической загрузке сотрудника в проектах
    '''

    change_list_template = 'admin/workload_user_change_list.html'

    list_filter = (
        BaseReportAdmin.SliceFilter,
        BaseReportAdmin.YearFilter,
        BaseReportAdmin.UserFilter
    )

    # Отображение списка бюджетов и месячной загруженности по выбранному сотруднику
    def changelist_view(self, request, extra_context=None):
        t = Timing('WorklogReport')

        # выбранный диапазон месяцев
        year = get_year_param(request)
        month_list = [date(year, 1+i, 1) for i in range(BaseReportAdmin.COLUMNS)]
        stop_date = get_slice_param(request)
        last_date = month_list[-1] + monthdelta(1)
        if stop_date and stop_date > last_date:
            # сброс параметра, если выбран набор данных в прошлом
            stop_date = None
        
        qs = self.get_queryset(request).filter(
            startdate__range=(
                month_list[0],
                stop_date or last_date
            )
        )

        # загрузка и сохранение в request журнала работ за год
        # (оптимизация для предотвращения необходимости повторной загрузки фрейма в фильтрах)
        worklogframe = WorklogFrame().load(qs)
        # ограничение набора данных только теми, по которым решал задачи пользователь
        if not request.user.has_perm('jiradata.view_all'):
            worklogframe = worklogframe.filter(author=request.user.username)

        request.worklogframe = worklogframe
        rows = worklogframe.rows() 

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

        # фильтрация по выбранному сотруднику
        user = get_user_param(request)
        worklogframe = worklogframe.filter(author=user)

        # список норм рабочего времени
        month_norma = calc_month_norma(month_list, stop_date=stop_date)

        seconds = t.step()
        
        response.context_data['months'] = month_list
        response.context_data['member'] = JiraUser.objects.filter(user_name=user).first()
        response.context_data['summary'], response.context_data['total'] = worklogframe.aggr_month_budget(month_list, month_norma)
        response.context_data['norma'] = month_norma
        response.context_data['slice'] = stop_date
        response.context_data['year'] = year
        response.context_data['stat'] = f'{rows} строк обработано за {seconds:.2} c'

        return response
