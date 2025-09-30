#!/usr/bin/env python3
"""
Apply month-based multiplicative seasonality to a time series CSV.

Input CSV schema (default): PeriodStart, Cost
Output CSV schema: same as input, with Cost values multiplied by monthly factors.

Presets:
  - toys: peak in November and December
  - holidays: peaks in August, December, and February

Examples:
  python demo/add_seasonality.py \
    --input demo/input/monthly_flat.csv \
    --output demo/input/monthly_flat_toys.csv \
    --preset toys --date-column PeriodStart --value-column Cost

  python demo/add_seasonality.py \
    --input demo/input/monthly_flat.csv \
    --output demo/input/monthly_flat_custom.csv \
    --factors 1.0,1.05,1.02,0.98,0.95,0.97,1.00,1.10,1.03,1.05,1.20,1.30
"""

import argparse
import pandas as pd
from typing import List


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply monthly multiplicative seasonality to a CSV series")
    parser.add_argument("--input", required=True, help="Path to input CSV")
    parser.add_argument("--output", required=True, help="Path to output CSV")
    parser.add_argument("--date-column", default="PeriodStart", help="Date column name")
    parser.add_argument("--value-column", default="Cost", help="Value column name to scale")
    parser.add_argument("--preset", choices=["toys", "holidays"], help="Preset monthly profile")
    parser.add_argument("--factors", help="Comma-separated 12 floats for Jan..Dec (overrides preset)")
    return parser.parse_args()


def get_preset_factors(name: str) -> List[float]:
    if name == "toys":
        # Neutral most of the year, ramp in Nov/Dec
        return [
            0.95, 0.95, 0.97, 0.98, 1.00, 1.02,
            1.03, 1.05, 1.07, 1.10, 1.30, 1.40
        ]
    if name == "holidays":
        # Peaks in Aug, Dec, and smaller bump in Feb
        return [
            1.00, 1.08, 1.00, 0.98, 0.97, 0.98,
            1.00, 1.15, 1.02, 1.03, 1.05, 1.20
        ]
    raise ValueError(f"Unknown preset: {name}")


def parse_factors(s: str) -> List[float]:
    parts = [p.strip() for p in s.split(",") if p.strip()]
    if len(parts) != 12:
        raise SystemExit("--factors must specify exactly 12 comma-separated numbers for Jan..Dec")
    try:
        return [float(p) for p in parts]
    except ValueError:
        raise SystemExit("--factors contains non-numeric value(s)")


def main() -> None:
    args = parse_args()
    df = pd.read_csv(args.input)

    if args.value_column not in df.columns:
        raise SystemExit(f"Missing value column: {args.value_column}")
    if args.date_column not in df.columns:
        raise SystemExit(f"Missing date column: {args.date_column}")

    if args.factors:
        factors = parse_factors(args.factors)
    elif args.preset:
        factors = get_preset_factors(args.preset)
    else:
        raise SystemExit("Specify either --preset or --factors")

    # Ensure datetime and extract month index 1..12
    dates = pd.to_datetime(df[args.date_column], errors="coerce")
    if dates.isna().any():
        raise SystemExit(f"Invalid dates found in column {args.date_column}")

    month_idx = dates.dt.month - 1  # 0..11
    scale = month_idx.map(lambda m: factors[int(m)])

    df[args.value_column] = df[args.value_column].astype(float) * scale.to_numpy(dtype=float)

    df.to_csv(args.output, index=False)
    print(f"Applied seasonality; wrote {args.output}")


if __name__ == "__main__":
    main()




