# pylint: disable=no-member
from datetime import date, timedelta

from django.contrib import admin, messages
from django.db import transaction
from django.utils import timezone

from .models import HolidayName, SpecialDay, WorktimeStandards
from .utils import standards_report, WEEKEND

# Register your models here.


@admin.register(HolidayName)
class HolidayNameAdmin(admin.ModelAdmin):
    '''
    Справочник праздников
    '''
    list_display = ('dayname','month', 'day', 'count')


class YearFilter(admin.SimpleListFilter):
    '''
    Фильтр отображения по годам
    '''
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = 'Данные за год'

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'date__year'

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
        try:
            year = date(int(self.value()), 1, 1).year
        except:
            year = timezone.now().year
        return queryset.filter(date__year=year)


def _get_year_param(admin, request):
    try:
        param = request.GET.get('date__year') or timezone.now().year
        return date(int(param), 1, 1).year
    except (AttributeError, KeyError, TypeError, ValueError):
        admin.message_user(request, f'Указан ошибочный год, выберите параметр из фильтра', messages.ERROR)
        return None


@admin.register(SpecialDay)
class SpecialDayAdmin(admin.ModelAdmin):
    '''
    Редактирование календаря измененных дней
    '''
    @transaction.atomic
    def _add_holidays(self, request, queryset, year):
        hd_qs = HolidayName.objects.all()
        for hd in hd_qs:
            # установка сокращенного дня перед началом праздника
            short_date = date(year, hd.month, hd.day) - timedelta(1)
            # если уже не установленный  день и не выходной
            if not SpecialDay.objects.filter(date=short_date).exists() and \
               not short_date.weekday() in WEEKEND:
                SpecialDay.objects.update_or_create(
                    date=short_date,
                    defaults={'daytype':SpecialDay.SHORTENED}
                )

            # установка праздничных дней
            count = hd.count
            n = 0
            while n < count:
                holiday_date = date(year, hd.month, hd.day) + timedelta(n)
                # смещение праздника на первый нерабочий день, кроме января
                if holiday_date.weekday() in WEEKEND and not holiday_date.month == 1:
                    count += 1
                    n += 1
                    continue
                # если уже не установленный  день
                if not SpecialDay.objects.filter(date=holiday_date).exists():
                    SpecialDay.objects.update_or_create(
                        date=holiday_date,
                        defaults={
                            'daytype':SpecialDay.HOLIDAY,
                            'dayname':hd
                        }
                    )
                n += 1
        self.message_user(request, f'Праздники добавлены в календарь {year} года, установите корректный перенос праздничных дат января')
   
    def add_holidays(self, request, queryset):
        year = _get_year_param(self, request)
        if not year:
            return # некорректный параметр года
        # заполнение календаря
        self._add_holidays(request, queryset, year)
    add_holidays.short_description = 'Добавить праздники в календарь текущего года'

    def add_holidays_next(self, request, queryset):
        year = _get_year_param(self, request)
        if not year:
            return # некорректный параметр года
        # заполнение календаря
        self._add_holidays(request, queryset, year + 1)
    add_holidays_next.short_description = 'Добавить праздники в календарь следующего года'
    
    def add_holidays_prev(self, request, queryset):
        year = _get_year_param(self, request)
        if not year:
            return # некорректный параметр года
        # заполнение календаря
        self._add_holidays(request, queryset, year - 1)
    add_holidays_prev.short_description = 'Добавить праздники в календарь предыдущего года'

    list_display = ('date', 'daytype', 'dayname', 'comment')
    list_filter = (YearFilter, 'daytype', 'dayname') 
    date_hierarchy = 'date'
    actions = (add_holidays_prev, add_holidays, add_holidays_next) 


@admin.register(WorktimeStandards)
class WorktimeStandardsAdmin(admin.ModelAdmin):
    '''
    Отчет по нормам рабочего времени 
    '''
    change_list_template = 'admin/worktime_standards_change_list.html'

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
            param = request.GET.get('date__year') or timezone.now().year
            year = date(int(param), 1, 1).year
        except (AttributeError, KeyError, TypeError, ValueError):
            self.message_user(request, f'Указан ошибочный параметр, выберите параметр из фильтра', messages.ERROR)
            return response

        response.context_data['year'] = year
        response.context_data['header'] = ['Календарных', 'Рабочих', 'Выходных', 'Загрузка 100%', 'Загрузка 70%','Загрузка 50%']
        response.context_data['summary'] = standards_report(year)

        return response
