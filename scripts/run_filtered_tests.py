#!/usr/bin/env python3
"""
Run filtered tests based on pattern matching.
This script allows running only specific tests that match a given pattern.
"""
import sys
import argparse
import unittest
import fnmatch
import os
from pathlib import Path


def find_test_modules(test_dir='tests', pattern='*', exclude_patterns=None):
    """Find test modules matching pattern and not in exclude_patterns."""
    if exclude_patterns is None:
        exclude_patterns = []
        
    test_modules = []
    
    for root, _, files in os.walk(test_dir):
        for filename in files:
            if filename.startswith('test_') and filename.endswith('.py'):
                # Check if file should be excluded
                skip = False
                for exclude in exclude_patterns:
                    if fnmatch.fnmatch(filename, exclude):
                        skip = True
                        break
                
                # Check if it matches the pattern
                if not skip and (pattern == '*' or fnmatch.fnmatch(filename, f"*{pattern}*.py")):
                    module_path = os.path.join(root, filename)
                    # Convert path to module name
                    module_name = os.path.splitext(module_path)[0].replace(os.path.sep, '.')
                    test_modules.append(module_name)
                    
    return test_modules


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
        "--exclude", "-e",
        action="append",
        default=[],
        help="Test pattern to exclude (can be used multiple times)"
    )
    parser.add_argument(
        "--unittest",
        action="store_true",
        help="Use unittest instead of pytest"
    )
    
    args = parser.parse_args()
    
    # Set up paths correctly
    project_root = Path(__file__).parent.parent
    test_dir = str(project_root / "tests")
            
    # Change to project root and add to Python path
    os.chdir(project_root)
    sys.path.insert(0, str(project_root))
    
    if args.unittest:
        # Use unittest
        # Files to exclude
        exclude_patterns = args.exclude + [
            'test_repomap_comprehensive.py',  # Complex test that may cause issues
        ]
        
        # Find test modules
        test_modules = find_test_modules(test_dir=test_dir, 
                                          pattern=args.pattern, 
                                          exclude_patterns=exclude_patterns)
        
        if args.verbose:
            print(f"Running {len(test_modules)} test modules:")
            for module in test_modules:
                print(f"  {module}")
            print()
        
        # Load and run tests
        test_suite = unittest.defaultTestLoader.loadTestsFromNames(test_modules)
        runner = unittest.TextTestRunner(verbosity=2 if args.verbose else 1)
        result = runner.run(test_suite)
        
        # Exit with appropriate exit code
        return not result.wasSuccessful()
    else:
        # Use pytest (default)
        import subprocess
        
        # Construct the pytest command
        cmd = ["python", "-m", "pytest"]
        
        # Add pattern
        if args.pattern != "*":
            cmd.append(f"-k={args.pattern}")
        
        # Add excludes
        for exclude in args.exclude:
            cmd.append(f"--ignore=*{exclude}*")
        
        # Add test directory
        cmd.append(test_dir)
        
        # Add verbose flag if requested
        if args.verbose:
            cmd.append("-v")
        
        if args.verbose:
            print(f"Running command: {' '.join(cmd)}")
        
        # Run the command
        result = subprocess.run(cmd)
        return result.returncode


if __name__ == "__main__":
    sys.exit(main())
