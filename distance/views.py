from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from distance.models import distance
from stb_loader.models import loaderID
from distance.forms import UploadFileForm
import pandas as pd
from pandas import DataFrame
from datetime import datetime, timedelta
import json


# Create your views here.
def index(request):
    today = timezone.now().date()
    seven_days_ago = today - timedelta(days=7)
    form = UploadFileForm()
    dates = (
        distance.objects.filter(date__range=[seven_days_ago, today])
        .values_list("date", flat=True)
        .distinct()
        .order_by("date")
    )
    return render(request, "distance/index.html", {"form": form, "dates": dates})


def extract_data_ob(df: DataFrame, date: datetime, lokasi: str) -> DataFrame:
    column_names = {
        0: "date",
        1: "loader",
        2: "blok_loading",
        3: "elevasi_loading",
        4: "lokasi_dumping",
        5: "elevasi_dumping",
        6: "horizontal_distance",
        7: "bcm_survey",
        8: "vertical_distance",
    }
    df = df[df.iloc[:, 0] == date]
    df = df.iloc[:, [0, 5, 7, 9, 11, 13, 22, 55, 19]]

    df = df.rename(
        columns={df.columns[idx]: new_name for idx, new_name in column_names.items()}
    )
    df["lokasi"] = lokasi
    df["vdistance_x_bcm"] = df["vertical_distance"] * df["bcm_survey"]
    df["vertical_distance"] = df.groupby(["loader"])["vdistance_x_bcm"].transform(
        "sum"
    ) / df.groupby(["loader"])["bcm_survey"].transform("sum")
    df = df.drop(columns=["vdistance_x_bcm", "bcm_survey"])
    return df


def extract_data_coal(df: DataFrame, date: datetime, lokasi: str) -> DataFrame:
    column_names = {
        0: "date",
        1: "loader",
        2: "blok_loading",
        3: "elevasi_loading",
        4: "lokasi_dumping",
        5: "elevasi_dumping",
        6: "horizontal_distance",
        7: "vertical_distance",
    }
    df = df[df.iloc[:, 0] == date]
    df = df.iloc[:, [0, 5, 7, 9, 14, 13, 21, 17]]
    df = df.rename(
        columns={df.columns[idx]: new_name for idx, new_name in column_names.items()}
    )
    df["lokasi_dumping"] = df["lokasi_dumping"].replace("_", " ", regex=True)
    df["lokasi"] = lokasi
    return df


def import_data(request):
    if request.method == "POST":
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            date = form.cleaned_data["date"]
            if isinstance(date, datetime):
                date = date.replace(tzinfo=None)
            file_ob = request.FILES["file_OB"]
            file_coal = request.FILES["file_Coal"]

            file_ob = pd.read_excel(
                file_ob, sheet_name=["CENTRAL", "NORTH IPPKH"], usecols="C:BF"
            )
            file_coal = pd.read_excel(
                file_coal,
                sheet_name=[
                    "Jigsaw SIS Rom 13A CT",
                    "Jigsaw SIS Rom 13B CT",
                    "Jigsaw SIS Rom 17 (CT)",
                    "Jigsaw SIS Rom 19",
                    "Jigsaw SIS Rom 17B",
                    "Jigsaw SIS Rom 20",
                ],
                usecols="C:BE",
                skipfooter=12,
            )

            df = extract_data_ob(file_ob["NORTH IPPKH"], date, "NORTH")
            df = pd.concat(
                [
                    df,
                    extract_data_ob(file_ob["CENTRAL"], date, "CT1"),
                    extract_data_coal(file_coal["Jigsaw SIS Rom 13A CT"], date, "CT1"),
                    extract_data_coal(file_coal["Jigsaw SIS Rom 13B CT"], date, "CT1"),
                    extract_data_coal(file_coal["Jigsaw SIS Rom 17 (CT)"], date, "CT1"),
                    extract_data_coal(file_coal["Jigsaw SIS Rom 19"], date, "CT1"),
                    extract_data_coal(file_coal["Jigsaw SIS Rom 17B"], date, "NORTH"),
                    extract_data_coal(file_coal["Jigsaw SIS Rom 20"], date, "NORTH"),
                ],
                ignore_index=True,
            )
            df["date"] = pd.to_datetime(df["date"]).dt.date

            df_html = df.to_html(
                classes="table table-striped table-hover",
                table_id="table-distance",
            )
        return render(request, "distance/show_table.html", {"df_html": df_html})
    else:
        return render(request, "distance/show_table.html", {"df_html": {}})


def to_db(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            updated_list = []
            for d in data:
                loader, _ = loaderID.objects.get_or_create(unit=d["loader"])
                _, created = distance.objects.update_or_create(
                    date=datetime.strptime(d["date"], "%Y-%m-%d").date(),
                    loader=loader,
                    blok_loading=d["blok_loading"],
                    lokasi_dumping=d["lokasi_dumping"],
                    defaults={
                        "elevasi_loading": int(d["elevasi_loading"]),
                        "elevasi_dumping": float(d["elevasi_dumping"]),
                        "horizontal_distance": float(d["horizontal_distance"]),
                        "lokasi": d["lokasi"],
                        "vertical_distance": float(d["vertical_distance"]),
                    },
                )
                x = {d["loader"]: created}
                updated_list.append(x)
            return JsonResponse(
                {"message": "Table data received successfully", "data": updated_list},
                status=200,
            )
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
    return JsonResponse({"error": "Invalid request method"}, status=405)
