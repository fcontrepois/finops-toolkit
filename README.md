# FinOps Toolkit: AWS Cost and Usage (and Forecasting)

Welcome to the **FinOps Toolkit**—the only toolkit that helps you understand, predict, and perhaps even laugh at your AWS bill, all without the need for a PhD in hieroglyphics, a stiff drink, or a séance. This repository contains scripts to explore, analyse, and forecast your AWS Cost and Usage data, all from the comfort of your terminal (preferably with a cup of tea in hand).

## What Is This?

A growing collection of Python scripts that use the AWS CLI to pull cost and usage data from your AWS account, then help you slice, dice, forecast, and even detect anomalies in your cloud spend by service, account, or tag. The toolkit is designed for those who want more rigour than a homebrew spreadsheet, but more flexibility than a SaaS “solution” that thinks customisation means changing the logo.

## Features

- **Flexible granularity:** Choose between hourly, daily, or monthly data.
- **Custom intervals:** Report by day, week, month, quarter, semester, or year.
- **Group by:** Service, linked account, or tag.
- **Advanced Forecasting:** Predict your future AWS costs using multiple forecasting methods:
  - **Simple Moving Average (SMA):** Basic trend analysis with configurable window size
  - **Exponential Smoothing (ES):** Weighted average with configurable smoothing factor
  - **Holt-Winters Triple Exponential Smoothing:** Handles trend and seasonality with configurable parameters
  - **ARIMA/SARIMA:** AutoRegressive Integrated Moving Average models for complex time series
  - **Theta Method:** Linear trend combined with exponential smoothing
  - **NeuralProphet:** Neural network-based Prophet for advanced pattern recognition
  - **Darts Integration:** Multiple algorithms including Linear Regression, Random Forest, and XGBoost
  - **Ensemble Forecasting:** Combines multiple methods for improved accuracy
  - All external libraries are optional; missing dependencies gracefully return NaN with warnings
- **Milestone summary:** Use `--milestone-summary` to print a summary table of forecasted values at key milestones (end of month, next month, next quarter, following quarter, year).
- **Anomaly detection:** Automatically flag suspicious jumps in your forecasted costs.
- **Budget Analysis:** Compare actual costs against AWS budgets with variance analysis and threshold alerts.
- **Output formats:** CSV, always delivered to standard out, so you can redirect, pipe, or graph in Excel.
- **Extensible:** New scripts will be added over time.
- **No nonsense:** No web dashboards, no vendor lock-in, and absolutely no blockchain.

## Quickstart

### 1. Install Requirements

- Python 3.7+
- AWS CLI configured with permissions for Cost Explorer and Budgets
- **Core dependencies:** pandas, numpy (required for basic forecasting)
- **Optional dependencies for advanced forecasting:**
  - `prophet` - Facebook Prophet for advanced time series forecasting
  - `neuralprophet` - Neural network-based Prophet
  - `statsmodels` - For ARIMA/SARIMA models
  - `darts` - For multiple forecasting algorithms (Linear Regression, Random Forest, XGBoost)
- Your favourite terminal

**Note:** All external forecasting libraries are optional. The toolkit will gracefully handle missing dependencies by returning NaN values for those specific algorithms while continuing to work with available methods.

### 2. Explore Your Costs

```bash
python aws/cost_and_usage.py --granularity daily --interval month --group SERVICE --output-format csv
```

For more options, try:

```bash
python aws/cost_and_usage.py --help
```

Redirect CSV output to a file, or pipe it to your favourite spreadsheet tool:

```bash
python aws/cost_and_usage.py --granularity monthly --group LINKED_ACCOUNT > costs.csv
```

### 3. Forecast Future Costs

- Input must have at least 10 valid (non-NaN) rows after cleaning, or the script will warn and exit.
- Output is always CSV with multiple forecast columns, suitable for graphing in Excel.
- All forecasting algorithms run in parallel, with graceful degradation for missing dependencies.

#### Basic Forecasting

```bash
python forecast_costs.py --input costs.csv --date-column PeriodStart --value-column Cost
```

#### Advanced Forecasting with Custom Parameters

```bash
# Holt-Winters with custom parameters
python forecast_costs.py --input costs.csv --date-column PeriodStart --value-column Cost \
  --hw-alpha 0.3 --hw-beta 0.1 --hw-gamma 0.2 --hw-seasonal-periods 12

# ARIMA with custom order
python forecast_costs.py --input costs.csv --date-column PeriodStart --value-column Cost \
  --arima-order "2,1,2"

# Include NeuralProphet and Darts algorithms
python forecast_costs.py --input costs.csv --date-column PeriodStart --value-column Cost \
  --neural-prophet --darts-algorithm xgboost --ensemble
```

#### Milestone Summary Example

Print a summary table of forecasted values at key milestones:

