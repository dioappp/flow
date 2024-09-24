from datetime import time, timedelta
from stb_loader.models import LoaderStatus

data = LoaderStatus.objects.filter(timeStart__time__lt=time(6, 30), hour=6, shift=1)

for d in data:
    d.report_date -= timedelta(days=1)
    d.shift = 2
    d.save()

data = LoaderStatus.objects.filter(timeStart__time__gte=time(6, 30), hour=6, shift=2)

for d in data:
    try:
        d.report_date += timedelta(days=1)
        d.shift = 1
        d.save()
    except:
        d.delete()
