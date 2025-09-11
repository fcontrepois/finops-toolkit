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
Command Name: forecast_costs

Purpose:
    Forecasts AWS costs using three algorithms: Simple Moving Average (SMA),
    Exponential Smoothing (ES), and Facebook Prophet. Outputs a CSV table to stdout
    with the same granularity as the input (daily or monthly), and for each forecasted
    date, provides a column for each algorithm. The output is suitable for graphing in Excel.

Input Format:
    CSV with columns: [date_column], [value_column]
    - date_column: Date column name (e.g., PeriodStart)
    - value_column: Value column name (e.g., UnblendedCost)
    - Input must have at least 10 valid (non-NaN) rows after cleaning

Output Format:
    CSV with columns: [date_column], [value_column], sma, es, prophet
    - [date_column]: The date of the forecast
    - [value_column]: The actual value (if available, else NaN)
    - sma: Forecasted value using Simple Moving Average
    - es: Forecasted value using Exponential Smoothing
    - prophet: Forecasted value using Prophet (if installed)

Error Handling:
    - Exit code 1: Invalid arguments, data processing errors
    - Exit code 2: File I/O errors (file not found, permission denied)
    - Exit code 3: Data validation errors (insufficient data, missing columns)

Dependencies:
    - pandas
    - numpy
    - prophet (optional, for Prophet forecasting)
    - Python 3.8+

Examples:
    # Basic usage
    python aws/forecast_costs.py --input costs.csv --date-column PeriodStart --value-column UnblendedCost
    
    # With pipe
    python aws/cost_and_usage.py --granularity daily | python aws/forecast_costs.py --date-column PeriodStart --value-column UnblendedCost
    
    # Custom parameters
    python aws/forecast_costs.py --input costs.csv --date-column PeriodStart --value-column UnblendedCost --sma-window 14 --es-alpha 0.3
    
    # With milestone summary
    python aws/forecast_costs.py --input costs.csv --date-column PeriodStart --value-column UnblendedCost --milestone-summary

