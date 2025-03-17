#!/usr/bin/env python3

"""
RepoMap command-line interface
"""

import sys
import os
import argparse
from pathlib import Path

# Import from package
try:
    from . import RepoMap, find_src_files
except ImportError:
    # Direct import when run as script
    from repomap import RepoMap, find_src_files


class SimpleIO:
    """Simple IO class to handle tool warnings and outputs"""
    
    def tool_warning(self, message):
        print(f"WARNING: {message}", file=sys.stderr)
    
    def tool_output(self, message):
        print(message)
    
    def tool_error(self, message):
        print(f"ERROR: {message}", file=sys.stderr)
    
    def read_text(self, fname):
        """Read text from a file"""
        try:
            with open(fname, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            self.tool_error(f"Failed to read {fname}: {e}")
            return None


def main():
    parser = argparse.ArgumentParser(description="Generate a map of a code repository")
    parser.add_argument("files", nargs="+", help="Files or directories to include in the map")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    
    if len(sys.argv) == 1:
        parser.print_help()
        return 1
    
    args = parser.parse_args()
    
    chat_fnames = []
    other_fnames = []
    for fname in args.files:
        if Path(fname).is_dir():
            chat_fnames += find_src_files(fname)
        else:
            chat_fnames.append(fname)
    
    class MockModel:
        """Mock model for token counting"""
        def token_count(self, text):
            """Simple token count estimate: 1 token per 4 characters"""
            return len(text) // 4

    io = SimpleIO()
    rm = RepoMap(root=".", io=io, verbose=args.verbose, main_model=MockModel(), map_tokens=8192)
    repo_map = rm.get_ranked_tags_map(chat_fnames, other_fnames)
    
    if repo_map:
        print(repo_map)
        return 0
    else:
        print("No repository map could be generated")
        return 1


if __name__ == "__main__":
    sys.exit(main())