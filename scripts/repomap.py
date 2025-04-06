#!/usr/bin/env python3
"""
RepoMap - A command-line script wrapper for running the RepoMap tool.
This script allows users to run 'python repomap.py <args>' directly.
"""
import sys
import os
from pathlib import Path

# Add parent directory to path for running from any location
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

# Import the main function from repomap
try:
    from repomap import main
except ImportError:
    # Fallback if the package isn't installed
    try:
        # Try importing from parent directory
        # This is needed because the first import might fail due to relative imports
        from repomap import main
    except ImportError:
        print("Error: Could not import RepoMap. Please ensure it's installed.")
        sys.exit(1)

if __name__ == "__main__":
    # Pass all command-line arguments to the main function
    sys.exit(main())