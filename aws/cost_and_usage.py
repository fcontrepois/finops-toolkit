# aws/cost_and_usage.py

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
# Usage Examples and Tests

# 1. Minimal required: daily granularity, default group (SERVICE)
python aws/cost_and_usage.py --granularity daily

# 2. All granularities
python aws/cost_and_usage.py --granularity hourly
python aws/cost_and_usage.py --granularity daily
python aws/cost_and_usage.py --granularity monthly

# 3. All intervals
python aws/cost_and_usage.py --granularity daily --interval day
python aws/cost_and_usage.py --granularity daily --interval week
python aws/cost_and_usage.py --granularity daily --interval month
python aws/cost_and_usage.py --granularity daily --interval quarter
python aws/cost_and_usage.py --granularity daily --interval semester
python aws/cost_and_usage.py --granularity daily --interval year

# 4. Include today
python aws/cost_and_usage.py --granularity daily --interval week --include-today

# 5. All groupings
python aws/cost_and_usage.py --granularity daily --group SERVICE
python aws/cost_and_usage.py --granularity daily --group LINKED_ACCOUNT
python aws/cost_and_usage.py --granularity daily --group TAG --tag-key Environment
python aws/cost_and_usage.py --granularity daily --group ALL

# 6. All output formats
python aws/cost_and_usage.py --granularity daily --output-format csv
python aws/cost_and_usage.py --granularity daily --output-format json

# 7. Group by tag with tag-key
python aws/cost_and_usage.py --granularity daily --group TAG --tag-key Owner

# 8. Full power: combine all flags
python aws/cost_and_usage.py --granularity hourly --interval day --include-today --group TAG --tag-key Project --output-format json

# 9. Redirect output to file
python aws/cost_and_usage.py --granularity monthly --group SERVICE --output-format csv > my-costs.csv

# 10. Help
python aws/cost_and_usage.py --help

# 11. Error: missing tag-key
python aws/cost_and_usage.py --granularity daily --group TAG

# 12. Error: --tag-key used without --group TAG
python aws/cost_and_usage.py --granularity daily --tag-key Owner

# 13. Error: invalid group
python aws/cost_and_usage.py --granularity daily --group INVALID

# 14. Error: invalid interval
python aws/cost_and_usage.py --granularity daily --interval nonsense

# 15. Error: invalid output format
python aws/cost_and_usage.py --granularity daily --output-format nonsense

# 16. Custom metric (only one allowed)
python aws/cost_and_usage.py --granularity daily --metrics UnblendedCost
python aws/cost_and_usage.py --granularity daily --metrics BlendedCost
python aws/cost_and_usage.py --granularity daily --metrics AmortizedCost
python aws/cost_and_usage.py --granularity daily --metrics NetUnblendedCost

# 17. Error: multiple metrics not allowed
python aws/cost_and_usage.py --granularity daily --metrics UnblendedCost,BlendedCost

# 18. Custom date range
python aws/cost_and_usage.py --granularity daily --start 2025-01-01 --end 2025-01-31

# 19. Verbose pagination
python aws/cost_and_usage.py --granularity daily --group SERVICE --verbose
"""

import argparse
import subprocess
import json
import sys
import csv
from datetime import datetime, timedelta, date
from typing import Optional, Tuple, Dict, Any

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

def run_aws_cli(cmd: list) -> dict:
    """Runs the AWS CLI command and returns the parsed JSON output. Exits on error."""
    try:
        result = subprocess.run(cmd, capture_output=True, check=True, text=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print("Error running AWS CLI:", e.stderr, file=sys.stderr)
        sys.exit(1)

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

def print_csv_summary(
    results: Dict[str, Any],
    group_key: str,
    metric: str,
    fileobj=sys.stdout
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
    fileobj=sys.stdout
) -> None:
    """
    Prints a CSV summary of total values for each period.
    The column name for the metric is set to the metric name.
    """
    unit = METRIC_UNITS.get(metric, "")
    header = ["PeriodStart", f"{metric}"]
    writer = csv.writer(fileobj)
    writer.writerow(header)
    for time_period in results.get('ResultsByTime', []):
        period_start = time_period['TimePeriod']['Start']
        amount = time_period.get('Total', {}).get(metric, {}).get('Amount', '')
        try:
            amount = f"{float(amount):.6f}"
        except Exception:
            pass
        writer.writerow([period_start, amount])

def print_json_summary(
    results: Dict[str, Any],
    fileobj=sys.stdout
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
        print("Error: Only one metric can be specified at a time.", file=sys.stderr)
        sys.exit(1)
    m = metrics[0]
    if m not in VALID_METRICS:
        print(f"Error: Invalid metric '{m}'. Valid options: {', '.join(VALID_METRICS)}", file=sys.stderr)
        sys.exit(1)
    return m

def parse_date(date_str: str) -> date:
    """Parses a date string in YYYY-MM-DD format."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except Exception:
        print(f"Error: Invalid date format '{date_str}'. Use YYYY-MM-DD.", file=sys.stderr)
        sys.exit(1)

