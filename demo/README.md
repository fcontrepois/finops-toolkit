## Forecast demo toolkit

This folder helps you record short, clear videos that compare forecasting algorithms and flags using deterministic, synthetic datasets.

Directory layout:
- `demo/input`: generated input CSVs (actuals)
- `demo/out`: forecast CSVs and saved plots

### 1) Setup and activate

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Prophet is optional; if not installed, the `prophet` column will be NaN.

### 2) One-command demo (recommended)

```bash
bash demo/run_examples.sh
```

This cleans `demo/input` and `demo/out`, generates inputs, runs forecasts, and saves plots.

### 3) Manual step-by-step

Generate inputs:
```bash
python demo/generate_series.py --pattern upward_trend --granularity monthly --periods 36 --noise 0.05 --baseline 100 --trend 3 --out demo/input/monthly_upward.csv
python demo/generate_series.py --pattern seasonal --granularity daily --periods 240 --season-length 30 --amplitude 15 --baseline 80 --trend 0.2 --noise 0.08 --out demo/input/daily_seasonal.csv
python demo/generate_series.py --pattern step_change --granularity monthly --periods 30 --baseline 120 --step-size 70 --out demo/input/monthly_step.csv
```

Produce forecasts:
```bash
python forecast_costs.py --input demo/input/monthly_upward.csv --date-column PeriodStart --value-column Cost --ensemble > demo/out/monthly_upward_forecasts.csv
python forecast_costs.py --input demo/input/daily_seasonal.csv --date-column PeriodStart --value-column Cost --sma-window 14 --prophet-weekly-seasonality true --ensemble > demo/out/daily_seasonal_forecasts.csv
python forecast_costs.py --input demo/input/monthly_step.csv --date-column PeriodStart --value-column Cost --hw-alpha 0.4 --hw-beta 0.2 --hw-gamma 0.2 --ensemble > demo/out/monthly_step_forecasts.csv
```

Plot for screen recording (use `--output` to save PNG):
```bash
python demo/plot_forecasts.py --input demo/out/monthly_upward_forecasts.csv --date-column PeriodStart --value-column UnblendedCost --algos sma es hw prophet ensemble --title "Monthly Upward Trend" --output demo/out/monthly_upward.png
```

You can also pipe directly from a CLI producing costs:
```bash
python aws/cost_and_usage.py --granularity daily | \
python forecast_costs.py --date-column PeriodStart --value-column Cost --ensemble | \
python demo/plot_forecasts.py --date-column PeriodStart --value-column UnblendedCost --algos sma es hw prophet ensemble --title "Piped Daily"
```

### Suggested video beats

- Baseline dataset and actuals
- Compare **SMA** vs **ES** vs **HW** on trend
- Add **Prophet**; toggle weekly/yearly seasonality flags
- Show **ARIMA/SARIMA** if `statsmodels` is installed
- Enable `--ensemble` and discuss stability/variance
- Stress-test with step change and spike datasets

Tip: Keep terminal font large, zoom the plot, and narrate flag changes.



