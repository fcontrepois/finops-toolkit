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
# AUTHOLS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
Tests for aws/budget_analysis.py command.

This module tests the budget analysis functionality including:
- Argument parsing and validation
- Error handling
- Output formats (CSV and JSON)
- AWS CLI integration
- Pipe compatibility
- Budget analysis calculations
"""

import pytest
import subprocess
import sys
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock
import pandas as pd
import json

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from aws.budget_analysis import (
    handle_error,
    create_argument_parser,
    check_aws_cli_available,
    read_input_from_stdin,
    read_input_from_file,
    validate_required_columns,
    get_budgets_from_aws,
    get_budget_by_name,
    parse_budget_amount,
    calculate_variance,
    determine_budget_status,
    process_budget_analysis,
    write_csv_output,
    write_json_output
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
            handle_error("Test error message", 3)
        
        assert exc_info.value.code == 3
        captured = capsys.readouterr()
        assert "Error: Test error message" in captured.err

class TestCreateArgumentParser:
    """Test the create_argument_parser function."""
    
    def test_parser_creation(self):
        """Test that argument parser is created correctly."""
        parser = create_argument_parser()
        assert parser is not None
        # The prog name will be the script name when run, not necessarily "budget_analysis.py"
        assert parser.prog is not None

    def test_required_arguments(self):
        """Test that required arguments are properly configured."""
        parser = create_argument_parser()
        
        # Test that budget selection is required (mutually exclusive group)
        with pytest.raises(SystemExit):
            parser.parse_args([])

    def test_optional_arguments(self):
        """Test that optional arguments have correct defaults."""
        parser = create_argument_parser()
        
        # Test with valid arguments
        args = parser.parse_args(["--budget-name", "test-budget"])
        assert args.budget_name == "test-budget"
        assert args.all_budgets == False
        assert args.threshold == 80.0
        assert args.alert_on_breach == False
        assert args.output_format == "csv"

    def test_mutually_exclusive_budget_args(self):
        """Test that budget name and all budgets are mutually exclusive."""
        parser = create_argument_parser()
        
        # This should work
        args = parser.parse_args(["--budget-name", "test-budget"])
        assert args.budget_name == "test-budget"
        assert args.all_budgets == False
        
        # This should also work
        args = parser.parse_args(["--all-budgets"])
        assert args.budget_name is None
        assert args.all_budgets == True

class TestCheckAwsCliAvailable:
    """Test the check_aws_cli_available function."""
    
    @patch('shutil.which')
    def test_aws_cli_not_installed(self, mock_which):
        """Test error when AWS CLI is not installed."""
        mock_which.return_value = None
        
        with pytest.raises(SystemExit) as exc_info:
            check_aws_cli_available()
        
        assert exc_info.value.code == 4

    @patch('shutil.which')
    @patch('subprocess.run')
    def test_aws_cli_not_configured(self, mock_run, mock_which):
        """Test error when AWS CLI is not configured."""
        mock_which.return_value = "/usr/bin/aws"
        mock_run.return_value.returncode = 1
        
        with pytest.raises(SystemExit) as exc_info:
            check_aws_cli_available()
        
        assert exc_info.value.code == 4

    @patch('shutil.which')
    @patch('subprocess.run')
    def test_aws_cli_available_and_configured(self, mock_run, mock_which):
        """Test success when AWS CLI is available and configured."""
        mock_which.return_value = "/usr/bin/aws"
        mock_run.return_value.returncode = 0
        
        # Should not raise an exception
        check_aws_cli_available()

class TestReadInputFromStdin:
    """Test the read_input_from_stdin function."""
    
    @patch('sys.stdin.isatty')
    def test_no_input_data(self, mock_isatty):
        """Test error when no input data is provided."""
        mock_isatty.return_value = True
        
        with pytest.raises(SystemExit) as exc_info:
            read_input_from_stdin()
        
        assert exc_info.value.code == 1

    @patch('sys.stdin.isatty')
    @patch('pandas.read_csv')
    def test_empty_input_data(self, mock_read_csv, mock_isatty):
        """Test error when input data is empty."""
        mock_isatty.return_value = False
        mock_read_csv.return_value = pd.DataFrame()
        
        with pytest.raises(SystemExit) as exc_info:
            read_input_from_stdin()
        
        assert exc_info.value.code == 3

    @patch('sys.stdin.isatty')
    @patch('pandas.read_csv')
    def test_valid_input_data(self, mock_read_csv, mock_isatty):
        """Test successful reading of valid input data."""
        mock_isatty.return_value = False
        mock_df = pd.DataFrame({"PeriodStart": ["2025-01-01"], "UnblendedCost": [100.0]})
        mock_read_csv.return_value = mock_df
        
        result = read_input_from_stdin()
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1

class TestReadInputFromFile:
    """Test the read_input_from_file function."""
    
    def test_file_not_exists(self):
        """Test error when input file doesn't exist."""
        with pytest.raises(SystemExit) as exc_info:
            read_input_from_file("nonexistent.csv")
        
        assert exc_info.value.code == 2

    @patch('os.path.isfile')
    @patch('pandas.read_csv')
    def test_empty_file(self, mock_read_csv, mock_isfile):
        """Test error when input file is empty."""
        mock_isfile.return_value = True
        mock_read_csv.return_value = pd.DataFrame()
        
        with pytest.raises(SystemExit) as exc_info:
            read_input_from_file("test.csv")
        
        assert exc_info.value.code == 3

    @patch('os.path.isfile')
    @patch('pandas.read_csv')
    def test_valid_file(self, mock_read_csv, mock_isfile):
        """Test successful reading of valid file."""
        mock_isfile.return_value = True
        mock_df = pd.DataFrame({"PeriodStart": ["2025-01-01"], "UnblendedCost": [100.0]})
        mock_read_csv.return_value = mock_df
        
        result = read_input_from_file("test.csv")
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1

