from django.shortcuts import render
from django.utils import timezone
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.forms.models import model_to_dict
from django.http import JsonResponse, HttpResponse
from ritase.models import ritase, cek_ritase
from hm.models import hmOperator, Operator
from django.db.models import Subquery, OuterRef, Q
from django.db.models.functions import Coalesce
from datetime import datetime, timedelta
from pytz import UTC
import pandas as pd
import math

# Create your views here.
material = {
    "Mud": "Mud",
    "GENS": "Sekatan",
    "GENK": "Kocoran",
    "GENFC": "Fine Coal",
    "PAAP": "PAAP",
    "GENMC": "Mud Cair",
}


def index(request):
    return render(request, "ritase/index.html")


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


def operator(request):
    date = request.POST.get("date")
    shift = request.POST.get("shift")
    hauler = request.POST.get("hauler").upper()

    ts, te = get_shift_time(date, shift)
    te = te - timedelta(minutes=15)

    data = (
        hmOperator.objects.filter(
            Q(equipment=hauler),
            Q(login_time__gte=ts, login_time__lt=te)
            | Q(logout_time__gt=ts, logout_time__lte=te),
        )
        .values("id", "NRP__operator", "NRP", "hm_start", "hm_end")
        .order_by("hm_start")
    )

    response = {"data": list(data)}
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

    try:
        data = cek_ritase.objects.get(
            deleted_at__isnull=True,
            date=date,
            shift=shift,
            operator_hauler_id=operator_id,
        )
        data = model_to_dict(data)
        data["action"] = createButton(data["id"])
        data_return = [data]

        response = {"draw": request.POST.get("draw"), "data": data_return}
        return JsonResponse(response)

    except MultipleObjectsReturned:
        data = cek_ritase.objects.filter(
            deleted_at__isnull=True,
            date=date,
            shift=shift,
            operator_hauler_id=operator_id,
        )
        data_return = []
        for d in data:
            x = model_to_dict(d)
            x["action"] = createButton(x["id"])
            data_return.append(x)

        response = {
            "draw": request.POST.get("draw"),
            "data": data_return,
        }
        return JsonResponse(response)

    except ObjectDoesNotExist:
        response = {
            "draw": request.POST.get("draw"),
            "data": [],
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
    unit = request.POST.get("unit")

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