```bash
python forecast_costs.py --input costs.csv --date-column PeriodStart --value-column Cost --milestone-summary
```

#### Pipe from cost_and_usage.py

```bash
python aws/cost_and_usage.py --granularity daily --output-format csv | python forecast_costs.py --date-column PeriodStart --value-column Cost --milestone-summary
```

#### Output Format

The forecasting script outputs CSV with multiple columns:
- **Original data columns:** Your input date and value columns
- **Forecast columns:** One column for each forecasting algorithm:
  - `sma` - Simple Moving Average
  - `es` - Exponential Smoothing  
  - `hw` - Holt-Winters Triple Exponential Smoothing
  - `arima` - ARIMA forecast
  - `sarima` - SARIMA forecast
  - `theta` - Theta Method
  - `neural_prophet` - NeuralProphet (if available)
  - `darts` - Darts algorithm (if specified)
  - `ensemble` - Ensemble average (if enabled)
- **NaN values:** Missing dependencies gracefully return NaN for unavailable algorithms

### 4. Detect Anomalies in Forecasts

Spot those cost spikes before they spot you. For example, to flag any forecast change over 20%:

```bash
bash aws/anomaly_detection_forecast.sh --threshold 20
```

Customise the detection with more options:

```bash
bash aws/anomaly_detection_forecast.sh --threshold 10 --granularity daily --metric UnblendedCost
bash aws/anomaly_detection_forecast.sh --threshold 15 --method es
bash aws/anomaly_detection_forecast.sh --threshold 10 --group SERVICE
bash aws/anomaly_detection_forecast.sh --threshold 10 --group TAG --tag-key Owner
bash aws/anomaly_detection_forecast.sh --threshold 10 --granularity daily --metric BlendedCost --group ALL --method prophet
```

### 5. Analyze Budget Performance

Compare your actual costs against AWS budgets and get variance analysis:

```bash
# Basic budget analysis
python aws/budget_analysis.py --budget-name "Monthly-Production-Budget"

# With pipe from cost_and_usage
python aws/cost_and_usage.py --granularity daily | python aws/budget_analysis.py --budget-name "Q1-Budget"

# With threshold alerts
python aws/budget_analysis.py --budget-name "Monthly-Budget" --threshold 80 --alert-on-breach

# Analyze all budgets
python aws/budget_analysis.py --all-budgets --threshold 90
```

## Arguments and Examples

### cost_and_usage.py

- `--granularity` Granularity of the data: `hourly`, `daily`, or `monthly` (required).
- `--interval` Interval to report: `day`, `week`, `month`, `quarter`, `semester`, or `year` (optional).
- `--include-today` Include today in the interval (optional).
- `--group` Group costs by `SERVICE`, `LINKED_ACCOUNT`, `TAG`, or `ALL` (default: `SERVICE`).
- `--tag-key` Tag key to group by (required if `--group TAG`).
- `--output-format` Output format: `csv` or `json` (default: `csv`).
- `--metrics` Metric to retrieve: e.g., `UnblendedCost`, `BlendedCost`, `AmortizedCost`, `NetUnblendedCost`.
- `--start`, `--end` Custom date range (YYYY-MM-DD).
- `--verbose` Print debug info.

**Examples:**

```bash
python aws/cost_and_usage.py --granularity daily --group SERVICE
python aws/cost_and_usage.py --granularity daily --interval week --group SERVICE
python aws/cost_and_usage.py --granularity daily --group TAG --tag-key Environment
python aws/cost_and_usage.py --granularity daily --output-format json
python aws/cost_and_usage.py --granularity monthly --group SERVICE --output-format csv > my-costs.csv
```

### forecast_costs.py

**Core Arguments:**
- `--input` Input CSV file (or pipe from standard input).
- `--date-column` and `--value-column` Specify the date and value columns from your cost data.
- `--milestone-summary` Print a summary table of forecasted values at key milestones.

**Basic Forecasting Parameters:**
- `--sma-window` Window size for Simple Moving Average (default: 7).
- `--es-alpha` Smoothing factor for Exponential Smoothing (default: 0.5).

**Holt-Winters Parameters:**
- `--hw-alpha` Alpha for Holt-Winters level smoothing (default: 0.3).
- `--hw-beta` Beta for Holt-Winters trend smoothing (default: 0.1).
- `--hw-gamma` Gamma for Holt-Winters seasonal smoothing (default: 0.2).
- `--hw-seasonal-periods` Seasonal periods for Holt-Winters (default: 12).

**ARIMA/SARIMA Parameters:**
- `--arima-order` ARIMA order as comma-separated values (p,d,q) (default: 1,1,1).
- `--sarima-order` SARIMA order as comma-separated values (p,d,q) (default: 1,1,1).
- `--sarima-seasonal-order` SARIMA seasonal order as comma-separated values (P,D,Q,s) (default: 1,1,1,12).

