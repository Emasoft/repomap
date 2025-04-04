#!/usr/bin/env python3
"""
Comprehensive tests for the ast_parser.py module.
Tests all features including wildcards, code extraction, and output formats.
"""
import os
import sys
import unittest
import tempfile
import subprocess
from pathlib import Path
from unittest import mock
import json
import re

# Add parent directory to path to import repomap
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from repomap.ast_parser import (
    match_name_pattern,
    extract_line_range,
    find_nodes,
    format_code_with_line_numbers,
    process_file,
    print_results
)


class TestAstParserCore(unittest.TestCase):
    """Test the core functionality of ast_parser.py."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a sample Python file for testing
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_file_path = Path(self.temp_dir.name) / "test_sample.py"
        
        with open(self.test_file_path, 'w', encoding='utf-8') as f:
            f.write("""#!/usr/bin/env python3
\"\"\"Sample module for testing.\"\"\"
import sys
from typing import List, Dict, Optional

# Constants
MAX_VALUE = 100
MIN_VALUE = 0

# Global variable
counter = 0

class TestClass:
    \"\"\"A test class with methods.\"\"\"
    
    # Class attribute
    class_attr = 42
    
    def __init__(self, name, value=0):
        \"\"\"Initialize with name and value.\"\"\"
        self.name = name
        self.value = value
    
    def get_value(self):
        \"\"\"Return the value.\"\"\"
        return self.value
    
    @property
    def info(self):
        \"\"\"Return information.\"\"\"
        return f"{self.name}: {self.value}"

def sample_function(x, y):
    \"\"\"Sample function that adds two numbers.\"\"\"
    return x + y

# Some code outside functions
if __name__ == "__main__":
    obj = TestClass("Test", 10)
    print(obj.info)
