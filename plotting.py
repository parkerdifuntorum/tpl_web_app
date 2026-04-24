from __future__ import annotations

import matplotlib.pyplot as plt
import networkx as nx
import pandapower as pp
import pandas as pd


def build_topology_layout(net, seed: int = 42):
    """Builds automatic bus coordinates from current network topology."""
    graph = nx.Graph()

    for bus_idx in net.bus.index:
        graph.add_node(int(bus_idx))

    for idx in net.line.index:
        if bool(net.line.at[idx, "in_service"]):
            graph.add_edge(int(net.line.at[idx, "from_bus"]), int(net.line.at[idx, "to_bus"]))

    for idx in net.trafo.index:
        if bool(net.trafo.at[idx, "in_service"]):
            graph.add_edge(int(net.trafo.at[idx, "hv_bus"]), int(net.trafo.at[idx, "lv_bus"]))

    if len(graph.nodes) == 0:
        return {}

    pos = nx.spring_layout(graph, seed=seed, k=1.6, iterations=150)

    # Stretch horizontal axis for better readability.
    return {node: (float(x) * 8.0, float(y) * 5.0) for node, (x, y) in pos.items()}


def offset_label(x1, y1, x2, y2, offset=0.35):
    mx = (x1 + x2) / 2
    my = (y1 + y2) / 2
    dx = x2 - x1
    dy = y2 - y1
    length = (dx ** 2 + dy ** 2) ** 0.5

    if length == 0:
        return mx, my

    ox = -dy / length * offset
    oy = dx / length * offset
    return mx + ox, my + oy


def plot_upgrade_ranking(upgrade_df: pd.DataFrame):
    if upgrade_df.empty:
        return None

    fig, ax = plt.subplots(figsize=(12, 5))
    top = upgrade_df.head(10).copy()
    ax.bar(top["violated_device"], top["upgrade_priority_score"])
    ax.set_title("Upgrade Priority Ranking by Failed Device")
    ax.set_xlabel("Device")
    ax.set_ylabel("Upgrade Priority Score")
    ax.tick_params(axis="x", rotation=35)
    fig.tight_layout()
    return fig


