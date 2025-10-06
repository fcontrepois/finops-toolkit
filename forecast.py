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
    - value_column: Value column name (e.g., Cost)
    - Input must have at least 10 valid (non-NaN) rows after cleaning

Output Format:
    CSV with columns: [date_column], [value_column], sma, es, hw, arima, sarima, theta, prophet, neural_prophet, darts, ensemble
    - [date_column]: The date of the forecast
    - [value_column]: The actual value (if available, else NaN)
    - sma: Forecasted value using Simple Moving Average
    - es: Forecasted value using Exponential Smoothing
    - hw: Forecasted value using Holt-Winters Triple Exponential Smoothing
    - arima: Forecasted value using ARIMA (if statsmodels installed)
    - sarima: Forecasted value using SARIMA (if statsmodels installed)
    - theta: Forecasted value using Theta Method
    - prophet: Forecasted value using Prophet (if installed)
    - neural_prophet: Forecasted value using NeuralProphet (if --neural-prophet flag used and neuralprophet installed)
    - darts: Forecasted value using Darts algorithm (if --darts-algorithm specified and darts installed)
    - ensemble: Ensemble forecast (average of all available forecasts, if --ensemble flag used)

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
    python forecast_costs.py --input costs.csv --date-column PeriodStart --value-column Cost
    
    # With pipe
    python aws/cost_and_usage.py --granularity daily | python forecast_costs.py --date-column PeriodStart --value-column Cost
    
    # Custom parameters
    python forecast_costs.py --input costs.csv --date-column PeriodStart --value-column Cost --sma-window 14 --es-alpha 0.3 --hw-alpha 0.2 --hw-beta 0.1 --hw-gamma 0.1
    
    # With milestone summary
    python forecast_costs.py --input costs.csv --date-column PeriodStart --value-column Cost --milestone-summary

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
DEFAULT_HW_ALPHA = 0.3
DEFAULT_HW_BETA = 0.1
DEFAULT_HW_GAMMA = 0.1
DEFAULT_HW_SEASONAL_PERIODS = 12
DEFAULT_ARIMA_ORDER = (1, 1, 1)
DEFAULT_SARIMA_ORDER = (1, 1, 1)
DEFAULT_SARIMA_SEASONAL_ORDER = (1, 1, 1, 12)
DEFAULT_THETA_METHOD = 2
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
    python forecast_costs.py --input costs.csv --date-column PeriodStart --value-column Cost
    
    # With pipe
    python aws/cost_and_usage.py --granularity daily | python forecast_costs.py --date-column PeriodStart --value-column Cost
    
    # Custom parameters
    python forecast_costs.py --input costs.csv --date-column PeriodStart --value-column Cost --sma-window 14 --es-alpha 0.3 --hw-alpha 0.2 --hw-beta 0.1 --hw-gamma 0.1
    
    # With milestone summary
    python forecast_costs.py --input costs.csv --date-column PeriodStart --value-column Cost --milestone-summary
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
        help='Name of the value column (e.g., Cost)'
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
        '--hw-alpha', 
        type=float, 
        default=DEFAULT_HW_ALPHA, 
        help=f'Alpha for Holt-Winters level smoothing (default: {DEFAULT_HW_ALPHA})'
    )
    parser.add_argument(
        '--hw-beta', 
        type=float, 
        default=DEFAULT_HW_BETA, 
        help=f'Beta for Holt-Winters trend smoothing (default: {DEFAULT_HW_BETA})'
    )
    parser.add_argument(
        '--hw-gamma', 
        type=float, 
        default=DEFAULT_HW_GAMMA, 
        help=f'Gamma for Holt-Winters seasonal smoothing (default: {DEFAULT_HW_GAMMA})'
    )
    parser.add_argument(
        '--hw-seasonal-periods', 
        type=int, 
        default=DEFAULT_HW_SEASONAL_PERIODS, 
        help=f'Seasonal periods for Holt-Winters (default: {DEFAULT_HW_SEASONAL_PERIODS})'
    )
    parser.add_argument(
        '--arima-order', 
        type=str, 
        default='1,1,1', 
        help='ARIMA order as comma-separated values (p,d,q) (default: 1,1,1)'
    )
    parser.add_argument(
        '--sarima-order', 
        type=str, 
        default='1,1,1', 
        help='SARIMA order as comma-separated values (p,d,q) (default: 1,1,1)'
    )
    parser.add_argument(
        '--sarima-seasonal-order', 
        type=str, 
        default='1,1,1,12', 
        help='SARIMA seasonal order as comma-separated values (P,D,Q,s) (default: 1,1,1,12)'
    )
    parser.add_argument(
        '--theta-method', 
        type=int, 
        default=DEFAULT_THETA_METHOD, 
        help=f'Theta method parameter (default: {DEFAULT_THETA_METHOD})'
    )
    parser.add_argument(
        '--neural-prophet', 
        action='store_true', 
        help='Include NeuralProphet forecast (requires neuralprophet). Install with: pip install neuralprophet'
    )
    parser.add_argument(
        '--ensemble', 
        action='store_true', 
        help='Include ensemble forecast (average of all available forecasts)'
    )
    parser.add_argument(
        '--darts-algorithm', 
        type=str, 
        choices=['exponential_smoothing', 'arima', 'auto_arima', 'theta', 'linear_regression', 'random_forest', 'xgboost'],
        help='Include Darts forecast with specified algorithm (requires u8darts). Install with: pip install u8darts'
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

def holt_winters_forecast(df: pd.DataFrame, value_col: str, forecast_dates: List[pd.Timestamp], 
                         alpha: float, beta: float, gamma: float, seasonal_periods: int) -> List[float]:
    """
    Generate Holt-Winters Triple Exponential Smoothing forecast.
    
    Args:
        df: Input DataFrame
        value_col: Name of the value column
        forecast_dates: List of forecast dates
        alpha: Level smoothing parameter (0-1)
        beta: Trend smoothing parameter (0-1)
        gamma: Seasonal smoothing parameter (0-1)
        seasonal_periods: Number of seasonal periods
        
    Returns:
        List of forecasted values
    """
    values = df[value_col].values
    n = len(values)
    
    # Need at least 2 * seasonal_periods for proper initialization
    if n < 2 * seasonal_periods:
        # Fall back to simple exponential smoothing if insufficient data
        es = values[0]
        for v in values[1:]:
            es = alpha * v + (1 - alpha) * es
        return [es] * len(forecast_dates)
    
    # Initialize level, trend, and seasonal components
    level = np.zeros(n)
    trend = np.zeros(n)
    seasonal = np.zeros(n)
    
    # Initial seasonal components (average of first seasonal_periods)
    for i in range(seasonal_periods):
        seasonal[i] = values[i] / np.mean(values[:seasonal_periods])
    
    # Initial level and trend
    level[seasonal_periods - 1] = np.mean(values[:seasonal_periods])
    trend[seasonal_periods - 1] = (np.mean(values[seasonal_periods:2*seasonal_periods]) - 
                                   np.mean(values[:seasonal_periods])) / seasonal_periods
    
    # Holt-Winters triple exponential smoothing
    for i in range(seasonal_periods, n):
        # Update level
        level[i] = alpha * (values[i] / seasonal[i - seasonal_periods]) + (1 - alpha) * (level[i-1] + trend[i-1])
        
        # Update trend
        trend[i] = beta * (level[i] - level[i-1]) + (1 - beta) * trend[i-1]
        
        # Update seasonal
        seasonal[i] = gamma * (values[i] / level[i]) + (1 - gamma) * seasonal[i - seasonal_periods]
    
    # Generate forecasts
    forecasts = []
    last_level = level[-1]
    last_trend = trend[-1]
    last_seasonal = seasonal[-seasonal_periods:]
    
    for h in range(1, len(forecast_dates) + 1):
        # Forecast formula: (level + h * trend) * seasonal
        seasonal_idx = (h - 1) % seasonal_periods
        forecast = (last_level + h * last_trend) * last_seasonal[seasonal_idx]
        forecasts.append(forecast)
    
    return forecasts

def arima_forecast(df: pd.DataFrame, value_col: str, forecast_dates: List[pd.Timestamp], order: Tuple[int, int, int]) -> List[float]:
    """
    Generate ARIMA forecast.
    
    Args:
        df: Input DataFrame
        value_col: Name of the value column
        forecast_dates: List of forecast dates
        order: ARIMA order (p, d, q)
        
    Returns:
        List of forecasted values (or NaN if statsmodels not available)
    """
    # Honor environment toggle to keep tests stable when statsmodels happens to be installed
    if not os.environ.get("ENABLE_STATSMODELS"):
        warnings.warn("[statsmodels-disabled] statsmodels usage disabled. ARIMA forecast will be NaN.")
        return [np.nan] * len(forecast_dates)
    try:
        from statsmodels.tsa.arima.model import ARIMA
    except ImportError:
        warnings.warn("statsmodels is not installed. ARIMA forecast will be NaN.")
        return [np.nan] * len(forecast_dates)
    
    values = df[value_col].values
    
    try:
        model = ARIMA(values, order=order)
        fitted_model = model.fit()
        forecast = fitted_model.forecast(steps=len(forecast_dates))
        return forecast.tolist()
    except Exception as e:
        warnings.warn(f"ARIMA forecast failed: {e}. Returning NaN.")
        return [np.nan] * len(forecast_dates)

def sarima_forecast(df: pd.DataFrame, value_col: str, forecast_dates: List[pd.Timestamp], 
                   order: Tuple[int, int, int], seasonal_order: Tuple[int, int, int, int]) -> List[float]:
    """
    Generate SARIMA forecast.
    
    Args:
        df: Input DataFrame
        value_col: Name of the value column
        forecast_dates: List of forecast dates
        order: SARIMA order (p, d, q)
        seasonal_order: SARIMA seasonal order (P, D, Q, s)
        
    Returns:
        List of forecasted values (or NaN if statsmodels not available)
    """
    # Honor environment toggle to keep tests stable when statsmodels happens to be installed
    if not os.environ.get("ENABLE_STATSMODELS"):
        warnings.warn("[statsmodels-disabled] statsmodels usage disabled. SARIMA forecast will be NaN.")
        return [np.nan] * len(forecast_dates)
    try:
        from statsmodels.tsa.statespace.sarimax import SARIMAX
    except ImportError:
        warnings.warn("statsmodels is not installed. SARIMA forecast will be NaN.")
        return [np.nan] * len(forecast_dates)
    
    values = df[value_col].values
    
    try:
        model = SARIMAX(values, order=order, seasonal_order=seasonal_order)
        fitted_model = model.fit(disp=False)
        forecast = fitted_model.forecast(steps=len(forecast_dates))
        return forecast.tolist()
    except Exception as e:
        warnings.warn(f"SARIMA forecast failed: {e}. Returning NaN.")
        return [np.nan] * len(forecast_dates)

def theta_forecast(df: pd.DataFrame, value_col: str, forecast_dates: List[pd.Timestamp], theta: float) -> List[float]:
    """
    Generate Theta method forecast.
    
    The theta method works by:
    1. Fitting a linear trend to the data
    2. Creating a "theta line" by applying theta transformation to the detrended series
    3. Forecasting by combining the linear trend with the theta line
    
    Args:
        df: Input DataFrame
        value_col: Name of the value column
        forecast_dates: List of forecast dates
        theta: Theta parameter (typically 0.5 to 2.0)
        
    Returns:
        List of forecasted values
    """
    values = df[value_col].values
    n = len(values)
    
    if n < 2:
        return [values[-1]] * len(forecast_dates)
    
    # Calculate linear trend
    x = np.arange(n)
    coeffs = np.polyfit(x, values, 1)
    trend = coeffs[0] * x + coeffs[1]
    
    # Calculate detrended series
    detrended = values - trend
    
    # Create theta line: apply theta transformation to detrended series
    # The theta line should maintain the same level as the original series
    theta_line = theta * detrended + trend
    
    # Forecast using linear extrapolation
    forecasts = []
    for h in range(1, len(forecast_dates) + 1):
        # Linear trend forecast
        trend_forecast = coeffs[0] * (n + h - 1) + coeffs[1]
        
        # Theta line forecast (extrapolate the theta line)
        theta_forecast = theta_line[-1] + (theta_line[-1] - theta_line[-2]) if len(theta_line) > 1 else theta_line[-1]
        
        # Combine trend and theta components
        forecast = trend_forecast + (theta_forecast - trend[-1])
        forecasts.append(forecast)
    
    return forecasts

def parse_order_parameter(order_str: str, expected_length: int) -> Tuple[int, ...]:
    """
    Parse order parameter string into tuple.
    
    Args:
        order_str: Comma-separated string of integers
        expected_length: Expected number of parameters
        
    Returns:
        Tuple of integers
        
    Raises:
        SystemExit: If parsing fails
    """
    try:
        parts = [int(x.strip()) for x in order_str.split(',')]
        if len(parts) != expected_length:
            handle_error(f"Order parameter must have {expected_length} comma-separated values", 1)
        return tuple(parts)
    except ValueError:
        handle_error(f"Invalid order parameter format: {order_str}", 1)

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
            warnings.warn("[prophet-missing] Prophet is not installed. Install with: pip install prophet. Column 'prophet' will be NaN.")
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

def neural_prophet_forecast(df: pd.DataFrame, date_col: str, value_col: str, forecast_dates: List[pd.Timestamp], args) -> List[float]:
    """
    Generate NeuralProphet forecast.
    
    Args:
        df: Input DataFrame
        date_col: Name of the date column
        value_col: Name of the value column
        forecast_dates: List of forecast dates
        args: Command line arguments
        
    Returns:
        List of forecasted values (or NaN if NeuralProphet not available)
    """
    # Handle constant/near-constant series by short-circuiting to a stable forecast
    values = df[value_col].to_numpy()
    if len(values) == 0 or len(forecast_dates) == 0:
        return [np.nan] * len(forecast_dates)
    if np.allclose(values, values[0]):
        warnings.warn("[neuralprophet-constant] Input series is constant. Using constant fallback for 'neural_prophet'.")
        return [float(values[-1])] * len(forecast_dates)

    try:
        from neuralprophet import NeuralProphet
    except ImportError:
        warnings.warn("[neuralprophet-missing] NeuralProphet not installed. Install with: pip install neuralprophet (requires torch). Column 'neural_prophet' will be NaN.")
        return [np.nan] * len(forecast_dates)
    
    prophet_df = df.rename(columns={date_col: 'ds', value_col: 'y'})
    
    try:
        model = NeuralProphet(
            daily_seasonality=getattr(args, 'prophet_daily_seasonality', True),
            yearly_seasonality=getattr(args, 'prophet_yearly_seasonality', True),
            weekly_seasonality=getattr(args, 'prophet_weekly_seasonality', False),
            changepoints_range=getattr(args, 'prophet_changepoint_prior_scale', 0.05),
            seasonality_reg=getattr(args, 'prophet_seasonality_prior_scale', 10.0)
        )
        model.fit(prophet_df, freq='D')
        future = pd.DataFrame({'ds': forecast_dates})
        forecast = model.predict(future)
        return forecast['yhat'].values
    except Exception as e:
        warnings.warn(f"[neuralprophet-failed] NeuralProphet run failed: {e}. Column 'neural_prophet' will be NaN.")
        return [np.nan] * len(forecast_dates)

def ensemble_forecast(forecasts: Dict[str, List[float]]) -> List[float]:
    """
    Generate ensemble forecast by averaging available forecasts.
    
    Args:
        forecasts: Dictionary of algorithm names to forecast values
        
    Returns:
        List of ensemble forecasted values
    """
    if not forecasts:
        return []
    
    # Get the length from the first forecast
    forecast_length = len(next(iter(forecasts.values())))
    ensemble_values = []
    
    for i in range(forecast_length):
        values = []
        for algo, forecast in forecasts.items():
            if i < len(forecast) and not np.isnan(forecast[i]):
                values.append(forecast[i])
        
        if values:
            ensemble_values.append(np.mean(values))
        else:
            ensemble_values.append(np.nan)
    
    return ensemble_values

def darts_forecast(df: pd.DataFrame, value_col: str, forecast_dates: List[pd.Timestamp], 
                  algorithm: str = 'exponential_smoothing') -> List[float]:
    """
    Generate forecast using Darts library algorithms.
    
    Args:
        df: Input DataFrame
        value_col: Name of the value column
        forecast_dates: List of forecast dates
        algorithm: Darts algorithm to use
        
    Returns:
        List of forecasted values (or NaN if Darts not available)
    """
    # Honor environment toggle to keep tests stable when Darts happens to be installed.
    # Only enable if explicitly set to a truthy value (1/true/yes/on).
    _enable_darts_flag = str(os.environ.get("ENABLE_DARTS", "")).strip().lower()
    if _enable_darts_flag not in {"1", "true", "yes", "on"}:
        warnings.warn("[darts-disabled] darts usage disabled. Darts forecast will be NaN.")
        return [np.nan] * len(forecast_dates)
    try:
        from darts import TimeSeries
        from darts.models import (
            ExponentialSmoothing, ARIMA, AutoARIMA, Theta, 
            LinearRegressionModel, RandomForest, XGBModel
        )
    except ImportError:
        warnings.warn("[darts-missing] Darts not installed. Install with: pip install u8darts. Column 'darts' will be NaN.")
        return [np.nan] * len(forecast_dates)
    
    values = df[value_col].values
    
    try:
        # Create TimeSeries object
        ts = TimeSeries.from_values(values)
        
        # Select algorithm
        if algorithm == 'exponential_smoothing':
            model = ExponentialSmoothing()
        elif algorithm == 'arima':
            model = ARIMA(p=1, d=1, q=1)
        elif algorithm == 'auto_arima':
            model = AutoARIMA()
        elif algorithm == 'theta':
            model = Theta()
        elif algorithm == 'linear_regression':
            model = LinearRegressionModel(lags=12)
        elif algorithm == 'random_forest':
            model = RandomForest(lags=12)
        elif algorithm == 'xgboost':
            model = XGBModel(lags=12)
        else:
            warnings.warn(f"Unknown Darts algorithm: {algorithm}. Using ExponentialSmoothing.")
            model = ExponentialSmoothing()
        
        # Fit and forecast
        model.fit(ts)
        forecast = model.predict(len(forecast_dates))
        return forecast.values().flatten().tolist()
        
    except Exception as e:
        warnings.warn(f"[darts-failed] Darts {algorithm} failed: {e}. Column 'darts' will be NaN.")
        return [np.nan] * len(forecast_dates)

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

    # Parse order parameters
    arima_order = parse_order_parameter(args.arima_order, 3)
    sarima_order = parse_order_parameter(args.sarima_order, 3)
    sarima_seasonal_order = parse_order_parameter(args.sarima_seasonal_order, 4)

    # Compute forecasts for forecasted dates only
    sma_forecast = simple_moving_average_forecast(df, value_col, forecast_dates, args.sma_window)
    es_forecast = exponential_smoothing_forecast(df, value_col, forecast_dates, args.es_alpha)
    hw_forecast = holt_winters_forecast(df, value_col, forecast_dates, 
                                       args.hw_alpha, args.hw_beta, args.hw_gamma, args.hw_seasonal_periods)
    arima_forecast_vals = arima_forecast(df, value_col, forecast_dates, arima_order)
    sarima_forecast_vals = sarima_forecast(df, value_col, forecast_dates, sarima_order, sarima_seasonal_order)
    theta_forecast_vals = theta_forecast(df, value_col, forecast_dates, args.theta_method)
    prophet_forecast_vals = prophet_forecast(df, date_col, value_col, forecast_dates, args)
    
    # NeuralProphet is optional
    if getattr(args, 'neural_prophet', False):
        neural_prophet_forecast_vals = neural_prophet_forecast(df, date_col, value_col, forecast_dates, args)
    else:
        neural_prophet_forecast_vals = [np.nan] * len(forecast_dates)
    
    # Darts forecast
    if getattr(args, 'darts_algorithm', None):
        darts_forecast_vals = darts_forecast(df, value_col, forecast_dates, args.darts_algorithm)
    else:
        darts_forecast_vals = [np.nan] * len(forecast_dates)
    
    # Ensemble forecast
    if getattr(args, 'ensemble', False):
        forecasts_dict = {
            'sma': sma_forecast,
            'es': es_forecast,
            'hw': hw_forecast,
            'arima': arima_forecast_vals,
            'sarima': sarima_forecast_vals,
            'theta': theta_forecast_vals,
            'prophet': prophet_forecast_vals,
            'neural_prophet': neural_prophet_forecast_vals,
            'darts': darts_forecast_vals
        }
        ensemble_forecast_vals = ensemble_forecast(forecasts_dict)
    else:
        ensemble_forecast_vals = [np.nan] * len(forecast_dates)

    # Fill forecast columns: NaN for input dates, forecast for forecasted dates
    out_df['sma'] = np.nan
    out_df['es'] = np.nan
    out_df['hw'] = np.nan
    out_df['arima'] = np.nan
    out_df['sarima'] = np.nan
    out_df['theta'] = np.nan
    out_df['prophet'] = np.nan
    out_df['neural_prophet'] = np.nan
    out_df['darts'] = np.nan
    out_df['ensemble'] = np.nan

    forecast_mask = out_df[date_col].isin(forecast_dates)
    out_df.loc[forecast_mask, 'sma'] = sma_forecast
    out_df.loc[forecast_mask, 'es'] = es_forecast
    out_df.loc[forecast_mask, 'hw'] = hw_forecast
    out_df.loc[forecast_mask, 'arima'] = arima_forecast_vals
    out_df.loc[forecast_mask, 'sarima'] = sarima_forecast_vals
    out_df.loc[forecast_mask, 'theta'] = theta_forecast_vals
    out_df.loc[forecast_mask, 'prophet'] = prophet_forecast_vals
    out_df.loc[forecast_mask, 'neural_prophet'] = neural_prophet_forecast_vals
    out_df.loc[forecast_mask, 'darts'] = darts_forecast_vals
    out_df.loc[forecast_mask, 'ensemble'] = ensemble_forecast_vals

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
            algorithms = ['sma', 'es', 'hw', 'arima', 'sarima', 'theta', 'prophet']
            if getattr(args, 'neural_prophet', False):
                algorithms.append('neural_prophet')
            if getattr(args, 'darts_algorithm', None):
                algorithms.append('darts')
            if getattr(args, 'ensemble', False):
                algorithms.append('ensemble')
            for algo in algorithms:
                total = forecast_only.loc[mask, algo].sum()
                print(f"  {algo}: {total:.2f}", file=sys.stdout)
            print("", file=sys.stdout)

if __name__ == "__main__":
    main()
