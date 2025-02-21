import json
from django.shortcuts import render
from exporter.views import is_in_jam_kritis
from hm.models import hmOperator
from ritase.models import ritase
from ritase.views import get_shift_time
from stb_loader.models import LoaderStatus
from django.http import JsonResponse
from datetime import timedelta
import math
from asgiref.sync import sync_to_async
from django.db.models import F, Q, Max, Sum
import pandas as pd

from stb_loader.views import is_nempel_ke_jam_kritis


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

    maindata = (
        LoaderStatus.objects.filter(report_date=date_pattern, shift=shift_pattern)
        .values("unit__unit")
        .annotate(
            cluster=Max("location__cluster"),
            pit=Max("location__pit"),
        )
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

    ts, te = get_shift_time(date_pattern, str(shift_pattern))
    ts = ts - timedelta(minutes=30)
    te = te - timedelta(hours=1)

    data_hm = (
        hmOperator.objects.filter(
            Q(equipment__startswith="X")
            | Q(equipment__startswith="S")
            | Q(equipment__startswith="E"),
            Q(login_time__gte=ts, login_time__lt=te),
        )
        .annotate(d=(F("hm_end") - F("hm_start")))
        .values("equipment")
        .annotate(durasi=Sum("d"))
        .values("equipment", "durasi")
    )
    data_hm = {item["equipment"]: item["durasi"] for item in data_hm}

    unit_list = [item["unit__unit"] for item in page_obj]

    data_wh = get_wh(date_pattern, shift_pattern, unit_list)

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
        x["cluster"] = f"{d['cluster']}, {d['pit']}"
        x["hm"] = data_hm.get(d["unit__unit"], 0)
        x["wh"] = data_wh.get(d["unit__unit"], 0)
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


def get_wh(date, shift, unit_list) -> dict:
    data_loader = (
        LoaderStatus.objects.filter(
            report_date=date, shift=shift, unit__unit__in=unit_list
        )
        .annotate(
            equipment=F("unit__unit"),
        )
        .values(
            "equipment",
            "timeStart",
            "standby_code",
        )
    )
    data = list(data_loader)
    if not data:
        return {}

    df = pd.DataFrame(data)
    df = df.sort_values(by=["equipment", "timeStart"])
    df["timeStart"] = pd.to_datetime(df["timeStart"])

    s = 60 - df["timeStart"].max().second
    if shift == 2 and df["timeStart"].max().hour == 6:
        m = 29 - df["timeStart"].max().minute
    else:
        m = 59 - df["timeStart"].max().minute

    te = df["timeStart"].max() + pd.Timedelta(minutes=m, seconds=s)

    df["timeEnd"] = df.groupby("equipment")["timeStart"].shift(-1)
    df["timeEnd"] = df["timeEnd"].fillna(te)

    df["durasi"] = df["timeEnd"] - df["timeStart"]
    df["durasi"] = pd.to_timedelta(df["durasi"]).dt.total_seconds() / 3600

    df["shift"] = shift

    df = df.reset_index(drop=True)

    ids = df.index[df.standby_code == "S12"].tolist()

    for id in ids:
        if not is_in_jam_kritis(id, df):
            df.loc[id, "standby_code"] = "WH"

    df = df.groupby(["equipment", "standby_code"], as_index=False).agg(
        {
            "durasi": "sum",
        }
    )

    df = df[df["standby_code"].str.contains("WH")]
    df = df.groupby("equipment").sum()
    df = df.drop(columns="standby_code")
    return df.to_dict()["durasi"]


@sync_to_async
def get_loader_status(date_pattern, shift_pattern, unit_pattern):
    return list(
        LoaderStatus.objects.filter(
            report_date=date_pattern, shift=shift_pattern, unit__unit=unit_pattern
        )
        .order_by("timeStart")
        .values("id", "standby_code", "timeStart", "hour")
    )


@sync_to_async
def get_ritase(date_pattern, shift_pattern, unit_pattern):
    return list(
        ritase.objects.filter(
            report_date=date_pattern,
            type__isnull=False,
            shift=shift_pattern,
            loader_id__unit=unit_pattern,
        ).values("type", "time_full", "hour", "date")
    )


def get_wh_proses(maindata: list, ritdata: list, unit_pattern: str) -> dict:
    response = {}
    response["state"] = []
    response["ritase"] = []

    df = pd.DataFrame(maindata)
    df = df.sort_values(["timeStart"]).reset_index(drop=True)
    df["equipment"] = unit_pattern
    ids = df.index[df.standby_code == "S12"].tolist()

    for id in ids:
        if not is_in_jam_kritis(id, df):
            df.loc[id, "standby_code"] = "WH"

    df["group"] = (df["standby_code"] != df["standby_code"].shift()).cumsum()
    df = df.groupby(["hour", "group"], as_index=False).first()
    df = df.drop(columns="group")

    if ritdata:
        rdf = pd.DataFrame(ritdata)
        rdf = rdf.sort_values(["time_full"]).reset_index(drop=True)
        rdf["group"] = (rdf["type"] != rdf["type"].shift()).cumsum()
        rdf = rdf.groupby(["hour", "group"], as_index=False).last()
        rdf = rdf.drop(columns="group")

        counter = rdf.groupby(["date", "hour"], as_index=False).agg(
            {"time_full": "count", "type": "first"}
        )
        for i, d in counter.iterrows():
            df.loc[
                (df["standby_code"] == "WH") & (df["hour"] == d.hour),
                "standby_code",
            ] = f"WH {d.type}"

            if d.time_full != 1:
                x = []
                x = rdf[(rdf["date"] == d.date) & (rdf["hour"] == d.hour)]
                x = x.rename(columns={"time_full": "timeStart", "type": "standby_code"})
                x["standby_code"] = x["standby_code"].apply(lambda x: f"WH {x}")
                last_data = x.loc[x.index[-1], "standby_code"]
                x["standby_code"] = x["standby_code"].shift(-1)
                x.loc[x.index[-1], "standby_code"] = last_data
                df = pd.concat([df, x])
        df = df.sort_values(["timeStart"]).reset_index(drop=True)
        df["id"] = df["id"].fillna(0)
        df = df.ffill()

    hour_list = list(df["hour"].unique())
    df.loc[df["standby_code"].isin(["WH None"]), "standby_code"] = "WH GEN"
    df = df.to_dict(orient="records")

    for h in hour_list:
        data = [d for d in df if d.get("hour") == h]
        for i, d in enumerate(data):
            x = {}
            x["database_id"] = d.get(
                "id",
            )
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
    return response


async def timeline(request):
    date_pattern = request.POST.get("date")
    shift_pattern = request.POST.get("shift")
    unit_pattern = request.POST.get("unit_id")
    show_hanging = request.POST.get("hanging") == "true"
    wh_proses = request.POST.get("wh_proses") == "true"

    maindata = await get_loader_status(date_pattern, shift_pattern, unit_pattern)

    response = {}
    response["state"] = []
    response["ritase"] = []

    if wh_proses:
        ritdata = await get_ritase(date_pattern, shift_pattern, unit_pattern)
        response = get_wh_proses(maindata, ritdata, unit_pattern)

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
            if not show_hanging:
                x["label"] = "WH" if d["standby_code"] == "S12" else d["standby_code"]
            else:
                x["label"] = d["standby_code"]
            response["state"].append(x)
    return JsonResponse(response, safe=False)


@sync_to_async
def get_status_batch(date_pattern, shift_pattern, unit_pattern):
    return list(
        LoaderStatus.objects.filter(
            report_date=date_pattern, shift=shift_pattern, unit__unit__in=unit_pattern
        )
        .order_by("unit__unit", "timeStart")
        .values("id", "unit__unit", "standby_code", "timeStart", "hour")
    )


@sync_to_async
def get_ritase_batch(date_pattern, shift_pattern, unit_pattern):
    return list(
        ritase.objects.filter(
            report_date=date_pattern,
            shift=shift_pattern,
            loader_id__unit__in=unit_pattern,
        )
        .order_by("time_full")
        .values(
            "id",
            "time_full",
            "time_empty",
            "type",
            "hour",
            "date",
            "loader_id__unit",
            "truck_id__jigsaw",
            "dump_location",
            "truck_id__OB_capacity",
        )
    )


async def timeline_batch(request):
    date = request.POST.get("date")
    shift = request.POST.get("shift")
    units = json.loads(request.POST.get("unit_id"))
    show_hanging = request.POST.get("hanging") == "true"
    wh_proses = request.POST.get("wh_proses") == "true"

    maindata = await get_status_batch(date, shift, units)
    ritasedata = await get_ritase_batch(date, shift, units)

    response = {}
    data = []

    for unit in units:
        response[unit] = {"state": [], "ritase": []}
        if wh_proses:
            stb_unit = [item for item in maindata if unit in item["unit__unit"]]
            rit_unit = [item for item in ritasedata if unit in item["loader_id__unit"]]
            response[unit] = get_wh_proses(stb_unit, rit_unit, unit)

    if wh_proses:
        return JsonResponse(response, safe=False, status=200)

    hour_list = []
    for d in maindata:
        if d["hour"] not in hour_list:
            hour_list.append(d["hour"])

    for h in hour_list:
        data = [d for d in maindata if d.get("hour") == h]
        for i, d in enumerate(data):
            x = {}
            x["database_id"] = d["id"]
            x["unit"] = d["unit__unit"]
            x["timeStart"] = d["timeStart"].strftime("%Y-%m-%d %H:%M:%S")
            if not h == 6:
                x["timeEnd"] = (
                    (data[0]["timeStart"] + timedelta(hours=1)).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    if i == len(data) - 1
                    or data[i]["unit__unit"] != data[i + 1]["unit__unit"]
                    else data[i + 1]["timeStart"].strftime("%Y-%m-%d %H:%M:%S")
                )
            else:
                x["timeEnd"] = (
                    (data[0]["timeStart"] + timedelta(minutes=30)).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    if i == len(data) - 1
                    or data[i]["unit__unit"] != data[i + 1]["unit__unit"]
                    else data[i + 1]["timeStart"].strftime("%Y-%m-%d %H:%M:%S")
                )
            # Check the previous and next records if they exist
            prev_code = maindata[i - 1]["standby_code"] if i > 0 else None
            next_code = (
                maindata[i + 1]["standby_code"] if i < len(maindata) - 1 else None
            )

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

    return JsonResponse(response, safe=False)