def plot_recommended_upgrade_case(
    net,
    original_loads: pd.DataFrame,
    base_case: pd.Series,
    recommended_row: pd.Series,
    overload_limit: float,
    low_voltage_limit: float,
    high_voltage_limit: float,
    seed: int = 42,
):
    """Plots representative case for top recommended upgrade candidate."""
    from model_builder import apply_base_case

    recommended_device = str(recommended_row["violated_device"])
    recommended_type = str(recommended_row["violation_type"])
    recommended_case = str(recommended_row["representative_base_case"])
    recommended_outage = str(recommended_row["representative_outaged_element"])

    apply_base_case(net, base_case, original_loads)
    pp.runpp(net, enforce_q_lims=True)

    base_line_loading = net.res_line["loading_percent"].copy()
    base_trafo_loading = net.res_trafo["loading_percent"].copy()
    base_bus_voltage = net.res_bus["vm_pu"].copy()

    outage_line_idx = None
    for idx in net.line.index:
        if str(net.line.at[idx, "name"]) == recommended_outage:
            outage_line_idx = idx
            break

    if outage_line_idx is None:
        raise ValueError(f"Could not find representative outaged line: {recommended_outage}")

    net.line.at[outage_line_idx, "in_service"] = False
    pp.runpp(net, enforce_q_lims=True)

    cont_line_loading = net.res_line["loading_percent"].copy()
    cont_trafo_loading = net.res_trafo["loading_percent"].copy()
    cont_bus_voltage = net.res_bus["vm_pu"].copy()
    cont_line_p_from = net.res_line["p_from_mw"].copy()
    cont_trafo_p_hv = net.res_trafo["p_hv_mw"].copy()

    net.line.at[outage_line_idx, "in_service"] = True

    pos = build_topology_layout(net, seed=seed)

    fig, ax = plt.subplots(figsize=(17, 10))

    # Draw lines
    for idx in net.line.index:
        from_bus = int(net.line.at[idx, "from_bus"])
        to_bus = int(net.line.at[idx, "to_bus"])
        line_name = str(net.line.at[idx, "name"])

        x1, y1 = pos[from_bus]
        x2, y2 = pos[to_bus]

        if idx == outage_line_idx:
            color = "blue"
            linestyle = "--"
            cont_text = "OUT"
            flow_text = "OUT"
            linewidth = 3.0
        else:
            loading = float(cont_line_loading.loc[idx])
            p_from = float(cont_line_p_from.loc[idx])

            if line_name == recommended_device:
                color = "darkred"
                linewidth = 5.0
            elif loading > overload_limit:
                color = "red"
                linewidth = 3.5
            else:
                color = "black"
                linewidth = 2.2

            linestyle = "-"
            cont_text = f"{loading:.1f}%"
            flow_text = f"{abs(p_from):.1f} MW"

        ax.plot([x1, x2], [y1, y2], color=color, linestyle=linestyle, linewidth=linewidth, zorder=1)

        if idx != outage_line_idx:
            p_from = float(cont_line_p_from.loc[idx])
            if p_from >= 0:
                start_x, start_y = x1, y1
                end_x, end_y = x2, y2
            else:
                start_x, start_y = x2, y2
                end_x, end_y = x1, y1

            dx = end_x - start_x
            dy = end_y - start_y

            ax.arrow(
                start_x + 0.25 * dx,
                start_y + 0.25 * dy,
                0.35 * dx,
                0.35 * dy,
                length_includes_head=True,
                head_width=0.10,
                head_length=0.16,
                color=color,
                zorder=2,
            )

        label_x, label_y = offset_label(x1, y1, x2, y2, offset=0.55)
        base_loading = float(base_line_loading.loc[idx])
        label_prefix = "UPGRADE CANDIDATE\\n" if line_name == recommended_device else ""

        ax.text(
            label_x,
            label_y,
            f"{label_prefix}{line_name}\\nBase: {base_loading:.1f}%\\nCont: {cont_text}\\nFlow: {flow_text}",
            fontsize=7.2,
            ha="center",
            va="center",
            bbox=dict(facecolor="white", edgecolor=color, alpha=0.90),
            zorder=4,
        )

    # Draw transformers
    for idx in net.trafo.index:
        hv_bus = int(net.trafo.at[idx, "hv_bus"])
        lv_bus = int(net.trafo.at[idx, "lv_bus"])
        trafo_name = str(net.trafo.at[idx, "name"])

        x1, y1 = pos[hv_bus]
        x2, y2 = pos[lv_bus]

        loading = float(cont_trafo_loading.loc[idx])
        base_loading = float(base_trafo_loading.loc[idx])
        p_hv = float(cont_trafo_p_hv.loc[idx])

        if trafo_name == recommended_device:
            color = "darkred"
            linewidth = 5.0
        elif loading > overload_limit:
            color = "red"
            linewidth = 3.5
        else:
            color = "purple"
            linewidth = 3.0

        ax.plot([x1, x2], [y1, y2], color=color, linewidth=linewidth, linestyle="--", zorder=2)

        marker_x, marker_y = offset_label(x1, y1, x2, y2, offset=0.0)
        ax.scatter(marker_x, marker_y, s=420, marker="s", color="violet", edgecolors=color, linewidths=2, zorder=6)
        ax.text(marker_x, marker_y, "XFMR", fontsize=7.2, ha="center", va="center", fontweight="bold", zorder=7)

        # Shift all transformer description boxes to the right.
        label_x, label_y = offset_label(x1, y1, x2, y2, offset=0.7)
        label_x += 1.1

        label_prefix = "UPGRADE CANDIDATE\\n" if trafo_name == recommended_device else ""

        ax.text(
            label_x,
            label_y,
            f"{label_prefix}{trafo_name}\\nBase: {base_loading:.1f}%\\nCont: {loading:.1f}%\\nFlow: {abs(p_hv):.1f} MW",
            fontsize=7.2,
            ha="center",
            va="center",
            bbox=dict(facecolor="white", edgecolor=color, alpha=0.90),
            zorder=8,
        )

    # Draw buses
    for bus_idx in net.bus.index:
        x, y = pos[int(bus_idx)]
        bus_name = str(net.bus.at[bus_idx, "name"])
        voltage = float(cont_bus_voltage.loc[bus_idx])
        base_voltage = float(base_bus_voltage.loc[bus_idx])

        bus_color = "orange" if voltage < low_voltage_limit or voltage > high_voltage_limit else "lightgray"

        ax.scatter(x, y, s=360, color=bus_color, edgecolors="black", zorder=9)
        ax.text(
            x,
            y + 0.55,
            f"{bus_name}\\nBase: {base_voltage:.3f} pu\\nCont: {voltage:.3f} pu",
            fontsize=7.2,
            ha="center",
            fontweight="bold",
            bbox=dict(facecolor="white", edgecolor="gray", alpha=0.75),
            zorder=10,
        )

    # Draw generators
    for idx in net.gen.index:
        bus = int(net.gen.at[idx, "bus"])
        gen_name = str(net.gen.at[idx, "name"])
        p_mw = float(net.gen.at[idx, "p_mw"])
        x, y = pos[bus]

        ax.text(
            x - 0.6,
            y - 0.95,
            f"{gen_name}\\n{p_mw:.1f} MW",
            fontsize=7.2,
            ha="center",
            bbox=dict(facecolor="lightyellow", edgecolor="orange", alpha=0.9),
            zorder=11,
        )

    # Draw loads, shifted down from other boxes
    for idx in net.load.index:
        bus = int(net.load.at[idx, "bus"])
        load_name = str(net.load.at[idx, "name"])
        p_mw = float(net.load.at[idx, "p_mw"])
        x, y = pos[bus]

        ax.text(
            x + 0.6,
            y - 1.55,
            f"{load_name}\\n{p_mw:.1f} MW",
            fontsize=7.2,
            ha="center",
            bbox=dict(facecolor="mistyrose", edgecolor="darkred", alpha=0.88, boxstyle="round,pad=0.35"),
            zorder=11,
        )

    fig.suptitle(
        "Interactive Multi-Basecase N-1 Study — Recommended Upgrade Visualization",
        fontsize=13,
        fontweight="bold",
        y=0.98,
    )

    summary_text = (
        "RECOMMENDED FIRST UPGRADE\\n"
        f"Device: {recommended_device}   |   Type: {recommended_type}\\n"
        f"Representative Case: {recommended_case}   |   Outaged: {recommended_outage}\\n"
        f"Failure Count: {recommended_row['failure_count']}   |   "
        f"Max Loading: {recommended_row['max_loading_percent']:.1f}%   |   "
        f"Priority Score: {recommended_row['upgrade_priority_score']:.1f}"
    )

    ax.text(
        0.5,
        -0.16,
        summary_text,
        transform=ax.transAxes,
        fontsize=9.2,
        ha="center",
        va="top",
        fontweight="bold",
        bbox=dict(facecolor="white", edgecolor="black", alpha=0.96, boxstyle="round,pad=0.5"),
    )

    legend_text = (
        "LEGEND\\n"
        "Blue dashed = Outaged element\\n"
        "Dark red = Recommended upgrade candidate\\n"
        "Red = Other overloaded device\\n"
        "Orange bus = Voltage violation\\n"
        "Arrow = MW flow direction"
    )

    ax.text(
        0.01,
        0.01,
        legend_text,
        transform=ax.transAxes,
        fontsize=7.2,
        ha="left",
        va="bottom",
        bbox=dict(facecolor="white", edgecolor="gray", alpha=0.92, boxstyle="round,pad=0.35"),
    )

    callout_text = (
        "UPGRADE PRIORITY #1\\n"
        f"{recommended_device}\\n"
        f"Fails in {recommended_row['failure_count']} contingency case(s)"
    )

    ax.text(
        0.99,
        0.07,
        callout_text,
        transform=ax.transAxes,
        fontsize=8.2,
        ha="right",
        va="bottom",
        fontweight="bold",
        bbox=dict(facecolor="mistyrose", edgecolor="darkred", alpha=0.95, boxstyle="round,pad=0.4"),
    )

    ax.set_aspect("equal")
    ax.axis("off")
    plt.subplots_adjust(bottom=0.25, top=0.86)

    return fig
