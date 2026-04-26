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

