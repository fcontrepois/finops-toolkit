## Forecast demo scenarios (daily inputs for one year)

This document outlines exactly how to reproduce the demo datasets, forecasts, and plots using the existing tools in `demo/`.

All scenarios use daily inputs covering one full year (365 days), and produce three plots per scenario focused on the next month (~30 days), next quarter (~90 days), and next year (~365 days) of forecasts.

Conventions:
- Inputs go to `demo/input/`
- Forecast CSVs and plots go to `demo/out/`
- Date column: `PeriodStart`, Value column: `Cost`

### 0) Setup

```bash
source .venv/bin/activate
pip install -r requirements.txt
mkdir -p demo/input demo/out
```

Helper function to filter forecast horizon and save a focused CSV (uses Python inline for reproducibility):

```bash
# Usage: filter_forecast_horizon <in_csv> <out_csv> <days>
filter_forecast_horizon() {
  IN_CSV="$1"; OUT_CSV="$2"; DAYS="$3";
  python - "$IN_CSV" "$OUT_CSV" "$DAYS" << 'PY'
import sys, pandas as pd

in_csv, out_csv, days = sys.argv[1], sys.argv[2], int(sys.argv[3])
df = pd.read_csv(in_csv)
df['PeriodStart'] = pd.to_datetime(df['PeriodStart'])

# Forecast rows are those where any forecast column is non-null
forecast_cols = ['sma','es','hw','arima','sarima','theta','prophet','neural_prophet','darts','ensemble']
forecast_only = df[df[forecast_cols].notna().any(axis=1)].copy()
start = forecast_only['PeriodStart'].min()
end = start + pd.Timedelta(days=days)
focused = df[(df['PeriodStart'] >= start) & (df['PeriodStart'] < end)]
focused.to_csv(out_csv, index=False)
print(f"Wrote {len(focused)} rows to {out_csv}")
PY
}
```

Helper to add random positive spikes up to a bounded percentage (keeps determinism via fixed seed):

```bash
# Usage: add_spikes <in_csv> <out_csv> <max_pct (e.g., 0.10)> <daily_prob (e.g., 0.05)>
add_spikes() {
  IN_CSV="$1"; OUT_CSV="$2"; MAX_PCT="$3"; PROB="$4";
  python - "$IN_CSV" "$OUT_CSV" "$MAX_PCT" "$PROB" << 'PY'
import sys, numpy as np, pandas as pd

in_csv, out_csv, max_pct, prob = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
rng = np.random.default_rng(42)
df = pd.read_csv(in_csv)
v = df['Cost'].to_numpy(dtype=float)
mask = rng.random(v.shape[0]) < prob
mult = 1.0 + rng.uniform(0.0, max_pct, size=v.shape[0])
v_spiked = v.copy()
v_spiked[mask] = v[mask] * mult[mask]
df['Cost'] = v_spiked
df.to_csv(out_csv, index=False)
print(f"Spikes applied to {(mask.sum())} days (max {max_pct*100:.0f}%); wrote {out_csv}")
PY
}
```

### 1) Scenario: Flat (no noise)

Generate input (365 days, daily):
```bash
python demo/generate_series.py \
  --pattern flat --granularity daily --periods 365 \
  --baseline 100 --noise 0.0 \
  --out demo/input/daily_flat.csv
```

Forecast and save CSV:
```bash
python forecast_costs.py \
  --input demo/input/daily_flat.csv \
  --date-column PeriodStart --value-column Cost \
  --ensemble > demo/out/daily_flat_forecasts.csv
```

Plots (next month / quarter / year):
```bash
filter_forecast_horizon demo/out/daily_flat_forecasts.csv demo/out/daily_flat_next_month.csv 30
filter_forecast_horizon demo/out/daily_flat_forecasts.csv demo/out/daily_flat_next_quarter.csv 90
filter_forecast_horizon demo/out/daily_flat_forecasts.csv demo/out/daily_flat_next_year.csv 365

python demo/plot_forecasts.py --input demo/out/daily_flat_next_month.csv --date-column PeriodStart --value-column Cost --algos sma es hw prophet ensemble --title "Flat • Next Month" --output demo/out/daily_flat_next_month.png
python demo/plot_forecasts.py --input demo/out/daily_flat_next_quarter.csv --date-column PeriodStart --value-column Cost --algos sma es hw prophet ensemble --title "Flat • Next Quarter" --output demo/out/daily_flat_next_quarter.png
python demo/plot_forecasts.py --input demo/out/daily_flat_next_year.csv --date-column PeriodStart --value-column Cost --algos sma es hw prophet ensemble --title "Flat • Next Year" --output demo/out/daily_flat_next_year.png
```

### 2) Scenario: Predictable growth (no noise)

