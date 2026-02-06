#!/usr/bin/env python3
# MIT License
#
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

"""
Command Name: anomaly_detection_forecast

Purpose:
    Detects anomalies in AWS cost forecasts by comparing the most recent forecast
    to previous periods (day before, week ago, month ago, quarter ago) for each group and method.
    If the percent change exceeds a user-defined threshold, an alert is printed.

Input Format:
    N/A (Data Source Command - fetches from AWS API and processes forecasts)

Output Format:
    CSV with columns: Group, Method, Period, Change (%), Anomaly (Y/N)
    - Group: Service, Account, or Tag value being analyzed
    - Method: Forecast method used (sma, es, prophet)
    - Period: Comparison period (Day Before Yesterday, Week Ago, Month Ago, Quarter Ago)
    - Change (%): Percentage change from previous period
    - Anomaly: Y if change exceeds threshold, N otherwise

Error Handling:
    - Exit code 1: Invalid arguments, data processing errors
    - Exit code 2: File I/O errors
    - Exit code 3: Data validation errors (insufficient data, missing columns)
    - Exit code 4: AWS CLI not configured or missing

Dependencies:
    - AWS CLI configured with appropriate permissions
    - pandas
    - dateutil
    - finops-toolkit's aws/cost_and_usage.py and forecast_costs.py
    - Python 3.8+

Examples:
    # Basic usage
    python aws/anomaly_detection_forecast.py --threshold 20
    
    # With specific granularity and metric
    python aws/anomaly_detection_forecast.py --threshold 10 --granularity daily --metric UnblendedCost
    
    # Group by service
    python aws/anomaly_detection_forecast.py --threshold 10 --group SERVICE
    
    # Group by tag
    python aws/anomaly_detection_forecast.py --threshold 10 --group TAG --tag-key Owner

Author: Frank Contrepois
License: MIT
"""

# Standard library imports first
import argparse
import csv
import io
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

# Third-party imports second
import pandas as pd
from dateutil.relativedelta import relativedelta

# Command-specific constants
PERIODS = [
    ("Day Before Yesterday", -2),
    ("Week Ago", -7),
    ("Month Ago", -30),
    ("Quarter Ago", -90)
]

METHODS = ["sma", "es", "hw", "arima", "sarima", "theta", "prophet", "neural_prophet", "darts", "ensemble"]

GROUP_COLS = {
    "ALL": None,
    "SERVICE": "Service",
    "LINKED_ACCOUNT": "Account",
    "TAG": None  # Will be set to Tag:<tag_key>
}

DEFAULT_GRANULARITY = "daily"
DEFAULT_METRIC = "UnblendedCost"
DEFAULT_GROUP = "ALL"
DEFAULT_METHOD = "all"
MIN_DATA_POINTS = 10

def handle_error(message: str, exit_code: int = 1) -> None:
    """
    Print error message and exit with specified code.
    
    Args:
        message: Error message to display
        exit_code: Exit code to use
    """
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(exit_code)

def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser for this command."""
    parser = argparse.ArgumentParser(
        description="Detect anomalies in AWS cost forecasts by comparing forecasts to previous periods",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Basic usage
    python aws/anomaly_detection_forecast.py --threshold 20
    
    # With specific granularity and metric
    python aws/anomaly_detection_forecast.py --threshold 10 --granularity daily --metric UnblendedCost
    
    # Group by service
    python aws/anomaly_detection_forecast.py --threshold 10 --group SERVICE
    
    # Group by tag
    python aws/anomaly_detection_forecast.py --threshold 10 --group TAG --tag-key Owner
        """
    )
    
    # Required arguments first
    parser.add_argument(
        '--threshold', 
        type=float, 
        required=True, 
        help='Percent change to flag as anomaly (required)'
    )
    
    # Optional arguments with defaults
    parser.add_argument(
        '--granularity', 
        default=DEFAULT_GRANULARITY, 
        choices=['hourly', 'daily', 'monthly'], 
        help=f'Granularity (default: {DEFAULT_GRANULARITY})'
    )
    parser.add_argument(
        '--metric', 
        default=DEFAULT_METRIC, 
        help=f'Metric to use (default: {DEFAULT_METRIC})'
    )
    parser.add_argument(
        '--group', 
        default=DEFAULT_GROUP, 
        choices=['ALL', 'SERVICE', 'LINKED_ACCOUNT', 'TAG'], 
        help=f'Group type (default: {DEFAULT_GROUP})'
    )
    parser.add_argument(
        '--tag-key', 
        default=None, 
        help='Tag key (required if group is TAG)'
    )
    parser.add_argument(
        '--method', 
        default=DEFAULT_METHOD, 
        choices=['all', 'sma', 'es', 'prophet'], 
        help=f'Forecast method (default: {DEFAULT_METHOD})'
    )
    
    return parser

