#!/usr/bin/env python3
"""
Tests for the utility functions in RepoMap
"""

import os
import sys
import unittest
import tempfile
from pathlib import Path
from io import StringIO
from unittest.mock import patch

# Make sure we can import the main package
sys.path.insert(0, str(Path(__file__).parent.parent))
from repomap.utils import (
    is_image_file, Spinner, safe_abs_path, format_tokens,
    IgnorantTemporaryDirectory, ChdirTemporaryDirectory
)

# For Windows vs Unix path testing
IS_WINDOWS = sys.platform.startswith('win')


class TestUtils(unittest.TestCase):
    """Tests for the utility functions"""

    def test_is_image_file(self):
        """Test image file detection"""
        # Test positive cases
        for ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp', '.pdf']:
            filename = f"test{ext}"
            self.assertTrue(is_image_file(filename), f"Failed for {ext}")

        # Test negative cases
        for ext in ['.py', '.txt', '.md', '.json', '.xml']:
            filename = f"test{ext}"
            self.assertFalse(is_image_file(filename), f"Failed for {ext}")

        # Test with Path object
        self.assertTrue(is_image_file(Path("test.png")))
        self.assertFalse(is_image_file(Path("test.txt")))

    def test_format_tokens(self):
        """Test token formatting"""
        # Test small number
        self.assertEqual(format_tokens(123), "123")

        # Test thousands
        self.assertEqual(format_tokens(1234), "1.2k")
        self.assertEqual(format_tokens(5678), "5.7k")

        # Test larger numbers
        self.assertEqual(format_tokens(12345), "12k")
        self.assertEqual(format_tokens(123456), "123k")

    def test_safe_abs_path(self):
        """Test safe absolute path conversion"""
        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test with string
            abs_path = safe_abs_path(temp_dir)
            self.assertTrue(os.path.isabs(abs_path))

            # Test with Path object
            abs_path = safe_abs_path(Path(temp_dir))
            self.assertTrue(os.path.isabs(abs_path))

            # Test with relative path
            # We need to be careful because the absolute path depends on CWD
            rel_path = "."
            abs_path = safe_abs_path(rel_path)
            self.assertTrue(os.path.isabs(abs_path))

    def test_ignorant_temp_dir(self):
        """Test IgnorantTemporaryDirectory"""
        # Basic functionality
        with IgnorantTemporaryDirectory() as temp_dir:
            # Check that directory exists
            self.assertTrue(os.path.exists(temp_dir))
            # Create a test file in the directory
            test_file = os.path.join(temp_dir, "test.txt")
            with open(test_file, 'w') as f:
                f.write("test")
            self.assertTrue(os.path.exists(test_file))

        # Check that directory is cleaned up
        self.assertFalse(os.path.exists(temp_dir))

    def test_chdir_temp_dir(self):
        """Test ChdirTemporaryDirectory"""
        # Save current directory
        original_dir = os.getcwd()

        # Use the context manager
        with ChdirTemporaryDirectory() as temp_dir:
            # Check that we changed to the temporary directory
            self.assertEqual(os.getcwd(), os.path.realpath(temp_dir))

            # Create a test file
            with open("test.txt", 'w') as f:
                f.write("test")

            # Verify file is in the temp directory
            self.assertTrue(os.path.exists(os.path.join(temp_dir, "test.txt")))

        # Verify we're back to the original directory
        self.assertEqual(os.getcwd(), original_dir)

        # Verify temp directory is gone
        self.assertFalse(os.path.exists(temp_dir))

    @patch('sys.stdout', new_callable=StringIO)
    def test_spinner(self, mock_stdout):
        """Test Spinner class"""
        # Basic spinner creation
        spinner = Spinner("Testing")
        self.assertEqual(spinner.text, "Testing")

        # Test step and end methods - just make sure they don't crash
        # This is hard to test fully due to timing and terminal interactions
        spinner.step()
        spinner.end()

        # Check that something was output (when connected to a TTY)
        # This is more of a smoke test
        if sys.stdout.isatty():
            # Can't reliably test output when connected to a TTY
            pass
        else:
            # When not connected to TTY, the spinner shouldn't output anything
            self.assertEqual(mock_stdout.getvalue(), "")


if __name__ == '__main__':
    unittest.main()
