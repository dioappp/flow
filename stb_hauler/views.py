import asyncio
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.core.management import call_command
from stb_hauler.models import HaulerStatus
from ritase.models import ritase
from datetime import timedelta, datetime
import math
from asgiref.sync import sync_to_async


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
        "stb_hauler/index.html",
        {"jam": loop_times, "stb": stb, "ritase": tipe_ritase},
    )


def reportDataSTB(request):
    date_pattern = request.POST.get("date")
    hour_pattern = request.POST.get("hour")

    maindata = (
        HaulerStatus.objects.filter(date=date_pattern, hour=hour_pattern)
        .values("unit__jigsaw")
        .distinct()
        .order_by("-unit__jigsaw")
    )

    maindata_list = list(maindata)
    total = len(maindata_list)
    search_val = request.POST.get("search[value]", "")
    data = [
        item
        for item in maindata_list
        if search_val.lower() in item["unit__jigsaw"].lower()
    ]
    total_filtered = len(data)
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
        x["unit"] = d["unit__jigsaw"]
        x["action"] = (
            '<div id="data-'
            + str(d["unit__jigsaw"])
            + '" data-id="'
            + str(d["unit__jigsaw"])
            + '" class="d3-timeline"></div>'
        )

        # ritase_sum = ritase.objects.filter(date=date_pattern, hour=hour_pattern, loader_id__unit=d['unit__unit']).aggregate(Sum('truck_id__OB_capacity'))
        # x['produksi'] = ritase_sum['truck_id__OB_capacity__sum'] if ritase_sum['truck_id__OB_capacity__sum'] is not None else 0
        x["produksi"] = None
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


@sync_to_async
def get_hauler_status(date_pattern, hour_pattern, unit_pattern):
    return list(
        HaulerStatus.objects.filter(
            date=date_pattern, hour=hour_pattern, unit__jigsaw=unit_pattern
        )
        .order_by("timeStart")
        .values("id", "standby_code", "timeStart")
    )


@sync_to_async
def get_ritase(date_pattern, hour_pattern, unit_pattern):
    return list(
        ritase.objects.filter(
            date=date_pattern, hour=hour_pattern, truck_id__jigsaw=unit_pattern
        )
        .order_by("time_full")
        .values(
            "id",
            "time_full",
            "time_empty",
            "type",
            "loader_id__unit",
            "dump_location",
            "truck_id__OB_capacity",
        )
    )


async def timeline(request):
    date_pattern = request.POST.get("date")
    hour_pattern = request.POST.get("hour")
    unit_pattern = request.POST.get("unit_id")

    maindata = await get_hauler_status(date_pattern, hour_pattern, unit_pattern)
    response = {}
    response["state"] = []
    response["ritase"] = []

    for i, d in enumerate(maindata):
        x = {}
        x["database_id"] = d["id"]
        x["unit"] = unit_pattern
        x["timeStart"] = d["timeStart"].strftime("%Y-%m-%d %H:%M:%S")
        x["timeEnd"] = (
            (maindata[0]["timeStart"] + timedelta(hours=1)).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            if i == len(maindata) - 1
            else maindata[i + 1]["timeStart"].strftime("%Y-%m-%d %H:%M:%S")
        )

        x["label"] = d["standby_code"]
        response["state"].append(x)

    ritasedata = await get_ritase(date_pattern, hour_pattern, unit_pattern)

    for d in ritasedata:
        x = {}
        x["database_id"] = d["id"]
        x["time_full"] = d["time_full"].strftime("%Y-%m-%d %H:%M:%S")
        x["time_empty"] = (
            d["time_empty"].strftime("%Y-%m-%d %H:%M:%S") if d["time_empty"] else "N/A"
        )
        x["type"] = d["type"]
        x["loader"] = d["loader_id__unit"]
        x["loc"] = d["dump_location"]
        response["ritase"].append(x)
    return JsonResponse(response, safe=False)


async def load_data(request):
    date = request.POST.get("date")
    hour = int(request.POST.get("hour"))

    date_str = f"{date} {hour:02d}:00"  # YYYY-MM-DD HH:MM

    def run_command():
        call_command("loadHauler", date=date_str)

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, run_command)
    return HttpResponse(status=204)


def update(request):
    ts = request.POST.get("timestart")
    id = int(request.POST.get("database_id"))
    stb_code = str(request.POST.get("stb")).upper()

    stb = HaulerStatus.objects.get(pk=id)

    ts = f"{stb.date} {ts}"
    ts = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")

    stb.standby_code = stb_code
    stb.timeStart = ts
    stb.save()
    return HttpResponse(status=204)


def add(request):
    id = int(request.POST.get("database_id"))
    stb = str(request.POST.get("stb")).upper()
    old = HaulerStatus.objects.get(pk=id)

    ts = request.POST.get("timestart")
    ts = f"{old.date} {ts}"
    ts = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")

    HaulerStatus.objects.create(
        standby_code=stb,
        timeStart=ts,
        unit=old.unit,
        hour=old.hour,
        date=old.date,
        shift=old.shift,
        remarks=old.remarks,
        report_date=old.report_date,
    )
    return HttpResponse(status=204)


def delete(request):
    id = int(request.POST.get("database_id_delete"))
    if "delete" in request.POST:
        HaulerStatus.objects.get(pk=id).delete()
    return HttpResponse(status=204)


def split(request):
    id = int(request.POST.get("database_id"))
    ts = request.POST.get("timestart")
    ts = datetime.strptime(ts, "%d/%m/%Y, %H:%M:%S")

    old = HaulerStatus.objects.get(pk=id)
    HaulerStatus.objects.create(
        standby_code=old.standby_code,
        timeStart=ts,
        unit=old.unit,
        hour=old.hour,
        date=old.date,
        shift=old.shift,
        remarks=old.remarks,
        report_date=old.report_date,
    )
    return HttpResponse(status=204)
