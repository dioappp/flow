from django.shortcuts import render
from django.http import HttpResponse
from tablib import Dataset
from distance.resources import DistanceResource
from distance.forms import UploadFileForm
import pandas as pd
from pandas import DataFrame
from datetime import datetime


# Create your views here.
def index(request):
    form = UploadFileForm()
    return render(request, "distance/index.html", {"form": form})


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
    df["lokasi"] = lokasi
    print(df.head())
    return df


def import_data(request):
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

        df_html = df.to_html(classes="table table-striped table-hover")
    return render(request, "distance/index.html", {"df_html": df_html})
