# Generated by Django 2.1.1 on 2018-09-24 15:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pplan', '0019_auto_20180924_1802'),
    ]

    operations = [
        migrations.AddField(
            model_name='staffingtable',
            name='count',
            field=models.IntegerField(default=1, verbose_name='Число позиций'),
        ),
    ]
