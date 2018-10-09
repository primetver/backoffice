import sys

from django.db import models as md
from django.apps import apps
from django.utils.encoding import smart_text
from django.contrib.auth.management import _get_all_permissions
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

# proxy model missing permission workaround - modified for Django 2.0
def proxy_perm_create(**kwargs):
    for model in apps.get_models():
        opts = model._meta
        #print(opts.verbose_name_raw)
        ctype, created = ContentType.objects.get_or_create(
            app_label=opts.app_label,
            model=opts.object_name.lower())

        for code_tupel in _get_all_permissions(opts):
            codename = code_tupel[0]
            name = code_tupel[1]
            p, created = Permission.objects.get_or_create(
                codename=codename,
                content_type=ctype,
                defaults={'name': name})
            if created:
                sys.stdout.write('Adding permission {}\n'.format(p))


md.signals.post_migrate.connect(proxy_perm_create)