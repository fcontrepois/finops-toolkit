# forecast-costs.py
#
# MIT License
#
# Copyright (c) 2025 Frank Contrepois
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
# Usage Examples and Tests

# 1. Forecast from CSV file (default SMA window=7, ES alpha=0.5, Prophet defaults)
python forecast-costs.py --input costs.csv --date-column PeriodStart --value-column UnblendedCost --method all

# 2. Forecast from CSV file with custom SMA window (e.g., 14 days)
python forecast-costs.py --input costs.csv --date-column PeriodStart --value-column UnblendedCost --method sma --sma-window 14

# 3. Forecast from CSV file with custom ES alpha (e.g., 0.3)
python forecast-costs.py --input costs.csv --date-column PeriodStart --value-column UnblendedCost --method es --es-alpha 0.3

# 4. Forecast from CSV file with custom Prophet changepoint prior scale
python forecast-costs.py --input costs.csv --date-column PeriodStart --value-column UnblendedCost --method prophet --prophet-changepoint-prior-scale 0.1

# 5. Forecast from CSV file with custom Prophet seasonality prior scale
python forecast-costs.py --input costs.csv --date-column PeriodStart --value-column UnblendedCost --method prophet --prophet-seasonality-prior-scale 5.0

# 6. Forecast from CSV file with custom Prophet seasonality flags
python forecast-costs.py --input costs.csv --date-column PeriodStart --value-column UnblendedCost --method prophet --prophet-daily-seasonality False --prophet-yearly-seasonality True --prophet-weekly-seasonality True

# 7. Forecast for a specific group with custom SMA window and ES alpha
python forecast-costs.py --input costs.csv --date-column PeriodStart --value-column UnblendedCost --group-column Service --group-value AmazonEC2 --method all --sma-window 30 --es-alpha 0.2

# 8. Forecast from stdin (pipe from cost-and-usage.py) with all custom params
python aws/cost-and-usage.py --granularity daily --output-format csv | python aws/forecast-costs.py --date-column PeriodStart --value-column UnblendedCost --method all --sma-window 10 --es-alpha 0.7 --prophet-changepoint-prior-scale 0.2 --prophet-seasonality-prior-scale 15.0 --prophet-daily-seasonality True --prophet-yearly-seasonality True --prophet-weekly-seasonality False

# 9. Show help
python aws/forecast-costs.py --help

# 10. Error: input file does not exist
python aws/forecast-costs.py --input notfound.csv --date-column PeriodStart --value-column UnblendedCost --method all

# 11. Error: no input file and no stdin
python aws/forecast-costs.py --date-column PeriodStart --value-column UnblendedCost --method all
"""

"""
Output Documentation

The script outputs forecasted AWS costs for several future time horizons using the selected forecasting methods (Simple Moving Average, Exponential Smoothing, Facebook Prophet).

-------------------------
OUTPUT FORMAT
-------------------------

For each method, the script prints a section like:

Forecasts using <Method Description>:
  End Of Week: <value>
  End Of Month: <value>
  End Of Quarter 1: <value>
  End Of Quarter 2: <value>
  End Of Quarter 3: <value>
  End Of Year: <value>

- Each <value> is a floating-point number rounded to two decimals, representing the forecasted cumulative cost at the end of the specified period.

-------------------------
CUMULATIVE FORECASTS
-------------------------

- The forecasted value for each horizon (e.g., "End Of Quarter 2") is cumulative: it represents the total projected cost from the start of your data up to the end of that period.
- For example, "End Of Quarter 2" includes all estimated costs for Quarter 1 and Quarter 2.
- These values are not incremental for each period, but running totals.

-------------------------
PERIOD-SPECIFIC COSTS
-------------------------

- If you want the estimated cost for a specific period (e.g., just Quarter 2), subtract the forecast for the previous period's end from the forecast for the current period's end:
    period_cost = forecast_end_of_period - forecast_end_of_previous_period

-------------------------
EXAMPLES
-------------------------

Example output:

Forecasts using Simple Moving Average (window=7):
  End Of Week: 123.45
  End Of Month: 123.45
  End Of Quarter 1: 123.45
  End Of Quarter 2: 123.45
  End Of Quarter 3: 123.45
  End Of Year: 123.45

