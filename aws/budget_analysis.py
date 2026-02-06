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
Command Name: budget_analysis

Purpose:
    Analyzes AWS budgets against actual costs and provides variance analysis.
    Compares actual costs from Cost Explorer with budget thresholds and generates
    insights on budget performance, variance percentages, and threshold breaches.

Input Format:
    CSV with columns: PeriodStart, [GroupColumn], [MetricColumn]
    - PeriodStart: Start date of the period (YYYY-MM-DD)
    - GroupColumn: Service, Account, or Tag:KeyName based on grouping
    - MetricColumn: Cost metric name (e.g., UnblendedCost)

Output Format:
    CSV with columns: PeriodStart, BudgetName, BudgetAmount, ActualCost, Variance, VariancePercent, Status
    - PeriodStart: Start date of the period
    - BudgetName: Name of the AWS budget
    - BudgetAmount: Budget threshold amount
    - ActualCost: Actual cost for the period
    - Variance: Difference between budget and actual (Budget - Actual)
    - VariancePercent: Percentage variance ((Actual - Budget) / Budget * 100)
    - Status: Budget status (UNDER_BUDGET, OVER_BUDGET, THRESHOLD_BREACH)

Error Handling:
    - Exit code 1: Invalid arguments, AWS CLI errors
    - Exit code 2: File I/O errors
    - Exit code 3: Data validation errors
    - Exit code 4: AWS CLI not configured or missing

Dependencies:
    - AWS CLI configured with appropriate permissions
    - Python 3.8+
    - pandas

Examples:
    # Basic usage with budget name
    python aws/budget_analysis.py --budget-name "Monthly-Production-Budget"
    
    # With pipe from cost_and_usage
    python aws/cost_and_usage.py --granularity daily | python aws/budget_analysis.py --budget-name "Q1-Budget"
    
    # With threshold alerts
    python aws/budget_analysis.py --budget-name "Monthly-Budget" --threshold 80 --alert-on-breach
    
    # Analyze all budgets
    python aws/budget_analysis.py --all-budgets --threshold 90

Author: Frank Contrepois
License: MIT
"""

# Standard library imports first
import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, date
from typing import Optional, Dict, Any, List, Tuple

# Third-party imports second
import pandas as pd

# Shared utilities
from common.cli_utils import handle_error, write_csv_output, write_json_output

# Command-specific constants
BUDGET_TYPES = ["COST", "USAGE", "RI_UTILIZATION", "RI_COVERAGE", "SAVINGS_PLANS_UTILIZATION", "SAVINGS_PLANS_COVERAGE"]
BUDGET_TIME_UNITS = ["DAILY", "MONTHLY", "QUARTERLY", "ANNUALLY"]
DEFAULT_THRESHOLD = 80.0

# handle_error provided by common.cli_utils

def check_aws_cli_available() -> None:
    """Check if AWS CLI is available and configured."""
    if not shutil.which("aws"):
        handle_error("AWS CLI is not installed or not in PATH.", 4)
    
    # Test AWS CLI configuration
    try:
        result = subprocess.run(
            ["aws", "sts", "get-caller-identity"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            handle_error("AWS CLI is not configured. Run 'aws configure' to set up credentials.", 4)
    except subprocess.TimeoutExpired:
        handle_error("AWS CLI command timed out. Check your network connection.", 4)
    except Exception as e:
        handle_error(f"Failed to verify AWS CLI configuration: {e}", 4)

def read_input_from_stdin() -> pd.DataFrame:
    """
    Read CSV data from stdin.
    
    Returns:
        pd.DataFrame: Parsed CSV data
        
    Raises:
        SystemExit: If stdin is empty or data is invalid
    """
    if sys.stdin.isatty():
        handle_error("No input data provided via stdin.", 1)
    
    try:
        df = pd.read_csv(sys.stdin)
        if df.empty:
            handle_error("Input data is empty.", 3)
        return df
    except Exception as e:
        handle_error(f"Failed to parse input data: {e}", 3)

def read_input_from_file(filepath: str) -> pd.DataFrame:
    """
    Read CSV data from file.
    
    Args:
        filepath: Path to the input CSV file
        
    Returns:
        pd.DataFrame: Parsed CSV data
        
    Raises:
        SystemExit: If file doesn't exist or data is invalid
    """
    if not os.path.isfile(filepath):
        handle_error(f"Input file '{filepath}' does not exist.", 2)
    
    try:
        df = pd.read_csv(filepath)
        if df.empty:
            handle_error("Input file is empty.", 3)
        return df
    except Exception as e:
        handle_error(f"Failed to read input file: {e}", 2)

def validate_required_columns(df: pd.DataFrame, required_columns: List[str]) -> None:
    """
    Validate that DataFrame contains required columns.
    
    Args:
        df: DataFrame to validate
        required_columns: List of required column names
        
    Raises:
        SystemExit: If required columns are missing
    """
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        handle_error(f"Missing required columns: {', '.join(missing_columns)}", 3)

def get_budgets_from_aws() -> List[Dict[str, Any]]:
    """
    Fetch all budgets from AWS Budgets API.
    
    Returns:
        List of budget dictionaries
        
    Raises:
        SystemExit: If AWS CLI command fails
    """
    try:
        result = subprocess.run(
            ["aws", "budgets", "describe-budgets", "--account-id", "self"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            handle_error(f"Failed to fetch budgets from AWS: {result.stderr}", 1)
        
        data = json.loads(result.stdout)
        return data.get("Budgets", [])
        
    except json.JSONDecodeError as e:
        handle_error(f"Failed to parse AWS budgets response: {e}", 1)
    except subprocess.TimeoutExpired:
        handle_error("AWS CLI command timed out while fetching budgets.", 1)
    except Exception as e:
        handle_error(f"Failed to fetch budgets: {e}", 1)

def get_budget_by_name(budget_name: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific budget by name.
    
    Args:
        budget_name: Name of the budget to fetch
        
    Returns:
        Budget dictionary or None if not found
    """
    budgets = get_budgets_from_aws()
    for budget in budgets:
        if budget.get("BudgetName") == budget_name:
            return budget
    return None

