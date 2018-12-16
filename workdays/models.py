from django.db import models as md

# Create your models here.


class Holidays(md.Model):
    '''
    Праздники и сокращенные дни
    '''
    class Meta():
        verbose_name = 'праздник'
        verbose_name_plural = 'праздники'

    HOLIDAY = 'HL'
    SHORTENED = 'SH'
    DAYTYPE_CHOICES = (
        (HOLIDAY,   'Нерабочий день'),
        (SHORTENED, 'Сокращенный день'),
    )

    date = md.DateField('Дата', db_index=True)
    dayname = md.CharField('Название', max_length=200)
    daytype = md.CharField('Тип дня', max_length=2, default=HOLIDAY, choices=DAYTYPE_CHOICES)
    shorthours = md.IntegerField('Сокращение', default=0)