Generate input:
```bash
python demo/generate_series.py \
  --pattern upward_trend --granularity daily --periods 365 \
  --baseline 100 --trend 0.5 --noise 0.0 \
  --out demo/input/daily_growth.csv
```

Forecast and plots (same steps/names):
```bash
python forecast_costs.py --input demo/input/daily_growth.csv --date-column PeriodStart --value-column Cost --ensemble > demo/out/daily_growth_forecasts.csv
filter_forecast_horizon demo/out/daily_growth_forecasts.csv demo/out/daily_growth_next_month.csv 30
filter_forecast_horizon demo/out/daily_growth_forecasts.csv demo/out/daily_growth_next_quarter.csv 90
filter_forecast_horizon demo/out/daily_growth_forecasts.csv demo/out/daily_growth_next_year.csv 365
python demo/plot_forecasts.py --input demo/out/daily_growth_next_month.csv --date-column PeriodStart --value-column Cost --algos sma es hw prophet ensemble --title "Growth • Next Month" --output demo/out/daily_growth_next_month.png
python demo/plot_forecasts.py --input demo/out/daily_growth_next_quarter.csv --date-column PeriodStart --value-column Cost --algos sma es hw prophet ensemble --title "Growth • Next Quarter" --output demo/out/daily_growth_next_quarter.png
python demo/plot_forecasts.py --input demo/out/daily_growth_next_year.csv --date-column PeriodStart --value-column Cost --algos sma es hw prophet ensemble --title "Growth • Next Year" --output demo/out/daily_growth_next_year.png
```

### 3) Scenario: Flat with spikes (max 10% daily)

Generate base (flat, no noise), then apply bounded spikes (deterministic):
```bash
python demo/generate_series.py --pattern flat --granularity daily --periods 365 --baseline 100 --noise 0.0 --out demo/input/daily_flat_10_base.csv
add_spikes demo/input/daily_flat_10_base.csv demo/input/daily_flat_spikes_10.csv 0.10 0.05
```

Forecast and plots:
```bash
python forecast_costs.py --input demo/input/daily_flat_spikes_10.csv --date-column PeriodStart --value-column Cost --ensemble > demo/out/daily_flat_spikes_10_forecasts.csv
filter_forecast_horizon demo/out/daily_flat_spikes_10_forecasts.csv demo/out/daily_flat_spikes_10_next_month.csv 30
filter_forecast_horizon demo/out/daily_flat_spikes_10_forecasts.csv demo/out/daily_flat_spikes_10_next_quarter.csv 90
filter_forecast_horizon demo/out/daily_flat_spikes_10_forecasts.csv demo/out/daily_flat_spikes_10_next_year.csv 365
python demo/plot_forecasts.py --input demo/out/daily_flat_spikes_10_next_month.csv --date-column PeriodStart --value-column Cost --algos sma es hw prophet ensemble --title "Flat+Spikes≤10% • Next Month" --output demo/out/daily_flat_spikes_10_next_month.png
python demo/plot_forecasts.py --input demo/out/daily_flat_spikes_10_next_quarter.csv --date-column PeriodStart --value-column Cost --algos sma es hw prophet ensemble --title "Flat+Spikes≤10% • Next Quarter" --output demo/out/daily_flat_spikes_10_next_quarter.png
python demo/plot_forecasts.py --input demo/out/daily_flat_spikes_10_next_year.csv --date-column PeriodStart --value-column Cost --algos sma es hw prophet ensemble --title "Flat+Spikes≤10% • Next Year" --output demo/out/daily_flat_spikes_10_next_year.png
```

### 4) Scenario: Flat with spikes (max 20% daily)

```bash
python demo/generate_series.py --pattern flat --granularity daily --periods 365 --baseline 100 --noise 0.0 --out demo/input/daily_flat_20_base.csv
add_spikes demo/input/daily_flat_20_base.csv demo/input/daily_flat_spikes_20.csv 0.20 0.05

python forecast_costs.py --input demo/input/daily_flat_spikes_20.csv --date-column PeriodStart --value-column Cost --ensemble > demo/out/daily_flat_spikes_20_forecasts.csv
filter_forecast_horizon demo/out/daily_flat_spikes_20_forecasts.csv demo/out/daily_flat_spikes_20_next_month.csv 30
filter_forecast_horizon demo/out/daily_flat_spikes_20_forecasts.csv demo/out/daily_flat_spikes_20_next_quarter.csv 90
filter_forecast_horizon demo/out/daily_flat_spikes_20_forecasts.csv demo/out/daily_flat_spikes_20_next_year.csv 365
python demo/plot_forecasts.py --input demo/out/daily_flat_spikes_20_next_month.csv --date-column PeriodStart --value-column Cost --algos sma es hw prophet ensemble --title "Flat+Spikes≤20% • Next Month" --output demo/out/daily_flat_spikes_20_next_month.png
python demo/plot_forecasts.py --input demo/out/daily_flat_spikes_20_next_quarter.csv --date-column PeriodStart --value-column Cost --algos sma es hw prophet ensemble --title "Flat+Spikes≤20% • Next Quarter" --output demo/out/daily_flat_spikes_20_next_quarter.png
python demo/plot_forecasts.py --input demo/out/daily_flat_spikes_20_next_year.csv --date-column PeriodStart --value-column Cost --algos sma es hw prophet ensemble --title "Flat+Spikes≤20% • Next Year" --output demo/out/daily_flat_spikes_20_next_year.png
```

