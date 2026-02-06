#!/usr/bin/env python3
# Tests for the helper commands under tools/.

import os
import sys
import subprocess

import pandas as pd
import pytest


ROOT_DIR = os.path.dirname(os.path.dirname(__file__))


def run_tool(args):
    """Run a tool script from the project root and return CompletedProcess."""
    return subprocess.run(
        [sys.executable] + args,
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
    )


def test_generate_series_daily_flat(tmp_path):
    """generate_series: basic daily flat series with deterministic output."""
    out_csv = tmp_path / "series.csv"

    result = run_tool(
        [
            "tools/generate_series.py",
            "--pattern",
            "flat",
            "--granularity",
            "daily",
            "--periods",
            "10",
            "--baseline",
            "100",
            "--noise",
            "0.0",
            "--out",
            str(out_csv),
        ]
    )

    assert result.returncode == 0, result.stderr
    df = pd.read_csv(out_csv)

    assert len(df) == 10
    assert list(df.columns) == ["PeriodStart", "Cost"]
    dates = pd.to_datetime(df["PeriodStart"])
    assert dates.is_monotonic_increasing
    assert (df["Cost"] == 100.0).all()


def _write_simple_cost_series(tmp_path, filename="input.csv", days=5, value=100.0):
    dates = pd.date_range("2025-01-01", periods=days, freq="D")
    df = pd.DataFrame({"PeriodStart": dates, "Cost": value})
    path = tmp_path / filename
    df.to_csv(path, index=False)
    return path


def test_add_spike_pct_with_note(tmp_path):
    """add_spike: applies a positive spike over a fixed window and notes first day."""
    input_csv = _write_simple_cost_series(tmp_path)
    out_csv = tmp_path / "out_spike.csv"

    result = run_tool(
        [
            "tools/add_spike.py",
            "--input",
            str(input_csv),
            "--output",
            str(out_csv),
            "--start-date",
            "2025-01-03",
            "--length",
            "2",
            "--pct",
            "0.5",
            "--note",
            "Promo spike +50%",
        ]
    )

    assert result.returncode == 0, result.stderr
    df = pd.read_csv(out_csv)

    # First two days unchanged, next two days +50%, last day unchanged.
    assert (df.loc[0:1, "Cost"] == 100.0).all()
    assert (df.loc[2:3, "Cost"] == 150.0).all()
    assert df.loc[4, "Cost"] == 100.0

    # Note only on the first spiked date (2025-01-03).
    assert "note" in df.columns
    assert df.loc[2, "note"] == "Promo spike +50%"
    assert (df.loc[[0, 1, 3, 4], "note"].fillna("") == "").all()


def test_add_deep_value_clamped(tmp_path):
    """add_deep: applies a negative deep and clamps to zero."""
    input_csv = _write_simple_cost_series(tmp_path)
    out_csv = tmp_path / "out_deep.csv"

    # Deep larger than baseline so values would go negative without clamping.
    result = run_tool(
        [
            "tools/add_deep.py",
            "--input",
            str(input_csv),
            "--output",
            str(out_csv),
            "--start-date",
            "2025-01-01",
            "--length",
            "3",
            "--value",
            "150.0",
            "--note",
            "Planned outage - deep",
        ]
    )

    assert result.returncode == 0, result.stderr
    df = pd.read_csv(out_csv)

    # First three rows clamped at 0, remaining rows unchanged.
    assert (df.loc[0:2, "Cost"] == 0.0).all()
    assert (df.loc[3:, "Cost"] == 100.0).all()

    # Note only on the first deep date.
    assert df.loc[0, "note"] == "Planned outage - deep"
    assert (df.loc[1:, "note"].fillna("") == "").all()


