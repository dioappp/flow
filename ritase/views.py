from django.shortcuts import render
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse, HttpResponse
from ritase.models import cek_ritase, truckID, material
from hm.models import hmOperator, Operator
from django.db.models import Q
from datetime import datetime, timedelta
from pytz import UTC
import math
from stb_hauler.models import HaulerStatus
from stb_loader.models import loaderID
import pandas as pd


# Create your views here.
def index(request):
    options = material.objects.values_list("code", flat=True)
    loaders = loaderID.objects.values_list("unit", flat=True).order_by("unit")
    return render(
        request, "ritase/index.html", {"options": options, "loaders": loaders}
    )


def index_loader(request):
    options = material.objects.values_list("code", flat=True)
    loaders = loaderID.objects.values_list("unit", flat=True).order_by("unit")
    return render(
        request, "ritase/index_loader.html", {"options": options, "loaders": loaders}
    )


def get_shift_time(date: str, shift: str) -> tuple[datetime, datetime]:
    if shift == "1":
        ts = date + " 06:30"
        te = date + " 18:00"
    else:
        ts = date + " 18:00"
        date_date = datetime.strptime(date, "%Y-%m-%d") + timedelta(days=1)
        date_str = datetime.strftime(date_date, "%Y-%m-%d")
        te = date_str + " 06:30"

    ts = UTC.localize(datetime.strptime(ts, "%Y-%m-%d %H:%M"))
    te = UTC.localize(datetime.strptime(te, "%Y-%m-%d %H:%M"))
    return ts, te


def get_cn_jigsaw(hauler_pattern: str) -> str:
    if not str(hauler_pattern).startswith("d"):
        obj = truckID.objects.get(code=hauler_pattern)
        hauler_jigsaw = obj.jigsaw
    else:
        hauler_jigsaw = str(hauler_pattern).upper()
    return hauler_jigsaw


def operator(request):
    date_pattern = request.POST.get("date")
    shift_pattern = request.POST.get("shift")
    hauler_pattern = request.POST.get("hauler")

    ts, te = get_shift_time(date_pattern, shift_pattern)
    ts = ts - timedelta(minutes=30)
    te = te - timedelta(hours=1)

    hauler_jigsaw = get_cn_jigsaw(hauler_pattern)

    data = (
        hmOperator.objects.filter(
            Q(equipment=hauler_jigsaw),
            Q(login_time__gte=ts, login_time__lt=te),
            # | Q(logout_time__gt=ts, logout_time__lte=te),
        )
        .values("id", "NRP__operator", "NRP", "hm_start", "hm_end")
        .order_by("hm_start")
    )

    response = {"data": list(data), "equipment": hauler_jigsaw}
    return JsonResponse(response)


def calculate_wh(request):
    date_pattern = request.POST.get("date")
    shift_pattern = request.POST.get("shift")
    hauler_pattern = str(request.POST.get("hauler")).upper()

    hauler_jigsaw = get_cn_jigsaw(hauler_pattern)

    wh = HaulerStatus.objects.filter(
        report_date=date_pattern,
        shift=shift_pattern,
        unit__jigsaw=hauler_jigsaw,
    ).values(
        "timeStart",
        "standby_code",
    )

    if not wh:
        response = {"error": f"tidak ada data WH untuk unit {hauler_jigsaw}"}
        return JsonResponse(response, status=405)

    df = pd.DataFrame(list(wh))
    df = df.sort_values("timeStart")
    df["timeStart"] = pd.to_datetime(df["timeStart"])

    s = 60 - df["timeStart"].max().second
    if shift_pattern == 2 and df["timeStart"].max().hour == 6:
        m = 29 - df["timeStart"].max().minute
    else:
        m = 59 - df["timeStart"].max().minute

    te = df["timeStart"].max() + pd.Timedelta(minutes=m, seconds=s)

    df["timeEnd"] = df["timeStart"].shift(-1)
    df["timeEnd"] = df["timeEnd"].fillna(te)

    df["durasi"] = df["timeEnd"] - df["timeStart"]
    df["durasi"] = pd.to_timedelta(df["durasi"]).dt.total_seconds() / 3600

    df = df.reset_index(drop=True)

    df = df.groupby(["standby_code"], as_index=False).agg(
        {
            "durasi": "sum",
        }
    )
    df = df.set_index("standby_code")
    stb = df.to_dict()
    response = {"data": stb}
    return JsonResponse(response)


