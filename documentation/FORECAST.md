# forecast.py — Time Series Forecasting Tool

A comprehensive time series forecasting tool that supports multiple algorithms for financial and operational data analysis.

## Overview

`forecast.py` provides a unified interface to various forecasting methods, from simple moving averages to advanced neural networks. It's designed for FinOps use cases but works with any time series data.

## Quick Start

```bash
# Basic usage with ensemble forecasting
python forecast.py \
  --input data.csv \
  --date-column PeriodStart \
  --value-column Cost \
  --ensemble > forecasts.csv

# Enable optional models
python forecast.py \
  --input data.csv \
  --date-column PeriodStart \
  --value-column Cost \
  --neural-prophet \
  --darts-algorithm theta \
  --ensemble > forecasts.csv
```

## Pipe-first workflows (stdin/stdout)

All demo tools now support piping by default. You can chain generators, transformers, and the forecaster without intermediate files.

### Daily flat + toys seasonality → forecast
```bash
python demo/generate_series.py \
  --pattern flat --granularity daily --periods 365 --baseline 100 --noise 0.0 \
| python demo/add_seasonality.py --preset toys \
| python forecast.py --date-column PeriodStart --value-column Cost --ensemble \
> forecasts_flat_toys.csv
```

### Daily growth + holidays seasonality → forecast
```bash
python demo/generate_series.py \
  --pattern upward_trend --granularity daily --periods 365 --baseline 100 --trend 0.5 --noise 0.0 \
| python demo/add_seasonality.py --preset holidays \
| python forecast.py --date-column PeriodStart --value-column Cost --ensemble \
> forecasts_growth_holidays.csv
```

### Add spikes inline (example)
```bash
python demo/generate_series.py \
  --pattern flat --granularity daily --periods 365 --baseline 10 --noise 0.0 \
| python demo/add_spikes.py --max-pct 0.10 --prob 0.05 \
| python forecast.py --date-column PeriodStart --value-column Cost --ensemble \
> forecasts_flat_spikes_10.csv
```

Notes:
- Omit `--input/--output/--out` to use stdin/stdout; specify them only when you want files.
- `aws/cost_and_usage.py` and `aws/budget_analysis.py` already print to stdout and accept stdin as documented below.

## Input Requirements

- **CSV format** with date and value columns
- **Date column**: Must be parseable by pandas (YYYY-MM-DD, etc.)
- **Value column**: Numeric values to forecast
- **No missing values** in the value column

## Core Algorithms

### Built-in Methods

| Method | Description | Best For |
|--------|-------------|----------|
| **SMA** | Simple Moving Average | Stable, slow-reacting baseline |
| **ES** | Exponential Smoothing | Quick adaptation to recent changes |
| **Holt-Winters** | Triple Exponential Smoothing | Trends and seasonality |
| **ARIMA** | AutoRegressive Integrated Moving Average | Short-term autocorrelation |
| **SARIMA** | Seasonal ARIMA | Seasonal patterns |
| **Theta** | Theta method | Strong baseline on simple series |
| **Prophet** | Facebook Prophet | Trend changes and seasonality |
| **Ensemble** | Average of available models | Reduced variance, robust baseline |

### Optional Methods

| Method | Flag | Requirements | Description |
|--------|------|--------------|-------------|
| **NeuralProphet** | `--neural-prophet` | `pip install neuralprophet` | Neural network version of Prophet |
| **Darts** | `--darts-algorithm <algo>` | `pip install u8darts` | Various algorithms (theta, ARIMA, etc.) |

## Command Line Options

### Required Arguments
- `--input`: Input CSV file path
- `--date-column`: Name of the date column
- `--value-column`: Name of the value column

### Model Selection
- `--ensemble`: Include ensemble forecast (recommended)
- `--neural-prophet`: Include NeuralProphet forecast
- `--darts-algorithm <algo>`: Include Darts forecast with specified algorithm

### Algorithm Tuning

#### Simple Moving Average
- `--sma-window N`: Window size for SMA (default: 7)

#### Exponential Smoothing
- `--es-alpha FLOAT`: Smoothing parameter (0-1, default: 0.3)

#### Holt-Winters
- `--hw-alpha FLOAT`: Level smoothing (0-1, default: 0.3)
- `--hw-beta FLOAT`: Trend smoothing (0-1, default: 0.1)
- `--hw-gamma FLOAT`: Seasonality smoothing (0-1, default: 0.1)

