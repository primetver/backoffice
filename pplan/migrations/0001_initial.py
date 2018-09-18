# Generated by Django 2.1.1 on 2018-09-18 06:02

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Booking',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('month', models.DateField(verbose_name='Месяц загрузки')),
                ('load', models.FloatField(verbose_name='Коэффициент загрузки')),
                ('state', models.CharField(choices=[('DR', 'Черновик'), ('PL', 'Планируемое участие'), ('FA', 'Фактическое участие')], default='DR', max_length=2, verbose_name='Статус данных о загрузке')),
            ],
            options={
                'verbose_name': 'загрузка участника',
                'verbose_name_plural': 'загрузки участников',
                'ordering': ('project_member', 'month'),
            },
        ),
        migrations.CreateModel(
            name='Employee',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('last_name', models.CharField(db_index=True, max_length=200, verbose_name='Фамилия')),
                ('first_name', models.CharField(max_length=200, verbose_name='Имя')),
                ('sur_name', models.CharField(blank=True, max_length=200, verbose_name='Отчество')),
                ('hire_date', models.DateField(verbose_name='Дата приема на работу')),
                ('fire_date', models.DateField(blank=True, default=None, null=True, verbose_name='Дата увольнения')),
                ('is_fulltime', models.BooleanField(default=True, verbose_name='Работает полный день?')),
                ('business_k', models.FloatField(default=0.5, verbose_name='Коэффициент участия в бизнесе')),
            ],
            options={
                'verbose_name': 'сотрудник',
                'verbose_name_plural': 'сотрудники',
                'ordering': ('last_name', 'first_name'),
            },
        ),
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('business', models.CharField(max_length=20, verbose_name='Бизнес')),
                ('short_name', models.CharField(max_length=40, verbose_name='Сокращенное название')),
                ('full_name', models.TextField(verbose_name='Полное название')),
                ('start_date', models.DateField(verbose_name='Дата начала')),
                ('finish_date', models.DateField(blank=True, default=None, verbose_name='Дата окончания')),
                ('state', models.CharField(choices=[('IN', 'Проект планируется'), ('OP', 'Проект открыт'), ('CL', 'Проект в стадии закрытия'), ('CD', 'Проект закрыт')], default='IN', max_length=2, verbose_name='Статус проекта')),
                ('budget_state', models.CharField(choices=[('NO', 'Бюджет планируется'), ('PR', 'Бюджет согласуется'), ('AP', 'Бюджет утвержден')], default='NO', max_length=2, verbose_name='Состояние бюджета')),
            ],
            options={
                'verbose_name': 'проект',
                'verbose_name_plural': 'проекты',
                'ordering': ('start_date', 'short_name'),
                'get_latest_by': 'start_date',
            },
        ),
        migrations.CreateModel(
            name='ProjectMember',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_lead', models.BooleanField(default=False, verbose_name='Руководитель проекта?')),
                ('start_date', models.DateField(verbose_name='Дата включения в рабочую группу')),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='pplan.Employee', verbose_name='Участник')),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='pplan.Project', verbose_name='Проект')),
            ],
            options={
                'verbose_name': 'участник проекта',
                'verbose_name_plural': 'участника проекта',
                'ordering': ('project', 'employee'),
            },
        ),
        migrations.CreateModel(
            name='Role',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(max_length=40, unique=True, verbose_name='Роль')),
                ('descr', models.TextField(verbose_name='Описание роли')),
            ],
            options={
                'verbose_name': 'проектная роль',
                'verbose_name_plural': 'проектные роли',
            },
        ),
        migrations.CreateModel(
            name='Salary',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.IntegerField(verbose_name='Оклад')),
                ('start_date', models.DateField(verbose_name='Дата изменения')),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='pplan.Employee', verbose_name='Сотрудник')),
            ],
            options={
                'verbose_name': 'оклад',
                'verbose_name_plural': 'оклады',
                'ordering': ('-start_date', 'employee'),
                'get_latest_by': 'start_date',
            },
        ),
        migrations.AddField(
            model_name='projectmember',
            name='role',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='pplan.Role', verbose_name='Роль в проекте'),
        ),
        migrations.AlterUniqueTogether(
            name='project',
            unique_together={('business', 'short_name')},
        ),
        migrations.AddField(
            model_name='booking',
            name='project_member',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='pplan.ProjectMember'),
        ),
        migrations.AlterUniqueTogether(
            name='salary',
            unique_together={('employee', 'start_date')},
        ),
        migrations.AlterUniqueTogether(
            name='projectmember',
            unique_together={('project', 'employee')},
        ),
        migrations.AlterUniqueTogether(
            name='booking',
            unique_together={('project_member', 'month', 'state')},
        ),
    ]
