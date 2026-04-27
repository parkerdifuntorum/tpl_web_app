from __future__ import annotations

import streamlit as st

from defaults import (
    default_buses,
    default_lines,
    default_transformers,
    default_generators,
    default_loads,
    default_ext_grids,
    default_base_cases,
)
from model_builder import build_network
from study_engine import run_multicase_n1_study, rank_upgrade_candidates
from plotting import plot_recommended_upgrade_case, plot_upgrade_ranking


st.set_page_config(page_title="TPL N-1 Study Sandbox", layout="wide")

APP_DATA_VERSION = "slack-node-v1"


def init_state():
    defaults = {
        "buses_df": default_buses(),
        "lines_df": default_lines(),
        "trafos_df": default_transformers(),
        "gens_df": default_generators(),
        "loads_df": default_loads(),
        "ext_grids_df": default_ext_grids(),
        "base_cases_df": default_base_cases(),
    }

    # Force session-state reload when the default topology changes.
    if st.session_state.get("app_data_version") != APP_DATA_VERSION:
        for key, value in defaults.items():
            st.session_state[key] = value.copy()
        st.session_state["app_data_version"] = APP_DATA_VERSION
        return

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value.copy()


def df_download_button(df, label, filename):
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(label=label, data=csv, file_name=filename, mime="text/csv")


def sync_base_case_generator_columns(base_cases_df, gens_df):
    out = base_cases_df.copy()
    if "case_name" not in out.columns:
        out["case_name"] = "new_case"
    if "load_scale" not in out.columns:
        out["load_scale"] = 1.0
    for _, row in gens_df.iterrows():
        gen_name = str(row["name"])
        if gen_name and gen_name not in out.columns:
            out[gen_name] = float(row.get("p_mw", 0.0))
    return out


init_state()

st.title("Interactive TPL-Style N-1 Transmission Study Sandbox")
st.caption("Editable network topology, automatic one-line mapping, multi-basecase contingency analysis, and upgrade prioritization.")

with st.sidebar:
    st.header("Study Settings")
    overload_limit = st.number_input("Thermal overload limit (%)", min_value=1.0, max_value=300.0, value=100.0, step=5.0)
    low_voltage_limit = st.number_input("Low voltage limit (pu)", min_value=0.50, max_value=1.00, value=0.95, step=0.01)
    high_voltage_limit = st.number_input("High voltage limit (pu)", min_value=1.00, max_value=1.50, value=1.05, step=0.01)
    layout_seed = st.number_input("Auto-map layout seed", min_value=0, max_value=9999, value=42, step=1)
    st.divider()
    if st.button("Reset to Default Network"):
        for key in ["buses_df", "lines_df", "trafos_df", "gens_df", "loads_df", "ext_grids_df", "base_cases_df"]:
            del st.session_state[key]
        init_state()
        st.rerun()

tabs = st.tabs(["Buses", "Lines", "Transformers", "Generators", "Loads", "External Grid", "Base Cases", "Run Study"])

with tabs[0]:
    st.subheader("Editable Buses")
    st.session_state.buses_df = st.data_editor(st.session_state.buses_df, num_rows="dynamic", use_container_width=True, key="buses_editor")

with tabs[1]:
    st.subheader("Editable Lines")
    st.info("Lines should connect buses at the same voltage level. Use transformers between voltage levels.")
    st.session_state.lines_df = st.data_editor(st.session_state.lines_df, num_rows="dynamic", use_container_width=True, key="lines_editor")

with tabs[2]:
    st.subheader("Editable Transformers")
    st.session_state.trafos_df = st.data_editor(st.session_state.trafos_df, num_rows="dynamic", use_container_width=True, key="trafos_editor")

with tabs[3]:
    st.subheader("Editable Generators")
    st.info("Default generators connect to 12.5 kV generator terminal buses through explicit GSU transformers.")
    st.session_state.gens_df = st.data_editor(st.session_state.gens_df, num_rows="dynamic", use_container_width=True, key="gens_editor")

with tabs[4]:
    st.subheader("Editable Loads")
    st.session_state.loads_df = st.data_editor(st.session_state.loads_df, num_rows="dynamic", use_container_width=True, key="loads_editor")

