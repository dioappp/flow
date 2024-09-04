from ritase.models import ritase, truckID
from stb_loader.models import loaderID, LoaderStatus
import pandas as pd
from django.db.models import F
from exporter.views import is_in_jam_kritis

data_loader = (
    LoaderStatus.objects.filter(report_date="2024-07-31")
    .annotate(equipment=F("unit__unit"))
    .values("equipment", "data", "timeStart", "standby_code")
)


df = pd.DataFrame(list(data_loader))
df = df.sort_values(["equipment", "date", "timeStart"]).reset_index(drop=True)

s = 60 - df["timeStart"].max().second
m = 29 - df["timeStart"].max().minute
te = df["timeStart"].max() + pd.Timedelta(minutes=m, seconds=s)

ids = df.index[df.standby_code == "S12"].tolist()

for id in ids:
    if not is_in_jam_kritis(id, df):
        df.loc[id, "standby_code"] = "WH"

df["group"] = (df["standby_code"] != df["standby_code"].shift()).cumsum()
df = df.groupby(["equipment", "group"], as_index=False).first()

rit = (
    ritase.objects.filter(report_date="2024-07-31", type__isnull=False)
    .annotate(loader=F("loader_id__unit"), hauler=F("truck_id__jigsaw"))
    .values("loader", "hauler", "type", "time_full")
)
rdf = pd.DataFrame(list(rit))
rdf = rdf.sort_values(["loader", "time_full"]).reset_index(drop=True)
rdf["group"] = (rdf["type"] != rdf["type"].shift()).cumsum()
rdf = rdf.groupby(["loader", "group"], as_index=False).first()
rdf = rdf.drop(columns="group")
