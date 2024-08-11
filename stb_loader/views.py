from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.core.management import call_command
from django.db.models import Sum, Subquery, OuterRef, Q
from stb_loader.models import LoaderStatus, ClusterLoader, LoaderStatusHistory
from ritase.models import ritase
from datetime import datetime, timedelta
import math
import pandas as pd
from django.db.models.functions import Coalesce
import json
from django.core import serializers


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


def is_nempel_ke_jam_kritis(stb: str, prev: str, next: str) -> bool:
    jam_kritis = ["S6", "S5A", "S8"]
    return stb == "S12" and (prev in jam_kritis or next in jam_kritis)


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
        # Check the previous and next records if they exist
        prev_code = maindata[i - 1]["standby_code"] if i > 0 else None
        next_code = maindata[i + 1]["standby_code"] if i < len(maindata) - 1 else None

        hanging_jam_kritis = is_nempel_ke_jam_kritis(
            d["standby_code"], prev_code, next_code
        )

        if show_hanging or hanging_jam_kritis or d["standby_code"] != "S12":
            x["label"] = d["standby_code"]
            response["state"].append(x)
            continue

        # If neither the previous nor the next code is S6, change S12 to WH
        x["label"] = "WH"
        response["state"].append(x)
        continue

    ritasedata = ritase.objects.filter(
        date=date_pattern, hour=hour_pattern, loader_id__unit=unit_pattern
    ).order_by("time_full")
    ritasedata = ritasedata.values(
        "id",
        "time_full",
        "time_empty",
        "type",
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
        x["type"] = d["type"]
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

    # Save the current state before updating
    LoaderStatusHistory.objects.create(
        action="update",
        loader_status_id=id,
        data=serializers.serialize("json", [stb]),
        token=request.COOKIES.get("csrftoken"),
    )

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

    new_instance = LoaderStatus.objects.create(
        standby_code=stb,
        timeStart=ts,
        unit=old.unit,
        hour=old.hour,
        date=old.date,
        shift=old.shift,
        remarks=old.remarks,
        report_date=old.report_date,
    )

    # Save the new instance's state
    LoaderStatusHistory.objects.create(
        action="add",
        loader_status_id=new_instance.id,
        data=serializers.serialize("json", [new_instance]),
        token=request.COOKIES.get("csrftoken"),
    )

    if old.hour == 6:
        t = f"{old.date} 06:30:00"
        t = datetime.strptime(t, "%Y-%m-%d %H:%M:%S")
        try:
            LoaderStatus.objects.get(
                timeStart=t,
                unit=old.unit,
                date=old.date,
            )
        except LoaderStatus.DoesNotExist:
            new_instance_630 = LoaderStatus.objects.create(
                standby_code=stb,
                timeStart=t,
                unit=old.unit,
                hour=old.hour,
                date=old.date,
                shift=1,
                remarks=old.remarks,
                report_date=old.date,
            )
            # Save the new instance's state
            LoaderStatusHistory.objects.create(
                action="add",
                loader_status_id=new_instance_630.id,
                data=serializers.serialize("json", [new_instance_630]),
                token=request.COOKIES.get("csrftoken"),
            )
    return redirect(request.META.get("HTTP_REFERER"))


def delete(request):
    id = int(request.POST.get("database_id_delete"))
    if "delete" in request.POST:
        stb = LoaderStatus.objects.get(pk=id)

        # Save the current state before deleting
        LoaderStatusHistory.objects.create(
            action="delete",
            loader_status_id=id,
            data=serializers.serialize("json", [stb]),
            token=request.COOKIES.get("csrftoken"),
        )
        stb.delete()
    return redirect(request.META.get("HTTP_REFERER"))


def split(request):
    id = int(request.POST.get("database_id"))
    ts = request.POST.get("timestart")
    ts = datetime.strptime(ts, "%d/%m/%Y, %H:%M:%S")

    old = LoaderStatus.objects.get(pk=id)

    # Save the state of the old instance before the split
    LoaderStatusHistory.objects.create(
        action="split",
        loader_status_id=id,
        data=serializers.serialize("json", [old]),
        token=request.COOKIES.get("csrftoken"),
    )
    new_instance = LoaderStatus.objects.create(
        standby_code=old.standby_code,
        timeStart=ts,
        unit=old.unit,
        hour=old.hour,
        date=old.date,
        shift=old.shift,
        remarks=old.remarks,
        report_date=old.report_date,
    )
    # Save the state of the new instance after the split
    LoaderStatusHistory.objects.create(
        action="add",
        loader_status_id=new_instance.id,
        data=serializers.serialize("json", [new_instance]),
        token=request.COOKIES.get("csrftoken"),
    )
    return redirect(request.META.get("HTTP_REFERER"))


def undo(request):
    last_action = LoaderStatusHistory.objects.filter(
        token=request.COOKIES.get("csrftoken")
    ).last()

    if not last_action:
        return redirect(request.META.get("HTTP_REFERER"))

    if last_action.action == "update":
        # Revert to previous state
        obj = list(serializers.deserialize("json", last_action.data))[0]
        obj.save()

    elif last_action.action == "add":
        # Delete the last added object
        LoaderStatus.objects.get(pk=last_action.loader_status_id).delete()

    elif last_action.action == "delete":
        # Restore the deleted object
        obj = list(serializers.deserialize("json", last_action.data))[0]
        obj.save()

    elif last_action.action == "split":
        # Revert the split by deleting the new instance and restoring the old one
        added_action = LoaderStatusHistory.objects.filter(
            action="add", loader_status_id=last_action.loader_status_id
        ).last()
        if added_action:
            LoaderStatus.objects.get(pk=added_action.loader_status_id).delete()
            added_action.delete()
        obj = list(serializers.deserialize("json", last_action.data))[0]
        obj.save()

    # Remove the last action from history
    last_action.delete()

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
