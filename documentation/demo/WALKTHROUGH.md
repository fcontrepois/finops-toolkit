## Forecasting demo walkthrough (read‑aloud script + copy‑paste commands)

### Why this demo and what you'll see

Say: "In FinOps, we need simple, transparent forecasts to plan budgets and spot risk. This demo uses small, understandable models over synthetic datasets so we can see how each method behaves under different conditions (flat costs, steady growth, and occasional spikes)."

Say: "We'll generate a few datasets, run several forecasting approaches, and compare short-, medium-, and long‑horizon behavior. The goal is intuition: when does a method stay calm, when does it react fast, and how does it generalize beyond recent data?"

### What we’ll try

Say: "We’ll create synthetic time series with:"
- Flat baseline (no noise)
- Linear growth (no noise)
- Flat/growth with occasional positive spikes (≤10% and ≤20%)

Say: "For each, we’ll produce forecasts for the next month, quarter, and year, then plot actuals vs predictions."

### Algorithms in plain language

Say: "Here’s what each method tries to do, in simple terms:"
- SMA (Simple Moving Average): "Average of the last N points. Very stable, slow to react."
- ES (Exponential Smoothing): "Weighted average that favors recent data. Reacts faster than SMA."
- Holt‑Winters (Triple Exponential Smoothing): "Tracks level and trend (and seasonality if present). Good when there’s a slope and repeating patterns."
- ARIMA: "Statistical model for short‑term autocorrelation. Can capture persistence and mean‑reversion without seasonality."
- SARIMA: "ARIMA with seasonality. Useful if there’s a repeating weekly/monthly pattern."
- Theta: "Blend of level and trend lines. Often a strong baseline on simple series."
- Prophet: "Piecewise linear trend with changepoints plus seasonality priors. Adaptable when trends change."
- NeuralProphet: "Neural network version of Prophet—can fit flexible trends/seasonality; needs enough variation."
- Ensemble: "Average of available models to reduce variance and over‑/under‑reaction."

Note: "Optional models Darts (various algorithms) and NeuralProphet are off unless enabled; we’ll show how to turn them on."

Use the exact narration prompts (“Say: …”) while recording. Below each speaking line, copy‑paste the command shown.

Conventions:
- Inputs: `demo/input/`
- Outputs (forecasts + plots): `demo/out/`
- Columns: `PeriodStart` (date), `Cost` (value)

### 0) Setup (one time per shell)

```bash
source .venv/bin/activate
pip install -r requirements.txt
mkdir -p demo/input demo/out
```

Say: "I'll start by activating my environment and creating the input and output folders we'll use for the demo."

Say: "We'll use three tools. One, generate_series to create synthetic costs. Two, forecast_costs to run multiple forecasting methods. Three, plot_forecasts to visualize actuals versus forecasts."

Say: "Key flags are --date-column and --value-column, which we bind to PeriodStart and Cost; model tuning like --sma-window, --es-alpha, and Holt‑Winters --hw‑alpha, --hw‑beta, --hw‑gamma; and --ensemble to average the models. Prophet weekly seasonality can be toggled with --prophet-weekly-seasonality true on daily data."

Say: "To enable optional models: pass --neural-prophet to compute the NeuralProphet column, and --darts-algorithm <algo> (theta, exponential_smoothing, arima, auto_arima, linear_regression, random_forest, xgboost) to compute the Darts column. If omitted or if the library is missing, the CLI prints a tagged warning with an install hint and leaves that column as NaN."

Say: "The requirements include optional dependencies: statsmodels/pmdarima (ARIMA/SARIMA), u8darts (Darts), and neuralprophet (requires torch). Missing libs trigger warnings like [darts-missing] or [neuralprophet-missing] and the corresponding column will be NaN. On perfectly flat series, NeuralProphet may fail to train; the CLI detects constant series and falls back to a constant forecast for the neural_prophet column, emitting [neuralprophet-constant]."

Tip: "To enable both optional models in one run, add --neural-prophet --darts-algorithm theta."

---

### 1) Flat (no noise) — one‑year of daily data

Say: "First, a perfectly flat year with no noise."
```bash
python demo/generate_series.py \
  --pattern flat --granularity daily --periods 365 \
  --baseline 100 --noise 0.0 \
  --out demo/input/daily_flat.csv
```
Say: "This creates a constant series; --noise 0.0 ensures it's deterministic."

