# Generated by Django 2.1.1 on 2018-09-18 06:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pplan', '0002_auto_20180918_0914'),
    ]

    operations = [
        migrations.AlterField(
            model_name='role',
            name='descr',
            field=models.TextField(blank=True, verbose_name='Описание роли'),
        ),
    ]