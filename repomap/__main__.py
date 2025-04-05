#!/usr/bin/env python3
"""
Main entry point for RepoMap when run as a module.
"""
import sys
import os
import argparse
from pathlib import Path

from .modules.core import RepoMap
from .io_utils import InputOutput

def main():
    """Main function for the command line interface."""
    parser = argparse.ArgumentParser(
        description="RepoMap: Generate maps of repositories for easy understanding."
    )
    parser.add_argument(
        "files", nargs="*", help="Files or directories to include in the map"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )
    parser.add_argument(
        "--debug", action="store_true", help="Enable debug output, including parser info"
    )
    parser.add_argument(
        "--output", "-o", help="Write repository map to this file"
    )
    parser.add_argument(
        "--tokens", "-t", type=int, default=4096,
        help="Maximum number of tokens per section"
    )
    parser.add_argument(
        "--no-splitting", action="store_true", help="Disable map splitting"
    )
    parser.add_argument(
        "--skip-tests", action="store_true", help="Skip test files and directories"
    )
    parser.add_argument(
        "--skip-docs", action="store_true", help="Skip documentation files"
    )
    parser.add_argument(
        "--skip-git", action="store_true", help="Skip git-related files and directories"
    )
    args = parser.parse_args()

    io = InputOutput(quiet=not args.verbose)
    
    if args.debug:
        try:
            from grep_ast.tsl import get_language_ids
            parsers = get_language_ids()
            print("Available language parsers:")
            for p in sorted(parsers):
                print(f"  - {p}")
            print()
        except ImportError:
            print("Warning: grep_ast.tsl not available, some features will be limited.")
    
    if not args.files:
        parser.print_help()
        return 1
    
    repo_map = RepoMap(
        io=io,
        verbose=args.verbose,
        debug=args.debug,
        map_tokens=args.tokens,
        disable_splitting=args.no_splitting,
        skip_tests=args.skip_tests,
        skip_docs=args.skip_docs,
        skip_git=args.skip_git
    )
    
    expanded_files = []
    for pattern in args.files:
        expanded_files.extend(repo_map.expand_globs(pattern))
    
    if not expanded_files:
        print(f"Error: No files found matching: {', '.join(args.files)}")
        return 1
    
    output = repo_map.get_repo_map(expanded_files)
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output)
        print(f"Repository map written to {args.output}")
    else:
        print(output)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
