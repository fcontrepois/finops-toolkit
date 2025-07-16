# anomaly_detection_forecast.py
#
# MIT License
# Copyright (c) 2025 Frank Contrepois
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# -----------------------------------------------------------------------------
# Documentation:
#   This script detects anomalies in AWS cost forecasts by comparing the most recent forecast
#   to previous periods (day before, week ago, month ago, quarter ago) for each group and method.
#   If the percent change exceeds a user-defined threshold, an alert is printed.
#
#   - Supports all group types: ALL, SERVICE, LINKED_ACCOUNT, TAG (with --tag-key)
#   - Supports all forecast methods: sma, es, prophet, or all
#   - Prints alerts and a summary table (CSV) with columns: Group, Method, Period, Change (%), Anomaly (Y/N)
#
# Requirements:
#   - Python 3
#   - pandas
#   - AWS CLI configured
#   - finops-toolkit's aws/cost_and_usage.py and aws/forecast_costs.py in PATH
#
# Usage examples:
#   python aws/anomaly_detection_forecast.py --threshold 20
#   python aws/anomaly_detection_forecast.py --threshold 10 --granularity daily --metric UnblendedCost
#   python aws/anomaly_detection_forecast.py --threshold 10 --group SERVICE
#   python aws/anomaly_detection_forecast.py --threshold 10 --group TAG --tag-key Owner
#   python aws/anomaly_detection_forecast.py --threshold 10 --granularity daily --metric BlendedCost --group ALL
# -----------------------------------------------------------------------------

import argparse
import subprocess
import sys
import os
import pandas as pd
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import tempfile
import io

PERIODS = [
    ("Day Before Yesterday", -2),
    ("Week Ago", -7),
    ("Month Ago", -30),
    ("Quarter Ago", -90)
]

METHODS = ["sma", "es", "prophet"]

GROUP_COLS = {
    "ALL": None,
    "SERVICE": "Service",
    "LINKED_ACCOUNT": "Account",
    "TAG": None  # Will be set to Tag:<tag_key>
}

def parse_args():
    parser = argparse.ArgumentParser(description="Detect anomalies in AWS cost forecasts.")
    parser.add_argument('--threshold', type=float, required=True, help='Percent change to flag as anomaly (required)')
    parser.add_argument('--granularity', default='daily', choices=['hourly', 'daily', 'monthly'], help='Granularity (default: daily)')
    parser.add_argument('--metric', default='UnblendedCost', help='Metric to use (default: UnblendedCost)')
    parser.add_argument('--group', default='ALL', choices=['ALL', 'SERVICE', 'LINKED_ACCOUNT', 'TAG'], help='Group type (default: ALL)')
    parser.add_argument('--tag-key', default=None, help='Tag key (required if group is TAG)')
    parser.add_argument('--method', default='all', choices=['all', 'sma', 'es', 'prophet'], help='Forecast method (default: all)')
    return parser.parse_args()

def get_dates():
    today = datetime.utcnow().date()
    dates = {
        "TODAY": today,
        "YESTERDAY": today - timedelta(days=1),
        "DAY_BEFORE_YESTERDAY": today - timedelta(days=2),
        "WEEK_AGO": today - timedelta(days=7),
        "MONTH_AGO": today - relativedelta(months=1),
        "QUARTER_AGO": today - relativedelta(months=3)
    }
    return dates

def run_cost_and_usage(granularity, group, metric, tag_key, start, end):
    cmd = [sys.executable, 'aws/cost_and_usage.py', '--granularity', granularity, '--group', group, '--metrics', metric, '--output-format', 'csv', '--start', str(start), '--end', str(end)]
    if group == 'TAG' and tag_key:
        cmd += ['--tag-key', tag_key]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("Error running cost_and_usage.py:", result.stderr, file=sys.stderr)
        sys.exit(1)
    return pd.read_csv(io.StringIO(result.stdout))

def run_forecast_costs(df, metric, method):
    with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.csv') as tmp:
        df.to_csv(tmp.name, index=False)
        cmd = [sys.executable, 'aws/forecast_costs.py', '--input', tmp.name, '--date-column', 'PeriodStart', '--value-column', metric]
        result = subprocess.run(cmd, capture_output=True, text=True)
        os.unlink(tmp.name)
    if result.returncode != 0:
        return None
    return pd.read_csv(io.StringIO(result.stdout))

def percent_diff(a, b):
    try:
        a = float(a)
        b = float(b)
        if b == 0:
            return None
        return ((a - b) / b) * 100
    except Exception:
        return None

def main():
    args = parse_args()
    dates = get_dates()
    start = dates["QUARTER_AGO"] - timedelta(days=10)  # Get enough history
    end = dates["TODAY"]
    group_col = GROUP_COLS[args.group]
    if args.group == 'TAG':
        if not args.tag_key:
            print("--tag-key is required when group is TAG", file=sys.stderr)
            sys.exit(1)
        group_col = f'Tag:{args.tag_key}'

    # Get cost data
    cost_df = run_cost_and_usage(args.granularity, args.group, args.metric, args.tag_key, start, end)
    if args.group == 'ALL':
        groups = ['ALL']
    else:
        groups = cost_df[group_col].dropna().unique()

    methods = METHODS if args.method == 'all' else [args.method]
    summary_rows = []

    print(f"Anomaly Detection Report (Forecast, Threshold: {args.threshold}%)")
    print(f"Comparing yesterday's forecast to previous periods for each group and method.")

    for group in groups:
        if args.group == 'ALL':
            group_df = cost_df.copy()
        else:
            group_df = cost_df[cost_df[group_col] == group]
        # Pivot to PeriodStart,Metric
        group_df = pd.DataFrame(group_df[['PeriodStart', args.metric]])
        group_df = group_df.rename(columns={args.metric: 'Value'})
        if len(group_df) < 10:
            print(f"Skipping group {group}: not enough data ({len(group_df)} rows)")
            continue
        for method in methods:
            # Run forecast
            forecast_df = run_forecast_costs(group_df, 'Value', method)
            if forecast_df is None or forecast_df.empty:
                print(f"  {group} | {method}: Forecast failed or empty.")
                continue
            # Get forecasted values for each date
            for label, offset in PERIODS:
                target_date = dates["YESTERDAY"]
                prev_date = dates["YESTERDAY"] + timedelta(days=offset)
                try:
                    yest_val = forecast_df.loc[forecast_df['PeriodStart'] == pd.Timestamp(target_date), method].values[0]
                    prev_val = forecast_df.loc[forecast_df['PeriodStart'] == pd.Timestamp(prev_date), method].values[0]
                except Exception:
                    yest_val = prev_val = None
                diff = percent_diff(yest_val, prev_val)
                anomaly = 'N'
                if diff is not None and abs(diff) > args.threshold:
                    print(f"  ALERT: Group: {group} | Method: {method} | {label}: Change = {diff:.2f}% (Threshold: {args.threshold}%)")
                    anomaly = 'Y'
                else:
                    print(f"  Group: {group} | Method: {method} | {label}: Change = {diff if diff is not None else 'N/A'}%")
                summary_rows.append({
                    'Group': group,
                    'Method': method,
                    'Period': label,
                    'Change (%)': f"{diff if diff is not None else 'N/A'}",
                    'Anomaly': anomaly
                })
    # Print summary table
    print("\n# Anomaly Detection Summary Table (CSV)")
    import csv
    import sys
    writer = csv.DictWriter(sys.stdout, fieldnames=['Group', 'Method', 'Period', 'Change (%)', 'Anomaly'])
    writer.writeheader()
    for row in summary_rows:
        writer.writerow(row)

if __name__ == "__main__":
    main() 