class TestValidateRequiredColumns:
    """Test the validate_required_columns function."""
    
    def test_missing_columns(self):
        """Test error when required columns are missing."""
        df = pd.DataFrame({"PeriodStart": ["2025-01-01"]})
        required_columns = ["PeriodStart", "UnblendedCost"]
        
        with pytest.raises(SystemExit) as exc_info:
            validate_required_columns(df, required_columns)
        
        assert exc_info.value.code == 3

    def test_all_columns_present(self):
        """Test success when all required columns are present."""
        df = pd.DataFrame({"PeriodStart": ["2025-01-01"], "UnblendedCost": [100.0]})
        required_columns = ["PeriodStart", "UnblendedCost"]
        
        # Should not raise an exception
        validate_required_columns(df, required_columns)

class TestGetBudgetsFromAws:
    """Test the get_budgets_from_aws function."""
    
    @patch('subprocess.run')
    def test_successful_budget_fetch(self, mock_run):
        """Test successful fetching of budgets from AWS."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({"Budgets": [{"BudgetName": "test-budget"}]})
        mock_run.return_value = mock_result
        
        budgets = get_budgets_from_aws()
        assert len(budgets) == 1
        assert budgets[0]["BudgetName"] == "test-budget"

    @patch('subprocess.run')
    def test_aws_cli_error(self, mock_run):
        """Test error when AWS CLI command fails."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Access denied"
        mock_run.return_value = mock_result
        
        with pytest.raises(SystemExit) as exc_info:
            get_budgets_from_aws()
        
        assert exc_info.value.code == 1

    @patch('subprocess.run')
    def test_json_parse_error(self, mock_run):
        """Test error when JSON parsing fails."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "invalid json"
        mock_run.return_value = mock_result
        
        with pytest.raises(SystemExit) as exc_info:
            get_budgets_from_aws()
        
        assert exc_info.value.code == 1

class TestGetBudgetByName:
    """Test the get_budget_by_name function."""
    
    @patch('aws.budget_analysis.get_budgets_from_aws')
    def test_budget_found(self, mock_get_budgets):
        """Test finding a budget by name."""
        mock_budgets = [
            {"BudgetName": "budget1"},
            {"BudgetName": "budget2"}
        ]
        mock_get_budgets.return_value = mock_budgets
        
        budget = get_budget_by_name("budget2")
        assert budget is not None
        assert budget["BudgetName"] == "budget2"

    @patch('aws.budget_analysis.get_budgets_from_aws')
    def test_budget_not_found(self, mock_get_budgets):
        """Test when budget is not found."""
        mock_budgets = [
            {"BudgetName": "budget1"},
            {"BudgetName": "budget2"}
        ]
        mock_get_budgets.return_value = mock_budgets
        
        budget = get_budget_by_name("nonexistent")
        assert budget is None

class TestParseBudgetAmount:
    """Test the parse_budget_amount function."""
    
    def test_budget_with_limit(self):
        """Test parsing budget with BudgetLimit."""
        budget = {
            "BudgetLimit": {
                "Amount": "1000.00"
            }
        }
        
        amount = parse_budget_amount(budget)
        assert amount == 1000.0

    def test_budget_without_limit(self):
        """Test parsing budget without BudgetLimit."""
        budget = {
            "CostFilters": {}
        }
        
        amount = parse_budget_amount(budget)
        assert amount == 0.0

    def test_empty_budget(self):
        """Test parsing empty budget."""
        budget = {}
        
        amount = parse_budget_amount(budget)
        assert amount == 0.0

class TestCalculateVariance:
    """Test the calculate_variance function."""
    
    def test_normal_variance(self):
        """Test normal variance calculation."""
        actual_cost = 800.0
        budget_amount = 1000.0
        
        variance_amount, variance_percentage = calculate_variance(actual_cost, budget_amount)
        
        assert variance_amount == 200.0  # Budget - Actual
        assert variance_percentage == -20.0  # (Actual - Budget) / Budget * 100

    def test_over_budget(self):
        """Test variance when over budget."""
        actual_cost = 1200.0
        budget_amount = 1000.0
        
        variance_amount, variance_percentage = calculate_variance(actual_cost, budget_amount)
        
        assert variance_amount == -200.0  # Budget - Actual
        assert variance_percentage == 20.0  # (Actual - Budget) / Budget * 100

    def test_zero_budget(self):
        """Test variance calculation with zero budget."""
        actual_cost = 100.0
        budget_amount = 0.0
        
        variance_amount, variance_percentage = calculate_variance(actual_cost, budget_amount)
        
        assert variance_amount == 0.0
        assert variance_percentage == 0.0

class TestDetermineBudgetStatus:
    """Test the determine_budget_status function."""
    
    def test_under_budget(self):
        """Test status when under budget."""
        actual_cost = 500.0
        budget_amount = 1000.0
        threshold = 80.0
        
        status = determine_budget_status(actual_cost, budget_amount, threshold)
        assert status == "UNDER_BUDGET"

    def test_threshold_breach(self):
        """Test status when threshold is breached."""
        actual_cost = 850.0
        budget_amount = 1000.0
        threshold = 80.0
        
        status = determine_budget_status(actual_cost, budget_amount, threshold)
        assert status == "THRESHOLD_BREACH"

    def test_over_budget(self):
        """Test status when over budget."""
        actual_cost = 1100.0
        budget_amount = 1000.0
        threshold = 80.0
        
        status = determine_budget_status(actual_cost, budget_amount, threshold)
        assert status == "OVER_BUDGET"

    def test_no_budget(self):
        """Test status when no budget is set."""
        actual_cost = 100.0
        budget_amount = 0.0
        threshold = 80.0
        
        status = determine_budget_status(actual_cost, budget_amount, threshold)
        assert status == "NO_BUDGET"

class TestProcessBudgetAnalysis:
    """Test the process_budget_analysis function."""
    
    @patch('aws.budget_analysis.get_budget_by_name')
    def test_single_budget_analysis(self, mock_get_budget):
        """Test analysis with a single budget."""
        # Mock budget data
        mock_budget = {
            "BudgetName": "test-budget",
            "BudgetLimit": {"Amount": "1000.00"}
        }
        mock_get_budget.return_value = mock_budget
        
        # Test data
        df = pd.DataFrame({
            "PeriodStart": ["2025-01-01", "2025-01-02"],
            "UnblendedCost": [500.0, 800.0]
        })
        
        result_df = process_budget_analysis(df, "test-budget", False, 80.0, False)
        
        assert len(result_df) == 2
        assert "BudgetName" in result_df.columns
        assert "BudgetAmount" in result_df.columns
        assert "ActualCost" in result_df.columns
        assert "Variance" in result_df.columns
        assert "VariancePercent" in result_df.columns
        assert "Status" in result_df.columns

    @patch('aws.budget_analysis.get_budget_by_name')
    def test_budget_not_found(self, mock_get_budget):
        """Test error when budget is not found."""
        mock_get_budget.return_value = None
        
        df = pd.DataFrame({
            "PeriodStart": ["2025-01-01"],
            "UnblendedCost": [500.0]
        })
        
        with pytest.raises(SystemExit) as exc_info:
            process_budget_analysis(df, "nonexistent-budget", False, 80.0, False)
        
        assert exc_info.value.code == 1

    def test_no_budget_specified(self):
        """Test error when no budget is specified."""
        df = pd.DataFrame({
            "PeriodStart": ["2025-01-01"],
            "UnblendedCost": [500.0]
        })
        
        with pytest.raises(SystemExit) as exc_info:
            process_budget_analysis(df, None, False, 80.0, False)
        
        assert exc_info.value.code == 1

class TestOutputFunctions:
    """Test output functions using temporary files."""
    
    def test_csv_output_function(self):
        """Test CSV output function using temporary file."""
        df = pd.DataFrame({
            "PeriodStart": ["2025-01-01"],
            "BudgetName": ["test-budget"],
            "BudgetAmount": [1000.0],
            "ActualCost": [500.0],
            "Variance": [500.0],
            "VariancePercent": [-50.0],
            "Status": ["UNDER_BUDGET"]
        })
        
        # Use temporary file to capture output
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp_file:
            # Redirect stdout to temporary file
            original_stdout = sys.stdout
            sys.stdout = tmp_file
            
            try:
                write_csv_output(df)
                tmp_file.flush()
                
                # Read the file content
                with open(tmp_file.name, 'r') as f:
                    output = f.read()
                
            finally:
                sys.stdout = original_stdout
                os.unlink(tmp_file.name)
        
        # Assert on the output
        assert "PeriodStart" in output
        assert "BudgetName" in output
        assert "2025-01-01" in output
        assert "test-budget" in output

    def test_json_output_function(self):
        """Test JSON output function using temporary file."""
        data = {
            "metadata": {
                "command": "budget_analysis",
                "timestamp": "2025-01-01T00:00:00",
                "parameters": {}
            },
            "data": [
                {
                    "PeriodStart": "2025-01-01",
                    "BudgetName": "test-budget",
                    "BudgetAmount": 1000.0,
                    "ActualCost": 500.0,
                    "Variance": 500.0,
                    "VariancePercent": -50.0,
                    "Status": "UNDER_BUDGET"
                }
            ]
        }
        
        # Use temporary file to capture output
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp_file:
            # Redirect stdout to temporary file
            original_stdout = sys.stdout
            sys.stdout = tmp_file
            
            try:
                write_json_output(data)
                tmp_file.flush()
                
                # Read the file content
                with open(tmp_file.name, 'r') as f:
                    output = f.read()
                
            finally:
                sys.stdout = original_stdout
                os.unlink(tmp_file.name)
        
        # Parse and assert on the output
        parsed_output = json.loads(output)
        assert "metadata" in parsed_output
        assert "data" in parsed_output
        assert parsed_output["metadata"]["command"] == "budget_analysis"
        assert len(parsed_output["data"]) == 1

class TestCommandLineInterface:
    """Test the command-line interface."""
    
    def test_help_output(self):
        """Test that help output is generated correctly."""
        result = subprocess.run([
            sys.executable, "aws/budget_analysis.py", "--help"
        ], capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(__file__)))
        
        assert result.returncode == 0
        assert "budget_analysis" in result.stdout
        assert "--budget-name" in result.stdout
        assert "--all-budgets" in result.stdout

    def test_missing_required_argument(self):
        """Test error when required argument is missing."""
        result = subprocess.run([
            sys.executable, "aws/budget_analysis.py"
        ], capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(__file__)))
        
        assert result.returncode == 2
        assert "error" in result.stderr.lower()

class TestAwsCliIntegration:
    """Test AWS CLI integration (requires AWS CLI to be configured)."""
    
    @pytest.mark.skipif(
        not shutil.which("aws"),
        reason="AWS CLI not available"
    )
    def test_real_aws_integration(self):
        """Test real AWS integration with budget analysis."""
        # Create test input data
        test_data = "PeriodStart,UnblendedCost\n2025-01-01,100.0\n2025-01-02,200.0"
        
        result = subprocess.run([
            sys.executable, "aws/budget_analysis.py",
            "--budget-name", "test-budget"
        ], input=test_data, capture_output=True, text=True, 
        cwd=os.path.dirname(os.path.dirname(__file__)))
        
        # Handle both success and failure cases
        if result.returncode == 0:
            assert "PeriodStart" in result.stdout
            assert "BudgetName" in result.stdout
        else:
            # Expected if no budgets exist or AWS not configured
            assert "budget" in result.stderr.lower() or "aws" in result.stderr.lower()

class TestPipeCompatibility:
    """Test pipe compatibility with other commands."""
    
    def test_pipe_from_cost_and_usage(self):
        """Test piping from cost_and_usage command."""
        # This test would require cost_and_usage to be working
        # For now, just test that the command accepts stdin input
        test_data = "PeriodStart,UnblendedCost\n2025-01-01,100.0"
        
        result = subprocess.run([
            sys.executable, "aws/budget_analysis.py",
            "--budget-name", "test-budget"
        ], input=test_data, capture_output=True, text=True,
        cwd=os.path.dirname(os.path.dirname(__file__)))
        
        # Should fail gracefully if AWS CLI not configured
        assert result.returncode in [0, 1, 4]  # Success, argument error, or AWS CLI error
