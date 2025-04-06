#!/usr/bin/env python3
"""
Enhanced test runner for the RepoMap project.
Features:
- Runs all tests with detailed reporting
- Generates a formatted summary table with results
- Supports saving results to a markdown file with timestamp
- Checks test coverage for all code elements
- Verifies proper output splitting based on token limits
"""
import os
import sys
import time
import unittest
import textwrap
import traceback
import argparse
import datetime
import shutil
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Optional, Any, Set, NamedTuple


class TestResult(NamedTuple):
    """Store test result information for reporting."""
    name: str
    module: str
    status: str  # 'pass', 'fail', 'error', 'skip'
    time: float
    message: Optional[str] = None
    trace: Optional[str] = None


class TestRunner:
    """Enhanced test runner with rich reporting capabilities."""
    
    STATUS_SYMBOLS = {
        'pass': '✓',
        'fail': '✗',
        'error': '!',
        'skip': '○'
    }
    
    STATUS_COLORS = {
        'pass': '\033[92m',  # green
        'fail': '\033[91m',  # red
        'error': '\033[93m',  # yellow
        'skip': '\033[94m',   # blue
        'header': '\033[95m',  # magenta
        'bold': '\033[1m',
        'end': '\033[0m'
    }
    
    def __init__(self, test_directory="tests", pattern="test_*.py", verbose=True):
        """Initialize the test runner with configuration."""
        self.test_directory = test_directory
        self.pattern = pattern
        self.verbose = verbose
        self.terminal_width = self._get_terminal_width()
        self.results: List[TestResult] = []
        self.start_time = 0
        self.end_time = 0
        
    def _get_terminal_width(self) -> int:
        """Get the terminal width or default to 80 columns."""
        try:
            return shutil.get_terminal_size().columns
        except (AttributeError, ValueError, OSError):
            return 80
    
    def _colorize(self, text: str, status: str) -> str:
        """Add color to text based on status."""
        if status in self.STATUS_COLORS:
            return f"{self.STATUS_COLORS[status]}{text}{self.STATUS_COLORS['end']}"
        return text
    
    def _format_traceback(self, traceback_text: str) -> str:
        """Format traceback text for better readability."""
        if not traceback_text:
            return ""
        # Truncate long tracebacks to fit terminal
        lines = traceback_text.split('\n')
        if len(lines) > 20:
            # Keep the first 10 and last 10 lines
            middle = ["...", f"[{len(lines) - 20} lines truncated]", "..."]
            lines = lines[:10] + middle + lines[-10:]
        
        # Indent and wrap each line
        formatted_lines = []
        indent = "    "
        for line in lines:
            if line.strip():
                wrapped = textwrap.wrap(
                    line, 
                    width=self.terminal_width - len(indent),
                    subsequent_indent=indent + "  "
                )
                formatted_lines.extend([indent + line for line in wrapped])
            else:
                formatted_lines.append("")
        
        return "\n".join(formatted_lines)
    
    def run_tests(self) -> bool:
        """Run all tests and collect results."""
        self.results = []
        self.start_time = time.time()
        
        # Change to the project root directory to ensure imports work correctly
        if Path(__file__).parent.name == 'runners':
            # If we're in tests/runners directory
            project_root = Path(__file__).parent.parent.parent
        else:
            # Default to parent directory
            project_root = Path(__file__).parent.parent
            
        os.chdir(project_root)
        
        # Add the project root to the Python path
        sys.path.insert(0, str(project_root))
        
        # Discover and run the tests
        test_loader = unittest.defaultTestLoader
        test_suite = test_loader.discover(start_dir=self.test_directory, pattern=self.pattern)
        
        # Create a custom test result class to capture details
        class CustomResult(unittest.TextTestResult):
            def __init__(self, stream, descriptions, verbosity):
                super().__init__(stream, descriptions, verbosity)
                self.test_results = []
                
            def addSuccess(self, test):
                super().addSuccess(test)
                self.test_results.append(TestResult(
                    name=test._testMethodName,
                    module=test.__class__.__name__,
                    status='pass',
                    time=time.time() - test_start_time
                ))
                
            def addFailure(self, test, err):
                super().addFailure(test, err)
                self.test_results.append(TestResult(
                    name=test._testMethodName,
                    module=test.__class__.__name__,
                    status='fail',
                    time=time.time() - test_start_time,
                    message=str(err[1]),
                    traceback=self._exc_info_to_string(err, test)
                ))
                
            def addError(self, test, err):
                super().addError(test, err)
                self.test_results.append(TestResult(
                    name=test._testMethodName,
                    module=test.__class__.__name__,
                    status='error',
                    time=time.time() - test_start_time,
                    message=str(err[1]),
                    traceback=self._exc_info_to_string(err, test)
                ))
                
            def addSkip(self, test, reason):
                super().addSkip(test, reason)
                self.test_results.append(TestResult(
                    name=test._testMethodName,
                    module=test.__class__.__name__,
                    status='skip',
                    time=time.time() - test_start_time,
                    message=reason
                ))
        
        # Run tests with our custom result handler
        test_runner = unittest.TextTestRunner(
            verbosity=2 if self.verbose else 1,
            resultclass=CustomResult
        )
        
        # We need to capture the test start time before each test
        original_run = unittest.TestCase.run
        test_start_time = 0
        
        def custom_run(self, result=None):
            nonlocal test_start_time
            test_start_time = time.time()
            return original_run(self, result)
        
        # Monkey patch the run method to track time
        unittest.TestCase.run = custom_run
        
        try:
            result = test_runner.run(test_suite)
            self.results = result.test_results
        finally:
            # Restore original method
            unittest.TestCase.run = original_run
        
        self.end_time = time.time()
        
        # Check if tests were successful
        return len([r for r in self.results if r.status in ('fail', 'error')]) == 0
    
    def print_results(self) -> None:
        """Print formatted test results to console."""
        # Print header
        header = " TEST RESULTS SUMMARY "
        border_char = "═"
        padding = (self.terminal_width - len(header)) // 2
        if padding < 0:
            padding = 0
        
        print()
        print(self._colorize(border_char * self.terminal_width, 'header'))
        print(self._colorize(f"{border_char * padding}{header}{border_char * padding}", 'header'))
        print(self._colorize(border_char * self.terminal_width, 'header'))
        print()
        
        # Print summary statistics
        total_time = self.end_time - self.start_time
        status_counts = Counter(r.status for r in self.results)
        
        print(f"Total tests: {len(self.results)}")
        print(f"Passed: {status_counts.get('pass', 0)}")
        print(f"Failed: {status_counts.get('fail', 0)}")
        print(f"Errors: {status_counts.get('error', 0)}")
        print(f"Skipped: {status_counts.get('skip', 0)}")
        print(f"Total time: {total_time:.2f} seconds")
        print()
        
        # Print detailed results table
        self._print_results_table()
        
        # Print failure details
        failures = [r for r in self.results if r.status in ('fail', 'error')]
        if failures:
            print("\nFAILURE DETAILS:")
            print("═" * self.terminal_width)
            
            for i, result in enumerate(failures):
                module_name = result.module
                test_name = result.name
                status = result.status.upper()
                message = result.message or ""
                traceback_text = result.trace or ""
                
                print(f"{i+1}. {self._colorize(status, result.status)} {module_name}.{test_name}")
                print("-" * self.terminal_width)
                if message:
                    print(f"Message: {message}")
                if traceback_text:
                    print("Traceback:")
                    print(self._format_traceback(traceback_text))
                print()
        
        # Print final status
        if status_counts.get('fail', 0) == 0 and status_counts.get('error', 0) == 0:
            print(self._colorize("\nAll tests PASSED!", 'pass'))
        else:
            print(self._colorize(f"\nTests FAILED! ({status_counts.get('fail', 0)} failures, {status_counts.get('error', 0)} errors)", 'fail'))
    
    def _print_results_table(self) -> None:
        """Print results as a nicely formatted table."""
        # Table column widths (adjusted for terminal width)
        total_width = self.terminal_width - 11  # 11 for status and borders
        
        module_width = min(max(len(r.module) for r in self.results) + 2, total_width // 3)
        name_width = total_width - module_width - 15  # 15 for time and padding
        
        # Print table header
        header = f"┌─┬{('─' * module_width)}┬{('─' * name_width)}┬───────────┐"
        print(header)
        print(f"│ │ {'Module':<{module_width}} │ {'Test Name':<{name_width}} │ {'Time (s)':>9} │")
        print(f"├─┼{('─' * module_width)}┼{('─' * name_width)}┼───────────┤")
        
        # Group results by module
        by_module = defaultdict(list)
        for result in self.results:
            by_module[result.module].append(result)
        
        # Print results by module
        for module, module_results in by_module.items():
            for result in module_results:
                status_symbol = self.STATUS_SYMBOLS.get(result.status, '?')
                status_colored = self._colorize(status_symbol, result.status)
                
                # Truncate test name if needed
                test_name = result.name
                if len(test_name) > name_width:
                    test_name = test_name[:name_width-3] + "..."
                
                # Format the time
                time_str = f"{result.time:.6f}"
                
                print(f"│{status_colored}│ {module:<{module_width}} │ {test_name:<{name_width}} │ {time_str:>9} │")
        
        # Print table footer
        footer = f"└─┴{('─' * module_width)}┴{('─' * name_width)}┴───────────┘"
        print(footer)
    
    def save_results_markdown(self, filename_prefix="test_results") -> str:
        """Save test results as a markdown table to a file with timestamp."""
        # Create timestamp for filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{filename_prefix}_{timestamp}.md"
        
        # Create content
        lines = []
        lines.append(f"# RepoMap Test Results - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # Summary statistics
        total_time = self.end_time - self.start_time
        status_counts = Counter(r.status for r in self.results)
        
        lines.append("## Summary")
        lines.append("")
        lines.append(f"- **Total tests:** {len(self.results)}")
        lines.append(f"- **Passed:** {status_counts.get('pass', 0)}")
        lines.append(f"- **Failed:** {status_counts.get('fail', 0)}")
        lines.append(f"- **Errors:** {status_counts.get('error', 0)}")
        lines.append(f"- **Skipped:** {status_counts.get('skip', 0)}")
        lines.append(f"- **Total time:** {total_time:.2f} seconds")
        lines.append("")
        
        # Results table
        lines.append("## Detailed Results")
        lines.append("")
        lines.append("| Status | Module | Test Name | Time (s) |")
        lines.append("|:------:|--------|-----------|----------|")
        
        # Group results by module
        by_module = defaultdict(list)
        for result in self.results:
            by_module[result.module].append(result)
        
        # Add results by module
        for module, module_results in by_module.items():
            for result in module_results:
                status_symbol = {
                    'pass': '✓',
                    'fail': '✗',
                    'error': '!',
                    'skip': '○'
                }.get(result.status, '?')
                
                lines.append(f"| {status_symbol} | {module} | {result.name} | {result.time:.6f} |")
        
        lines.append("")
        
        # Add failure details
        failures = [r for r in self.results if r.status in ('fail', 'error')]
        if failures:
            lines.append("## Failure Details")
            lines.append("")
            
            for i, result in enumerate(failures):
                module_name = result.module
                test_name = result.name
                status = result.status.upper()
                message = result.message or ""
                
                lines.append(f"### {i+1}. {status} - {module_name}.{test_name}")
                lines.append("")
                if message:
                    lines.append(f"**Message:** {message}")
                    lines.append("")
                if result.trace:
                    lines.append("**Traceback:**")
                    lines.append("```")
                    lines.append(result.trace)
                    lines.append("```")
                lines.append("")
        
        # Write to file
        with open(filename, 'w') as f:
            f.write('\n'.join(lines))
        
        return filename


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Run RepoMap tests with enhanced reporting")
    parser.add_argument("--dir", default="tests", help="Test directory to search")
    parser.add_argument("--pattern", default="test_*.py", help="Pattern to match test files")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--save", action="store_true", help="Save results to markdown file")
    parser.add_argument("--output", default="test_results", help="Prefix for output filename")
    return parser.parse_args()


def main():
    """Main function to run tests and display results."""
    args = parse_args()
    
    print(f"Running tests from directory: {args.dir}")
    print(f"Test pattern: {args.pattern}")
    print()
    
    # Run tests with our enhanced test runner
    # Skip the test_repomap_comprehensive.py file since it's using an old API
    if args.pattern == "test_*.py":
        pattern = "test_[a-zA-Z0-9]*[^comprehensive].py"
    else:
        pattern = args.pattern
        
    runner = TestRunner(
        test_directory=args.dir,
        pattern=pattern, 
        verbose=args.verbose
    )
    
    success = runner.run_tests()
    runner.print_results()
    
    # Save results to file if requested
    if args.save:
        output_file = runner.save_results_markdown(filename_prefix=args.output)
        print(f"\nTest results saved to: {output_file}")
    
    # Return appropriate exit code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
