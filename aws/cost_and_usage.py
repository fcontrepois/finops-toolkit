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
Command Name: cost_and_usage

Purpose:
    Fetches AWS cost and usage data from Cost Explorer API and outputs it in structured CSV format.
    Supports multiple granularities, grouping options, and date ranges.

Input Format:
    N/A (Data Source Command - fetches from AWS API)

Output Format:
    CSV with columns: PeriodStart, [GroupColumn], [MetricColumn]
    - PeriodStart: Start date of the period (YYYY-MM-DD)
    - GroupColumn: Service, Account, or Tag:KeyName based on --group
    - MetricColumn: Cost metric name (e.g., UnblendedCost)

Error Handling:
    - Exit code 1: Invalid arguments, AWS CLI errors
    - Exit code 2: File I/O errors
    - Exit code 4: AWS CLI not configured or missing

Dependencies:
    - AWS CLI configured with appropriate permissions
    - Python 3.8+

Examples:
    # Basic usage
    python aws/cost_and_usage.py --granularity daily
    
    # With pipe
    python aws/cost_and_usage.py --granularity daily | python aws/forecast_costs.py
    
    # Group by service
    python aws/cost_and_usage.py --granularity daily --group SERVICE
    
    # Custom date range
    python aws/cost_and_usage.py --granularity daily --start 2025-01-01 --end 2025-01-31

Author: Frank Contrepois
License: MIT
"""

# Standard library imports first
import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, date
from typing import Optional, Tuple, Dict, Any, List, TextIO

# Third-party imports second
import pandas as pd

# Command-specific constants
VALID_METRICS = [
    "BlendedCost",
    "UnblendedCost",
    "AmortizedCost",
    "NetAmortizedCost",
    "NetUnblendedCost",
    "UsageQuantity",
    "NormalizedUsageAmount"
]

METRIC_UNITS = {
    "BlendedCost": "USD",
    "UnblendedCost": "USD",
    "AmortizedCost": "USD",
    "NetAmortizedCost": "USD",
    "NetUnblendedCost": "USD",
    "UsageQuantity": "Hours",
    "NormalizedUsageAmount": "NormalizedUnits"
}


def handle_error(message: str, exit_code: int = 1) -> None:
    """
    Print error message and exit with specified code.
    
    Args:
        message: Error message to display
        exit_code: Exit code to use
    """
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(exit_code)

def check_aws_cli_available() -> None:
    """Checks if AWS CLI is available in PATH and configured."""
    if shutil.which("aws") is None:
        handle_error("AWS CLI is not installed or not found in PATH.", 4)
    
    # Check if AWS CLI is configured (basic check)
    try:
        result = subprocess.run(["aws", "sts", "get-caller-identity"], capture_output=True, check=True, text=True)
    except subprocess.CalledProcessError as e:
        if "Unable to locate credentials" in e.stderr:
            handle_error("AWS CLI is not configured with credentials.", 4)
        else:
            handle_error(f"AWS CLI configuration issue: {e.stderr}", 4)

def run_aws_cli(cmd: List[str]) -> Dict[str, Any]:
    """Runs the AWS CLI command and returns the parsed JSON output. Exits on error with specific messages."""
    try:
        result = subprocess.run(cmd, capture_output=True, check=True, text=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        stderr = e.stderr or ""
        if "Unable to locate credentials" in stderr:
            handle_error("AWS CLI credentials not found. Please configure your AWS credentials.", 4)
        elif "is not authorized to perform" in stderr:
            handle_error(f"Permission denied. {stderr}", 1)
        elif "could not be found" in stderr or "command not found" in stderr:
            handle_error("AWS CLI command not found. Is AWS CLI installed?", 4)
        else:
            handle_error(f"Running AWS CLI: {stderr}", 1)

def format_aws_datetime(dt: datetime) -> str:
    """Formats a datetime object to AWS Cost Explorer's required string format."""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

