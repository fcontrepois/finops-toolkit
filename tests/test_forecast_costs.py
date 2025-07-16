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
# Tests for aws/forecast_costs.py

# Example invocations (see also docstring in forecast_costs.py):

# python aws/forecast_costs.py --input costs.csv --date-column PeriodStart --value-column UnblendedCost --method all
# python aws/forecast_costs.py --input costs.csv --date-column PeriodStart --value-column UnblendedCost --method sma --sma-window 14
# python aws/forecast_costs.py --input costs.csv --date-column PeriodStart --value-column UnblendedCost --method es --es-alpha 0.3
# python aws/forecast_costs.py --input costs.csv --date-column PeriodStart --value-column UnblendedCost --method prophet --prophet-changepoint-prior-scale 0.1
# python aws/forecast_costs.py --input costs.csv --date-column PeriodStart --value-column UnblendedCost --method prophet --prophet-seasonality-prior-scale 5.0
# python aws/forecast_costs.py --input costs.csv --date-column PeriodStart --value-column UnblendedCost --method prophet --prophet-daily-seasonality False --prophet-yearly-seasonality True --prophet-weekly-seasonality True
# python aws/forecast_costs.py --input costs.csv --date-column PeriodStart --value-column UnblendedCost --group-column Service --group-value AmazonEC2 --method all --sma-window 30 --es-alpha 0.2
# python aws/cost_and_usage.py --granularity daily --output-format csv | python aws/forecast_costs.py --date-column PeriodStart --value-column UnblendedCost --method all --sma-window 10 --es-alpha 0.7 --prophet-changepoint-prior-scale 0.2 --prophet-seasonality-prior-scale 15.0 --prophet-daily-seasonality True --prophet-yearly-seasonality True --prophet-weekly-seasonality False
# python aws/forecast_costs.py --help
# python aws/forecast_costs.py --input notfound.csv --date-column PeriodStart --value-column UnblendedCost --method all
# python aws/forecast_costs.py --date-column PeriodStart --value-column UnblendedCost --method all
# python aws/forecast_costs.py --input costs.csv --date-column PeriodStart --value-column UnblendedCost --method all --output-format time-table

"""

import unittest
from unittest.mock import patch, MagicMock
from io import StringIO
import sys
import pandas as pd
import numpy as np
import builtins
import os
import subprocess

import aws.forecast_costs as fc

class TestForecastCosts(unittest.TestCase):
    def test_load_data_file_not_found(self):
        args = MagicMock()
        args.input = "notfound.csv"
        args.group_column = None
        args.group_value = None
        args.date_column = "PeriodStart"
        args.value_column = "UnblendedCost"
        with self.assertRaises(SystemExit):
            fc.load_data(args)

    def test_load_data_missing_column(self):
        args = MagicMock()
        args.input = None
        args.group_column = None
        args.group_value = None
        args.date_column = "MissingDate"
        args.value_column = "UnblendedCost"
        # Patch stdin to provide a valid CSV
        with patch("sys.stdin", StringIO("PeriodStart,UnblendedCost\n2025-01-01,10\n")):
            with self.assertRaises(SystemExit):
                fc.load_data(args)

    def test_main_no_input_file_and_no_stdin(self):
        # Simulate no input file and no stdin
        args = [
            "forecast_costs.py",
            "--date-column", "PeriodStart",
            "--value-column", "UnblendedCost",
            "--method", "all"
        ]
        with patch.object(sys, 'argv', args):
            with patch("sys.stdin.isatty", return_value=True):
                with self.assertRaises(SystemExit):
                    fc.main()

    def test_integration_daily_csv(self):
        test_csv = os.path.join(os.path.dirname(__file__), 'input', 'daily_costs_simple.csv')
        result = subprocess.run([
            sys.executable, 'aws/forecast_costs.py',
            '--input', test_csv,
            '--date-column', 'PeriodStart',
            '--value-column', 'UnblendedCost',
            '--milestone-summary'
        ], capture_output=True, text=True)
        self.assertIn('# Forecast Milestone Summary', result.stdout)
        self.assertIn('end_of_this_month', result.stdout)
        self.assertIn('sma:', result.stdout)

    def test_integration_monthly_csv(self):
        test_csv = os.path.join(os.path.dirname(__file__), 'input', 'monthly_costs_simple.csv')
        result = subprocess.run([
            sys.executable, 'aws/forecast_costs.py',
            '--input', test_csv,
            '--date-column', 'PeriodStart',
            '--value-column', 'UnblendedCost',
            '--milestone-summary'
        ], capture_output=True, text=True)
        self.assertIn('# Forecast Milestone Summary', result.stdout)
        self.assertIn('end_of_this_month', result.stdout)
        self.assertIn('sma:', result.stdout)

    def test_integration_missing_values(self):
        test_csv = os.path.join(os.path.dirname(__file__), 'input', 'costs_with_missing.csv')
        result = subprocess.run([
            sys.executable, 'aws/forecast_costs.py',
            '--input', test_csv,
            '--date-column', 'PeriodStart',
            '--value-column', 'UnblendedCost',
            '--milestone-summary'
        ], capture_output=True, text=True)
        self.assertIn('# Forecast Milestone Summary', result.stdout)
        self.assertIn('sma:', result.stdout)

    def test_integration_short_input(self):
        test_csv = os.path.join(os.path.dirname(__file__), 'input', 'costs_short.csv')
        result = subprocess.run([
            sys.executable, 'aws/forecast_costs.py',
            '--input', test_csv,
            '--date-column', 'PeriodStart',
            '--value-column', 'UnblendedCost',
            '--milestone-summary'
        ], capture_output=True, text=True)
        self.assertIn('# Forecast Milestone Summary', result.stdout)
        self.assertIn('sma:', result.stdout)

    def test_integration_nonmonotonic_dates(self):
        test_csv = os.path.join(os.path.dirname(__file__), 'input', 'costs_nonmonotonic.csv')
        result = subprocess.run([
            sys.executable, 'aws/forecast_costs.py',
            '--input', test_csv,
            '--date-column', 'PeriodStart',
            '--value-column', 'UnblendedCost',
            '--milestone-summary'
        ], capture_output=True, text=True)
        self.assertIn('# Forecast Milestone Summary', result.stdout)
        self.assertIn('sma:', result.stdout)

if __name__ == "__main__":
    unittest.main()
