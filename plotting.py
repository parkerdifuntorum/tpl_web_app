from __future__ import annotations

import math
import pandas as pd
import pandapower as pp
import networkx as nx
import plotly.graph_objects as go


def build_topology_layout(net, seed: int = 42):
    """
    Build automatic bus coordinates from current network topology.

    For the default model, this uses a deterministic layered one-line layout:
      - B0 slack/grid source above the 230 kV row
      - B1/B2/B3 on the 230 kV row
      - B7/B6/B5/B4 on the 115 kV row
      - generator terminal buses on the 12.5 kV row
    """
    graph = nx.Graph()

    for bus_idx in net.bus.index:
        graph.add_node(int(bus_idx))

    for idx in net.line.index:
        if bool(net.line.at[idx, "in_service"]):
            graph.add_edge(
                int(net.line.at[idx, "from_bus"]),
                int(net.line.at[idx, "to_bus"])
            )

    for idx in net.trafo.index:
        if bool(net.trafo.at[idx, "in_service"]):
            graph.add_edge(
                int(net.trafo.at[idx, "hv_bus"]),
                int(net.trafo.at[idx, "lv_bus"])
            )

    if len(graph.nodes) == 0:
        return {}

    def infer_bus_id(bus_name: str):
        if bus_name.startswith("Bus 0"):
            return "B0"
        if bus_name.startswith("Bus 1"):
            return "B1"
        if bus_name.startswith("Bus 2"):
            return "B2"
        if bus_name.startswith("Bus 3"):
            return "B3"
        if bus_name.startswith("Bus 4"):
            return "B4"
        if bus_name.startswith("Bus 5"):
            return "B5"
        if bus_name.startswith("Bus 6"):
            return "B6"
        if bus_name.startswith("Bus 7"):
            return "B7"
        if bus_name.startswith("Gen Bus G2"):
            return "G2"
        if bus_name.startswith("Gen Bus G5"):
            return "G5"
        if bus_name.startswith("Gen Bus G7"):
            return "G7"
        return None

    bus_id_positions = {
        # Slack/source bus
        "B0": (12.0, 20.0),

        # 230 kV row
        "B1": (0.0, 10.0),
        "B2": (12.0, 10.0),
        "B3": (24.0, 10.0),

        # 115 kV row
        "B7": (0.0, 0.0),
        "B6": (8.0, 0.0),
        "B5": (16.0, 0.0),
        "B4": (24.0, 0.0),

        # 12.5 kV generator terminal buses
        "G7": (0.0, -7.0),
        "G5": (16.0, -7.0),
        "G2": (12.0, 17.0),
    }

    pos = {}

    for idx in net.bus.index:
        bus_name = str(net.bus.at[idx, "name"])
        bus_id = infer_bus_id(bus_name)
        if bus_id in bus_id_positions:
            pos[int(idx)] = bus_id_positions[bus_id]

    # Fallback for any user-added buses.
    missing = [int(idx) for idx in net.bus.index if int(idx) not in pos]
    if missing:
        spring_pos = nx.spring_layout(graph, seed=seed, k=3.0, iterations=400)
        for node in missing:
            x, y = spring_pos[node]
            pos[node] = (float(x) * 32.0, float(y) * 14.0)

    return pos


def _midpoint(x1, y1, x2, y2):
    return (x1 + x2) / 2.0, (y1 + y2) / 2.0


def _offset_point(x1, y1, x2, y2, offset=0.8):
    mx, my = _midpoint(x1, y1, x2, y2)
    dx = x2 - x1
    dy = y2 - y1
    length = math.sqrt(dx * dx + dy * dy)
    if length == 0:
        return mx, my
    return mx + (-dy / length) * offset, my + (dx / length) * offset


