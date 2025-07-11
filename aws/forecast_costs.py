# forecast_costs.py
#
# MIT License
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
#
# -----------------------------------------------------------------------------
# Documentation:
#   This script forecasts AWS costs using three algorithms: Simple Moving Average (SMA),
#   Exponential Smoothing (ES), and Facebook Prophet. It outputs a CSV table to stdout
#   with the same granularity as the input (daily or monthly), and for each forecasted
#   date, provides a column for each algorithm.
#
#   The output columns are:
#     - <date_column>: The date of the forecast
#     - <value_column>: The actual value (if available, else NaN)
#     - sma: Forecasted value using SMA (window configurable)
#     - es: Forecasted value using Exponential Smoothing (alpha configurable)
#     - prophet: Forecasted value using Prophet (if installed)
#
#   The forecast is a continuation of the input, i.e., the forecasted values start
#   after the last date in the input and continue for the next year (365 days for daily,
#   12 months for monthly).
#
# Examples of usage:
#
#   # 1. Forecast the next year (daily granularity) from a CSV file (default params)
#   python aws/forecast_costs.py --input costs.csv --date-column PeriodStart --value-column UnblendedCost
#
#   # 2. Forecast the next year (monthly granularity) from a monthly CSV file
#   python aws/forecast_costs.py --input costs.csv --date-column PeriodStart --value-column UnblendedCost
#
#   # 3. Forecast from stdin (pipe from cost_and_usage.py)
#   python aws/cost_and_usage.py --granularity daily --output-format csv | python aws/forecast_costs.py --date-column PeriodStart --value-column UnblendedCost
#
#   # 4. Use custom SMA window and ES alpha
#   python aws/forecast_costs.py --input costs.csv --date-column PeriodStart --value-column UnblendedCost --sma-window 14 --es-alpha 0.3
#
# -----------------------------------------------------------------------------

import argparse
import sys
import os
import pandas as pd
import numpy as np
from datetime import timedelta
import warnings

def parse_args():
    parser = argparse.ArgumentParser(
        description="Forecast AWS costs using SMA, Exponential Smoothing, and Prophet. Outputs a CSV with a column for each algorithm."
    )
    parser.add_argument('--input', required=False, help='Input CSV file. If omitted, reads from stdin.')
    parser.add_argument('--date-column', required=True, help='Name of the date column (e.g., PeriodStart)')
    parser.add_argument('--value-column', required=True, help='Name of the value column (e.g., UnblendedCost)')
    parser.add_argument('--sma-window', type=int, default=7, help='Window size for Simple Moving Average (default: 7)')
    parser.add_argument('--es-alpha', type=float, default=0.5, help='Alpha for Exponential Smoothing (default: 0.5)')
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
        df = pd.read_csv(args.input)
    else:
        if sys.stdin.isatty():
            print("Error: No input file provided and no data piped to stdin.", file=sys.stderr)
            sys.exit(1)
        df = pd.read_csv(sys.stdin)
    if args.date_column not in df.columns or args.value_column not in df.columns:
        print(f"Error: Required columns not found in input.", file=sys.stderr)
        sys.exit(2)
    df[args.date_column] = pd.to_datetime(df[args.date_column], errors='coerce')
    df = df.sort_values(args.date_column)
    df = df[[args.date_column, args.value_column]].dropna()
    df[args.value_column] = pd.to_numeric(df[args.value_column], errors='coerce')
    df = df.dropna(subset=[args.value_column])
    if df.empty:
        print("Error: No valid data after filtering and cleaning.", file=sys.stderr)
        sys.exit(2)
    return df

def infer_granularity(df, date_col):
    # If all dates are first of month, treat as monthly, else daily
    days = df[date_col].dt.day.unique()
    if set(days) == {1}:
        return 'monthly'
    freq = pd.infer_freq(df[date_col])
    if freq and freq.startswith('M'):
        return 'monthly'
    return 'daily'

def get_forecast_dates(last_date, granularity):
    dates = []
    if granularity == 'monthly':
        for i in range(1, 13):
            next_month = (last_date + pd.DateOffset(months=i)).replace(day=1)
            dates.append(next_month)
    else:
        for i in range(1, 366):
            dates.append(last_date + timedelta(days=i))
    return dates

def simple_moving_average_forecast(df, value_col, forecast_dates, window):
    last_sma = df[value_col].rolling(window=window, min_periods=1).mean().iloc[-1]
    return [last_sma] * len(forecast_dates)

def exponential_smoothing_forecast(df, value_col, forecast_dates, alpha):
    values = df[value_col].values
    es = values[0]
    for v in values[1:]:
        es = alpha * v + (1 - alpha) * es
    return [es] * len(forecast_dates)

def prophet_forecast(df, date_col, value_col, forecast_dates, args):
    try:
        from prophet import Prophet
    except ImportError:
        try:
            from fbprophet import Prophet
        except ImportError:
            warnings.warn("Prophet is not installed. Prophet forecast will be NaN.")
            return [np.nan] * len(forecast_dates)
    prophet_df = df.rename(columns={date_col: 'ds', value_col: 'y'})
    model = Prophet(
        daily_seasonality=args.prophet_daily_seasonality,
        yearly_seasonality=args.prophet_yearly_seasonality,
        weekly_seasonality=args.prophet_weekly_seasonality,
        changepoint_prior_scale=args.prophet_changepoint_prior_scale,
        seasonality_prior_scale=args.prophet_seasonality_prior_scale
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model.fit(prophet_df)
    future = pd.DataFrame({'ds': forecast_dates})
    forecast = model.predict(future)
    return forecast['yhat'].values

def main():
    args = parse_args()
    df = load_data(args)
    date_col = args.date_column
    value_col = args.value_column
    granularity = infer_granularity(df, date_col)
    last_date = df[date_col].max()
    forecast_dates = get_forecast_dates(last_date, granularity)

    # Prepare output DataFrame: all input + forecasted dates
    all_dates = list(df[date_col]) + forecast_dates
    all_dates = pd.Series(all_dates).drop_duplicates().sort_values()
    out_df = pd.DataFrame({date_col: all_dates})
    out_df = out_df.merge(df, on=date_col, how='left')

    # Compute forecasts for forecasted dates only
    sma_forecast = simple_moving_average_forecast(df, value_col, forecast_dates, args.sma_window)
    es_forecast = exponential_smoothing_forecast(df, value_col, forecast_dates, args.es_alpha)
    prophet_forecast_vals = prophet_forecast(df, date_col, value_col, forecast_dates, args)

    # Fill forecast columns: NaN for input dates, forecast for forecasted dates
    out_df['sma'] = np.nan
    out_df['es'] = np.nan
    out_df['prophet'] = np.nan

    forecast_mask = out_df[date_col].isin(forecast_dates)
    out_df.loc[forecast_mask, 'sma'] = sma_forecast
    out_df.loc[forecast_mask, 'es'] = es_forecast
    out_df.loc[forecast_mask, 'prophet'] = prophet_forecast_vals

    # Output as CSV to stdout
    out_df.to_csv(sys.stdout, index=False)

if __name__ == "__main__":
    main()
