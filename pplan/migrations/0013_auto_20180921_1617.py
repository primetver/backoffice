# Generated by Django 2.1.1 on 2018-09-21 13:17

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pplan', '0012_auto_20180921_1611'),
    ]

    operations = [
        migrations.AlterField(
            model_name='position',
            name='position_name',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='pplan.PositionName', verbose_name='Должность'),
        ),
    ]