def _transformer_symbol_points(x1, y1, x2, y2, radius=0.50):
    mx, my = _midpoint(x1, y1, x2, y2)
    dx = x2 - x1
    dy = y2 - y1
    length = math.sqrt(dx * dx + dy * dy)
    if length == 0:
        return (mx - radius, my), (mx + radius, my)
    ux = dx / length
    uy = dy / length
    return (mx - ux * radius, my - uy * radius), (mx + ux * radius, my + uy * radius)


def _circle_trace(cx, cy, r, color, hovertext):
    theta = [i * 2 * math.pi / 60 for i in range(61)]
    return go.Scatter(
        x=[cx + r * math.cos(t) for t in theta],
        y=[cy + r * math.sin(t) for t in theta],
        mode="lines",
        line=dict(color=color, width=2),
        hoverinfo="text",
        hovertext=hovertext,
        showlegend=False,
    )


def plot_upgrade_ranking(upgrade_df: pd.DataFrame):
    if upgrade_df.empty:
        return None
    top = upgrade_df.head(10).copy()
    fig = go.Figure(data=[go.Bar(
        x=top["violated_device"],
        y=top["upgrade_priority_score"],
        text=top["upgrade_priority_score"].round(1),
        textposition="auto",
        hovertemplate="<b>%{x}</b><br>Priority score: %{y:.2f}<extra></extra>",
    )])
    fig.update_layout(
        title="Upgrade Priority Ranking by Failed Device",
        xaxis_title="Device",
        yaxis_title="Upgrade Priority Score",
        height=450,
        margin=dict(l=40, r=30, t=70, b=120),
    )
    return fig


