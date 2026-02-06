#!/usr/bin/env python3
"""
Add a fixed-duration positive spike to a time series CSV.

Given a start date, length, and a magnitude (percent or absolute), this command
applies a temporary increase to the selected window and then reverts to the
original baseline afterwards.

Examples:
  # +50% for 4 days starting on 2025-05-01
  python tools/add_spike.py \
    --input input.csv --output output.csv \
    --start-date 2025-05-01 --length 4 --pct 0.5

  # +20 units for 7 monthly periods starting on 2025-01-01
  python tools/add_spike.py \
    --input input.csv --output output.csv \
    --start-date 2025-01-01 --length 7 --value 20
"""

import argparse

from common.timeseries_transforms import (
    apply_pct_or_value_change,
    append_note_for_first_masked_row,
    ensure_datetime_column,
    mask_fixed_window_from_start,
    read_input_csv,
    sort_by_date,
    write_output_csv,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Add a fixed-duration positive spike to a time series CSV."
    )
    parser.add_argument("--input", help="Path to input CSV (if omitted, reads from stdin)")
    parser.add_argument("--output", help="Path to output CSV (if omitted, writes to stdout)")
    parser.add_argument("--date-column", default="PeriodStart", help="Date column name")
    parser.add_argument("--value-column", default="Cost", help="Value column to adjust")
    parser.add_argument(
        "--start-date",
        required=True,
        help="Start date (YYYY-MM-DD) at which the spike begins",
    )
    parser.add_argument(
        "--length",
        type=int,
        required=True,
        help="Number of periods to keep the spike applied (>= 1)",
    )
    parser.add_argument(
        "--pct",
        type=float,
        help="Positive fractional percentage change (e.g., 0.5 = +50%)",
    )
    parser.add_argument(
        "--value",
        type=float,
        help="Positive absolute additive change (e.g., 20)",
    )
    parser.add_argument(
        "--note",
        help="Optional explanatory note to attach on the spike start date in the `note` column",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.pct is not None and args.pct <= 0:
        raise SystemExit("--pct must be > 0 for add_spike")
    if args.value is not None and args.value <= 0:
        raise SystemExit("--value must be > 0 for add_spike")

    df = read_input_csv(args.input)
    df = ensure_datetime_column(df, args.date_column)
    df = sort_by_date(df, args.date_column)

    mask = mask_fixed_window_from_start(df, args.date_column, args.start_date, args.length)

    out = apply_pct_or_value_change(
        df,
        value_column=args.value_column,
        mask=mask,
        pct=args.pct,
        value=args.value,
        clamp_non_negative=True,
    )
    out = append_note_for_first_masked_row(out, args.date_column, mask, args.note)
    write_output_csv(out, args.output)


if __name__ == "__main__":
    main()

