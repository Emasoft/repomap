#!/usr/bin/env python3
"""
Tests for the ast_parser module.
"""
import unittest
import os
import tempfile
import sys
from pathlib import Path

# Add parent directory to path to import repomap
sys.path.insert(0, str(Path(__file__).parent.parent))
from repomap.ast_parser import process_file


class TestAstParser(unittest.TestCase):
    """Tests for the ast_parser module."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temporary test files
        self.temp_js_file = tempfile.NamedTemporaryFile(suffix='.js', delete=False)
        self.temp_js_file.write(b"""
class TestClass {
    constructor(name) {
        this.name = name;
    }
    
    initialize() {
        console.log('Initializing component');
    }
    
    static getCount() {
        return TestClass.count;
    }
}

function testFunction() {
    return "test";
}

const arrowFunc = () => {
    return "arrow function";
};
""")
        self.temp_js_file.close()
        
        self.temp_py_file = tempfile.NamedTemporaryFile(suffix='.py', delete=False)
        self.temp_py_file.write(b"""
class TestClass:
    def __init__(self):
        self.value = 0
        
    def test_method(self):
        return self.value
        
    @classmethod
    def from_value(cls, value):
        return cls()
        
def standalone_function():
    return "test"
""")
        self.temp_py_file.close()
    
    def tearDown(self):
        """Tear down test fixtures."""
        # Remove temporary files
        os.unlink(self.temp_js_file.name)
        os.unlink(self.temp_py_file.name)
    
    def test_parse_javascript_returns_error(self):
        """Test that JavaScript files are no longer supported by the ast_parser module."""
        result = process_file(self.temp_js_file.name)
        self.assertIn('error', result)
        
    def test_parse_python(self):
        """Test parsing Python files."""
        result = process_file(self.temp_py_file.name)
        
        # Make sure we get results and not an error
        self.assertIn('results', result)
        
        # Check if we found the class
        element_names = [e['name'] for e in result['results']]
        self.assertIn('TestClass', element_names)
        
        # Check if methods were found
        method_found = False
        for element in result['results']:
            if element['type'] == 'FunctionDef' and element['name'] == 'test_method':
                method_found = True
                break
        self.assertTrue(method_found)
    
    def test_parse_file_non_python(self):
        """Test process_file with non-Python file returns error."""
        result = process_file(self.temp_js_file.name)
        self.assertIn('error', result)
    
    def test_parse_file_py(self):
        """Test process_file with Python file."""
        result = process_file(self.temp_py_file.name)
        self.assertIn('results', result)
        self.assertGreater(len(result['results']), 0)
        element_names = [e['name'] for e in result['results']]
        self.assertIn('TestClass', element_names)
        # Verify the elements have the required attributes
        for element in result['results']:
            if element['name'] == 'TestClass':
                self.assertTrue('start_line' in element)
                self.assertTrue('end_line' in element)
        
    def test_cli_interface(self):
        """Test the CLI interface with specific function names."""
        import subprocess
        
        # Test with a specific function name
        cmd = [sys.executable, self.temp_py_file.name, "TestClass"]
        result = subprocess.run(
            [sys.executable, os.path.join(Path(__file__).parent.parent, "repomap", "ast_parser.py"), 
             self.temp_py_file.name, "TestClass"],
            capture_output=True, text=True
        )
        
        # Check if the output matches what section_splitting.py expects
        self.assertEqual(result.returncode, 0)
        self.assertIn("Found Callable 'TestClass' at lines", result.stdout)


if __name__ == "__main__":
    unittest.main()
