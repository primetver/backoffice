# Generated by Django 2.1.1 on 2018-09-24 14:42

from django.db import migrations, models
import django.db.models.deletion
import pplan.models


class Migration(migrations.Migration):

    dependencies = [
        ('pplan', '0017_auto_20180924_1707'),
    ]

    operations = [
        migrations.AlterField(
            model_name='employee',
            name='position',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='pplan.Position', verbose_name='Должность'),
        ),
    ]
