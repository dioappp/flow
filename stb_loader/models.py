from django.db import models


# Create your models here.
class loaderID(models.Model):
    unit = models.CharField(max_length=20)
    ellipse = models.CharField(max_length=20, null=True)

    def __str__(self):
        return self.unit


class RestTime(models.Model):
    time_start = models.TimeField()
    time_end = models.TimeField()
    standby_code = models.CharField(max_length=10)


class LoaderStatus(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True)

    date = models.DateField()
    hour = models.SmallIntegerField()
    shift = models.SmallIntegerField()
    timeStart = models.DateTimeField()
    unit = models.ForeignKey(loaderID, on_delete=models.SET_NULL, null=True)
    standby_code = models.CharField(max_length=10)
    remarks = models.CharField(max_length=200, null=True)
    report_date = models.DateField()


class ClusterLoader(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True)

    date = models.DateField()
    hour = models.IntegerField()
    unit = models.ForeignKey(loaderID, on_delete=models.CASCADE)
    cluster = models.CharField(max_length=20, null=True)
    pit = models.CharField(max_length=10, null=True)
