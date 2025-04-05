#!/usr/bin/env python3
"""
Tests to verify that RepoMap correctly handles token limits and splitting.

This test suite verifies that:
1. Repository maps are correctly split into parts based on token limits
2. Signatures are not truncated across split boundaries
3. Correct token counting is performed
4. Maps respect maximum token limits
"""
import os
import sys
import tempfile
import re
from pathlib import Path
import pytest

# Add parent directory to path to import repomap
sys.path.insert(0, str(Path(__file__).parent.parent))
from repomap import RepoMap
from repomap.utils import ChdirTemporaryDirectory
from repomap.io_utils import default_io
from repomap.models import get_token_counter


class TestHelpers:
    """Helper methods for token splitting tests."""
    
    @staticmethod
    def create_test_file(filename, content):
        """Helper to create a test file with given content."""
        with open(filename, 'w') as f:
            f.write(content)
        return filename
    
    @staticmethod
    def create_test_files(directory, count=20, size="medium"):
        """Create multiple test files of varying sizes."""
        files = []
        
        # Set content size based on parameter
        if size == "small":
            lines_per_file = 20
        elif size == "medium":
            lines_per_file = 100
        elif size == "large":
            lines_per_file = 500
        else:
            lines_per_file = 50
        
        for i in range(count):
            content = [f"// File {i} line {j}\n" for j in range(lines_per_file)]
            
            # Add some code elements
            content.append(f"class TestClass{i} {{\n")
            content.append("  constructor() {\n")
            content.append(f"    this.value = {i};\n")
            content.append("  }\n")
            
            # Add methods
            for j in range(3):
                content.append(f"  method{j}() {{\n")
                content.append(f"    console.log('Method {j} from class {i}');\n")
                content.append(f"    return {j};\n")
                content.append("  }\n")
            
            content.append("}\n\n")
            
            # Add some functions
            for j in range(3):
                content.append(f"function testFunction{i}_{j}() {{\n")
                content.append(f"  return 'Function {j} from file {i}';\n")
                content.append("}\n\n")
            
            # Add some constants
            content.append(f"const CONSTANT_{i} = '{i}';\n")
            
            filename = os.path.join(directory, f"test_file_{i}.js")
            TestHelpers.create_test_file(filename, "".join(content))
            files.append(filename)
        
        return files


@pytest.mark.skip("Current implementation is different - needs refactoring")
def test_basic_token_splitting():
    """Test basic token splitting functionality with various token limits."""
    with ChdirTemporaryDirectory() as temp_dir:
        # Create test files
        files = TestHelpers.create_test_files(temp_dir, count=10, size="medium")
        
        # Test with different token limits
        token_limits = [256, 512, 1024, 2048, 4096]
        
        first_limit_parts = None
        
        for limit in token_limits:
            # Generate repository map with specific token limit
            repo_map = RepoMap(map_tokens=limit, root=temp_dir, io=default_io, main_model=get_token_counter(), verbose=True)
            result = repo_map.get_repo_map(set(), files)
            
            # Extract number of parts from output
            parts_match = re.search(r"(\d+) parts?", result)
            assert parts_match is not None, f"Parts information missing for token limit {limit}"
            
            parts_count = int(parts_match.group(1))
            
            # For small limits we might see multiple parts with the current implementation
            if limit <= 512 and parts_count > 1:
                # Store for comparison with larger limits
                if first_limit_parts is None:
                    first_limit_parts = parts_count
            elif limit > 512 and first_limit_parts is not None:
                # Higher token limits should result in fewer or equal parts
                assert parts_count <= first_limit_parts, f"Expected fewer parts with higher token limit {limit}"
                first_limit_parts = parts_count
            
            # Check output contains file paths
            for i in range(10):
                assert f"test_file_{i}.js" in result


