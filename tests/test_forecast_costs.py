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
Tests for aws/forecast_costs.py command.

This module tests the forecast_costs command functionality including:
- Argument parsing and validation
- Error handling
- Output formats (CSV and milestone summary)
- Input validation and data processing
- Pipe compatibility
"""

import pytest
import subprocess
import sys
import os
import tempfile
from io import StringIO
from unittest.mock import patch, MagicMock

# Add the project root to the path so we can import the command
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from aws.forecast_costs import (
    handle_error,
    create_argument_parser,
    read_input_from_file,
    read_input_from_stdin,
    validate_required_columns,
    load_data,
    infer_granularity,
    get_forecast_dates,
    get_milestone_dates,
    simple_moving_average_forecast,
    exponential_smoothing_forecast,
    holt_winters_forecast,
    prophet_forecast,
    MIN_DATA_POINTS,
    DEFAULT_SMA_WINDOW,
    DEFAULT_ES_ALPHA,
    DEFAULT_HW_ALPHA,
    DEFAULT_HW_BETA,
    DEFAULT_HW_GAMMA,
    DEFAULT_HW_SEASONAL_PERIODS
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
        # Test that date-column and value-column are required
        with pytest.raises(SystemExit):
            parser.parse_args([])
        
        # Test that required arguments work when provided
        args = parser.parse_args(["--date-column", "PeriodStart", "--value-column", "UnblendedCost"])
        assert args.date_column == "PeriodStart"
        assert args.value_column == "UnblendedCost"
    
    def test_optional_arguments_defaults(self):
        """Test that optional arguments have correct defaults."""
        parser = create_argument_parser()
        args = parser.parse_args(["--date-column", "PeriodStart", "--value-column", "UnblendedCost"])
        
        assert args.input is None
        assert args.sma_window == DEFAULT_SMA_WINDOW
        assert args.es_alpha == DEFAULT_ES_ALPHA
        assert args.hw_alpha == DEFAULT_HW_ALPHA
        assert args.hw_beta == DEFAULT_HW_BETA
        assert args.hw_gamma == DEFAULT_HW_GAMMA
        assert args.hw_seasonal_periods == DEFAULT_HW_SEASONAL_PERIODS
        assert args.prophet_daily_seasonality is True
        assert args.prophet_yearly_seasonality is True
        assert args.prophet_weekly_seasonality is False
        assert args.milestone_summary is False


class TestReadInputFromFile:
    """Test the read_input_from_file function."""
    
    def test_read_input_from_file_not_found(self, capsys):
        """Test read_input_from_file with non-existent file."""
        with pytest.raises(SystemExit) as exc_info:
            read_input_from_file("nonexistent.csv")
        
        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "Input file 'nonexistent.csv' does not exist" in captured.err
    
    def test_read_input_from_file_empty(self, capsys):
        """Test read_input_from_file with empty file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as tmp_file:
            tmp_file.write("")  # Empty file
            tmp_file.flush()
            
            with pytest.raises(SystemExit) as exc_info:
                read_input_from_file(tmp_file.name)
            
            assert exc_info.value.code == 2
            captured = capsys.readouterr()
            assert "Failed to read input file" in captured.err
            
            # Clean up
            os.unlink(tmp_file.name)


class TestReadInputFromStdin:
    """Test the read_input_from_stdin function."""
    
    def test_read_input_from_stdin_no_data(self, capsys):
        """Test read_input_from_stdin with no data."""
        with patch("sys.stdin.isatty", return_value=True):
            with pytest.raises(SystemExit) as exc_info:
                read_input_from_stdin()
            
            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "No input data provided via stdin" in captured.err
    
    def test_read_input_from_stdin_empty_data(self, capsys):
        """Test read_input_from_stdin with empty data."""
        with patch("sys.stdin.isatty", return_value=False):
            with patch("sys.stdin", StringIO("")):
                with pytest.raises(SystemExit) as exc_info:
                    read_input_from_stdin()
                
                assert exc_info.value.code == 1
                captured = capsys.readouterr()
                assert "Failed to parse input data" in captured.err


