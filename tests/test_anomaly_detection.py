import subprocess
import os
import csv
import tempfile

# Updated to use the Python script instead of the shell script
def run_anomaly_detection(threshold=20, group="ALL", metric="UnblendedCost", tag_key=None, method="all", input_csv=None):
    cmd = ["python3", "aws/anomaly_detection_forecast.py", "--threshold", str(threshold), "--group", group, "--metric", metric]
    if tag_key:
        cmd += ["--tag-key", tag_key]
    if method:
        cmd += ["--method", method]
    if input_csv:
        cmd += ["--input-csv", input_csv]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout, result.stderr

def parse_summary_table(output):
    lines = output.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.strip().startswith('# Anomaly Detection Summary Table'):
            start = i + 1
            break
    if start is None:
        raise ValueError('Summary table not found in output')
    reader = csv.DictReader(lines[start:])
    return list(reader)

def test_known_anomaly():
    # Use a test CSV with a known spike for ALL group
    test_csv = os.path.join(os.path.dirname(__file__), 'input', 'daily_costs_simple.csv')
    out, err = run_anomaly_detection(threshold=5, group="ALL", input_csv=test_csv)
    summary = parse_summary_table(out)
    # Check that at least one anomaly is detected
    anomalies = [row for row in summary if row['Anomaly'] == 'Y']
    print(f"Detected {len(anomalies)} anomalies:")
    for row in anomalies:
        print(row)
    assert anomalies, "No anomalies detected when at least one was expected."

def test_no_anomaly():
    # Use a test CSV with no spike (all values the same)
    test_csv = os.path.join(os.path.dirname(__file__), 'input', 'costs_short.csv')
    out, err = run_anomaly_detection(threshold=50, group="ALL", input_csv=test_csv)
    summary = parse_summary_table(out)
    anomalies = [row for row in summary if row['Anomaly'] == 'Y']
    print(f"Detected {len(anomalies)} anomalies (should be 0):")
    for row in anomalies:
        print(row)
    assert not anomalies, "Anomalies detected when none were expected."

if __name__ == "__main__":
    test_known_anomaly()
    test_no_anomaly()
    print("All anomaly detection tests passed.") 