""")

        # Path to the ast_parser.py script
        self.ast_parser_path = Path(__file__).parent.parent / "ast_parser.py"
        
    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()
        
    def test_match_name_pattern(self):
        """Test pattern matching with wildcards."""
        # Exact matches
        self.assertTrue(match_name_pattern("sample_function", "sample_function"))
        self.assertTrue(match_name_pattern("TestClass", "TestClass"))
        
        # Wildcard matches
        self.assertTrue(match_name_pattern("sample_function", "*function"))
        self.assertTrue(match_name_pattern("sample_function", "sample_*"))
        self.assertTrue(match_name_pattern("sample_function", "*_*"))
        self.assertTrue(match_name_pattern("sample_function", "sample?function"))
        self.assertTrue(match_name_pattern("TestClass", "Test*"))
        
        # Non-matches
        self.assertFalse(match_name_pattern("sample_function", "other_function"))
        self.assertFalse(match_name_pattern("sample_function", "sample"))
        self.assertFalse(match_name_pattern("TestClass", "Class"))
        
        # Match all pattern
        self.assertTrue(match_name_pattern("anything", "*"))
        
    def test_extract_line_range(self):
        """Test extracting line ranges from source code."""
        # Create a simple source with 10 lines
        source_lines = [f"Line {i}\n" for i in range(1, 11)]
        
        # Test with a dictionary node
        node_dict = {'lineno': 3, 'end_lineno': 6}
        start, end, lines = extract_line_range(node_dict, source_lines)
        self.assertEqual(start, 3)
        self.assertEqual(end, 6)
        self.assertEqual(lines, source_lines[2:6])
        
        # Test with context lines
        start, end, lines = extract_line_range(node_dict, source_lines, context_lines=2)
        self.assertEqual(start, 1)
        self.assertEqual(end, 8)
        self.assertEqual(lines, source_lines[0:8])
        
        # Test with limiting context at boundaries
        node_dict = {'lineno': 1, 'end_lineno': 3}
        start, end, lines = extract_line_range(node_dict, source_lines, context_lines=2)
        self.assertEqual(start, 1)
        self.assertEqual(end, 5)
        self.assertEqual(lines, source_lines[0:5])
        
        node_dict = {'lineno': 8, 'end_lineno': 10}
        start, end, lines = extract_line_range(node_dict, source_lines, context_lines=2)
        self.assertEqual(start, 6)
        self.assertEqual(end, 10)
        self.assertEqual(lines, source_lines[5:10])
        
    def test_format_code_with_line_numbers(self):
        """Test formatting code with line numbers."""
        code_lines = ["def example():\n", "    return True\n"]
        
        # Without line numbers
        formatted = format_code_with_line_numbers(code_lines, 1, add_line_numbers=False)
        self.assertEqual(formatted, "def example():\n    return True\n")
        
        # With line numbers
        formatted = format_code_with_line_numbers(code_lines, 1, add_line_numbers=True)
        self.assertEqual(formatted, "1 〉def example():\n2 〉    return True\n")
        
        # With higher starting line number
        formatted = format_code_with_line_numbers(code_lines, 10, add_line_numbers=True)
        self.assertEqual(formatted, "10 〉def example():\n11 〉    return True\n")
        
        # With three-digit line numbers (ensure padding works)
        formatted = format_code_with_line_numbers(code_lines, 100, add_line_numbers=True)
        self.assertEqual(formatted, "100 〉def example():\n101 〉    return True\n")
        
    def test_find_nodes_callable(self):
        """Test finding callable nodes in source code."""
        with open(self.test_file_path, 'r', encoding='utf-8') as f:
            source = f.read()
            
        # Find all callable nodes
        nodes = find_nodes(source, str(self.test_file_path), name_pattern="*")
        
        # Check that we found the expected callable nodes
        node_names = [node['name'] for node in nodes]
        self.assertIn("TestClass", node_names)
        self.assertIn("__init__", node_names)
        self.assertIn("get_value", node_names)
        self.assertIn("info", node_names)
        self.assertIn("sample_function", node_names)
        
        # Check that we didn't find non-callable nodes
        self.assertNotIn("MAX_VALUE", node_names)
        self.assertNotIn("counter", node_names)
        
        # Check specific pattern
        nodes = find_nodes(source, str(self.test_file_path), name_pattern="get*")
        node_names = [node['name'] for node in nodes]
        self.assertEqual(len(nodes), 1)
        self.assertIn("get_value", node_names)
        
    def test_find_nodes_non_callable(self):
        """Test finding non-callable nodes in source code."""
        with open(self.test_file_path, 'r', encoding='utf-8') as f:
            source = f.read()
            
        # Find all nodes including non-callables
        nodes = find_nodes(
            source, 
            str(self.test_file_path), 
            name_pattern="*", 
            include_non_callables=True
        )
        
        # Check that we found the non-callable nodes
        node_names = [node['name'] for node in nodes]
        self.assertIn("MAX_VALUE", node_names)
        self.assertIn("MIN_VALUE", node_names)
        self.assertIn("counter", node_names)
        self.assertIn("sys", node_names)
        self.assertIn("Optional", node_names)
        
        # Check specific pattern for non-callables
        nodes = find_nodes(
            source, 
            str(self.test_file_path), 
            name_pattern="*VALUE", 
            include_non_callables=True
        )
        node_names = [node['name'] for node in nodes]
        self.assertEqual(len(nodes), 2)
        self.assertIn("MAX_VALUE", node_names)
        self.assertIn("MIN_VALUE", node_names)
        
    def test_process_file(self):
        """Test the process_file function with various options."""
        # Basic processing with default options
        results = process_file(str(self.test_file_path), name_pattern="TestClass")
        self.assertIn('results', results)
        self.assertEqual(len(results['results']), 1)
        self.assertEqual(results['results'][0]['name'], "TestClass")
        
        # With line numbers only
        results = process_file(
            str(self.test_file_path), 
            name_pattern="*", 
            line_numbers_only=True
        )
        self.assertIn('results', results)
        for result in results['results']:
            self.assertIn('name', result)
            self.assertIn('type', result)
            self.assertIn('start_line', result)
            self.assertIn('end_line', result)
            
        # With get code
        results = process_file(
            str(self.test_file_path), 
            name_pattern="sample_function", 
            get_code=True
        )
        self.assertIn('results', results)
        self.assertEqual(len(results['results']), 1)
        self.assertIn('code', results['results'][0])
        self.assertIn('def sample_function', results['results'][0]['code'])
        
        # With non-callables
        results = process_file(
            str(self.test_file_path), 
            name_pattern="MAX_VALUE", 
            include_non_callables=True
        )
        self.assertIn('results', results)
        self.assertEqual(len(results['results']), 1)
        self.assertEqual(results['results'][0]['name'], "MAX_VALUE")
        self.assertEqual(results['results'][0]['type'], "Variable")
        self.assertFalse(results['results'][0]['is_callable'])


class TestAstParserCLI(unittest.TestCase):
    """Test the command-line interface of ast_parser.py."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a sample Python file for testing
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_file_path = Path(self.temp_dir.name) / "test_sample.py"
        
        with open(self.test_file_path, 'w', encoding='utf-8') as f:
            f.write("""#!/usr/bin/env python3
\"\"\"Sample module for testing.\"\"\"
import sys
from typing import List, Dict, Optional

# Constants
MAX_VALUE = 100
MIN_VALUE = 0

# Global variable
counter = 0

class TestClass:
    \"\"\"A test class with methods.\"\"\"
    
    # Class attribute
    class_attr = 42
    
    def __init__(self, name, value=0):
        \"\"\"Initialize with name and value.\"\"\"
        self.name = name
        self.value = value
    
    def get_value(self):
        \"\"\"Return the value.\"\"\"
        return self.value
    
    @property
    def info(self):
        \"\"\"Return information.\"\"\"
        return f"{self.name}: {self.value}"

def sample_function(x, y):
    \"\"\"Sample function that adds two numbers.\"\"\"
    return x + y

# Some code outside functions
if __name__ == "__main__":
    obj = TestClass("Test", 10)
    print(obj.info)
""")

        # Path to the ast_parser.py script
        self.ast_parser_path = Path(__file__).parent.parent / "ast_parser.py"
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()
        
    def run_ast_parser(self, *args):
        """Run the ast_parser.py script with the given arguments."""
        cmd = [sys.executable, str(self.ast_parser_path), str(self.test_file_path)] + list(args)
        result = subprocess.run(cmd, 
                               capture_output=True, 
                               text=True,
                               check=False)
        return result
    
    def test_cli_basic(self):
        """Test basic CLI operation."""
        # Test finding a specific function
        result = self.run_ast_parser("sample_function")
        self.assertEqual(result.returncode, 0)
        self.assertIn("Found Callable 'sample_function'", result.stdout)
        
        # Test wildcard pattern
        result = self.run_ast_parser("*", "--line-numbers-only")
        self.assertEqual(result.returncode, 0)
        self.assertIn("TestClass (ClassDef)", result.stdout)
        self.assertIn("sample_function (FunctionDef)", result.stdout)
        
        # Test non-existent function
        result = self.run_ast_parser("nonexistent_function")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Callable 'nonexistent_function' not found", result.stdout)
        
    def test_cli_non_callables(self):
        """Test --non-callables option."""
        result = self.run_ast_parser("MAX_VALUE", "--non-callables")
        self.assertEqual(result.returncode, 0)
        self.assertIn("Found Variable 'MAX_VALUE'", result.stdout)
        
        result = self.run_ast_parser("*_VALUE", "--non-callables", "--line-numbers-only")
        self.assertEqual(result.returncode, 0)
        self.assertIn("MAX_VALUE (Variable)", result.stdout)
        self.assertIn("MIN_VALUE (Variable)", result.stdout)
        
    def test_cli_get_code(self):
        """Test --get-code option."""
        result = self.run_ast_parser("sample_function", "--get-code")
        self.assertEqual(result.returncode, 0)
        self.assertIn("def sample_function(x, y):", result.stdout)
        self.assertIn("\"\"\"Sample function that adds two numbers.\"\"\"", result.stdout)
        self.assertIn("return x + y", result.stdout)
        
    def test_cli_add_context(self):
        """Test --add-context option."""
        # Default context (10 lines)
        result = self.run_ast_parser("sample_function", "--get-code", "--add-context")
        self.assertEqual(result.returncode, 0)
        line_count = result.stdout.count('\n')
        self.assertGreater(line_count, 5)  # More lines than just the function
        
        # Custom context (2 lines)
        result = self.run_ast_parser("sample_function", "--get-code", "--add-context", "10")
        self.assertEqual(result.returncode, 0)
        # Should include function + lines before/after (with enough context to reach "info")
        # The function is at the end of the file, so we check for content that occurs earlier
        self.assertIn("def info", result.stdout)  # The property getter function defined earlier
        # Check that we also get content that comes after
        self.assertIn("# Some code outside functions", result.stdout)
        
    def test_cli_add_line_numbers(self):
        """Test --add-line-numbers option."""
        result = self.run_ast_parser("sample_function", "--get-code", "--add-line-numbers")
        self.assertEqual(result.returncode, 0)
        # Should have line numbers
        line_number_pattern = r'\d+ 〉'
        self.assertTrue(re.search(line_number_pattern, result.stdout))
        
    def test_cli_signature_only(self):
        """Test --signature-only option."""
        result = self.run_ast_parser("sample_function", "--signature-only")
        self.assertEqual(result.returncode, 0)
        # Should include function declaration but not the whole function body
        self.assertIn("def sample_function(x, y):", result.stdout)
        # Should include the docstring but not the return statement
        self.assertIn("\"\"\"Sample function that adds two numbers.\"\"\"", result.stdout)
        self.assertNotIn("return x + y", result.stdout)
        
        # The output should contain the function declaration and docstring
        # but not the implementation
        self.assertIn("def sample_function", result.stdout)
        self.assertIn("Sample function that adds two numbers", result.stdout)
        
    def test_cli_combined_options(self):
        """Test combining multiple CLI options."""
        result = self.run_ast_parser(
            "*", 
            "--non-callables", 
            "--get-code", 
            "--add-context", "3",
            "--add-line-numbers"
        )
        self.assertEqual(result.returncode, 0)
        
        # Should contain line numbers
        line_number_pattern = r'\d+ 〉'
        self.assertTrue(re.search(line_number_pattern, result.stdout))
        
        # Should contain both callables and non-callables
        self.assertIn("TestClass", result.stdout)
        self.assertIn("MAX_VALUE", result.stdout)
        
    def test_cli_backward_compatibility(self):
        """Test backward compatibility with section_splitting.py."""
        # The original format was: ast_parser.py file.py function_name
        result = self.run_ast_parser("sample_function")
        self.assertEqual(result.returncode, 0)
        # Should output a single line with the matching callable
        output_lines = result.stdout.strip().split('\n')
        self.assertTrue(any("Found Callable 'sample_function' at lines" in line 
                          for line in output_lines))


if __name__ == "__main__":
    unittest.main()