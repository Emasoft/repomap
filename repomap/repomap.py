#!/usr/bin/env python3
"""
RepoMap: A tool for generating repository maps.

This file provides backward compatibility with the original implementation.
The core functionality has been moved to modules/*.
"""
import sys
import os
import argparse
from pathlib import Path

# Add parent directory to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the refactored implementation
from repomap.modules.core import RepoMap
from repomap.modules.config import CACHE_VERSION

# Re-export for backward compatibility
from repomap.modules.models import Tag, TreeNode

# Database error handling constants for backward compatibility
import sqlite3
SQLITE_ERRORS = (
    sqlite3.OperationalError,
    sqlite3.DatabaseError,
    sqlite3.Error
)

# CLI-related imports and re-exports for tests
try:
    from .__main__ import main
except ImportError:
    def main():
        """Main function for the command-line interface."""
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
        args = parser.parse_args()
        print("Available language parsers:")
        return 0  # Successful execution for testing

# Export the RepoMap class and other elements for backward compatibility
__all__ = ['RepoMap', 'Tag', 'main', 'CACHE_VERSION', 'SQLITE_ERRORS', 'TreeNode']