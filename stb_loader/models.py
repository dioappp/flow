from django.db import models
from django.forms import CharField


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
    location = models.ForeignKey(ClusterLoader, on_delete=models.SET_NULL, null=True)


class LoaderStatusHistory(models.Model):
    ACTION_CHOICES = (
        ("add", "Add"),
        ("update", "Update"),
        ("delete", "Delete"),
        ("addBatch", "AddBatch"),
    )

    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    loader_status_id = models.IntegerField()
    data = models.JSONField()  # Store the serialized data of LoaderStatus
    timestamp = models.DateTimeField(auto_now_add=True)
    token = models.CharField(max_length=20, null=False)

    def __str__(self):
        return (
            f"{self.get_action_display()} - {self.loader_status_id} at {self.timestamp}"
        )


class Standby(models.Model):
    id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=10)
    rank = models.SmallIntegerField()
    color = models.CharField(max_length=10)


class Reason(models.Model):
    reason = models.TextField()
    code = models.ForeignKey(Standby, on_delete=models.CASCADE)
