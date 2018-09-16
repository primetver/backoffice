from django.contrib import admin
from .models import Employee, Salary, Project

# Register your models here.

admin.site.register(Employee)
admin.site.register(Salary)
admin.site.register(Project)
