from django.core.management import BaseCommand
from django.db.models import OuterRef, Subquery
from django.db.models.functions import Coalesce
from hm.models import hmOperator
from ritase.models import material, ritase, cek_ritase
import math
import pandas as pd
from datetime import datetime, timedelta, time


class Command(BaseCommand):
    def add_arguments(self, parser):
        now = datetime.now()
        start_time = datetime.combine(now.date(), time(6, 30))
        end_time = datetime.combine(now.date(), time(18, 0))

        if start_time < now < end_time:
            date = (now - timedelta(days=1)).strftime("%Y-%m-%d")
            shift = 2
        else:
            date = now.strftime("%Y-%m-%d")
            shift = 1

        parser.add_argument(
            "--date",
            "-d",
            dest="date",
            default=date,
            action="store",
            type=str,
            help="Input tanggal yang akan di ambil ex. '2024-06-30'",
        )
        parser.add_argument(
            "--shift",
            "-s",
            dest="shift",
            default=shift,
            action="store",
            type=int,
            help="Input shift 1 atau 2",
        )

    def handle(self, *args, **options):
        date = options.get("date")
        shift = options.get("shift")

        subquery_hauler = hmOperator.objects.filter(
            equipment=OuterRef("truck_id__jigsaw"),
            login_time__lte=OuterRef("time_full"),
            logout_time__gte=OuterRef("time_full"),
        ).values("id")[:1]

        subquery_loader = hmOperator.objects.filter(
            equipment=OuterRef("loader_id__unit"),
            login_time__lte=OuterRef("time_full"),
            logout_time__gte=OuterRef("time_full"),
        ).values("id")[:1]

        data = (
            ritase.objects.filter(
                deleted_at__isnull=True, report_date=date, shift=shift
            )
            .annotate(
                operator_hauler_id=Coalesce(
                    Subquery(subquery_hauler.values("id")), None
                ),
                operator_loader_id=Coalesce(
                    Subquery(subquery_loader.values("id")), None
                ),
            )
            .values(
                "truck_id__jigsaw",
                "operator_hauler_id",
                "time_full",
                "loader_id__unit",
                "operator_loader_id",
                "type",
                "hour",
                "report_date",
                "shift",
            )
        )
        df = pd.DataFrame(list(data))
        df = df.rename(
            columns={"loader_id__unit": "loader", "truck_id__jigsaw": "hauler"}
        )
        result = df.groupby(
            [
                "hauler",
                "operator_hauler_id",
                "loader",
                "operator_loader_id",
                "type",
                "hour",
                "report_date",
                "shift",
            ],
            as_index=False,
            dropna=False,
        ).agg({"time_full": "count"})
        result = (
            result.pivot(
                index=[
                    "report_date",
                    "shift",
                    "hauler",
                    "operator_hauler_id",
                    "loader",
                    "operator_loader_id",
                    "type",
                ],
                columns="hour",
                values="time_full",
            )
            .fillna(0)
            .astype(int)
        )
        result = result.sort_values("hauler").reset_index()

        for i, d in result.iterrows():
            try:
                code = material.objects.get(code=d["type"])
            except:
                code = None

            cek_ritase.objects.create(
                date=d["report_date"],
                shift=d["shift"],
                hauler=d["hauler"],
                operator_hauler_id=(
                    d["operator_hauler_id"]
                    if not math.isnan(d["operator_hauler_id"])
                    else None
                ),
                loader=d["loader"],
                operator_loader_id=(
                    d["operator_loader_id"]
                    if not math.isnan(d["operator_loader_id"])
                    else None
                ),
                code_material=code,
                a=(
                    d.get(6, 0) if d["shift"] == 1 else d.get(18, 0)
                ),  # 06.30 - 07.00 | 18.00 - 19.00
                b=(
                    d.get(7, 0) if d["shift"] == 1 else d.get(19, 0)
                ),  # 07.00 - 08.00 | 19.00 - 20.00
                c=(
                    d.get(8, 0) if d["shift"] == 1 else d.get(20, 0)
                ),  # 08.00 - 09.00 | 20.00 - 21.00
                d=(
                    d.get(9, 0) if d["shift"] == 1 else d.get(21, 0)
                ),  # 09.00 - 10.00 | 21.00 - 22.00
                e=(
                    d.get(10, 0) if d["shift"] == 1 else d.get(22, 0)
                ),  # 10.00 - 11.00 | 22.00 - 23.00
                f=(
                    d.get(11, 0) if d["shift"] == 1 else d.get(23, 0)
                ),  # 11.00 - 12.00 | 23.00 - 00.00
                g=(
                    d.get(12, 0) if d["shift"] == 1 else d.get(0, 0)
                ),  # 12.00 - 13.00 | 00.00 - 01.00
                h=(
                    d.get(13, 0) if d["shift"] == 1 else d.get(1, 0)
                ),  # 13.00 - 14.00 | 01.00 - 02.00
                i=(
                    d.get(14, 0) if d["shift"] == 1 else d.get(2, 0)
                ),  # 14.00 - 15.00 | 02.00 - 03.00
                j=(
                    d.get(15, 0) if d["shift"] == 1 else d.get(3, 0)
                ),  # 15.00 - 16.00 | 03.00 - 04.00
                k=(
                    d.get(16, 0) if d["shift"] == 1 else d.get(4, 0)
                ),  # 16.00 - 17.00 | 04.00 - 05.00
                l=(
                    d.get(17, 0) if d["shift"] == 1 else d.get(5, 0)
                ),  # 17.00 - 18.00 | 05.00 - 06.00
                m=0 if d["shift"] == 1 else d.get(6, 0),  #                06.00 - 06.30
            )
