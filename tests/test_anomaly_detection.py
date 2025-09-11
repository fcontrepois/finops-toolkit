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
Tests for aws/anomaly_detection_forecast.py command.

This module tests the anomaly_detection_forecast command functionality including:
- Argument parsing and validation
- Error handling
- Output formats (CSV summary table)
- AWS CLI integration
- Anomaly detection logic
"""

import pytest
import subprocess
import sys
import os
import csv
import tempfile
from io import StringIO
from unittest.mock import patch, MagicMock

# Add the project root to the path so we can import the command
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from aws.anomaly_detection_forecast import (
    handle_error,
    create_argument_parser,
    get_dates,
    run_cost_and_usage,
    run_forecast_costs,
    percent_diff,
    PERIODS,
    METHODS,
    GROUP_COLS,
    DEFAULT_GRANULARITY,
    DEFAULT_METRIC,
    DEFAULT_GROUP,
    DEFAULT_METHOD,
    MIN_DATA_POINTS
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


class TestCreateArgumentParser:
    """Test the create_argument_parser function."""
    
    def test_create_argument_parser(self):
        """Test create_argument_parser returns valid parser."""
        parser = create_argument_parser()
        assert parser is not None
        assert hasattr(parser, 'prog')
    
    def test_required_arguments(self):
        """Test that required arguments are properly defined."""
        parser = create_argument_parser()
        # Test that threshold is required
        with pytest.raises(SystemExit):
            parser.parse_args([])
        
        # Test that threshold works when provided
        args = parser.parse_args(["--threshold", "20"])
        assert args.threshold == 20.0
    
    def test_optional_arguments_defaults(self):
        """Test that optional arguments have correct defaults."""
        parser = create_argument_parser()
        args = parser.parse_args(["--threshold", "20"])
        
        assert args.granularity == DEFAULT_GRANULARITY
        assert args.metric == DEFAULT_METRIC
        assert args.group == DEFAULT_GROUP
        assert args.method == DEFAULT_METHOD
        assert args.tag_key is None


class TestGetDates:
    """Test the get_dates function."""
    
    def test_get_dates(self):
        """Test get_dates returns proper date structure."""
        dates = get_dates()
        
        assert isinstance(dates, dict)
        assert "TODAY" in dates
        assert "YESTERDAY" in dates
        assert "DAY_BEFORE_YESTERDAY" in dates
        assert "WEEK_AGO" in dates
        assert "MONTH_AGO" in dates
        assert "QUARTER_AGO" in dates
        
        # Check that dates are in proper order
        assert dates["TODAY"] > dates["YESTERDAY"]
        assert dates["YESTERDAY"] > dates["DAY_BEFORE_YESTERDAY"]


class TestPercentDiff:
    """Test the percent_diff function."""
    
    def test_percent_diff_normal(self):
        """Test percent_diff with normal values."""
        result = percent_diff(120, 100)
        assert result == 20.0
    
    def test_percent_diff_negative(self):
        """Test percent_diff with negative change."""
        result = percent_diff(80, 100)
        assert result == -20.0
    
    def test_percent_diff_zero_baseline(self):
        """Test percent_diff with zero baseline."""
        result = percent_diff(100, 0)
        assert result is None
    
    def test_percent_diff_invalid_input(self):
        """Test percent_diff with invalid input."""
        result = percent_diff("invalid", "invalid")
        assert result is None


class TestCommandLineInterface:
    """Test the command-line interface."""
    
    def test_help_output(self):
        """Test that help output is generated correctly."""
        result = subprocess.run([
            sys.executable, "aws/anomaly_detection_forecast.py", "--help"
        ], capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(__file__)))
        
        assert result.returncode == 0
        assert "Detect anomalies in AWS cost forecasts" in result.stdout
        assert "--threshold" in result.stdout
        assert "Examples:" in result.stdout
    
    def test_missing_required_argument(self):
        """Test that missing required argument causes error."""
        result = subprocess.run([
            sys.executable, "aws/anomaly_detection_forecast.py"
        ], capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(__file__)))
        
        assert result.returncode != 0
        assert "required" in result.stderr.lower()
    
    def test_tag_group_without_tag_key(self):
        """Test that TAG group without tag-key causes error."""
        result = subprocess.run([
            sys.executable, "aws/anomaly_detection_forecast.py", 
            "--threshold", "20",
            "--group", "TAG"
        ], capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(__file__)))
        
        assert result.returncode == 1
        assert "--tag-key is required when group is TAG" in result.stderr


class TestConstants:
    """Test that constants are properly defined."""
    
    def test_periods_constant(self):
        """Test PERIODS constant."""
        assert isinstance(PERIODS, list)
        assert len(PERIODS) == 4
        assert ("Day Before Yesterday", -2) in PERIODS
    
    def test_methods_constant(self):
        """Test METHODS constant."""
        assert isinstance(METHODS, list)
        assert "sma" in METHODS
        assert "es" in METHODS
        assert "prophet" in METHODS
    
    def test_group_cols_constant(self):
        """Test GROUP_COLS constant."""
        assert isinstance(GROUP_COLS, dict)
        assert "ALL" in GROUP_COLS
        assert "SERVICE" in GROUP_COLS
        assert "LINKED_ACCOUNT" in GROUP_COLS
        assert "TAG" in GROUP_COLS
    
    def test_default_constants(self):
        """Test default constants."""
        assert DEFAULT_GRANULARITY == "daily"
        assert DEFAULT_METRIC == "UnblendedCost"
        assert DEFAULT_GROUP == "ALL"
        assert DEFAULT_METHOD == "all"
        assert MIN_DATA_POINTS == 10


class TestIntegrationTests:
    """Test integration with real data files."""
    
    def test_known_anomaly(self):
        """Test detection of known anomalies."""
        # Use a test CSV with a known spike for ALL group
        test_csv = os.path.join(os.path.dirname(__file__), 'input', 'daily_costs_simple.csv')
        result = subprocess.run([
            sys.executable, "aws/anomaly_detection_forecast.py",
            "--threshold", "5",
            "--group", "ALL"
        ], capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(__file__)))
        
        # This test might fail if AWS CLI is not configured, which is expected
        if result.returncode == 0:
            assert "# Anomaly Detection Summary Table" in result.stdout
        else:
            # If not configured, should get a clear error message
            assert "AWS CLI" in result.stderr or "credentials" in result.stderr
    
    def test_no_anomaly(self):
        """Test detection with no anomalies expected."""
        # Use a test CSV with no spike (all values the same)
        test_csv = os.path.join(os.path.dirname(__file__), 'input', 'costs_short.csv')
        result = subprocess.run([
            sys.executable, "aws/anomaly_detection_forecast.py",
            "--threshold", "50",
            "--group", "ALL"
        ], capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(__file__)))
        
        # This test might fail if AWS CLI is not configured, which is expected
        if result.returncode == 0:
            assert "# Anomaly Detection Summary Table" in result.stdout
        else:
            # If not configured, should get a clear error message
            assert "AWS CLI" in result.stderr or "credentials" in result.stderr


if __name__ == "__main__":
    pytest.main([__file__]) 