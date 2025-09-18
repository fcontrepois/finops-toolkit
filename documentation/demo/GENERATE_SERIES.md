## generate_series.py — synthetic dataset generator

Create deterministic CSV time series for demos and tests.

Outputs a CSV with columns `PeriodStart` and `Cost` (customizable), suitable as input to `forecast_costs.py`.

### Install and setup

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### CLI usage

```bash
python demo/generate_series.py \
  --pattern {flat,upward_trend,downward_trend,seasonal,step_change,spike} \
  --granularity {daily,monthly} \
  --periods <N> \
  [--baseline <float>] [--trend <float>] \
  [--season-length <int>] [--amplitude <float>] \
  [--noise <0..1>] \
  [--step-index <int>] [--step-size <float>] \
  [--spike-index <int>] [--spike-size <float>] \
  [--date-column <str>] [--value-column <str>] \
  [--start YYYY-MM-DD] \
  --out <path.csv>
```

### Arguments

- pattern: shape of the series
  - `flat`: constant baseline
  - `upward_trend`: linear growth by `trend` per period
  - `downward_trend`: linear decline by `-trend` per period
  - `seasonal`: baseline + sin seasonality (`season-length`, `amplitude`) + optional linear `trend`
  - `step_change`: baseline with a jump of `step-size` from `step-index`
  - `spike`: one-off spike of `spike-size` at `spike-index`
- granularity: `daily` or `monthly`
- periods: number of rows to generate
- baseline: base value (default 100)
- trend: linear per-period delta (can be negative)
- season-length: cycle length (e.g., 30 for daily monthly-ish seasonality)
- amplitude: seasonal amplitude
- noise: multiplicative noise standard deviation (0 disables)
- step-index / step-size: for `step_change`
- spike-index / spike-size: for `spike`
- date-column / value-column: override column names
- start: first date; defaults to today (day=1 for monthly)
- out: output CSV path

Notes:
- Randomness uses a fixed seed for reproducibility.
- Values are clamped at 0 to avoid negatives.

### One-year daily examples

- Flat (no noise):
```bash
python demo/generate_series.py --pattern flat --granularity daily --periods 365 --baseline 100 --noise 0.0 --out demo/input/daily_flat.csv
```

- Predictable growth (no noise):
```bash
python demo/generate_series.py --pattern upward_trend --granularity daily --periods 365 --baseline 100 --trend 0.5 --noise 0.0 --out demo/input/daily_growth.csv
```

- Flat with single spike at day 120:
```bash
python demo/generate_series.py --pattern spike --granularity daily --periods 365 --baseline 100 --spike-index 120 --spike-size 20 --noise 0.0 --out demo/input/daily_flat_spike.csv
```

- Flat with step change halfway:
```bash
python demo/generate_series.py --pattern step_change --granularity daily --periods 365 --baseline 100 --step-size 50 --noise 0.0 --out demo/input/daily_flat_step.csv
```

- Seasonal + mild growth:
```bash
python demo/generate_series.py --pattern seasonal --granularity daily --periods 365 --baseline 100 --season-length 30 --amplitude 15 --trend 0.2 --noise 0.05 --out demo/input/daily_seasonal_growth.csv
```

### Piping into forecasting

```bash
python demo/generate_series.py --pattern flat --granularity daily --periods 365 --baseline 100 --noise 0.0 --out demo/input/daily_flat.csv
python forecast_costs.py --input demo/input/daily_flat.csv --date-column PeriodStart --value-column Cost --ensemble > demo/out/daily_flat_forecasts.csv
```

See also: `demo/Demo_Scenarios.md` for end-to-end scenarios and plotting.


