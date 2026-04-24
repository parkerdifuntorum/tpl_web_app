from __future__ import annotations

import pandas as pd
import pandapower as pp

from model_builder import apply_base_case


def run_multicase_n1_study(
    net,
    base_cases_df: pd.DataFrame,
    overload_limit: float,
    low_voltage_limit: float,
    high_voltage_limit: float,
):
    """Runs line N-1 contingencies for all base cases."""
    summary_rows = []
    detail_rows = []
    original_loads = net.load[["p_mw", "q_mvar"]].copy()

    for _, case in base_cases_df.dropna(subset=["case_name"]).iterrows():
        case_name = str(case["case_name"])

        apply_base_case(net, case, original_loads)

        try:
            pp.runpp(net, enforce_q_lims=True)
        except Exception as e:
            summary_rows.append({
                "base_case": case_name,
                "outaged_element": "Base Case",
                "outaged_type": "None",
                "status": "Base Case No Convergence",
                "error": str(e),
            })
            continue

        base_line_loading = net.res_line["loading_percent"].copy()
        base_trafo_loading = net.res_trafo["loading_percent"].copy()
        base_bus_voltage = net.res_bus["vm_pu"].copy()

        for line_idx in net.line.index:
            if not bool(net.line.at[line_idx, "in_service"]):
                continue

            outaged_element_name = str(net.line.at[line_idx, "name"])
            net.line.at[line_idx, "in_service"] = False

            try:
                pp.runpp(net, enforce_q_lims=True)

                cont_line_loading = net.res_line["loading_percent"].copy()
                cont_trafo_loading = net.res_trafo["loading_percent"].copy()
                cont_bus_voltage = net.res_bus["vm_pu"].copy()

                overloaded_devices = []
                low_voltage_buses = []
                high_voltage_buses = []

                for idx in net.line.index:
                    if idx == line_idx:
                        continue

                    loading = float(cont_line_loading.loc[idx])
                    if loading > overload_limit:
                        device_name = str(net.line.at[idx, "name"])
                        overloaded_devices.append(device_name)

                        detail_rows.append({
                            "base_case": case_name,
                            "outaged_element": outaged_element_name,
                            "outaged_type": "Line",
                            "violation_type": "Line Overload",
                            "violated_device": device_name,
                            "base_value": round(float(base_line_loading.loc[idx]), 2),
                            "contingency_value": round(loading, 2),
                            "limit": overload_limit,
                            "units": "%",
                        })

                for idx in net.trafo.index:
                    loading = float(cont_trafo_loading.loc[idx])
                    if loading > overload_limit:
                        device_name = str(net.trafo.at[idx, "name"])
                        overloaded_devices.append(device_name)

                        detail_rows.append({
                            "base_case": case_name,
                            "outaged_element": outaged_element_name,
                            "outaged_type": "Line",
                            "violation_type": "Transformer Overload",
                            "violated_device": device_name,
                            "base_value": round(float(base_trafo_loading.loc[idx]), 2),
                            "contingency_value": round(loading, 2),
                            "limit": overload_limit,
                            "units": "%",
                        })

                for idx in net.bus.index:
                    voltage = float(cont_bus_voltage.loc[idx])
                    bus_name = str(net.bus.at[idx, "name"])

                    if voltage < low_voltage_limit:
                        low_voltage_buses.append(bus_name)
                        detail_rows.append({
                            "base_case": case_name,
                            "outaged_element": outaged_element_name,
                            "outaged_type": "Line",
                            "violation_type": "Low Voltage",
                            "violated_device": bus_name,
                            "base_value": round(float(base_bus_voltage.loc[idx]), 4),
                            "contingency_value": round(voltage, 4),
                            "limit": low_voltage_limit,
                            "units": "pu",
                        })

                    elif voltage > high_voltage_limit:
                        high_voltage_buses.append(bus_name)
                        detail_rows.append({
                            "base_case": case_name,
                            "outaged_element": outaged_element_name,
                            "outaged_type": "Line",
                            "violation_type": "High Voltage",
                            "violated_device": bus_name,
                            "base_value": round(float(base_bus_voltage.loc[idx]), 4),
                            "contingency_value": round(voltage, 4),
                            "limit": high_voltage_limit,
                            "units": "pu",
                        })

                summary_rows.append({
                    "base_case": case_name,
                    "outaged_element": outaged_element_name,
                    "outaged_type": "Line",
                    "status": "Solved",
                    "max_line_loading_percent": round(float(cont_line_loading.max()), 2),
                    "max_trafo_loading_percent": round(float(cont_trafo_loading.max()), 2) if len(cont_trafo_loading) else 0,
                    "min_voltage_pu": round(float(cont_bus_voltage.min()), 4),
                    "max_voltage_pu": round(float(cont_bus_voltage.max()), 4),
                    "num_overloaded_devices": len(overloaded_devices),
                    "overloaded_devices": ", ".join(overloaded_devices) if overloaded_devices else "None",
                    "low_voltage_buses": ", ".join(low_voltage_buses) if low_voltage_buses else "None",
                    "high_voltage_buses": ", ".join(high_voltage_buses) if high_voltage_buses else "None",
                })

            except Exception as e:
                summary_rows.append({
                    "base_case": case_name,
                    "outaged_element": outaged_element_name,
                    "outaged_type": "Line",
                    "status": "No Convergence",
                    "error": str(e),
                })

            finally:
                net.line.at[line_idx, "in_service"] = True

    summary_df = pd.DataFrame(summary_rows)
    detail_df = pd.DataFrame(detail_rows)

    return summary_df, detail_df


def rank_upgrade_candidates(detail_df: pd.DataFrame) -> pd.DataFrame:
    """Ranks overloaded devices by repeated failures and severity."""
    if detail_df.empty:
        return pd.DataFrame()

    thermal_df = detail_df[
        detail_df["violation_type"].isin(["Line Overload", "Transformer Overload"])
    ].copy()

    if thermal_df.empty:
        return pd.DataFrame()

    thermal_df["exceedance_percent"] = thermal_df["contingency_value"] - thermal_df["limit"]

    ranking = (
        thermal_df
        .groupby(["violated_device", "violation_type"])
        .agg(
            failure_count=("violated_device", "count"),
            max_loading_percent=("contingency_value", "max"),
            average_loading_percent=("contingency_value", "mean"),
            total_exceedance_percent=("exceedance_percent", "sum"),
            representative_base_case=("base_case", lambda x: x.iloc[0]),
            representative_outaged_element=("outaged_element", lambda x: x.iloc[0]),
        )
        .reset_index()
    )

    ranking["upgrade_priority_score"] = (
        ranking["failure_count"] * 10
        + ranking["total_exceedance_percent"]
        + ranking["max_loading_percent"] / 10
    )

    ranking = ranking.sort_values("upgrade_priority_score", ascending=False).reset_index(drop=True)

    return ranking
