# Generated by Django 2.1.1 on 2018-09-28 09:12

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pplan', '0030_auto_20180927_1530'),
    ]

    operations = [
        migrations.CreateModel(
            name='MonthBooking',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('month', models.DateField(verbose_name='Месяц')),
                ('days', models.IntegerField(verbose_name='Участие, дней')),
                ('load', models.FloatField(default=0, verbose_name='Процент загрузки в месяце')),
                ('volume', models.FloatField(default=0, verbose_name='Объем, чел.дн.')),
                ('booking', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='pplan.Booking', verbose_name='Запись по загрузке')),
            ],
            options={
                'verbose_name': 'месячная загрузка',
                'verbose_name_plural': 'данные месячной загрузки',
                'ordering': (),
            },
        ),
    ]