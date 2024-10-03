from stb_loader.models import LoaderStatus
from django.db.models import Max, Count

uniq_f = ["date", "shift", "hour", "timeStart", "unit", "report_date"]

dups = (
    LoaderStatus.objects.values(*uniq_f)
    .order_by()
    .annotate(max_id=Max("id"), count_id=Count("id"))
    .filter(count_id__gt=1)
)

for dup in dups:
    LoaderStatus.objects.filter(**{x: dup[x] for x in uniq_f}).exclude(
        id=dup["max_id"]
    ).delete()