Say: "Now I run the forecaster and include an ensemble column which averages available models."
```bash
python forecast.py \
  --input demo/input/daily_flat.csv \
  --date-column PeriodStart --value-column Cost \
  --ensemble > demo/out/daily_flat_forecasts.csv
```
Say: "The output CSV contains the original values and one column per forecasting method."

Say: "For storytelling, I'll focus on three horizons: next month, next quarter, and next year. I'll plot each."
```bash
python demo/filter_forecast_horizon.py --input demo/out/daily_flat_forecasts.csv --output demo/out/daily_flat_next_month.csv --days 30
python demo/filter_forecast_horizon.py --input demo/out/daily_flat_forecasts.csv --output demo/out/daily_flat_next_quarter.csv --days 90
python demo/filter_forecast_horizon.py --input demo/out/daily_flat_forecasts.csv --output demo/out/daily_flat_next_year.csv --days 365

python demo/plot_forecasts.py --input demo/out/daily_flat_next_month.csv --date-column PeriodStart --value-column Cost --algos sma es hw prophet ensemble --title "Flat • Next Month" --output demo/out/daily_flat_next_month.png
python demo/plot_forecasts.py --input demo/out/daily_flat_next_quarter.csv --date-column PeriodStart --value-column Cost --algos sma es hw prophet ensemble --title "Flat • Next Quarter" --output demo/out/daily_flat_next_quarter.png
python demo/plot_forecasts.py --input demo/out/daily_flat_next_year.csv --date-column PeriodStart --value-column Cost --algos sma es hw prophet ensemble --title "Flat • Next Year" --output demo/out/daily_flat_next_year.png
```

---

### 2) Predictable growth (no noise)

Say: "Second, a predictable linear growth pattern—half a unit per day."
```bash
python demo/generate_series.py \
  --pattern upward_trend --granularity daily --periods 365 \
  --baseline 100 --trend 0.5 --noise 0.0 \
  --out demo/input/daily_growth.csv
```
Say: "The trend increases the baseline steadily; no noise keeps it clean for comparison."

Say: "I'll forecast and plot the same three horizons to compare model behavior under growth."
```bash
python forecast.py --input demo/input/daily_growth.csv --date-column PeriodStart --value-column Cost --ensemble > demo/out/daily_growth_forecasts.csv
python demo/filter_forecast_horizon.py --input demo/out/daily_growth_forecasts.csv --output demo/out/daily_growth_next_month.csv --days 30
python demo/filter_forecast_horizon.py --input demo/out/daily_growth_forecasts.csv --output demo/out/daily_growth_next_quarter.csv --days 90
python demo/filter_forecast_horizon.py --input demo/out/daily_growth_forecasts.csv --output demo/out/daily_growth_next_year.csv --days 365
python demo/plot_forecasts.py --input demo/out/daily_growth_next_month.csv --date-column PeriodStart --value-column Cost --algos sma es hw prophet ensemble --title "Growth • Next Month" --output demo/out/daily_growth_next_month.png
python demo/plot_forecasts.py --input demo/out/daily_growth_next_quarter.csv --date-column PeriodStart --value-column Cost --algos sma es hw prophet ensemble --title "Growth • Next Quarter" --output demo/out/daily_growth_next_quarter.png
python demo/plot_forecasts.py --input demo/out/daily_growth_next_year.csv --date-column PeriodStart --value-column Cost --algos sma es hw prophet ensemble --title "Growth • Next Year" --output demo/out/daily_growth_next_year.png
```

Say: "Notice Holt‑Winters usually tracks level and trend, while Prophet adapts trend via changepoints."

---

### 3) Flat with spikes (≤10% daily)

Say: "Third, I introduce occasional positive spikes up to ten percent on a flat baseline."
```bash
python demo/generate_series.py --pattern flat --granularity daily --periods 365 --baseline 100 --noise 0.0 --out demo/input/daily_flat_10_base.csv
python demo/add_spikes.py --input demo/input/daily_flat_10_base.csv --output demo/input/daily_flat_spikes_10.csv --max-pct 0.10 --prob 0.05
```
Say: "This applies bounded spikes (max ten percent) with a small daily probability, using a fixed seed for reproducibility."

