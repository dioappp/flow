import asyncio
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.core.management import call_command
from django.db.models import F, Max
from exporter.views import is_in_jam_kritis
from stb_loader.models import LoaderStatus, LoaderStatusHistory, loaderID
from ritase.models import ritase
from datetime import datetime, timedelta, time
import math
import json
from django.core import serializers
from asgiref.sync import sync_to_async
from ritase.models import ritase
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
        "stb_loader/index.html",
        {
            "jam": loop_times,
            "stb": stb,
            "ritase": tipe_ritase,
        },
    )


def data_child(request):
    date = request.POST.get("date")
    hour = int(request.POST.get("hour"))
    unit = request.POST.get("unit")

    if hour in list(range(7, 18)):
        shift = 1
    else:
        shift = 2

    loader = loaderID.objects.get(unit=unit)
    maindata = (
        ritase.objects.filter(date=date, hour=hour, loader_id=loader)
        .annotate(hauler=F("truck_id__jigsaw"))
        .values("hauler")
        .distinct()
        .order_by("-hauler")
    )

    if not maindata:
        maindata = (
            ritase.objects.filter(date=date, shift=shift, loader_id=loader)
            .annotate(hauler=F("truck_id__jigsaw"))
            .values("hauler")
            .distinct()
            .order_by("-hauler")
        )

    data_return = []
    for d in maindata:
        x = {}
        x["hauler"] = d["hauler"]
        data_return.append(x)

    response = {"data": data_return}
    return JsonResponse(response)


