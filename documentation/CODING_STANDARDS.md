# FinOps Toolkit - Coding Standards

## Overview

This document establishes the coding standards and architectural principles for the FinOps Toolkit. All commands in the `aws/` directory must follow these standards to ensure consistency, maintainability, and interoperability.

## Core Principles

### 1. Unix Philosophy
- **Do one thing well**: Each command has a single, well-defined purpose
- **Compose with pipes**: Commands must work together via stdin/stdout
- **Text-based interfaces**: All data exchange happens through structured text formats
- **Fail fast**: Commands should exit with appropriate error codes on failure

### 2. Independence
- **No shared code**: Each command is completely independent
- **No imports between commands**: Commands cannot import from other commands in the toolkit
- **Self-contained**: Each command includes all necessary dependencies and logic
- **Standard library first**: Prefer Python standard library over external dependencies

### 3. Interoperability
- **Consistent I/O**: All commands follow the same input/output patterns
- **Structured data**: Use CSV as the primary data exchange format
- **Error handling**: Consistent error reporting and exit codes
- **Documentation**: Comprehensive inline and external documentation

## File Structure Standards

### Command File Naming
- Use snake_case: `command_name.py`
- Be descriptive and specific: `cost_and_usage.py`, `anomaly_detection.py`
- Avoid generic names: `utils.py`, `helpers.py`, `common.py`

### File Header Template
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
Command Name: [Brief description of what the command does]