class TestValidateRequiredColumns:
    """Test the validate_required_columns function."""
    
    def test_validate_required_columns_success(self):
        """Test validate_required_columns with all required columns present."""
        import pandas as pd
        df = pd.DataFrame({
            'PeriodStart': ['2024-01-01'],
            'UnblendedCost': [100.0]
        })
        # Should not raise an exception
        validate_required_columns(df, ['PeriodStart', 'UnblendedCost'])
    
    def test_validate_required_columns_missing(self, capsys):
        """Test validate_required_columns with missing columns."""
        import pandas as pd
        df = pd.DataFrame({
            'PeriodStart': ['2024-01-01']
        })
        
        with pytest.raises(SystemExit) as exc_info:
            validate_required_columns(df, ['PeriodStart', 'UnblendedCost'])
        
        assert exc_info.value.code == 3
        captured = capsys.readouterr()
        assert "Missing required columns: UnblendedCost" in captured.err


class TestInferGranularity:
    """Test the infer_granularity function."""
    
    def test_infer_granularity_monthly(self):
        """Test infer_granularity with monthly data."""
        import pandas as pd
        df = pd.DataFrame({
            'date': pd.to_datetime(['2024-01-01', '2024-02-01', '2024-03-01'])
        })
        result = infer_granularity(df, 'date')
        assert result == 'monthly'
    
    def test_infer_granularity_daily(self):
        """Test infer_granularity with daily data."""
        import pandas as pd
        df = pd.DataFrame({
            'date': pd.to_datetime(['2024-01-01', '2024-01-02', '2024-01-03'])
        })
        result = infer_granularity(df, 'date')
        assert result == 'daily'


class TestGetForecastDates:
    """Test the get_forecast_dates function."""
    
    def test_get_forecast_dates_daily(self):
        """Test get_forecast_dates for daily granularity."""
        import pandas as pd
        last_date = pd.Timestamp('2024-01-01')
        dates = get_forecast_dates(last_date, 'daily')
        
        assert len(dates) == 365
        assert dates[0] == pd.Timestamp('2024-01-02')
        assert dates[-1] == pd.Timestamp('2024-12-31')
    
    def test_get_forecast_dates_monthly(self):
        """Test get_forecast_dates for monthly granularity."""
        import pandas as pd
        last_date = pd.Timestamp('2024-01-01')
        dates = get_forecast_dates(last_date, 'monthly')
        
        assert len(dates) == 12
        assert dates[0] == pd.Timestamp('2024-02-01')
        assert dates[-1] == pd.Timestamp('2025-01-01')


class TestSimpleMovingAverageForecast:
    """Test the simple_moving_average_forecast function."""
    
    def test_simple_moving_average_forecast(self):
        """Test simple_moving_average_forecast calculation."""
        import pandas as pd
        df = pd.DataFrame({
            'value': [10, 20, 30, 40, 50]
        })
        forecast_dates = [pd.Timestamp('2024-01-06'), pd.Timestamp('2024-01-07')]
        
        result = simple_moving_average_forecast(df, 'value', forecast_dates, 3)
        
        # Last 3 values: 30, 40, 50, average = 40
        assert len(result) == 2
        assert result[0] == 40.0
        assert result[1] == 40.0


class TestExponentialSmoothingForecast:
    """Test the exponential_smoothing_forecast function."""
    
    def test_exponential_smoothing_forecast(self):
        """Test exponential_smoothing_forecast calculation."""
        import pandas as pd
        df = pd.DataFrame({
            'value': [10, 20, 30, 40, 50]
        })
        forecast_dates = [pd.Timestamp('2024-01-06')]
        
        result = exponential_smoothing_forecast(df, 'value', forecast_dates, 0.3)
        
        # Should return a list with one value
        assert len(result) == 1
        assert isinstance(result[0], float)


