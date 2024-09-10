from django.core.management.base import BaseCommand
from django.db import OperationalError, transaction, connections
from stb_loader.models import loaderID, LoaderStatus, ClusterLoader, Reason
from stb_loader.management.commands.stb_code import BDC
import stb_loader.management.commands.function as f
import pandas as pd
from pandas import DataFrame
from datetime import time, datetime, timedelta
import logging

db_logger = logging.getLogger("stb_loader")


class Command(BaseCommand):
    def main(self, dtime: str) -> tuple[DataFrame, DataFrame, DataFrame]:
        self.stdout.write(self.style.SUCCESS(f"{dtime}: Load data shift states Loader"))
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
            dateadd("HH",8,sfi.time) as 'Time Start' -- 0
            ,dateadd("HH",8,time_end) as 'Time End' -- 1
            ,eqp.name as 'Equipment' -- 2
            ,enum.name as 'Status' -- 3
            ,reason.descrip as 'Reason' -- 4
            ,loc.name as 'Lokasi' -- 5
            ,clust.region as 'Cluster' -- 6
            ,clust.pit as 'Pit' -- 7
            ,enum2.name as 'Equipment_Class' -- 8
        FROM [jmineops_reporting].[dbo].[states_for_interval](dateadd("HH",-8,@time_start),dateadd("HH",-8,@time_end)) sfi
        JOIN [jmineops_reporting].[dbo].[equipment] eqp ON eqp.id=sfi.equipment_id
        FULL JOIN [jmineops_reporting].[dbo].[enum_tables] enum ON enum.id = sfi.status_id
        FULL JOIN [jmineops_reporting].[dbo].[reasons] reason ON reason.id = sfi.reason_id
        FULL JOIN [jmineops_reporting].[dbo].[locations] loc ON loc.id = sfi.location_id
        FULL JOIN [jmineops_reporting].[dbo].[enum_tables] enum2 ON enum2.id = eqp.equipment_type_id
        left join jmineops_reporting.dbo.adaro_ust_pathjalur clust on clust.code = LEFT(loc.name,3)
        WHERE sfi.deleted_at is NULL AND sfi.id is not NULL and (eqp.name like 'X%%' or eqp.name like 'S%%' or eqp.name like 'E%%') 
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
        cluster_df = pd.DataFrame(
            columns=["Equipment", "Hour", "Date", "Cluster", "Pit"]
        )

        for i, d in enumerate(data):
            shift_states_df.loc[i, "Time Start"] = d[0]
            shift_states_df.loc[i, "Time End"] = d[1]
            shift_states_df.loc[i, "Equipment"] = d[2]
            shift_states_df.loc[i, "Reason"] = d[4]
            cluster_df.loc[i, "Hour"] = d[0]
            cluster_df.loc[i, "Date"] = d[0]
            cluster_df.loc[i, "Equipment"] = d[2]
            cluster_df.loc[i, "Cluster"] = d[6]
            cluster_df.loc[i, "Pit"] = d[7]

        cluster_df["Date"] = pd.to_datetime(cluster_df["Date"]).dt.date
        cluster_df["Hour"] = pd.to_datetime(cluster_df["Hour"]).dt.hour
        cluster_df = cluster_df.drop_duplicates().reset_index(drop=True)

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
        loader_df = shift_states_df.copy()

        self.stdout.write(self.style.SUCCESS(f"{dtime}: Load data shift activity"))

        # Shift Activity
        ac_sql = f"""
        declare @time_start datetime, @time_end datetime
        set @time_start = '{dtime}'
        set @time_end = DATEADD(hour, 1, @time_start)

        select 
            dateadd(hh, 8, afi.time_start) [Time Start], 
            dateadd(hh, 8, afi.time_end) [Time End],
            --afi.equipment_id,
            e.name Equipment,
            --afi.activity_id,
            --afi.shovel_id,
            eq.name Shovel,
            et.name Activity,
            datediff(ss, dateadd(hh, 8, afi.time_start), dateadd(hh, 8, afi.time_end)) durasi
        from activities_for_interval(dateadd(hh, -8, @time_start), dateadd(hh, -8, @time_end)) afi
        left join enum_tables et on et.id = afi.activity_id
        left join equipment e on e.id = afi.equipment_id
        left join equipment eq on eq.id = afi.shovel_id
        WHERE e.name LIKE 'D%' AND et.name IN ('spotting', 'loading', 'waiting')
        """

        try:
            cursor_jigsaw.execute(ac_sql)
            data = cursor_jigsaw.fetchall()
        except Exception as e:
            db_logger.error(f"Failed to execute query ac_ql: {e}")
            self.stderr.write(f"Failed to execute: {e}")
            raise

        shift_activity_df = pd.DataFrame(
            columns=["Time Start", "Time End", "Equipment", "Shovel", "Activity"]
        )
        i = 0
        for d in data:
            shift_activity_df.loc[i, "Time Start"] = d[0]
            shift_activity_df.loc[i, "Time End"] = d[1]
            shift_activity_df.loc[i, "Equipment"] = d[2]
            shift_activity_df.loc[i, "Shovel"] = d[3]
            shift_activity_df.loc[i, "Activity"] = d[4]
            i += 1
        shift_activity_df["Time Start"] = pd.to_datetime(
            shift_activity_df["Time Start"], format="%Y-%m-%d %H:%M:%S", utc=True
        )
        shift_activity_df["Time End"] = pd.to_datetime(
            shift_activity_df["Time End"], format="%Y-%m-%d %H:%M:%S", utc=True
        )

        cursor_jigsaw.close()

        self.stdout.write(self.style.SUCCESS(f"{dtime}: Load data MCR BD Loader"))

        bd_sql = """
        select bd_date, bd_time, rfu_date, rfu_time, unit_id, bd_code, problem, 
        case when `bd_status`(`shift_breakdown`.`problem`) = 'BA' then 'BUS' else `bd_status`(`shift_breakdown`.`problem`) end AS `problem_type` 
        from `shift_breakdown` 
        where 
        (
            (`shift_breakdown`.`deleted_at` is null) 
            and 
            `shift_breakdown`.`section` = 'PLD'
            and
            (
                (`shift_breakdown`.`temp_rfu_date` >= cast((now() + interval -(14) day) as date)) 
                or 
                (`shift_breakdown`.`rfu_date` = '0000-00-00') 
                or 
                (`shift_breakdown`.`rfu_date` = '')
                or 
                (`shift_breakdown`.`rfu_date` is null)
            )
        ) 
        order by `shift_breakdown`.`id` desc
        """
        # Data Breakdown
        try:
            cursor_mcr = connections["MCRBD"].cursor()
        except OperationalError as e:
            self.stderr.write(f"Operational Error: {e}")
            db_logger.error(f"Server MCRBD Error -{dtime}: {e}")
            return

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

        list_loader = loader_df.Equipment.unique()

        ts = shift_states_df["Time Start"].min()
        te = shift_states_df["Time End"].max()
        half_time = ts + pd.Timedelta(30, "minutes")
        hour = ts.hour

        isRestTime = ts.time() == time(12, 0) or ts.time() == time(0, 0)
        isFriday = ts.weekday() == 4  # 4 represents Friday in datetime module

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

        # for debbuging
        # shift_states_df.to_parquet(f'raw/ss-{str(ts)[:13]}.parquet.gzip')
        # shift_activity_df.to_parquet(f'raw/ac-{str(ts)[:13]}.parquet.gzip')
        # breakdown_df.to_parquet(f'raw/bd-{str(ts)[:13]}.parquet.gzip')

        data_change_shift = {
            "hours": [6, 17, 18],
            "Time Start": [
                ts + pd.Timedelta(minutes=25),
                ts + pd.Timedelta(minutes=55),
                ts,
            ],
            "Time End": [
                ts + pd.Timedelta(minutes=35),
                te,
                ts + pd.Timedelta(minutes=5),
            ],
            "Standby Code": "S6",
            "Rank": ranks["S6"],
        }
        change_shift_df = pd.DataFrame(data=data_change_shift)

        change_shift_df = change_shift_df[change_shift_df.hours == hour]

        # format output final data
        result = pd.DataFrame(
            columns=["Time Start", "Time End", "Equipment", "Standby Code", "remarks"]
        )

        for loader in list_loader:
            loader_bd = breakdown_df[breakdown_df["Equipment"] == loader]
            if loader_bd.empty or (loader_bd["durasi"] < 60).any():
                ss = (
                    loader_df[loader_df["Equipment"] == loader]
                    .sort_values("Time Start")
                    .reset_index(drop=True)
                    .copy()
                )

                s12 = f.generate_s12(loader, shift_activity_df, ts, te)

                if not s12.empty:
                    data = f.combine(loader, ss, s12)
                else:
                    data = ss
                    data["src"] = "ss"
                    data["remarks"] = None

                if not change_shift_df.empty and str(loader).startswith(
                    ("X1", "X2", "EX")
                ):
                    data = f.combine_cs(data, change_shift_df)

                if not loader_bd.empty:
                    # Data BD
                    data = f.combine_bd(data, loader_bd)

                data = data[data["Time Start"] != data["Time End"]].reset_index(
                    drop=True
                )

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
            else:
                if hour == 6:
                    loader_bd = f.split30min(loader_bd)
                result = pd.concat(
                    [
                        result,
                        loader_bd[
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
        return result, cluster_df, shift_states_df

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

        self.stdout.write(
            self.style.SUCCESS(
                f"{dtime}: Load data shift states, shift activity, dan MCR BD Loader"
            )
        )
        errors_data = []
        try:
            data, cluster, ss = self.main(dtime)
            clusters = {}
            with transaction.atomic():
                for i, row in cluster.iterrows():
                    try:
                        unit, _ = loaderID.objects.get_or_create(unit=row["Equipment"])
                        cluster, _ = ClusterLoader.objects.update_or_create(
                            unit=unit,
                            hour=row["Hour"],
                            date=row["Date"],
                            defaults={"cluster": row["Cluster"], "pit": row["Pit"]},
                        )
                        clusters[unit] = cluster
                    except Exception as e:
                        # Log detailed information about the error
                        db_logger.error(
                            f"Error inserting ClusterLoader row {i}: {e}, data: {row.to_dict()}"
                        )
                        raise  # Raise exception to trigger rollback for the entire transaction

                for i, row in data.iterrows():
                    try:
                        unit, _ = loaderID.objects.get_or_create(unit=row["Equipment"])
                        LoaderStatus.objects.update_or_create(
                            date=row["date"],
                            shift=row["shift"],
                            hour=row["hour"],
                            timeStart=row["Time Start"],
                            report_date=row["report_date"],
                            unit=unit,
                            location=clusters.get(unit, None),
                            defaults={
                                "standby_code": (
                                    None
                                    if pd.isna(row["Standby Code"])
                                    else row["Standby Code"]
                                ),
                                "remarks": row["remarks"],
                            },
                        )
                    except Exception as e:
                        ss = ss[ss["Equipment"] == row["Equipment"]]
                        ss = ss[ss["Standby Code"].isna()]
                        errors_data.append((i, e, ss.to_dict()))
                        raise  # Raise exception to trigger rollback for the entire transaction

                self.stdout.write(self.style.SUCCESS(f"{dtime}: Load data sukses"))
        except Exception as e:
            # Log the final exception that caused the transaction to fail
            if errors_data:
                for i, e, data in errors_data:
                    db_logger.error(f"Error inserting Row {i}: {e}, data: {data}")
            db_logger.error(f"stb loader failed - {dtime} => {e}")
            self.stdout.write(
                self.style.ERROR(f"{dtime}: Data load failed due to error")
            )
