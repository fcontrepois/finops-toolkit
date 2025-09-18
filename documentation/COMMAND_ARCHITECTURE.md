# FinOps Toolkit - Command Architecture

## Overview

This document defines the architectural patterns and design principles for commands in the FinOps Toolkit. It establishes how commands should be structured, how they interact, and how they can be composed together to create powerful FinOps workflows.

## Architecture Principles

### 1. Command Independence
Each command in the `aws/` directory is a completely independent, self-contained tool:

- **No shared code**: Commands cannot import from other commands
- **No shared state**: Commands do not share variables, configurations, or data structures
- **Self-contained logic**: Each command includes all necessary business logic
- **Independent testing**: Each command can be tested in isolation

### 2. Pipe-Based Composition
Commands are designed to work together through Unix pipes:

- **stdin/stdout interface**: All data exchange happens through standard streams
- **CSV as lingua franca**: CSV is the primary data exchange format
- **Streaming processing**: Commands should handle data as streams when possible
- **Error propagation**: Errors should be handled gracefully in pipe chains

### 3. Single Responsibility
Each command has one well-defined purpose:

- **Focused functionality**: Each command does one thing exceptionally well
- **Clear boundaries**: Command responsibilities are well-defined and non-overlapping
- **Composable**: Commands can be combined to create complex workflows
- **Extensible**: New commands can be added without modifying existing ones

## Command Categories

### 1. Data Source Commands
Commands that fetch data from external sources (AWS APIs, files, etc.):

**Characteristics:**
- Fetch data from external sources
- Output structured data to stdout
- Handle authentication and API calls
- Provide data in standard formats

**Examples:**
- `cost_and_usage.py`: Fetches cost data from AWS Cost Explorer
- `billing_data.py`: Fetches billing data from AWS Billing
- `usage_reports.py`: Fetches usage reports from AWS

**Input:** Command-line arguments, configuration files
**Output:** CSV data to stdout

### 2. Data Processing Commands
Commands that transform, filter, or analyze data:

**Characteristics:**
- Read data from stdin or files
- Apply transformations, filters, or calculations
- Output processed data to stdout
- Handle data validation and error cases

**Examples:**
- `forecast_costs.py`: Applies forecasting algorithms to cost data
- `anomaly_detection.py`: Detects anomalies in cost patterns
- `cost_optimization.py`: Identifies cost optimization opportunities

**Input:** CSV data from stdin or files
**Output:** CSV data to stdout

### 3. Data Analysis Commands
Commands that perform complex analysis and generate insights:

**Characteristics:**
- Read processed data from stdin
- Perform statistical analysis, machine learning, or complex calculations
- Generate reports, summaries, or insights
- Output analysis results in structured formats

**Examples:**
- `trend_analysis.py`: Analyzes cost trends over time
- `budget_analysis.py`: Compares actual costs to budgets
- `efficiency_metrics.py`: Calculates efficiency and utilization metrics

**Input:** CSV data from stdin
**Output:** CSV reports or JSON insights to stdout

### 4. Output Commands
Commands that format and present data for specific use cases:

**Characteristics:**
- Read data from stdin
- Format data for specific outputs (reports, dashboards, alerts)
- Handle different output formats and destinations
- Generate human-readable or machine-readable output

**Examples:**
- `report_generator.py`: Generates formatted reports
- `alert_generator.py`: Creates alerts based on thresholds
- `dashboard_data.py`: Formats data for dashboard consumption

**Input:** CSV data from stdin
**Output:** Formatted text, HTML, JSON, or other formats to stdout

## Data Flow Patterns

### 1. Linear Pipeline
Simple sequential processing:

```bash
python aws/cost_and_usage.py --granularity daily | \
python forecast_costs.py --method sma | \
python aws/anomaly_detection.py --threshold 20
```

### 2. Parallel Processing
Multiple data streams processed in parallel:

```bash
python aws/cost_and_usage.py --granularity daily --group SERVICE | \
python forecast_costs.py --method sma > service_forecasts.csv &

python aws/cost_and_usage.py --granularity daily --group ACCOUNT | \
python forecast_costs.py --method es > account_forecasts.csv &

wait
```

### 3. Conditional Processing
Different processing based on data characteristics:

```bash
python aws/cost_and_usage.py --granularity daily | \
python aws/data_router.py --condition "cost > 1000" | \
python aws/high_cost_analysis.py
```

### 4. Aggregation and Splitting
Combine or split data streams:

```bash
# Aggregate multiple services
python aws/cost_and_usage.py --granularity daily --group SERVICE | \
python aws/aggregate_costs.py --group-by service_type

# Split by account
python aws/cost_and_usage.py --granularity daily --group ACCOUNT | \
python aws/split_by_account.py
```

## Command Interface Standards

### 1. Input Handling
All commands must support multiple input methods:

```python
def get_input_data(args) -> pd.DataFrame:
    """Get input data from file or stdin."""
    if args.input_file:
        return read_from_file(args.input_file)
    elif not sys.stdin.isatty():
        return read_from_stdin()
    else:
        handle_error("No input data provided")
```

### 2. Output Handling
All commands must output to stdout in standard formats:

```python
def write_output(data: pd.DataFrame, format_type: str) -> None:
    """Write output data to stdout."""
    if format_type == "csv":
        data.to_csv(sys.stdout, index=False)
    elif format_type == "json":
        data.to_json(sys.stdout, orient="records", indent=2)
    else:
        handle_error(f"Unsupported output format: {format_type}")
```

### 3. Error Handling
Consistent error handling across all commands:

```python
def handle_error(message: str, exit_code: int = 1) -> None:
    """Handle errors consistently."""
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(exit_code)
```

## Data Format Standards

### 1. CSV Format
Primary data exchange format:

**Requirements:**
- UTF-8 encoding
- Comma-separated values
- Header row with descriptive column names
- Consistent date formats (YYYY-MM-DD)
- Numeric precision (6 decimal places for costs)
- Empty strings for missing values (not "NaN")

**Standard Columns:**
- `PeriodStart`: Start date of the period
- `PeriodEnd`: End date of the period
- `Service`: AWS service name
- `Account`: AWS account identifier
- `Tag:KeyName`: Tag values (prefixed with "Tag:")
- `UnblendedCost`: Unblended cost amount
- `BlendedCost`: Blended cost amount
- `UsageQuantity`: Usage quantity
- `Unit`: Unit of measurement

### 2. JSON Format
For complex data structures:

**Requirements:**
- UTF-8 encoding
- Pretty-printed with 2-space indentation
- Consistent field naming (snake_case)
- ISO date formats
- Appropriate data types

**Structure:**
```json
{
  "metadata": {
    "command": "command_name",
    "version": "1.0.0",
    "timestamp": "2025-01-01T00:00:00Z",
    "parameters": {}
  },
  "data": [
    {
      "period_start": "2025-01-01",
      "service": "EC2",
      "cost": 100.50
    }
  ]
}
```

## Command Development Patterns

### 1. Command Structure Template
```python
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
Command Name: [command_name]

Purpose:
    [Detailed description of command purpose]

Input Format:
    [Description of expected input]

Output Format:
    [Description of output format]

Examples:
    [Usage examples]

Author: Frank Contrepois
License: MIT
"""

import argparse
import sys
from typing import Optional, Dict, Any
import pandas as pd

# Command-specific constants
CONSTANT_NAME = "value"

def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser."""
    # Implementation here
    pass

def read_input_data(args) -> pd.DataFrame:
    """Read input data from file or stdin."""
    # Implementation here
    pass

def validate_input_data(df: pd.DataFrame) -> None:
    """Validate input data format."""
    # Implementation here
    pass

def process_data(df: pd.DataFrame, args) -> pd.DataFrame:
    """Process the input data."""
    # Implementation here
    pass

def write_output(data: pd.DataFrame, args) -> None:
    """Write output data to stdout."""
    # Implementation here
    pass

def main() -> None:
    """Main entry point."""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Read and validate input
    df = read_input_data(args)
    validate_input_data(df)
    
    # Process data
    result_df = process_data(df, args)
    
    # Write output
    write_output(result_df, args)

if __name__ == "__main__":
    main()
```