def plot_recommended_upgrade_case(net, original_loads, base_case, recommended_row, overload_limit, low_voltage_limit, high_voltage_limit, seed=42):
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
    fig = go.Figure()

    # Lines
    lx, ly, ltext, lhover = [], [], [], []
    for idx in net.line.index:
        fbus = int(net.line.at[idx, "from_bus"])
        tbus = int(net.line.at[idx, "to_bus"])
        name = str(net.line.at[idx, "name"])
        x1, y1 = pos[fbus]
        x2, y2 = pos[tbus]

        if idx == outage_line_idx:
            color, dash, width = "royalblue", "dash", 4
            cont_text, flow_text, status = "OUT", "OUT", "Outaged"
        else:
            loading = float(cont_line_loading.loc[idx])
            p_from = float(cont_line_p_from.loc[idx])
            if name == recommended_device:
                color, width, status = "darkred", 7, "Recommended upgrade candidate"
            elif loading > overload_limit:
                color, width, status = "red", 5, "Overloaded"
            else:
                color, width, status = "black", 3, "OK"
            dash = "solid"
            cont_text = f"{loading:.1f}%"
            flow_text = f"{abs(p_from):.1f} MW"

        base_loading = float(base_line_loading.loc[idx])
        hover = (
            f"<b>{name}</b><br>Type: Line<br>Status: {status}<br>"
            f"Base loading: {base_loading:.2f}%<br>Contingency loading: {cont_text}<br>"
            f"Flow: {flow_text}<br>From: {net.bus.at[fbus, 'name']}<br>To: {net.bus.at[tbus, 'name']}"
        )

        fig.add_trace(go.Scatter(
            x=[x1, x2], y=[y1, y2], mode="lines",
            line=dict(color=color, width=width, dash=dash),
            hoverinfo="text", hovertext=hover, showlegend=False, name=name
        ))

        if idx != outage_line_idx:
            p_from = float(cont_line_p_from.loc[idx])
            sx, sy, ex, ey = (x1, y1, x2, y2) if p_from >= 0 else (x2, y2, x1, y1)
            fig.add_annotation(
                x=sx + 0.58 * (ex - sx), y=sy + 0.58 * (ey - sy),
                ax=sx + 0.42 * (ex - sx), ay=sy + 0.42 * (ey - sy),
                xref="x", yref="y", axref="x", ayref="y",
                showarrow=True, arrowhead=3, arrowsize=1, arrowwidth=max(1, width - 2),
                arrowcolor=color, opacity=0.9,
            )

        line_label_offsets = {
            "Line 0-1": 1.25,
            "Line 0-3": -1.65,
            "Line 1-2": 1.25,
            "Line 2-3": 1.45,
            "Line 4-5": 1.25,
            "Line 5-6": 1.25,
            "Line 6-7": -1.25,
            "Line 4-6": 1.55,
        }
        tx, ty = _offset_point(x1, y1, x2, y2, offset=line_label_offsets.get(name, 1.15))
        label = f"{name}<br>{cont_text}"
        if name == recommended_device:
            label = f"<b>UPGRADE</b><br>{name}<br>{cont_text}"
        lx.append(tx); ly.append(ty); ltext.append(label); lhover.append(hover)

    fig.add_trace(go.Scatter(
        x=lx, y=ly, mode="text", text=ltext,
        textposition="middle center", textfont=dict(size=10, color="black"),
        hoverinfo="text", hovertext=lhover, showlegend=False
    ))

    # Transformers
    txs, tys, ttext, thover = [], [], [], []
    for idx in net.trafo.index:
        hv = int(net.trafo.at[idx, "hv_bus"])
        lv = int(net.trafo.at[idx, "lv_bus"])
        name = str(net.trafo.at[idx, "name"])
        x1, y1 = pos[hv]
        x2, y2 = pos[lv]

        loading = float(cont_trafo_loading.loc[idx])
        base_loading = float(base_trafo_loading.loc[idx])
        p_hv = float(cont_trafo_p_hv.loc[idx])

        if name == recommended_device:
            color, width, status = "darkred", 7, "Recommended upgrade candidate"
        elif loading > overload_limit:
            color, width, status = "red", 5, "Overloaded"
        else:
            color, width, status = "purple", 4, "OK"

        hover = (
            f"<b>{name}</b><br>Type: Transformer<br>Status: {status}<br>"
            f"Base loading: {base_loading:.2f}%<br>Contingency loading: {loading:.2f}%<br>"
            f"HV flow: {abs(p_hv):.2f} MW<br>HV bus: {net.bus.at[hv, 'name']}<br>LV bus: {net.bus.at[lv, 'name']}"
        )

        fig.add_trace(go.Scatter(
            x=[x1, x2], y=[y1, y2], mode="lines",
            line=dict(color=color, width=width, dash="dot"),
            hoverinfo="text", hovertext=hover, showlegend=False, name=name
        ))

        (c1x, c1y), (c2x, c2y) = _transformer_symbol_points(x1, y1, x2, y2, radius=0.55)
        fig.add_trace(_circle_trace(c1x, c1y, 0.48, color, hover))
        fig.add_trace(_circle_trace(c2x, c2y, 0.48, color, hover))

        label_x, label_y = _offset_point(x1, y1, x2, y2, offset=1.65)
        label_x += 0.95
        label = f"{name}<br>{loading:.1f}%"
        if name == recommended_device:
            label = f"<b>UPGRADE</b><br>{name}<br>{loading:.1f}%"
        txs.append(label_x); tys.append(label_y); ttext.append(label); thover.append(hover)

    fig.add_trace(go.Scatter(
        x=txs, y=tys, mode="text", text=ttext,
        textposition="middle center", textfont=dict(size=10, color="purple"),
        hoverinfo="text", hovertext=thover, showlegend=False
    ))

    # Buses
    bx, by, btext, bhover, bcolor = [], [], [], [], []
    for bus_idx in net.bus.index:
        x, y = pos[int(bus_idx)]
        name = str(net.bus.at[bus_idx, "name"])
        base_v = float(base_bus_voltage.loc[bus_idx])
        cont_v = float(cont_bus_voltage.loc[bus_idx])
        voltage_bad = cont_v < low_voltage_limit or cont_v > high_voltage_limit
        bx.append(x); by.append(y); btext.append(name)
        bcolor.append("orange" if voltage_bad else "lightgray")
        bhover.append(
            f"<b>{name}</b><br>Type: Bus<br>Nominal kV: {net.bus.at[bus_idx, 'vn_kv']}<br>"
            f"Base voltage: {base_v:.4f} pu<br>Contingency voltage: {cont_v:.4f} pu"
        )

    fig.add_trace(go.Scatter(
        x=bx, y=by, mode="markers+text",
        marker=dict(size=22, color=bcolor, line=dict(color="black", width=2)),
        text=btext, textposition="top center", textfont=dict(size=11, color="black"),
        hoverinfo="text", hovertext=bhover, showlegend=False
    ))

    # Generator labels
    gx, gy, gtext, ghover = [], [], [], []
    for idx in net.gen.index:
        bus = int(net.gen.at[idx, "bus"])
        x, y = pos[bus]
        name = str(net.gen.at[idx, "name"])
        p = float(net.gen.at[idx, "p_mw"])
        gx.append(x - 0.85); gy.append(y - 1.35)
        gtext.append(f"GEN<br>{name}")
        ghover.append(f"<b>{name}</b><br>Type: Generator<br>Dispatch: {p:.2f} MW<br>Bus: {net.bus.at[bus, 'name']}")

    fig.add_trace(go.Scatter(
        x=gx, y=gy, mode="markers+text",
        marker=dict(size=16, symbol="triangle-up", color="gold", line=dict(color="orange", width=2)),
        text=gtext, textposition="bottom center", textfont=dict(size=9, color="darkorange"),
        hoverinfo="text", hovertext=ghover, showlegend=False
    ))

    # Load labels
    loadx, loady, loadtext, loadhover = [], [], [], []
    for idx in net.load.index:
        bus = int(net.load.at[idx, "bus"])
        x, y = pos[bus]
        name = str(net.load.at[idx, "name"])
        p = float(net.load.at[idx, "p_mw"])
        q = float(net.load.at[idx, "q_mvar"])
        loadx.append(x + 0.85); loady.append(y - 1.65)
        loadtext.append(f"LOAD<br>{name}")
        loadhover.append(f"<b>{name}</b><br>Type: Load<br>P: {p:.2f} MW<br>Q: {q:.2f} MVAr<br>Bus: {net.bus.at[bus, 'name']}")

    fig.add_trace(go.Scatter(
        x=loadx, y=loady, mode="markers+text",
        marker=dict(size=15, symbol="square", color="mistyrose", line=dict(color="darkred", width=2)),
        text=loadtext, textposition="bottom center", textfont=dict(size=9, color="darkred"),
        hoverinfo="text", hovertext=loadhover, showlegend=False
    ))

    summary = (
        f"Recommended first upgrade: {recommended_device} | {recommended_type} | "
        f"Case: {recommended_case} | Outage: {recommended_outage} | "
        f"Failures: {recommended_row['failure_count']} | "
        f"Max Loading: {recommended_row['max_loading_percent']:.1f}% | "
        f"Score: {recommended_row['upgrade_priority_score']:.1f}"
    )

    fig.update_layout(
        title=dict(text="Interactive Multi-Basecase N-1 Study — One-Line Style Recommended Upgrade Plot", x=0.5, xanchor="center"),
        annotations=[
            dict(text=summary, x=0.5, y=-0.10, xref="paper", yref="paper", showarrow=False, align="center", font=dict(size=12), bordercolor="black", borderwidth=1, bgcolor="white", opacity=0.95),
            dict(text="Legend: blue dashed = outaged line | dark red = recommended upgrade | red = overloaded | orange bus = voltage violation | hover/zoom/pan for details", x=0.5, y=-0.17, xref="paper", yref="paper", showarrow=False, align="center", font=dict(size=11), bgcolor="white", opacity=0.9),
        ],
        height=920,
        margin=dict(l=20, r=20, t=70, b=155),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        plot_bgcolor="white",
        dragmode="pan",
    )
    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    return fig
