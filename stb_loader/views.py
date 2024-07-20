from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.core.management import call_command
from django.db.models import Sum, Subquery, OuterRef, Q
from stb_loader.models import LoaderStatus, ClusterLoader
from ritase.models import ritase
from datetime import datetime, timedelta
import math
import pandas as pd
from django.db.models.functions import Coalesce
import json


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
        "WH general",
    ]
    tipe_ritase = ["OB", "General", "Coal", "Top Soil", "IPD", "Mud", "Spoil"]
    pits = list(
        ClusterLoader.objects.exclude(pit=None).values_list("pit", flat=True).distinct()
    )
    clusters = []
    for pit in pits:
        cluster = list(
            ClusterLoader.objects.exclude(cluster=None)
            .filter(pit=pit)
            .values_list("cluster", flat=True)
            .distinct()
        )
        clusters.append(cluster)
    pit_cluster = [
        (pit.capitalize(), [cluster.capitalize() for cluster in cluster_list])
        for pit, cluster_list in zip(pits, clusters)
    ]
    return render(
        request,
        "stb_loader/index.html",
        {
            "jam": loop_times,
            "stb": stb,
            "ritase": tipe_ritase,
            "pit_cluster": pit_cluster,
        },
    )


def reportDataSTB(request):
    date_pattern = request.POST.get("date")
    hour_pattern = request.POST.get("hour")
    cluster = json.loads(request.POST.get("cluster"))
    cluster = [item.upper() for item in cluster]

    subquery_loader = ClusterLoader.objects.filter(
        unit=OuterRef("unit"), date=OuterRef("date"), hour=OuterRef("hour")
    )

    maindata = (
        LoaderStatus.objects.filter(date=date_pattern, hour=hour_pattern)
        .annotate(
            cluster=Coalesce(Subquery(subquery_loader.values("cluster")[:1]), None),
            pit=Coalesce(Subquery(subquery_loader.values("pit")[:1]), None),
        )
        .values("unit__unit", "pit", "cluster")
        .order_by("-pit", "cluster", "-unit__unit")
    )
    if not cluster:
        maindata = maindata.values("unit__unit").distinct()
    else:
        maindata = maindata.filter(cluster__in=cluster).values("unit__unit").distinct()

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

        ritase_sum = ritase.objects.filter(
            date=date_pattern, hour=hour_pattern, loader_id__unit=d["unit__unit"]
        ).aggregate(Sum("truck_id__OB_capacity"))
        x["produksi"] = (
            ritase_sum["truck_id__OB_capacity__sum"]
            if ritase_sum["truck_id__OB_capacity__sum"] is not None
            else 0
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
    hour_pattern = request.POST.get("hour")
    unit_pattern = request.POST.get("unit_id")
    show_hanging = request.POST.get("hanging") == "true"

    maindata = LoaderStatus.objects.filter(
        date=date_pattern, hour=hour_pattern, unit__unit=unit_pattern
    ).order_by("timeStart")
    maindata = maindata.values("id", "standby_code", "timeStart")
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
        if not show_hanging:
            x["label"] = "WH" if d["standby_code"] == "S12" else d["standby_code"]
        else:
            x["label"] = d["standby_code"]
        response["state"].append(x)

    ritasedata = ritase.objects.filter(
        date=date_pattern, hour=hour_pattern, loader_id__unit=unit_pattern
    ).order_by("time_full")
    ritasedata = ritasedata.values(
        "id",
        "time_full",
        "time_empty",
        "type__material",
        "truck_id__jigsaw",
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
        x["type"] = d["type__material"]
        x["hauler"] = d["truck_id__jigsaw"]
        x["loc"] = d["dump_location"]
        response["ritase"].append(x)

    return JsonResponse(response, safe=False)


def load_data(request):
    date = request.POST.get("date")
    hour = int(request.POST.get("hour"))

    date_str = f"{date} {hour:02d}:00"  # YYYY-MM-DD HH:MM

    call_command("ritase", date=date_str)
    call_command("loadLoader", date=date_str)
    call_command("loadHauler", date=date_str)
    return redirect(request.META.get("HTTP_REFERER"))


def update(request):
    ts = request.POST.get("timestart")
    id = int(request.POST.get("database_id"))
    stb_code = request.POST.get("stb")

    stb = LoaderStatus.objects.get(pk=id)

    ts = f"{stb.date} {ts}"
    ts = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")

    stb.standby_code = stb_code
    stb.timeStart = ts
    stb.save()
    return redirect(request.META.get("HTTP_REFERER"))


def add(request):
    id = int(request.POST.get("database_id"))
    stb = request.POST.get("stb")
    old = LoaderStatus.objects.get(pk=id)

    ts = request.POST.get("timestart")
    ts = f"{old.date} {ts}"
    ts = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")

    LoaderStatus.objects.create(
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
        LoaderStatus.objects.get(pk=id).delete()
    return redirect(request.META.get("HTTP_REFERER"))


def split(request):
    id = int(request.POST.get("database_id"))
    ts = request.POST.get("timestart")
    ts = datetime.strptime(ts, "%d/%m/%Y, %H:%M:%S")

    old = LoaderStatus.objects.get(pk=id)
    LoaderStatus.objects.create(
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

    subquery = ClusterLoader.objects.filter(
        date=OuterRef("date"), hour=OuterRef("hour"), unit=OuterRef("unit")
    )
    data = (
        LoaderStatus.objects.filter(report_date=date, shift=shift)
        .annotate(
            pit=Coalesce(Subquery(subquery.values("pit")[:1]), None),
        )
        .values(
            "report_date",
            "hour",
            "shift",
            "timeStart",
            "standby_code",
            "unit__unit",
            "remarks",
            "date",
            "pit",
        )
    )

    df = pd.DataFrame(list(data))
    df = df.rename(columns={"unit__unit": "unit"})
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
            "pit": "first",
        }
    )
    result["Project"] = "ADMO"

    result[["remarks", "BD Status", "statusBDC"]] = result["remarks"].str.split(
        ";", expand=True
    )
    result.rename(columns={"pit": "Location"}, inplace=True)
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