class TestHoltWintersForecast:
    """Test the holt_winters_forecast function."""
    
    def test_holt_winters_forecast_sufficient_data(self):
        """Test holt_winters_forecast with sufficient data for seasonal patterns."""
        import pandas as pd
        import numpy as np
        
        # Create data with seasonal pattern (24 data points for 12 seasonal periods)
        values = [100, 110, 120, 130, 140, 150, 160, 170, 180, 190, 200, 210,
                 105, 115, 125, 135, 145, 155, 165, 175, 185, 195, 205, 215]
        df = pd.DataFrame({'value': values})
        forecast_dates = [pd.Timestamp('2024-01-25'), pd.Timestamp('2024-01-26')]
        
        result = holt_winters_forecast(df, 'value', forecast_dates, 0.3, 0.1, 0.1, 12)
        
        # Should return a list with two forecast values
        assert len(result) == 2
        assert all(isinstance(x, float) for x in result)
        assert all(not np.isnan(x) for x in result)
    
    def test_holt_winters_forecast_insufficient_data(self):
        """Test holt_winters_forecast with insufficient data falls back to ES."""
        import pandas as pd
        
        # Create data with less than 2 * seasonal_periods
        df = pd.DataFrame({'value': [10, 20, 30, 40, 50]})
        forecast_dates = [pd.Timestamp('2024-01-06')]
        
        result = holt_winters_forecast(df, 'value', forecast_dates, 0.3, 0.1, 0.1, 12)
        
        # Should return a list with one value (fallback to ES)
        assert len(result) == 1
        assert isinstance(result[0], float)
    
    def test_holt_winters_forecast_parameters(self):
        """Test holt_winters_forecast with different parameter values."""
        import pandas as pd
        import numpy as np
        
        # Create sufficient data
        values = [100, 110, 120, 130, 140, 150, 160, 170, 180, 190, 200, 210,
                 105, 115, 125, 135, 145, 155, 165, 175, 185, 195, 205, 215]
        df = pd.DataFrame({'value': values})
        forecast_dates = [pd.Timestamp('2024-01-25')]
        
        # Test with different alpha, beta, gamma values
        result1 = holt_winters_forecast(df, 'value', forecast_dates, 0.1, 0.1, 0.1, 12)
        result2 = holt_winters_forecast(df, 'value', forecast_dates, 0.9, 0.9, 0.9, 12)
        
        # Both should return valid results
        assert len(result1) == 1
        assert len(result2) == 1
        assert not np.isnan(result1[0])
        assert not np.isnan(result2[0])
        # Results should be different due to different parameters
        assert result1[0] != result2[0]
    
    def test_holt_winters_forecast_seasonal_periods(self):
        """Test holt_winters_forecast with different seasonal periods."""
        import pandas as pd
        import numpy as np
        
        # Create data for 6 seasonal periods
        values = [100, 110, 120, 130, 140, 150, 105, 115, 125, 135, 145, 155]
        df = pd.DataFrame({'value': values})
        forecast_dates = [pd.Timestamp('2024-01-13')]
        
        result = holt_winters_forecast(df, 'value', forecast_dates, 0.3, 0.1, 0.1, 6)
        
        # Should return valid result
        assert len(result) == 1
        assert not np.isnan(result[0])
        assert isinstance(result[0], float)


class TestCommandLineInterface:
    """Test the command-line interface."""
    
    def test_help_output(self):
        """Test that help output is generated correctly."""
        result = subprocess.run([
            sys.executable, "aws/forecast_costs.py", "--help"
        ], capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(__file__)))
        
        assert result.returncode == 0
        assert "Forecast AWS costs using SMA, Exponential Smoothing, and Prophet" in result.stdout
        assert "--date-column" in result.stdout
        assert "--hw-alpha" in result.stdout
        assert "--hw-beta" in result.stdout
        assert "--hw-gamma" in result.stdout
        assert "--hw-seasonal-periods" in result.stdout
        assert "Examples:" in result.stdout
    
    def test_missing_required_argument(self):
        """Test that missing required argument causes error."""
        result = subprocess.run([
            sys.executable, "aws/forecast_costs.py"
        ], capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(__file__)))
        
        assert result.returncode != 0
        assert "required" in result.stderr.lower()


