# FinOps Toolkit: AWS Cost and Usage (and Forecasting)

Welcome to the **FinOps Toolkit**—the only toolkit that helps you understand, predict, and perhaps even laugh at your AWS bill, all without the need for a PhD in hieroglyphics, a stiff drink, or a séance. This repository contains scripts to explore, analyse, and forecast your AWS Cost and Usage data (for now), all from the comfort of your terminal.

## What Is This?

A growing collection of Python scripts that use the AWS CLI to pull cost and usage data from your AWS account, then help you slice, dice, and even forecast your cloud spend by service, account, or tag. The toolkit is designed for those who want more rigour than a homebrew spreadsheet, but more flexibility than a SaaS “solution” that thinks customisation means changing the logo.

## Features

- **Flexible granularity:** Choose between hourly, daily, or monthly data. Sometimes you need to know exactly when your budget went up in smoke.
- **Custom intervals:** Report by day, week, month, quarter, semester, or year. Or just pick “today” if you like living dangerously.
- **Group by:** Service, linked account, or tag. Group therapy for your cloud costs.
- **Forecasting:** Predict your future AWS costs using three forecasting methods—Simple Moving Average, Exponential Smoothing, and Facebook Prophet. Peer into the financial abyss with style.
- **Output formats:** CSV or JSON, always delivered to standard out, so you can redirect, pipe, or simply stare at the numbers in awe.
- **Extensible:** New scripts will be added over time, working together to make FinOps more standardised than DIY, yet far more flexible than any boxed-in tool.
- **No nonsense:** No web dashboards, no vendor lock-in, and absolutely no blockchain.

## Quickstart

1. **Install Requirements**

   - Python 3.7+
   - AWS CLI configured with permissions for Cost Explorer
   - Prophet (for forecasting; install with `pip install prophet` or use conda)
   - Your favourite terminal

2. **Run the cost and usage script**

   ```bash
   python aws/cost-and-usage.py --granularity daily --interval month --group SERVICE --output-format csv
   ```

   For more options, try:

   ```bash
   python aws/cost-and-usage.py --help
   ```

   Redirect CSV output to a file, or pipe it to your favourite spreadsheet tool:

   ```bash
   python aws/cost-and-usage.py --granularity monthly --group LINKED_ACCOUNT > costs.csv
   ```

3. **Forecast future costs**

   ```bash
   python aws/forecast-costs.py --input costs.csv --date-column PeriodStart --value-column UnblendedCost --method all
   ```

   Or, pipe directly from cost-and-usage.py:

   ```bash
   python aws/cost-and-usage.py --granularity daily --output-format csv | python aws/forecast-costs.py --date-column PeriodStart --value-column UnblendedCost --method all
   ```

## Arguments and Examples

### cost-and-usage.py

#### `--granularity`
Granularity of the data: `hourly`, `daily`, or `monthly` (required).

```bash
python aws/cost-and-usage.py --granularity hourly --group SERVICE
```

#### `--interval`
Interval to report: `day`, `week`, `month`, `quarter`, `semester`, or `year` (optional).

```bash
python aws/cost-and-usage.py --granularity daily --interval week --group SERVICE
```

#### `--include-today`
Include today in the interval (optional).

```bash
python aws/cost-and-usage.py --granularity daily --interval week --include-today --group SERVICE
```

#### `--group`
Group costs by `SERVICE`, `LINKED_ACCOUNT`, or `TAG` (default: `SERVICE`).

```bash
python aws/cost-and-usage.py --granularity daily --group TAG --tag-key Environment
```

#### `--output-format`
Output format: `csv` or `json` (default: `csv`).

```bash
python aws/cost-and-usage.py --granularity daily --output-format json
```

### forecast-costs.py

#### `--input`
Input CSV file (or pipe from standard input).

#### `--date-column` and `--value-column`
Specify the date and value columns from your cost data.

#### Forecasting methods and parameters

- `--method` Choose from `all`, `sma`, `es`, `prophet`
- `--sma-window` Window size for Simple Moving Average (default: 7)
- `--es-alpha` Smoothing factor for Exponential Smoothing (default: 0.5)
- Prophet options:
    - `--prophet-daily-seasonality` (default: True)
    - `--prophet-yearly-seasonality` (default: True)
    - `--prophet-weekly-seasonality` (default: False)
    - `--prophet-changepoint-prior-scale` (default: 0.05)
    - `--prophet-seasonality-prior-scale` (default: 10.0)

#### Examples

```bash
# Forecast from CSV file (default parameters)
python aws/forecast-costs.py --input costs.csv --date-column PeriodStart --value-column UnblendedCost --method all

# Use a custom SMA window
python aws/forecast-costs.py --input costs.csv --date-column PeriodStart --value-column UnblendedCost --method sma --sma-window 14

# Use a custom ES alpha
python aws/forecast-costs.py --input costs.csv --date-column PeriodStart --value-column UnblendedCost --method es --es-alpha 0.3

# Use custom Prophet parameters
python aws/forecast-costs.py --input costs.csv --date-column PeriodStart --value-column UnblendedCost --method prophet --prophet-changepoint-prior-scale 0.1 --prophet-seasonality-prior-scale 5.0

# Pipe cost-and-usage.py straight into forecast-costs.py
python aws/cost-and-usage.py --granularity daily --output-format csv | python aws/forecast-costs.py --date-column PeriodStart --value-column UnblendedCost --method all --sma-window 10 --es-alpha 0.7
```

## Roadmap

This toolkit is just getting started. Over time, expect a growing suite of scripts that work together—each one a finely tuned instrument in the orchestra of FinOps. The goal: make implementing FinOps more standard than rolling your own, yet more flexible than being shackled to a tool that thinks “customisation” means changing the logo.

## Troubleshooting

- If you see errors about AWS CLI, check your credentials, permissions, and whether you have angered the cloud gods.
- If Prophet complains, try installing it with conda, and make sure `pystan` is installed too.
- If you see only zeros, it’s either a good day, or you’ve filtered yourself into oblivion.
- For any other issues, raise an issue, consult your nearest rubber duck, or take a brisk walk.

## License

MIT License. Use, fork, and share. Just don’t blame us if your cloud bill still gives you nightmares.

## Contributing

Pull requests, witty comments, and bug reports are all welcome. If you can make cloud billing funnier, you’re hired (in spirit).

---

_Because understanding your AWS bill shouldn’t require a séance, a therapist, or a second mortgage._