Author: Frank Contrepois
License: MIT
"""

# Standard library imports first
import argparse
import os
import sys
import warnings
from datetime import timedelta
from typing import Optional, Dict, Any, List, Tuple

# Third-party imports second
import numpy as np
import pandas as pd

# Command-specific constants
MIN_DATA_POINTS = 10
DEFAULT_SMA_WINDOW = 7
DEFAULT_ES_ALPHA = 0.5
DEFAULT_PROPHET_CHANGEPOINT_PRIOR_SCALE = 0.05
DEFAULT_PROPHET_SEASONALITY_PRIOR_SCALE = 10.0

def handle_error(message: str, exit_code: int = 1) -> None:
    """
    Print error message and exit with specified code.
    
    Args:
        message: Error message to display
        exit_code: Exit code to use
    """
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(exit_code)

def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser for this command."""
    parser = argparse.ArgumentParser(
        description="Forecast AWS costs using SMA, Exponential Smoothing, and Prophet. Outputs a CSV with a column for each algorithm.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Basic usage
    python aws/forecast_costs.py --input costs.csv --date-column PeriodStart --value-column UnblendedCost
    
    # With pipe
    python aws/cost_and_usage.py --granularity daily | python aws/forecast_costs.py --date-column PeriodStart --value-column UnblendedCost
    
    # Custom parameters
    python aws/forecast_costs.py --input costs.csv --date-column PeriodStart --value-column UnblendedCost --sma-window 14 --es-alpha 0.3
    
    # With milestone summary
    python aws/forecast_costs.py --input costs.csv --date-column PeriodStart --value-column UnblendedCost --milestone-summary
        """
    )
    
    # Required arguments first
    parser.add_argument(
        '--date-column', 
        required=True, 
        help='Name of the date column (e.g., PeriodStart)'
    )
    parser.add_argument(
        '--value-column', 
        required=True, 
        help='Name of the value column (e.g., UnblendedCost)'
    )
    
    # Optional arguments with defaults
    parser.add_argument(
        '--input', 
        help='Input CSV file. If omitted, reads from stdin.'
    )
    parser.add_argument(
        '--sma-window', 
        type=int, 
        default=DEFAULT_SMA_WINDOW, 
        help=f'Window size for Simple Moving Average (default: {DEFAULT_SMA_WINDOW})'
    )
    parser.add_argument(
        '--es-alpha', 
        type=float, 
        default=DEFAULT_ES_ALPHA, 
        help=f'Alpha for Exponential Smoothing (default: {DEFAULT_ES_ALPHA})'
    )
    parser.add_argument(
        '--prophet-daily-seasonality', 
        type=lambda x: x.lower() == 'true', 
        default=True, 
        help='Prophet daily seasonality (default: True)'
    )
    parser.add_argument(
        '--prophet-yearly-seasonality', 
        type=lambda x: x.lower() == 'true', 
        default=True, 
        help='Prophet yearly seasonality (default: True)'
    )
    parser.add_argument(
        '--prophet-weekly-seasonality', 
        type=lambda x: x.lower() == 'true', 
        default=False, 
        help='Prophet weekly seasonality (default: False)'
    )
    parser.add_argument(
        '--prophet-changepoint-prior-scale', 
        type=float, 
        default=DEFAULT_PROPHET_CHANGEPOINT_PRIOR_SCALE, 
        help=f'Prophet changepoint prior scale (default: {DEFAULT_PROPHET_CHANGEPOINT_PRIOR_SCALE})'
    )
    parser.add_argument(
        '--prophet-seasonality-prior-scale', 
        type=float, 
        default=DEFAULT_PROPHET_SEASONALITY_PRIOR_SCALE, 
        help=f'Prophet seasonality prior scale (default: {DEFAULT_PROPHET_SEASONALITY_PRIOR_SCALE})'
    )
    
    # Boolean flags
    parser.add_argument(
        '--milestone-summary', 
        action='store_true', 
        help='Print a summary table of total forecasted values at key milestones.'
    )
    
    return parser

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
        handle_error(f"Input file '{filepath}' does not exist or is not a file.", 2)
    
    try:
        df = pd.read_csv(filepath)
        if df.empty:
            handle_error("Input file is empty.", 2)
        return df
    except Exception as e:
        handle_error(f"Failed to read input file: {e}", 2)

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
            handle_error("Input data is empty.", 1)
        return df
    except Exception as e:
        handle_error(f"Failed to parse input data: {e}", 1)

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

def load_data(args) -> pd.DataFrame:
    """
    Load and validate input data from file or stdin.
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        pd.DataFrame: Cleaned and validated data
        
    Raises:
        SystemExit: If data validation fails
    """
    # Read data from file or stdin
    if args.input:
        df = read_input_from_file(args.input)
    else:
        df = read_input_from_stdin()
    
    # Validate required columns
    validate_required_columns(df, [args.date_column, args.value_column])
    
    # Clean and process data
    df[args.date_column] = pd.to_datetime(df[args.date_column], errors='coerce')
    df = df.sort_values(args.date_column)
    df = df[[args.date_column, args.value_column]].dropna(subset=[args.date_column, args.value_column])
    df[args.value_column] = pd.to_numeric(df[args.value_column], errors='coerce')
    df = df.dropna(subset=[args.value_column])
    
    if df.empty:
        handle_error("No valid data after filtering and cleaning.", 3)
    
    return df

def infer_granularity(df: pd.DataFrame, date_col: str) -> str:
    """
    Infer the granularity (daily or monthly) from the date column.
    
    Args:
        df: DataFrame containing the date column
        date_col: Name of the date column
        
    Returns:
        str: 'daily' or 'monthly'
    """
    # If all dates are first of month, treat as monthly, else daily
    days = df[date_col].dt.day.unique()
    if set(days) == {1}:
        return 'monthly'
    freq = pd.infer_freq(df[date_col])
    if freq and freq.startswith('M'):
        return 'monthly'
    return 'daily'

def get_forecast_dates(last_date: pd.Timestamp, granularity: str) -> List[pd.Timestamp]:
    """
    Generate forecast dates based on granularity.
    
    Args:
        last_date: Last date in the input data
        granularity: 'daily' or 'monthly'
        
    Returns:
        List of forecast dates
    """
    dates = []
    if granularity == 'monthly':
        for i in range(1, 13):
            next_month = (last_date + pd.DateOffset(months=i)).replace(day=1)
            dates.append(next_month)
    else:
        for i in range(1, 366):
            dates.append(last_date + timedelta(days=i))
    return dates

def get_milestone_dates(last_date: pd.Timestamp, granularity: str) -> Dict[str, Any]:
    """
    Return a dict of milestone labels to dates for which to sum forecasted values.
    
    Args:
        last_date: Last date in the input data
        granularity: 'daily' or 'monthly'
        
    Returns:
        Dict mapping milestone labels to dates
    """
    from pandas.tseries.offsets import MonthEnd, QuarterEnd, YearEnd
    milestones = {}
    if granularity == 'monthly':
        # End of this month, next month, next quarter, following quarter, year
        milestones['end_of_this_month'] = (last_date + MonthEnd(1)).date()
        milestones['end_of_next_month'] = (last_date + MonthEnd(2)).date()
        milestones['end_of_next_quarter'] = (last_date + QuarterEnd(1)).date()
        milestones['end_of_following_quarter'] = (last_date + QuarterEnd(2)).date()
        milestones['end_of_year'] = (last_date + YearEnd(1)).date()
    else:
        # For daily, find the last day of each period after last_date
        milestones['end_of_this_month'] = (last_date + MonthEnd(1)).date()
        milestones['end_of_next_month'] = (last_date + MonthEnd(2)).date()
        milestones['end_of_next_quarter'] = (last_date + QuarterEnd(1)).date()
        milestones['end_of_following_quarter'] = (last_date + QuarterEnd(2)).date()
        milestones['end_of_year'] = (last_date + YearEnd(1)).date()
    return milestones

def simple_moving_average_forecast(df: pd.DataFrame, value_col: str, forecast_dates: List[pd.Timestamp], window: int) -> List[float]:
    """
    Generate Simple Moving Average forecast.
    
    Args:
        df: Input DataFrame
        value_col: Name of the value column
        forecast_dates: List of forecast dates
        window: SMA window size
        
    Returns:
        List of forecasted values
    """
    last_sma = df[value_col].rolling(window=window, min_periods=1).mean().iloc[-1]
    return [last_sma] * len(forecast_dates)

def exponential_smoothing_forecast(df: pd.DataFrame, value_col: str, forecast_dates: List[pd.Timestamp], alpha: float) -> List[float]:
    """
    Generate Exponential Smoothing forecast.
    
    Args:
        df: Input DataFrame
        value_col: Name of the value column
        forecast_dates: List of forecast dates
        alpha: Smoothing parameter
        
    Returns:
        List of forecasted values
    """
    values = df[value_col].values
    es = values[0]
    for v in values[1:]:
        es = alpha * v + (1 - alpha) * es
    return [es] * len(forecast_dates)

def prophet_forecast(df: pd.DataFrame, date_col: str, value_col: str, forecast_dates: List[pd.Timestamp], args) -> List[float]:
    """
    Generate Prophet forecast.
    
    Args:
        df: Input DataFrame
        date_col: Name of the date column
        value_col: Name of the value column
        forecast_dates: List of forecast dates
        args: Command line arguments
        
    Returns:
        List of forecasted values (or NaN if Prophet not available)
    """
    try:
        from prophet import Prophet
    except ImportError:
        try:
            from fbprophet import Prophet
        except ImportError:
            warnings.warn("Prophet is not installed. Prophet forecast will be NaN.")
            return [np.nan] * len(forecast_dates)
    
    prophet_df = df.rename(columns={date_col: 'ds', value_col: 'y'})
    model = Prophet(
        daily_seasonality=args.prophet_daily_seasonality,
        yearly_seasonality=args.prophet_yearly_seasonality,
        weekly_seasonality=args.prophet_weekly_seasonality,
        changepoint_prior_scale=args.prophet_changepoint_prior_scale,
        seasonality_prior_scale=args.prophet_seasonality_prior_scale
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model.fit(prophet_df)
    future = pd.DataFrame({'ds': forecast_dates})
    forecast = model.predict(future)
    return forecast['yhat'].values

def main() -> None:
    """Main entry point for the CLI tool."""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Load and validate data
    df = load_data(args)
    if len(df) < MIN_DATA_POINTS:
        handle_error(f"Not enough data to forecast. At least {MIN_DATA_POINTS} dates are required.", 3)
    
    date_col = args.date_column
    value_col = args.value_column
    granularity = infer_granularity(df, date_col)
    last_date = df[date_col].max()
    forecast_dates = get_forecast_dates(last_date, granularity)

    # Prepare output DataFrame: all input + forecasted dates
    all_dates = list(df[date_col]) + forecast_dates
    all_dates = pd.Series(all_dates).drop_duplicates().sort_values()
    out_df = pd.DataFrame({date_col: all_dates})
    out_df = out_df.merge(df, on=date_col, how='left')

    # Compute forecasts for forecasted dates only
    sma_forecast = simple_moving_average_forecast(df, value_col, forecast_dates, args.sma_window)
    es_forecast = exponential_smoothing_forecast(df, value_col, forecast_dates, args.es_alpha)
    prophet_forecast_vals = prophet_forecast(df, date_col, value_col, forecast_dates, args)

    # Fill forecast columns: NaN for input dates, forecast for forecasted dates
    out_df['sma'] = np.nan
    out_df['es'] = np.nan
    out_df['prophet'] = np.nan

    forecast_mask = out_df[date_col].isin(forecast_dates)
    out_df.loc[forecast_mask, 'sma'] = sma_forecast
    out_df.loc[forecast_mask, 'es'] = es_forecast
    out_df.loc[forecast_mask, 'prophet'] = prophet_forecast_vals

    # Output as CSV to stdout (for Excel graphing)
    out_df.to_csv(sys.stdout, index=False)

    # If milestone summary requested, print it after the CSV
    if getattr(args, 'milestone_summary', False):
        print("\n# Forecast Milestone Summary\n", file=sys.stdout)
        milestones = get_milestone_dates(last_date, granularity)
        forecast_only = out_df[forecast_mask].copy()
        forecast_only[date_col] = pd.to_datetime(forecast_only[date_col])
        for label, mdate in milestones.items():
            # For each algorithm, sum forecasted values up to and including the milestone date
            mask = forecast_only[date_col] <= pd.Timestamp(mdate)
            print(f"{label} ({mdate}):", file=sys.stdout)
            for algo in ['sma', 'es', 'prophet']:
                total = forecast_only.loc[mask, algo].sum()
                print(f"  {algo}: {total:.2f}", file=sys.stdout)
            print("", file=sys.stdout)

if __name__ == "__main__":
    main()
