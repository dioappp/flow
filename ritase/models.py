from django.db import models
from stb_loader.models import loaderID


# Create your models here.
class truckID(models.Model):
    jigsaw = models.CharField(max_length=20)
    ellipse = models.CharField(max_length=20, null=True)
    code = models.CharField(max_length=10, null=True)
    OB_capacity = models.IntegerField(null=True)

    def __str__(self):
        return self.jigsaw


class ritase(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True)

    date = models.DateField()
    shift = models.IntegerField()
    hour = models.IntegerField()
    load_id = models.IntegerField(null=True)
    time_full = models.DateTimeField()
    time_empty = models.DateTimeField(null=True)
    truck_id = models.ForeignKey(truckID, on_delete=models.SET_NULL, null=True)
    loader_id = models.ForeignKey(loaderID, on_delete=models.SET_NULL, null=True)
    material = models.CharField(max_length=20)
    blast = models.CharField(max_length=30, null=True)
    grade = models.CharField(max_length=30, null=True)
    dump_location = models.CharField(max_length=30, null=True)
    type = models.CharField(max_length=10, null=True)
    report_date = models.DateField(null=True)

    def __str__(self):
        return self.material


class cek_ritase(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True)

    date = models.DateField()
    shift = models.IntegerField()
    hauler = models.CharField(max_length=10)
    operator_hauler_id = models.BigIntegerField(null=True)
    loader = models.CharField(max_length=10)
    operator_loader_id = models.BigIntegerField(null=True)
    material = models.CharField(max_length=10)
    remark = models.CharField(max_length=10, null=True)
    a = models.SmallIntegerField()  # 06.30 - 07.00 | 18.00 - 19.00
    b = models.SmallIntegerField()  # 07.00 - 08.00 | 19.00 - 20.00
    c = models.SmallIntegerField()  # 08.00 - 09.00 | 20.00 - 21.00
    d = models.SmallIntegerField()  # 09.00 - 10.00 | 21.00 - 22.00
    e = models.SmallIntegerField()  # 10.00 - 11.00 | 22.00 - 23.00
    f = models.SmallIntegerField()  # 11.00 - 12.00 | 23.00 - 00.00
    g = models.SmallIntegerField()  # 12.00 - 13.00 | 00.00 - 01.00
    h = models.SmallIntegerField()  # 13.00 - 14.00 | 01.00 - 02.00
    i = models.SmallIntegerField()  # 14.00 - 15.00 | 02.00 - 03.00
    j = models.SmallIntegerField()  # 15.00 - 16.00 | 03.00 - 04.00
    k = models.SmallIntegerField()  # 16.00 - 17.00 | 04.00 - 05.00
    l = models.SmallIntegerField()  # 17.00 - 18.00 | 05.00 - 06.00
    m = models.SmallIntegerField()  #                06.00 - 06.30

    def __str__(self):
        return self.material