### 2. Testing Patterns
```python
#!/usr/bin/env python3
# MIT License
# [License header...]

"""
Tests for aws/command_name.py command.

This module tests the command functionality including:
- Argument parsing and validation
- Error handling
- Output formats (CSV and JSON)
- AWS CLI integration
- Pipe compatibility
"""

import pytest
import subprocess
import sys
import os
import tempfile
import shutil
from unittest.mock import patch

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from aws.command_name import (
    handle_error,
    create_argument_parser,
    # ... other functions
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

class TestCommandLineInterface:
    """Test the command-line interface."""
    
    def test_help_output(self):
        """Test that help output is generated correctly."""
        result = subprocess.run([
            sys.executable, "aws/command_name.py", "--help"
        ], capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(__file__)))
        
        assert result.returncode == 0
        assert "Description" in result.stdout

class TestAwsCliIntegration:
    """Test AWS CLI integration (requires AWS CLI to be configured)."""
    
    @pytest.mark.skipif(
        not shutil.which("aws"),
        reason="AWS CLI not available"
    )
    def test_real_aws_integration(self):
        """Test real AWS integration with a small date range."""
        result = subprocess.run([
            sys.executable, "aws/command_name.py",
            "--granularity", "daily",
            "--start", "2024-12-01",
            "--end", "2024-12-02"
        ], capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(__file__)))
        
        # Handle both success and failure cases
        if result.returncode == 0:
            assert "PeriodStart" in result.stdout
        else:
            assert "AWS CLI" in result.stderr or "credentials" in result.stderr

class TestOutputFunctions:
    """Test output functions using temporary files."""
    
    def test_csv_output_function(self):
        """Test CSV output function using temporary file."""
        # Use temporary file to capture output
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp_file:
            # Call the function with temporary file
            output_function(data, fileobj=tmp_file)
            tmp_file.flush()
            
            # Read the file content
            with open(tmp_file.name, 'r') as f:
                output = f.read()
            
            # Clean up
            os.unlink(tmp_file.name)
        
        # Assert on the output
        assert "expected content" in output
```

## Performance Considerations

### 1. Memory Management
- Process data in chunks for large datasets
- Use generators for streaming processing
- Avoid loading entire datasets into memory
- Clean up resources properly

### 2. Processing Efficiency
- Use appropriate algorithms for data processing
- Optimize for common use cases
- Provide progress indicators for long operations
- Handle timeouts and resource limits

### 3. I/O Optimization
- Minimize file I/O operations
- Use efficient data formats
- Handle network timeouts gracefully
- Implement retry logic for external APIs

## Security Considerations

### 1. Input Validation
- Validate all input data
- Sanitize file paths and user inputs
- Check data types and ranges
- Prevent injection attacks

### 2. Credential Management
- Never hardcode credentials
- Use environment variables for sensitive data
- Follow AWS security best practices
- Document security requirements

### 3. Data Privacy
- Handle sensitive data appropriately
- Log only necessary information
- Follow data retention policies
- Implement access controls

## Monitoring and Observability

### 1. Logging
- Log important operations and errors
- Use structured logging formats
- Include relevant context in logs
- Avoid logging sensitive data

### 2. Metrics
- Track command execution times
- Monitor resource usage
- Count successful/failed operations
- Provide performance insights

### 3. Error Reporting
- Provide clear error messages
- Include relevant context in errors
- Use appropriate exit codes
- Enable debugging when needed

