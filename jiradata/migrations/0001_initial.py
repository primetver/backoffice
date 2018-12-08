# Generated by Django 2.1.4 on 2018-12-07 14:44

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Worklog',
            fields=[
                ('id', models.DecimalField(decimal_places=0, max_digits=18, primary_key=True, serialize=False, verbose_name='ID')),
                ('issueid', models.DecimalField(decimal_places=0, max_digits=18, verbose_name='Issue ID')),
                ('author', models.CharField(max_length=255, verbose_name='Создал')),
                ('worklogbody', models.TextField(verbose_name='Содержание')),
                ('created', models.DateTimeField(verbose_name='Дата создания')),
                ('updateauthor', models.CharField(max_length=255, verbose_name='Обновил')),
                ('updated', models.DateTimeField(verbose_name='Дата обновления')),
                ('startdate', models.DateTimeField(verbose_name='Дата выполнения работ')),
                ('timeworked', models.DecimalField(decimal_places=0, max_digits=18, verbose_name='Затраченное время, c')),
            ],
            options={
                'verbose_name': 'запись о работе',
                'verbose_name_plural': 'записи о выполнении работ',
                'db_table': 'worklog',
                'abstract': False,
                'managed': False,
            },
        ),
    ]