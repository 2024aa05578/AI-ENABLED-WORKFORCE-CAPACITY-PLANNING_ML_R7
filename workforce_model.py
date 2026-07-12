import math
import pandas as pd


def calculate_workforce(
    df,
    growth_parameters,
    attrition_parameters,
    productive_hours,
    working_days,
    target_utilization,
):
    results = []

    annual_capacity = productive_hours * working_days * 12
    effective_capacity = annual_capacity * target_utilization / 100

    for _, row in df.iterrows():
        region = row["Region"]
        product = row["Product"]

        growth = growth_parameters.get(
            region,
            {}
        ).get(
            product,
            {
                "BAU": 0,
                "DC": 0
            }
        )

        bau_growth = growth["BAU"]
        dc_growth = growth["DC"]
        total_growth = bau_growth + dc_growth

        attrition = attrition_parameters.get(
            product,
            8
        )

        current_hours = (
            row["Breakdown_WO"] * row["Breakdown_Hrs"]
            + row["PM_WO"] * row["PM_Hrs"]
            + row["Startup_WO"] * row["Startup_Hrs"]
        )

        bau_future_hours = current_hours * (
            1 + bau_growth / 100
        )

        dc_incremental_hours = current_hours * (
            dc_growth / 100
        )

        combined_future_hours = current_hours * (
            1 + total_growth / 100
        )

        current_required_engineers = current_hours / effective_capacity
        bau_required_engineers = bau_future_hours / effective_capacity
        dc_incremental_engineers = dc_incremental_hours / effective_capacity
        combined_required_engineers = combined_future_hours / effective_capacity

        available_engineers = row["Current_SE"] * (
            1 - attrition / 100
        )

        bau_gap = bau_required_engineers - available_engineers
        combined_gap = combined_required_engineers - available_engineers

        results.append(
            {
                "Region": region,
                "Product": product,
                "BAU Growth %": bau_growth,
                "DC Growth %": dc_growth,
                "Total Growth %": total_growth,
                "Attrition %": attrition,
                "Productive Hrs/Day": productive_hours,
                "Working Days/Month": working_days,
                "Utilization %": target_utilization,
                "Annual Capacity": round(annual_capacity),
                "Effective Capacity": round(effective_capacity),
                "Current Hours": round(current_hours),
                "Current Required Engineers": round(current_required_engineers, 1),
                "BAU Future Hours": round(bau_future_hours),
                "BAU Required Engineers": round(bau_required_engineers, 1),
                "BAU Additional Required": max(
                    math.ceil(bau_gap),
                    0
                ),
                "DC Incremental Hours": round(dc_incremental_hours),
                "DC Incremental Engineers": round(dc_incremental_engineers, 1),
                "DC Additional Required": max(
                    math.ceil(dc_incremental_engineers),
                    0
                ),
                "Combined Future Hours": round(combined_future_hours),
                "Combined Required Engineers": round(combined_required_engineers, 1),
                "Available Engineers": round(available_engineers, 1),
                "Combined Net Gap / Surplus": round(combined_gap, 1),
                "Combined Additional Required": max(
                    math.ceil(combined_gap),
                    0
                ),
            }
        )

    return pd.DataFrame(results)
``
