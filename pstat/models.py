from django.db import models as md
from django_pandas.io import read_frame

from pplan.models import (Booking, Employee, MonthBooking, Project,
                          ProjectMember, Salary)

# Create your models here.


class MonthBookingSummary(MonthBooking):
    ''' 
    Прокси-модель для сводного отчета о загрузке сотрудников по месяцам
    '''
    class Meta():
        proxy = True
        verbose_name = 'загрузка по месяцам'
        verbose_name_plural = 'отчет о загрузке по месяцам'
        default_permissions = ('view',)

    class Manager(md.Manager):
        def get_queryset(self):
            return MonthBookingSummary.QuerySet(self.model, using=self._db)

    # замена менеджера по умолчанию
    objects = Manager()

    class QuerySet(md.QuerySet):
        '''
        Дополненный класс запроса для вывода загруженности по месяцам
        '''
        # Формирование набора данных по месяцам

        def get_booking(self, month_list):
            # чтение запроса в фрейм
            df = read_frame(
                self,
                fieldnames=[
                    'booking__project_member__employee',
                    'month',
                    'load',
                    'volume'
                ]
            )
            if df.empty:
                return []

            # агрегирование по сотрудникам и месяцам, получаем фрейм с иерархическим индексом
            month_booking = df.groupby(
                ['booking__project_member__employee', 'month']).sum()

            # результат - генератор последовательности словарей с полями:
            #   - сотрудник,
            #   - список помесячных записей о его загрузке для каждого месяца из переданного списка
            #     (отсутствующие данные заполняются нулями)
            return (
                {
                    'name': e,
                    # сбрасываем индекс по сотруднику, переиндексируем по списку месяцев, выводим в список словарей
                    'booking': booking.reset_index(level=0, drop=True).reindex(month_list, fill_value=0).to_dict('records')
                    # это замена примерно следующего кода:
                    # [
                    #    {
                    #        'load':booking.ix[e].load.get(month, 0),
                    #        'volume':booking.ix[e].volume.get(month, 0)
                    #    } for month in month_list
                    # ]
                } for e, booking in month_booking.groupby(level='booking__project_member__employee')
            )


class ProjectBooking(MonthBooking):
    ''' 
    Прокси-модель для отчета о загрузке сотрудников по проектам
    '''
    class Meta():
        proxy = True
        verbose_name = 'загрузка по проектам'
        verbose_name_plural = 'отчет о загрузке по проектам'
        default_permissions = ('view',)

    class Manager(md.Manager):
        def get_queryset(self):
            return ProjectBooking.QuerySet(self.model, using=self._db)

    # замена менеджера по умолчанию
    objects = Manager()

    class QuerySet(md.QuerySet):
        '''
        Дополненный класс запроса для вывода загруженности по проектам
        '''
        # Формирование набора данных по проектам с возможностью вывода данных по выплатам за указанный месяц

        def get_booking(self, projects, salary_month=None):
            # чтение запроса в фрейм
            df = read_frame(
                self,
                fieldnames=[
                    'booking__project_member__employee',
                    'booking__project_member__project__short_name',
                    'load',
                    'volume',
                ],
                index_col='booking__project_member__employee__id'
            )
            if df.empty:
                return []

            if salary_month:
                # чтение данных по з/п, выбор актуальных на заданный месяц
                sdf = read_frame(
                    # pylint: disable=no-member
                    Salary.objects.filter(start_date__lte=salary_month),
                    fieldnames=[
                        'employee__id',
                        'employee__business_k',
                        'amount'
                    ]
                ).groupby(['employee__id']).first()

                # обогащение набора данных и расчет оплаты в соответствии с загрузкой
                df = df.join(sdf)
                df['cost'] = df['load'] * df['amount'] * \
                    df['employee__business_k'] / 100

                # удаление ненужного столбца
                del df['amount'], df['employee__business_k']

            # агрегирование по сотрудникам и проектам, получаем фрейм с иерархическим индексом
            project_booking = df.groupby([
                'booking__project_member__employee',
                'booking__project_member__project__short_name']).sum()

            # результат - генератор последовательности словарей с полями:
            #   - сотрудник,
            #   - список записей о его загрузке для каждого проекта из переданного списка
            #     (отсутствующие данные заполняются нулями),
            #   - запись о суммарной загрузке
            return (
                {
                    'name': e,
                    # сбрасываем индекс по сотруднику,
                    # переиндексируем по списку проектов, выводим в список словарей
                    'booking': booking.reset_index(level=0, drop=True).reindex(projects, fill_value=0).to_dict('records'),
                    'total': booking.sum().to_dict()
                } for e, booking in project_booking.groupby(level='booking__project_member__employee')
            )


class MonthBookingEmployee(MonthBooking):
    ''' 
    Прокси-модель для отчета о загрузке выбранного сотрудника
    '''
    class Meta():
        proxy = True
        verbose_name = 'загрузка по сотруднику'
        verbose_name_plural = 'отчет о загрузке по сотруднику'
        default_permissions = ('view',)
        permissions = (
            ("view_all", "Просмотр любого сотрудника"),
        )

    class Manager(md.Manager):
        def get_queryset(self):
            return MonthBookingEmployee.QuerySet(self.model, using=self._db)

    # замена менеджера по умолчанию
    objects = Manager()

    class QuerySet(md.QuerySet):
        '''
        Дополненный класс запроса для вывода загруженности по сотруднику
        '''
        # Формирование набора данных по сотруднику

        def get_booking(self, month_list, employee_id):
            # фильтрация запроса
            qs = self.filter(
                month__range=(month_list[0], month_list[-1]),
                booking__project_member__employee__id=employee_id
            )

            # чтение запроса в фрейм
            df = read_frame(
                qs,
                fieldnames=[
                    'booking__project_member__project__short_name',
                    'month',
                    'load',
                    'volume',
                ],
            )
            if df.empty:
                return [], None

            # агрегирование по проектам и месяцам, получаем фрейм с иерархическим индексом: проект, месяц
            month_booking = df.groupby(
                ['booking__project_member__project__short_name', 'month']).sum()

            # результат -- кортеж:
            # 1) генератор последовательности словарей с полями:
            #   - проект,
            #   - список помесячных записей о загрузке для каждого месяца из переданного списка
            #     (отсутствующие данные заполняются нулями)
            # 2) итоговая строка
            return (
                (
                    {
                        'project': p,
                        # сбрасываем индекс по проектам, переиндексируем по списку месяцев, выводим в список словарей
                        'booking': booking.reset_index(level=0, drop=True).reindex(month_list, fill_value=0).to_dict('records')
                    } for p, booking in month_booking.groupby(level='booking__project_member__project__short_name')
                ),
                {
                    # дополнительная итоговая строка
                    'booking': month_booking.groupby('month').sum().reindex(month_list, fill_value=0).to_dict('records')
                }
            )
