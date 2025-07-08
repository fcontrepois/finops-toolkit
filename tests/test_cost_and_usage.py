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
# Tests for aws/cost_and_usage.py

This file contains unit tests for the main cost and usage script in the FinOps Toolkit.

# Example invocations (see also docstring in cost_and_usage.py):

# Run the tests with:
python -m unittest tests/test_cost_and_usage.py

# Or, from the root of the repository:
pytest tests/test_cost_and_usage.py

# Example invocations of the script under test:
# python aws/cost_and_usage.py --granularity daily
# python aws/cost_and_usage.py --granularity daily --group SERVICE
# python aws/cost_and_usage.py --granularity daily --group ALL
# python aws/cost_and_usage.py --granularity daily --metrics UnblendedCost
# python aws/cost_and_usage.py --granularity daily --metrics BlendedCost
# python aws/cost_and_usage.py --granularity daily --metrics UnblendedCost,BlendedCost
# python aws/cost_and_usage.py --granularity daily --group TAG --tag-key Owner
# python aws/cost_and_usage.py --granularity daily --group TAG
# python aws/cost_and_usage.py --granularity daily --tag-key Owner
# python aws/cost_and_usage.py --granularity daily --interval nonsense
# python aws/cost_and_usage.py --granularity daily --output-format nonsense
# python aws/cost_and_usage.py --granularity daily --start 2025-01-01 --end 2025-01-31
# python aws/cost_and_usage.py --granularity daily --group SERVICE --verbose
"""

import unittest
from unittest.mock import patch
from io import StringIO
import sys
import json
import subprocess
import aws.cost_and_usage as cau
from datetime import datetime

class TestCostAndUsage(unittest.TestCase):

    def test_parse_metric_valid(self):
        self.assertEqual(cau.parse_metric("BlendedCost"), "BlendedCost")

    def test_parse_metric_default(self):
        self.assertEqual(cau.parse_metric(None), "UnblendedCost")

    def test_parse_metric_invalid(self):
        with self.assertRaises(SystemExit):
            cau.parse_metric("InvalidCost")

    def test_parse_metric_multiple(self):
        with self.assertRaises(SystemExit):
            cau.parse_metric("BlendedCost,UnblendedCost")

    def test_format_aws_datetime(self):
        dt = datetime(2025, 7, 1, 12, 0)
        self.assertEqual(cau.format_aws_datetime(dt), "2025-07-01T12:00:00Z")

    @patch("aws.cost_and_usage.subprocess.run")
    def test_run_aws_cli_success(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout=json.dumps({"ResultsByTime": []}), stderr=""
        )
        result = cau.run_aws_cli(["fake", "command"])
        self.assertEqual(result, {"ResultsByTime": []})

    @patch("aws.cost_and_usage.subprocess.run", side_effect=subprocess.CalledProcessError(1, 'cmd', stderr='error'))
    def test_run_aws_cli_failure(self, mock_run):
        with self.assertRaises(SystemExit):
            cau.run_aws_cli(["fake", "command"])

    def test_get_date_range_invalid_granularity(self):
        with self.assertRaises(ValueError):
            cau.get_date_range("INVALID", None, False)

    def test_get_date_range_interval_invalid(self):
        with self.assertRaises(ValueError):
            cau.get_date_range("DAILY", "nonsense", False)

    def test_parse_date_valid(self):
        self.assertEqual(cau.parse_date("2025-01-31").isoformat(), "2025-01-31")

    def test_parse_date_invalid(self):
        with self.assertRaises(SystemExit):
            cau.parse_date("2025-31-01")  # invalid format

    def test_print_csv_summary_grouped_header_unit(self):
        results = {
            "ResultsByTime": [
                {
                    "TimePeriod": {"Start": "2025-07-01"},
                    "Groups": [
                        {
                            "Keys": ["AmazonEC2"],
                            "Metrics": {"UnblendedCost": {"Amount": "123.456"}}
                        }
                    ]
                }
            ]
        }
        output = StringIO()
        cau.print_csv_summary(results, "Service", "UnblendedCost", fileobj=output)
        csv_output = output.getvalue()
        self.assertIn("UnblendedCost", csv_output)
        self.assertIn("123.456000", csv_output)

    def test_print_csv_summary_all_header_unit(self):
        results = {
            "ResultsByTime": [
                {"TimePeriod": {"Start": "2025-07-01"},
                 "Total": {"UnblendedCost": {"Amount": "42.123456"}}}
            ]
        }
        output = StringIO()
        cau.print_csv_summary_all(results, "UnblendedCost", fileobj=output)
        csv_output = output.getvalue()
        lines = csv_output.strip().splitlines()
        # Check header
        self.assertEqual(lines[0].split(","), ["PeriodStart", "Group", "UnblendedCost"])
        # Check row
        row = lines[1].split(",")
        self.assertEqual(row[0], "2025-07-01")
        self.assertEqual(row[1], "Total")
        self.assertEqual(row[2], "42.123456")


    def test_print_json_summary(self):
        results = {"ResultsByTime": [{"TimePeriod": {"Start": "2025-07-01"}}]}
        output = StringIO()
        cau.print_json_summary(results, fileobj=output)
        self.assertIn('"Start": "2025-07-01"', output.getvalue())

    def test_verbose_flag_effect(self):
        with patch("aws.cost_and_usage.run_aws_cli") as mock_run:
            mock_run.return_value = {"ResultsByTime": [], "NextPageToken": None}
            results = cau.fetch_costs("2025-01-01", "2025-01-02", None, "DAILY", "UnblendedCost", verbose=True)
            self.assertIn("ResultsByTime", results)

if __name__ == "__main__":
    unittest.main()
