#!/usr/bin/env python3
"""
Script to add execute permission to the run_tests.py file.
"""
import os
import stat
from pathlib import Path

def add_execute_permission(file_path):
    """Add execute permission to the specified file."""
    # Get current permissions
    current_permissions = os.stat(file_path).st_mode
    
    # Add execute permission for owner, group, and others
    new_permissions = current_permissions | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
    
    # Set new permissions
    os.chmod(file_path, new_permissions)
    
    print(f"Execute permission added to {file_path}")

if __name__ == "__main__":
    # Add permission to both runners
    runners = ["run_tests.py", "run_filtered_tests.py"]
    for runner in runners:
        script_path = Path(__file__).parent / runner
        add_execute_permission(script_path)
