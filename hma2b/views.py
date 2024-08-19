from datetime import timedelta
import math
from django.http import JsonResponse
from django.shortcuts import render
from hm.models import hmOperator
from ritase.views import get_cn_jigsaw, get_shift_time
from django.db.models import Q


# Create your views here.
def index(request):
    return render(request, "hma2b/index.html")


def operator(request):
    date_pattern = request.POST.get("date")
    shift_pattern = request.POST.get("shift")

    ts, te = get_shift_time(date_pattern, shift_pattern)
    ts = ts - timedelta(minutes=30)
    te = te - timedelta(hours=1)

    maindata = (
        hmOperator.objects.filter(
            Q(equipment__startswith="X") | Q(equipment__startswith="G"),
            Q(login_time__gte=ts, login_time__lt=te),
            # | Q(logout_time__gt=ts, logout_time__lte=te),
        )
        .values(
            "id",
            "equipment",
            "NRP__operator",
            "NRP",
            "hm_start",
            "hm_end",
            "login_time",
            "logout_time",
        )
        .order_by("equipment", "hm_start")
    )

    total = maindata.count()
    data = maindata.filter(equipment__icontains=request.POST.get("search[value]"))
    total_filtered = data.count()
    _start = request.POST.get("start")
    _length = request.POST.get("length")
    page = 1

    if _start and _length:
        start = int(_start)
        length = int(_length)
        page = math.ceil(start / length) + 1
    page_obj = data[start : start + length]

    response = {
        "draw": request.POST.get("draw"),
        "data": list(page_obj),
        "page": int(page) if page else 1,
        "per_page": length,
        "recordsTotal": total,
        "recordsFiltered": total_filtered,
    }
    return JsonResponse(response)


def update(request):
    id = request.POST.get("id")
    col = request.POST.get("fieldName")
    val = request.POST.get("value")
    hmOperator.objects.filter(pk=id).update(**{col: val})

    response = {}
    return JsonResponse(response)
