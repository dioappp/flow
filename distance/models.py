from django.db import models
from stb_loader.models import loaderID


# Create your models here.
class distance(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True)

    date = models.DateField()
    loader = models.ForeignKey(loaderID, on_delete=models.SET_NULL, null=True)
    blok_loading = models.FloatField()
    elevasi_loading = models.IntegerField()
    lokasi_dumping = models.CharField(max_length=20)
    elevasi_dumping = models.FloatField()
    horizontal_distance = models.FloatField()
    lokasi = models.CharField(max_length=10)
    vertical_distance = models.FloatField()
