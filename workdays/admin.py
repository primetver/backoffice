# pylint: disable=no-member
from datetime import date, timedelta

from django.contrib import admin, messages
from django.db import transaction
from django.utils import timezone

from .models import HolidayName, SpecialDay, WorktimeStandards
from .utils import standards_report

# Register your models here.


@admin.register(HolidayName)
class HolidayNameAdmin(admin.ModelAdmin):
    '''
    Справочник праздников
    '''
    @transaction.atomic
    def make_published_year(self, request, queryset, year):
        for hd in queryset:
            for n in range(hd.count):
                SpecialDay.objects.update_or_create(
                    date=date(year, hd.month, hd.day) + timedelta(n),
                    defaults={
                        'daytype':SpecialDay.HOLIDAY,
                        'dayname':hd
                    }
                )
        self.message_user(request, f'Праздники добавлены в календарь {year} года')
    
    def make_published(self, request, queryset):
        return self.make_published_year(request, queryset, timezone.now().year)
    make_published.short_description = 'Добавить в календарь текущего года'

    def make_published_next(self, request, queryset):
        return self.make_published_year(request, queryset, timezone.now().year + 1)
    make_published_next.short_description = 'Добавить в календарь следующего года'

    list_display = ('dayname','month', 'day', 'count')
    actions = (make_published, make_published_next)



@admin.register(SpecialDay)
class SpecialDayAdmin(admin.ModelAdmin):
    '''
    Редактирование календаря особых дней
    '''
    list_display = ('date', 'daytype', 'dayname')
    list_filter = ('date', 'daytype', 'dayname') 
    date_hierarchy = 'date'   


@admin.register(WorktimeStandards)
class WorktimeStandardsAdmin(admin.ModelAdmin):
    '''
    Отчет по нормам рабочего времени 
    '''
    change_list_template = 'admin/worktime_standards_change_list.html'

    # Фильтр отображения по годам
    class YearFilter(admin.SimpleListFilter):
        # Human-readable title which will be displayed in the
        # right admin sidebar just above the filter options.
        title = 'Данные за год'

        # Parameter for the filter that will be used in the URL query.
        parameter_name = 'year'

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
        # Перечень значений фильтра для выбора
        def lookups(self, request, model_admin):
            qs = model_admin.get_queryset(request).order_by('date')

            first_year = qs.first().date.year
            last_year = qs.last().date.year
            
            return ( (year, year) for year in range(first_year, last_year + 1) )

        def queryset(self, request, queryset):
            # не фильтруем, фильтр по датам вычисляется в changelist_view()    
            return queryset

    list_display_links = None
    list_filter = (YearFilter,)
    
    # Данные можно только смотреть
    def has_add_permission(self, request, extra_context=None): return False
    def has_change_permission(self, request, extra_context=None): return False
    def has_delete_permission(self, request, extra_context=None): return False

    # Отображение отчета по нормам рабочего времени
    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(
            request,
            extra_context=extra_context
        )

        try:
            cl = response.context_data['cl']
            qs = cl.queryset
            year = int(cl.get_filters_params().get("year", timezone.now().year))
        except (AttributeError, KeyError, TypeError, ValueError):
            return response

        response.context_data['year'] = year
        response.context_data['header'] = ['Дней', 'Рабочих дней', 'Выходных', 'Рабочих часов']
        response.context_data['summary'] = standards_report(year)

        return response
