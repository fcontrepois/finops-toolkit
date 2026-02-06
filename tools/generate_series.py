#!/usr/bin/env python3
"""
Generate synthetic CSV time series for forecasting demos.

Usage examples:
  python tools/generate_series.py --pattern upward_trend --granularity monthly --periods 36 --noise 0.05 --out demo/input/monthly_upward.csv
  # Note: Seasonality was removed from this generator. Use tools/add_seasonality.py to apply monthly profiles.

Patterns:
  - upward_trend: linear growth with noise
  - downward_trend: linear decline with noise
  - step_change: baseline with sudden jump at a given index
  - spike: baseline with one-off spike on a given index
  - flat: constant baseline with noise
"""

import argparse
import sys
from datetime import datetime
import numpy as np
import pandas as pd
from typing import Optional


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate synthetic time series CSV for demos")
    parser.add_argument("--pattern", required=True, choices=[
        "upward_trend", "downward_trend", "step_change", "spike", "flat"
    ])
    parser.add_argument("--granularity", required=True, choices=["daily", "monthly"])
    parser.add_argument("--periods", type=int, default=36)
    parser.add_argument("--baseline", type=float, default=100.0)
    parser.add_argument("--trend", type=float, default=1.0, help="Per-period change (use negative for downward)")
    parser.add_argument("--noise", type=float, default=0.05, help="Relative noise level, e.g., 0.05 = 5%")
    parser.add_argument("--step-index", type=int, default=None, help="Index of step change (0-based)")
    parser.add_argument("--step-size", type=float, default=50.0, help="Magnitude of step change")
    parser.add_argument("--spike-index", type=int, default=None, help="Index of spike (0-based)")
    parser.add_argument("--spike-size", type=float, default=100.0, help="Magnitude of spike")
    parser.add_argument("--date-column", default="PeriodStart")
    parser.add_argument("--value-column", default="Cost")
    parser.add_argument("--start", default=None, help="Start date (YYYY-MM-DD). Defaults to calculated start to end today.")
    parser.add_argument("--end-date", default=None, help="End date (YYYY-MM-DD). Defaults to today. If specified, start date is calculated backwards from end date.")
    parser.add_argument("--out", required=False, help="Output CSV path (if omitted, writes CSV to stdout)")
    return parser.parse_args()


def generate_dates(start_str: Optional[str], end_str: Optional[str], periods: int, granularity: str) -> pd.DatetimeIndex:
    if start_str:
        start = pd.to_datetime(start_str)
    elif end_str:
        # Calculate start date backwards from end date
        end = pd.to_datetime(end_str)
        if granularity == "monthly":
            start = end - pd.DateOffset(months=periods-1)
        else:
            start = end - pd.DateOffset(days=periods-1)
    else:
        # End today instead of starting today
        today = pd.Timestamp.today().normalize()
        # Calculate start date to end today
        if granularity == "monthly":
            start = today.replace(day=1) - pd.DateOffset(months=periods-1)
        else:
            start = today - pd.DateOffset(days=periods-1)
    freq = "MS" if granularity == "monthly" else "D"
    return pd.date_range(start=start, periods=periods, freq=freq)


def build_series(args: argparse.Namespace) -> np.ndarray:
    n = args.periods
    rng = np.random.default_rng(42)
    noise_scale = args.noise
    values = np.full(n, args.baseline, dtype=float)

    if args.pattern == "upward_trend":
        values += np.arange(n) * abs(args.trend)
    elif args.pattern == "downward_trend":
        values += np.arange(n) * (-abs(args.trend))
    elif args.pattern == "step_change":
        idx = args.step_index if args.step_index is not None else n // 2
        values[idx:] += args.step_size
    elif args.pattern == "spike":
        idx = args.spike_index if args.spike_index is not None else n // 3
        values[idx] += args.spike_size
    elif args.pattern == "flat":
        pass

    # Add multiplicative noise
    noise = rng.normal(0.0, noise_scale, size=n)
    values = values * (1.0 + noise)
    return np.maximum(values, 0.0)


def main() -> None:
    args = parse_args()
    dates = generate_dates(args.start, args.end_date, args.periods, args.granularity)
    series = build_series(args)

    df = pd.DataFrame({
        args.date_column: dates,
        args.value_column: series
    })

    if args.out:
        df.to_csv(args.out, index=False)
        # Avoid noisy stdout when used in pipes
    else:
        df.to_csv(sys.stdout, index=False)


if __name__ == "__main__":
    main()

