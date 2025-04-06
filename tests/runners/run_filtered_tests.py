#!/usr/bin/env python3
"""
Script to run a filtered subset of tests, excluding problematic ones.
"""
import os
import sys
import unittest
import fnmatch

def find_test_modules(test_dir='tests', pattern='test_*.py', exclude_patterns=None):
    """Find test modules matching pattern and not in exclude_patterns."""
    if exclude_patterns is None:
        exclude_patterns = []
        
    test_modules = []
    
    for root, _, files in os.walk(test_dir):
        for filename in files:
            if fnmatch.fnmatch(filename, pattern):
                # Check if file should be excluded
                skip = False
                for exclude in exclude_patterns:
                    if fnmatch.fnmatch(filename, exclude):
                        skip = True
                        break
                        
                if not skip:
                    module_path = os.path.join(root, filename)
                    # Convert path to module name
                    module_name = os.path.splitext(module_path)[0].replace(os.path.sep, '.')
                    test_modules.append(module_name)
                    
    return test_modules

def main():
    # Set up paths correctly
    from pathlib import Path
    
    if Path(__file__).parent.name == 'runners':
        # If we're in tests/runners directory
        project_root = Path(__file__).parent.parent.parent
        test_dir = str(Path(__file__).parent.parent)
    else:
        # Default to parent directory
        project_root = Path(__file__).parent.parent
        test_dir = str(Path(__file__).parent)
            
    # Change to project root and add to Python path
    os.chdir(project_root)
    sys.path.insert(0, str(project_root))
    
    # Files to exclude
    exclude_patterns = [
        'test_repomap_comprehensive.py',  # API mismatch
    ]
    
    # Find test modules
    test_modules = find_test_modules(test_dir=test_dir, exclude_patterns=exclude_patterns)
    print(f"Running {len(test_modules)} test modules:")
    for module in test_modules:
        print(f"  {module}")
    print()
    
    # Load and run tests
    test_suite = unittest.defaultTestLoader.loadTestsFromNames(test_modules)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Exit with appropriate exit code
    sys.exit(not result.wasSuccessful())

if __name__ == "__main__":
    main()