def get_dates() -> Dict[str, Any]:
    """
    Get date references for anomaly detection periods.
    
    Returns:
        Dict mapping period names to date objects
    """
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

def run_cost_and_usage(granularity: str, group: str, metric: str, tag_key: Optional[str], start: Any, end: Any) -> pd.DataFrame:
    """
    Run cost_and_usage.py command and return parsed data.
    
    Args:
        granularity: Data granularity (hourly, daily, monthly)
        group: Group type (ALL, SERVICE, LINKED_ACCOUNT, TAG)
        metric: Cost metric to retrieve
        tag_key: Tag key (required for TAG group)
        start: Start date
        end: End date
        
    Returns:
        DataFrame with cost data
        
    Raises:
        SystemExit: If cost_and_usage.py fails
    """
    cmd = [sys.executable, 'aws/cost_and_usage.py', '--granularity', granularity, '--group', group, '--metrics', metric, '--output-format', 'csv', '--start', str(start), '--end', str(end)]
    if group == 'TAG' and tag_key:
        cmd += ['--tag-key', tag_key]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        handle_error(f"Failed to run cost_and_usage.py: {result.stderr}", 4)
    return pd.read_csv(io.StringIO(result.stdout))

def run_forecast_costs(df: pd.DataFrame, metric: str, method: str) -> Optional[pd.DataFrame]:
    """
    Run forecast_costs.py command and return parsed data.
    
    Args:
        df: Input DataFrame with cost data
        metric: Metric column name
        method: Forecast method
        
    Returns:
        DataFrame with forecast data, or None if forecast fails
    """
    with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.csv') as tmp:
        df.to_csv(tmp.name, index=False)
        cmd = [sys.executable, 'forecast_costs.py', '--input', tmp.name, '--date-column', 'PeriodStart', '--value-column', metric]
        result = subprocess.run(cmd, capture_output=True, text=True)
        os.unlink(tmp.name)
    if result.returncode != 0:
        return None
    return pd.read_csv(io.StringIO(result.stdout))

def percent_diff(a: Any, b: Any) -> Optional[float]:
    """
    Calculate percentage difference between two values.
    
    Args:
        a: First value
        b: Second value (baseline)
        
    Returns:
        Percentage difference, or None if calculation fails
    """
    try:
        a = float(a)
        b = float(b)
        if b == 0:
            return None
        return ((a - b) / b) * 100
    except Exception:
        return None

def main() -> None:
    """Main entry point for the CLI tool."""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Validate arguments
    if args.group == 'TAG' and not args.tag_key:
        handle_error("--tag-key is required when group is TAG", 1)
    
    dates = get_dates()
    start = dates["QUARTER_AGO"] - timedelta(days=10)  # Get enough history
    end = dates["TODAY"]
    group_col = GROUP_COLS[args.group]
    if args.group == 'TAG':
        group_col = f'Tag:{args.tag_key}'

    # Get cost data
    cost_df = run_cost_and_usage(args.granularity, args.group, args.metric, args.tag_key, start, end)
    if cost_df.empty:
        handle_error("No cost data retrieved from AWS", 3)
    
    if args.group == 'ALL':
        groups = ['ALL']
    else:
        groups = cost_df[group_col].dropna().unique()

    # Determine methods dynamically based on forecast output when using 'all'
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
        if len(group_df) < MIN_DATA_POINTS:
            print(f"Skipping group {group}: not enough data ({len(group_df)} rows)")
            continue
        for method in methods:
            # Run forecast
            forecast_df = run_forecast_costs(group_df, 'Value', method)
            if forecast_df is None or forecast_df.empty:
                print(f"  {group} | {method}: Forecast failed or empty.")
                continue
            # If using 'all', constrain methods to columns actually present in forecast_df
            if args.method == 'all':
                available_cols = set(forecast_df.columns)
                methods = [m for m in METHODS if m in available_cols]
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
    writer = csv.DictWriter(sys.stdout, fieldnames=['Group', 'Method', 'Period', 'Change (%)', 'Anomaly'])
    writer.writeheader()
    for row in summary_rows:
        writer.writerow(row)

if __name__ == "__main__":
    main() 