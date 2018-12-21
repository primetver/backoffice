# pylint: disable=no-member
import itertools as it
from datetime import date, timedelta

from django.utils import timezone
from monthdelta import monthdelta 

from .models import SpecialDay

# TODO: настройка
WORKHOURS = 8    # число рабочих часов в стандартном дне
WEEKEND = (5,6)  # список выходных (понедельник = 0)

MONTHS = [
        (1, 'Январь'),
        (2, 'Февраль'),
        (3, 'Март'),
        (4, 'Апрель'),
        (5, 'Май'),
        (6, 'Июнь'),
        (7, 'Июль'),
        (8, 'Август'),
        (9, 'Сентябрь'),
        (10, 'Октябрь'),
        (11, 'Ноябрь'),
        (12, 'Декабрь')
] 

QUARTES = [
        (1, '1 квартал'),
        (4, '2 квартал'),
        (7, '3 квартал'),
        (10, '4 квартал')
] 


def today():
    return timezone.now().date()


def tomorrow():
    return today() + timedelta(days=1)


def is_holiday(date):
    holiday = SpecialDay.objects.filter(date=date).first()
    if holiday:
        return holiday.daytype == SpecialDay.HOLIDAY
    else:
        return date.weekday() in WEEKEND

def days(fromdate, todate):
    return (todate - fromdate).days + 1

def workdayholidayhours(fromdate, todate):
    '''
    Расчет числа рабочих дней, выходных и рабочих часов в заданных границах
    '''
    # перечень дней в заданных границах
    daygenerator = ( fromdate + timedelta(x) for x in range(days(fromdate, todate)) )
    
    # словарь специальных дней (день, часов) из производственного календаря
    qs = SpecialDay.objects.filter(date__range=(fromdate, todate))
    special_map = { day.date:day.workdayholidayhours(WORKHOURS) for day in qs }
    
    # генератор последовательности (день, часов) для перечня дней 
    dayhours = (
        # поиск дня в словаре, если нет - проверка на выходной
        special_map.get(
            date, 
            (0, 1, 0) if date.weekday() in WEEKEND else (1, 0, WORKHOURS)
        ) for date in daygenerator
    )

    # преобразование в список с результатами
    result_list = list(zip(*dayhours))

    # итоговый подсчет числа дней и часов
    return sum(result_list[0]), sum(result_list[1]), sum(result_list[2])

def workdays(fromdate, todate):
    return workdayholidayhours(fromdate, todate)[0]

def holidays(fromdate, todate):
    return workdayholidayhours(fromdate, todate)[1]

def workhours(fromdate, todate):
    return workdayholidayhours(fromdate, todate)[2]


# Объем работы в человекоднях при заданной продолжительности и проценте загрузки
def volume(workdays, load):
    return workdays * load / 100

# Формирование набора данных статистики производственного календаря 
def standards_report(year):
    # расчет диапазонов дат для каждого месяца и квартала
    m_ranges = ( (m[1], date(year, m[0], 1), date(year, m[0], 1) + monthdelta(1) - timedelta(days=1)) for m in MONTHS )
    q_ranges = ( (q[1], date(year, q[0], 1), date(year, q[0], 1) + monthdelta(3) - timedelta(days=1)) for q in QUARTES )
    y_range = ( ('Год', date(year, 1, 1), date(year+1, 1, 1) - timedelta(days=1)), )

    return (
        {
            'name': r[0],
            'stat': (days(r[1], r[2]), *workdayholidayhours(r[1], r[2]))
        } for r in it.chain(m_ranges, q_ranges, y_range)
    )
