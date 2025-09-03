from django.contrib.auth.models import Group

def _rol(user):
    return next(iter(Group.objects.filter(user=user).values_list("name", flat=True)), None)