from datetime import date

from django.contrib import admin
from monthdelta import monthdelta, monthmod

from .datautils import today, months
from .models import (Booking, Business, Division, Employee, MonthBookingSummary, MonthBookingEmployee,
                     Passport, Position, Project, ProjectBooking,
                     ProjectMember, Role, Salary, StaffingTable)

admin.AdminSite.site_header = 'Тверской филиал'


@admin.register(Division)
class DivisionAdmin(admin.ModelAdmin):
    '''
    Справочник подразделений
    '''
  #  class EmployeeInline(admin.TabularInline):
  #      model = Employee
  #      extra = 1
  #      fk_name = 'position__division'

  #  inlines = [EmployeeInline]
    list_display = ('name', 'full_name', 'head', 'occupied')


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    '''
    Справочник должностей
    '''
    list_display = ('name', 'occupied')


@admin.register(StaffingTable)
class StaffingTableAdmin(admin.ModelAdmin):
    '''
    Администрирование штатного расписания
    '''
    list_display = ('division', 'position', 'count', 'occupied', 'vacant')
    list_filter = ('division__name', 'position__name')


class ProjectMemberInline(admin.TabularInline):
    model = ProjectMember
    extra = 0


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    '''
    Администрирование сотрудника
    '''
    class PassportInline(admin.StackedInline):
        model = Passport
        extra = 0
        fields = (('doctype', 'is_valid'), ('series', 'number'),
                  ('issuer', 'issue_date'), 'registered')

    class SalaryInline(admin.TabularInline):
        model = Salary
        extra = 0

    fieldsets = [
        (None,
            {'fields': [
                'last_name', 'first_name', 'sur_name',
                ('division', 'position'),
                'hire_date', 'fire_date',
                ('is_3d', 'business_k')],
             'classes': [],
             }),
        ('Дополнительные сведения'.upper(),
            {'fields': [
                'birthday',
                ('local_phone', 'work_phone', 'mobile_phone')],
             'classes': [
                'collapse']
             })
    ]

    inlines = [PassportInline, SalaryInline]
    list_display = ('full_name', 'division', 'position',
                    'salary', 'hire_date', 'fire_date', 'is_3d')
    list_filter = ('division__name', 'position__name',
                   'is_3d', 'hire_date', 'fire_date')


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    '''
    Администрирование проекта и рабочей группы
    '''
    inlines = [ProjectMemberInline]
    list_display = ('__str__', 'lead', 'member_count', 'volume_str',
                    'start_date', 'finish_date', 'state')
    list_filter = ('business__name', 'state', 'budget_state')


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    '''
    Справочник бизнесов
    '''
    list_display = ('name', 'lead')


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    '''
    Справочник проектных ролей
    '''
    list_display = ('role', 'is_lead')


@admin.register(ProjectMember)
class ProjectMemberAdmin(admin.ModelAdmin):
    '''
    Администрирование участников
    '''
    class BookingInline(admin.TabularInline):
        model = Booking
        extra = 0

    inlines = [BookingInline]
    list_display = ('project', 'employee', 'role', 'start_date',
                    'finish_date', 'volume_str', 'percent_str', 'month_count', 'load_str')
    list_display_links = ('employee',)
    list_filter = ('project__short_name', 'role', 'project__state')
    # search_fields = (
    #    'employee__last_name', 'employee__first_name', 'employee__sur_name',
    #    'project__business__name','project__short_name', 'role__role')
    date_hierarchy = 'project__start_date'


class BaseBookingAdmin(admin.ModelAdmin):
    '''
    Базовый класс для сводных отчетов по месячной загрузке
    '''
    # Фильтр отображения по годам
    class YearFilter(admin.SimpleListFilter):
        # Human-readable title which will be displayed in the
        # right admin sidebar just above the filter options.
        title = 'Данные за год'

        # Parameter for the filter that will be used in the URL query.
        parameter_name = 'year'

        def lookups(self, request, model_admin):
            qs = model_admin.get_queryset(request).order_by('month')

            first_year = qs.first().month.year
            last_year = qs.last().month.year
            
            return ( (year, year) for year in range(first_year, last_year + 1) )

        def queryset(self, request, queryset):
            # не фильтруем, фильтр по датам вычисляется в changelist_view()    
            return queryset

    list_display_links = None
    list_filter = (YearFilter,)
    
    # Данные месячной загрузки можно только смотреть или удалить (через связанный объект)
    def has_add_permission(self, request, extra_context=None): return False
    def has_change_permission(self, request, extra_context=None): return False