Say: "I'll run forecasts and show how each model handles transient spikes over the three horizons."
```bash
python forecast.py --input demo/input/daily_flat_spikes_10.csv --date-column PeriodStart --value-column Cost --ensemble > demo/out/daily_flat_spikes_10_forecasts.csv
python demo/filter_forecast_horizon.py --input demo/out/daily_flat_spikes_10_forecasts.csv --output demo/out/daily_flat_spikes_10_next_month.csv --days 30
python demo/filter_forecast_horizon.py --input demo/out/daily_flat_spikes_10_forecasts.csv --output demo/out/daily_flat_spikes_10_next_quarter.csv --days 90
python demo/filter_forecast_horizon.py --input demo/out/daily_flat_spikes_10_forecasts.csv --output demo/out/daily_flat_spikes_10_next_year.csv --days 365
python demo/plot_forecasts.py --input demo/out/daily_flat_spikes_10_next_month.csv --date-column PeriodStart --value-column Cost --algos sma es hw prophet ensemble --title "Flat+Spikes≤10% • Next Month" --output demo/out/daily_flat_spikes_10_next_month.png
python demo/plot_forecasts.py --input demo/out/daily_flat_spikes_10_next_quarter.csv --date-column PeriodStart --value-column Cost --algos sma es hw prophet ensemble --title "Flat+Spikes≤10% • Next Quarter" --output demo/out/daily_flat_spikes_10_next_quarter.png
python demo/plot_forecasts.py --input demo/out/daily_flat_spikes_10_next_year.csv --date-column PeriodStart --value-column Cost --algos sma es hw prophet ensemble --title "Flat+Spikes≤10% • Next Year" --output demo/out/daily_flat_spikes_10_next_year.png
```

---

### 4) Flat with spikes (≤20% daily)

Say: "Fourth, same idea but with larger volatility—spikes up to twenty percent."

```bash
python demo/generate_series.py --pattern flat --granularity daily --periods 365 --baseline 100 --noise 0.0 --out demo/input/daily_flat_20_base.csv
python demo/add_spikes.py --input demo/input/daily_flat_20_base.csv --output demo/input/daily_flat_spikes_20.csv --max-pct 0.20 --prob 0.05

python forecast.py --input demo/input/daily_flat_spikes_20.csv --date-column PeriodStart --value-column Cost --ensemble > demo/out/daily_flat_spikes_20_forecasts.csv
python demo/filter_forecast_horizon.py --input demo/out/daily_flat_spikes_20_forecasts.csv --output demo/out/daily_flat_spikes_20_next_month.csv --days 30
python demo/filter_forecast_horizon.py --input demo/out/daily_flat_spikes_20_forecasts.csv --output demo/out/daily_flat_spikes_20_next_quarter.csv --days 90
python demo/filter_forecast_horizon.py --input demo/out/daily_flat_spikes_20_forecasts.csv --output demo/out/daily_flat_spikes_20_next_year.csv --days 365
python demo/plot_forecasts.py --input demo/out/daily_flat_spikes_20_next_month.csv --date-column PeriodStart --value-column Cost --algos sma es hw prophet ensemble --title "Flat+Spikes≤20% • Next Month" --output demo/out/daily_flat_spikes_20_next_month.png
python demo/plot_forecasts.py --input demo/out/daily_flat_spikes_20_next_quarter.csv --date-column PeriodStart --value-column Cost --algos sma es hw prophet ensemble --title "Flat+Spikes≤20% • Next Quarter" --output demo/out/daily_flat_spikes_20_next_quarter.png
python demo/plot_forecasts.py --input demo/out/daily_flat_spikes_20_next_year.csv --date-column PeriodStart --value-column Cost --algos sma es hw prophet ensemble --title "Flat+Spikes≤20% • Next Year" --output demo/out/daily_flat_spikes_20_next_year.png
```

---

### 5) Growth with spikes (≤10% daily)

Say: "Fifth, we combine growth with moderate spikes up to ten percent."

