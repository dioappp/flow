from typing import Any
import pandas as pd
from pandas import DataFrame, Timestamp
import warnings

# Disable future warnings
warnings.simplefilter(action="ignore", category=FutureWarning)


def generate_s12(
    loader: str, act_df: DataFrame, ts: Timestamp, te: Timestamp
) -> DataFrame:
    trucks_act = (
        act_df[act_df["Shovel"] == loader]
        .sort_values(by=["Equipment", "Time Start"])
        .reset_index(drop=True)
    )

    trucks_act = trucks_act[trucks_act["Time Start"] != trucks_act["Time End"]].copy()

    trucks_act["groups"] = (
        trucks_act["Time Start"] != trucks_act["Time End"].shift()
    ).cumsum()
    trucks_act = trucks_act.groupby("groups", as_index=False).agg(
        {
            "Time Start": "first",
            "Time End": "last",
            "Equipment": "first",
            "Activity": ", ".join,
            "Shovel": "first",
        }
    )

    trucks_act = trucks_act.sort_values(["Time Start", "Time End"]).reset_index(
        drop=True
    )

    RUN = True
    while RUN:
        eval = ~(
            (trucks_act["Time Start"] > trucks_act["Time Start"].shift())
            & (trucks_act["Time End"] < trucks_act["Time End"].shift())
        )
        RUN = not all(eval)
        trucks_act = trucks_act[eval]

    trucks_act["groups"] = ~(trucks_act["Time Start"] <= trucks_act["Time End"].shift())
    trucks_act["groups"] = trucks_act["groups"].cumsum()
    trucks_act = trucks_act.groupby("groups", as_index=False).agg(
        {
            "Time Start": "min",
            "Time End": "max",
            "Equipment": ", ".join,
            "Activity": "first",
            "Shovel": "first",
        }
    )
    trucks_act["Activity"] = "WH"
    trucks_act = trucks_act.drop("groups", axis=1)
    trucks_act = fill_gap(trucks_act, ts, te, loader)  # data S12 only

    trucks_act = trucks_act.rename(columns={"Activity": "Standby Code"})
    trucks_act["Rank"] = 20
    trucks_act["src"] = "ac"
    trucks_act["remarks"] = None
    return trucks_act


def fill_gap(
    trucks_act: DataFrame, ts: Timestamp, te: Timestamp, loader: str
) -> DataFrame:
    filled_rows: list[dict[Any, Any]] = []
    if trucks_act.empty:
        filled_rows.append(
            {
                "Time Start": ts,
                "Time End": te,
                "Equipment": "DT",
                "Activity": "S12",
                "Shovel": loader,
            }
        )
        data_s12 = pd.DataFrame.from_dict(filled_rows)  # type: ignore
        return data_s12

    if trucks_act.loc[0, "Time Start"] > ts:  # type: ignore
        filled_rows.append(
            {
                "Time Start": ts,
                "Time End": trucks_act.loc[0, "Time Start"],
                "Equipment": "DT",
                "Activity": "S12",
                "Shovel": loader,
            }
        )

    for i in range(len(trucks_act) - 1):
        gap_start = trucks_act.loc[i, "Time End"]
        gap_end = trucks_act.loc[i + 1, "Time Start"]
        filled_rows.append(
            {
                "Time Start": gap_start,
                "Time End": gap_end,
                "Equipment": "DT",
                "Activity": "S12",
                "Shovel": loader,
            }
        )

    if trucks_act.loc[len(trucks_act) - 1, "Time End"] < te:  # type: ignore
        filled_rows.append(
            {
                "Time Start": trucks_act.loc[len(trucks_act) - 1, "Time End"],
                "Time End": te,
                "Equipment": "DT",
                "Activity": "S12",
                "Shovel": loader,
            }
        )

    data_s12 = pd.DataFrame.from_dict(filled_rows)  # type: ignore
    return data_s12


def combine(loader: str, ss: DataFrame, s12: DataFrame) -> DataFrame:
    ss = ss[["Time Start", "Time End", "Equipment", "Standby Code", "Rank"]].copy()
    ss[["src", "remarks"]] = ["ss", None]

    if s12.empty:
        data = ss
        return data

    s12 = s12[["Time Start", "Time End", "Equipment", "Standby Code", "Rank"]].copy()
    s12[["src", "remarks"]] = ["act", None]

    s12_splited = split(s12, ss)

    data = summarize(loader, s12_splited, ss)
    return data


