#!/usr/bin/env python3
"""
Comprehensive tests for the io_utils module.
"""
import sys
import unittest
from unittest import mock
from pathlib import Path
import tempfile
import os
import io

# Add parent directory to path to import repomap
sys.path.insert(0, str(Path(__file__).parent.parent))
from repomap.io_utils import InputOutput, default_io


class TestInputOutput(unittest.TestCase):
    """Tests for the InputOutput class in io_utils.py."""

    def test_initialization(self):
        """Test InputOutput initialization."""
        # Test default initialization
        io_handler = InputOutput()
        self.assertIsNotNone(io_handler)
        self.assertEqual(io_handler.stdout, sys.stdout)
        self.assertEqual(io_handler.stderr, sys.stderr)
        self.assertFalse(io_handler.quiet)
        
        # Test with custom streams and quiet flag
        stdout = io.StringIO()
        stderr = io.StringIO()
        io_handler = InputOutput(stdout=stdout, stderr=stderr, quiet=True)
        self.assertEqual(io_handler.stdout, stdout)
        self.assertEqual(io_handler.stderr, stderr)
        self.assertTrue(io_handler.quiet)
    
    def test_output_methods(self):
        """Test various output methods."""
        stdout = io.StringIO()
        stderr = io.StringIO()
        io_handler = InputOutput(stdout=stdout, stderr=stderr)
        
        # Test tool_output
        io_handler.tool_output("Info message")
        self.assertEqual(stdout.getvalue(), "Info message\n")
        self.assertEqual(stderr.getvalue(), "")
        
        # Reset buffers
        stdout = io.StringIO()
        stderr = io.StringIO()
        io_handler = InputOutput(stdout=stdout, stderr=stderr)
        
        # Test tool_warning
        io_handler.tool_warning("Warning message")
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "WARNING: Warning message\n")
        
        # Reset buffers
        stdout = io.StringIO()
        stderr = io.StringIO()
        io_handler = InputOutput(stdout=stdout, stderr=stderr)
        
        # Test tool_error
        io_handler.tool_error("Error message")
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "ERROR: Error message\n")
        
        # Test quiet mode
        stdout = io.StringIO()
        stderr = io.StringIO()
        io_handler = InputOutput(stdout=stdout, stderr=stderr, quiet=True)
        
        io_handler.tool_output("Should be suppressed")
        self.assertEqual(stdout.getvalue(), "")  # Output should be suppressed
        
        io_handler.tool_error("Error still shows")
        self.assertEqual(stderr.getvalue(), "ERROR: Error still shows\n")  # Errors still show
    
    def test_confirm_ask(self):
        """Test confirm_ask method."""
        # In the CLI version, confirm_ask always returns True
        io_handler = InputOutput()
        self.assertTrue(io_handler.confirm_ask("Continue?"))
        self.assertTrue(io_handler.confirm_ask("Continue?", default="n"))
        self.assertTrue(io_handler.confirm_ask("Continue?", subject="Operation"))
    
    def test_read_text(self):
        """Test read_text method."""
        # Create a temporary test file
        with tempfile.NamedTemporaryFile(delete=False, mode="w", encoding="utf-8") as f:
            f.write("Test content")
            temp_path = f.name
        
        try:
            io_handler = InputOutput()
            
            # Test reading existing file
            content = io_handler.read_text(temp_path)
            self.assertEqual(content, "Test content")
            
            # Test file caching
            # Modify the file after it's been cached
            with open(temp_path, "w", encoding="utf-8") as f:
                f.write("Modified content")
            
            # Should still return the cached content
            cached_content = io_handler.read_text(temp_path)
            self.assertEqual(cached_content, "Test content")
            
            # Test reading non-existent file
            stderr = io.StringIO()
            io_handler = InputOutput(stderr=stderr)
            content = io_handler.read_text("/nonexistent/path")
            self.assertIsNone(content)
            self.assertTrue("ERROR: Failed to read" in stderr.getvalue())
        
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_write_text(self):
        """Test write_text method."""
        # Create a temporary path
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.txt")
            nested_path = os.path.join(temp_dir, "nested", "test.txt")
            
            io_handler = InputOutput()
            
            # Test writing to file
            result = io_handler.write_text(file_path, "Test content")
            self.assertTrue(result)
            
            # Verify file was written
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                self.assertEqual(content, "Test content")
            
            # Test writing to nested path (should create directories)
            result = io_handler.write_text(nested_path, "Nested content")
            self.assertTrue(result)
            
            # Verify nested file was written
            with open(nested_path, "r", encoding="utf-8") as f:
                content = f.read()
                self.assertEqual(content, "Nested content")
            
            # Test writing with error
            stderr = io.StringIO()
            io_handler = InputOutput(stderr=stderr)
            
            # Create a scenario that will cause an error (try to write to a directory)
            nested_dir = os.path.join(temp_dir, "cant_write_here")
            os.makedirs(nested_dir, exist_ok=True)
            
            # Mock open to raise an exception
            with mock.patch("builtins.open", side_effect=IOError("Permission denied")):
                result = io_handler.write_text(nested_dir, "This will fail")
                self.assertFalse(result)
                self.assertTrue("ERROR: Failed to write" in stderr.getvalue())
    
    def test_list_files(self):
        """Test list_files method."""
        # Create a temporary directory with various files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create some files with different extensions
            py_file = os.path.join(temp_dir, "test.py")
            js_file = os.path.join(temp_dir, "test.js")
            txt_file = os.path.join(temp_dir, "test.txt")
            
            # Create a nested directory with a file
            nested_dir = os.path.join(temp_dir, "nested")
            os.makedirs(nested_dir, exist_ok=True)
            nested_py_file = os.path.join(nested_dir, "nested.py")
            
            # Create all the files
            for file_path in [py_file, js_file, txt_file, nested_py_file]:
                with open(file_path, "w") as f:
                    f.write(f"Content of {os.path.basename(file_path)}")
            
            io_handler = InputOutput()
            
            # Test listing all files recursively
            all_files = io_handler.list_files(temp_dir)
            self.assertEqual(len(all_files), 4)
            self.assertTrue(any(f.endswith("test.py") for f in all_files))
            self.assertTrue(any(f.endswith("nested.py") for f in all_files))
            
            # Test listing with specific extensions
            py_files = io_handler.list_files(temp_dir, extensions=[".py"])
            self.assertEqual(len(py_files), 2)
            self.assertTrue(all(f.endswith(".py") for f in py_files))
            
            # Test non-recursive listing
            top_files = io_handler.list_files(temp_dir, recursive=False)
            self.assertEqual(len(top_files), 3)  # Should include only files in the top directory
            self.assertFalse(any(f.endswith("nested.py") for f in top_files))
            
            # Test listing from non-existent directory
            stderr = io.StringIO()
            io_handler = InputOutput(stderr=stderr)
            no_files = io_handler.list_files("/nonexistent/path")
            self.assertEqual(len(no_files), 0)
            self.assertTrue("WARNING: Directory does not exist" in stderr.getvalue())
            
            # Test error during listing
            stderr = io.StringIO()
            io_handler = InputOutput(stderr=stderr)
            with mock.patch("os.walk", side_effect=PermissionError("Permission denied")):
                no_files = io_handler.list_files(temp_dir)
                self.assertEqual(len(no_files), 0)
                self.assertTrue("ERROR: Error listing files" in stderr.getvalue())
    
    def test_default_io_instance(self):
        """Test that default_io is an instance of InputOutput."""
        self.assertIsInstance(default_io, InputOutput)


if __name__ == "__main__":
    unittest.main()