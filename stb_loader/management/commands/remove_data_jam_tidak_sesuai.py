from stb_loader.models import LoaderStatus
from django.db.models import F, Q
from django.db.models.functions import ExtractHour

data = LoaderStatus.objects.annotate(h=ExtractHour("timeStart")).filter(~Q(hour=F("h")))
data.delete()
