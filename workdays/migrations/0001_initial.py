# Generated by Django 2.1.3 on 2018-12-25 14:11

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='HolidayName',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dayname', models.CharField(max_length=150, verbose_name='Название')),
                ('month', models.IntegerField(default=1, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(12)], verbose_name='Месяц')),
                ('day', models.IntegerField(default=1, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(31)], verbose_name='День')),
                ('count', models.IntegerField(default=1, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(10)], verbose_name='Число дней')),
            ],
            options={
                'verbose_name': 'наименование праздника',
                'verbose_name_plural': 'наименования праздников',
                'ordering': ('month', 'day'),
            },
        ),
        migrations.CreateModel(
            name='SpecialDay',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(db_index=True, unique=True, verbose_name='Дата')),
                ('daytype', models.CharField(choices=[('HL', 'Выходной день'), ('SH', 'Сокращенный день'), ('WK', 'Рабочий день')], default='HL', max_length=2, verbose_name='Тип дня')),
                ('comment', models.TextField(blank=True, null=True, verbose_name='Комментарий')),
                ('dayname', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='workdays.HolidayName', verbose_name='Название')),
            ],
            options={
                'verbose_name': 'нестандартный день календаря',
                'verbose_name_plural': 'нестандартные дни календаря',
                'ordering': ('date',),
            },
        ),
        migrations.CreateModel(
            name='WorktimeStandards',
            fields=[
            ],
            options={
                'verbose_name': 'норма рабочего времени',
                'verbose_name_plural': 'нормы рабочего времени',
                'proxy': True,
                'default_permissions': ('view',),
                'indexes': [],
            },
            bases=('workdays.specialday',),
        ),
    ]