def summarize(loader: str, s12: DataFrame, ss: DataFrame) -> DataFrame:
    # Initialize an empty list to store the result rows
    result_rows = []

    # Iterate over s12 and check for overlaps with ss
    for (
        _,
        row_s12,
    ) in s12.iterrows():
        # Find overlapping intervals in ss
        overlaps_df = ss[
            (ss["Time Start"] < row_s12["Time End"])
            & (ss["Time End"] > row_s12["Time Start"])
            & (ss["Rank"] >= row_s12["Rank"])
        ]

        for i, row_ss in overlaps_df.iterrows():
            # Split ss's interval if necessary
            if row_s12["Time Start"] > row_ss["Time Start"]:
                result_rows.append(
                    {
                        "Time Start": row_ss["Time Start"],
                        "Time End": row_s12["Time Start"],
                        "Equipment": row_ss["Equipment"],
                        "Standby Code": row_ss["Standby Code"],
                        "Rank": row_ss["Rank"],
                        "src": row_ss["src"],
                        "remarks": row_ss["remarks"],
                    }
                )

            # Insert s12's interval
            result_rows.append(
                {
                    "Time Start": max(row_s12["Time Start"], row_ss["Time Start"]),
                    "Time End": min(row_s12["Time End"], row_ss["Time End"]),
                    "Equipment": row_s12["Equipment"],
                    "Standby Code": row_s12["Standby Code"],
                    "Rank": row_s12["Rank"],
                    "src": row_s12["src"],
                    "remarks": row_s12["remarks"],
                }
            )

            # Update ss's interval if necessary
            if row_s12["Time End"] < row_ss["Time End"]:
                ss.at[i, "Time Start"] = row_s12["Time End"]
            else:
                ss.drop(i, inplace=True)
    # Append remaining intervals from df1 that had no overlap or were not completely covered by df2
    result_rows.extend(ss.to_dict("records"))

    # Convert result_rows to DataFrame and sort by time start
    output_df = (
        pd.DataFrame(result_rows).sort_values("Time Start").reset_index(drop=True)
    )
    output_df["Equipment"] = loader
    output_df["src"] = "combined"
    return output_df


def split(s12: DataFrame, ss: DataFrame) -> DataFrame:
    column_name = ss.columns.values
    s12_splited = pd.DataFrame(columns=column_name)

    for _, row_ss in ss.iterrows():
        for _, row_s12 in s12.iterrows():
            if (row_s12["Time Start"] < row_ss["Time End"]) and (
                row_s12["Time End"] > row_ss["Time Start"]
            ):
                start_time = max(row_s12["Time Start"], row_ss["Time Start"])
                end_time = min(row_s12["Time End"], row_ss["Time End"])

                new_row = pd.DataFrame(
                    {"Time Start": [start_time], "Time End": [end_time]}
                )
                s12_splited = pd.concat([s12_splited, new_row], ignore_index=True)

    s12_splited["Equipment"] = s12.loc[0, "Equipment"]
    s12_splited["Standby Code"] = "S12"
    s12_splited["Rank"] = 20
    s12_splited["src"] = "ac"
    s12_splited["remarks"] = None
    s12_splited.sort_values("Time Start").reset_index(drop=True)
    return s12_splited


def combine_cs(df: DataFrame, cs: DataFrame) -> DataFrame:
    intersect_in_start = (df["Time Start"] <= cs["Time Start"].iloc[0]) & (
        cs["Time Start"].iloc[0] <= df["Time End"]
    )
    idx_in_start = df.index[intersect_in_start].to_list()

    intersect_in_end = (df["Time Start"] <= cs["Time End"].iloc[0]) & (
        cs["Time End"].iloc[0] <= df["Time End"]
    )
    idx_in_end = df.index[intersect_in_end].to_list()

    intersect_inside = (
        (cs["Time Start"].iloc[0] <= df["Time Start"])
        & (df["Time Start"] <= cs["Time End"].iloc[0])
        & (cs["Time Start"].iloc[0] <= df["Time End"])
        & (df["Time End"] <= cs["Time End"].iloc[0])
    )
    idx_inside = df.index[intersect_inside].to_list()
    l = len(df)

    if idx_in_start == idx_in_end:
        row = df.loc[idx_in_start].copy()
        df.loc[idx_in_start, "Time End"] = cs["Time Start"].iloc[0]
        df = pd.concat([df, row]).reset_index(drop=True)
        df.loc[l, "Time Start"] = cs["Time Start"].iloc[0]
        df.loc[l, "Time End"] = cs["Time End"].iloc[0]
        df.loc[l, "Standby Code"] = cs["Standby Code"].iloc[0]
        df.loc[l, "Rank"] = cs["Rank"].iloc[0]
        df = pd.concat([df, row]).reset_index(drop=True)
        df.loc[l + 1, "Time Start"] = cs["Time End"].iloc[0]
        return df.sort_values("Time Start").reset_index(drop=True)

    if intersect_in_start.any():
        df.loc[idx_in_start, "Time End"] = cs["Time Start"].iloc[0]
        row = df.loc[idx_in_start].copy()
        df = pd.concat([df, row]).reset_index(drop=True)
        df.loc[l, "Time Start"] = cs["Time Start"].iloc[0]
        df.loc[l, "Time End"] = cs["Time End"].iloc[0]
        df.loc[l, "Standby Code"] = cs["Standby Code"].iloc[0]
        df.loc[l, "Rank"] = cs["Rank"].iloc[0]

    if intersect_in_end.any():
        df.loc[idx_in_end, "Time Start"] = cs["Time End"].iloc[0]

    if intersect_inside.any():
        df = df.drop(index=idx_inside)

    return df.sort_values("Time Start").reset_index(drop=True)


