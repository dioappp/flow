from django.core.management.base import BaseCommand
from django.db import connections
from hm.models import hmOperator, Operator
from datetime import datetime, timedelta
import pytz


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            "-d",
            dest="date",
            action="store",
            type=str,
            help="Input tanggal yang akan di ambil ex. '2024-06-30'",
        )
        parser.add_argument(
            "--shift",
            "-s",
            dest="shift",
            action="store",
            type=int,
            help="Input shift 1 atau 2",
        )

    def handle(self, *args, **options):
        date_str = options.get("date")
        date = datetime.strptime(date_str, "%Y-%m-%d")
        shift = options.get("shift")

        if shift == 1:
            ts = date_str + " 06:30"
            te = date_str + " 18:00"
        elif shift == 2:
            date = date + timedelta(days=1)
            date = date.strftime("%Y-%m-%d")
            ts = date_str + " 18:00"
            te = date + " 06:30"

        query = f"""
        declare @startdate datetime, @enddate datetime
        set @startdate = '{ts}'
        set @enddate = '{te}'

        exec [jmineops_reporting].[dbo].[mdi_login_hm] @startdate, @enddate
        """

        csr = connections["jigsaw"].cursor()
        csr.execute(query)
        data = csr.fetchall()

        tz = pytz.timezone("UTC")

        for d in data:
            nrp, _ = Operator.objects.get_or_create(
                NRP=d[2], defaults={"operator": d[1]}
            )
            hmOperator.objects.get_or_create(
                equipment=d[0],
                NRP=nrp,
                login_time=tz.localize(d[3]),
                defaults={
                    "logout_time": tz.localize(d[4]) if d[4] else None,
                    "hm_start": d[5],
                    "hm_end": d[6],
                },
            )