def createButton(id):
    button = (
        '<button id="delete-'
        + str(id)
        + '" data-id="'
        + str(id)
        + '" class="btn btn-icon btn-danger avtar-xs mb-0" onclick="deleteRow(this)"><i class="ti ti-minus" style="color: #FFFFFF"></div>'
    )
    return button


def load_ritase(request):
    date = request.POST.get("date")
    shift = request.POST.get("shift")
    operator_id = request.POST.get("operator_id")

    cek_ritase_fields = [field.name for field in cek_ritase._meta.fields]
    cek_ritase_fields.append("code_material__remark")

    data = cek_ritase.objects.filter(
        deleted_at__isnull=True,
        date=date,
        shift=shift,
        operator_hauler_id=operator_id,
    ).values(*cek_ritase_fields)
    data_return = []
    for d in data:
        d["action"] = createButton(d["id"])
        data_return.append(d)

    response = {
        "draw": request.POST.get("draw"),
        "data": data_return,
    }
    return JsonResponse(response)


def load_ritase_loader(request):
    date = request.POST.get("date")
    shift = request.POST.get("shift")

    cek_ritase_fields = [field.name for field in cek_ritase._meta.fields]
    cek_ritase_fields.append("code_material__remark")

    maindata = (
        cek_ritase.objects.filter(
            deleted_at__isnull=True,
            date=date,
            shift=shift,
        )
        .values(*cek_ritase_fields)
        .order_by("loader", "hauler")
    )

    total = maindata.count()

    search_value = request.POST.get("search[value]")
    data = maindata.filter(
        Q(loader__icontains=search_value) | Q(hauler__icontains=search_value)
    )
    total_filtered = data.count()

    _start = request.POST.get("start")
    _length = request.POST.get("length")
    page = 1

    if _start and _length:
        start = int(_start)
        length = int(_length)
        page = math.ceil(start / length) + 1
    page_obj = data[start : start + length]

    data_return = []
    for d in page_obj:
        d["action"] = createButton(d["id"])
        data_return.append(d)

    response = {
        "draw": request.POST.get("draw"),
        "data": data_return,
        "page": int(page) if page else 1,
        "per_page": length,
        "recordsTotal": total,
        "recordsFiltered": total_filtered,
    }
    return JsonResponse(response)


def addrow(request):
    date = request.POST.get("date")
    shift = int(request.POST.get("shift"))
    hauler = request.POST.get("hauler").upper()
    operator_id = int(request.POST.get("id"))

    cek_ritase.objects.create(
        date=datetime.strptime(date, "%Y-%m-%d"),
        shift=shift,
        hauler=hauler,
        operator_hauler_id=operator_id,
        a=0,
        b=0,
        c=0,
        d=0,
        e=0,
        f=0,
        g=0,
        h=0,
        i=0,
        j=0,
        k=0,
        l=0,
        m=0,
    )
    return HttpResponse(status=204)


def update(request):
    id = request.POST.get("id")
    col = request.POST.get("fieldName")
    val = request.POST.get("value")
    cek_ritase.objects.filter(pk=id).update(**{col: val})

    if col == "material":
        remark = material.get(val, None)
        csr = cek_ritase.objects.get(pk=id)
        csr.remark = remark
        csr.save()

    response = {}
    return JsonResponse(response)


def update_operator(request):
    id = int(request.POST.get("ID"))
    hm_start = float(request.POST.get("HM Start"))
    hm_end = float(request.POST.get("HM End"))

    obj = hmOperator.objects.get(pk=id)
    obj.hm_start = hm_start
    obj.hm_end = hm_end
    obj.save()

    return HttpResponse(status=204)


def create_operator(request):
    shift = request.POST.get("shift")
    date = request.POST.get("date")
    nrp = int(request.POST.get("NRP"))
    hm_start = float(request.POST.get("HM Start"))
    hm_end = float(request.POST.get("HM End"))
    unit = str(request.POST.get("unit")).upper()

    unit = get_cn_jigsaw(unit)

    login, logout = get_shift_time(date, shift)
    try:
        nrp_instance = Operator.objects.get(NRP=nrp)
        hmOperator.objects.create(
            NRP=nrp_instance,
            hm_start=hm_start,
            hm_end=hm_end,
            equipment=unit,
            login_time=login,
            logout_time=logout,
        )

        return HttpResponse(status=204)
    except ObjectDoesNotExist:
        return HttpResponse("NRP Belum terdaftar di Database Procon")


def delete_row(request):
    id = request.POST.get("id")
    obj = cek_ritase.objects.get(pk=id)
    obj.deleted_at = timezone.now()
    obj.save()
    return HttpResponse(status=204)
