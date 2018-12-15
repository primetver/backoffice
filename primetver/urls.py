"""primetver URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

admin.AdminSite.site_header = 'Тверской филиал'
admin.AdminSite.site_url = None
admin.AdminSite.index_title = 'Главная страница' 

# Load proxy model permission creator
from .proxy_perm_create import proxy_perm_create

urlpatterns = [
    path('', admin.site.urls),
   # path('plan/', include('pplan.urls'))
]
