from django.db import models as md

# Create your models here.

class Server(md.Model):
    '''
    Сервер
    '''
    hostname = md.CharField('Имя сервера', max_length=60, unique=True)
    casemodel = md.CharField('Модель сервера', max_length=200, blank=True)
    cpumodel = md.CharField('Модель процессора', max_length=40, unique=True)
    architecture = md.CharField('Архитектура', max_length=20)
    cpucores = md.PositiveIntegerField('Число ядер')
    ram_gb = md.PositiveIntegerField('Память, ГБайт')
    disks = md.PositiveIntegerField('Число дисков')
    storage_gb = md.PositiveIntegerField('Дисковая память, Гбайт')
    ifaces = md.PositiveIntegerField('Число сетевых интерфейсов')

