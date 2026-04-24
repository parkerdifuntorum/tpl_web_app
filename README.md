# Interactive TPL-Style N-1 Study Sandbox

This Streamlit application is an interactive transmission planning sandbox built with Python, pandapower, pandas, matplotlib, and NetworkX.

It allows users to edit a meshed transmission/subtransmission network, add or remove base cases, run multi-basecase N-1 contingency analysis, visualize network results with automatic topology-based mapping, and generate upgrade recommendations based on repeated thermal overload behavior.

## Features

- Editable buses, lines, transformers, generators, and loads
- Editable base cases with generator dispatch columns
- Automatic network rebuild after table edits
- Automatic topology-based mapping after network changes
- Multi-basecase N-1 line contingency screening
- Line overload, transformer overload, and voltage violation detection
- Upgrade candidate ranking
- Recommended upgrade visualization
- CSV downloads for summary, violations, and upgrade ranking

## How to Run

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the app:

```bash
streamlit run app.py
```

## Study Logic

For each base case, the app:

1. Scales all loads by the selected load scale.
2. Applies generator dispatch values from the base-case table.
3. Runs the base-case power flow.
4. Sequentially outages each in-service line.
5. Re-runs power flow.
6. Records thermal and voltage violations.
7. Aggregates failed devices across all contingencies.
8. Recommends the highest-priority upgrade candidate.

## Upgrade Priority Score

The current scoring method is:

```text
Upgrade Priority Score =
  Failure Count × 10
+ Total Exceedance
+ Max Loading / 10
```

This favors devices that fail repeatedly across multiple contingencies and base cases.

## Auto-Mapping

The app uses NetworkX spring layout to automatically redraw the network whenever topology changes. This avoids hard-coded bus coordinates and supports quick topology experimentation.

Future versions can replace this with true GIS/geodata plotting using pandapower `geo` columns or imported utility/GIS coordinates.

## Future Advancements

Recommended next features:

- Transformer outage contingencies
- Generator outage contingencies
- N-1-1 sequential contingency analysis
- Save/load network cases to JSON
- True geodata support
- GIS/mapbox plotting
- Automated layout collision avoidance
- PV/QV voltage stability curves
- Short-circuit studies
- PDF report generation

## Engineering Learning Notes

The project supports studying how system behavior changes under different loading and dispatch conditions. One important observation from the earlier script-based version was that voltage can rise during light-load conditions, particularly at electrically remote buses. This is consistent with reduced reactive absorption and line charging effects in lightly loaded transmission corridors.

