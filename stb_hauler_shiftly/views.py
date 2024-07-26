from django.shortcuts import render, redirect
from django.db.models import Count
from stb_hauler.models import HaulerStatus
from ritase.models import ritase
from django.http import JsonResponse, HttpResponse
from django.core.management import call_command
from datetime import timedelta, datetime
import math
import pandas as pd


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
        "WH general",
    ]
    tipe_ritase = ["OB", "General", "Coal", "Top Soil", "IPD", "Mud", "Spoil"]
    return render(
        request, "stb_hauler_shiftly/index.html", {"stb": stb, "ritase": tipe_ritase}
    )


def reportDataSTB(request):
    date_pattern = request.POST.get("date")
    shift_pattern = int(request.POST.get("shift"))

    maindata = HaulerStatus.objects.filter(
        report_date=date_pattern, shift=shift_pattern
    )
    maindata = maindata.values("unit__jigsaw").distinct().order_by("-unit__jigsaw")

    total = maindata.count()
    data = maindata.filter(unit__jigsaw__icontains=request.POST.get("search[value]"))
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


def timeline(request):
    date_pattern = request.POST.get("date")
    shift_pattern = request.POST.get("shift")
    unit_pattern = request.POST.get("unit_id")

    maindata = HaulerStatus.objects.filter(
        report_date=date_pattern, shift=shift_pattern, unit__jigsaw=unit_pattern
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

            x["label"] = d["standby_code"]
            response["state"].append(x)

    ritasedata = ritase.objects.filter(
        date=date_pattern, shift=shift_pattern, truck_id__jigsaw=unit_pattern
    ).order_by("time_full")
    ritasedata = ritasedata.values(
        "id",
        "time_full",
        "time_empty",
        "type",
        "loader_id__unit",
        "dump_location",
        "truck_id__OB_capacity",
    )

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


def update(request):
    ts = request.POST.get("timestart")
    id = int(request.POST.get("database_id"))
    stb_code = request.POST.get("stb")

    stb = HaulerStatus.objects.get(pk=id)

    ts = f"{stb.date} {ts}"
    ts = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")

    stb.standby_code = stb_code
    stb.timeStart = ts
    stb.save()
    return redirect(request.META.get("HTTP_REFERER"))


def add(request):
    id = int(request.POST.get("database_id"))
    stb = request.POST.get("stb")
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
    return redirect(request.META.get("HTTP_REFERER"))


def delete(request):
    id = int(request.POST.get("database_id_delete"))
    if "delete" in request.POST:
        HaulerStatus.objects.get(pk=id).delete()
    return redirect(request.META.get("HTTP_REFERER"))


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
    return redirect(request.META.get("HTTP_REFERER"))


def export_excel(request):
    date = request.POST.get("date")
    shift = int(request.POST.get("shift"))

    data = HaulerStatus.objects.filter(report_date=date, shift=shift).values(
        "report_date",
        "hour",
        "shift",
        "timeStart",
        "standby_code",
        "truck_id__jigsaw",
        "remarks",
        "date",
    )

    df = pd.DataFrame(list(data))
    df = df.rename(columns={"truck_id__jigsaw": "unit"})
    df = df.sort_values(by=["unit", "timeStart"])
    df["timeStart"] = pd.to_datetime(df["timeStart"])

    s = 60 - df["timeStart"].max().second
    if shift == 2 and df["timeStart"].max().hour == 6:
        m = 29 - df["timeStart"].max().minute
    else:
        m = 59 - df["timeStart"].max().minute

    te = df["timeStart"].max() + pd.Timedelta(minutes=m, seconds=s)

    df["timeEnd"] = df.groupby("unit")["timeStart"].shift(-1)
    df["timeEnd"] = df["timeEnd"].fillna(te)

    df["durasi"] = df["timeEnd"] - df["timeStart"]
    df["durasi"] = pd.to_timedelta(df["durasi"]).dt.total_seconds() / 60

    cond = ~df["hour"].isin([6, 11, 13]) & (df["standby_code"] == "S12")
    df.loc[cond, "standby_code"] = "WH"

    result = df.groupby(["hour", "unit", "standby_code"], as_index=False).agg(
        {
            "report_date": "first",
            "durasi": "sum",
            "remarks": "first",
            "date": "first",
        }
    )
    result["Project"] = "ADMO"

    result[["remarks", "BD Status", "statusBDC"]] = result["remarks"].str.split(
        ";", expand=True
    )
    result["Location"] = "NT/CT (not yet)"
    result["hour"] = result["hour"].apply(
        lambda x: (
            f"{x:02d}:00 - {(x+1):02d}:00"
            if ((0 <= x < 6) or (6 < x <= 23))
            else "06:30 - 07:00" if shift == 1 else "06:00 - 06:30"
        )
    )
    column_order = [
        "report_date",
        "Project",
        "Location",
        "unit",
        "date",
        "hour",
        "BD Status",
        "statusBDC",
        "standby_code",
        "durasi",
        "remarks",
    ]
    result = result.reindex(columns=column_order)
    result = result.sort_values(by=["unit", "date", "hour"])

    filename = f"standby-{date}-shift{shift}.xlsx"
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    result.to_excel(response, index=False)
    return response