#### Prophet
- `--prophet-weekly-seasonality`: Enable weekly seasonality (default: auto)
- `--prophet-daily-seasonality`: Enable daily seasonality (default: auto)

#### ARIMA/SARIMA
- `--arima-order "p,d,q"`: ARIMA order (default: auto)
- `--sarima-order "p,d,q,P,D,Q,s"`: SARIMA order (default: auto)

### Output Options
- `--output`: Output CSV file path (default: stdout)
- `--forecast-periods N`: Number of periods to forecast (default: 30)

## Installation

### Core Dependencies
```bash
pip install pandas numpy prophet matplotlib
```

### Optional Dependencies
```bash
# For ARIMA/SARIMA
pip install statsmodels pmdarima

# For Darts
pip install u8darts

# For NeuralProphet
pip install neuralprophet
```

## Usage Examples

### Basic Forecasting
```bash
python forecast.py \
  --input monthly_costs.csv \
  --date-column Date \
  --value-column Amount \
  --ensemble
```

### Advanced Configuration
```bash
python forecast.py \
  --input daily_usage.csv \
  --date-column PeriodStart \
  --value-column Cost \
  --sma-window 14 \
  --es-alpha 0.2 \
  --hw-alpha 0.4 \
  --hw-beta 0.2 \
  --prophet-weekly-seasonality true \
  --neural-prophet \
  --darts-algorithm auto_arima \
  --ensemble \
  --forecast-periods 90
```

### Darts Algorithm Options
Available algorithms for `--darts-algorithm`:
- `exponential_smoothing`: Exponential smoothing
- `arima`: ARIMA model
- `auto_arima`: Automatic ARIMA selection
- `theta`: Theta method
- `linear_regression`: Linear regression
- `random_forest`: Random forest
- `xgboost`: XGBoost

## Output Format

The output CSV contains:
- Original date and value columns
- One column per forecasting method
- Forecasted values for the specified number of periods

### Column Naming
- `sma`: Simple Moving Average
- `es`: Exponential Smoothing
- `hw`: Holt-Winters
- `arima`: ARIMA
- `sarima`: SARIMA
- `theta`: Theta method
- `prophet`: Prophet
- `neural_prophet`: NeuralProphet (if enabled)
- `darts`: Darts forecast (if enabled)
- `ensemble`: Ensemble average

## Error Handling

### Missing Dependencies
When optional libraries are missing, the tool will:
- Print a tagged warning (e.g., `[neuralprophet-missing]`)
- Set the corresponding column to NaN
- Continue with available methods

### Model Failures
- Constant series: NeuralProphet falls back to constant forecast
- Insufficient data: Methods return NaN for that column
- Training failures: Clear error messages with suggestions

## Best Practices

### Data Preparation
1. **Clean data**: Remove outliers and handle missing values
2. **Consistent frequency**: Ensure regular time intervals
3. **Sufficient history**: At least 30-50 data points for reliable forecasts

### Model Selection
1. **Start simple**: Use ensemble for baseline
2. **Add complexity**: Enable NeuralProphet for flexible trends
3. **Validate**: Compare multiple methods on historical data

### Parameter Tuning
1. **SMA window**: Larger for stability, smaller for responsiveness
2. **ES alpha**: Higher for recent data emphasis
3. **Holt-Winters**: Adjust based on trend/seasonality strength

## Troubleshooting

### Common Issues

**Empty columns in output:**
- Check if optional dependencies are installed
- Look for warning messages in stderr
- Verify data has sufficient variation

**Poor forecast quality:**
- Try different algorithms
- Adjust smoothing parameters
- Check for data quality issues

**Memory issues with large datasets:**
- Reduce forecast periods
- Use simpler models
- Consider data sampling

### Debug Mode
Add `--verbose` flag for detailed logging of model training and parameter selection.

## Integration

### With Other Tools
- Use with `generate_series.py` for synthetic data testing
- Combine with `plot_forecasts.py` for visualization
- Filter results with `filter_forecast_horizon.py`

### Programmatic Usage
```python
from forecast import forecast_time_series

result = forecast_time_series(
    df=your_dataframe,
    date_col='Date',
    value_col='Value',
    methods=['sma', 'es', 'ensemble'],
    forecast_periods=30
)
```
