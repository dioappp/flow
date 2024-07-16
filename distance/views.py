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
    df = df[df.iloc[:, 0] == date]
    df = df.iloc[:, [0, 5, 7, 9, 11, 13, 22, 55, 19]]

    df = df.rename(
        columns={
            "Unnamed: 2": "date",
            "Unnamed: 7": "loader",
            "Unnamed: 9": "blok_loading",
            "Unnamed: 11": "elevasi_loading",
            "Unnamed: 13": "lokasi_dumping",
            "Unnamed: 15": "elevasi_dumping",
            "Unnamed: 24": "horizontal_distance",
            "Unnamed: 57": "bcm_survey",
            "Unnamed: 21": "vertical_distance",
        }
    )
    df["lokasi"] = lokasi
    df["vdistance_x_bcm"] = df["vertical_distance"] * df["bcm_survey"]
    df["vertical_distance"] = df.groupby(["loader"])["vdistance_x_bcm"].transform(
        "sum"
    ) / df.groupby(["loader"])["bcm_survey"].transform("sum")
    df = df.drop(columns=["vdistance_x_bcm", "bcm_survey"])
    return df


def import_data(request):
    form = UploadFileForm(request.POST, request.FILES)
    if form.is_valid():
        date = form.cleaned_data["date"]
        if isinstance(date, datetime):
            date = date.replace(tzinfo=None)
        file_ob = request.FILES["file_OB"]
        file_ob = pd.read_excel(
            file_ob, sheet_name=["CENTRAL", "NORTH IPPKH"], usecols="C:BF"
        )
        df = extract_data_ob(file_ob["NORTH IPPKH"], date, "NORTH")
        df = pd.concat(
            [df, extract_data_ob(file_ob["CENTRAL"], date, "CENTRAL")],
            ignore_index=True,
        )
        print(df)
    return HttpResponse(status=204)