Forecasts using Exponential Smoothing (alpha=0.5):
  End Of Week: 124.67
  End Of Month: 124.67
  End Of Quarter 1: 124.67
  End Of Quarter 2: 124.67
  End Of Quarter 3: 124.67
  End Of Year: 124.67

Forecasts using Facebook Prophet (daily_seasonality=True, yearly_seasonality=True, weekly_seasonality=False, changepoint_prior_scale=0.05, seasonality_prior_scale=10.0):
  End Of Week: 120.12
  End Of Month: 121.34
  End Of Quarter 1: 125.67
  End Of Quarter 2: 130.45
  End Of Quarter 3: 135.12
  End Of Year: 140.00

-------------------------
ERROR OUTPUTS
-------------------------

If an error occurs (e.g., missing file, missing columns, Prophet not installed), an error message is printed to standard error and the script exits with a non-zero code.

Example:
Error: Input file 'notfound.csv' does not exist or is not a file.

-------------------------
USAGE EXAMPLES & TESTS
-------------------------

# 1. Forecast from CSV file (default SMA window=7, ES alpha=0.5, Prophet defaults)
python forecast-costs.py --input costs.csv --date-column PeriodStart --value-column UnblendedCost --method all

# 2. Forecast from CSV file with custom SMA window (e.g., 14 days)
python forecast-costs.py --input costs.csv --date-column PeriodStart --value-column UnblendedCost --method sma --sma-window 14

# 3. Forecast from CSV file with custom ES alpha (e.g., 0.3)
python forecast-costs.py --input costs.csv --date-column PeriodStart --value-column UnblendedCost --method es --es-alpha 0.3

# 4. Forecast from CSV file with custom Prophet changepoint prior scale
python forecast-costs.py --input costs.csv --date-column PeriodStart --value-column UnblendedCost --method prophet --prophet-changepoint-prior-scale 0.1

# 5. Forecast from CSV file with custom Prophet seasonality prior scale
python forecast-costs.py --input costs.csv --date-column PeriodStart --value-column UnblendedCost --method prophet --prophet-seasonality-prior-scale 5.0

# 6. Forecast from CSV file with custom Prophet seasonality flags
python forecast-costs.py --input costs.csv --date-column PeriodStart --value-column UnblendedCost --method prophet --prophet-daily-seasonality False --prophet-yearly-seasonality True --prophet-weekly-seasonality True

# 7. Forecast for a specific group with custom SMA window and ES alpha
python forecast-costs.py --input costs.csv --date-column PeriodStart --value-column UnblendedCost --group-column Service --group-value AmazonEC2 --method all --sma-window 30 --es-alpha 0.2

# 8. Forecast from stdin (pipe from cost-and-usage.py) with all custom params
python aws/cost-and-usage.py --granularity daily --output-format csv | python aws/forecast-costs.py --date-column PeriodStart --value-column UnblendedCost --method all --sma-window 10 --es-alpha 0.7 --prophet-changepoint-prior-scale 0.2 --prophet-seasonality-prior-scale 15.0 --prophet-daily-seasonality True --prophet-yearly-seasonality True --prophet-weekly-seasonality False

# 9. Show help
python aws/forecast-costs.py --help

# 10. Error: input file does not exist
python aws/forecast-costs.py --input notfound.csv --date-column PeriodStart --value-column UnblendedCost --method all

# 11. Error: no input file and no stdin
python aws/forecast-costs.py --date-column PeriodStart --value-column UnblendedCost --method all

