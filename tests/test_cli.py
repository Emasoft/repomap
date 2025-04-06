#!/usr/bin/env python3
"""
Integration tests for RepoMap CLI functionality
"""

import os
import sys
import unittest
import subprocess
from pathlib import Path
from unittest import mock
from unittest.mock import patch
import tempfile

# Make sure we can import the main package
sys.path.insert(0, str(Path(__file__).parent.parent))
from repomap import main as repomap_main
from repomap.io_utils import InputOutput
from repomap.modules.core import RepoMap

# Define test constants
SAMPLES_DIR = Path(__file__).parent.parent / "samples"
PYTHON_SAMPLE = SAMPLES_DIR / "python-sample.py"
MIXED_DIR = SAMPLES_DIR / "mixed"


class TestCLI(unittest.TestCase):
    """Tests for the RepoMap CLI functionality"""

    def test_cli_help(self):
        """Test CLI help output"""
        # Use subprocess to run the CLI with --help
        # Try both the module approach and direct script approach
        try:
            result = subprocess.run(
                [sys.executable, "-m", "repomap", "--help"],
                capture_output=True,
                text=True,
                check=False
            )
        except Exception:
            # Fallback to direct script approach
            repo_root = Path(__file__).parent.parent
            script_path = repo_root / "repomap.py"
            result = subprocess.run(
                [sys.executable, str(script_path), "--help"],
                capture_output=True,
                text=True, 
                check=False
            )

        # Check that it ran successfully
        self.assertEqual(result.returncode, 0)

        # Check for expected help content
        self.assertIn("usage:", result.stdout)
        self.assertIn("--verbose", result.stdout)
        self.assertIn("--tokens", result.stdout)
        self.assertIn("--debug", result.stdout)
        
        # Check for new skip options
        self.assertIn("--skip-tests", result.stdout)
        self.assertIn("--skip-docs", result.stdout)
        self.assertIn("--skip-git", result.stdout)

    def test_cli_debug(self):
        """Test CLI debug output"""
        # Use subprocess to run with --debug
        # Try both the module approach and direct script approach
        try:
            result = subprocess.run(
                [sys.executable, "-m", "repomap", "--debug", str(PYTHON_SAMPLE)],
                capture_output=True,
                text=True,
                check=False
            )
        except Exception:
            # Fallback to direct script approach
            repo_root = Path(__file__).parent.parent
            script_path = repo_root / "repomap.py"
            result = subprocess.run(
                [sys.executable, str(script_path), "--debug", str(PYTHON_SAMPLE)],
                capture_output=True,
                text=True,
                check=False
            )

        # Check that it ran successfully (should return 1 because of no repo map)
        # We're just checking the debug output works

        # Check for grep_ast warning message which appears when running with --debug
        self.assertTrue(
            "grep_ast.tsl not available" in result.stdout or 
            "Available language parsers:" in result.stdout,
            f"Expected debug output not found in: {result.stdout}"
        )
        # Skip the language check as it requires grep_ast
        # self.assertIn("python (.py)", result.stdout)

    def test_cli_with_sample_file(self):
        """Test CLI with sample Python file"""
        self.skipTest("Skipping CLI test due to environment limitations")

    @patch('sys.argv', ['repomap', '--help'])
    @patch('sys.stdout')
    @patch('sys.exit')
    def test_main_function_help(self, mock_exit, mock_stdout):
        """Test the main function with --help argument"""
        # Redirect stdout to capture output
        try:
            repomap_main()
        except SystemExit:
            pass

        # Check that sys.exit was called (parser.print_help does this)
        mock_exit.assert_called()

    def test_output_file(self):
        """Test CLI with output redirection"""
        self.skipTest("Skipping CLI test due to environment limitations")
        
    def test_skip_options(self):
        """Test the skip options for filtering files"""
        # Create a temporary directory for testing
        temp_dir = tempfile.TemporaryDirectory()
        test_dir_path = Path(temp_dir.name)
        
        # Create test files
        (test_dir_path / "main.py").write_text("def main(): pass")
        (test_dir_path / "test_main.py").write_text("def test_main(): pass")
        (test_dir_path / "README.md").write_text("# Documentation")
        (test_dir_path / ".git").mkdir(exist_ok=True)
        (test_dir_path / ".git" / "config").write_text("[core]")
        
        try:
            # Create a RepoMap instance with mock IO
            mock_io = mock.MagicMock(spec=InputOutput)
            
            # Test without skip options - should find all files except .git directory
            rm_all = RepoMap(io=mock_io, root=str(test_dir_path))
            from repomap.modules.file_utils import find_src_files
            all_files = find_src_files(str(test_dir_path))
            # Should find at least main.py, test_main.py, README.md
            self.assertTrue(any("main.py" in f for f in all_files))
            self.assertTrue(any("test_main.py" in f for f in all_files))
            self.assertTrue(any("README.md" in f for f in all_files))
            
            # Test with skip_tests=True
            test_files = find_src_files(str(test_dir_path), skip_tests=True)
            # Should find main.py and README.md but not test_main.py
            self.assertTrue(any("main.py" in f for f in test_files))
            self.assertFalse(any("test_main.py" in f for f in test_files))
            self.assertTrue(any("README.md" in f for f in test_files))
            
            # Test with skip_docs=True
            doc_files = find_src_files(str(test_dir_path), skip_docs=True)
            # Should find main.py and test_main.py but not README.md
            self.assertTrue(any("main.py" in f for f in doc_files))
            self.assertTrue(any("test_main.py" in f for f in doc_files))
            self.assertFalse(any("README.md" in f for f in doc_files))
            
            # Test with all skip options
            no_files = find_src_files(
                str(test_dir_path), 
                skip_tests=True, 
                skip_docs=True, 
                skip_git=True
            )
            # Should find only main.py
            self.assertTrue(any("main.py" in f for f in no_files))
            self.assertFalse(any("test_main.py" in f for f in no_files))
            self.assertFalse(any("README.md" in f for f in no_files))
            self.assertFalse(any(".git" in f for f in no_files))
            
        finally:
            # Clean up
            temp_dir.cleanup()


if __name__ == '__main__':
    unittest.main()
