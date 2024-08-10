from django.shortcuts import render, redirect
from django.db.models import OuterRef, Subquery
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from hm.models import Operator, hmOperator
from ritase.models import cek_ritase
from stb_loader.models import ClusterLoader, LoaderStatus
import pandas as pd


# Create your views here.
def index(request):
    return render(request, "exporter/index.html")


def standby(request):
    date = request.POST.get("date")
    shift = int(request.POST.get("shift"))
    format = request.POST.get("format")

    if format == "SICoPP":
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
    elif format == "Input Ritasi":
        return HttpResponse("Format yang Input Ritasi belum tersedia")
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