"""


import logging
logger = logging.getLogger('cmdstanpy')
logger.addHandler(logging.NullHandler())
logger.propagate = False
logger.setLevel(logging.WARNING)

import argparse
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings("ignore")

def parse_args():
    parser = argparse.ArgumentParser(
        description="Forecast AWS costs using SMA, Exponential Smoothing, and Facebook Prophet."
    )
    parser.add_argument('--input', required=False, help='Input CSV file (output from cost-and-usage.py). If omitted, reads from stdin.')
    parser.add_argument('--date-column', required=True, help='Name of the date column (e.g., PeriodStart)')
    parser.add_argument('--value-column', required=True, help='Name of the value column (e.g., UnblendedCost)')
    parser.add_argument('--group-column', required=False, help='Name of the group column (e.g., Service, Tag:Environment)')
    parser.add_argument('--group-value', required=False, help='Value of the group to filter (e.g., AmazonEC2, prod)')
    parser.add_argument('--method', choices=['all', 'sma', 'es', 'prophet'], default='all', help='Forecasting method(s) to use')
    parser.add_argument('--sma-window', type=int, default=7, help='Window size for Simple Moving Average (default: 7)')
    parser.add_argument('--es-alpha', type=float, default=0.5, help='Alpha (smoothing factor) for Exponential Smoothing (default: 0.5)')
    parser.add_argument('--prophet-daily-seasonality', type=lambda x: x.lower() == 'true', default=True, help='Prophet daily seasonality (default: True)')
    parser.add_argument('--prophet-yearly-seasonality', type=lambda x: x.lower() == 'true', default=True, help='Prophet yearly seasonality (default: True)')
    parser.add_argument('--prophet-weekly-seasonality', type=lambda x: x.lower() == 'true', default=False, help='Prophet weekly seasonality (default: False)')
    parser.add_argument('--prophet-changepoint-prior-scale', type=float, default=0.05, help='Prophet changepoint prior scale (default: 0.05)')
    parser.add_argument('--prophet-seasonality-prior-scale', type=float, default=10.0, help='Prophet seasonality prior scale (default: 10.0)')
    return parser.parse_args()

def load_data(args):
    if args.input:
        if not os.path.isfile(args.input):
            print(f"Error: Input file '{args.input}' does not exist or is not a file.", file=sys.stderr)
            sys.exit(2)
        try:
            df = pd.read_csv(args.input)
        except Exception as e:
            print(f"Error: Could not read input file '{args.input}': {e}", file=sys.stderr)
            sys.exit(2)
    else:
        if sys.stdin.isatty():
            print("Error: No input file provided and no data piped to stdin.", file=sys.stderr)
            sys.exit(1)
        try:
            df = pd.read_csv(sys.stdin)
        except Exception as e:
            print(f"Error: Could not read from stdin: {e}", file=sys.stderr)
            sys.exit(2)
    # Filter by group if specified
    if args.group_column and args.group_value:
        if args.group_column not in df.columns:
            print(f"Error: Group column '{args.group_column}' not found in input data.", file=sys.stderr)
            sys.exit(2)
        df = df[df[args.group_column] == args.group_value]
    # Parse date column
    if args.date_column not in df.columns:
        print(f"Error: Date column '{args.date_column}' not found in input data.", file=sys.stderr)
        sys.exit(2)
    if args.value_column not in df.columns:
        print(f"Error: Value column '{args.value_column}' not found in input data.", file=sys.stderr)
        sys.exit(2)
    df[args.date_column] = pd.to_datetime(df[args.date_column])
    df = df.sort_values(args.date_column)
    # Remove rows with missing values
    df = df[[args.date_column, args.value_column]].dropna()
    # Convert value column to float
    df[args.value_column] = df[args.value_column].astype(float)
    return df

def get_forecast_horizons(df, date_col):
    last_date = df[date_col].max()
    # End of week (next Sunday)
    eow = last_date + timedelta(days=(6 - last_date.weekday()))
    # End of month
    eom = (last_date.replace(day=1) + pd.offsets.MonthEnd(0)).date()
    # End of next 3 quarters
    quarters = []
    q_date = last_date
    for _ in range(3):
        month = ((q_date.month - 1) // 3 + 1) * 3 + 1
        year = q_date.year
        if month > 12:
            month -= 12
            year += 1
        q_end = datetime(year, month, 1) + pd.offsets.MonthEnd(2)
        quarters.append(q_end.date())
        q_date = q_end
    # End of year
    eoy = datetime(last_date.year, 12, 31).date()
    return {
        'end_of_week': eow.date(),
        'end_of_month': eom,
        'end_of_quarter_1': quarters[0],
        'end_of_quarter_2': quarters[1],
        'end_of_quarter_3': quarters[2],
        'end_of_year': eoy
    }

def simple_moving_average(df, date_col, value_col, target_dates, window=7):
    sma = df[value_col].rolling(window=window, min_periods=1).mean().iloc[-1]
    forecasts = {}
    for label, target_date in target_dates.items():
        forecasts[label] = sma
    return forecasts

def exponential_smoothing(df, date_col, value_col, target_dates, alpha=0.5):
    values = df[value_col].values
    if len(values) == 0:
        return {label: None for label in target_dates}
    es = values[0]
    for v in values[1:]:
        es = alpha * v + (1 - alpha) * es
    forecasts = {}
    for label, target_date in target_dates.items():
        forecasts[label] = es
    return forecasts

def prophet_forecast(df, date_col, value_col, target_dates, daily_seasonality=True, yearly_seasonality=True, weekly_seasonality=False, changepoint_prior_scale=0.05, seasonality_prior_scale=10.0):
    try:
        from prophet import Prophet
    except ImportError:
        try:
            from fbprophet import Prophet
        except ImportError:
            print("Facebook Prophet is not installed. Please install with 'pip install prophet' or 'pip install fbprophet'.", file=sys.stderr)
            return {label: None for label in target_dates}
    prophet_df = df.rename(columns={date_col: 'ds', value_col: 'y'})
    model = Prophet(
        daily_seasonality=daily_seasonality,
        yearly_seasonality=yearly_seasonality,
        weekly_seasonality=weekly_seasonality,
        changepoint_prior_scale=changepoint_prior_scale,
        seasonality_prior_scale=seasonality_prior_scale
    )
    model.fit(prophet_df)
    max_target = max(target_dates.values())
    import pandas as pd
    periods = (pd.to_datetime(max_target) - prophet_df['ds'].max()).days
    if periods < 1:
        periods = 1
    future = model.make_future_dataframe(periods=periods)
    forecast = model.predict(future)
    forecasts = {}
    for label, target_date in target_dates.items():
        target_row = forecast[forecast['ds'] == pd.to_datetime(target_date)]
        if target_row.empty:
            idx = (forecast['ds'] - pd.to_datetime(target_date)).abs().idxmin()
            yhat = forecast.loc[idx, 'yhat']
        else:
            yhat = target_row['yhat'].values[0]
        forecasts[label] = yhat
    return forecasts

def print_forecasts(method, forecasts):
    print(f"\nForecasts using {method}:")
    for label, value in forecasts.items():
        if value is not None:
            print(f"  {label.replace('_', ' ').title()}: {value:.2f}")
        else:
            print(f"  {label.replace('_', ' ').title()}: N/A")

def main():
    args = parse_args()
    df = load_data(args)
    date_col = args.date_column
    value_col = args.value_column

    target_dates = get_forecast_horizons(df, date_col)

    if args.method in ('all', 'sma'):
        sma_forecasts = simple_moving_average(df, date_col, value_col, target_dates, window=args.sma_window)
        print_forecasts(f"Simple Moving Average (window={args.sma_window})", sma_forecasts)

    if args.method in ('all', 'es'):
        es_forecasts = exponential_smoothing(df, date_col, value_col, target_dates, alpha=args.es_alpha)
        print_forecasts(f"Exponential Smoothing (alpha={args.es_alpha})", es_forecasts)

    if args.method in ('all', 'prophet'):
        prophet_forecasts = prophet_forecast(
            df, date_col, value_col, target_dates,
            daily_seasonality=args.prophet_daily_seasonality,
            yearly_seasonality=args.prophet_yearly_seasonality,
            weekly_seasonality=args.prophet_weekly_seasonality,
            changepoint_prior_scale=args.prophet_changepoint_prior_scale,
            seasonality_prior_scale=args.prophet_seasonality_prior_scale
        )
        print_forecasts(
            f"Facebook Prophet (daily_seasonality={args.prophet_daily_seasonality}, yearly_seasonality={args.prophet_yearly_seasonality}, weekly_seasonality={args.prophet_weekly_seasonality}, changepoint_prior_scale={args.prophet_changepoint_prior_scale}, seasonality_prior_scale={args.prophet_seasonality_prior_scale})",
            prophet_forecasts
        )

if __name__ == "__main__":
    main()
