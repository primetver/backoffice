from datetime import date

from django.contrib import admin
from monthdelta import monthdelta, monthmod

from .datautils import months, today
from .models import (Booking, Business, Division, Employee, Passport, Position,
                     Project, ProjectMember, Role, Salary, StaffingTable)


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
                'user',
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
