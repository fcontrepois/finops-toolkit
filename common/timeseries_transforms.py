#!/usr/bin/env python3
"""
Shared helpers for simple time-series CSV transformations.

These utilities are intentionally small and focused so they can be reused
by CLI tools such as add_step_change, add_spike, and add_deep without
pulling in heavier dependencies.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd


def read_input_csv(path: Optional[str]) -> pd.DataFrame:
    """Read a CSV file or stdin into a DataFrame."""
    import sys

    if path:
        return pd.read_csv(path)
    return pd.read_csv(sys.stdin)


def write_output_csv(df: pd.DataFrame, path: Optional[str]) -> None:
    """Write a DataFrame to a CSV file or stdout."""
    import sys

    if path:
        df.to_csv(path, index=False)
    else:
        df.to_csv(sys.stdout, index=False)


def ensure_datetime_column(df: pd.DataFrame, date_column: str) -> pd.DataFrame:
    """Ensure the date column exists and is a valid datetime."""
    if date_column not in df.columns:
        raise SystemExit(f"Missing date column: {date_column}")

    dates = pd.to_datetime(df[date_column], errors="coerce")
    if dates.isna().any():
        raise SystemExit(f"Invalid dates found in column {date_column}")
    df = df.copy()
    df[date_column] = dates
    return df


def sort_by_date(df: pd.DataFrame, date_column: str) -> pd.DataFrame:
    """Return a copy of the DataFrame sorted by the date column."""
    return df.sort_values(date_column).reset_index(drop=True)


def mask_from_start_date(df: pd.DataFrame, date_column: str, start_date: str) -> pd.Series:
    """Boolean mask selecting rows from start_date onward (inclusive)."""
    start = pd.to_datetime(start_date)
    return df[date_column] >= start


def mask_fixed_window_from_start(
    df: pd.DataFrame, date_column: str, start_date: str, length: int
) -> pd.Series:
    """
    Boolean mask selecting the first `length` rows with date >= start_date.

    Works for both daily and monthly series, regardless of gaps, by selecting
    based on sorted dates, not assumed frequency.
    """
    if length <= 0:
        raise SystemExit("--length must be >= 1")

    start = pd.to_datetime(start_date)
    eligible = df[df[date_column] >= start]
    if eligible.empty:
        raise SystemExit("No rows found at or after the specified start date")

    window_index = eligible.index[:length]
    return df.index.isin(window_index)


def apply_pct_or_value_change(
    df: pd.DataFrame,
    value_column: str,
    mask,
    pct: Optional[float] = None,
    value: Optional[float] = None,
    clamp_non_negative: bool = False,
) -> pd.DataFrame:
    """
    Apply either a percentage or absolute value change on rows where mask is True.

    pct is interpreted as a fractional change (e.g., 0.5 = +50%, -0.2 = -20%).
    value is interpreted as an additive change.
    """
    if (pct is None and value is None) or (pct is not None and value is not None):
        raise SystemExit("Specify exactly one of --pct or --value")

    if value_column not in df.columns:
        raise SystemExit(f"Missing value column: {value_column}")

    out = df.copy()
    series = out[value_column].astype(float)

    if pct is not None:
        series.loc[mask] = series.loc[mask] * (1.0 + pct)
    else:
        series.loc[mask] = series.loc[mask] + value  # type: ignore[arg-type]

    if clamp_non_negative:
        series = series.clip(lower=0.0)

    out[value_column] = series
    return out


def append_note_for_first_masked_row(
    df: pd.DataFrame,
    date_column: str,
    mask,
    note: Optional[str],
) -> pd.DataFrame:
    """
    Append a note to the first row where mask is True.

    - Creates a `note` column if it does not exist.
    - If the target row already has a note, the new note is appended on a new line.
    - If `note` is None or empty, the DataFrame is returned unchanged.
    """
    if not note:
        return df

    if date_column not in df.columns:
        raise SystemExit(f"Missing date column: {date_column}")

    out = df.copy()
    if "note" not in out.columns:
        out["note"] = ""

    masked_rows = out[mask]
    if masked_rows.empty:
        # Nothing to annotate; return unchanged
        return out

    first_idx = masked_rows.index.min()
    existing = out.at[first_idx, "note"]
    if pd.isna(existing) or existing == "":
        out.at[first_idx, "note"] = note
    else:
        out.at[first_idx, "note"] = f"{existing}\n{note}"

    return out