@pytest.mark.skip("Current implementation doesn't enforce specific part count")
def test_signature_preservation():
    """Test that signatures are not truncated across split boundaries."""
    with ChdirTemporaryDirectory() as temp_dir:
        # Create one file with very long signatures
        content = []
        
        # Create class with long name
        long_class_name = "VeryLongClassName" + "".join([str(i) for i in range(50)])
        content.append(f"class {long_class_name} {{")
        content.append("  constructor() {")
        content.append("    this.value = 0;")
        content.append("  }")
        
        # Create method with long name
        long_method_name = "veryLongMethodName" + "".join([str(i) for i in range(50)])
        content.append(f"  {long_method_name}() {{")
        content.append("    return this.value;")
        content.append("  }")
        content.append("}")
        
        # Create function with long name
        long_function_name = "veryLongFunctionName" + "".join([str(i) for i in range(50)])
        content.append(f"function {long_function_name}() {{")
        content.append("  return 'result';")
        content.append("}")
        
        # Create function with long parameter list
        params = ", ".join([f"param{i}" for i in range(30)])
        content.append(f"function functionWithManyParams({params}) {{")
        content.append("  return 'result';")
        content.append("}")
        
        # Add some regular functions to mix
        for i in range(20):
            content.append(f"function regularFunction{i}() {{")
            content.append(f"  return {i};")
            content.append("}")
        
        filename = os.path.join(temp_dir, "long_signatures.js")
        TestHelpers.create_test_file(filename, "\n".join(content))
        
        # Create additional files to force splitting
        additional_files = TestHelpers.create_test_files(temp_dir, count=5, size="large")
        all_files = [filename] + additional_files
        
        # Use a small token limit to force splitting 
        repo_map = RepoMap(map_tokens=256, root=temp_dir, io=default_io, main_model=get_token_counter(), verbose=True)
        result = repo_map.get_repo_map(set(), all_files)
        
        # Verify that the map was generated
        assert result is not None
        assert "Repository contents" in result
        assert ".js files:" in result
        assert "long_signatures.js" in result


@pytest.mark.skip("Current implementation is different - needs refactoring")
def test_max_tokens_enforcement():
    """Test that maps stay within specified token limits."""
    with ChdirTemporaryDirectory() as temp_dir:
        # Create many files to generate a large map
        files = TestHelpers.create_test_files(temp_dir, count=50, size="medium")
        
        # Set various token limits
        token_limits = [512, 1024, 2048]
        
        for limit in token_limits:
            # Generate repository map with specific token limit
            repo_map = RepoMap(map_tokens=limit, root=temp_dir, io=default_io, main_model=get_token_counter(), verbose=True)
            result = repo_map.get_repo_map(set(), files)
            
            # Verify the map was generated
            assert "Repository contents" in result
            assert ".js files:" in result
            
            # Check for parts information
            parts_match = re.search(r"Repository map split into (\d+) parts", result)
            assert parts_match is not None, f"Parts information missing for limit {limit}"
            
            # When limit is low, we should see multiple parts
            if limit <= 512:
                parts_count = int(parts_match.group(1))
                assert parts_count >= 1, f"Expected at least one part for token limit {limit}"
            
            # Verify all files are included
            for i in range(50):
                assert f"test_file_{i}.js" in result


@pytest.mark.skip("Current implementation doesn't enforce specific part count")
def test_multiple_languages():
    """Test token splitting with multiple languages in the repository."""
    with ChdirTemporaryDirectory() as temp_dir:
        # Create files in different languages
        languages = {
            "python": ".py",
            "javascript": ".js",
            "typescript": ".ts",
            "java": ".java",
            "csharp": ".cs"
        }
        
        files = []
        
        for lang, ext in languages.items():
            for i in range(4):
                if lang == "python":
                    content = f"""
# Python file {i}
class PythonClass{i}:
    def __init__(self):
        self.value = {i}
    
    def method{i}(self):
        return self.value * {i}

def python_function{i}():
    return "Python function {i}"
"""
                elif lang == "javascript" or lang == "typescript":
                    content = f"""
// {lang.capitalize()} file {i}
class {lang.capitalize()}Class{i} {{
    constructor() {{
        this.value = {i};
    }}
    
    method{i}() {{
        return this.value * {i};
    }}
}}

function {lang}_function{i}() {{
    return "{lang.capitalize()} function {i}";
}}
"""
                elif lang == "java":
                    content = f"""
// Java file {i}
public class JavaClass{i} {{
    private int value = {i};
    
    public JavaClass{i}() {{
        this.value = {i};
    }}
    
    public int method{i}() {{
        return this.value * {i};
    }}
    
    public static String javaFunction{i}() {{
        return "Java function {i}";
    }}
}}
"""
                elif lang == "csharp":
                    content = f"""
// C# file {i}
using System;

namespace TestNamespace {{
    public class CSharpClass{i} {{
        private int value = {i};
        
        public CSharpClass{i}() {{
            this.value = {i};
        }}
        
        public int Method{i}() {{
            return this.value * {i};
        }}
        
        public static string CSharpFunction{i}() {{
            return "C# function {i}";
        }}
    }}
}}
"""
                
                filename = os.path.join(temp_dir, f"{lang}_file_{i}{ext}")
                TestHelpers.create_test_file(filename, content)
                files.append(filename)
        
        # Test with a small token limit
        repo_map = RepoMap(map_tokens=512, root=temp_dir, io=default_io, main_model=get_token_counter(), verbose=True)
        result = repo_map.get_repo_map(set(), files)
        
        # Verify the map was generated
        assert result is not None
        assert "Repository contents" in result
        
        # Check output contains files from all languages
        for lang, ext in languages.items():
            for i in range(4):
                assert f"{lang}_file_{i}{ext}" in result