from itertools import chain
from django.shortcuts import render
from django.db.models import OuterRef, Subquery, F
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from hm.models import hmOperator
from ritase.models import cek_ritase, ritase
from stb_hauler.models import HaulerStatus
from stb_loader.models import ClusterLoader, LoaderStatus
import pandas as pd


# Create your views here.
def index(request):
    return render(request, "exporter/index.html")


def is_in_jam_kritis(id: int, df: pd.DataFrame) -> bool:
    if df.loc[id, "shift"] == 1:
        jam_kritis = ["S6", "S5A", "S8", "S15"]
    elif df.loc[id, "shift"] == 2:
        jam_kritis = ["S6"]

    unit = df.loc[id, "equipment"]

    if id == 0 or id == len(df) - 1:
        return True

    unit_before = df.loc[id - 1, "equipment"]
    unit_after = df.loc[id + 1, "equipment"]

    if unit_before != unit or unit_after != unit:
        return True

    stb_before = df.loc[id - 1, "standby_code"]
    check_before = stb_before in jam_kritis

    stb_after = df.loc[id + 1, "standby_code"]
    check_after = stb_after in jam_kritis

    return check_before or check_after


def standby(request):
    date = request.POST.get("date")
    shift = int(request.POST.get("shift"))
    format = request.POST.get("format")

    if format == "":
        subquery = ClusterLoader.objects.filter(
            date=OuterRef("date"), hour=OuterRef("hour"), unit=OuterRef("unit")
        )
        data_loader = (
            LoaderStatus.objects.filter(report_date=date, shift=shift)
            .annotate(
                pit=Coalesce(Subquery(subquery.values("pit")[:1]), None),
                equipment=F("unit__unit"),
            )
            .values(
                "report_date",
                "hour",
                "shift",
                "timeStart",
                "standby_code",
                "equipment",
                "remarks",
                "date",
                "pit",
            )
        )
        data_hauler = (
            HaulerStatus.objects.filter(report_date=date, shift=shift)
            .annotate(equipment=F("unit__jigsaw"))
            .values(
                "report_date",
                "hour",
                "shift",
                "timeStart",
                "standby_code",
                "equipment",
                "remarks",
                "date",
            )
        )

        data = list(chain(list(data_loader), list(data_hauler)))

        if not data:
            return HttpResponse(
                f"Data Standby tanggal: {date}, Shift {shift} belum tersedia"
            )

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
        df["durasi"] = pd.to_timedelta(df["durasi"]).dt.total_seconds() / 60

        df = df.reset_index(drop=True)

        ids = df.index[df.standby_code == "S12"].tolist()

        for id in ids:
            if not is_in_jam_kritis(id, df):
                df.loc[id, "standby_code"] = "WH"

        result = df.groupby(["hour", "equipment", "standby_code"], as_index=False).agg(
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
            "equipment",
            "date",
            "hour",
            "BD Status",
            "statusBDC",
            "standby_code",
            "durasi",
            "remarks",
        ]
        result = result.reindex(columns=column_order)
        result = result.sort_values(by=["equipment", "date", "hour"])
        result = result.drop(columns="date")
        # result = result[~result["standby_code"].str.startswith("WH")].reset_index(
        #     drop=True
        # )

        filename = f"standby-{date}-shift{shift}.xlsx"
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        result.to_excel(response, index=False)
        return response
    elif format == "Input Ritasi":
        data = LoaderStatus.objects.filter(report_date=date, shift=shift).values(
            "timeStart",
            "standby_code",
            "unit__unit",
        )
        if not data:
            return HttpResponse(
                f"Data Standby tanggal: {date}, Shift {shift} belum tersedia"
            )

        df = pd.DataFrame(list(data))
        df = df.rename(columns={"unit__unit": "equipment"})
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
        df["durasi"] = pd.to_timedelta(df["durasi"]).dt.total_seconds() / 60

        df = df.reset_index(drop=True)

        ids = df.index[df.standby_code == "S12"].tolist()

        for id in ids:
            if not is_in_jam_kritis(id, df):
                df.loc[id, "standby_code"] = "WH"

        result = df.groupby(["equipment", "standby_code"], as_index=False).agg(
            {
                "durasi": "sum",
            }
        )
        result = (
            result.pivot(index="equipment", columns="standby_code", values="durasi")
            .fillna(0)
            .reset_index()
        )
        filename = f"standby-{date}-shift{shift}-pivot.xlsx"
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        result.to_excel(response, index=False)

        return response
    elif format == "SICoPP":
        data_loader = (
            LoaderStatus.objects.filter(report_date=date, shift=shift)
            .annotate(
                pit=F("location__pit"),
                equipment=F("unit__unit"),
            )
            .values(
                "report_date",
                "hour",
                "shift",
                "timeStart",
                "standby_code",
                "equipment",
                "remarks",
                "date",
                "pit",
            )
        )
        if not data_loader:
            return HttpResponse(
                f"Data Standby tanggal: {date}, Shift {shift} belum tersedia"
            )
        df = pd.DataFrame(list(data_loader))
        df = df.sort_values(["equipment", "timeStart"]).reset_index(drop=True)

        ids = df.index[df.standby_code == "S12"].tolist()

        for id in ids:
            if not is_in_jam_kritis(id, df):
                df.loc[id, "standby_code"] = "WH"

        df["group"] = (df["standby_code"] != df["standby_code"].shift()).cumsum()
        df = df.groupby(["equipment", "date", "hour", "group"], as_index=False).first()
        df = df.drop(columns="group")

        rit = (
            ritase.objects.filter(report_date=date, type__isnull=False, shift=shift)
            .annotate(equipment=F("loader_id__unit"))
            .values("equipment", "type", "time_full", "hour", "date")
        )
        rdf = pd.DataFrame(list(rit))
        rdf = rdf.sort_values(["equipment", "time_full"]).reset_index(drop=True)
        rdf["group"] = (rdf["type"] != rdf["type"].shift()).cumsum()
        rdf = rdf.groupby(["equipment", "hour", "group"], as_index=False).last()
        rdf = rdf.drop(columns="group")
        counter = rdf.groupby(["equipment", "date", "hour"], as_index=False).agg(
            {"time_full": "count", "type": "first"}
        )
        for i, d in counter.iterrows():
            df.loc[
                (df["standby_code"] == "WH")
                & (df["hour"] == d.hour)
                & (df["date"] == d.date)
                & (df["equipment"] == d.equipment),
                "standby_code",
            ] = f"WH {d.type}"

            if d.time_full != 1:
                x = []
                x = rdf[
                    (rdf["date"] == d.date)
                    & (rdf["hour"] == d.hour)
                    & (rdf["equipment"] == d.equipment)
                ]
                x = x.rename(columns={"time_full": "timeStart", "type": "standby_code"})
                x["standby_code"] = x["standby_code"].apply(lambda x: f"WH {x}")
                last_data = x.loc[x.index[-1], "standby_code"]
                x["standby_code"] = x["standby_code"].shift(-1)
                x.loc[x.index[-1], "standby_code"] = last_data
                df = pd.concat([df, x])

        df = df.sort_values(["equipment", "timeStart"]).reset_index(drop=True)
        df[["report_date", "shift", "pit"]] = df[
            ["report_date", "shift", "pit"]
        ].ffill()

        s = 60 - df["timeStart"].max().second
        if shift == 2 and df["timeStart"].max().hour == 6:
            m = 29 - df["timeStart"].max().minute
        else:
            m = 59 - df["timeStart"].max().minute

        te = df["timeStart"].max() + pd.Timedelta(minutes=m, seconds=s)

        df["timeEnd"] = df.groupby("equipment")["timeStart"].shift(-1)
        df["timeEnd"] = df["timeEnd"].fillna(te)

        df["durasi"] = df["timeEnd"] - df["timeStart"]
        df["durasi"] = pd.to_timedelta(df["durasi"]).dt.total_seconds() / 60

        df = df.reset_index(drop=True)

        result = df.groupby(["hour", "equipment", "standby_code"], as_index=False).agg(
            {
                "report_date": "first",
                "durasi": "sum",
                "remarks": "first",
                "date": "first",
                "pit": "first",
                "shift": "first",
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
            "equipment",
            "date",
            "hour",
            "BD Status",
            "statusBDC",
            "standby_code",
            "durasi",
            "remarks",
            "shift",
        ]
        result = result.reindex(columns=column_order)
        result = result.sort_values(by=["equipment", "date", "hour"])
        result = result.drop(columns="date")

        filename = f"standby-{date}-shift{shift}.xlsx"
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        result.to_excel(response, index=False)

        return response
    else:
        return HttpResponse("Format yang ada pilih belum tersedia")


def production(request):
    date = request.POST.get("date")
    shift = int(request.POST.get("shift"))

    subquery = hmOperator.objects.filter(id=OuterRef("operator_hauler_id"))

    data = (
        cek_ritase.objects.filter(date=date, shift=shift, code_material__isnull=False)
        .annotate(
            nrp=Coalesce(Subquery(subquery.values("NRP")[:1]), None),
            operator_hauler=Coalesce(
                Subquery(subquery.values("NRP__operator")[:1]), None
            ),
            hm_start=Coalesce(Subquery(subquery.values("hm_start")[:1]), None),
            hm_end=Coalesce(Subquery(subquery.values("hm_end")[:1]), None),
            material=F("code_material__material"),
            remark=F("code_material__remark"),
        )
        .values(
            "date",
            "shift",
            "loader",
            "material",
            "remark",
            "hauler",
            "nrp",
            "operator_hauler",
            "hm_start",
            "hm_end",
            "a",
            "b",
            "c",
            "d",
            "e",
            "f",
            "g",
            "h",
            "i",
            "j",
            "k",
            "l",
            "m",
        )
    )
    df = pd.DataFrame(list(data))
    column_order = [
        "date",
        "shift",
        "hauler",
        "nrp",
        "hm_start",
        "hm_end",
        "loader",
        "material",
        "remark",
        "a",
        "b",
        "c",
        "d",
        "e",
        "f",
        "g",
        "h",
        "i",
        "j",
        "k",
        "l",
        "m",
        "operator_hauler",
    ]
    df = df.reindex(columns=column_order)
    filename = f"ritase-{date}-{shift}.xlsx"
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    df.to_excel(response, index=False)
    return response
