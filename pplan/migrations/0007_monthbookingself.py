# Generated by Django 2.1.1 on 2018-11-16 11:00

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('pplan', '0006_auto_20181116_1358'),
    ]

    operations = [
        migrations.CreateModel(
            name='MonthBookingSelf',
            fields=[
            ],
            options={
                'verbose_name': 'собственная загрузка',
                'verbose_name_plural': 'отчет о собственной загрузке',
                'proxy': True,
                'indexes': [],
            },
            bases=('pplan.monthbookingemployee',),
        ),
    ]