## Extension Points

### 1. Plugin Architecture
Commands can be extended through:

- **Custom algorithms**: New processing methods
- **Custom formats**: New input/output formats
- **Custom validators**: New data validation rules
- **Custom transformers**: New data transformations

### 2. Configuration
Commands should support:

- **Environment variables**: For configuration
- **Configuration files**: For complex settings
- **Command-line overrides**: For runtime customization
- **Default values**: For sensible defaults

### 3. Integration
Commands should integrate with:

- **External APIs**: AWS services, third-party tools
- **File systems**: Local and remote storage
- **Databases**: For persistent storage
- **Message queues**: For asynchronous processing

## Refactoring Case Study: cost_and_usage.py

### Successful Refactoring Process
The refactoring of `cost_and_usage.py` demonstrates the proper approach to updating existing commands to meet new standards:

#### 1. **High Priority Changes Applied**:
- ✅ Updated file header to new template format with MIT license
- ✅ Added `handle_error()` function and standardized all error handling
- ✅ Restructured functions to match template (created `create_argument_parser()`)
- ✅ Added comprehensive type hints to all functions
- ✅ Reorganized imports and constants following standards

#### 2. **Testing Strategy**:
- ✅ Created comprehensive test suite with 32 test cases
- ✅ Used temporary files for reliable output testing
- ✅ Implemented AWS CLI integration tests with skip conditions
- ✅ Tested all functionality manually before automation
- ✅ Achieved 100% test pass rate

#### 3. **Backward Compatibility Maintained**:
- ✅ All existing command-line arguments work unchanged
- ✅ Pipe functionality preserved and tested
- ✅ Real AWS API integration verified
- ✅ Output formats (CSV/JSON) unchanged
- ✅ Error handling improved while maintaining behavior

#### 4. **Key Lessons Learned**:
- **Temporary Files**: More reliable than stdout capture for testing output functions
- **Skip Conditions**: Essential for tests requiring external dependencies
- **Manual Testing First**: Verify functionality before implementing automated tests
- **Incremental Approach**: Apply high-priority changes first, then medium/low priority
- **Documentation Updates**: Update standards based on real-world experience

### Refactoring Checklist
When refactoring existing commands, follow this proven process:

1. **Preparation**:
   - [ ] Read and understand existing code
   - [ ] Test current functionality manually
   - [ ] Identify areas needing updates

2. **High Priority Changes**:
   - [ ] Update file header with MIT license
   - [ ] Add `handle_error()` function
   - [ ] Extract argument parser to separate function
   - [ ] Add type hints to all functions
   - [ ] Reorganize imports and constants

3. **Testing**:
   - [ ] Create comprehensive test suite
   - [ ] Test all functionality manually
   - [ ] Implement automated tests
   - [ ] Verify AWS CLI integration
   - [ ] Test pipe compatibility

4. **Documentation**:
   - [ ] Update coding standards with lessons learned
   - [ ] Document new patterns and approaches
   - [ ] Update templates with proven methods

## Best Practices

### 1. Development
- Write comprehensive tests before refactoring
- Use type hints throughout
- Follow PEP 8 style guidelines
- Document all public interfaces
- Test with real AWS APIs when possible

### 2. Testing
- Use temporary files for output testing
- Implement skip conditions for external dependencies
- Test both success and failure scenarios
- Include AWS CLI integration tests
- Verify pipe compatibility

### 3. Deployment
- Use virtual environments
- Pin dependency versions
- Provide installation instructions
- Test in target environments

### 4. Maintenance
- Keep dependencies updated
- Monitor for security vulnerabilities
- Provide migration guides
- Maintain backward compatibility
- Update documentation based on experience

This architecture document provides the foundation for building consistent, maintainable, and interoperable commands in the FinOps Toolkit. All commands should follow these patterns to ensure they work well together and provide a cohesive user experience.
