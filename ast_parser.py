#!/usr/bin/env python3
"""
AST Parser - Main entry point for the command-line tool.
This script provides a direct way to run the AST Parser tool from the command line.
"""
import sys
import os
from pathlib import Path

# Add the package directory to the Python path
current_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir))

try:
    # Import from installed package
    from repomap.ast_parser import main
except ImportError:
    try:
        # Try direct import from current directory
        sys.path.insert(0, str(current_dir))
        from repomap.ast_parser import main
    except ImportError:
        print("Error: RepoMap package not found. Please install it first.")
        sys.exit(1)

if __name__ == "__main__":
    # Pass command-line arguments to the main function
    sys.exit(main())