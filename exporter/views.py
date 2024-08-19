from itertools import chain
from django.shortcuts import render, redirect
from django.db.models import OuterRef, Subquery, F
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from hm.models import Operator, hmOperator
from ritase.models import cek_ritase
from stb_hauler.models import HaulerStatus
from stb_loader.models import ClusterLoader, LoaderStatus
import pandas as pd


# Create your views here.
def index(request):
    return render(request, "exporter/index.html")


def is_in_jam_kritis(id: int, df: pd.DataFrame) -> bool:
    jam_kritis = ["S6", "S5A", "S8"]
    unit = df.loc[id, "equipment"]

    if id == 0:
        check_before = True
    else:
        stb_before = df.loc[id - 1, "standby_code"]
        unit_before = df.loc[id - 1, "equipment"]
        check_before = (stb_before in jam_kritis) and (unit_before == unit)

    if id == len(df) - 1:
        check_after = True
    else:
        stb_after = df.loc[id + 1, "standby_code"]
        unit_after = df.loc[id + 1, "equipment"]
        check_after = (stb_after in jam_kritis) and (unit_after == unit)

    return check_before or check_after


def standby(request):
    date = request.POST.get("date")
    shift = int(request.POST.get("shift"))
    format = request.POST.get("format")

    if format == "SICoPP":
        subquery = ClusterLoader.objects.filter(
            date=OuterRef("date"), hour=OuterRef("hour"), unit=OuterRef("unit")
        )
        data_loader = (
            LoaderStatus.objects.filter(report_date=date, shift=shift)
            .annotate(
                pit=Coalesce(Subquery(subquery.values("pit")[:1]), None),
                equipment=F("unit__ellipse"),
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

        df = df.reset_index(drop=True)

        ids = df.index[df.standby_code == "S12"].tolist()

        for id in ids:
            if not is_in_jam_kritis(id, df):
                df.loc[id, "standby_code"] = "WH"

        result = df.groupby(["unit", "standby_code"], as_index=False).agg(
            {
                "durasi": "sum",
            }
        )
        result = (
            result.pivot(index="unit", columns="standby_code", values="durasi")
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
    else:
        return HttpResponse("Format yang ada pilih belum tersedia")


def production(request):
    date = request.POST.get("date")
    shift = int(request.POST.get("shift"))

    subquery = hmOperator.objects.filter(id=OuterRef("operator_hauler_id"))

    data = (
        cek_ritase.objects.filter(date=date, shift=shift)
        .annotate(
            nrp=Coalesce(Subquery(subquery.values("NRP")[:1]), None),
            operator_hauler=Coalesce(
                Subquery(subquery.values("NRP__operator")[:1]), None
            ),
            hm_start=Coalesce(Subquery(subquery.values("hm_start")[:1]), None),
            hm_end=Coalesce(Subquery(subquery.values("hm_end")[:1]), None),
        )
        .values(
            "loader",
            "code_material",
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
    filename = "ritase.xlsx"
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    df.to_excel(response, index=False)
    return response
