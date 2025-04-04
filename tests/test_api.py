"""Tests for the repomap.api module."""

import os
import tempfile
import unittest
from pathlib import Path

import pytest

from repomap.api import generate_map, process_directory, get_file_symbols


class TestRepoMapAPI(unittest.TestCase):
    """Test the RepoMap API functions."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for test files
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_dir = Path(self.temp_dir.name)

        # Create a simple Python file for testing
        self.test_file = self.test_dir / "test_file.py"
        with open(self.test_file, "w") as f:
            f.write("""
def test_function():
    \"\"\"Test function.\"\"\"
    return "test"

class TestClass:
    \"\"\"Test class.\"\"\"

    def method(self):
        \"\"\"Test method.\"\"\"
        return "test method"
""")

        # Create an output directory
        self.output_dir = self.test_dir / "output"
        os.makedirs(self.output_dir, exist_ok=True)

    def tearDown(self):
        """Tear down test fixtures."""
        self.temp_dir.cleanup()

    def test_generate_map(self):
        """Test generating a repository map."""
        repo_map, part_files = generate_map(
            paths=[str(self.test_file)],
            output_dir=str(self.output_dir),
            token_limit=4096,
            verbose=False,
            no_split=True
        )

        # Check that we got a result
        self.assertIsNotNone(repo_map)
        self.assertTrue(len(repo_map) > 0)

        # Check that we got at least one output file
        self.assertTrue(len(part_files) > 0)

        # Check that the output file exists
        self.assertTrue(os.path.exists(part_files[0]))

        # Check that the repository map contains the test file
        self.assertIn("test_file.py", repo_map)

    def test_process_directory(self):
        """Test processing a directory."""
        repo_map, part_files = process_directory(
            directory=str(self.test_dir),
            extensions=['.py'],
            output_dir=str(self.output_dir),
            token_limit=4096,
            verbose=False,
            no_split=True
        )

        # Check that we got a result
        self.assertIsNotNone(repo_map)
        self.assertTrue(len(repo_map) > 0)

        # Check that we got at least one output file
        self.assertTrue(len(part_files) > 0)

        # Check that the output file exists
        self.assertTrue(os.path.exists(part_files[0]))

        # Check that the repository map contains the test file
        self.assertIn("test_file.py", repo_map)

    def test_get_file_symbols(self):
        """Test extracting symbols from a file."""
        symbols = get_file_symbols(str(self.test_file), verbose=False)

        # Check that we got symbols
        self.assertTrue(len(symbols) > 0)

        # Check that we got the expected symbols
        symbol_names = [symbol["name"] for symbol in symbols.values()]
        self.assertIn("test_function", symbol_names)
        self.assertIn("TestClass", symbol_names)


if __name__ == "__main__":
    unittest.main()