def parse_budget_amount(budget: Dict[str, Any]) -> float:
    """
    Parse budget amount from budget dictionary.
    
    Args:
        budget: Budget dictionary from AWS API
        
    Returns:
        Budget amount as float
    """
    budget_limit = budget.get("BudgetLimit", {})
    if budget_limit:
        return float(budget_limit.get("Amount", 0))
    
    # Handle cost filters for more complex budgets
    cost_filters = budget.get("CostFilters", {})
    if cost_filters:
        # For now, return 0 for complex budgets - could be enhanced
        return 0.0
    
    return 0.0

def calculate_variance(actual_cost: float, budget_amount: float) -> Tuple[float, float]:
    """
    Calculate variance between actual cost and budget.
    
    Args:
        actual_cost: Actual cost amount
        budget_amount: Budget amount
        
    Returns:
        Tuple of (variance_amount, variance_percentage)
    """
    if budget_amount == 0:
        return 0.0, 0.0
    
    variance_amount = budget_amount - actual_cost
    variance_percentage = ((actual_cost - budget_amount) / budget_amount) * 100
    
    return variance_amount, variance_percentage

def determine_budget_status(actual_cost: float, budget_amount: float, threshold: float) -> str:
    """
    Determine budget status based on actual cost and threshold.
    
    Args:
        actual_cost: Actual cost amount
        budget_amount: Budget amount
        threshold: Threshold percentage for alerts
        
    Returns:
        Budget status string
    """
    if budget_amount == 0:
        return "NO_BUDGET"
    
    percentage_used = (actual_cost / budget_amount) * 100
    
    if percentage_used >= 100:
        return "OVER_BUDGET"
    elif percentage_used >= threshold:
        return "THRESHOLD_BREACH"
    else:
        return "UNDER_BUDGET"

