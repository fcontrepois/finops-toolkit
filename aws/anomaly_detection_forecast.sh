# anomaly_detection_forecast.sh
#
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
#
# -----------------------------------------------------------------------------
# Anomaly Detection Script for AWS Cost Forecasts
#
# This script uses finops-toolkit's cost_and_usage.py and forecast_costs.py
# to detect anomalies in forecasted AWS cost data by comparing yesterday's
# forecast to:
#   - The day before yesterday's forecast
#   - A week earlier's forecast
#   - A month earlier's forecast
#   - A quarter earlier's forecast
# If the difference exceeds a user-defined percentage threshold, it is flagged.
#
# USAGE EXAMPLES:
#
#   # 1. Basic anomaly detection with a 20% threshold
#   bash aws/anomaly_detection_forecast.sh --threshold 20
#
#   # 2. Use a 10% threshold, daily granularity, and a specific metric
#   bash aws/anomaly_detection_forecast.sh --threshold 10 --granularity daily --metric UnblendedCost
#
#   # 3. Use a different forecasting method (exponential smoothing)
#   bash aws/anomaly_detection_forecast.sh --threshold 15 --method es
#
#   # 4. Use a custom group (e.g., by SERVICE)
#   bash aws/anomaly_detection_forecast.sh --threshold 10 --group SERVICE
#
#   # 5. Use a custom tag key (when grouping by TAG)
#   bash aws/anomaly_detection_forecast.sh --threshold 10 --group TAG --tag-key Owner
#
#   # 6. Full example with all options
#   bash aws/anomaly_detection_forecast.sh --threshold 10 --granularity daily --metric BlendedCost --group ALL --method prophet
#
# REQUIREMENTS:
#   - Python 3
#   - AWS CLI configured
#   - pandas, numpy, prophet (for forecast_costs.py)
#   - finops-toolkit's aws/cost_and_usage.py and aws/forecast_costs.py in PATH
# -----------------------------------------------------------------------------

set -e

# Default values
THRESHOLD=""
GRANULARITY="daily"
METRIC="UnblendedCost"
GROUP="ALL"
TAG_KEY=""
METHOD="all"

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --threshold)
      THRESHOLD="$2"
      shift 2
      ;;
    --granularity)
      GRANULARITY="$2"
      shift 2
      ;;
    --metric)
      METRIC="$2"
      shift 2
      ;;
    --group)
      GROUP="$2"
      shift 2
      ;;
    --tag-key)
      TAG_KEY="$2"
      shift 2
      ;;
    --method)
      METHOD="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

if [[ -z "$THRESHOLD" ]]; then
  echo "Error: --threshold is required." >&2
  exit 1
fi

# Date calculations (macOS/BSD style)
TODAY=$(date -u +%Y-%m-%d)
YESTERDAY=$(date -u -v-1d +%Y-%m-%d)
DAY_BEFORE_YESTERDAY=$(date -u -v-2d +%Y-%m-%d)
WEEK_AGO=$(date -u -v-7d +%Y-%m-%d)
MONTH_AGO=$(date -u -v-1m +%Y-%m-%d)
QUARTER_AGO=$(date -u -v-3m +%Y-%m-%d)

# Prepare cost_and_usage.py command
CMD="python3 aws/cost_and_usage.py --granularity $GRANULARITY --group $GROUP --metrics $METRIC --output-format csv"
if [[ "$GROUP" == "TAG" && -n "$TAG_KEY" ]]; then
  CMD="$CMD --tag-key $TAG_KEY"
fi

# Get costs for the last 100 days (enough for all lookbacks)
START_DATE=$(date -u -v-100d +%Y-%m-%d)
TMPFILE=$(mktemp)
$CMD --start $START_DATE --end $TODAY > "$TMPFILE"

# Prepare forecast_costs.py command
FCAST_CMD="python3 aws/forecast_costs.py --date-column PeriodStart --value-column $METRIC --method $METHOD"
if [[ "$GROUP" != "ALL" ]]; then
  echo "Grouped anomaly detection for forecasts is not implemented in this script." >&2
  rm -f "$TMPFILE"
  exit 2
fi

# Helper: get forecast for a specific date
get_forecast_for_date() {
  local target_date="$1"
  awk -F, -v d="$target_date" 'NR==1 || $1<=d' "$TMPFILE" | \
    $FCAST_CMD --output-format time-table 2>/dev/null | \
    awk -F, -v d="$target_date" '$1==d && $4=="Simple Moving Average (window=7)" {print $2}' | head -1
}

# Get forecasts for each date
YESTERDAY_FCAST=$(get_forecast_for_date "$YESTERDAY")
DAY_BEFORE_YESTERDAY_FCAST=$(get_forecast_for_date "$DAY_BEFORE_YESTERDAY")
WEEK_AGO_FCAST=$(get_forecast_for_date "$WEEK_AGO")
MONTH_AGO_FCAST=$(get_forecast_for_date "$MONTH_AGO")
QUARTER_AGO_FCAST=$(get_forecast_for_date "$QUARTER_AGO")

# Function to compute percent difference
percent_diff() {
  local a="$1"
  local b="$2"
  if [[ -z "$a" || -z "$b" ]]; then
    echo "N/A"
    return
  fi
  awk -v a="$a" -v b="$b" 'BEGIN { if (b==0) print "N/A"; else print ((a-b)/b)*100 }'
}

# Output header
echo "Anomaly Detection Report (Forecast, Threshold: $THRESHOLD%)"
echo "Comparing yesterday's forecast to previous periods (SMA, window=7)."

for label in "Day Before Yesterday" "Week Ago" "Month Ago" "Quarter Ago"; do
  case $label in
    "Day Before Yesterday") PREV_VAL="$DAY_BEFORE_YESTERDAY_FCAST";;
    "Week Ago") PREV_VAL="$WEEK_AGO_FCAST";;
    "Month Ago") PREV_VAL="$MONTH_AGO_FCAST";;
    "Quarter Ago") PREV_VAL="$QUARTER_AGO_FCAST";;
  esac
  DIFF=$(percent_diff "$YESTERDAY_FCAST" "$PREV_VAL")
  if [[ "$DIFF" != "N/A" && ( $(echo "$DIFF > $THRESHOLD" | bc -l) || $(echo "$DIFF < -$THRESHOLD" | bc -l) ) ]]; then
    echo "ALERT: $label: Change = $DIFF% (Threshold: $THRESHOLD%)"
  else
    echo "$label: Change = $DIFF%"
  fi
done

rm -f "$TMPFILE"
