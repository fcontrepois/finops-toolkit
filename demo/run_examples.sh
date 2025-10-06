#!/usr/bin/env bash

set -euo pipefail

# Resolve repository root based on this script's location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

echo "[1/5] Preparing demo directories..."
mkdir -p demo/input demo/out
rm -f demo/input/*.csv || true
rm -f demo/out/*.csv demo/out/*.png || true

echo "[2/5] Generating input datasets..."
python demo/generate_series.py \
  --pattern upward_trend \
  --granularity monthly \
  --periods 36 \
  --noise 0.05 \
  --baseline 100 \
  --trend 3 \
  --out demo/input/monthly_upward.csv

python demo/generate_series.py \
  --pattern seasonal \
  --granularity daily \
  --periods 240 \
  --season-length 30 \
  --amplitude 15 \
  --baseline 80 \
  --trend 0.2 \
  --noise 0.08 \
  --out demo/input/daily_seasonal.csv

python demo/generate_series.py \
  --pattern step_change \
  --granularity monthly \
  --periods 30 \
  --baseline 120 \
  --step-size 70 \
  --out demo/input/monthly_step.csv

echo "[3/5] Producing forecasts..."
python forecast_costs.py \
  --input demo/input/monthly_upward.csv \
  --date-column PeriodStart \
  --value-column Cost \
  --ensemble \
  > demo/out/monthly_upward_forecasts.csv

python forecast_costs.py \
  --input demo/input/daily_seasonal.csv \
  --date-column PeriodStart \
  --value-column Cost \
  --sma-window 14 \
  --prophet-weekly-seasonality true \
  --ensemble \
  > demo/out/daily_seasonal_forecasts.csv

python forecast_costs.py \
  --input demo/input/monthly_step.csv \
  --date-column PeriodStart \
  --value-column Cost \
  --hw-alpha 0.4 \
  --hw-beta 0.2 \
  --hw-gamma 0.2 \
  --ensemble \
  > demo/out/monthly_step_forecasts.csv

echo "[4/5] Plotting example chart..."
python demo/plot_forecasts.py \
  --input demo/out/monthly_upward_forecasts.csv \
  --date-column PeriodStart \
  --value-column UnblendedCost \
  --algos sma es hw prophet ensemble \
  --title "Monthly Upward Trend" \
  --output demo/out/monthly_upward.png

echo "[5/5] Done. Outputs in demo/out and inputs in demo/input"


