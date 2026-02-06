#!/usr/bin/env python3

import pandas as pd

from common.timeseries_transforms import (
    apply_pct_or_value_change,
    append_note_for_first_masked_row,
    ensure_datetime_column,
    mask_fixed_window_from_start,
    mask_from_start_date,
    sort_by_date,
)


def _make_df():
    dates = pd.date_range("2025-01-01", periods=10, freq="D")
    return pd.DataFrame({"PeriodStart": dates, "Cost": [100.0] * len(dates)})


def test_add_step_change_pct_positive():
    df = _make_df()
    df = ensure_datetime_column(df, "PeriodStart")
    df = sort_by_date(df, "PeriodStart")

    mask = mask_from_start_date(df, "PeriodStart", "2025-01-06")
    out = apply_pct_or_value_change(df, "Cost", mask, pct=0.5)

    # First 5 days unchanged
    assert (out.loc[:4, "Cost"] == 100.0).all()
    # From 6th day onward, +50%
    assert (out.loc[5:, "Cost"] == 150.0).all()


def test_add_step_change_value_negative():
    df = _make_df()
    df = ensure_datetime_column(df, "PeriodStart")
    df = sort_by_date(df, "PeriodStart")

    mask = mask_from_start_date(df, "PeriodStart", "2025-01-04")
    out = apply_pct_or_value_change(df, "Cost", mask, value=-20.0)

    # First 3 days unchanged
    assert (out.loc[:2, "Cost"] == 100.0).all()
    # From 4th day onward, -20
    assert (out.loc[3:, "Cost"] == 80.0).all()


def test_fixed_duration_spike_pct():
    df = _make_df()
    df = ensure_datetime_column(df, "PeriodStart")
    df = sort_by_date(df, "PeriodStart")

    mask = mask_fixed_window_from_start(df, "PeriodStart", "2025-01-03", length=4)
    out = apply_pct_or_value_change(df, "Cost", mask, pct=0.25)

    # Rows 0-1 unchanged
    assert (out.loc[:1, "Cost"] == 100.0).all()
    # Rows 2-5 spiked by +25%
    assert (out.loc[2:5, "Cost"] == 125.0).all()
    # Remaining rows unchanged
    assert (out.loc[6:, "Cost"] == 100.0).all()


def test_fixed_duration_deep_value_clamped():
    df = _make_df()
    df = ensure_datetime_column(df, "PeriodStart")
    df = sort_by_date(df, "PeriodStart")

    mask = mask_fixed_window_from_start(df, "PeriodStart", "2025-01-01", length=3)
    out = apply_pct_or_value_change(df, "Cost", mask, value=-150.0, clamp_non_negative=True)

    # First 3 rows clamped at 0
    assert (out.loc[:2, "Cost"] == 0.0).all()
    # Remaining rows unchanged
    assert (out.loc[3:, "Cost"] == 100.0).all()


def test_append_note_for_first_masked_row_new_column():
    df = _make_df()
    df = ensure_datetime_column(df, "PeriodStart")
    df = sort_by_date(df, "PeriodStart")

    mask = mask_from_start_date(df, "PeriodStart", "2025-01-06")
    out = append_note_for_first_masked_row(df, "PeriodStart", mask, "Step change +50%")

    # Note only on the first affected date (2025-01-06)
    assert "note" in out.columns
    assert out.loc[5, "note"] == "Step change +50%"
    assert (out.loc[:4, "note"] == "").all()
    assert (out.loc[6:, "note"] == "").all()


def test_append_note_for_first_masked_row_appends_existing():
    df = _make_df()
    df["note"] = ""
    df.at[5, "note"] = "Existing note"
    df = ensure_datetime_column(df, "PeriodStart")
    df = sort_by_date(df, "PeriodStart")

    mask = mask_from_start_date(df, "PeriodStart", "2025-01-06")
    out = append_note_for_first_masked_row(df, "PeriodStart", mask, "New context")

    assert out.loc[5, "note"] == "Existing note\nNew context"

