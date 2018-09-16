# Generated by Django 2.1.1 on 2018-09-16 15:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pplan', '0007_auto_20180915_1954'),
    ]

    operations = [
        migrations.CreateModel(
            name='Role',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
        ),
        migrations.CreateModel(
            name='Workgroup',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
        ),
        migrations.AlterModelOptions(
            name='salary',
            options={'get_latest_by': 'start_date', 'ordering': ('-start_date', 'employee'), 'verbose_name': 'оклад', 'verbose_name_plural': 'оклады'},
        ),
    ]
