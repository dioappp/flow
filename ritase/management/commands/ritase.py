from django.core.management.base import BaseCommand
from stb_loader.models import loaderID
from ritase.models import truckID, ritase
from django.db import OperationalError, connections
from datetime import timedelta, datetime
import pytz
import pandas as pd


class Command(BaseCommand):
    def add_arguments(self, parser):
        def_time = datetime.now() - timedelta(hours=1)
        def_time = def_time - timedelta(minutes=def_time.minute)
        def_time = datetime.strftime(def_time, "%Y-%m-%d %H:%M")
        parser.add_argument(
            "--date",
            dest="date",
            action="store",
            type=str,
            default=def_time,
            help="Input tanggal dan jam data yang ingin diambil dengan format 'YYYY-MM-DD HH:MM'",
        )
        parser.add_argument(
            "--durasi", dest="durasi", action="store", type=float, default=1
        )

    def handle(self, *args, **options):
        dtime = options.get("date")
        dur = options.get("durasi")
        dtime_end = datetime.strptime(dtime, "%Y-%m-%d %H:%M") + timedelta(hours=dur)
        dtime_end = datetime.strftime(dtime_end, "%Y-%m-%d %H:%M")

        self.stdout.write(self.style.SUCCESS(f"{dtime}: Load data ritase"))
        tz = pytz.timezone("UTC")
        sql_load = f"""
        declare @start_date datetime, @enddate datetime
        set @start_date = '{dtime}'
        set @enddate = '{dtime_end}'

        SELECT 
            sl.id as 'load_id',  -- 0
            DATEADD("hh",8,sl.[time_full]) AS 'Time-Full', -- 1
            EQP.name as 'Truck', -- 2
            EQP1.name as 'Shovel',  -- 3
            enum.name as 'Material', -- 4
            loc.name as 'Blast', -- 5
            loc3.name as 'Grade' -- 6

        FROM [jmineops_reporting].[dbo].[shift_loads] sl
        FULL JOIN [jmineops_reporting].[dbo].[equipment] EQP ON EQP.id= sl.truck_id
        FULL JOIN [jmineops_reporting].[dbo].[equipment] EQP1 ON EQP1.id= sl.shovel_id
        FULL JOIN [jmineops_reporting].[dbo].[enum_tables] enum ON enum.id= sl.material_id
        FULL JOIN [jmineops_reporting].[dbo].[locations] loc ON loc.id= sl.blast_id
        FULL JOIN [jmineops_reporting].[dbo].[locations] loc3 ON loc3.id = loc.region_id
        WHERE sl.deleted_at is NULL AND dateadd("HH",8,time_full) between @start_date and @enddate
        ORDER BY time_full asc
        """
        sql_dump = f"""
        declare @start_date datetime, @enddate datetime
        set @start_date = '{dtime}'
        set @enddate = dateadd("mi",30,'{dtime_end}')

        SELECT 
            sl.id as 'load_id', -- 0
            dateadd("HH",8,time_empty) as 'time_empty', -- 1
            loc.name as 'dump_loc', -- 2
            case 
                when (loc.name like '%PERBAIKAN%' or loc.name like '%INPIT%' or loc.name like '%FRONT%' or loc.name like '%JALAN%' or loc.name like '%MAINT%' or loc.name like '%SUPP%' or loc.name like '%JLN%') and loc.name not like 'D%' then 'I' 
                when loc.name like '%TS%' and emat.name in ('OB','Blasted','Non-Blasted','Non-Blaste','Ripping','Soft DD','Blasted-2','Non-Blasted-2') then 'T'
                else (	case 
                    when emat.name in ('OB','Blasted','Non-Blasted','Non-Blaste','Ripping','Soft DD','Blasted-2','Non-Blasted-2') then 'O'
                    when emat.name in ('Coal','Coal-Blasted') then 'C' 
                    when emat.name in ('Top Soil') then 'TD' 
                    when emat.name in ('Mud') then 'M' 
                    -- when emat.name in ('Spoilled') then 'Spoilled' 
                    when emat.name in ('Dirty Coal','Spoilled') then 'G' 
                    else 'O' end) end material_id -- 3

        FROM [jmineops_reporting].[dbo].[shift_dumps] sd
        JOIN [jmineops_reporting].[dbo].[locations] loc ON loc.id=sd.dump_id 
        join [jmineops_reporting].[dbo].[shift_loads] sl on sl.dump_id = sd.id
        join [jmineops_reporting].[dbo].[enum_tables] emat on emat.id = sd.material_id
        WHERE sd.deleted_at is NULL AND dateadd("HH",8,time_empty) between @start_date and @enddate
        ORDER BY time_empty asc
        """
        try:
            cursor_jigsaw = connections["jigsaw"].cursor()
        except OperationalError as e:
            self.stderr.write(f"Operational Error: {e}")
            return

        cursor_jigsaw.execute(sql_load)
        data = pd.DataFrame(cursor_jigsaw.fetchall())
        data.columns = [
            "load_id",
            "time_full",
            "truck",
            "shovel",
            "material",
            "blast",
            "grade",
        ]

        cursor_jigsaw.execute(sql_dump)
        dumping = pd.DataFrame(cursor_jigsaw.fetchall())
        dumping.columns = ["load_id", "time_empty", "dump_loc", "material_id"]

        cursor_jigsaw.close()

        data = pd.merge(
            data, dumping, left_on="load_id", right_on="load_id", how="left"
        )

        dumping = dumping[~dumping["load_id"].isin(data["load_id"])]

        for _, d in data.iterrows():
            dt = d["time_full"].tz_localize("UTC")
            date = dt.date()
            hour = dt.hour
            if (6 < hour < 18) or ((hour == 6) and (dt.minute >= 30)):
                shift = 1
            else:
                shift = 2

            if (shift == 2) and (hour <= 6):
                report_date = date - timedelta(days=1)
            else:
                report_date = date

            loader, _ = loaderID.objects.get_or_create(unit=d["truck"])
            truck, _ = truckID.objects.get_or_create(jigsaw=d["shovel"])
            ritase.objects.update_or_create(
                load_id=d["load_id"],
                defaults={
                    "date": date,
                    "hour": hour,
                    "shift": shift,
                    "time_full": dt,
                    "truck_id": truck,
                    "loader_id": loader,
                    "material": d["material"],
                    "blast": d["blast"],
                    "grade": d["grade"],
                    "report_date": report_date,
                    "time_empty": (
                        None
                        if pd.isna(d["time_empty"])
                        else d["time_empty"].tz_localize("UTC")
                    ),
                    "dump_location": None if pd.isna(d["dump_loc"]) else d["dump_loc"],
                    "type": None if pd.isna(d["material_id"]) else d["material_id"],
                },
            )

        self.stdout.write(self.style.SUCCESS(f"{dtime}: Sukses memuat data loading"))
        self.stdout.write(self.style.SUCCESS(f"{dtime}: Memulai memuat data Dumping"))

        for _, d in dumping.iterrows():
            try:
                entry = ritase.objects.get(load_id=d["load_id"])
                entry.time_empty = d["time_empty"].tz_localize("UTC")
                entry.dump_location = d["dump_loc"]
                entry.type = d["material_id"]
                entry.save()
            except ritase.DoesNotExist:
                continue

        self.stdout.write(self.style.SUCCESS(f"{dtime}: Sukses memuat data Dumping"))
