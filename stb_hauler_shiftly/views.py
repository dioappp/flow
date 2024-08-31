from django.shortcuts import render
from stb_hauler.models import HaulerStatus
from ritase.models import ritase
from django.http import JsonResponse
from datetime import timedelta
from asgiref.sync import sync_to_async
import math


# Create your views here.
def index(request):

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
        request, "stb_hauler_shiftly/index.html", {"stb": stb, "ritase": tipe_ritase}
    )


def reportDataSTB(request):
    date_pattern = request.POST.get("date")
    shift_pattern = int(request.POST.get("shift"))

    maindata = (
        HaulerStatus.objects.filter(report_date=date_pattern, shift=shift_pattern)
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
def get_hauler_status(date_pattern, shift_pattern, unit_pattern):
    return list(
        HaulerStatus.objects.filter(
            report_date=date_pattern, shift=shift_pattern, unit__jigsaw=unit_pattern
        )
        .order_by("timeStart")
        .values("id", "standby_code", "timeStart", "hour")
    )


@sync_to_async
def get_ritase(date_pattern, shift_pattern, unit_pattern):
    return list(
        ritase.objects.filter(
            report_date=date_pattern, shift=shift_pattern, truck_id__jigsaw=unit_pattern
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
    shift_pattern = request.POST.get("shift")
    unit_pattern = request.POST.get("unit_id")

    maindata = await get_hauler_status(date_pattern, shift_pattern, unit_pattern)
    response = {}
    response["state"] = []
    response["ritase"] = []

    hour_list = []
    for d in maindata:
        if d["hour"] not in hour_list:
            hour_list.append(d["hour"])

    for h in hour_list:
        data = [d for d in maindata if d.get("hour") == h]
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

            x["label"] = d["standby_code"]
            response["state"].append(x)

    ritasedata = await get_ritase(date_pattern, shift_pattern, unit_pattern)

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
