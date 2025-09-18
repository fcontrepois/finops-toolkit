# Demo Tools Documentation

This directory contains utility tools for generating synthetic data, processing forecasts, and creating visualizations for forecasting demonstrations.

## Tools Overview

| Tool | Purpose | Input | Output |
|------|---------|-------|--------|
| `generate_series.py` | Create synthetic time series | Parameters | CSV with dates and values |
| `add_spikes.py` | Add random spikes to existing data | CSV | CSV with spikes |
| `filter_forecast_horizon.py` | Extract specific forecast periods | CSV | CSV with filtered data |
| `plot_forecasts.py` | Visualize forecasts vs actuals | CSV | PNG plot |

---

## generate_series.py

Generate synthetic time series data for forecasting demonstrations.

### Usage
```bash
python demo/generate_series.py [OPTIONS] --out OUTPUT.csv
```

### Required Arguments
- `--pattern`: Time series pattern type
- `--granularity`: Data frequency (daily/monthly)
- `--out`: Output CSV file path

### Pattern Types

| Pattern | Description | Use Case |
|---------|-------------|----------|
| `flat` | Constant baseline | Testing stability |
| `upward_trend` | Linear growth | Testing trend detection |
| `downward_trend` | Linear decline | Testing decline detection |
| `seasonal` | Seasonal patterns | Testing seasonality |
| `step_change` | Sudden level change | Testing changepoint detection |
| `spike` | One-off spike | Testing outlier handling |

### Key Parameters

#### Data Configuration
- `--periods N`: Number of data points (default: 36)
- `--baseline FLOAT`: Base value (default: 100.0)
- `--noise FLOAT`: Noise level 0-1 (default: 0.05)
- `--trend FLOAT`: Per-period change (default: 1.0)

#### Date Configuration
- `--start DATE`: Start date (YYYY-MM-DD)
- `--end-date DATE`: End date (YYYY-MM-DD)
- `--date-column NAME`: Date column name (default: PeriodStart)
- `--value-column NAME`: Value column name (default: Cost)

#### Pattern-Specific Parameters
- `--season-length N`: Season length for seasonal pattern (default: 12)
- `--amplitude FLOAT`: Season amplitude for seasonal pattern (default: 20.0)
- `--step-index N`: Index of step change (0-based)
- `--step-size FLOAT`: Magnitude of step change (default: 50.0)
- `--spike-index N`: Index of spike (0-based)
- `--spike-size FLOAT`: Magnitude of spike (default: 100.0)

### Examples

#### Flat Data (No Noise)
```bash
python demo/generate_series.py \
  --pattern flat \
  --granularity daily \
  --periods 365 \
  --baseline 100 \
  --noise 0.0 \
  --out demo/input/daily_flat.csv
```

#### Growth with Seasonality
```bash
python demo/generate_series.py \
  --pattern seasonal \
  --granularity monthly \
  --periods 36 \
  --baseline 1000 \
  --trend 10 \
  --season-length 12 \
  --amplitude 200 \
  --noise 0.1 \
  --out demo/input/monthly_seasonal.csv
```

#### Step Change
```bash
python demo/generate_series.py \
  --pattern step_change \
  --granularity daily \
  --periods 100 \
  --baseline 50 \
  --step-index 50 \
  --step-size 25 \
  --noise 0.05 \
  --out demo/input/daily_step.csv
```

### Special Features

#### Theoretical Column
When `--noise 0.0`, the output includes a `theoretical` column showing the expected values that forecasting algorithms should match. This is useful for validating forecast accuracy.

#### Date Handling
- **Default**: Data ends today, starts `periods-1` time units ago
- **With --end-date**: Data ends on specified date
- **With --start**: Data starts on specified date (overrides end-date)

---

## add_spikes.py

Add random positive spikes to existing time series data.

### Usage
```bash
python demo/add_spikes.py --input INPUT.csv --output OUTPUT.csv [OPTIONS]
```

### Required Arguments
- `--input`: Input CSV file path
- `--output`: Output CSV file path

### Parameters
- `--max-pct FLOAT`: Maximum spike size as percentage (default: 0.1 = 10%)
- `--prob FLOAT`: Daily probability of spike (default: 0.05 = 5%)
- `--seed INT`: Random seed for reproducibility (default: 42)
- `--date-column NAME`: Date column name (default: PeriodStart)
- `--value-column NAME`: Value column name (default: Cost)

### Examples

#### Add 10% Spikes
```bash
python demo/add_spikes.py \
  --input demo/input/daily_flat.csv \
  --output demo/input/daily_flat_spikes.csv \
  --max-pct 0.10 \
  --prob 0.05
```

#### Add 20% Spikes with Higher Frequency
```bash
python demo/add_spikes.py \
  --input demo/input/daily_growth.csv \
  --output demo/input/daily_growth_spikes.csv \
  --max-pct 0.20 \
  --prob 0.10
```

### Algorithm
1. For each data point, generate random number
2. If random < probability, add spike
3. Spike size = random(0, max-pct) × current_value
4. Add spike to current value

---

## filter_forecast_horizon.py

Extract specific forecast periods from forecast results.

### Usage
```bash
python demo/filter_forecast_horizon.py --input INPUT.csv --output OUTPUT.csv --days N
```

