#!/usr/bin/env python3
"""
Apply a permanent step change to a time series CSV.

Given a start date and either a percentage change or an absolute value change,
this command shifts all values from that date onward.

Examples:
  # +50% from 2025-05-01 onward
  python tools/add_step_change.py \
    --input input.csv --output output.csv \
    --start-date 2025-05-01 --pct 0.5

  # -20 units from 2025-06-15 onward
  python tools/add_step_change.py \
    --input input.csv --output output.csv \
    --start-date 2025-06-15 --value -20
"""

import argparse
from typing import Optional

from common.timeseries_transforms import (
    apply_pct_or_value_change,
    append_note_for_first_masked_row,
    ensure_datetime_column,
    mask_from_start_date,
    read_input_csv,
    sort_by_date,
    write_output_csv,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply a permanent step change from a given start date onward.")
    parser.add_argument("--input", help="Path to input CSV (if omitted, reads from stdin)")
    parser.add_argument("--output", help="Path to output CSV (if omitted, writes to stdout)")
    parser.add_argument("--date-column", default="PeriodStart", help="Date column name")
    parser.add_argument("--value-column", default="Cost", help="Value column to adjust")
    parser.add_argument(
        "--start-date",
        required=True,
        help="Start date (YYYY-MM-DD) at which to apply the step change",
    )
    parser.add_argument(
        "--pct",
        type=float,
        help="Fractional percentage change (e.g., 0.5 = +50%, -0.2 = -20%)",
    )
    parser.add_argument(
        "--value",
        type=float,
        help="Absolute additive change (e.g., 50 or -25)",
    )
    parser.add_argument(
        "--note",
        help="Optional explanatory note to attach on the step start date in the `note` column",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    df = read_input_csv(args.input)
    df = ensure_datetime_column(df, args.date_column)
    df = sort_by_date(df, args.date_column)

    mask = mask_from_start_date(df, args.date_column, args.start_date)
    if not mask.any():
        raise SystemExit("No rows found at or after the specified start date")

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

