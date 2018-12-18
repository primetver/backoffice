from django.contrib import admin
from .models import HolidayName, SpecialDay

# Register your models here.


@admin.register(HolidayName)
class HolidayNameAdmin(admin.ModelAdmin):
    '''
    Справочник нерабочих дней
    '''
    list_display = ('dayname',)


@admin.register(SpecialDay)
class SpecialDayAdmin(admin.ModelAdmin):
    '''
    Редактирование календаря особых дней
    '''
    list_display = ('date', 'daytype', 'dayname', 'shorthours')