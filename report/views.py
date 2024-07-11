from django.shortcuts import render
from stb_loader.models import LoaderStatus
from django.http import JsonResponse
import math
import pandas as pd
import sqlite3


# Create your views here.
def index(request):
    loop_times = [f"{hour:02d}:00 - {(hour+1)%24:02d}:00" for hour in range(24)]
    return render(request, "report/index.html", {"jam": loop_times})


def showreport(request):
    date_pattern = request.POST.get("date")
    shift_pattern = request.POST.get("shift")
    con = sqlite3.connect("db.sqlite3")

    query = f"""
    SELECT report_date, hour, shift, timeStart, standby_code, stb_loaderid.unit, remarks, date
    FROM stb_loaderstatus
    LEFT OUTER JOIN stb_loaderid ON (stb_loaderid.id = stb_loaderstatus.unit_id)
    where report_date = '{date_pattern}' and shift = {shift_pattern}
    """
    df = pd.read_sql(query, con)

    if df.empty:
        data_return = []
        response = {
            "draw": request.POST.get("draw"),
            "data": data_return,
        }
        return JsonResponse(response)

    df = df.sort_values(by=["unit", "timeStart"])
    df["timeStart"] = pd.to_datetime(df["timeStart"])

    s = 60 - df["timeStart"].max().second
    if shift_pattern == 2 and df["timeStart"].max().hour == 6:
        m = 29 - df["timeStart"].max().minute
    else:
        m = 59 - df["timeStart"].max().minute

    te = df["timeStart"].max() + pd.Timedelta(minutes=m, seconds=s)

    df["timeEnd"] = df.groupby("unit")["timeStart"].shift(-1)
    df["timeEnd"] = df["timeEnd"].fillna(te)

    df["durasi"] = df["timeEnd"] - df["timeStart"]
    df["durasi"] = pd.to_timedelta(df["durasi"]).dt.total_seconds() / 3600

    cond = ~df["hour"].isin([6, 11, 13, 18, 19]) & (df["standby_code"] == "S12")
    df.loc[cond, "standby_code"] = "WH"

    result = df.groupby(["unit", "standby_code"], as_index=False).agg(
        {
            "report_date": "first",
            "durasi": "sum",
            "remarks": "first",
        }
    )
    result = result.sort_values(by=["unit"], ascending=False)
    result = result[result["standby_code"] == "WH"]
    total = len(result)
    data = result[
        result["unit"].str.contains(
            request.POST.get("search[value]"), regex=False, na=False
        )
    ]
    total_filtered = len(data)
    _start = request.POST.get("start")
    _length = request.POST.get("length")
    page = 1

    if _start and _length:
        start = int(_start)
        length = int(_length)
        page = math.ceil(start / length) + 1
    page_obj = data.iloc[start : start + length]

    data_return = page_obj.to_dict(orient="records")

    response = {
        "draw": request.POST.get("draw"),
        "data": data_return,
        "page": int(page) if page else 1,
        "per_page": length,
        "recordsTotal": total,
        "recordsFiltered": total_filtered,
    }

    return JsonResponse(response)
