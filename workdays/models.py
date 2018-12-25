# pylint: disable=no-member
from datetime import date

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models as md
from django.utils import timezone

# Create your models here.

class HolidayName(md.Model):
    '''
    Наименование праздника
    '''
    class Meta():
        verbose_name = 'наименование праздника'
        verbose_name_plural = 'наименования праздников'
        ordering = ('month', 'day')

    dayname = md.CharField('Название', max_length=150)
    month = md.IntegerField('Месяц', default=1, validators=[MinValueValidator(1), MaxValueValidator(12)])
    day = md.IntegerField('День', default=1, validators=[MinValueValidator(1), MaxValueValidator(31)])
    count = md.IntegerField('Число дней', default=1, validators=[MinValueValidator(1), MaxValueValidator(10)])

    def clean(self):
        try:
            date(timezone.now().year, self.month, self.day)
        except ValueError:
            raise ValidationError('Введите корректное календарное значение месяца и дня праздника')
    
    def __str__(self):
        return self.dayname


class SpecialDay(md.Model):
    '''
    Календарь праздников, сокращенных и рабочих выходных дней
    '''
    class Meta():
        verbose_name = 'нестандартный день календаря'
        verbose_name_plural = 'нестандартные дни календаря'
        ordering = ('date',)


    HOLIDAY = 'HL'
    SHORTENED = 'SH'
    WORK = 'WK'
    DAYTYPE_CHOICES = (
        (HOLIDAY,   'Выходной день'),
        (SHORTENED, 'Сокращенный день'),
        (WORK, 'Рабочий день')
    )

    date = md.DateField('Дата', db_index=True, unique=True)
    daytype = md.CharField('Тип дня', max_length=2, default=HOLIDAY, choices=DAYTYPE_CHOICES)
    dayname = md.ForeignKey(HolidayName, null=True, blank=True, on_delete=md.PROTECT, verbose_name='Название')
    comment = md.TextField('Комментарий', null=True, blank=True)

    def workdayholidayhours(self, hours):
        if self.daytype == SpecialDay.HOLIDAY:
            return (0, 1, 0)
        elif self.daytype == SpecialDay.SHORTENED:
            return (1, 0, hours - 1)
        else:
            return (1, 0, hours)
    
    def __str__(self):
        return f'{self.get_daytype_display()} {self.date:%d.%m.%Y} {self.dayname or ""}'.rstrip()


class WorktimeStandards(SpecialDay):
    '''
    Модель отчета по нормам рабочего времени
    '''
    class Meta():
        proxy = True
        verbose_name = 'норма рабочего времени'
        verbose_name_plural = 'нормы рабочего времени'
        default_permissions = ('view',)
