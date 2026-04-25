import pandas as pd


def default_buses():
    return pd.DataFrame([
        {"bus_id": "B1", "name": "Bus 1 - Grid Source", "vn_kv": 230.0},
        {"bus_id": "B2", "name": "Bus 2 - Gen Hub", "vn_kv": 230.0},
        {"bus_id": "B3", "name": "Bus 3 - Transfer Bus", "vn_kv": 230.0},
        {"bus_id": "B4", "name": "Bus 4 - Load Pocket", "vn_kv": 115.0},
        {"bus_id": "B5", "name": "Bus 5 - Local Gen / Load", "vn_kv": 115.0},
        {"bus_id": "B6", "name": "Bus 6 - Industrial Load", "vn_kv": 115.0},
        {"bus_id": "B7", "name": "Bus 7 - Secondary Gen / Load", "vn_kv": 115.0},
        {"bus_id": "G2", "name": "Gen Bus G2 - 12.5 kV", "vn_kv": 12.5},
        {"bus_id": "G5", "name": "Gen Bus G5 - 12.5 kV", "vn_kv": 12.5},
        {"bus_id": "G7", "name": "Gen Bus G7 - 12.5 kV", "vn_kv": 12.5},
    ])


def default_ext_grids():
    return pd.DataFrame([
        {"name": "Grid Source", "bus_id": "B1", "vm_pu": 1.00},
    ])


def default_generators():
    return pd.DataFrame([
        {
            "name": "Gen 1 at Bus G2",
            "bus_id": "G2",
            "p_mw": 120.0,
            "vm_pu": 1.00,
            "min_q_mvar": -20.0,
            "max_q_mvar": 40.0,
        },
        {
            "name": "Local Gen at Bus G5",
            "bus_id": "G5",
            "p_mw": 35.0,
            "vm_pu": 1.00,
            "min_q_mvar": -10.0,
            "max_q_mvar": 15.0,
        },
        {
            "name": "Gen 2 at Bus G7",
            "bus_id": "G7",
            "p_mw": 45.0,
            "vm_pu": 1.00,
            "min_q_mvar": -15.0,
            "max_q_mvar": 25.0,
        },
    ])


def default_loads():
    return pd.DataFrame([
        {"name": "Load at Bus 4", "bus_id": "B4", "p_mw": 140.0, "q_mvar": 45.0},
        {"name": "Load at Bus 5", "bus_id": "B5", "p_mw": 65.0, "q_mvar": 20.0},
        {"name": "Industrial Load at Bus 6", "bus_id": "B6", "p_mw": 75.0, "q_mvar": 25.0},
        {"name": "Load at Bus 7", "bus_id": "B7", "p_mw": 50.0, "q_mvar": 18.0},
    ])


def default_lines():
    return pd.DataFrame([
        # -----------------------------
        # 230 kV transmission mesh
        # -----------------------------
        {
            "name": "Line 1-2",
            "from_bus_id": "B1",
            "to_bus_id": "B2",
            "length_km": 40.0,
            "r_ohm_per_km": 0.035,
            "x_ohm_per_km": 0.55,
            "c_nf_per_km": 12.0,
            "max_i_ka": 0.55,
            "in_service": True,
        },
        {
            "name": "Line 2-3 A",
            "from_bus_id": "B2",
            "to_bus_id": "B3",
            "length_km": 35.0,
            "r_ohm_per_km": 0.035,
            "x_ohm_per_km": 0.55,
            "c_nf_per_km": 12.0,
            "max_i_ka": 0.38,
            "in_service": True,
        },
        {
            "name": "Line 2-3 B",
            "from_bus_id": "B2",
            "to_bus_id": "B3",
            "length_km": 35.0,
            "r_ohm_per_km": 0.035,
            "x_ohm_per_km": 0.55,
            "c_nf_per_km": 12.0,
            "max_i_ka": 0.38,
            "in_service": True,
        },
        {
            "name": "Line 1-3",
            "from_bus_id": "B1",
            "to_bus_id": "B3",
            "length_km": 60.0,
            "r_ohm_per_km": 0.04,
            "x_ohm_per_km": 0.60,
            "c_nf_per_km": 12.0,
            "max_i_ka": 0.45,
            "in_service": True,
        },

        # -----------------------------
        # 115 kV subtransmission mesh
        # No 230 kV to 115 kV line connections.
        # Voltage changes occur only through transformers.
        # -----------------------------
        {
            "name": "Line 4-5",
            "from_bus_id": "B4",
            "to_bus_id": "B5",
            "length_km": 25.0,
            "r_ohm_per_km": 0.08,
            "x_ohm_per_km": 0.40,
            "c_nf_per_km": 12.0,
            "max_i_ka": 0.45,
            "in_service": True,
        },
        {
            "name": "Line 4-7 Tie",
            "from_bus_id": "B4",
            "to_bus_id": "B7",
            "length_km": 50.0,
            "r_ohm_per_km": 0.10,
            "x_ohm_per_km": 0.45,
            "c_nf_per_km": 12.0,
            "max_i_ka": 0.30,
            "in_service": True,
        },
        {
            "name": "Line 5-6",
            "from_bus_id": "B5",
            "to_bus_id": "B6",
            "length_km": 30.0,
            "r_ohm_per_km": 0.08,
            "x_ohm_per_km": 0.38,
            "c_nf_per_km": 12.0,
            "max_i_ka": 0.38,
            "in_service": True,
        },
        {
            "name": "Line 6-7",
            "from_bus_id": "B6",
            "to_bus_id": "B7",
            "length_km": 28.0,
            "r_ohm_per_km": 0.08,
            "x_ohm_per_km": 0.38,
            "c_nf_per_km": 12.0,
            "max_i_ka": 0.35,
            "in_service": True,
        },
        {
            "name": "Line 4-6",
            "from_bus_id": "B4",
            "to_bus_id": "B6",
            "length_km": 35.0,
            "r_ohm_per_km": 0.09,
            "x_ohm_per_km": 0.42,
            "c_nf_per_km": 12.0,
            "max_i_ka": 0.35,
            "in_service": True,
        },
        {
            "name": "Line 5-7",
            "from_bus_id": "B5",
            "to_bus_id": "B7",
            "length_km": 32.0,
            "r_ohm_per_km": 0.08,
            "x_ohm_per_km": 0.40,
            "c_nf_per_km": 12.0,
            "max_i_ka": 0.34,
            "in_service": True,
        },
    ])


