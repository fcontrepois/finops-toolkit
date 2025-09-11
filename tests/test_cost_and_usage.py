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
Tests for aws/cost_and_usage.py command.

This module tests the cost_and_usage command functionality including:
- Argument parsing and validation
- Error handling
- Output formats (CSV and JSON)
- AWS CLI integration
- Pipe compatibility
"""

import pytest
import subprocess
import sys
import os
import json
import csv
import shutil
from io import StringIO
from unittest.mock import patch, MagicMock
import tempfile

# Add the project root to the path so we can import the command
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from aws.cost_and_usage import (
    handle_error,
    check_aws_cli_available,
    run_aws_cli,
    format_aws_datetime,
    get_date_range,
    fetch_costs,
    write_csv_output,
    print_csv_summary,
    print_csv_summary_all,
    print_json_summary,
    parse_metric,
    parse_date,
    create_argument_parser,
    VALID_METRICS,
    METRIC_UNITS
)


class TestHandleError:
    """Test the handle_error function."""
    
    def test_handle_error_default_exit_code(self, capsys):
        """Test handle_error with default exit code."""
        with pytest.raises(SystemExit) as exc_info:
            handle_error("Test error message")
        
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Error: Test error message" in captured.err
    
    def test_handle_error_custom_exit_code(self, capsys):
        """Test handle_error with custom exit code."""
        with pytest.raises(SystemExit) as exc_info:
            handle_error("Test error message", 2)
        
        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "Error: Test error message" in captured.err


class TestParseMetric:
    """Test the parse_metric function."""
    
    def test_parse_metric_default(self):
        """Test parse_metric with no input returns default."""
        assert parse_metric(None) == "UnblendedCost"
        assert parse_metric("") == "UnblendedCost"
    
    def test_parse_metric_valid_single(self):
        """Test parse_metric with valid single metric."""
        assert parse_metric("BlendedCost") == "BlendedCost"
        assert parse_metric("UsageQuantity") == "UsageQuantity"
    
    def test_parse_metric_multiple_metrics_error(self, capsys):
        """Test parse_metric with multiple metrics raises error."""
        with pytest.raises(SystemExit) as exc_info:
            parse_metric("UnblendedCost,BlendedCost")
        
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Only one metric can be specified at a time" in captured.err
    
    def test_parse_metric_invalid_metric_error(self, capsys):
        """Test parse_metric with invalid metric raises error."""
        with pytest.raises(SystemExit) as exc_info:
            parse_metric("InvalidMetric")
        
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Invalid metric 'InvalidMetric'" in captured.err


class TestParseDate:
    """Test the parse_date function."""
    
    def test_parse_date_valid(self):
        """Test parse_date with valid date string."""
        result = parse_date("2024-12-01")
        assert result.year == 2024
        assert result.month == 12
        assert result.day == 1
    
    def test_parse_date_invalid_format(self, capsys):
        """Test parse_date with invalid format raises error."""
        with pytest.raises(SystemExit) as exc_info:
            parse_date("2024/12/01")
        
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Invalid date format '2024/12/01'" in captured.err


class TestFormatAwsDatetime:
    """Test the format_aws_datetime function."""
    
    def test_format_aws_datetime(self):
        """Test format_aws_datetime formats correctly."""
        from datetime import datetime
        dt = datetime(2024, 12, 1, 10, 30, 45)
        result = format_aws_datetime(dt)
        assert result == "2024-12-01T10:30:45Z"


class TestGetDateRange:
    """Test the get_date_range function."""
    
    def test_get_date_range_daily_default(self):
        """Test get_date_range for daily granularity with default interval."""
        start, end = get_date_range("DAILY", None, False)
        # Should return strings in YYYY-MM-DD format
        assert isinstance(start, str)
        assert isinstance(end, str)
        assert len(start) == 10  # YYYY-MM-DD
        assert len(end) == 10    # YYYY-MM-DD
    
    def test_get_date_range_hourly_default(self):
        """Test get_date_range for hourly granularity with default interval."""
        start, end = get_date_range("HOURLY", None, False)
        # Should return strings in ISO format
        assert isinstance(start, str)
        assert isinstance(end, str)
        assert "T" in start  # ISO format
        assert "T" in end    # ISO format
    
    def test_get_date_range_with_interval(self):
        """Test get_date_range with specific interval."""
        start, end = get_date_range("DAILY", "week", False)
        assert isinstance(start, str)
        assert isinstance(end, str)
        assert len(start) == 10
        assert len(end) == 10
    
    def test_get_date_range_invalid_granularity(self):
        """Test get_date_range with invalid granularity raises error."""
        with pytest.raises(ValueError):
            get_date_range("INVALID", None, False)
    
    def test_get_date_range_invalid_interval(self):
        """Test get_date_range with invalid interval raises error."""
        with pytest.raises(ValueError):
            get_date_range("DAILY", "invalid", False)


class TestCreateArgumentParser:
    """Test the create_argument_parser function."""
    
    def test_create_argument_parser(self):
        """Test create_argument_parser returns valid parser."""
        parser = create_argument_parser()
        assert parser is not None
        # The prog name might be different when imported as module
        assert hasattr(parser, 'prog')
    
    def test_required_arguments(self):
        """Test that required arguments are properly defined."""
        parser = create_argument_parser()
        # Test that granularity is required
        with pytest.raises(SystemExit):
            parser.parse_args([])
        
        # Test that granularity works when provided
        args = parser.parse_args(["--granularity", "daily"])
        assert args.granularity == "daily"
    
    def test_optional_arguments_defaults(self):
        """Test that optional arguments have correct defaults."""
        parser = create_argument_parser()
        args = parser.parse_args(["--granularity", "daily"])
        
        assert args.interval is None
        assert args.group == "SERVICE"
        assert args.output_format == "csv"
        assert args.metrics == "UnblendedCost"
        assert args.start is None
        assert args.end is None
        assert args.tag_key is None
        assert args.include_today is False
        assert args.verbose is False


class TestWriteCsvOutput:
    """Test the write_csv_output function."""
    
    def test_write_csv_output(self, capsys):
        """Test write_csv_output writes CSV correctly."""
        import pandas as pd
        
        df = pd.DataFrame({
            'PeriodStart': ['2024-12-01', '2024-12-02'],
            'Service': ['EC2', 'S3'],
            'UnblendedCost': [10.50, 5.25]
        })
        
        write_csv_output(df)
        
        captured = capsys.readouterr()
        lines = captured.out.strip().split('\n')
        
        assert lines[0] == "PeriodStart,Service,UnblendedCost"
        assert "2024-12-01,EC2,10.5" in lines[1]
        assert "2024-12-02,S3,5.25" in lines[2]
    
    def test_write_csv_output_no_header(self, capsys):
        """Test write_csv_output without header."""
        import pandas as pd
        
        df = pd.DataFrame({
            'PeriodStart': ['2024-12-01'],
            'Service': ['EC2'],
            'UnblendedCost': [10.50]
        })
        
        write_csv_output(df, include_header=False)
        
        captured = capsys.readouterr()
        lines = captured.out.strip().split('\n')
        
        # Should not have header
        assert len(lines) == 1
        assert "2024-12-01,EC2,10.5" in lines[0]


class TestPrintCsvSummary:
    """Test the print_csv_summary function."""
    
    def test_print_csv_summary(self):
        """Test print_csv_summary outputs correct CSV."""
        results = {
            'ResultsByTime': [
                {
                    'TimePeriod': {'Start': '2024-12-01'},
                    'Groups': [
                        {
                            'Keys': ['EC2'],
                            'Metrics': {'UnblendedCost': {'Amount': '10.50'}}
                        }
                    ]
                }
            ]
        }
        
        # Use temporary file to capture output
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp_file:
            print_csv_summary(results, "Service", "UnblendedCost", fileobj=tmp_file)
            tmp_file.flush()
            
            # Read the file content
            with open(tmp_file.name, 'r') as f:
                output = f.read()
            
            # Clean up
            os.unlink(tmp_file.name)
        
        assert "PeriodStart,Service,UnblendedCost" in output
        assert "2024-12-01,EC2,10.500000" in output


class TestPrintCsvSummaryAll:
    """Test the print_csv_summary_all function."""
    
    def test_print_csv_summary_all(self):
        """Test print_csv_summary_all outputs correct CSV."""
        results = {
            'ResultsByTime': [
                {
                    'TimePeriod': {'Start': '2024-12-01'},
                    'Total': {'UnblendedCost': {'Amount': '15.75'}}
                }
            ]
        }
        
        # Use temporary file to capture output
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp_file:
            print_csv_summary_all(results, "UnblendedCost", fileobj=tmp_file)
            tmp_file.flush()
            
            # Read the file content
            with open(tmp_file.name, 'r') as f:
                output = f.read()
            
            # Clean up
            os.unlink(tmp_file.name)
        
        assert "PeriodStart,Group,UnblendedCost" in output
        assert "2024-12-01,Total,15.750000" in output


class TestPrintJsonSummary:
    """Test the print_json_summary function."""
    
    def test_print_json_summary(self):
        """Test print_json_summary outputs correct JSON."""
        results = {
            'ResultsByTime': [
                {
                    'TimePeriod': {'Start': '2024-12-01'},
                    'Groups': []
                }
            ]
        }
        
        # Use temporary file to capture output
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp_file:
            print_json_summary(results, fileobj=tmp_file)
            tmp_file.flush()
            
            # Read the file content
            with open(tmp_file.name, 'r') as f:
                output = f.read()
            
            # Clean up
            os.unlink(tmp_file.name)
        
        # Should be valid JSON
        json.loads(output)
        assert '"Start": "2024-12-01"' in output


class TestCommandLineInterface:
    """Test the command-line interface."""
    
    def test_help_output(self):
        """Test that help output is generated correctly."""
        result = subprocess.run([
            sys.executable, "aws/cost_and_usage.py", "--help"
        ], capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(__file__)))
        
        assert result.returncode == 0
        assert "Fetch AWS cost and usage data from Cost Explorer API" in result.stdout
        assert "--granularity" in result.stdout
        assert "Examples:" in result.stdout
    
    def test_missing_required_argument(self):
        """Test that missing required argument causes error."""
        result = subprocess.run([
            sys.executable, "aws/cost_and_usage.py"
        ], capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(__file__)))
        
        assert result.returncode != 0
        assert "required" in result.stderr.lower()
    
    def test_invalid_granularity(self):
        """Test that invalid granularity causes error."""
        result = subprocess.run([
            sys.executable, "aws/cost_and_usage.py", "--granularity", "invalid"
        ], capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(__file__)))
        
        assert result.returncode != 0
        assert "invalid choice" in result.stderr.lower()
    
    def test_tag_key_without_tag_group(self):
        """Test that tag-key without TAG group causes error."""
        result = subprocess.run([
            sys.executable, "aws/cost_and_usage.py", 
            "--granularity", "daily",
            "--tag-key", "Environment"
        ], capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(__file__)))
        
        assert result.returncode == 1
        assert "--tag-key can only be used with --group TAG" in result.stderr
    
    def test_tag_group_without_tag_key(self):
        """Test that TAG group without tag-key causes error."""
        result = subprocess.run([
            sys.executable, "aws/cost_and_usage.py", 
            "--granularity", "daily",
            "--group", "TAG"
        ], capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(__file__)))
        
        assert result.returncode == 1
        assert "--tag-key is required when grouping by TAG" in result.stderr


class TestAwsCliIntegration:
    """Test AWS CLI integration (requires AWS CLI to be configured)."""
    
    @pytest.mark.skipif(
        not shutil.which("aws"),
        reason="AWS CLI not available"
    )
    def test_aws_cli_available(self):
        """Test that AWS CLI availability check works."""
        # This should not raise an exception if AWS CLI is available
        try:
            check_aws_cli_available()
        except SystemExit as e:
            # If AWS CLI is not configured, that's also a valid test result
            assert e.code == 4
    
    @pytest.mark.skipif(
        not shutil.which("aws"),
        reason="AWS CLI not available"
    )
    def test_real_aws_integration(self):
        """Test real AWS integration with a small date range."""
        result = subprocess.run([
            sys.executable, "aws/cost_and_usage.py",
            "--granularity", "daily",
            "--start", "2024-12-01",
            "--end", "2024-12-02"
        ], capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(__file__)))
        
        # If AWS CLI is configured, this should work
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            assert len(lines) > 1  # Should have header + data
            assert "PeriodStart,Service,UnblendedCost" in lines[0]
        else:
            # If not configured, should get a clear error message
            assert "AWS CLI" in result.stderr or "credentials" in result.stderr


class TestPipeCompatibility:
    """Test pipe compatibility."""
    
    def test_pipe_with_head(self):
        """Test that output can be piped to head command."""
        result = subprocess.run([
            "bash", "-c", 
            f"{sys.executable} aws/cost_and_usage.py --granularity daily --start 2024-12-01 --end 2024-12-02 | head -5"
        ], capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(__file__)))
        
        # This test might fail if AWS CLI is not configured, which is expected
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            assert len(lines) <= 5  # head -5 should limit output
            # If there's output, check for the expected header
            if lines[0]:  # Only check if there's actual output
                assert "PeriodStart,Service,UnblendedCost" in lines[0]


class TestConstants:
    """Test that constants are properly defined."""
    
    def test_valid_metrics_constant(self):
        """Test VALID_METRICS constant."""
        assert isinstance(VALID_METRICS, list)
        assert len(VALID_METRICS) > 0
        assert "UnblendedCost" in VALID_METRICS
        assert "BlendedCost" in VALID_METRICS
    
    def test_metric_units_constant(self):
        """Test METRIC_UNITS constant."""
        assert isinstance(METRIC_UNITS, dict)
        assert "UnblendedCost" in METRIC_UNITS
        assert METRIC_UNITS["UnblendedCost"] == "USD"


if __name__ == "__main__":
    pytest.main([__file__])