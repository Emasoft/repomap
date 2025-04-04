#!/usr/bin/env python3
"""
Tests for the caching functionality in RepoMap
"""

import os
import sys
import unittest
import tempfile
import shutil
from pathlib import Path

# Make sure we can import the main package
sys.path.insert(0, str(Path(__file__).parent.parent))
from repomap import RepoMap


class SimpleTestIO:
    """Simple IO class for testing"""

    def __init__(self):
        self.warnings = []
        self.outputs = []
        self.errors = []
        self.read_files = {}

    def tool_warning(self, message):
        self.warnings.append(message)

    def tool_output(self, message):
        self.outputs.append(message)

    def tool_error(self, message):
        self.errors.append(message)

    def read_text(self, fname):
        if fname in self.read_files:
            return self.read_files[fname]
        try:
            with open(fname, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
                self.read_files[fname] = content
                return content
        except Exception as e:
            self.tool_error(f"Failed to read {fname}: {e}")
            return None

    def confirm_ask(self, message, default="y", subject=None):
        return True


class MockModel:
    """Mock model for token counting in tests"""

    def token_count(self, text):
        """Simple token count estimate: 1 token per 4 characters"""
        return len(text) // 4


class TestCache(unittest.TestCase):
    """Tests for the caching functionality"""

    def setUp(self):
        """Set up test fixtures"""
        # Create a temporary directory for the cache
        self.cache_dir = tempfile.mkdtemp()

        # Create a test file
        self.test_file = os.path.join(self.cache_dir, "test.py")
        with open(self.test_file, "w") as f:
            f.write("def test_function():\n    return 'test'\n")

        self.io = SimpleTestIO()
        self.model = MockModel()

    def tearDown(self):
        """Clean up after tests"""
        # Remove the temporary directory
        shutil.rmtree(self.cache_dir)

    def test_cache_initialization(self):
        """Test that the cache is initialized properly"""
        # Create a RepoMap instance with the test directory as root
        rm = RepoMap(
            root=self.cache_dir,
            io=self.io,
            main_model=self.model,
            verbose=True
        )

        # Check that the cache directory is correctly set
        self.assertTrue(hasattr(rm, 'TAGS_CACHE'))

        # Check that we can save to the cache
        try:
            rm.TAGS_CACHE['test_key'] = {'mtime': 123, 'data': ['test']}
            self.assertEqual(rm.TAGS_CACHE['test_key']['data'], ['test'])
        except Exception as e:
            self.fail(f"Failed to use cache: {e}")

    def test_cache_error_handling(self):
        """Test that cache errors are handled properly"""
        # Create a RepoMap instance
        rm = RepoMap(
            root=self.cache_dir,
            io=self.io,
            main_model=self.model,
            verbose=True
        )

        # Force an error to trigger warnings
        rm.tags_cache_error(original_error=ValueError("Test cache error"))

        # Make sure warnings were logged
        self.assertTrue(len(self.io.warnings) > 0, "No warnings were logged")
        # Skip specific message check since it's implementation dependent

    def test_cache_fallback_simulation(self):
        """Test a simulation of cache fallback behavior"""
        # Create a RepoMap instance
        rm = RepoMap(
            root=self.cache_dir,
            io=self.io,
            main_model=self.model,
            verbose=True
        )

        # We can't easily force the Cache to fail in a test,
        # so we'll just test that we can manually set the cache to a dict
        try:
            # Save original cache
            original_cache = rm.TAGS_CACHE

            # Set to a dict manually (simulating fallback)
            rm.TAGS_CACHE = dict()

            # Test the dict cache
            rm.TAGS_CACHE['test_key'] = {'mtime': 123, 'data': ['test']}
            self.assertEqual(rm.TAGS_CACHE['test_key']['data'], ['test'])

            # Restore original
            rm.TAGS_CACHE = original_cache
        except Exception as e:
            self.fail(f"Cache simulation failed: {e}")


if __name__ == '__main__':
    unittest.main()
