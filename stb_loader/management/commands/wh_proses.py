from django.core.management.base import BaseCommand
from ritase.models import ritase, truckID
from stb_loader.models import loaderID, LoaderStatus
import pandas as pd
from django.db.models import F
from exporter.views import is_in_jam_kritis


class Command(BaseCommand):
    def handle(self, *args, **options):
        date = "2024-09-01"
        data_loader = (
            LoaderStatus.objects.filter(report_date=date, unit__unit__startswith="X5")
            .annotate(equipment=F("unit__unit"))
            .values("equipment", "date", "timeStart", "standby_code", "hour")
        )

        df = pd.DataFrame(list(data_loader))
        df = df.sort_values(["equipment", "timeStart"]).reset_index(drop=True)

        s = 60 - df["timeStart"].max().second
        m = 29 - df["timeStart"].max().minute
        te = df["timeStart"].max() + pd.Timedelta(minutes=m, seconds=s)

        ids = df.index[df.standby_code == "S12"].tolist()

        for id in ids:
            if not is_in_jam_kritis(id, df):
                df.loc[id, "standby_code"] = "WH"

        df["group"] = (df["standby_code"] != df["standby_code"].shift()).cumsum()
        df = df.groupby(["equipment", "date", "hour", "group"], as_index=False).first()
        df = df.drop(columns="group")

        rit = (
            ritase.objects.filter(
                report_date=date, type__isnull=False, loader_id__unit__startswith="X5"
            )
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
            if d.time_full == 1:
                df.loc[
                    (df["standby_code"] == "WH")
                    & (df["hour"] == d.hour)
                    & (df["date"] == d.date)
                    & (df["equipment"] == d.equipment),
                    "standby_code",
                ] = f"WH {d.type}"
            else:
                x = []
                x = rdf[
                    (rdf["date"] == d.date)
                    & (rdf["equipment"] == d.equipment)
                    & (rdf["hour"] == d.hour)
                ]
                x = x.rename(columns={"time_full": "timeStart", "type": "standby_code"})
                x["standby_code"] = x["standby_code"].apply(lambda x: f"WH {x}")
                df = pd.concat([df, x])
        df = df.sort_values(["equipment", "timeStart"]).reset_index(drop=True)
        df["code_after"] = df["standby_code"].shift(-1)
        df.loc[df["standby_code"] == "WH", "standby_code"] = df["code_after"]
        df.drop(columns=["code_after"], inplace=True)
        df.to_csv("stb_perjam2.csv", sep=";")