@admin.register(MonthBookingSummary)
class MonthBookingAdmin(BaseBookingAdmin):
    '''
    Отчет о месячной загрузке сотрудников
    '''
    # Столбцов в отчете
    COLUMNS = 18

    change_list_template = 'admin/booking_summary_change_list.html'

    list_filter = (
        BaseBookingAdmin.YearFilter,
        'booking__project_member__project__short_name',
        'booking__project_member__role__role',
        'booking__project_member__project__state',
        'booking__project_member__project__budget_state'
    )
    
    # Отображение списка сотрудников и месячной загруженности
    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(
            request,
            extra_context=extra_context
        )

        try:
            cl = response.context_data['cl']
            qs = cl.queryset
            year = cl.get_filters_params().get("year", None)
        except (AttributeError, KeyError):
            return response

        if year:
            month_from = date(int(year), 1, 1)
        else:
            month_from = today().replace(day=1) - monthdelta(MonthBookingAdmin.COLUMNS - 12)

        month_list = [month_from + monthdelta(i) for i in range(MonthBookingAdmin.COLUMNS)]
        
        # фильтр на диапазон дат из списка для отображения
        qs = qs.filter(month__range=(month_list[0], month_list[-1]))

        response.context_data['months'] = month_list
        response.context_data['summary'] = qs.get_booking(month_list)
        response.context_data['projects'] = sorted(set(qs.values_list(
            'booking__project_member__project__short_name', flat=True)))

        return response

@admin.register(ProjectBooking)
class ProjectBookingAdmin(BaseBookingAdmin):
    '''
    Отчет о загрузке сотрудников в проектах
    '''
    # Фильтр отображения по годам
    class MonthFilter(admin.SimpleListFilter):
        title = 'Месяц'
        parameter_name = 'month'

        def lookups(self, request, model_admin):
            return months()

        def queryset(self, request, queryset):
            # не фильтруем, фильтр по датам вычисляется в changelist_view()    
            return queryset
    
    change_list_template = 'admin/booking_projects_change_list.html'
    
    list_filter = (
        BaseBookingAdmin.YearFilter,
        MonthFilter,
        'booking__project_member__project__state',
        'booking__project_member__project__budget_state'
    )

    # Отображение списка сотрудников и загруженности в проектах
    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(
            request,
            extra_context=extra_context
        )

        try:
            cl = response.context_data['cl']
            qs = cl.queryset
            year = cl.get_filters_params().get("year", None)
            month_num = cl.get_filters_params().get("month", None)
        except (AttributeError, KeyError):
            return response

        month = today().replace(day=1)

        # Извлечение значений из фильтра
        try:
            month = month.replace(year=int(year))
        except (TypeError, ValueError):
            pass

        try:
            month = month.replace(month=int(month_num))
        except (TypeError, ValueError):
            pass

        # фильтр на дату для отображения
        # TODO: перенести в кастомный qs прокси-модели, упростить интерфейс get_booking
        qs = qs.filter(month__exact=month)
        projects = sorted(set(qs.values_list(
            'booking__project_member__project__short_name', flat=True)))

        response.context_data['month'] = month
        response.context_data['summary'] = qs.get_booking(projects, month)
        response.context_data['projects'] = projects

        return response


@admin.register(MonthBookingEmployee)
class MonthBookingEmployeeAdmin(BaseBookingAdmin):
    '''
    Отчет о месячной загрузке сотрудника в проектах
    '''
    # Столбцов в отчете
    COLUMNS = 18

    change_list_template = 'admin/booking_employee_change_list.html'

    list_filter = (
        BaseBookingAdmin.YearFilter,
        'booking__project_member__employee'
    )
    
    # Отображение списка проектов и месячной загруженности по выбранному сотруднику
    # если сотрудник не выбран - ничего не отображается 
    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(
            request,
            extra_context=extra_context
        )

        try:
            cl = response.context_data['cl']
            qs = cl.queryset
            year = cl.get_filters_params().get("year", None)
            employee_id = cl.get_filters_params().get('booking__project_member__employee__id__exact', None)
        except (AttributeError, KeyError):
            return response

        if year:
            month_from = date(int(year), 1, 1)
        else:
            month_from = today().replace(day=1) - monthdelta(MonthBookingAdmin.COLUMNS - 12)

        month_list = [month_from + monthdelta(i) for i in range(MonthBookingAdmin.COLUMNS)]

        # pylint: disable=no-member
        response.context_data['months'] = month_list
        response.context_data['member'] = Employee.objects.filter(id=employee_id).first()
        response.context_data['summary'], response.context_data['total'] = qs.get_booking(month_list, employee_id)
        
        return response