### 5) Scenario: Growth with spikes (max 10% daily)

```bash
python demo/generate_series.py --pattern upward_trend --granularity daily --periods 365 --baseline 100 --trend 0.5 --noise 0.0 --out demo/input/daily_growth_10_base.csv
add_spikes demo/input/daily_growth_10_base.csv demo/input/daily_growth_spikes_10.csv 0.10 0.05

python forecast_costs.py --input demo/input/daily_growth_spikes_10.csv --date-column PeriodStart --value-column Cost --ensemble > demo/out/daily_growth_spikes_10_forecasts.csv
filter_forecast_horizon demo/out/daily_growth_spikes_10_forecasts.csv demo/out/daily_growth_spikes_10_next_month.csv 30
filter_forecast_horizon demo/out/daily_growth_spikes_10_forecasts.csv demo/out/daily_growth_spikes_10_next_quarter.csv 90
filter_forecast_horizon demo/out/daily_growth_spikes_10_forecasts.csv demo/out/daily_growth_spikes_10_next_year.csv 365
python demo/plot_forecasts.py --input demo/out/daily_growth_spikes_10_next_month.csv --date-column PeriodStart --value-column Cost --algos sma es hw prophet ensemble --title "Growth+Spikes≤10% • Next Month" --output demo/out/daily_growth_spikes_10_next_month.png
python demo/plot_forecasts.py --input demo/out/daily_growth_spikes_10_next_quarter.csv --date-column PeriodStart --value-column Cost --algos sma es hw prophet ensemble --title "Growth+Spikes≤10% • Next Quarter" --output demo/out/daily_growth_spikes_10_next_quarter.png
python demo/plot_forecasts.py --input demo/out/daily_growth_spikes_10_next_year.csv --date-column PeriodStart --value-column Cost --algos sma es hw prophet ensemble --title "Growth+Spikes≤10% • Next Year" --output demo/out/daily_growth_spikes_10_next_year.png
```

### 6) Scenario: Growth with spikes (max 20% daily)

```bash
python demo/generate_series.py --pattern upward_trend --granularity daily --periods 365 --baseline 100 --trend 0.5 --noise 0.0 --out demo/input/daily_growth_20_base.csv
add_spikes demo/input/daily_growth_20_base.csv demo/input/daily_growth_spikes_20.csv 0.20 0.05

python forecast_costs.py --input demo/input/daily_growth_spikes_20.csv --date-column PeriodStart --value-column Cost --ensemble > demo/out/daily_growth_spikes_20_forecasts.csv
filter_forecast_horizon demo/out/daily_growth_spikes_20_forecasts.csv demo/out/daily_growth_spikes_20_next_month.csv 30
filter_forecast_horizon demo/out/daily_growth_spikes_20_forecasts.csv demo/out/daily_growth_spikes_20_next_quarter.csv 90
filter_forecast_horizon demo/out/daily_growth_spikes_20_forecasts.csv demo/out/daily_growth_spikes_20_next_year.csv 365
python demo/plot_forecasts.py --input demo/out/daily_growth_spikes_20_next_month.csv --date-column PeriodStart --value-column Cost --algos sma es hw prophet ensemble --title "Growth+Spikes≤20% • Next Month" --output demo/out/daily_growth_spikes_20_next_month.png
python demo/plot_forecasts.py --input demo/out/daily_growth_spikes_20_next_quarter.csv --date-column PeriodStart --value-column Cost --algos sma es hw prophet ensemble --title "Growth+Spikes≤20% • Next Quarter" --output demo/out/daily_growth_spikes_20_next_quarter.png
python demo/plot_forecasts.py --input demo/out/daily_growth_spikes_20_next_year.csv --date-column PeriodStart --value-column Cost --algos sma es hw prophet ensemble --title "Growth+Spikes≤20% • Next Year" --output demo/out/daily_growth_spikes_20_next_year.png
```

Notes:
- If `statsmodels` is not installed, `arima`/`sarima` columns will be NaN; install via `pip install statsmodels` to enable them.
- For Prophet weekly seasonality on daily data, add `--prophet-weekly-seasonality true` to `forecast_costs.py` commands.
- The spike helper adds positive spikes only; adjust as needed for negative anomalies.


