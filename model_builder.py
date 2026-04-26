from __future__ import annotations

import pandas as pd
import pandapower as pp


def _require_columns(df: pd.DataFrame, columns: list[str], name: str) -> None:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ValueError(f"{name} is missing columns: {missing}")


def _clean_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return True
    return str(value).strip().lower() not in {"false", "0", "no", "n"}


def build_network(buses_df, lines_df, trafos_df, gens_df, loads_df, ext_grids_df):
    _require_columns(buses_df, ["bus_id", "name", "vn_kv"], "buses_df")
    _require_columns(lines_df, ["name", "from_bus_id", "to_bus_id", "length_km", "r_ohm_per_km", "x_ohm_per_km", "c_nf_per_km", "max_i_ka"], "lines_df")
    _require_columns(trafos_df, ["name", "hv_bus_id", "lv_bus_id", "sn_mva", "vn_hv_kv", "vn_lv_kv", "vk_percent", "vkr_percent", "pfe_kw", "i0_percent"], "trafos_df")
    _require_columns(gens_df, ["name", "bus_id", "p_mw", "vm_pu", "min_q_mvar", "max_q_mvar"], "gens_df")
    _require_columns(loads_df, ["name", "bus_id", "p_mw", "q_mvar"], "loads_df")
    _require_columns(ext_grids_df, ["name", "bus_id", "vm_pu"], "ext_grids_df")

    net = pp.create_empty_network()
    bus_lookup = {}

    for _, row in buses_df.dropna(subset=["bus_id"]).iterrows():
        bus_id = str(row["bus_id"]).strip()
        if not bus_id:
            continue
        idx = pp.create_bus(net, vn_kv=float(row["vn_kv"]), name=str(row["name"]))
        bus_lookup[bus_id] = idx

    def bus_idx(bus_id: str) -> int:
        key = str(bus_id).strip()
        if key not in bus_lookup:
            raise ValueError(f"Bus ID {key!r} not found in buses table.")
        return bus_lookup[key]

    for _, row in ext_grids_df.dropna(subset=["bus_id"]).iterrows():
        pp.create_ext_grid(net, bus=bus_idx(row["bus_id"]), vm_pu=float(row["vm_pu"]), name=str(row["name"]))

    for _, row in gens_df.dropna(subset=["bus_id"]).iterrows():
        pp.create_gen(
            net,
            bus=bus_idx(row["bus_id"]),
            p_mw=float(row["p_mw"]),
            vm_pu=float(row["vm_pu"]),
            min_q_mvar=float(row["min_q_mvar"]),
            max_q_mvar=float(row["max_q_mvar"]),
            name=str(row["name"]),
        )

    for _, row in loads_df.dropna(subset=["bus_id"]).iterrows():
        pp.create_load(net, bus=bus_idx(row["bus_id"]), p_mw=float(row["p_mw"]), q_mvar=float(row["q_mvar"]), name=str(row["name"]))

    for _, row in lines_df.dropna(subset=["from_bus_id", "to_bus_id"]).iterrows():
        idx = pp.create_line_from_parameters(
            net,
            from_bus=bus_idx(row["from_bus_id"]),
            to_bus=bus_idx(row["to_bus_id"]),
            length_km=float(row["length_km"]),
            r_ohm_per_km=float(row["r_ohm_per_km"]),
            x_ohm_per_km=float(row["x_ohm_per_km"]),
            c_nf_per_km=float(row["c_nf_per_km"]),
            max_i_ka=float(row["max_i_ka"]),
            name=str(row["name"]),
        )
        if "in_service" in row:
            net.line.at[idx, "in_service"] = _clean_bool(row["in_service"])

    for _, row in trafos_df.dropna(subset=["hv_bus_id", "lv_bus_id"]).iterrows():
        idx = pp.create_transformer_from_parameters(
            net,
            hv_bus=bus_idx(row["hv_bus_id"]),
            lv_bus=bus_idx(row["lv_bus_id"]),
            sn_mva=float(row["sn_mva"]),
            vn_hv_kv=float(row["vn_hv_kv"]),
            vn_lv_kv=float(row["vn_lv_kv"]),
            vk_percent=float(row["vk_percent"]),
            vkr_percent=float(row["vkr_percent"]),
            pfe_kw=float(row["pfe_kw"]),
            i0_percent=float(row["i0_percent"]),
            name=str(row["name"]),
        )
        if "in_service" in row:
            net.trafo.at[idx, "in_service"] = _clean_bool(row["in_service"])

    if len(net.ext_grid) == 0:
        raise ValueError("At least one external grid/slack source is required.")

    validate_voltage_level_consistency(net)
    return net, bus_lookup


def validate_voltage_level_consistency(net):
    bad_lines = []
    for idx in net.line.index:
        fb = net.line.at[idx, "from_bus"]
        tb = net.line.at[idx, "to_bus"]
        if float(net.bus.at[fb, "vn_kv"]) != float(net.bus.at[tb, "vn_kv"]):
            bad_lines.append(
                f"{net.line.at[idx, 'name']}: {net.bus.at[fb, 'vn_kv']} kV to {net.bus.at[tb, 'vn_kv']} kV"
            )
    if bad_lines:
        raise ValueError("Invalid line voltage connection(s). Use transformers between voltage levels: " + "; ".join(bad_lines))


def apply_base_case(net, base_case: pd.Series, original_loads: pd.DataFrame):
    load_scale = float(base_case.get("load_scale", 1.0))

    for idx in net.load.index:
        net.load.at[idx, "p_mw"] = float(original_loads.loc[idx, "p_mw"]) * load_scale
        net.load.at[idx, "q_mvar"] = float(original_loads.loc[idx, "q_mvar"]) * load_scale

    for idx in net.gen.index:
        gen_name = str(net.gen.at[idx, "name"])
        if gen_name in base_case.index and pd.notna(base_case[gen_name]):
            net.gen.at[idx, "p_mw"] = float(base_case[gen_name])
