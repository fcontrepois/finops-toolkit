#!/usr/bin/env python3
"""
Filter a forecast CSV to keep only the initial forecast horizon (next N days).

Assumes the CSV contains historical actuals followed by forecast rows (where
at least one forecast column is non-null). The script finds the first forecast
date, then keeps rows from that date up to N days after.

Input CSV schema (default): PeriodStart, Cost, [forecast columns]

Examples:
  python demo/filter_forecast_horizon.py --input demo/out/daily_flat_forecasts.csv --output demo/out/daily_flat_next_month.csv --days 30
  python demo/filter_forecast_horizon.py --input demo/out/daily_growth_forecasts.csv --output demo/out/daily_growth_next_year.csv --days 365
"""

import argparse
import pandas as pd


FORECAST_COLS = [
    'sma','es','hw','arima','sarima','theta','prophet','neural_prophet','darts','ensemble'
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Filter forecast CSV by horizon (days)")
    parser.add_argument("--input", required=True, help="Path to input forecast CSV")
    parser.add_argument("--output", required=True, help="Path to output CSV")
    parser.add_argument("--days", type=int, required=True, help="Number of days to keep starting from first forecast date")
    parser.add_argument("--date-column", default="PeriodStart", help="Date column name")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    df = pd.read_csv(args.input)
    if args.date_column not in df.columns:
        raise SystemExit(f"Missing date column: {args.date_column}")

    df[args.date_column] = pd.to_datetime(df[args.date_column])
    if not set(FORECAST_COLS) & set(df.columns):
        raise SystemExit("No forecast columns found in CSV")

    forecast_only = df[df[list(set(FORECAST_COLS) & set(df.columns))].notna().any(axis=1)].copy()
    if forecast_only.empty:
        raise SystemExit("No forecast rows found in CSV")

    start = forecast_only[args.date_column].min()
    end = start + pd.Timedelta(days=args.days)
    focused = df[(df[args.date_column] >= start) & (df[args.date_column] < end)]

    focused.to_csv(args.output, index=False)
    print(f"Wrote {len(focused)} rows to {args.output}")


if __name__ == "__main__":
    main()