def reportDataSTB(request):
    date_pattern = request.POST.get("date")
    hour_pattern = request.POST.get("hour")

    maindata = (
        LoaderStatus.objects.filter(date=date_pattern, hour=hour_pattern)
        .values("unit__unit")
        .annotate(pit=Max("location__pit"), cluster=Max("location__cluster"))
        .distinct()
        .order_by("-pit", "cluster", "-unit__unit")
    )

    maindata_list = list(maindata)
    total = len(maindata_list)
    search_val = request.POST.get("search[value]", "")
    data = [
        item
        for item in maindata_list
        if search_val.lower() in item["unit__unit"].lower()
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
        x["unit"] = d["unit__unit"]
        x["cluster"] = f"{d['cluster']}, {d['pit']}"
        x["action"] = (
            '<div id="data-'
            + str(d["unit__unit"])
            + '" data-id="'
            + str(d["unit__unit"])
            + '" class="d3-timeline"></div>'
        )

        # ritase_sum = ritase.objects.filter(
        #     date=date_pattern, hour=hour_pattern, loader_id__unit=d["unit__unit"]
        # ).aggregate(Sum("truck_id__OB_capacity"))
        # x["produksi"] = (
        #     ritase_sum["truck_id__OB_capacity__sum"]
        #     if ritase_sum["truck_id__OB_capacity__sum"] is not None
        #     else 0
        # )
        x["produksi"] = 0
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
    jam_kritis = ["S6", "S5A", "S8", "S15"]
    return stb == "S12" and (prev in jam_kritis or next in jam_kritis)


@sync_to_async
def get_loader_status(date_pattern, hour_pattern, unit_pattern):
    return list(
        LoaderStatus.objects.filter(
            date=date_pattern, hour=hour_pattern, unit__unit=unit_pattern
        )
        .order_by("timeStart")
        .values("id", "standby_code", "timeStart")
    )


@sync_to_async
def get_ritase(date_pattern, hour_pattern, unit_pattern):
    return list(
        ritase.objects.filter(
            date=date_pattern, hour=hour_pattern, loader_id__unit=unit_pattern
        )
        .order_by("time_full")
        .values(
            "id",
            "time_full",
            "time_empty",
            "type",
            "truck_id__jigsaw",
            "dump_location",
            "truck_id__OB_capacity",
        )
    )


def get_wh_proses(maindata: list, ritdata: list, unit_pattern: str) -> dict:
    df = pd.DataFrame(maindata)
    df = df.sort_values(["timeStart"]).reset_index(drop=True)
    df["equipment"] = unit_pattern
    ids = df.index[df.standby_code == "S12"].tolist()

    for id in ids:
        if not is_in_jam_kritis(id, df):
            df.loc[id, "standby_code"] = "WH"

    df["group"] = (df["standby_code"] != df["standby_code"].shift()).cumsum()
    df = df.groupby(["group"], as_index=False).first()
    df = df.drop(columns="group")

    if ritdata:
        rdf = pd.DataFrame(ritdata)
        rdf = rdf.sort_values(["time_full"]).reset_index(drop=True)
        rdf["group"] = (rdf["type"] != rdf["type"].shift()).cumsum()
        rdf = rdf.groupby(["group"], as_index=False).last()
        rdf = rdf.drop(columns="group")

        counter = len(rdf)

        df.loc[(df["standby_code"] == "WH"), "standby_code"] = f"WH {rdf.loc[0,'type']}"

        if counter != 1:
            x = []
            x = rdf
            x = x.rename(columns={"time_full": "timeStart", "type": "standby_code"})
            x["standby_code"] = x["standby_code"].apply(lambda x: f"WH {x}")
            x.drop(
                columns=[
                    "time_empty",
                    "truck_id__jigsaw",
                    "dump_location",
                    "truck_id__OB_capacity",
                    "loader_id__unit",
                ],
                inplace=True,
            )
            last_data = x.loc[counter - 1, "standby_code"]
            x["standby_code"] = x["standby_code"].shift(-1)
            x.loc[counter - 1, "standby_code"] = last_data
            df = pd.concat([df, x])
        df = df.sort_values(["timeStart"]).reset_index(drop=True)
        df["id"] = df["id"].fillna(0)
        df = df.ffill()

    df = df.to_dict(orient="records")
    return df


async def timeline(request):
    date_pattern = request.POST.get("date")
    hour_pattern = request.POST.get("hour")
    unit_pattern = request.POST.get("unit_id")
    show_hanging = request.POST.get("hanging") == "true"
    wh_proses = request.POST.get("wh_proses") == "true"

    maindata = await get_loader_status(date_pattern, hour_pattern, unit_pattern)
    response = {}
    response["state"] = []
    response["ritase"] = []

    if wh_proses:
        ritdata = await get_ritase(date_pattern, hour_pattern, unit_pattern)
        maindata = get_wh_proses(maindata, ritdata, unit_pattern)

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

    ritasedata = await get_ritase(date_pattern, hour_pattern, unit_pattern)

    for d in ritasedata:
        x = {}
        x["database_id"] = d["id"]
        x["time_full"] = d["time_full"].strftime("%Y-%m-%d %H:%M:%S")
        x["time_empty"] = (
            d["time_empty"].strftime("%Y-%m-%d %H:%M:%S") if d["time_empty"] else "N/A"
        )
        x["type"] = d["type"]
        x["unit"] = d["truck_id__jigsaw"]
        x["loc"] = d["dump_location"]
        response["ritase"].append(x)

    return JsonResponse(response, safe=False)


@sync_to_async
def get_status_batch(date_pattern, hour_pattern, unit_pattern):
    return list(
        LoaderStatus.objects.filter(
            date=date_pattern, hour=hour_pattern, unit__unit__in=unit_pattern
        )
        .order_by("unit__unit", "timeStart")
        .values("id", "unit__unit", "standby_code", "timeStart")
    )


@sync_to_async
def get_ritase_batch(date_pattern, hour_pattern, unit_pattern):
    return list(
        ritase.objects.filter(
            date=date_pattern, hour=hour_pattern, loader_id__unit__in=unit_pattern
        )
        .order_by("time_full")
        .values(
            "id",
            "time_full",
            "time_empty",
            "type",
            "loader_id__unit",
            "truck_id__jigsaw",
            "dump_location",
            "truck_id__OB_capacity",
        )
    )


def get_wh_proses_batch(maindata, ritdata, units): ...


async def timeline_batch(request):
    date = request.POST.get("date")
    hour = request.POST.get("hour")
    units = json.loads(request.POST.get("unit_id"))
    show_hanging = request.POST.get("hanging") == "true"
    wh_proses = request.POST.get("wh_proses") == "true"

    maindata = await get_status_batch(date, hour, units)
    ritasedata = await get_ritase_batch(date, hour, units)

    response = {}
    data = []

    for unit in units:
        response[unit] = {"state": [], "ritase": []}
        if wh_proses:
            stb_unit = [item for item in maindata if unit in item["unit__unit"]]
            rit_unit = [item for item in ritasedata if unit in item["loader_id__unit"]]
            data += get_wh_proses(stb_unit, rit_unit, unit)

    if wh_proses:
        maindata = data

    for i, d in enumerate(maindata):
        x = {}
        x["database_id"] = d["id"]
        x["unit"] = d["unit__unit"]
        x["timeStart"] = d["timeStart"].strftime("%Y-%m-%d %H:%M:%S")
        x["timeEnd"] = (
            (maindata[0]["timeStart"] + timedelta(hours=1)).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            if i == len(maindata) - 1
            or maindata[i]["unit__unit"] != maindata[i + 1]["unit__unit"]
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
            response[d["unit__unit"]]["state"].append(x)
            continue

        # If neither the previous nor the next code is S6, change S12 to WH
        x["label"] = "WH"
        response[d["unit__unit"]]["state"].append(x)
        continue

    for d in ritasedata:
        x = {}
        x["database_id"] = d["id"]
        x["time_full"] = d["time_full"].strftime("%Y-%m-%d %H:%M:%S")
        x["time_empty"] = (
            d["time_empty"].strftime("%Y-%m-%d %H:%M:%S") if d["time_empty"] else "N/A"
        )
        x["type"] = d["type"]
        x["unit"] = d["truck_id__jigsaw"]
        x["loc"] = d["dump_location"]
        response[d["loader_id__unit"]]["ritase"].append(x)

    return JsonResponse(response, safe=False)


async def load_data(request):
    date = request.POST.get("date")
    hour = int(request.POST.get("hour"))

    date_str = f"{date} {hour:02d}:00"  # YYYY-MM-DD HH:MM

    def run_command():
        call_command("loadLoader", date=date_str)

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, run_command)
    return HttpResponse(status=204)


def update(request):
    ts = request.POST.get("timestart")
    id = int(request.POST.get("database_id"))
    stb_code = str(request.POST.get("stb")).upper()

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
    return HttpResponse(status=204)


def add(request):
    id = int(request.POST.get("database_id"))
    stb = str(request.POST.get("stb")).upper()
    old = LoaderStatus.objects.get(pk=id)
    _old = serializers.serialize("json", [old])

    ts = request.POST.get("timestart")
    ts = f"{old.date} {ts}"
    ts = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")

    if old.hour == 6 and ts.time() >= time(6, 30, 0):
        shift = 1
        report_date = old.date
    elif old.hour == 6 and ts.time() < time(6, 30, 0):
        shift = 2
        report_date = old.date - timedelta(days=1)
    else:
        shift = old.shift
        report_date = old.report_date

    new_instance, created = LoaderStatus.objects.update_or_create(
        timeStart=ts,
        unit=old.unit,
        hour=old.hour,
        date=old.date,
        shift=shift,
        remarks=old.remarks,
        report_date=report_date,
        defaults={"standby_code": stb},
    )

    if created:
        # Save the new instance's state
        LoaderStatusHistory.objects.create(
            action="add",
            loader_status_id=new_instance.id,
            data=serializers.serialize("json", [new_instance]),
            token=request.COOKIES.get("csrftoken"),
        )
    else:
        LoaderStatusHistory.objects.create(
            action="update",
            loader_status_id=id,
            data=_old,
            token=request.COOKIES.get("csrftoken"),
        )

    return HttpResponse(status=204)


def addBatch(request):
    id = int(request.POST.get("database_id"))
    old = LoaderStatus.objects.get(pk=id)

    stb = str(request.POST.get("stb")).upper()
    units = json.loads(request.POST.get("units"))

    ts = request.POST.get("timestart")
    ts = f"{old.date} {ts}"
    ts = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")

    if old.hour == 6 and ts.time() >= time(6, 30, 0):
        shift = 1
        report_date = old.date
    elif old.hour == 6 and ts.time() < time(6, 30, 0):
        shift = 2
        report_date = old.date - timedelta(days=1)
    else:
        shift = old.shift
        report_date = old.report_date

    instances = []

    for u in units:
        unit = loaderID.objects.get(unit=u)
        instance, created = LoaderStatus.objects.update_or_create(
            timeStart=ts,
            hour=old.hour,
            date=old.date,
            shift=shift,
            remarks=old.remarks,
            report_date=report_date,
            unit=unit,
            defaults={"standby_code": stb},
        )
        instances.append(instance)

    if created:
        LoaderStatusHistory.objects.create(
            action="addBatch",
            loader_status_id=0,
            data=serializers.serialize("json", instances),
            token=request.COOKIES.get("csrftoken"),
        )
    else:
        LoaderStatusHistory.objects.create(
            action="updateBtch",
            loader_status_id=0,
            data=serializers.serialize("json", instances),
            token=request.COOKIES.get("csrftoken"),
        )

    return HttpResponse(status=204)


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
    return HttpResponse(status=204)


def split(request):
    id = int(request.POST.get("database_id"))
    ts = request.POST.get("timestart")
    ts = datetime.strptime(ts, "%d/%m/%Y, %H:%M:%S")

    old = LoaderStatus.objects.get(pk=id)

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
    return HttpResponse(status=204)


def undo(request):
    last_action = LoaderStatusHistory.objects.filter(
        token=request.COOKIES.get("csrftoken")
    ).last()

    if not last_action:
        return redirect(request.META.get("HTTP_REFERER"))

    obj = list(serializers.deserialize("json", last_action.data))[0]
    unit = obj.object.unit.unit

    units = []

    if last_action.action == "update":
        # Revert to previous state
        obj = list(serializers.deserialize("json", last_action.data))[0]
        obj.save()
        units.append(unit)

    elif last_action.action == "add":
        # Delete the last added object
        LoaderStatus.objects.get(pk=last_action.loader_status_id).delete()
        units.append(unit)

    elif last_action.action == "delete":
        # Restore the deleted object
        obj = list(serializers.deserialize("json", last_action.data))[0]
        obj.save()
        units.append(unit)

    elif last_action.action == "addBatch":
        objs = list(serializers.deserialize("json", last_action.data))
        for obj in objs:
            LoaderStatus.objects.get(pk=obj.object.id).delete()
            unit = obj.object.unit.unit
            units.append(unit)

    elif last_action.action == "updateBtch":
        objs = list(serializers.deserialize("json", last_action.data))
        for obj in objs:
            obj.save()
            unit = obj.object.unit.unit
            units.append(unit)

    # Remove the last action from history
    last_action.delete()

    return JsonResponse({"units": units}, status=200)
