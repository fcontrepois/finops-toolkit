#!/usr/bin/env python3
"""
Add bounded positive spikes to a time series CSV for demo scenarios.

Input CSV schema (default): PeriodStart, Cost
Output CSV schema: same as input, with Cost values spiked on random days.

Examples:
  python demo/add_spikes.py --input demo/input/daily_flat.csv --output demo/input/daily_flat_spikes_10.csv --max-pct 0.10 --prob 0.05
  python demo/add_spikes.py --input demo/input/daily_growth.csv --output demo/input/daily_growth_spikes_20.csv --max-pct 0.20 --prob 0.05 --value-column Cost
"""

import argparse
import numpy as np
import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Add bounded positive spikes to a CSV series")
    parser.add_argument("--input", required=True, help="Path to input CSV")
    parser.add_argument("--output", required=True, help="Path to output CSV")
    parser.add_argument("--max-pct", type=float, required=True, help="Maximum spike magnitude as fraction (e.g., 0.10 = 10%)")
    parser.add_argument("--prob", type=float, default=0.05, help="Daily probability of a spike (0..1)")
    parser.add_argument("--date-column", default="PeriodStart", help="Date column name")
    parser.add_argument("--value-column", default="Cost", help="Value column name to spike")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for determinism")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rng = np.random.default_rng(args.seed)

    df = pd.read_csv(args.input)
    if args.value_column not in df.columns:
        raise SystemExit(f"Missing value column: {args.value_column}")

    values = df[args.value_column].to_numpy(dtype=float)
    mask = rng.random(values.shape[0]) < args.prob
    multipliers = 1.0 + rng.uniform(0.0, args.max_pct, size=values.shape[0])

    spiked = values.copy()
    spiked[mask] = values[mask] * multipliers[mask]
    df[args.value_column] = spiked

    df.to_csv(args.output, index=False)
    print(f"Spikes applied to {int(mask.sum())} rows; wrote {args.output}")


if __name__ == "__main__":
    main()


