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

import aws.forecast_costs as fc

class TestForecastCosts(unittest.TestCase):

    def setUp(self):
        # Minimal DataFrame for tests
        self.df = pd.DataFrame({
            "PeriodStart": pd.date_range("2025-01-01", periods=10, freq="D"),
            "UnblendedCost": np.arange(10, 20)
        })

    def test_simple_moving_average(self):
        target_dates = {"end_of_week": pd.Timestamp("2025-01-10")}
        result = fc.simple_moving_average(self.df, "PeriodStart", "UnblendedCost", target_dates, window=3)
        self.assertIn("end_of_week", result)
        self.assertAlmostEqual(result["end_of_week"], self.df["UnblendedCost"].rolling(window=3, min_periods=1).mean().iloc[-1])

    def test_exponential_smoothing(self):
        target_dates = {"end_of_week": pd.Timestamp("2025-01-10")}
        result = fc.exponential_smoothing(self.df, "PeriodStart", "UnblendedCost", target_dates, alpha=0.5)
        self.assertIn("end_of_week", result)
        # The value should be a float
        self.assertIsInstance(result["end_of_week"], float)

    def test_get_forecast_horizons(self):
        horizons = fc.get_forecast_horizons(self.df, "PeriodStart")
        self.assertIn("end_of_week", horizons)
        self.assertIn("end_of_month", horizons)
        self.assertIn("end_of_quarter_1", horizons)
        self.assertIn("end_of_year", horizons)

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

    def test_print_forecasts(self):
        # Should print formatted output to stdout
        forecasts = {"end_of_week": 123.456, "end_of_month": None}
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            fc.print_forecasts("TestMethod", forecasts)
            output = mock_stdout.getvalue()
            self.assertIn("Forecasts using TestMethod:", output)
            self.assertIn("End Of Week: 123.46", output)
            self.assertIn("End Of Month: N/A", output)

    def test_output_time_table(self):
        df = pd.DataFrame({
            "PeriodStart": pd.date_range("2025-01-01", periods=2, freq="D"),
            "UnblendedCost": [10, 20]
        })
        forecasts_dict = {
            "SMA": {pd.Timestamp("2025-01-10").date(): 42.0}
        }
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            fc.output_time_table(df, "PeriodStart", "UnblendedCost", forecasts_dict)
            output = mock_stdout.getvalue()
            self.assertIn("date,value,forecast,methodology", output)
            self.assertIn("Real", output)
            self.assertIn("SMA", output)

    def test_parse_args_help(self):
        # Should not raise, just print help and exit
        test_args = ["forecast_costs.py", "--help"]
        with patch.object(sys, 'argv', test_args):
            with self.assertRaises(SystemExit):
                fc.parse_args()

    def test_prophet_import_error(self):
        # Simulate Prophet not installed
        with patch.dict('sys.modules', {'prophet': None, 'fbprophet': None}):
            result = fc.prophet_forecast(self.df, "PeriodStart", "UnblendedCost", {"end_of_week": pd.Timestamp("2025-01-10")})
            self.assertIsNone(result["end_of_week"])

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

if __name__ == "__main__":
    unittest.main()
