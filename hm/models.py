from django.db import models


# Create your models here.
class hmOperator(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True)

    equipment = models.CharField(max_length=10)
    operator = models.CharField(max_length=40)
    NRP = models.IntegerField()
    login_time = models.DateTimeField()
    logout_time = models.DateTimeField(null=True)
    hm_start = models.FloatField(null=True)
    hm_end = models.FloatField(null=True)
