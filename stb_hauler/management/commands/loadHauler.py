from django.core.management.base import BaseCommand
from django.db import OperationalError, connections, transaction
from stb_hauler.models import HaulerStatus
from ritase.models import truckID
import stb_loader.management.commands.function as f
import pandas as pd
from datetime import time, datetime, timedelta
from stb_loader.management.commands.stb_code import BDC
import logging
from stb_loader.models import Reason

db_logger = logging.getLogger("stb_hauler")


class Command(BaseCommand):
    def main(self, dtime: str) -> tuple[pd.DataFrame, pd.DataFrame]:
        self.stdout.write(self.style.SUCCESS(f"{dtime}: Load data shift states Hauler"))
        # Fetch all reasons with their related standby codes
        reasons = Reason.objects.select_related("code").all()

        # Separate the dictionaries for standby code and rank
        standby_codes = {reason.reason: reason.code.code for reason in reasons}
        ranks = {reason.code.code: reason.code.rank for reason in reasons}

        ss_sql = f"""
        declare @time_start datetime, @time_end datetime
        set @time_start = '{dtime}'
        set @time_end = DATEADD(hour, 1, @time_start)
        SELECT 
            dateadd("HH",8,sfi.time) as 'Time_Start'
            ,dateadd("HH",8,time_end) as 'Time_End'
            ,eqp.name as 'Equipment'
            ,enum.name as 'Status'
            ,reason.descrip as 'Reason'
            ,loc.name as 'Lokasi'
            ,reg.name as 'Region'
            ,comment
            ,enum2.name as 'Equipment_Class' 
            ,(CAST(sfi.seconds as float)/60) as 'Durasi_Menit'
        FROM [jmineops_reporting].[dbo].[states_for_interval](dateadd("HH",-8,@time_start),dateadd("HH",-8,@time_end)) sfi
        JOIN [jmineops_reporting].[dbo].[equipment] eqp ON eqp.id=sfi.equipment_id
        FULL JOIN [jmineops_reporting].[dbo].[enum_tables] enum ON enum.id = sfi.status_id
        FULL JOIN [jmineops_reporting].[dbo].[reasons] reason ON reason.id = sfi.reason_id
        FULL JOIN [jmineops_reporting].[dbo].[locations] loc ON loc.id = sfi.location_id
        FULL JOIN [jmineops_reporting].[dbo].[locations] reg ON loc.region_id = reg.id
        FULL JOIN [jmineops_reporting].[dbo].[locations] blast ON blast.id = sfi.blast_id
        FULL JOIN [jmineops_reporting].[dbo].[enum_tables] enum2 ON enum2.id = eqp.equipment_type_id
        WHERE sfi.deleted_at is NULL AND sfi.id is not NULL and eqp.name like 'D%%'
        """
        # Shift States
        try:
            cursor_jigsaw = connections["jigsaw"].cursor()
        except OperationalError as e:
            db_logger.error(f"Server Jigsaw Error -{dtime}: {e}")
            self.stderr.write(f"Operational Error: {e}")
            raise

        try:
            cursor_jigsaw.execute(ss_sql)
            data = cursor_jigsaw.fetchall()
        except Exception as e:
            db_logger.error(f"Failed to execute query ss_ql: {e}")
            self.stderr.write(f"Failed to execute: {e}")
            raise

        shift_states_df = pd.DataFrame(
            columns=["Time Start", "Time End", "Equipment", "Reason"]
        )

        for i, d in enumerate(data):
            shift_states_df.loc[i, "Time Start"] = d[0]
            shift_states_df.loc[i, "Time End"] = d[1]
            shift_states_df.loc[i, "Equipment"] = d[2]
            shift_states_df.loc[i, "Reason"] = d[4]

        shift_states_df["Time Start"] = pd.to_datetime(
            shift_states_df["Time Start"], format="%Y-%m-%d %H:%M:%S", utc=True
        )
        shift_states_df["Time End"] = pd.to_datetime(
            shift_states_df["Time End"], format="%Y-%m-%d %H:%M:%S", utc=True
        )
        # fill null reason
        shift_states_df["Reason"] = shift_states_df["Reason"].fillna("Production")
        # ambil loader aja
        shift_states_df["Standby Code"] = shift_states_df["Reason"].map(standby_codes)
        shift_states_df["Rank"] = shift_states_df["Standby Code"].map(ranks)
        hauler_df = shift_states_df.copy()

        list_hauler = hauler_df.Equipment.unique()

        ts = shift_states_df["Time Start"].min()
        te = shift_states_df["Time End"].max()
        half_time = ts + pd.Timedelta(30, "minutes")

        hour = ts.hour

        isFriday = ts.weekday() == 4  # 4 represents Friday in datetime module
        isRestTime = ts.time() == time(12, 0) or ts.time() == time(0, 0)

        self.stdout.write(self.style.SUCCESS(f"{dtime}: Load data MCR BD Hauler"))
        # Data Breakdown
        bd_sql = """
        select bd_date, bd_time, rfu_date, rfu_time, unit_id, bd_code, problem, 
        case when `bd_status`(`shift_breakdown`.`problem`) = 'BA' then 'BUS' else `bd_status`(`shift_breakdown`.`problem`) end AS `problem_type` 
        from `shift_breakdown` 
        where 
        (
            (`shift_breakdown`.`deleted_at` is null) 
            and 
            `shift_breakdown`.`section` = 'PHW'
            and
            (
                (`shift_breakdown`.`temp_rfu_date` >= cast((now() + interval -(14) day) as date)) 
                or 
                (`shift_breakdown`.`rfu_date` = '0000-00-00') 
                or 
                (`shift_breakdown`.`rfu_date` = '')
            )
        ) 
        order by `shift_breakdown`.`id` desc
        """
        try:
            cursor_mcr = connections["MCRBD"].cursor()
        except OperationalError as e:
            self.stderr.write(f"Operational Error: {e}")
            db_logger.error(f"Server MCRBD Error -{dtime}: {e}")
            raise

        try:
            cursor_mcr.execute(bd_sql)
            data = cursor_mcr.fetchall()
        except Exception as e:
            db_logger.error(f"Failed to execute query bd_sql: {e}")
            self.stderr.write(f"Failed to execute: {e}")
            raise

        breakdown_df = pd.DataFrame(
            columns=[
                "Time Start",
                "Time End",
                "Equipment",
                "bd_code",
                "remarks",
                "Standby Code",
            ]
        )
        for i, d in enumerate(data):
            a = str(f"{d[0]} {d[1]}")
            if d[2] != "":
                b = str(f"{d[2]} {d[3]}")
            else:
                b = ""
            breakdown_df.loc[i + 1, "Time Start"] = a
            breakdown_df.loc[i + 1, "Time End"] = b
            breakdown_df.loc[i + 1, "Equipment"] = d[4]
            breakdown_df.loc[i + 1, "bd_code"] = d[5]
            breakdown_df.loc[i + 1, "remarks"] = d[6]
            breakdown_df.loc[i + 1, "Standby Code"] = d[7]
        breakdown_df["Time Start"] = pd.to_datetime(
            breakdown_df["Time Start"], format="%Y-%m-%d %H:%M", utc=True
        )
        breakdown_df["Time End"] = pd.to_datetime(
            breakdown_df["Time End"], format="%Y-%m-%d %H:%M", utc=True
        )
        cursor_mcr.close()

        breakdown_df = breakdown_df[~(breakdown_df["Time Start"] > te)]
        breakdown_df = breakdown_df[~(breakdown_df["Time End"] < ts)]
        breakdown_df["Time Start"] = breakdown_df["Time Start"].clip(lower=ts)
        breakdown_df["Time End"] = breakdown_df["Time End"].fillna(te)
        breakdown_df["Time End"] = breakdown_df["Time End"].clip(upper=te)
        breakdown_df["durasi"] = breakdown_df["Time End"] - breakdown_df["Time Start"]
        breakdown_df["durasi"] = pd.to_timedelta(breakdown_df["durasi"])
        breakdown_df["durasi"] = breakdown_df["durasi"].dt.total_seconds() / 60
        breakdown_df = breakdown_df[breakdown_df["durasi"] > 0]

        breakdown_df["src"] = "bd"
        breakdown_df["Rank"] = 1

        breakdown_df["bd_code"] = breakdown_df["bd_code"].map(BDC)
        breakdown_df["statusBDC"] = breakdown_df["remarks"].apply(f.statusBDC)
        breakdown_df["statusBDC"] = breakdown_df["bd_code"].combine_first(
            breakdown_df["statusBDC"]
        )
        breakdown_df["BD Status"] = breakdown_df["remarks"].apply(f.BDstatus)
        breakdown_df["remarks"] = breakdown_df[
            ["remarks", "BD Status", "statusBDC"]
        ].apply(lambda x: ";".join(x.dropna()), axis=1)
        breakdown_df = breakdown_df.drop(columns=["BD Status", "statusBDC"])

        result = pd.DataFrame(
            columns=["Time Start", "Time End", "Equipment", "Standby Code", "remarks"]
        )

        for hauler in list_hauler:
            hauler_bd = breakdown_df[breakdown_df["Equipment"] == hauler]
            if hauler_bd.empty or (hauler_bd["durasi"] < 60).any():
                data = (
                    hauler_df[hauler_df["Equipment"] == hauler]
                    .sort_values("Time Start")
                    .reset_index(drop=True)
                    .copy()
                )

                data["src"] = "ss"
                data["remarks"] = None

                if not hauler_bd.empty:
                    # Data BD
                    data = f.combine_bd(data, hauler_bd)

                data.loc[
                    data["Standby Code"].astype(str).str.contains("SS", case=True),
                    ["Standby Code", "Rank"],
                ] = ["WH", 20]

                if hour == 6:
                    data = f.split30min(data)

                if isFriday and hour == 12:
                    data.loc[data["Rank"] > 3, ["Standby Code", "Rank"]] = ["S8", 3]
                    group = (
                        data["Standby Code"] != data["Standby Code"].shift()
                    ).cumsum()
                    data = data.groupby(group, as_index=False).agg(
                        {
                            "Time Start": "first",
                            "Time End": "last",
                            "Equipment": "first",
                            "Standby Code": "first",
                            "Rank": "first",
                            "src": "first",
                            "remarks": "first",
                        }
                    )

                if isFriday and hour == 11:
                    data = f.split30min(data)
                    conditions = (
                        (data["Time Start"] >= half_time) & (data["Rank"] > 5)
                    ) | (
                        (data["Time Start"] >= half_time)
                        & (data["Standby Code"] == "S8")
                    )
                    data.loc[conditions, ["Standby Code", "Rank"]] = ["S5A", 5]
                    group = (
                        data["Standby Code"] != data["Standby Code"].shift()
                    ).cumsum()
                    data = data.groupby(group, as_index=False).agg(
                        {
                            "Time Start": "first",
                            "Time End": "last",
                            "Equipment": "first",
                            "Standby Code": "first",
                            "Rank": "first",
                            "src": "first",
                            "remarks": "first",
                        }
                    )

                if isFriday and hour == 13:
                    data = f.split30min(data)
                    conditions = (
                        (data["Time Start"] < half_time) & (data["Rank"] > 5)
                    ) | (
                        (data["Time Start"] < half_time)
                        & (data["Standby Code"] == "S8")
                    )
                    data.loc[conditions, ["Standby Code", "Rank"]] = ["S5A", 5]
                    group = (
                        data["Standby Code"] != data["Standby Code"].shift()
                    ).cumsum()
                    data = data.groupby(group, as_index=False).agg(
                        {
                            "Time Start": "first",
                            "Time End": "last",
                            "Equipment": "first",
                            "Standby Code": "first",
                            "Rank": "first",
                            "src": "first",
                            "remarks": "first",
                        }
                    )

                if isRestTime and (not isFriday or hour == 0):
                    data.loc[data["Rank"] > 5, ["Standby Code", "Rank"]] = ["S5A", 5]
                    data = data.groupby("Standby Code", as_index=False).agg(
                        {
                            "Time Start": "first",
                            "Time End": "last",
                            "Equipment": "first",
                            "Standby Code": "first",
                            "Rank": "first",
                            "src": "first",
                            "remarks": "first",
                        }
                    )

                result = pd.concat(
                    [
                        result,
                        data[
                            [
                                "Time Start",
                                "Time End",
                                "Equipment",
                                "Standby Code",
                                "remarks",
                            ]
                        ],
                    ],
                    axis=0,
                )
                result = result[result["Time Start"] != result["Time End"]].reset_index(
                    drop=True
                )
            else:
                if hour == 6:
                    hauler_bd = f.split30min(hauler_bd)
                result = pd.concat(
                    [
                        result,
                        hauler_bd[
                            [
                                "Time Start",
                                "Time End",
                                "Equipment",
                                "Standby Code",
                                "remarks",
                            ]
                        ],
                    ],
                    axis=0,
                )

        result = result.dropna(how="all").reset_index(drop=True)
        result["date"] = pd.to_datetime(result["Time Start"]).dt.date
        result["hour"] = hour
        result["shift"] = 1 if (6 <= hour < 18) else 2
        if hour == 6:
            cond = result["Time Start"] < half_time
            result.loc[cond, "shift"] = 2

        result["durasi"] = result["Time End"] - result["Time Start"]
        result["durasi"] = pd.to_timedelta(result["durasi"]).dt.total_seconds() / 60
        result["report_date"] = result["date"]
        cond = (result["shift"] == 2) & (result["hour"] <= 6)
        result.loc[cond, "report_date"] = result["date"] - pd.Timedelta(days=1)
        return result, shift_states_df

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

    def handle(self, *args, **options):
        dtime = options.get("date")
        errors_data = []

        try:
            data, ss = self.main(dtime)
            with transaction.atomic():
                for i, row in data.iterrows():
                    try:
                        unit, _ = truckID.objects.get_or_create(jigsaw=row["Equipment"])
                        HaulerStatus.objects.update_or_create(
                            date=row["date"],
                            shift=row["shift"],
                            hour=row["hour"],
                            timeStart=row["Time Start"],
                            unit=unit,
                            report_date=row["report_date"],
                            defaults={
                                "standby_code": (
                                    None
                                    if pd.isna(row["Standby Code"])
                                    else row["Standby Code"]
                                ),
                                "remarks": row["remarks"],
                            },
                        )
                        # print(f'imported {i+1}/{len(data)}')
                    except Exception as e:
                        ss = ss[ss["Equipment"] == row["Equipment"]]
                        ss = ss[ss["Standby Code"].isna()]
                        errors_data.append((i, e, ss.to_dict()))
                        raise  # Raise exception to trigger rollback for the entire transaction
        except Exception as e:
            # Log the final exception that caused the transaction to fail
            if errors_data:
                for i, e, data in errors_data:
                    db_logger.error(f"Error inserting Row {i}: {e}, data: {data}")
            db_logger.error(f"stb hauler failed - {dtime} => {e}")
            self.stdout.write(
                self.style.ERROR(f"{dtime}: Data load failed due to error")
            )
