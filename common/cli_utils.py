#!/usr/bin/env python3

import sys
import json
from typing import Any, Dict


def handle_error(message: str, exit_code: int = 1) -> None:
    """Print error message and exit with specified code."""
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(exit_code)


def write_csv_output(df, include_header: bool = True) -> None:
    """Write DataFrame as CSV to stdout."""
    df.to_csv(sys.stdout, index=False, header=include_header)


def write_json_output(data: Dict[str, Any], indent: int = 2) -> None:
    """Write data as JSON to stdout."""
    json.dump(data, sys.stdout, indent=indent)
    sys.stdout.write("\n")



