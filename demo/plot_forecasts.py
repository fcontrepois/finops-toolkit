#!/usr/bin/env python3
"""
Plot actual vs forecast columns from forecast_costs.py CSV output.

Example:
  python aws/cost_and_usage.py --granularity daily | \
    python forecast_costs.py --date-column PeriodStart --value-column Cost --ensemble | \
    python demo/plot_forecasts.py --date-column PeriodStart --value-column Cost --algos sma es hw prophet ensemble

Or with a CSV file:
  python forecast_costs.py --input tests/input/daily_seasonal.csv --date-column PeriodStart --value-column Cost --ensemble > /tmp/out.csv
  python demo/plot_forecasts.py --input /tmp/out.csv --date-column PeriodStart --value-column Cost --algos sma es hw arima sarima theta prophet ensemble
"""

import argparse
import sys
import pandas as pd
import matplotlib.pyplot as plt
from typing import Optional


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plot forecasts from CSV")
    parser.add_argument("--input", help="Path to CSV. If omitted, read from stdin")
    parser.add_argument("--date-column", required=True)
    parser.add_argument("--value-column", required=True)
    parser.add_argument("--algos", nargs="+", required=True, help="Forecast columns to plot")
    parser.add_argument("--title", default="Forecast Comparison")
    parser.add_argument("--output", default=None, help="If provided, save figure to this path instead of showing")
    return parser.parse_args()


def read_csv(input_path: Optional[str]) -> pd.DataFrame:
    if input_path:
        return pd.read_csv(input_path)
    return pd.read_csv(sys.stdin)


def main() -> None:
    args = parse_args()
    df = read_csv(args.input)
    df[args.date_column] = pd.to_datetime(df[args.date_column])

    plt.figure(figsize=(12, 6))
    # Plot actuals
    plt.plot(df[args.date_column], df[args.value_column], label="actual", color="black", linewidth=2)

    # Plot forecasts
    for algo in args.algos:
        if algo in df.columns:
            plt.plot(df[args.date_column], df[algo], label=algo, linewidth=1)

    plt.title(args.title)
    plt.xlabel(args.date_column)
    plt.ylabel(args.value_column)
    plt.legend()
    plt.tight_layout()
    if args.output:
        plt.savefig(args.output, dpi=150)
        print(f"Saved figure to {args.output}")
    else:
        plt.show()


if __name__ == "__main__":
    main()



