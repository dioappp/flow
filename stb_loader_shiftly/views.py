from django.shortcuts import render, redirect
from django.db.models import Count
from stb_loader.models import LoaderStatus
from ritase.models import ritase
from django.http import JsonResponse, HttpResponse
from django.core.management import call_command
from datetime import datetime, timedelta
import math
import pandas as pd


# Create your views here.
def index(request):
    loop_times = [f"{hour:02d}:00 - {(hour+1)%24:02d}:00" for hour in range(24)]
    stb = [
        "BS",
        "BUS",
        "S8",
        "S18",
        "S5A",
        "S5B",
        "S5C",
        "S6",
        "S1",
        "S2",
        "S10A",
        "S10B",
        "S15",
        "S19",
        "S12",
        "S13",
        "S14A",
        "S14B",
        "S14C",
        "S17",
        "S4",
        "S11",
        "S20C",
        "WH",
        "WH GEN",
    ]
    tipe_ritase = ["OB", "General", "Coal", "Top Soil", "IPD", "Mud", "Spoil"]
    return render(
        request,
        "stb_loader_shiftly/index.html",
        {"jam": loop_times, "stb": stb, "ritase": tipe_ritase},
    )


def reportDataSTB(request):
    date_pattern = request.POST.get("date")
    shift_pattern = int(request.POST.get("shift"))

    maindata = LoaderStatus.objects.filter(
        report_date=date_pattern, shift=shift_pattern
    )
    maindata = maindata.values("unit__unit").distinct().order_by("-unit__unit")

    total = maindata.count()
    data = maindata.filter(unit__unit__icontains=request.POST.get("search[value]"))
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
        x = {}
        x["unit"] = d["unit__unit"]
        x["action"] = (
            '<div id="data-'
            + str(d["unit__unit"])
            + '" data-id="'
            + str(d["unit__unit"])
            + '" class="d3-timeline"></div>'
        )
        data_return.append(x)

    response = {
        "draw": request.POST.get("draw"),
        "data": data_return,
        "page": int(page) if page else 1,
        "per_page": length,
        "recordsTotal": total,
        "recordsFiltered": total_filtered,
    }
    return JsonResponse(response)


def timeline(request):
    date_pattern = request.POST.get("date")
    shift_pattern = request.POST.get("shift")
    unit_pattern = request.POST.get("unit_id")
    show_hanging = request.POST.get("hanging") == "true"

    maindata = LoaderStatus.objects.filter(
        report_date=date_pattern, shift=shift_pattern, unit__unit=unit_pattern
    ).order_by("timeStart")
    maindata = maindata.values("id", "standby_code", "timeStart", "hour")
    response = {}
    response["state"] = []
    response["ritase"] = []

    hour_list = []
    for d in maindata.values("hour"):
        if d["hour"] not in hour_list:
            hour_list.append(d["hour"])

    for h in hour_list:
        data = maindata.filter(hour=h)
        for i, d in enumerate(data):
            x = {}
            x["database_id"] = d["id"]
            x["unit"] = unit_pattern
            x["timeStart"] = d["timeStart"].strftime("%Y-%m-%d %H:%M:%S")
            if not h == 6:
                x["timeEnd"] = (
                    (data[0]["timeStart"] + timedelta(hours=1)).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    if i == len(data) - 1
                    else data[i + 1]["timeStart"].strftime("%Y-%m-%d %H:%M:%S")
                )
            else:
                x["timeEnd"] = (
                    (data[0]["timeStart"] + timedelta(minutes=30)).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    if i == len(data) - 1
                    else data[i + 1]["timeStart"].strftime("%Y-%m-%d %H:%M:%S")
                )
            if not show_hanging:
                x["label"] = "WH" if d["standby_code"] == "S12" else d["standby_code"]
            else:
                x["label"] = d["standby_code"]
            response["state"].append(x)
    return JsonResponse(response, safe=False)
