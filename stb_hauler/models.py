from django.db import models
from ritase.models import truckID


# Create your models here.
class HaulerStatus(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True)

    date = models.DateField()
    hour = models.SmallIntegerField()
    shift = models.SmallIntegerField()
    timeStart = models.DateTimeField()
    unit = models.ForeignKey(truckID, on_delete=models.SET_NULL, null=True)
    standby_code = models.CharField(max_length=10)
    remarks = models.CharField(max_length=200, null=True)
    report_date = models.DateField()
