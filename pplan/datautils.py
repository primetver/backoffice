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