### Required Arguments
- `--input`: Input forecast CSV file
- `--output`: Output filtered CSV file
- `--days N`: Number of days to extract from forecast

### Parameters
- `--date-column NAME`: Date column name (default: PeriodStart)
- `--value-column NAME`: Value column name (default: Cost)

### Examples

#### Extract Next Month
```bash
python demo/filter_forecast_horizon.py \
  --input demo/out/forecasts.csv \
  --output demo/out/next_month.csv \
  --days 30
```

#### Extract Next Quarter
```bash
python demo/filter_forecast_horizon.py \
  --input demo/out/forecasts.csv \
  --output demo/out/next_quarter.csv \
  --days 90
```

#### Extract Next Year
```bash
python demo/filter_forecast_horizon.py \
  --input demo/out/forecasts.csv \
  --output demo/out/next_year.csv \
  --days 365
```

### Algorithm
1. Find the last actual data point
2. Extract the next N days of forecast data
3. Include both actual and forecast periods
4. Preserve all forecast method columns

---

## plot_forecasts.py

Create visualizations comparing actual data with forecast results.

### Usage
```bash
python demo/plot_forecasts.py --input INPUT.csv [OPTIONS] --output PLOT.png
```

### Required Arguments
- `--input`: Input CSV file with forecasts
- `--output`: Output PNG file path

### Parameters
- `--date-column NAME`: Date column name (default: PeriodStart)
- `--value-column NAME`: Value column name (default: Cost)
- `--algos LIST`: Comma-separated list of algorithms to plot
- `--title STRING`: Plot title
- `--figsize WIDTH,HEIGHT`: Figure size in inches (default: 12,8)
- `--dpi INT`: DPI for output image (default: 100)

### Algorithm Options
Available algorithms for `--algos`:
- `sma`: Simple Moving Average
- `es`: Exponential Smoothing
- `hw`: Holt-Winters
- `arima`: ARIMA
- `sarima`: SARIMA
- `theta`: Theta method
- `prophet`: Prophet
- `neural_prophet`: NeuralProphet
- `darts`: Darts forecast
- `ensemble`: Ensemble average

### Examples

#### Basic Plot
```bash
python demo/plot_forecasts.py \
  --input demo/out/forecasts.csv \
  --output demo/out/forecast_plot.png
```

#### Custom Algorithm Selection
```bash
python demo/plot_forecasts.py \
  --input demo/out/forecasts.csv \
  --algos sma,es,hw,prophet,ensemble \
  --title "Forecast Comparison" \
  --output demo/out/comparison.png
```

#### High-Resolution Plot
```bash
python demo/plot_forecasts.py \
  --input demo/out/forecasts.csv \
  --figsize 16,10 \
  --dpi 150 \
  --output demo/out/high_res.png
```

### Visual Features
- **Actual data**: Solid line in blue
- **Forecast data**: Dashed lines in different colors
- **Legend**: Shows all plotted algorithms
- **Grid**: Light grid for easier reading
- **Automatic scaling**: Fits data range appropriately

---

## Workflow Examples

### Complete Demo Workflow
```bash
# 1. Generate flat data
python demo/generate_series.py \
  --pattern flat --granularity daily --periods 365 \
  --baseline 100 --noise 0.0 \
  --out demo/input/daily_flat.csv

# 2. Add spikes
python demo/add_spikes.py \
  --input demo/input/daily_flat.csv \
  --output demo/input/daily_flat_spikes.csv \
  --max-pct 0.10 --prob 0.05

# 3. Generate forecasts
python forecast.py \
  --input demo/input/daily_flat_spikes.csv \
  --date-column PeriodStart --value-column Cost \
  --ensemble > demo/out/forecasts.csv

# 4. Extract horizons
python demo/filter_forecast_horizon.py \
  --input demo/out/forecasts.csv \
  --output demo/out/next_month.csv --days 30

# 5. Create visualization
python demo/plot_forecasts.py \
  --input demo/out/next_month.csv \
  --algos sma,es,hw,prophet,ensemble \
  --title "Next Month Forecast" \
  --output demo/out/next_month.png
```

### Batch Processing
```bash
# Generate multiple scenarios
for pattern in flat upward_trend seasonal; do
  python demo/generate_series.py \
    --pattern $pattern --granularity daily --periods 365 \
    --out demo/input/daily_${pattern}.csv
done

# Forecast all scenarios
for pattern in flat upward_trend seasonal; do
  python forecast.py \
    --input demo/input/daily_${pattern}.csv \
    --date-column PeriodStart --value-column Cost \
    --ensemble > demo/out/daily_${pattern}_forecasts.csv
done
```

## Tips and Best Practices

### Data Generation
- Use `--noise 0.0` for clean synthetic data
- Test with different pattern types
- Vary spike parameters to test robustness

### Visualization
- Start with ensemble + key algorithms
- Use consistent color schemes
- Add descriptive titles

### Performance
- Use smaller datasets for quick testing
- Generate high-resolution plots for presentations
- Batch process multiple scenarios

### Troubleshooting
- Check CSV column names match parameters
- Verify date formats are consistent
- Ensure sufficient data for forecasting