def default_transformers():
    return pd.DataFrame([
        {
            "name": "GSU Transformer G2-2",
            "hv_bus_id": "B2",
            "lv_bus_id": "G2",
            "sn_mva": 150.0,
            "vn_hv_kv": 230.0,
            "vn_lv_kv": 12.5,
            "vk_percent": 12.0,
            "vkr_percent": 0.5,
            "pfe_kw": 0.0,
            "i0_percent": 0.0,
            "in_service": True,
        },
        {
            "name": "GSU Transformer G5-5",
            "hv_bus_id": "B5",
            "lv_bus_id": "G5",
            "sn_mva": 50.0,
            "vn_hv_kv": 115.0,
            "vn_lv_kv": 12.5,
            "vk_percent": 10.0,
            "vkr_percent": 0.6,
            "pfe_kw": 0.0,
            "i0_percent": 0.0,
            "in_service": True,
        },
        {
            "name": "GSU Transformer G7-7",
            "hv_bus_id": "B7",
            "lv_bus_id": "G7",
            "sn_mva": 65.0,
            "vn_hv_kv": 115.0,
            "vn_lv_kv": 12.5,
            "vk_percent": 10.0,
            "vkr_percent": 0.6,
            "pfe_kw": 0.0,
            "i0_percent": 0.0,
            "in_service": True,
        },
        {
            "name": "Transformer 3-4",
            "hv_bus_id": "B3",
            "lv_bus_id": "B4",
            "sn_mva": 120.0,
            "vn_hv_kv": 230.0,
            "vn_lv_kv": 115.0,
            "vk_percent": 10.0,
            "vkr_percent": 0.5,
            "pfe_kw": 0.0,
            "i0_percent": 0.0,
            "in_service": True,
        },
        {
            "name": "Transformer 2-6",
            "hv_bus_id": "B2",
            "lv_bus_id": "B6",
            "sn_mva": 100.0,
            "vn_hv_kv": 230.0,
            "vn_lv_kv": 115.0,
            "vk_percent": 10.5,
            "vkr_percent": 0.6,
            "pfe_kw": 0.0,
            "i0_percent": 0.0,
            "in_service": True,
        },
        {
            "name": "Transformer 1-7",
            "hv_bus_id": "B1",
            "lv_bus_id": "B7",
            "sn_mva": 90.0,
            "vn_hv_kv": 230.0,
            "vn_lv_kv": 115.0,
            "vk_percent": 11.0,
            "vkr_percent": 0.7,
            "pfe_kw": 0.0,
            "i0_percent": 0.0,
            "in_service": True,
        },
    ])


def default_base_cases():
    return pd.DataFrame([
        {
            "case_name": "summer_peak",
            "load_scale": 1.00,
            "Gen 1 at Bus G2": 120.0,
            "Local Gen at Bus G5": 35.0,
            "Gen 2 at Bus G7": 45.0,
        },
        {
            "case_name": "future_peak",
            "load_scale": 1.20,
            "Gen 1 at Bus 2": 120.0,
            "Local Gen at Bus 5": 35.0,
            "Gen 2 at Bus 7": 45.0,
        },
        {
            "case_name": "light_load",
            "load_scale": 0.40,
            "Gen 1 at Bus 2": 80.0,
            "Local Gen at Bus 5": 20.0,
            "Gen 2 at Bus 7": 25.0,
        },
        {
            "case_name": "local_gen_off",
            "load_scale": 1.00,
            "Gen 1 at Bus 2": 120.0,
            "Local Gen at Bus 5": 0.0,
            "Gen 2 at Bus 7": 0.0,
        },
    ])
