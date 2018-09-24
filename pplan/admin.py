from django.contrib import admin
from .models import Division, Position, StaffingTable, Employee, Salary, Business, Project, Role, ProjectMember, Booking


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
    list_display = ('division', 'position', 'count','occupied')
    list_filter = ('division__name', 'position')


class ProjectMemberInline(admin.TabularInline):
    model = ProjectMember
    extra = 1
    

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    '''
    Администрирование сотрудника
    '''
    class SalaryInline(admin.TabularInline):
        model = Salary
        extra = 1

    inlines = [SalaryInline, ProjectMemberInline]
    list_display = ('full_name', 'salary', 'hire_date', 'fire_date', 'is_3d')
    list_filter = ('division__name', 'position__name', 'hire_date', 'is_3d', 'fire_date')


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    '''
    Администрирование проекта и рабочей группы
    '''
    inlines = [ProjectMemberInline]
    list_display = ('__str__', 'lead', 'member_count','start_date', 'finish_date', 'state')
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
    list_display = ('project', 'employee', 'role')
    list_filter = ('project__business__name','project__short_name', 'project__state', 'role')
    #search_fields = (
    #    'employee__last_name', 'employee__first_name', 'employee__sur_name',
    #    'project__business__name','project__short_name', 'role__role')

admin.site.register(Booking)