def combine_bd(ss: DataFrame, bd: DataFrame) -> DataFrame:
    data = pd.concat([ss, bd], axis=0)
    data = data.sort_values("Time Start").reset_index(drop=True)
    column_name = ss.columns.values
    result = pd.DataFrame(columns=column_name)

    for _, row in data.iterrows():
        l = len(result)

        if result.empty:
            result.loc[0] = row
            continue

        if row["src"] == result.loc[l - 1, "src"]:
            result.loc[l] = row
            continue

        if row["Rank"] == 1:
            if row["Time End"] > result.loc[l - 1, "Time End"]:
                result.loc[l] = row
                continue
            else:  # row['Time End'] < result.loc[l-1,'Time End']:
                result.loc[l] = row
                result.loc[l + 1] = result.loc[l - 1]
                result.loc[l + 1, "Time Start"] = row["Time End"]
                continue

        if (row["Time Start"] < result.loc[l - 1, "Time End"]) and (
            row["Time End"] > result.loc[l - 1, "Time End"]
        ):
            result.loc[l] = row
            result.loc[l, "Time Start"] = result.loc[l - 1, "Time End"]
            continue

    result = adjustTimeEnd(result)

    groups = (result["Standby Code"] != result["Standby Code"].shift()).cumsum()
    result = result.groupby(groups, as_index=False).agg(
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
    result["src"] = "combined"
    return result


def adjustTimeEnd(data: DataFrame) -> DataFrame:
    # Update 'Time End' to match 'Time Start' of the next row
    len_data = len(data)
    if len_data > 1:
        data.loc[0 : len_data - 2, "Time End"] = data.loc[
            1:len_data, "Time Start"
        ].values
        data.loc[len_data - 1, "Time End"] = data.loc[0, "Time Start"] + pd.Timedelta(1, "h")  # type: ignore
    return data


def split30min(data: DataFrame) -> DataFrame:
    split_time = data["Time Start"].min() + pd.Timedelta(30, "minutes")
    column_name = data.columns.values
    result = pd.DataFrame(columns=column_name)
    for _, row in data.iterrows():
        l = len(result)
        if row["Time Start"] < split_time <= row["Time End"]:
            new_row = row.copy()
            row["Time End"] = split_time
            new_row["Time Start"] = split_time
            result.loc[l] = row
            result.loc[l + 1] = new_row
        else:
            result.loc[l] = row

    return result


def statusBDC(remark: str) -> str:
    C1 = [
        "eng",
        "ps",
        "low power",
        "service",
        "err",
        "e 0",
        "e-",
        "mati mendadak",
        "fip",
        "radiator",
        "start",
        "overh",
        "v-belt",
        "van belt",
        "midlife",
        "mid life",
    ]
    C2 = ["tran"]
    C3 = ["spro", "final", "trac", "undercar"]
    C4 = ["tyre", "tire", "suspensi", "r1", "r2", "r3", "r4"]
    C5 = [
        "ster",
        "drol",
        "motor",
        "hyd",
        "dum",
        "cyl",
        "bo",
        "hose cyl",
        "cil",
        "hose bo",
    ]
    C6 = ["lamp", "ele", "bat", "radio", "fuse", "short", "power window"]
    C8 = ["brake", "rem", "retar"]
    C9 = ["acci", "teet", "ac", "cut", "fuel", "autolube", "bucket"]

    remark = remark.lower()
    if any(criterion in remark for criterion in C1):
        return "C1"
    elif any(criterion in remark for criterion in C2):
        return "C2"
    elif any(criterion in remark for criterion in C3):
        return "C3"
    elif any(criterion in remark for criterion in C4):
        return "C4"
    elif any(criterion in remark for criterion in C5):
        return "C5"
    elif any(criterion in remark for criterion in C6):
        return "C6"
    elif any(criterion in remark for criterion in C8):
        return "C8"
    elif any(criterion in remark for criterion in C9):
        return "C9"
    else:
        return "C1"


def BDstatus(remark: str) -> str:
    B5 = ["acc", "den", "insi"]
    BS = [
        "g o h",
        "goh",
        "overhoul",
        "back",
        "serv",
        "mid",
        "ps",
        "sch",
        "ovh",
        "o v h",
    ]

    remark = remark.lower()
    if any(criterion in remark for criterion in BS):
        return "BS"
    elif any(criterion in remark for criterion in B5):
        return "B5"
    else:
        return "B3"
