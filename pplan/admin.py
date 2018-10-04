from django.contrib import admin
from monthdelta import monthdelta, monthmod

from .datautils import today
from .models import (Booking, Business, Division, Employee, EmployeeBooking,
                     MonthBooking, Passport, Position, Project, ProjectMember, ProjectMemberBooking,
                     Role, Salary, StaffingTable)

from django_pandas.io import read_frame


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
    list_display = ('__str__', 'lead', 'member_count',
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
                    'finish_date', 'volume', 'percent')
    list_filter = ('project__business__name',
                   'project__short_name', 'project__state', 'role')
    # search_fields = (
    #    'employee__last_name', 'employee__first_name', 'employee__sur_name',
    #    'project__business__name','project__short_name', 'role__role')
    date_hierarchy = 'project__start_date'


@admin.register(MonthBooking)
class MonthBookingAdmin(admin.ModelAdmin):
    readonly_fields = ('booking', 'month', 'days', 'load', 'volume')
    list_display_links = None
    list_filter = (
        'booking__project_member__project__short_name',
        'booking__project_member__role__role',
        'booking__project_member__project__state',
        'booking__project_member__project__budget_state'
    )
    change_list_template = 'admin/booking_summary_change_list.html'

    # Изменение отображения списка сотрудников и месячной загруженности в проекте
    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(
            request,
            extra_context=extra_context
        )

        try:
            qs = response.context_data['cl'].queryset
        except (AttributeError, KeyError):
            return response

        before = 6
        count = 12 + before
        month_from = today().replace(day=1) - monthdelta(before)
        month_list = [month_from + monthdelta(i) for i in range(count)]

        response.context_data['months'] = month_list
        response.context_data['summary'] = get_booking_summary(qs, month_list=month_list)

        return response

# вспомогательная функция формирования набора данных для отображения


def get_booking_summary(qs, month_list=None):
    month_list = month_list if month_list else [today().replace(day=1)]

    # ограничение запроса заданным диапазоном интересующих нас месяцев, если они заданы
    if month_list:
        qs = qs.filter(month__range=(month_list[0], month_list[-1]))

    # чтение DataFrame
    df = read_frame(
        qs,
        fieldnames=[
            'booking__project_member__employee',
            #'booking__project_member__project__short_name',
            'month',
            'load',
            'volume'
        ]
    )

    month_booking = df.groupby(['booking__project_member__employee', 'month']).sum()

    if month_booking.empty:
        return []

    return (
        {
            'name': e, 
            'booking': [
                {
                    'load':booking.ix[e].load.get(month, 0),
                    'volume':booking.ix[e].volume.get(month, 0)
                } for month in month_list
            ]
        } for e, booking in month_booking.groupby(level='booking__project_member__employee')
    )


@admin.register(EmployeeBooking)
class EmployeeBookingAdmin(admin.ModelAdmin):
    change_list_template = 'admin/booking_summary_change_list.html'
    list_filter = ('division__name', 'position__name',
                   'is_3d', 'hire_date', 'fire_date')

    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(
            request,
            extra_context=extra_context
        )

        try:
            qs = response.context_data['cl'].queryset
        except (AttributeError, KeyError):
            return response

        before = 6
        count = 12 + before
        month_from = today().replace(day=1) - monthdelta(before)
        month_list = [month_from + monthdelta(i) for i in range(count)]

        response.context_data['months'] = month_list
        response.context_data['summary'] = (
            {
                'name': e.full_name(),
                'booking': e.booking(month_list)
            } for e in qs
        )

        return response


@admin.register(ProjectMemberBooking)
class ProjectMemberBookingAdmin(admin.ModelAdmin):
    change_list_template = 'admin/booking_summary_change_list.html'
    list_filter = ('project__short_name',)

    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(
            request,
            extra_context=extra_context
        )

        try:
            qs = response.context_data['cl'].queryset
        except (AttributeError, KeyError):
            return response

        before = 6
        count = 12 + before
        month_from = today().replace(day=1) - monthdelta(before)
        month_list = [month_from + monthdelta(i) for i in range(count)]

        response.context_data['months'] = month_list
        response.context_data['summary'] = (
            {
                'name': e.employee.full_name(),
                'booking': e.member_booking(month_list)
            } for e in qs
        )

        return response
