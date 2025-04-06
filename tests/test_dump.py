#!/usr/bin/env python3
"""
Tests for the dump module.
"""
import sys
import unittest
from unittest import mock
from pathlib import Path
import json

# Add parent directory to path to import repomap
sys.path.insert(0, str(Path(__file__).parent.parent))
from repomap.dump import dump, cvt


class TestDump(unittest.TestCase):
    """Tests for the dump module."""

    def test_cvt_with_string(self):
        """Test cvt function with a string input."""
        result = cvt("test string")
        self.assertEqual(result, "test string")

    def test_cvt_with_json_serializable(self):
        """Test cvt function with a JSON serializable object."""
        test_dict = {"name": "test", "values": [1, 2, 3]}
        result = cvt(test_dict)
        # Verify it creates properly formatted JSON
        self.assertEqual(result, json.dumps(test_dict, indent=4))
        
        # Test with a list
        test_list = [1, 2, {"nested": True}]
        result = cvt(test_list)
        self.assertEqual(result, json.dumps(test_list, indent=4))

    def test_cvt_with_non_serializable(self):
        """Test cvt function with a non-JSON serializable object."""
        # Create an object that isn't JSON serializable
        class TestObj:
            def __str__(self):
                return "TestObj instance"
        
        test_obj = TestObj()
        result = cvt(test_obj)
        self.assertEqual(result, str(test_obj))
        
    def test_cvt_with_exception(self):
        """Test cvt function with an object that raises an exception during JSON serialization."""
        # Create an object that will raise an exception during JSON serialization
        class CircularRef:
            def __init__(self):
                self.ref = self
                
        circular = CircularRef()
        result = cvt(circular)
        self.assertEqual(result, str(circular))

    @mock.patch("builtins.print")
    def test_dump_with_single_line_output(self, mock_print):
        """Test dump function with values that produce single line output."""
        # Call dump with a simple string that won't have newlines
        dump("simple value")
        
        # Verify print was called with the right format
        # The first argument to print should contain the variable name from the call site
        mock_print.assert_called_once()
        args = mock_print.call_args[0]
        self.assertIn("simple value", args[1])
        
        # Verify the variable name extraction
        self.assertTrue(args[0].endswith(":"))

    @mock.patch("builtins.print")
    def test_dump_with_multi_line_output(self, mock_print):
        """Test dump function with values that produce multi-line output."""
        # Call dump with a complex structure that will have newlines
        dump({"multi": "line", "output": [1, 2, 3]})
        
        # Verify print was called twice - once for variable name, once for content
        self.assertEqual(mock_print.call_count, 2)
        
        # First call should contain just the variable name
        first_call = mock_print.call_args_list[0][0][0]
        self.assertTrue(first_call.endswith(":"))
        
        # Second call should contain the JSON representation
        second_call = mock_print.call_args_list[1][0][0]
        self.assertIn("multi", second_call)
        self.assertIn("line", second_call)

    @mock.patch("builtins.print")
    def test_dump_with_multiple_values(self, mock_print):
        """Test dump function with multiple values."""
        # Call dump with multiple values
        dump("value1", "value2", 123)
        
        # Verify print was called once with all values
        mock_print.assert_called_once()
        args = mock_print.call_args[0]
        self.assertIn("value1", args[1])
        self.assertIn("value2", args[1])
        self.assertIn("123", args[1])


if __name__ == "__main__":
    unittest.main()
