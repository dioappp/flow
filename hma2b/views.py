from datetime import timedelta
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
    cn_pattern = request.POST.get("cn")
    eqtype = request.POST.get("eqtype")

    ts, te = get_shift_time(date_pattern, shift_pattern)
    ts = ts - timedelta(minutes=30)

    data = (
        hmOperator.objects.filter(
            # Q(equipment=hauler_jigsaw),
            Q(login_time__gte=ts, login_time__lt=te),
            # | Q(logout_time__gt=ts, logout_time__lte=te),
        )
        .values("id", "NRP__operator", "NRP", "hm_start", "hm_end")
        .order_by("hm_start")
    )

    response = {"data": list(data)}
    return JsonResponse(response)
