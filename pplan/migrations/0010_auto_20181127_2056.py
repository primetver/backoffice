# Generated by Django 2.1.1 on 2018-11-27 17:56

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('pplan', '0009_auto_20181127_1628'),
    ]

    operations = [
        migrations.DeleteModel(
            name='MonthBookingSelf',
        ),
        migrations.AlterModelOptions(
            name='monthbookingemployee',
            options={'verbose_name': 'загрузка по сотруднику', 'verbose_name_plural': 'отчет о загрузке по сотруднику'},
        ),
    ]
