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
from repomap.ast_parser import parse_file, parse_javascript, parse_python


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
    
    def test_parse_javascript(self):
        """Test parsing JavaScript files."""
        elements = parse_javascript(self.temp_js_file.name)
        
        # Check if we found the expected elements
        element_names = [e['name'] for e in elements]
        self.assertIn('TestClass', element_names)
        self.assertIn('testFunction', element_names)
        
        # At least one method should be found
        method_found = False
        for element in elements:
            if element['type'] == 'method' or element['type'] == 'arrow_function':
                method_found = True
                break
        self.assertTrue(method_found)
    
    def test_parse_python(self):
        """Test parsing Python files."""
        elements = parse_python(self.temp_py_file.name)
        
        # Check if we found the class and functions
        element_names = [e['name'] for e in elements]
        self.assertIn('TestClass', element_names)
        self.assertIn('standalone_function', element_names)
        
        # Check if methods were found
        method_found = False
        for element in elements:
            if element['type'] == 'method' and element['name'] == 'test_method':
                method_found = True
                break
        self.assertTrue(method_found)
    
    def test_parse_file_js(self):
        """Test parse_file with JavaScript."""
        elements = parse_file(self.temp_js_file.name, 'javascript')
        self.assertGreater(len(elements), 0)
        self.assertIn('TestClass', [e['name'] for e in elements])
    
    def test_parse_file_py(self):
        """Test parse_file with Python."""
        elements = parse_file(self.temp_py_file.name, 'python')
        self.assertGreater(len(elements), 0)
        self.assertIn('TestClass', [e['name'] for e in elements])
    
    def test_parse_file_extension(self):
        """Test parse_file infers language from extension."""
        elements = parse_file(self.temp_js_file.name, '.js')
        self.assertGreater(len(elements), 0)
        self.assertIn('TestClass', [e['name'] for e in elements])


if __name__ == "__main__":
    unittest.main()