# tests/test_cost_and_usage.py

import unittest
from unittest.mock import patch
from io import StringIO
import sys
import json
import subprocess
import aws.cost_and_usage as cau  # Adjust this if needed

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
        dt = cau.datetime(2025, 7, 1, 12, 0)
        self.assertEqual(cau.format_aws_datetime(dt), "2025-07-01T12:00:00Z")

    @patch("aws.cost_and_usage.subprocess.run")
    def test_run_aws_cli_success(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=json.dumps({"key": "value"}),
            stderr=""
        )
        result = cau.run_aws_cli(["fake", "command"])
        self.assertEqual(result, {"key": "value"})

    @patch("aws.cost_and_usage.subprocess.run", side_effect=subprocess.CalledProcessError(1, 'cmd', stderr='error'))
    def test_run_aws_cli_failure(self, mock_run):
        with self.assertRaises(SystemExit):
            cau.run_aws_cli(["fake", "command"])

    def test_get_date_range_default_daily(self):
        start, end = cau.get_date_range("DAILY", None, False)
        self.assertTrue(len(start) == 10)
        self.assertTrue(len(end) == 10)

    def test_get_date_range_invalid_granularity(self):
        with self.assertRaises(ValueError):
            cau.get_date_range("INVALID", None, False)

    def test_get_date_range_interval_invalid(self):
        with self.assertRaises(ValueError):
            cau.get_date_range("DAILY", "nonsense", False)

    def test_print_csv_summary_all(self):
        results = {
            "ResultsByTime": [
                {
                    "TimePeriod": {"Start": "2025-07-01"},
                    "Total": {"UnblendedCost": {"Amount": "123.456"}}
                }
            ]
        }
        output = StringIO()
        cau.print_csv_summary_all(results, "UnblendedCost", fileobj=output)
        self.assertIn("2025-07-01", output.getvalue())
        self.assertIn("123.456000", output.getvalue())

    def test_print_json_summary(self):
        results = {"ResultsByTime": []}
        output = StringIO()
        cau.print_json_summary(results, fileobj=output)
        self.assertIn('"ResultsByTime": []', output.getvalue())


if __name__ == '__main__':
    unittest.main()