def test_add_step_change_pct(tmp_path):
    """add_step_change: permanent step change from given start date."""
    input_csv = _write_simple_cost_series(tmp_path)
    out_csv = tmp_path / "out_step.csv"

    result = run_tool(
        [
            "tools/add_step_change.py",
            "--input",
            str(input_csv),
            "--output",
            str(out_csv),
            "--start-date",
            "2025-01-04",
            "--pct",
            "0.2",
            "--note",
            "Step change +20%",
        ]
    )

    assert result.returncode == 0, result.stderr
    df = pd.read_csv(out_csv)

    # First three days unchanged, last two days +20%.
    assert (df.loc[0:2, "Cost"] == 100.0).all()
    assert (df.loc[3:, "Cost"] == 120.0).all()

    # Note only on the first affected date.
    assert df.loc[3, "note"] == "Step change +20%"
    assert (df.loc[[0, 1, 2, 4], "note"].fillna("") == "").all()


def test_add_spikes_max_pct_bounds(tmp_path):
    """add_spikes: all days spiked within [baseline, baseline * (1 + max_pct)]."""
    input_csv = _write_simple_cost_series(tmp_path, days=20)
    out_csv = tmp_path / "out_spikes.csv"

    result = run_tool(
        [
            "tools/add_spikes.py",
            "--input",
            str(input_csv),
            "--output",
            str(out_csv),
            "--max-pct",
            "0.10",
            "--prob",
            "1.0",
            "--value-column",
            "Cost",
            "--seed",
            "1",
        ]
    )

    assert result.returncode == 0, result.stderr
    df = pd.read_csv(out_csv)

    # All values are between baseline and baseline * (1 + max_pct).
    assert (df["Cost"] >= 100.0).all()
    assert (df["Cost"] <= 110.0).all()
    # And at least one value actually changed.
    assert df["Cost"].max() > 100.0


def test_add_seasonality_preset_toys(tmp_path):
    """add_seasonality: applies expected monthly factors for preset 'toys'."""
    dates = pd.date_range("2025-01-01", periods=12, freq="MS")
    df_in = pd.DataFrame({"PeriodStart": dates, "Cost": 100.0})
    input_csv = tmp_path / "monthly.csv"
    out_csv = tmp_path / "monthly_toys.csv"
    df_in.to_csv(input_csv, index=False)

    result = run_tool(
        [
            "tools/add_seasonality.py",
            "--input",
            str(input_csv),
            "--output",
            str(out_csv),
            "--preset",
            "toys",
            "--date-column",
            "PeriodStart",
            "--value-column",
            "Cost",
        ]
    )

    assert result.returncode == 0, result.stderr
    df = pd.read_csv(out_csv)
    dates_out = pd.to_datetime(df["PeriodStart"])

    # Factors from get_preset_factors("toys")
    jan = df.loc[dates_out.dt.month == 1, "Cost"].iloc[0]
    nov = df.loc[dates_out.dt.month == 11, "Cost"].iloc[0]
    dec = df.loc[dates_out.dt.month == 12, "Cost"].iloc[0]

    assert jan == pytest.approx(95.0)
    assert nov == pytest.approx(130.0)
    assert dec == pytest.approx(140.0)


def test_filter_forecast_horizon_keeps_expected_rows(tmp_path):
    """filter_forecast_horizon: keeps only N days from first forecast date."""
    dates = pd.date_range("2025-01-01", periods=10, freq="D")
    # First 5 rows are actuals (NaN forecasts), last 5 are forecasts.
    df_in = pd.DataFrame(
        {
            "PeriodStart": dates,
            "Cost": 100.0,
            "sma": [float("nan")] * 5 + [200.0] * 5,
            "es": [float("nan")] * 5 + [210.0] * 5,
        }
    )
    input_csv = tmp_path / "forecasts.csv"
    out_csv = tmp_path / "forecasts_filtered.csv"
    df_in.to_csv(input_csv, index=False)

    result = run_tool(
        [
            "tools/filter_forecast_horizon.py",
            "--input",
            str(input_csv),
            "--output",
            str(out_csv),
            "--days",
            "3",
            "--date-column",
            "PeriodStart",
        ]
    )

    assert result.returncode == 0, result.stderr
    df = pd.read_csv(out_csv)
    dates_out = pd.to_datetime(df["PeriodStart"])

    # First forecast date is 2025-01-06 (index 5); we keep 3 days: 6, 7, 8.
    assert len(df) == 3
    assert dates_out.min() == pd.Timestamp("2025-01-06")
    assert dates_out.max() == pd.Timestamp("2025-01-08")

