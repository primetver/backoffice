from django.utils import timezone
from datetime import timedelta

def today():
    return timezone.now().date()

def tomorrow():
    return today() + timedelta(days=1)

# Число рабочих дней без учета праздников, список выходных задается третьим параметром (понедельник = 0)
def workdays(fromdate, todate, weekend=(5,6)):
    daygenerator = (fromdate + timedelta(x) for x in range((todate - fromdate).days + 1))
    return sum(1 for day in daygenerator if day.weekday() not in weekend)

# Объем работы в человекоднях при заданной продолжительности и проценте загрузки
def volume(workdays, load):
    return workdays * load / 100

def months():
    return (
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
    ) 