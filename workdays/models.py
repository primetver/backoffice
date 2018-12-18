# pylint: disable=no-member
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models as md

# TODO: настройка
WORKHOURS = 8

# Create your models here.

class HolidayName(md.Model):
    '''
    Наименование праздника
    '''
    class Meta():
        verbose_name = 'наименование праздника'
        verbose_name_plural = 'наименования праздников'

    dayname = md.CharField('Название', max_length=200)
    
    def __str__(self):
        return self.dayname


class SpecialDay(md.Model):
    '''
    Календарь праздников, сокращенных и рабочих выходных дней
    '''
    class Meta():
        verbose_name = 'особый календарный день'
        verbose_name_plural = 'особые календарные дни'


    HOLIDAY = 'HL'
    SHORTENED = 'SH'
    WORK = 'WK'
    DAYTYPE_CHOICES = (
        (HOLIDAY,   'Нерабочий день'),
        (SHORTENED, 'Сокращенный день'),
        (WORK, 'Рабочий день')
    )

    date = md.DateField('Дата', db_index=True)
    dayname = md.ForeignKey(HolidayName, null=True, on_delete=md.PROTECT, verbose_name='Название')
    daytype = md.CharField('Тип дня', max_length=2, default=HOLIDAY, choices=DAYTYPE_CHOICES)
    shorthours = md.IntegerField('Сокращение дня, час', default=0,
        validators=[MinValueValidator(0), MaxValueValidator(WORKHOURS)])

    def clean(self):
        if self.daytype != SpecialDay.SHORTENED:
            if self.daytype != SpecialDay.HOLIDAY:
                self.shorthours = WORKHOURS
            else:
                self.shorthours = 0

    def __str__(self):
        return f'{self.get_daytype_display()} {self.date:%d.%m.%Y} {self.dayname or ""}'.rstrip()