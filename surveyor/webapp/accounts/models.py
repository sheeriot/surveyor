# from django.db import models
from django.contrib.auth.models import User
from device.models import EndNode


class Person(User):

    class Meta:
        proxy = True

    def __str__(self):
        return self.username

    def orgs(self):
        orgs = self.surveyororg_set.all()
        return orgs

    def orgs_list(self):
        loids = list(self.surveyororg_set.all().values_list('id', flat=True))
        return loids

    def endnodes(self):
        loids = list(self.surveyororg_set.all().values_list('id', flat=True))
        nodes = EndNode.objects.filter(surveyor_org__in=loids)
        return nodes
