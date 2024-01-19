from django.db import models
from django.contrib.auth.models import User


class EndNode(models.Model):
    surveyor_org = models.ForeignKey(
        'SurveyorOrg',
        on_delete=models.CASCADE,
        default=1
    )
    name = models.CharField(max_length=50, null=True, unique=True)
    dev_eui = models.CharField(max_length=16, default='')
    influx_source = models.ForeignKey(
        'InfluxSource',
        on_delete=models.CASCADE,
        default=1
    )
    influx_measurement = models.CharField(max_length=30, null=True, default='nameofmeas')
    app_eui = models.CharField(max_length=20, blank=True, default='')
    app_key = models.CharField(max_length=40, blank=True, default='')
    frequency_plan = models.CharField(max_length=20, blank=True, default='')
    manufacturer = models.CharField(max_length=40, blank=True, default='')
    model = models.CharField(max_length=40, blank=True, default='')
    revision = models.CharField(max_length=10, blank=True, default='')
    gps_payload = models.BooleanField(default=False)

    def __str__(self):
        if self.name:
            return self.surveyor_org.name + ":" + self.name + "(" + self.dev_eui + ")"
        else:
            return self.surveyor_org.name + " : " + self.dev_eui

    class Meta:
        ordering = ('surveyor_org', 'name',)


class BucketDevice(models.Model):
    # create a new model for bucket device info.
    # associated with Influx Source
    influx_source = models.ForeignKey(
        'InfluxSource',
        on_delete=models.CASCADE,
        default=1
    )
    dev_eui = models.CharField(max_length=16)
    # last_join = models.DateTimeField()
    name = models.CharField(max_length=50, blank=True, default='')
    lat = models.FloatField()
    long = models.FloatField()
    marker = models.CharField(max_length=30, blank=True, default='')
    address = models.CharField(max_length=50, blank=True, default='')
    # estimated_rssi = models.IntegerField(blank=True,null=True)

    def __str__(self):
        if self.name:
            return self.influx_source.name + ":" + self.name + "(" + self.dev_eui + ")"
        else:
            return self.influx_source.name + " : " + self.dev_eui

    class Meta:
        ordering = ('influx_source', 'name',)


class SurveyorOrg(models.Model):
    name = models.CharField(max_length=20, null=False, unique=True)
    users = models.ManyToManyField(User)

    def __str__(self):
        if self.name:
            return self.name


class InfluxSource(models.Model):
    surveyor_org = models.ForeignKey(
        'SurveyorOrg',
        on_delete=models.CASCADE,
        default=1
    )
    name = models.CharField(max_length=30, null=False, unique=True)
    host = models.CharField(max_length=60, null=True)
    path = models.CharField(max_length=30, null=True)
    dbname = models.CharField(max_length=30, null=True)

    influx_org = models.CharField(max_length=30, null=False, blank=True, default='')
    influx_token = models.CharField(max_length=100, null=False, blank=True, default='')

    def __str__(self):
        if self.name:
            return self.name