with tabs[5]:
    st.subheader("Editable External Grid / Slack Source")
    st.session_state.ext_grids_df = st.data_editor(st.session_state.ext_grids_df, num_rows="dynamic", use_container_width=True, key="ext_grid_editor")

with tabs[6]:
    st.subheader("Editable Base Cases")
    st.info("Add/remove rows to add/remove base cases. Generator dispatch columns are synced from generator names.")
    st.session_state.base_cases_df = sync_base_case_generator_columns(st.session_state.base_cases_df, st.session_state.gens_df)
    st.session_state.base_cases_df = st.data_editor(st.session_state.base_cases_df, num_rows="dynamic", use_container_width=True, key="base_cases_editor")

with tabs[7]:
    st.subheader("Run Multi-Basecase N-1 Study")
    if st.button("Build Network and Run N-1 Study", type="primary"):
        try:
            net, _ = build_network(
                st.session_state.buses_df,
                st.session_state.lines_df,
                st.session_state.trafos_df,
                st.session_state.gens_df,
                st.session_state.loads_df,
                st.session_state.ext_grids_df,
            )
            summary_df, detail_df = run_multicase_n1_study(net, st.session_state.base_cases_df, overload_limit, low_voltage_limit, high_voltage_limit)
            upgrade_df = rank_upgrade_candidates(detail_df)
            st.session_state["summary_df"] = summary_df
            st.session_state["detail_df"] = detail_df
            st.session_state["upgrade_df"] = upgrade_df
            st.success("Study completed.")
        except Exception as e:
            st.error(f"Study failed: {e}")

    if "summary_df" in st.session_state:
        summary_df = st.session_state["summary_df"]
        detail_df = st.session_state["detail_df"]
        upgrade_df = st.session_state["upgrade_df"]

        st.divider()
        st.subheader("Contingency Summary")
        st.dataframe(summary_df, use_container_width=True)
        df_download_button(summary_df, "Download Summary CSV", "tpl_summary.csv")

        st.subheader("Violation Details")
        if detail_df.empty:
            st.info("No violations detected.")
        else:
            st.dataframe(detail_df, use_container_width=True)
            df_download_button(detail_df, "Download Violations CSV", "tpl_violations.csv")

        st.subheader("Upgrade Candidate Ranking")
        if upgrade_df.empty:
            st.info("No thermal overloads detected. No upgrade ranking generated.")
        else:
            st.dataframe(upgrade_df, use_container_width=True)
            df_download_button(upgrade_df, "Download Upgrade Ranking CSV", "tpl_upgrade_ranking.csv")

            fig_rank = plot_upgrade_ranking(upgrade_df)
            if fig_rank is not None:
                st.plotly_chart(fig_rank, use_container_width=True)

            st.subheader("Recommended Upgrade Visualization")
            recommended = upgrade_df.iloc[0]
            representative_case_name = recommended["representative_base_case"]
            base_case_row = st.session_state.base_cases_df[st.session_state.base_cases_df["case_name"] == representative_case_name]

            if base_case_row.empty:
                st.warning("Representative base case no longer exists in the editable base-case table.")
            else:
                try:
                    plot_net, _ = build_network(
                        st.session_state.buses_df,
                        st.session_state.lines_df,
                        st.session_state.trafos_df,
                        st.session_state.gens_df,
                        st.session_state.loads_df,
                        st.session_state.ext_grids_df,
                    )
                    fig = plot_recommended_upgrade_case(
                        plot_net,
                        plot_net.load[["p_mw", "q_mvar"]].copy(),
                        base_case_row.iloc[0],
                        recommended,
                        overload_limit,
                        low_voltage_limit,
                        high_voltage_limit,
                        seed=int(layout_seed),
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    html = fig.to_html(include_plotlyjs="cdn")
                    st.download_button(
                        "Download Interactive Plot as HTML",
                        data=html.encode("utf-8"),
                        file_name="recommended_upgrade_plot.html",
                        mime="text/html",
                    )
                except Exception as e:
                    st.error(f"Could not generate recommended upgrade plot: {e}")