def main() -> None:
    """Main entry point for the CLI tool."""
    parser = argparse.ArgumentParser(
        description="Explore AWS cloud costs by service, account, or tag with flexible granularity and interval."
    )
    parser.add_argument(
        "--granularity", choices=["hourly", "daily", "monthly"], required=True,
        help="Granularity of the data: hourly, daily, or monthly (required)"
    )
    parser.add_argument(
        "--interval", choices=["day", "week", "month", "quarter", "semester", "year"], default=None,
        help="Interval to report: day, week, month, quarter, semester, year (optional)"
    )
    parser.add_argument(
        "--include-today", action="store_true",
        help="If set, include today in the interval"
    )
    parser.add_argument(
        "--group", choices=["SERVICE", "LINKED_ACCOUNT", "TAG", "ALL"], default="SERVICE",
        help="Group costs by SERVICE, LINKED_ACCOUNT, TAG, or ALL (default: SERVICE)"
    )
    parser.add_argument(
        "--tag-key", type=str, default=None,
        help="Tag key to group by (required if --group TAG)"
    )
    parser.add_argument(
        "--output-format", choices=["csv", "json"], default="csv",
        help="Output format: csv or json (default: csv, always prints to standard out)"
    )
    parser.add_argument(
        "--metrics", type=str, default="UnblendedCost",
        help=f"Metric to retrieve (default: UnblendedCost). Valid options: {', '.join(VALID_METRICS)}"
    )
    parser.add_argument(
        "--start", type=str, default=None,
        help="Start date (YYYY-MM-DD). If set with --end, overrides interval logic."
    )
    parser.add_argument(
        "--end", type=str, default=None,
        help="End date (YYYY-MM-DD). If set with --start, overrides interval logic."
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Print debug info (pagination, etc.)"
    )
    args = parser.parse_args()

    # Error if --tag-key is used without --group TAG
    if args.tag_key and args.group != "TAG":
        print("Error: --tag-key can only be used with --group TAG.", file=sys.stderr)
        sys.exit(1)

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
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    metric = parse_metric(args.metrics)

    if args.group == "TAG":
        if not args.tag_key:
            print("Error: --tag-key is required when grouping by TAG.", file=sys.stderr)
            sys.exit(1)
        group_by = {"Type": "TAG", "Key": args.tag_key}
        group_key = f"Tag:{args.tag_key}"
        results = fetch_costs(start, end, group_by, granularity, metric, args.verbose)
        if args.output_format == "csv":
            print_csv_summary(results, group_key, metric)
        elif args.output_format == "json":
            print_json_summary(results)
        else:
            print("Invalid output format.", file=sys.stderr)
            sys.exit(1)
    elif args.group == "SERVICE":
        group_by = {"Type": "DIMENSION", "Key": "SERVICE"}
        group_key = "Service"
        results = fetch_costs(start, end, group_by, granularity, metric, args.verbose)
        if args.output_format == "csv":
            print_csv_summary(results, group_key, metric)
        elif args.output_format == "json":
            print_json_summary(results)
        else:
            print("Invalid output format.", file=sys.stderr)
            sys.exit(1)
    elif args.group == "LINKED_ACCOUNT":
        group_by = {"Type": "DIMENSION", "Key": "LINKED_ACCOUNT"}
        group_key = "Account"
        results = fetch_costs(start, end, group_by, granularity, metric, args.verbose)
        if args.output_format == "csv":
            print_csv_summary(results, group_key, metric)
        elif args.output_format == "json":
            print_json_summary(results)
        else:
            print("Invalid output format.", file=sys.stderr)
            sys.exit(1)
    elif args.group == "ALL":
        results = fetch_costs(start, end, None, granularity, metric, args.verbose)
        if args.output_format == "csv":
            print_csv_summary_all(results, metric)
        elif args.output_format == "json":
            print_json_summary(results)
        else:
            print("Invalid output format.", file=sys.stderr)
            sys.exit(1)
    else:
        print("Invalid group type.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