def get_date_range(
    granularity: str,
    interval: Optional[str],
    include_today: bool
) -> Tuple[str, str]:
    """Determines the start and end date strings for the AWS Cost Explorer query."""
    now = datetime.utcnow().date()
    if include_today:
        end = now + timedelta(days=1)
    else:
        end = now

    if interval is None:
        if granularity == "HOURLY":
            start = now - timedelta(days=1)
            end = now if not include_today else now + timedelta(days=1)
            start_dt = datetime.combine(start, datetime.min.time())
            end_dt = datetime.combine(end, datetime.min.time())
            return format_aws_datetime(start_dt), format_aws_datetime(end_dt)
        elif granularity == "DAILY":
            start = now - timedelta(days=7)
            end = now if not include_today else now + timedelta(days=1)
            return str(start), str(end)
        elif granularity == "MONTHLY":
            first_of_this_month = now.replace(day=1)
            start = (first_of_this_month - timedelta(days=365)).replace(day=1)
            end = first_of_this_month if not include_today else now + timedelta(days=1)
            return str(start), str(end)
        else:
            raise ValueError("Invalid granularity")
    else:
        if interval == "day":
            start = now
            end = now + timedelta(days=1) if include_today else now
            if granularity == "HOURLY":
                start_dt = datetime.combine(start, datetime.min.time())
                end_dt = datetime.combine(end, datetime.min.time())
                return format_aws_datetime(start_dt), format_aws_datetime(end_dt)
            else:
                return str(start), str(end)
        elif interval == "week":
            start = now - timedelta(days=6)
        elif interval == "month":
            start = now.replace(day=1)
        elif interval == "quarter":
            month = ((now.month - 1) // 3) * 3 + 1
            start = date(now.year, month, 1)
        elif interval == "semester":
            month = 1 if now.month <= 6 else 7
            start = date(now.year, month, 1)
        elif interval == "year":
            start = date(now.year, 1, 1)
        else:
            raise ValueError("Invalid interval")
        if interval != "day":
            end = now + timedelta(days=1) if include_today else now
            if granularity == "HOURLY":
                start_dt = datetime.combine(start, datetime.min.time())
                end_dt = datetime.combine(end, datetime.min.time())
                return format_aws_datetime(start_dt), format_aws_datetime(end_dt)
            else:
                return str(start), str(end)

def fetch_costs(
    start: str,
    end: str,
    group_by: Optional[Dict[str, str]],
    granularity: str,
    metric: str,
    verbose: bool = False
) -> Dict[str, Any]:
    """Fetches cost data from AWS Cost Explorer using the AWS CLI. Handles pagination and returns all results."""
    all_results = []
    next_token = None
    page = 1
    while True:
        if verbose:
            print(f"Fetching page {page}...", file=sys.stderr)
        cmd = [
            "aws", "ce", "get-cost-and-usage",
            "--time-period", f"Start={start},End={end}",
            "--granularity", granularity,
            "--metrics", metric
        ]
        if group_by:
            cmd += ["--group-by", f"Type={group_by['Type']},Key={group_by['Key']}"]
        if next_token:
            cmd += ["--starting-token", next_token]
        result = run_aws_cli(cmd)
        all_results.extend(result.get('ResultsByTime', []))
        next_token = result.get('NextPageToken')
        if not next_token:
            break
        page += 1
    return {'ResultsByTime': all_results}

def write_csv_output(df: pd.DataFrame, include_header: bool = True) -> None:
    """
    Write DataFrame as CSV to stdout.
    
    Args:
        df: DataFrame to write
        include_header: Whether to include column headers
    """
    df.to_csv(sys.stdout, index=False, header=include_header)

def print_csv_summary(
    results: Dict[str, Any],
    group_key: str,
    metric: str,
    fileobj: TextIO = sys.stdout
) -> None:
    """
    Prints a CSV summary grouped by the specified key.
    The column name for the metric is set to the metric name.
    """
    unit = METRIC_UNITS.get(metric, "")
    header = ["PeriodStart", group_key, f"{metric}"]
    writer = csv.writer(fileobj)
    writer.writerow(header)
    for time_period in results.get('ResultsByTime', []):
        period_start = time_period['TimePeriod']['Start']
        for group in time_period.get('Groups', []):
            key = group['Keys'][0]
            amount = group['Metrics'].get(metric, {}).get('Amount', '')
            try:
                amount = f"{float(amount):.6f}"
            except Exception:
                pass
            writer.writerow([period_start, key, amount])

def print_csv_summary_all(
    results: Dict[str, Any],
    metric: str,
    fileobj: TextIO = sys.stdout
) -> None:
    """
    Prints a CSV summary of total values for each period.
    The column name for the metric is set to the metric name.
    The group column is always 'Total'.
    """
    unit = METRIC_UNITS.get(metric, "")
    header = ["PeriodStart", "Group", f"{metric}"]
    writer = csv.writer(fileobj)
    writer.writerow(header)
    for time_period in results.get('ResultsByTime', []):
        period_start = time_period['TimePeriod']['Start']
        amount = time_period.get('Total', {}).get(metric, {}).get('Amount', '')
        try:
            amount = f"{float(amount):.6f}"
        except Exception:
            pass
        writer.writerow([period_start, "Total", amount])

def print_json_summary(
    results: Dict[str, Any],
    fileobj: TextIO = sys.stdout
) -> None:
    """Prints the results as pretty-printed JSON."""
    json.dump(results, fileobj, indent=2)
    fileobj.write("\n")

def parse_metric(metric_str: Optional[str]) -> str:
    """Parses and validates the metric argument. Only one metric is allowed."""
    if not metric_str:
        return "UnblendedCost"
    metrics = [m.strip() for m in metric_str.split(",") if m.strip()]
    if len(metrics) != 1:
        handle_error("Only one metric can be specified at a time.", 1)
    m = metrics[0]
    if m not in VALID_METRICS:
        handle_error(f"Invalid metric '{m}'. Valid options: {', '.join(VALID_METRICS)}", 1)
    return m

def parse_date(date_str: str) -> date:
    """Parses a date string in YYYY-MM-DD format."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except Exception:
        handle_error(f"Invalid date format '{date_str}'. Use YYYY-MM-DD.", 1)

def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser for this command."""
    parser = argparse.ArgumentParser(
        description="Fetch AWS cost and usage data from Cost Explorer API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Basic usage
    python aws/cost_and_usage.py --granularity daily
    
    # With pipe
    python aws/cost_and_usage.py --granularity daily | python aws/forecast_costs.py
    
    # Group by service
    python aws/cost_and_usage.py --granularity daily --group SERVICE
    
    # Custom date range
    python aws/cost_and_usage.py --granularity daily --start 2025-01-01 --end 2025-01-31
        """
    )
    
    # Required arguments first
    parser.add_argument(
        "--granularity", 
        choices=["hourly", "daily", "monthly"], 
        required=True,
        help="Granularity of the data: hourly, daily, or monthly (required)"
    )
    
    # Optional arguments with defaults
    parser.add_argument(
        "--interval", 
        choices=["day", "week", "month", "quarter", "semester", "year"], 
        default=None,
        help="Interval to report: day, week, month, quarter, semester, year (optional)"
    )
    
    parser.add_argument(
        "--group", 
        choices=["SERVICE", "LINKED_ACCOUNT", "TAG", "ALL"], 
        default="SERVICE",
        help="Group costs by SERVICE, LINKED_ACCOUNT, TAG, or ALL (default: SERVICE)"
    )
    
    parser.add_argument(
        "--output-format", 
        choices=["csv", "json"], 
        default="csv",
        help="Output format: csv or json (default: csv, always prints to standard out)"
    )
    
    parser.add_argument(
        "--metrics", 
        type=str, 
        default="UnblendedCost",
        help=f"Metric to retrieve (default: UnblendedCost). Valid options: {', '.join(VALID_METRICS)}"
    )
    
    parser.add_argument(
        "--start", 
        type=str, 
        default=None,
        help="Start date (YYYY-MM-DD). If set with --end, overrides interval logic."
    )
    
    parser.add_argument(
        "--end", 
        type=str, 
        default=None,
        help="End date (YYYY-MM-DD). If set with --start, overrides interval logic."
    )
    
    parser.add_argument(
        "--tag-key", 
        type=str, 
        default=None,
        help="Tag key to group by (required if --group TAG)"
    )
    
    # Boolean flags
    parser.add_argument(
        "--include-today", 
        action="store_true",
        help="If set, include today in the interval"
    )
    
    parser.add_argument(
        "--verbose", 
        action="store_true",
        help="Print debug info (pagination, etc.)"
    )
    
    return parser

def main() -> None:
    """Main entry point for the CLI tool."""
    check_aws_cli_available()  # Pre-check for AWS CLI
    parser = create_argument_parser()
    args = parser.parse_args()

    # Error if --tag-key is used without --group TAG
    if args.tag_key and args.group != "TAG":
        handle_error("--tag-key can only be used with --group TAG.", 1)

    granularity_map = {
        "hourly": "HOURLY",
        "daily": "DAILY",
        "monthly": "MONTHLY"
    }
    granularity = granularity_map[args.granularity]

    # Support for custom date range
    if args.start and args.end:
        start = args.start
        end = args.end
    else:
        try:
            start, end = get_date_range(granularity, args.interval, args.include_today)
        except Exception as e:
            handle_error(str(e), 1)

    metric = parse_metric(args.metrics)

    if args.group == "TAG":
        if not args.tag_key:
            handle_error("--tag-key is required when grouping by TAG.", 1)
        group_by = {"Type": "TAG", "Key": args.tag_key}
        group_key = f"Tag:{args.tag_key}"
        results = fetch_costs(start, end, group_by, granularity, metric, args.verbose)
        if args.output_format == "csv":
            print_csv_summary(results, group_key, metric)
        elif args.output_format == "json":
            print_json_summary(results)
        else:
            handle_error("Invalid output format.", 1)
    elif args.group == "SERVICE":
        group_by = {"Type": "DIMENSION", "Key": "SERVICE"}
        group_key = "Service"
        results = fetch_costs(start, end, group_by, granularity, metric, args.verbose)
        if args.output_format == "csv":
            print_csv_summary(results, group_key, metric)
        elif args.output_format == "json":
            print_json_summary(results)
        else:
            handle_error("Invalid output format.", 1)
    elif args.group == "LINKED_ACCOUNT":
        group_by = {"Type": "DIMENSION", "Key": "LINKED_ACCOUNT"}
        group_key = "Account"
        results = fetch_costs(start, end, group_by, granularity, metric, args.verbose)
        if args.output_format == "csv":
            print_csv_summary(results, group_key, metric)
        elif args.output_format == "json":
            print_json_summary(results)
        else:
            handle_error("Invalid output format.", 1)
    elif args.group == "ALL":
        results = fetch_costs(start, end, None, granularity, metric, args.verbose)
        if args.output_format == "csv":
            print_csv_summary_all(results, metric)
        elif args.output_format == "json":
            print_json_summary(results)
        else:
            handle_error("Invalid output format.", 1)
    else:
        print("Invalid group type.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