Purpose:
    [Detailed explanation of the command's purpose and use cases]

Input Format:
    [Description of expected input format when reading from stdin]

Output Format:
    [Description of output format written to stdout]

Error Handling:
    [Description of error conditions and exit codes]

Dependencies:
    [List of required Python packages and system tools]

Examples:
    [Command-line examples showing usage patterns]

Author: Frank Contrepois
License: MIT
"""

# Standard library imports first
import argparse
import sys
import csv
from datetime import datetime
from typing import Optional, Dict, Any

# Third-party imports second
import pandas as pd

# Command-specific constants
CONSTANT_NAME = "value"
```

## Command-Line Interface Standards

### Argument Parser Structure
```python
def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser for this command."""
    parser = argparse.ArgumentParser(
        description="[One-line description of what the command does]",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Basic usage
    python aws/command_name.py --required-arg value
    
    # With pipe
    python aws/other_command.py | python aws/command_name.py --input-format csv
    
    # Error handling
    python aws/command_name.py --invalid-arg  # Should exit with code 1
        """
    )
    
    # Required arguments first
    parser.add_argument(
        "--required-arg",
        required=True,
        help="Description of required argument"
    )
    
    # Optional arguments with defaults
    parser.add_argument(
        "--optional-arg",
        default="default_value",
        help="Description of optional argument"
    )
    
    # Boolean flags
    parser.add_argument(
        "--flag",
        action="store_true",
        help="Description of boolean flag"
    )
    
    # Choices for validation
    parser.add_argument(
        "--choice",
        choices=["option1", "option2", "option3"],
        default="option1",
        help="Description of choice argument"
    )
    
    return parser
```

### Input Handling Standards

#### Reading from stdin (when piped)
```python
def read_input_from_stdin() -> pd.DataFrame:
    """
    Read CSV data from stdin.
    
    Returns:
        pd.DataFrame: Parsed CSV data
        
    Raises:
        SystemExit: If stdin is empty or data is invalid
    """
    if sys.stdin.isatty():
        print("Error: No input data provided via stdin.", file=sys.stderr)
        sys.exit(1)
    
    try:
        df = pd.read_csv(sys.stdin)
        if df.empty:
            print("Error: Input data is empty.", file=sys.stderr)
            sys.exit(1)
        return df
    except Exception as e:
        print(f"Error: Failed to parse input data: {e}", file=sys.stderr)
        sys.exit(1)
```

#### Reading from file
```python
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
        print(f"Error: Input file '{filepath}' does not exist.", file=sys.stderr)
        sys.exit(1)
    
    try:
        df = pd.read_csv(filepath)
        if df.empty:
            print("Error: Input file is empty.", file=sys.stderr)
            sys.exit(1)
        return df
    except Exception as e:
        print(f"Error: Failed to read input file: {e}", file=sys.stderr)
        sys.exit(1)
```

### Output Handling Standards

#### Writing CSV to stdout
```python
def write_csv_output(df: pd.DataFrame, include_header: bool = True) -> None:
    """
    Write DataFrame as CSV to stdout.
    
    Args:
        df: DataFrame to write
        include_header: Whether to include column headers
    """
    df.to_csv(sys.stdout, index=False, header=include_header)
```

#### Writing JSON to stdout
```python
def write_json_output(data: Dict[str, Any], indent: int = 2) -> None:
    """
    Write data as JSON to stdout.
    
    Args:
        data: Data to serialize as JSON
        indent: JSON indentation level
    """
    json.dump(data, sys.stdout, indent=indent)
    sys.stdout.write("\n")
```

## Data Format Standards

### CSV Format Requirements
- **Headers**: Always include descriptive column headers
- **Date format**: Use ISO format (YYYY-MM-DD) for dates
- **Numeric precision**: Use 6 decimal places for monetary values
- **Missing values**: Use empty strings, not "NaN" or "null"
- **Encoding**: UTF-8

### Standard Column Names
- `PeriodStart`: Start date of the period (ISO format)
- `PeriodEnd`: End date of the period (ISO format)
- `Service`: AWS service name
- `Account`: AWS account ID or name
- `Tag:KeyName`: Tag values (prefix with "Tag:")
- `UnblendedCost`: Unblended cost amount
- `BlendedCost`: Blended cost amount
- `UsageQuantity`: Usage quantity
- `Unit`: Unit of measurement

### JSON Format Requirements
- **Structure**: Use consistent nested structure
- **Dates**: ISO format strings
- **Numbers**: Use appropriate numeric types
- **Arrays**: Use arrays for multiple values
- **Objects**: Use objects for grouped data

## Error Handling Standards

### Exit Codes
- `0`: Success
- `1`: General error (invalid arguments, data processing errors)
- `2`: File I/O errors (file not found, permission denied)
- `3`: Data validation errors (invalid format, missing required columns)
- `4`: External dependency errors (AWS CLI not configured, missing tools)

### Error Message Format
```python
def handle_error(message: str, exit_code: int = 1) -> None:
    """
    Print error message and exit with specified code.
    
    Args:
        message: Error message to display
        exit_code: Exit code to use
    """
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(exit_code)
```

### Validation Functions
```python
def validate_required_columns(df: pd.DataFrame, required_columns: list) -> None:
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
```

## Testing Standards

### Test File Structure
- Test files go in `tests/` directory
- Name test files: `test_command_name.py`
- Use pytest framework
- Include both unit tests and integration tests
- Include MIT license header in test files

### Test Organization
- Group tests by functionality using test classes
- Use descriptive test class names: `TestHandleError`, `TestParseMetric`, etc.
- Use descriptive test method names: `test_handle_error_default_exit_code`
- Include comprehensive docstrings for each test

### Test Coverage Requirements
- **Unit Tests**: Test all individual functions
- **Integration Tests**: Test command-line interface and AWS CLI integration
- **Error Handling**: Test all error conditions and exit codes
- **Input Validation**: Test argument parsing and validation
- **Output Formats**: Test CSV and JSON output generation
- **Pipe Compatibility**: Test Unix pipe functionality
- **Edge Cases**: Test boundary conditions and error scenarios

### Testing Techniques
- **Temporary Files**: Use `tempfile.NamedTemporaryFile()` for testing output functions
- **Subprocess Testing**: Use `subprocess.run()` for CLI integration tests
- **Skip Conditions**: Use `@pytest.mark.skipif()` for tests requiring external dependencies
- **Mocking**: Use `unittest.mock` for external service dependencies
- **Fixtures**: Use pytest fixtures for common test setup

### Test Data Management
- Place test input files in `tests/input/`
- Use descriptive names: `daily_costs_simple.csv`, `monthly_costs_with_missing.csv`
- Include edge cases: empty files, malformed data, missing values
- Clean up temporary files in tests

### Example Test Structure
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
```

## Documentation Standards

### Inline Documentation
- Every function must have a docstring
- Use Google-style docstrings
- Include type hints for all parameters and return values
- Document exceptions that can be raised

### External Documentation
- Each command must have a comprehensive README section
- Include usage examples
- Document input/output formats
- Explain error conditions
- Provide troubleshooting guidance

### Code Comments
- Explain complex logic
- Document business rules
- Clarify non-obvious code
- Avoid obvious comments

## Performance Standards

### Memory Usage
- Process data in chunks for large datasets
- Avoid loading entire datasets into memory when possible
- Use generators for large data processing

### Execution Time
- Commands should complete within reasonable time
- Provide progress indicators for long-running operations
- Use appropriate algorithms for data processing

### Resource Management
- Close file handles properly
- Clean up temporary files
- Handle memory leaks

## Security Standards

### Input Validation
- Validate all user inputs
- Sanitize file paths
- Check data types and ranges
- Prevent injection attacks

### Credential Handling
- Never hardcode credentials
- Use environment variables for sensitive data
- Follow AWS security best practices
- Document security requirements

## Version Control Standards

### Commit Messages
- Use clear, descriptive commit messages
- Follow conventional commit format
- Reference issues when applicable
- Keep commits focused and atomic

### Code Review
- All code must be reviewed before merging
- Check adherence to coding standards
- Verify test coverage
- Ensure documentation is updated

## Dependencies

### Python Version
- Target Python 3.8+
- Use type hints
- Follow PEP 8 style guidelines

### External Dependencies
- Minimize external dependencies
- Pin dependency versions
- Document all dependencies
- Use virtual environments

### System Dependencies
- Document system requirements
- Check for required tools at startup
- Provide clear error messages for missing dependencies

## Refactoring Guidelines

### When Refactoring Existing Commands
Based on the successful refactoring of `cost_and_usage.py`, follow these steps:

1. **Start with High Priority Changes**:
   - Update file header to new template format
   - Add `handle_error()` function and standardize error handling
   - Restructure functions to match template (create_argument_parser, etc.)
   - Add type hints to all functions
   - Update imports and constants organization

2. **Maintain Backward Compatibility**:
   - Keep all existing functionality working
   - Test thoroughly with real AWS APIs
   - Ensure pipe compatibility is preserved
   - Verify all command-line arguments still work

3. **Testing Strategy**:
   - Create comprehensive test suite before refactoring
   - Test all functionality manually first
   - Implement automated tests covering all scenarios
   - Use temporary files for output testing
   - Include AWS CLI integration tests with skip conditions

4. **Documentation Updates**:
   - Update coding standards based on lessons learned
   - Document new patterns and best practices
   - Include examples of successful refactoring
   - Update templates with proven approaches

### Common Refactoring Patterns
- **Error Handling**: Replace direct `print()` and `sys.exit()` with `handle_error()`
- **Function Structure**: Extract argument parser to separate function
- **Output Testing**: Use temporary files instead of stdout capture
- **Type Safety**: Add comprehensive type hints to all functions
- **Import Organization**: Follow standard library → third-party → constants order

## Examples

### Complete Command Template
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
Command Name: example_command

Purpose:
    This command demonstrates the coding standards for FinOps toolkit commands.

Input Format:
    CSV with columns: PeriodStart, Service, UnblendedCost

Output Format:
    CSV with columns: PeriodStart, Service, ProcessedCost

Error Handling:
    - Exit code 1: Invalid arguments
    - Exit code 2: File I/O errors
    - Exit code 3: Data validation errors

Dependencies:
    - pandas
    - Python 3.8+

Examples:
    # Basic usage
    python aws/example_command.py --input data.csv --multiplier 1.5
    
    # With pipe
    python aws/cost_and_usage.py --granularity daily | python aws/example_command.py --multiplier 2.0

Author: Frank Contrepois
License: MIT
"""

import argparse
import sys
import os
from typing import Optional
import pandas as pd

def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        description="Example command demonstrating coding standards",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--input",
        help="Input CSV file (if not provided, reads from stdin)"
    )
    
    parser.add_argument(
        "--multiplier",
        type=float,
        default=1.0,
        help="Multiplier to apply to cost values (default: 1.0)"
    )
    
    return parser

def read_input_data(input_file: Optional[str]) -> pd.DataFrame:
    """Read input data from file or stdin."""
    if input_file:
        if not os.path.isfile(input_file):
            print(f"Error: Input file '{input_file}' does not exist.", file=sys.stderr)
            sys.exit(2)
        df = pd.read_csv(input_file)
    else:
        if sys.stdin.isatty():
            print("Error: No input data provided.", file=sys.stderr)
            sys.exit(1)
        df = pd.read_csv(sys.stdin)
    
    if df.empty:
        print("Error: Input data is empty.", file=sys.stderr)
        sys.exit(3)
    
    return df

def validate_input_data(df: pd.DataFrame) -> None:
    """Validate input data format."""
    required_columns = ["PeriodStart", "Service", "UnblendedCost"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        print(f"Error: Missing required columns: {', '.join(missing_columns)}", file=sys.stderr)
        sys.exit(3)

def process_data(df: pd.DataFrame, multiplier: float) -> pd.DataFrame:
    """Process the input data."""
    result_df = df.copy()
    result_df["ProcessedCost"] = result_df["UnblendedCost"] * multiplier
    return result_df[["PeriodStart", "Service", "ProcessedCost"]]

def main() -> None:
    """Main entry point."""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Read and validate input
    df = read_input_data(args.input)
    validate_input_data(df)
    
    # Process data
    result_df = process_data(df, args.multiplier)
    
    # Output results
    result_df.to_csv(sys.stdout, index=False)

if __name__ == "__main__":
    main()
```

This coding standards document serves as the definitive guide for all FinOps toolkit development. All commands must adhere to these standards to ensure consistency, maintainability, and interoperability across the toolkit.