class TestIntegrationTests:
    """Test integration with real data files."""
    
    def test_integration_daily_csv(self):
        """Test integration with daily CSV data."""
        test_csv = os.path.join(os.path.dirname(__file__), 'input', 'daily_costs_simple.csv')
        result = subprocess.run([
            sys.executable, 'aws/forecast_costs.py',
            '--input', test_csv,
            '--date-column', 'PeriodStart',
            '--value-column', 'UnblendedCost',
            '--milestone-summary'
        ], capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(__file__)))
        
        assert result.returncode == 0
        assert '# Forecast Milestone Summary' in result.stdout
        assert 'end_of_this_month' in result.stdout
        assert 'sma:' in result.stdout
        assert 'hw:' in result.stdout
    
    def test_integration_monthly_csv(self):
        """Test integration with monthly CSV data."""
        test_csv = os.path.join(os.path.dirname(__file__), 'input', 'monthly_costs_simple.csv')
        result = subprocess.run([
            sys.executable, 'aws/forecast_costs.py',
            '--input', test_csv,
            '--date-column', 'PeriodStart',
            '--value-column', 'UnblendedCost',
            '--milestone-summary'
        ], capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(__file__)))
        
        assert result.returncode == 0
        assert '# Forecast Milestone Summary' in result.stdout
        assert 'end_of_this_month' in result.stdout
        assert 'sma:' in result.stdout
        assert 'hw:' in result.stdout
    
    def test_integration_holt_winters_parameters(self):
        """Test integration with custom Holt-Winters parameters."""
        test_csv = os.path.join(os.path.dirname(__file__), 'input', 'daily_costs_simple.csv')
        result = subprocess.run([
            sys.executable, 'aws/forecast_costs.py',
            '--input', test_csv,
            '--date-column', 'PeriodStart',
            '--value-column', 'UnblendedCost',
            '--hw-alpha', '0.2',
            '--hw-beta', '0.1',
            '--hw-gamma', '0.1',
            '--hw-seasonal-periods', '6',
            '--milestone-summary'
        ], capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(__file__)))
        
        assert result.returncode == 0
        assert '# Forecast Milestone Summary' in result.stdout
        assert 'sma:' in result.stdout
        assert 'hw:' in result.stdout
    
    def test_integration_missing_values(self):
        """Test integration with data containing missing values."""
        test_csv = os.path.join(os.path.dirname(__file__), 'input', 'costs_with_missing.csv')
        result = subprocess.run([
            sys.executable, 'aws/forecast_costs.py',
            '--input', test_csv,
            '--date-column', 'PeriodStart',
            '--value-column', 'UnblendedCost',
            '--milestone-summary'
        ], capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(__file__)))
        
        assert result.returncode == 0
        assert '# Forecast Milestone Summary' in result.stdout
        assert 'sma:' in result.stdout
    
    def test_integration_short_input(self):
        """Test integration with short input data."""
        test_csv = os.path.join(os.path.dirname(__file__), 'input', 'costs_short.csv')
        result = subprocess.run([
            sys.executable, 'aws/forecast_costs.py',
            '--input', test_csv,
            '--date-column', 'PeriodStart',
            '--value-column', 'UnblendedCost',
            '--milestone-summary'
        ], capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(__file__)))
        
        assert result.returncode == 0
        assert '# Forecast Milestone Summary' in result.stdout
        assert 'sma:' in result.stdout
    
    def test_integration_nonmonotonic_dates(self):
        """Test integration with non-monotonic date data."""
        test_csv = os.path.join(os.path.dirname(__file__), 'input', 'costs_nonmonotonic.csv')
        result = subprocess.run([
            sys.executable, 'aws/forecast_costs.py',
            '--input', test_csv,
            '--date-column', 'PeriodStart',
            '--value-column', 'UnblendedCost',
            '--milestone-summary'
        ], capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(__file__)))
        
        assert result.returncode == 0
        assert '# Forecast Milestone Summary' in result.stdout
        assert 'sma:' in result.stdout


class TestConstants:
    """Test that constants are properly defined."""
    
    def test_min_data_points_constant(self):
        """Test MIN_DATA_POINTS constant."""
        assert isinstance(MIN_DATA_POINTS, int)
        assert MIN_DATA_POINTS == 10
    
    def test_default_sma_window_constant(self):
        """Test DEFAULT_SMA_WINDOW constant."""
        assert isinstance(DEFAULT_SMA_WINDOW, int)
        assert DEFAULT_SMA_WINDOW == 7
    
    def test_default_es_alpha_constant(self):
        """Test DEFAULT_ES_ALPHA constant."""
        assert isinstance(DEFAULT_ES_ALPHA, float)
        assert DEFAULT_ES_ALPHA == 0.5


if __name__ == "__main__":
    pytest.main([__file__])
