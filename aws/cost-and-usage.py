# aws/cost-and-usage.py

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
python aws/cost-and-usage.py --granularity daily

# 2. All granularities
python aws/cost-and-usage.py --granularity hourly
python aws/cost-and-usage.py --granularity daily
python aws/cost-and-usage.py --granularity monthly

# 3. All intervals
python aws/cost-and-usage.py --granularity daily --interval day
python aws/cost-and-usage.py --granularity daily --interval week
python aws/cost-and-usage.py --granularity daily --interval month
python aws/cost-and-usage.py --granularity daily --interval quarter
python aws/cost-and-usage.py --granularity daily --interval semester
python aws/cost-and-usage.py --granularity daily --interval year

# 4. Include today
python aws/cost-and-usage.py --granularity daily --interval week --include-today

# 5. All groupings
python aws/cost-and-usage.py --granularity daily --group SERVICE
python aws/cost-and-usage.py --granularity daily --group LINKED_ACCOUNT
python aws/cost-and-usage.py --granularity daily --group TAG --tag-key Environment

# 6. All output formats
python aws/cost-and-usage.py --granularity daily --output-format csv
python aws/cost-and-usage.py --granularity daily --output-format json

# 7. Group by tag with tag-key
python aws/cost-and-usage.py --granularity daily --group TAG --tag-key Owner

# 8. Full power: combine all flags
python aws/cost-and-usage.py --granularity hourly --interval day --include-today --group TAG --tag-key Project --output-format json

# 9. Redirect output to file
python aws/cost-and-usage.py --granularity monthly --group SERVICE --output-format csv > my-costs.csv

# 10. Help
python aws/cost-and-usage.py --help

# 11. Error: missing tag-key
python aws/cost-and-usage.py --granularity daily --group TAG

# 12. Error: invalid group
python aws/cost-and-usage.py --granularity daily --group INVALID

# 13. Error: invalid interval
python aws/cost-and-usage.py --granularity daily --interval nonsense

# 14. Error: invalid output format
python aws/cost-and-usage.py --granularity daily --output-format nonsense

# 15. Custom metric (only one allowed)
python aws/cost-and-usage.py --granularity daily --metrics UnblendedCost
python aws/cost-and-usage.py --granularity daily --metrics BlendedCost
python aws/cost-and-usage.py --granularity daily --metrics AmortizedCost
python aws/cost-and-usage.py --granularity daily --metrics NetUnblendedCost
python aws/cost-and-usage.py --granularity daily --metrics NetAmortizedCost
python aws/cost-and-usage.py --granularity daily --metrics UsageQuantity
python aws/cost-and-usage.py --granularity daily --metrics NormalizedUsageAmount

# 16. Error: multiple metrics not allowed
python aws/cost-and-usage.py --granularity daily --metrics UnblendedCost,BlendedCost

"""

import argparse
import subprocess
import json
import sys
import csv
from datetime import datetime, timedelta, date

# List of valid AWS Cost Explorer metrics as of 2025
VALID_METRICS = [
    "BlendedCost",
    "UnblendedCost",
    "AmortizedCost",
    "NetAmortizedCost",
    "NetUnblendedCost",
    "UsageQuantity",
    "NormalizedUsageAmount"
]

def run_aws_cli(cmd):
    try:
        result = subprocess.run(cmd, capture_output=True, check=True, text=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print("Error running AWS CLI:", e.stderr, file=sys.stderr)
        sys.exit(1)

def format_aws_datetime(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

def get_date_range(granularity, interval, include_today):
    now = datetime.utcnow().date()
    if include_today:
        end = now + timedelta(days=1)
    else:
        end = now

    # Default intervals if not set
    if interval is None:
        if granularity == "HOURLY":
            # Default: yesterday
            start = now - timedelta(days=1)
            end = now if not include_today else now + timedelta(days=1)
            start_dt = datetime.combine(start, datetime.min.time())
            end_dt = datetime.combine(end, datetime.min.time())
            return format_aws_datetime(start_dt), format_aws_datetime(end_dt)
        elif granularity == "DAILY":
            # Default: last week up to yesterday
            start = now - timedelta(days=7)
            end = now if not include_today else now + timedelta(days=1)
            return str(start), str(end)
        elif granularity == "MONTHLY":
            # Default: last year up to last month
            first_of_this_month = now.replace(day=1)
            start = (first_of_this_month - timedelta(days=365)).replace(day=1)
            end = first_of_this_month if not include_today else now + timedelta(days=1)
            return str(start), str(end)
        else:
            raise ValueError("Invalid granularity")
    else:
        # Parse interval
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

def fetch_costs(start, end, group_by, granularity, metric):
    all_results = []
    next_token = None
    while True:
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
        all_results.extend(result['ResultsByTime'])
        next_token = result.get('NextPageToken')
        if not next_token:
            break
    return {'ResultsByTime': all_results}

def print_csv_summary(results, group_key, metric, fileobj=sys.stdout):
    writer = csv.writer(fileobj)
    header = ["PeriodStart", group_key, metric]
    writer.writerow(header)
    for time_period in results['ResultsByTime']:
        period_start = time_period['TimePeriod']['Start']
        for group in time_period['Groups']:
            key = group['Keys'][0]
            amount = group['Metrics'].get(metric, {}).get('Amount', '')
            try:
                amount = f"{float(amount):.6f}"
            except Exception:
                pass
            writer.writerow([period_start, key, amount])

def print_json_summary(results, fileobj=sys.stdout):
    json.dump(results, fileobj, indent=2)
    fileobj.write("\n")

def parse_metric(metric_str):
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

def main():
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
        "--group", choices=["SERVICE", "LINKED_ACCOUNT", "TAG"], default="SERVICE",
        help="Group costs by SERVICE, LINKED_ACCOUNT, or TAG (default: SERVICE)"
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
    args = parser.parse_args()

    granularity_map = {
        "hourly": "HOURLY",
        "daily": "DAILY",
        "monthly": "MONTHLY"
    }
    granularity = granularity_map[args.granularity]

    try:
        start, end = get_date_range(granularity, args.interval, args.include_today)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.group == "TAG":
        if not args.tag_key:
            print("Error: --tag-key is required when grouping by TAG.", file=sys.stderr)
            sys.exit(1)
        group_by = {"Type": "TAG", "Key": args.tag_key}
        group_key = f"Tag:{args.tag_key}"
    elif args.group == "SERVICE":
        group_by = {"Type": "DIMENSION", "Key": "SERVICE"}
        group_key = "Service"
    elif args.group == "LINKED_ACCOUNT":
        group_by = {"Type": "DIMENSION", "Key": "LINKED_ACCOUNT"}
        group_key = "Account"
    else:
        print("Invalid group type.", file=sys.stderr)
        sys.exit(1)

    metric = parse_metric(args.metrics)

    results = fetch_costs(start, end, group_by, granularity, metric)

    if args.output_format == "csv":
        print_csv_summary(results, group_key, metric)
    elif args.output_format == "json":
        print_json_summary(results)
    else:
        print("Invalid output format.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
