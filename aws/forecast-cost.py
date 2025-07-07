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

# 1. Forecast from CSV file (daily granularity, group by SERVICE)
python forecast-costs.py --input costs.csv --date-column PeriodStart --value-column UnblendedCost --method all

# 2. Forecast from stdin (pipe from cost-and-usage.py)
python aws/cost-and-usage.py --granularity daily --output-format csv | python aws/forecast-costs.py --date-column PeriodStart --value-column UnblendedCost --method all

# 3. Forecast from CSV, only using Prophet
python aws/forecast-costs.py --input costs.csv --date-column PeriodStart --value-column UnblendedCost --method prophet

# 4. Forecast from CSV, only using SMA
python aws/forecast-costs.py --input costs.csv --date-column PeriodStart --value-column UnblendedCost --method sma

# 5. Forecast from CSV, only using Exponential Smoothing
python aws/forecast-costs.py --input costs.csv --date-column PeriodStart --value-column UnblendedCost --method es

# 6. Forecast for a specific group (e.g., Service=AmazonEC2)
python aws/forecast-costs.py --input costs.csv --date-column PeriodStart --value-column UnblendedCost --group-column Service --group-value AmazonEC2 --method all

# 7. Forecast for a specific tag (e.g., Tag:Environment=prod)
python aws/forecast-costs.py --input costs.csv --date-column PeriodStart --value-column UnblendedCost --group-column "Tag:Environment" --group-value prod --method all

# 8. Forecast from stdin for a group
python aws/cost-and-usage.py --granularity daily --output-format csv | python aws/forecast-costs.py --date-column PeriodStart --value-column UnblendedCost --group-column Service --group-value AmazonEC2 --method all

# 9. Show help
python aws/forecast-costs.py --help
"""

import argparse
import sys
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
    return parser.parse_args()

def load_data(args):
    if args.input:
        df = pd.read_csv(args.input)
    else:
        if sys.stdin.isatty():
            print("Error: No input file provided and no data piped to stdin.", file=sys.stderr)
            sys.exit(1)
        df = pd.read_csv(sys.stdin)
    # Filter by group if specified
    if args.group_column and args.group_value:
        df = df[df[args.group_column] == args.group_value]
    # Parse date column
    df[args.date_column] = pd.to_datetime(df[args.date_column])
    df = df.sort_values(args.date_column)
    # Remove rows with missing values
    df = df[[args.date_column, args.value_column]].dropna()
    # Convert value column to float
    df[args.value_column] = df[args.value_column].astype(float)
    return df

def get_forecast_horizons(df, date_col):
    last_date = df[date_col].max()
    freq = pd.infer_freq(df[date_col])
    if freq is None:
        freq = 'D'
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
    es = df[value_col].ewm(alpha=alpha, adjust=False).mean().iloc[-1]
    forecasts = {}
    for label, target_date in target_dates.items():
        forecasts[label] = es
    return forecasts

def prophet_forecast(df, date_col, value_col, target_dates):
    try:
        from prophet import Prophet
    except ImportError:
        try:
            from fbprophet import Prophet
        except ImportError:
            print("Facebook Prophet is not installed. Please install with 'pip install prophet' or 'pip install fbprophet'.", file=sys.stderr)
            return {label: None for label in target_dates}
    prophet_df = df.rename(columns={date_col: 'ds', value_col: 'y'})
    model = Prophet(daily_seasonality=True, yearly_seasonality=True)
    model.fit(prophet_df)
    max_target = max(target_dates.values())
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
        sma_forecasts = simple_moving_average(df, date_col, value_col, target_dates)
        print_forecasts("Simple Moving Average", sma_forecasts)

    if args.method in ('all', 'es'):
        es_forecasts = exponential_smoothing(df, date_col, value_col, target_dates)
        print_forecasts("Exponential Smoothing", es_forecasts)

    if args.method in ('all', 'prophet'):
        prophet_forecasts = prophet_forecast(df, date_col, value_col, target_dates)
        print_forecasts("Facebook Prophet", prophet_forecasts)

if __name__ == "__main__":
    main()
