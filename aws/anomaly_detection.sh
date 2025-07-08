# anomaly_detection.sh
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
# Anomaly Detection Script for AWS Cost Data
#
# This script uses the finops-toolkit's cost_and_usage.py and forecast_costs.py
# to detect anomalies in AWS cost data by comparing yesterday's cost to:
#   - The day before yesterday
#   - A week earlier
#   - A month earlier
#   - A quarter earlier
# If the difference exceeds a user-defined percentage threshold, it is flagged.
#
# USAGE EXAMPLES:
#   bash anomaly_detection.sh --threshold 20
#   bash anomaly_detection.sh --threshold 10 --granularity daily --metric UnblendedCost
#
# FLAGS:
#   --threshold X      Percentage threshold for anomaly detection (required)
#   --granularity G    Granularity for cost extraction (default: daily)
#   --metric M         Metric to use (default: UnblendedCost)
#   --group G          Grouping (default: ALL)
#   --tag-key T        Tag key if grouping by TAG
#
# REQUIREMENTS:
#   - Python 3
#   - AWS CLI configured
#   - pandas, numpy (for forecast_costs.py)
#   - finops-toolkit's aws/cost_and_usage.py and aws/forecast_costs.py in PATH
# -----------------------------------------------------------------------------

set -e

# Default values
THRESHOLD=""
GRANULARITY="daily"
METRIC="UnblendedCost"
GROUP="ALL"
TAG_KEY=""

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

# Date calculations
TODAY=$(date -u +%Y-%m-%d)
YESTERDAY=$(date -u -d "yesterday" +%Y-%m-%d)
DAY_BEFORE_YESTERDAY=$(date -u -d "2 days ago" +%Y-%m-%d)
WEEK_AGO=$(date -u -d "7 days ago" +%Y-%m-%d)
MONTH_AGO=$(date -u -d "1 month ago" +%Y-%m-%d)
QUARTER_AGO=$(date -u -d "3 months ago" +%Y-%m-%d)

# Prepare cost_and_usage.py command
CMD="python3 aws/cost_and_usage.py --granularity $GRANULARITY --group $GROUP --metrics $METRIC --output-format csv"
if [[ "$GROUP" == "TAG" && -n "$TAG_KEY" ]]; then
  CMD="$CMD --tag-key $TAG_KEY"
fi

# Get costs for the relevant days
TMPFILE=$(mktemp)
$CMD --start $DAY_BEFORE_YESTERDAY --end $TODAY > "$TMPFILE"

# Helper: get value for a date
get_value() {
  local date="$1"
  awk -F, -v d="$date" 'NR>1 && $1==d {print $2}' "$TMPFILE"
}

# If grouping is ALL, the value is in column 2, else in column 3
if [[ "$GROUP" == "ALL" ]]; then
  YESTERDAY_VAL=$(awk -F, -v d="$YESTERDAY" 'NR>1 && $1==d {print $2}' "$TMPFILE")
  DAY_BEFORE_YESTERDAY_VAL=$(awk -F, -v d="$DAY_BEFORE_YESTERDAY" 'NR>1 && $1==d {print $2}' "$TMPFILE")
  WEEK_AGO_VAL=$(awk -F, -v d="$WEEK_AGO" 'NR>1 && $1==d {print $2}' "$TMPFILE")
  MONTH_AGO_VAL=$(awk -F, -v d="$MONTH_AGO" 'NR>1 && $1==d {print $2}' "$TMPFILE")
  QUARTER_AGO_VAL=$(awk -F, -v d="$QUARTER_AGO" 'NR>1 && $1==d {print $2}' "$TMPFILE")
else
  # For groupings, print all groups for each date
  YESTERDAY_VALS=$(awk -F, -v d="$YESTERDAY" 'NR>1 && $1==d {print $2","$3}' "$TMPFILE")
  DAY_BEFORE_YESTERDAY_VALS=$(awk -F, -v d="$DAY_BEFORE_YESTERDAY" 'NR>1 && $1==d {print $2","$3}' "$TMPFILE")
  WEEK_AGO_VALS=$(awk -F, -v d="$WEEK_AGO" 'NR>1 && $1==d {print $2","$3}' "$TMPFILE")
  MONTH_AGO_VALS=$(awk -F, -v d="$MONTH_AGO" 'NR>1 && $1==d {print $2","$3}' "$TMPFILE")
  QUARTER_AGO_VALS=$(awk -F, -v d="$QUARTER_AGO" 'NR>1 && $1==d {print $2","$3}' "$TMPFILE")
fi

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
echo "Anomaly Detection Report (Threshold: $THRESHOLD%)"
echo "Comparing yesterday's cost to previous periods."

if [[ "$GROUP" == "ALL" ]]; then
  # Single value comparison
  for label in "Day Before Yesterday" "Week Ago" "Month Ago" "Quarter Ago"; do
    case $label in
      "Day Before Yesterday") PREV_VAL="$DAY_BEFORE_YESTERDAY_VAL";;
      "Week Ago") PREV_VAL="$WEEK_AGO_VAL";;
      "Month Ago") PREV_VAL="$MONTH_AGO_VAL";;
      "Quarter Ago") PREV_VAL="$QUARTER_AGO_VAL";;
    esac
    DIFF=$(percent_diff "$YESTERDAY_VAL" "$PREV_VAL")
    if [[ "$DIFF" != "N/A" && ( $(echo "$DIFF > $THRESHOLD" | bc -l) || $(echo "$DIFF < -$THRESHOLD" | bc -l) ) ]]; then
      echo "ALERT: $label: Change = $DIFF% (Threshold: $THRESHOLD%)"
    else
      echo "$label: Change = $DIFF%"
    fi
  done
else
  # Grouped comparison
  for label in "Day Before Yesterday" "Week Ago" "Month Ago" "Quarter Ago"; do
    case $label in
      "Day Before Yesterday") YEST="$YESTERDAY_VALS"; PREV="$DAY_BEFORE_YESTERDAY_VALS";;
      "Week Ago") YEST="$YESTERDAY_VALS"; PREV="$WEEK_AGO_VALS";;
      "Month Ago") YEST="$YESTERDAY_VALS"; PREV="$MONTH_AGO_VALS";;
      "Quarter Ago") YEST="$YESTERDAY_VALS"; PREV="$QUARTER_AGO_VALS";;
    esac
    # Build associative arrays for group->value
    declare -A yest_map prev_map
    while IFS=, read -r group val; do
      yest_map["$group"]="$val"
    done <<< "$YEST"
    while IFS=, read -r group val; do
      prev_map["$group"]="$val"
    done <<< "$PREV"
    for group in "${!yest_map[@]}"; do
      yval="${yest_map[$group]}"
      pval="${prev_map[$group]}"
      DIFF=$(percent_diff "$yval" "$pval")
      if [[ "$DIFF" != "N/A" && ( $(echo "$DIFF > $THRESHOLD" | bc -l) || $(echo "$DIFF < -$THRESHOLD" | bc -l) ) ]]; then
        echo "ALERT: $label [$group]: Change = $DIFF% (Threshold: $THRESHOLD%)"
      else
        echo "$label [$group]: Change = $DIFF%"
      fi
    done
  done
fi

rm -f "$TMPFILE"

# End of script