```bash
python demo/generate_series.py --pattern upward_trend --granularity daily --periods 365 --baseline 100 --trend 0.5 --noise 0.0 --out demo/input/daily_growth_10_base.csv
python demo/add_spikes.py --input demo/input/daily_growth_10_base.csv --output demo/input/daily_growth_spikes_10.csv --max-pct 0.10 --prob 0.05

python forecast.py --input demo/input/daily_growth_spikes_10.csv --date-column PeriodStart --value-column Cost --ensemble > demo/out/daily_growth_spikes_10_forecasts.csv
python demo/filter_forecast_horizon.py --input demo/out/daily_growth_spikes_10_forecasts.csv --output demo/out/daily_growth_spikes_10_next_month.csv --days 30
python demo/filter_forecast_horizon.py --input demo/out/daily_growth_spikes_10_forecasts.csv --output demo/out/daily_growth_spikes_10_next_quarter.csv --days 90
python demo/filter_forecast_horizon.py --input demo/out/daily_growth_spikes_10_forecasts.csv --output demo/out/daily_growth_spikes_10_next_year.csv --days 365
python demo/plot_forecasts.py --input demo/out/daily_growth_spikes_10_next_month.csv --date-column PeriodStart --value-column Cost --algos sma es hw prophet ensemble --title "Growth+Spikes≤10% • Next Month" --output demo/out/daily_growth_spikes_10_next_month.png
python demo/plot_forecasts.py --input demo/out/daily_growth_spikes_10_next_quarter.csv --date-column PeriodStart --value-column Cost --algos sma es hw prophet ensemble --title "Growth+Spikes≤10% • Next Quarter" --output demo/out/daily_growth_spikes_10_next_quarter.png
python demo/plot_forecasts.py --input demo/out/daily_growth_spikes_10_next_year.csv --date-column PeriodStart --value-column Cost --algos sma es hw prophet ensemble --title "Growth+Spikes≤10% • Next Year" --output demo/out/daily_growth_spikes_10_next_year.png
```

---

### 6) Growth with spikes (≤20% daily)

Say: "Finally, growth with larger spikes up to twenty percent, stressing the models."

```bash
python demo/generate_series.py --pattern upward_trend --granularity daily --periods 365 --baseline 100 --trend 0.5 --noise 0.0 --out demo/input/daily_growth_20_base.csv
python demo/add_spikes.py --input demo/input/daily_growth_20_base.csv --output demo/input/daily_growth_spikes_20.csv --max-pct 0.20 --prob 0.05

python forecast.py --input demo/input/daily_growth_spikes_20.csv --date-column PeriodStart --value-column Cost --ensemble > demo/out/daily_growth_spikes_20_forecasts.csv
python demo/filter_forecast_horizon.py --input demo/out/daily_growth_spikes_20_forecasts.csv --output demo/out/daily_growth_spikes_20_next_month.csv --days 30
python demo/filter_forecast_horizon.py --input demo/out/daily_growth_spikes_20_forecasts.csv --output demo/out/daily_growth_spikes_20_next_quarter.csv --days 90
python demo/filter_forecast_horizon.py --input demo/out/daily_growth_spikes_20_forecasts.csv --output demo/out/daily_growth_spikes_20_next_year.csv --days 365
python demo/plot_forecasts.py --input demo/out/daily_growth_spikes_20_next_month.csv --date-column PeriodStart --value-column Cost --algos sma es hw prophet ensemble --title "Growth+Spikes≤20% • Next Month" --output demo/out/daily_growth_spikes_20_next_month.png
python demo/plot_forecasts.py --input demo/out/daily_growth_spikes_20_next_quarter.csv --date-column PeriodStart --value-column Cost --algos sma es hw prophet ensemble --title "Growth+Spikes≤20% • Next Quarter" --output demo/out/daily_growth_spikes_20_next_quarter.png
python demo/plot_forecasts.py --input demo/out/daily_growth_spikes_20_next_year.csv --date-column PeriodStart --value-column Cost --algos sma es hw prophet ensemble --title "Growth+Spikes≤20% • Next Year" --output demo/out/daily_growth_spikes_20_next_year.png
```

---

### Closing notes (read aloud)
Say: "SMA is stable but slow to react, ES responds faster, Holt‑Winters models level and trend, and Prophet adapts trend via changepoints and seasonality."

Say: "The ensemble reduces variance by averaging models, often providing a robust baseline."

Say: "Short horizons emphasize recent behavior, while longer horizons show drift and uncertainty—this is important for budgeting and risk."


