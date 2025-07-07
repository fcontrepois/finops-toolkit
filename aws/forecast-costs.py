# forecast-costs.py
#
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

# 1. Forecast from CSV file (daily granularity, group by SERVICE)
python forecast-costs.py --input costs.csv --date-column PeriodStart --value-column UnblendedCost --method all

# 2. Forecast from stdin (pipe from cost-and-usage.py)
python aws/cost-and-usage.py --granularity daily --output-format csv | python aws/forecast-costs.py --date-column PeriodStart --value-column UnblendedCost --method all

# 3. Forecast from CSV, only using Prophet
python aws/forecast-costs.py --input costs.csv --date-column PeriodStart --value-column UnblendedCost --method prophet

# 4. Forecast from CSV, only using SMA
python aws/forecast-costs.py --input costs.csv --date-column PeriodStart --value-column UnblendedCost --method sma

# 5. Forecast from CSV, only using Exponential Smoothing
python aws/forecast-costs.py --input costs.csv --date-column PeriodStart --value-column UnblendedCost --method es

# 6. Forecast for a specific group (e.g., Service=AmazonEC2)
python aws/forecast-costs.py --input costs.csv --date-column PeriodStart --value-column UnblendedCost --group-column Service --group-value AmazonEC2 --method all

# 7. Forecast for a specific tag (e.g., Tag:Environment=prod)
python aws/forecast-costs.py --input costs.csv --date-column PeriodStart --value-column UnblendedCost --group-column "Tag:Environment" --group-value prod --method all

# 8. Forecast from stdin for a group
python aws/cost-and-usage.py --granularity daily --output-format csv | python aws/forecast-costs.py --date-column PeriodStart --value-column UnblendedCost --group-column Service --group-value AmazonEC2 --method all

# 9. Show help
python aws/forecast-costs.py --help

# 10. Error: input file does not exist
python aws/forecast-costs.py --input notfound.csv --date-column PeriodStart --value-column UnblendedCost --method all

# 11. Error: no input file and no stdin
python aws/forecast-costs.py --date-column PeriodStart --value-column UnblendedCost --method all
"""

import argparse
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings("ignore")

def parse_args():
    parser = argparse.ArgumentParser(
        description="Forecast AWS costs using SMA, Exponential Smoothing, and Facebook Prophet."
    )
    parser.add_argument('--input', required=False, help='Input CSV file (output from cost-and-usage.py). If omitted, reads from stdin.')
    parser.add_argument('--date-column', required=True, help='Name of the date column (e.g., PeriodStart)')
    parser.add_argument('--value-column', required=True, help='Name of the value column (e.g., UnblendedCost)')
    parser.add_argument('--group-column', required=False, help='Name of the group column (e.g., Service, Tag:Environment)')
    parser.add_argument('--group-value', required=False, help='Value of the group to filter (e.g., AmazonEC2, prod)')
    parser.add_argument('--method', choices=['all', 'sma', 'es', 'prophet'], default='all', help='Forecasting method(s) to use')
    return parser.parse_args()

def load_data(args):
    if args.input:
        if not os.path.isfile(args.input):
            print(f"Error: Input file '{args.input}' does not exist or is not a file.", file=sys.stderr)
            sys.exit(2)
        try:
            df = pd.read_csv(args.input)
        except Exception as e:
            print(f"Error: Could not read input file '{args.input}': {e}", file=sys.stderr)
            sys.exit(2)
    else:
        if sys.stdin.isatty():
            print("Error: No input file provided and no data piped to stdin.",