def process_budget_analysis(df: pd.DataFrame, budget_name: Optional[str], 
                          all_budgets: bool, threshold: float, 
                          alert_on_breach: bool) -> pd.DataFrame:
    """
    Process budget analysis on the input data.
    
    Args:
        df: Input DataFrame with cost data
        budget_name: Specific budget name to analyze
        all_budgets: Whether to analyze all budgets
        threshold: Threshold percentage for alerts
        alert_on_breach: Whether to alert on threshold breaches
        
    Returns:
        DataFrame with budget analysis results
    """
    results = []
    
    # Get budgets to analyze
    if all_budgets:
        budgets = get_budgets_from_aws()
    elif budget_name:
        budget = get_budget_by_name(budget_name)
        if not budget:
            handle_error(f"Budget '{budget_name}' not found.", 1)
        budgets = [budget]
    else:
        handle_error("Either --budget-name or --all-budgets must be specified.", 1)
    
    # Process each budget
    for budget in budgets:
        budget_name = budget.get("BudgetName", "Unknown")
        budget_amount = parse_budget_amount(budget)
        
        # Process each row in the input data
        for _, row in df.iterrows():
            period_start = row.get("PeriodStart", "")
            actual_cost = float(row.get("UnblendedCost", 0))
            
            variance_amount, variance_percentage = calculate_variance(actual_cost, budget_amount)
            status = determine_budget_status(actual_cost, budget_amount, threshold)
            
            results.append({
                "PeriodStart": period_start,
                "BudgetName": budget_name,
                "BudgetAmount": budget_amount,
                "ActualCost": actual_cost,
                "Variance": variance_amount,
                "VariancePercent": variance_percentage,
                "Status": status
            })
    
    result_df = pd.DataFrame(results)
    
    # Alert on threshold breaches if requested
    if alert_on_breach and not result_df.empty:
        breaches = result_df[result_df["Status"].isin(["THRESHOLD_BREACH", "OVER_BUDGET"])]
        if not breaches.empty:
            print(f"ALERT: {len(breaches)} budget threshold breaches detected!", file=sys.stderr)
            for _, breach in breaches.iterrows():
                print(f"  - {breach['BudgetName']}: {breach['ActualCost']:.2f} vs {breach['BudgetAmount']:.2f} "
                      f"({breach['VariancePercent']:.1f}% variance)", file=sys.stderr)
    
    return result_df

def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser for this command."""
    parser = argparse.ArgumentParser(
        description="Analyze AWS budgets against actual costs and provide variance analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Basic usage with budget name
    python aws/budget_analysis.py --budget-name "Monthly-Production-Budget"
    
    # With pipe from cost_and_usage
    python aws/cost_and_usage.py --granularity daily | python aws/budget_analysis.py --budget-name "Q1-Budget"
    
    # With threshold alerts
    python aws/budget_analysis.py --budget-name "Monthly-Budget" --threshold 80 --alert-on-breach
    
    # Analyze all budgets
    python aws/budget_analysis.py --all-budgets --threshold 90
        """
    )
    
    # Budget selection arguments
    budget_group = parser.add_mutually_exclusive_group(required=True)
    budget_group.add_argument(
        "--budget-name",
        help="Name of the specific budget to analyze"
    )
    budget_group.add_argument(
        "--all-budgets",
        action="store_true",
        help="Analyze all budgets in the account"
    )
    
    # Input arguments
    parser.add_argument(
        "--input",
        help="Input CSV file (if not provided, reads from stdin)"
    )
    
    # Analysis parameters
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help=f"Threshold percentage for budget alerts (default: {DEFAULT_THRESHOLD})"
    )
    
    parser.add_argument(
        "--alert-on-breach",
        action="store_true",
        help="Print alerts to stderr when budget thresholds are breached"
    )
    
    # Output format
    parser.add_argument(
        "--output-format",
        choices=["csv", "json"],
        default="csv",
        help="Output format: csv or json (default: csv)"
    )
    
    return parser

# write_csv_output provided by common.cli_utils

# write_json_output provided by common.cli_utils

def main() -> None:
    """Main entry point for the CLI tool."""
    parser = create_argument_parser()
    
    # Parse arguments and handle help/version first
    try:
        args = parser.parse_args()
    except SystemExit as e:
        # If argparse exits (e.g., for --help), let it handle it
        if e.code == 0:  # Help was shown successfully
            return
        else:
            # Re-raise for other argument errors
            raise
    
    # Check AWS CLI availability
    check_aws_cli_available()
    
    # Read input data
    if args.input:
        df = read_input_from_file(args.input)
    else:
        df = read_input_from_stdin()
    
    # Validate required columns
    required_columns = ["PeriodStart", "UnblendedCost"]
    validate_required_columns(df, required_columns)
    
    # Process budget analysis
    result_df = process_budget_analysis(
        df, 
        args.budget_name, 
        args.all_budgets, 
        args.threshold, 
        args.alert_on_breach
    )
    
    # Write output
    if args.output_format == "csv":
        write_csv_output(result_df)
    elif args.output_format == "json":
        # Convert DataFrame to JSON format
        json_data = {
            "metadata": {
                "command": "budget_analysis",
                "timestamp": datetime.now().isoformat(),
                "parameters": {
                    "budget_name": args.budget_name,
                    "all_budgets": args.all_budgets,
                    "threshold": args.threshold,
                    "alert_on_breach": args.alert_on_breach
                }
            },
            "data": result_df.to_dict("records")
        }
        write_json_output(json_data)

if __name__ == "__main__":
    main()
