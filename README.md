# Interactive TPL-Style N-1 Study Sandbox

This Streamlit app is an editable transmission planning sandbox using pandapower, pandas, NetworkX, and Plotly.

## Features

- Editable buses, lines, transformers, generators, loads, external grid, and base cases
- 12.5 kV generator terminal buses with explicit GSU transformers
- Voltage-level validation for lines
- Multi-basecase line N-1 contingency studies
- Line overload, transformer overload, low-voltage, and high-voltage detection
- Upgrade candidate ranking
- Interactive Plotly one-line style visualization with zoom, pan, hover details, visible device names, and transformer symbols

## Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Modeling Notes

Lines must connect buses at the same voltage level. Use transformers for voltage transitions. The default model uses:

- 230 kV transmission buses
- 115 kV subtransmission buses
- 12.5 kV generator terminal buses
- Explicit generator step-up transformers

## Visualization Notes

The one-line diagram is interactive. Use browser zoom/pan and hover over devices to inspect loading, voltage, flow, and upgrade-candidate details.



## Layout Update

The interactive one-line plot now uses a deterministic layered layout for the default model. This reduces non-connected line crossings by separating voltage levels into rows:

- 230 kV buses on the upper row
- 115 kV buses on the middle row
- 12.5 kV generator terminal buses below or above their point of interconnection

If users add custom buses that do not match the default naming pattern, the app falls back to wide NetworkX placement for those additional nodes.


## Topology Revision

The default network was revised to remove the following lines:

- Line 1-3
- Line 2-3 B
- Line 4-7 Tie
- Line 5-7

The remaining 230 kV path uses `Line 1-2` and `Line 2-3`. The previous `Line 2-3 A` was renamed to `Line 2-3`.


## Slack Bus / Switching Node Revision

The default topology now separates the slack/grid source from the first 230 kV switching node:

- `Bus 0 - Slack / Grid Source` is the external grid/slack bus.
- `Bus 1 - 230 kV Switching Node` connects to:
  - `Line 0-1`
  - `Line 1-2`
  - `Transformer 1-7`
- The slack bus also connects directly to Bus 3 through `Line 0-3`.

This creates a more realistic distinction between the grid reference/source and the nearby 230 kV switching/interconnection node.
