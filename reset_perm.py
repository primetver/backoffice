from django.contrib.auth.models import Permission

# delete add permissions
for perm in Permission.objects.all():
    perm.delete()