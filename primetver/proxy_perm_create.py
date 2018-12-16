import sys

from django.db import models as md
from django.db import transaction
from django.apps import apps
from django.utils.encoding import smart_text
from django.contrib.auth.management import _get_all_permissions
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType


# proxy model missing permission workaround for Django 2.0
@transaction.atomic
def proxy_perm_create(**kwargs):
    for model in apps.get_models():
        opts = model._meta
        ctype, created = ContentType.objects.get_or_create(
            app_label=opts.app_label,
            model=opts.object_name.lower())
        if created:
                sys.stdout.write('Adding content type: {}\n'.format(ctype))

        for code_tupel in _get_all_permissions(opts):
            codename = code_tupel[0]
            name = code_tupel[1]
            p, created = Permission.objects.get_or_create(
                codename=codename,
                content_type=ctype,
                defaults={'name': name})
            if created:
                sys.stdout.write('Adding permission: {}\n'.format(p))

            # delete unused parent model permission for proxy model
            # NOTE: this must be done for every migration, see django ticket #11154
            if opts.proxy:
                for parent in model.__bases__:
                    popts = parent._meta
                    pperm = Permission.objects.filter(
                        codename=codename,
                        content_type__app_label=popts.app_label,
                        content_type__model=popts.object_name.lower())
                    if pperm.exists():
                        sys.stdout.write('Delete parent permission: {}\n'.format(pperm.first()))
                        pperm.delete()
            

# connect to post migrate signal
md.signals.post_migrate.connect(proxy_perm_create)