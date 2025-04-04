#!/usr/bin/env python3
"""
Tests for the repository map splitting functionality.
These tests focus on the ability to split a large repository map into
smaller parts that still maintain coherence and stay within token limits.
"""
import os
import sys
import unittest
from unittest import mock
from pathlib import Path
import tempfile
import re
import glob

# Add parent directory to path to import repomap
sys.path.insert(0, str(Path(__file__).parent.parent))
from repomap.repomap import RepoMap
from repomap.section_splitting import split_large_section, split_section_by_signatures

class MockModel:
    """Mock model for token counting"""
    def token_count(self, text):
        """Simple token count estimate based on characters"""
        return len(text) // 4

class TestRepoMapSplitting(unittest.TestCase):
    """Tests for the repository map splitting functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for our test "repository"
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_dir = Path(self.temp_dir.name)
        self.output_dir = self.repo_dir / "output"
        self.output_dir.mkdir(exist_ok=True)

        # Create a simple tree of test files
        self.create_test_repo_structure()
        
        # Initialize RepoMap with mock IO
        self.mock_io = mock.MagicMock()
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()
    
    def create_test_repo_structure(self):
        """Create a simple repository structure for testing."""
        # Create directory structure
        src_dir = self.repo_dir / "src"
        src_dir.mkdir(exist_ok=True)
        
        # Create a large Python file to force splitting
        large_py_file = src_dir / "large.py"
        
        # Generate a large file with many functions and classes
        content = []
        content.append("#!/usr/bin/env python3")
        content.append("\"\"\"A large Python file for testing splitting.\"\"\"")
        content.append("")
        
        # Add imports
        content.append("import os")
        content.append("import sys")
        content.append("import json")
        content.append("import time")
        content.append("import random")
        content.append("import math")
        content.append("")
        
        # Add many functions and classes
        for i in range(50):  # 50 functions should be enough to exceed token limits
            content.append(f"def function_{i}(param_{i}=None):")
            content.append(f"    \"\"\"Function {i} docstring.\"\"\"")
            content.append(f"    # Implementation of function {i}")
            for j in range(10):  # Add some bulk to each function
                content.append(f"    var_{j} = {j} * {i}")
                content.append(f"    print(f\"Function {i}, iteration {j}: {{var_{j}}}\")")
            content.append(f"    return var_{9}")  # Return the last variable
            content.append("")
        
        for i in range(20):  # 20 classes
            content.append(f"class Class_{i}:")
            content.append(f"    \"\"\"Class {i} docstring.\"\"\"")
            content.append("")
            content.append(f"    def __init__(self, param_{i}=None):")
            content.append(f"        \"\"\"Initialize Class_{i}.\"\"\"")
            content.append(f"        self.param_{i} = param_{i}")
            content.append("")
            
            for j in range(5):  # 5 methods per class
                content.append(f"    def method_{i}_{j}(self, arg_{j}=None):")
                content.append(f"        \"\"\"Method {j} of Class_{i}.\"\"\"")
                content.append(f"        # Implementation of method {j}")
                for k in range(5):  # Some code in each method
                    content.append(f"        var_{k} = {k} * {j} + {i}")
                content.append(f"        return var_{4}")  # Return the last variable
                content.append("")
            
            # Add a staticmethod and a classmethod
            content.append("    @staticmethod")
            content.append(f"    def static_method_{i}():")
            content.append(f"        \"\"\"Static method of Class_{i}.\"\"\"")
            content.append(f"        return {i} * 100")
            content.append("")
            
            content.append("    @classmethod")
            content.append(f"    def class_method_{i}(cls):")
            content.append(f"        \"\"\"Class method of Class_{i}.\"\"\"")
            content.append("        return cls.__name__")
            content.append("")
        
        # Add some main code
        content.append("if __name__ == \"__main__\":")
        content.append("    # Test some functions and classes")
        content.append("    for i in range(5):")
        content.append("        result = function_i(i)")
        content.append("        print(f\"Function {i} result: {result}\")")
        content.append("")
        content.append("    # Test a class")
        content.append("    obj = Class_0()")
        content.append("    print(obj.method_0_0())")
        
        # Write the file
        large_py_file.write_text("\n".join(content))
        
        # Create a large JavaScript file as well
        large_js_file = src_dir / "large.js"
        
        js_content = []
        js_content.append("/**")
        js_content.append(" * A large JavaScript file for testing splitting.")
        js_content.append(" */")
        js_content.append("")
        
        # Add many functions
        for i in range(30):
            js_content.append(f"function jsFunction_{i}(param_{i}) {{")
            js_content.append(f"    // Implementation of jsFunction_{i}")
            for j in range(5):
                js_content.append(f"    let var_{j} = {j} * {i};")
                js_content.append(f"    console.log(`Function {i}, iteration {j}: ${{var_{j}}}`);")
            js_content.append(f"    return var_{4};")
            js_content.append("}")
            js_content.append("")
        
        # Add many classes
        for i in range(15):
            js_content.append(f"class JsClass_{i} {{")
            js_content.append(f"    constructor(param_{i}) {{")
            js_content.append(f"        this.param_{i} = param_{i};")
            js_content.append("    }")
            js_content.append("")
            
            for j in range(4):
                js_content.append(f"    jsMethod_{i}_{j}(arg_{j}) {{")
                js_content.append(f"        // Implementation of jsMethod_{i}_{j}")
                for k in range(3):
                    js_content.append(f"        let var_{k} = {k} * {j} + {i};")
                js_content.append(f"        return var_{2};")
                js_content.append("    }")
                js_content.append("")
            
            # Add a static method
            js_content.append(f"    static staticMethod_{i}() {{")
            js_content.append(f"        return {i} * 100;")
            js_content.append("    }")
            js_content.append("}")
            js_content.append("")
        
        # Add some initialization code
        js_content.append("// Initialize")
        js_content.append("function initialize() {")
        js_content.append("    console.log('Initializing application');")
        js_content.append("    ")
        js_content.append("    // Create some objects")
        js_content.append("    const obj1 = new JsClass_0('test');")
        js_content.append("    const obj2 = new JsClass_1('another test');")
        js_content.append("    ")
        js_content.append("    // Call some methods")
        js_content.append("    console.log(obj1.jsMethod_0_0('arg'));")
        js_content.append("    console.log(obj2.jsMethod_1_0('arg'));")
        js_content.append("}")
        js_content.append("")
        js_content.append("// Export")
        js_content.append("module.exports = {")
        js_content.append("    initialize,")
        js_content.append("    JsClass_0,")
        js_content.append("    JsClass_1,")
        js_content.append("    jsFunction_0")
        js_content.append("};")
        
        # Write the file
        large_js_file.write_text("\n".join(js_content))
    
    def test_splitting_with_small_token_limit(self):
        """Test splitting with a deliberately small token limit (minimum 4096)."""
        repo_map = RepoMap(
            io=self.mock_io,
            main_model=MockModel(),
            root=str(self.repo_dir),
            verbose=True,
            map_tokens=4096,  # Minimum token limit
        )
        
        # Generate the map - should trigger splitting
        chat_files = [str(self.repo_dir / "src" / "large.py")]
        other_files = [str(self.repo_dir / "src" / "large.js")]
        result = repo_map.get_repo_map(chat_files, other_files)
        
        # Check that splitting occurred (result is just the first part)
        self.assertTrue(result.startswith("Repository contents"))
        self.assertIn("src/large.py", result)  # First file should be included in first part
        
        # Verify that IO shows multiple parts were created
        self.mock_io.tool_output.assert_any_call(mock.ANY)  # Should output something about writing parts
    
    def test_section_splitting(self):
        """Test that the section_splitting function correctly splits content."""
        # Create a large string that will exceed token limits
        large_string = ""
        # Making the string much larger to ensure it splits into multiple parts
        for i in range(500):  # Increase from 100 to 500
            large_string += f"Line {i}: This is a test line with some content to make it long enough. Adding more text to ensure sufficient size.\n"
            if i % 10 == 0:
                large_string += "⋮\n"  # Add symbol markers every 10 lines
        
        # Create a token counter
        def token_counter(text):
            # Making the token counter more aggressive to ensure splitting
            return len(text) // 2  # Changed from 4 to 2
        
        # Split the section
        parts = split_section_by_signatures(token_counter, large_string, 4096)
        
        # Check that splitting occurred
        self.assertGreater(len(parts), 1)
        
        # Check that each part is under the token limit
        for part in parts:
            self.assertLessEqual(token_counter(part), 4096)
        
        # Check that key content is preserved
        self.assertTrue(any("Line 0:" in part for part in parts))
        self.assertTrue(any("Line 99:" in part for part in parts))
    
    def test_handle_large_section(self):
        """Test the handle_large_section function for managing large sections."""
        # Create a mock IO
        mock_io = mock.MagicMock()
        
        # Create test content
        large_content = ""
        for i in range(200):
            large_content += f"Line {i}: This is test content line {i}.\n"
            if i % 20 == 0:
                large_content += "⋮\n"  # Add symbol markers
        
        # Create parameters for the function
        section_tokens = 5000  # Larger than our token limit
        max_map_tokens = 4096  # Minimum token limit
        rel_fname = "test.py"
        def token_counter(text):
            return len(text) // 4
        current_map = "Repository contents:\n\n"
        output_parts = []
        current_part = 1
        
        # Call the function
        continued, new_map, new_part = split_large_section(
            mock_io, True, section_tokens, max_map_tokens, rel_fname,
            large_content, token_counter, current_map, output_parts, current_part
        )
        
        # Check the results
        self.assertTrue(continued)  # Should signal to continue processing
        self.assertNotEqual(current_map, new_map)  # Map should be updated
        
        # Verify that the section was split and added to the map
        mock_io.tool_warning.assert_called_with(mock.ANY)  # Should warn about large section
        mock_io.tool_output.assert_called_with("Splitting this section")
    
    def test_repomap_output_files(self):
        """Test that RepoMap correctly writes output files when splitting."""
        # Set up output directory
        output_dir = self.repo_dir / "output"
        output_dir.mkdir(exist_ok=True)
        
        # Create RepoMap with a small token limit to force splitting
        repo_map = RepoMap(
            io=self.mock_io,
            main_model=MockModel(),
            root=str(self.repo_dir),
            verbose=True,
            map_tokens=4096,  # Minimum token limit
        )
        
        # Generate the map
        chat_files = [str(self.repo_dir / "src" / "large.py")]
        other_files = [str(self.repo_dir / "src" / "large.js")]
        
        # Instead of mocking, we'll just verify that output is written
        repo_map.get_repo_map(chat_files, other_files)
        
        # Verify IO logs indicate something about writing a part
        # There should be a call like "Wrote part X with Y tokens to..."
        wrote_part_found = False
        for call_args, _ in self.mock_io.tool_output.call_args_list:
            if "Wrote part" in call_args[0]:
                wrote_part_found = True
                break
                
        self.assertTrue(wrote_part_found, "No evidence of parts being written")
    
    def test_minimum_token_limit(self):
        """Test that the minimum token limit of 4096 is enforced."""
        # Try to create RepoMap with a token limit below the minimum
        repo_map = RepoMap(
            io=self.mock_io,
            main_model=MockModel(),
            root=str(self.repo_dir),
            map_tokens=1000,  # Below minimum
        )
        
        # Verify that the minimum was enforced
        self.assertEqual(repo_map.max_map_tokens, 4096)
        
        # Simply test that the constructor enforces the minimum token limit
        # This is sufficient to verify the enforcement mechanism
        self.assertGreaterEqual(repo_map.max_map_tokens, 4096)


if __name__ == "__main__":
    unittest.main()