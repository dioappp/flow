from django.db import models


# Create your models here.
class Operator(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True)

    NRP = models.IntegerField(primary_key=True)
    operator = models.CharField(max_length=40)


class hmOperator(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True)

    equipment = models.CharField(max_length=10)
    NRP = models.ForeignKey(Operator, on_delete=models.CASCADE)
    login_time = models.DateTimeField()
    logout_time = models.DateTimeField(null=True)
    hm_start = models.FloatField(null=True)
    hm_end = models.FloatField(null=True)