**Advanced Algorithms:**
- `--theta-method` Theta method parameter (default: 2).
- `--neural-prophet` Include NeuralProphet forecast (requires neuralprophet package).
- `--darts-algorithm` Include Darts forecast with specified algorithm (exponential_smoothing, arima, auto_arima, theta, linear_regression, random_forest, xgboost).
- `--ensemble` Include ensemble forecast (average of all available forecasts).

**Prophet Options (Legacy):**
- `--prophet-daily-seasonality`, `--prophet-yearly-seasonality`, `--prophet-weekly-seasonality`
- `--prophet-changepoint-prior-scale`, `--prophet-seasonality-prior-scale`

**Examples:**

```bash
# Basic forecasting with all algorithms
python forecast_costs.py --input costs.csv --date-column PeriodStart --value-column Cost

# Custom Holt-Winters parameters
python forecast_costs.py --input costs.csv --date-column PeriodStart --value-column Cost \
  --hw-alpha 0.4 --hw-beta 0.2 --hw-gamma 0.3 --hw-seasonal-periods 24

# ARIMA with custom order
python forecast_costs.py --input costs.csv --date-column PeriodStart --value-column Cost \
  --arima-order "2,1,2"

# Include advanced algorithms
python forecast_costs.py --input costs.csv --date-column PeriodStart --value-column Cost \
  --neural-prophet --darts-algorithm xgboost --ensemble --milestone-summary
```

### budget_analysis.py

**Core Arguments:**
- `--budget-name` Name of the specific budget to analyze (mutually exclusive with --all-budgets).
- `--all-budgets` Analyze all budgets in the account (mutually exclusive with --budget-name).
- `--input` Input CSV file (if not provided, reads from stdin).

**Analysis Parameters:**
- `--threshold` Threshold percentage for budget alerts (default: 80.0).
- `--alert-on-breach` Print alerts to stderr when budget thresholds are breached.

**Output Format:**
- `--output-format` Output format: csv or json (default: csv).

**Examples:**

```bash
# Basic budget analysis
python aws/budget_analysis.py --budget-name "Monthly-Production-Budget"

# With pipe from cost_and_usage
python aws/cost_and_usage.py --granularity daily | python aws/budget_analysis.py --budget-name "Q1-Budget"

# With threshold alerts
python aws/budget_analysis.py --budget-name "Monthly-Budget" --threshold 80 --alert-on-breach

# Analyze all budgets
python aws/budget_analysis.py --all-budgets --threshold 90

# JSON output
python aws/budget_analysis.py --budget-name "Test-Budget" --output-format json
```

## Testing

- Comprehensive test suite with 94 tests covering all commands and edge cases.
- Integration and edge-case tests use CSV files in `tests/input/`.
- Tests validate graceful degradation when external libraries are missing.
- To run the tests:

```bash
# Run all tests
PYTHONPATH=. pytest -v tests/

# Run specific command tests
PYTHONPATH=. pytest -v tests/test_forecast_costs.py
PYTHONPATH=. pytest -v tests/test_budget_analysis.py
PYTHONPATH=. pytest -v tests/test_cost_and_usage.py

# Run specific test classes
PYTHONPATH=. pytest -v tests/test_forecast_costs.py::TestHoltWintersForecast
PYTHONPATH=. pytest -v tests/test_budget_analysis.py::TestProcessBudgetAnalysis
```

## Roadmap

This toolkit is just getting started. Over time, expect a growing suite of scripts that work together—each one a finely tuned instrument in the orchestra of FinOps. The goal: make implementing FinOps more standard than rolling your own, yet more flexible than being shackled to a tool that thinks “customisation” means changing the logo.

## Troubleshooting

- **AWS CLI errors:** Check your credentials, permissions, and whether you have angered the cloud gods.
- **Missing forecasting libraries:** The toolkit gracefully handles missing dependencies. If you see NaN values for specific algorithms, install the required packages:
  - `pip install prophet` for Facebook Prophet
  - `pip install neuralprophet` for NeuralProphet
  - `pip install statsmodels` for ARIMA/SARIMA
  - `pip install darts` for Darts algorithms
- **Prophet installation issues:** Try installing with conda, and make sure `pystan` is installed too.
- **Only zeros in output:** It's either a good day, or you've filtered yourself into oblivion.
- **Test failures:** Ensure all dependencies are installed and run tests with `PYTHONPATH=. pytest -v tests/`
- For any other issues, raise an issue, consult your nearest rubber duck, or take a brisk walk.

## License

MIT License. Use, fork, and share. Just don’t blame us if your cloud bill still gives you nightmares.

## Contributing

Pull requests, witty comments, and bug reports are all welcome. If you can make cloud billing funnier, you’re hired (in spirit).

---

_Because understanding your AWS bill shouldn’t require a séance, a therapist, or a second mortgage._
