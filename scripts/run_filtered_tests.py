#!/usr/bin/env python3
"""
Run filtered tests based on pattern matching.
This script allows running only specific tests that match a given pattern.
"""
import sys
import subprocess
import argparse
from pathlib import Path


def main():
    """Main function to run filtered tests."""
    parser = argparse.ArgumentParser(description="Run filtered tests based on pattern matching")
    parser.add_argument(
        "pattern",
        nargs="?",
        default="*",
        help="Test pattern to match (default: * for all tests)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--coverage", "-c",
        action="store_true",
        help="Generate coverage report"
    )
    
    args = parser.parse_args()
    
    # Construct the pytest command
    cmd = ["pytest"]
    
    # Add pattern
    if args.pattern != "*":
        cmd.append(f"-k={args.pattern}")
    
    # Add test directory
    cmd.append("tests/")
    
    # Add verbose flag if requested
    if args.verbose:
        cmd.append("-v")
    
    # Add coverage flag if requested
    if args.coverage:
        cmd.append("--cov=repomap")
    
    print(f"Running command: {' '.join(cmd)}")
    
    # Run the command
    result = subprocess.run(cmd)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())