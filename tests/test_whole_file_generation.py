#!/usr/bin/env python3
"""
Tests for the whole-file repository map generation without splitting.
This validates that the repository map generation works correctly when
splitting is disabled, producing a single comprehensive map.
"""
import os
import sys
import unittest
from unittest import mock
from pathlib import Path
import tempfile

# Add parent directory to path to import repomap
sys.path.insert(0, str(Path(__file__).parent.parent))
from repomap.repomap import RepoMap


class MockIO:
    """Mock IO class for testing."""
    
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


class MockModel:
    """Mock model for token counting in tests."""
    
    def token_count(self, text):
        """Simple token count estimate: 1 token per 4 characters."""
        return len(text) // 4


class TestWholeFileGeneration(unittest.TestCase):
    """Tests for repository map generation without splitting."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for test repo
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_dir = Path(self.temp_dir.name)
        
        # Create test files
        self.create_test_files()
        
        # Initialize RepoMap with disable_splitting=True
        self.io = MockIO()
        self.repo_map = RepoMap(
            root=str(self.repo_dir),
            io=self.io,
            main_model=MockModel(),
            verbose=True,
            map_tokens=4096,
            disable_splitting=True  # This is the key setting for our tests
        )
    
    def tearDown(self):
        """Clean up after tests."""
        self.temp_dir.cleanup()
    
    def create_test_files(self):
        """Create test files with various content types and sizes."""
        # Create directories
        src_dir = self.repo_dir / "src"
        test_dir = self.repo_dir / "tests"
        docs_dir = self.repo_dir / "docs"
        
        for directory in [src_dir, test_dir, docs_dir]:
            directory.mkdir(exist_ok=True)
        
        # Create Python files
        py_file1 = src_dir / "main.py"
        py_file1.write_text("""
def main():
    \"\"\"Main function.\"\"\"
    print("Hello, world!")
    return 0

class ExampleClass:
    \"\"\"An example class.\"\"\"
    
    def __init__(self, name):
        self.name = name
    
    def greet(self):
        \"\"\"Greet the user.\"\"\"
        return f"Hello, {self.name}!"

if __name__ == "__main__":
    main()
""")
        
        # Create a large Python file
        large_py_file = src_dir / "large.py"
        large_content = []
        for i in range(100):
            large_content.append(f"""
def function_{i}(a, b, c):
    \"\"\"Function {i} that does something.\"\"\"
    result = a + b + c
    print(f"Result: " + str(result))
    return result

class Class_{i}:
    \"\"\"Class {i} for demonstration.\"\"\"
    
    def __init__(self):
        self.value = {i}
    
    def get_value(self):
        return self.value
        
    def set_value(self, value):
        self.value = value
""")
        large_py_file.write_text("\n".join(large_content))
        
        # Create a JavaScript file
        js_file = src_dir / "app.js"
        js_file.write_text("""
function initialize() {
    console.log("Initializing app");
}

class Component {
    constructor(name) {
        this.name = name;
    }
    
    render() {
        return `<div>${this.name}</div>`;
    }
}

// Export for use in other files
module.exports = {
    initialize,
    Component
};
""")
        
        # Create a documentation file
        readme = self.repo_dir / "README.md"
        readme.write_text("""
# Test Repository

This is a test repository for RepoMap.

## Features

- Python code
- JavaScript code
- Tests
- Documentation
""")
    
    def _get_all_files(self):
        """Get all files in the test repository."""
        all_files = []
        for root, _, files in os.walk(self.repo_dir):
            for file in files:
                all_files.append(os.path.join(root, file))
        return all_files
    
    def test_disable_splitting_generates_single_file(self):
        """Test that disable_splitting generates a single complete repository map."""
        # Get the repository map
        repo_map = self.repo_map.get_repo_map([], self._get_all_files())
        
        # Verify we have a non-empty map
        self.assertIsNotNone(repo_map)
        self.assertGreater(len(repo_map), 0)
        
        # Check that splitting was disabled message appears in logs
        splitting_disabled_msg = any("Splitting disabled" in msg for msg in self.io.outputs)
        self.assertTrue(splitting_disabled_msg, "Splitting disabled message not found in logs")
        
        # Verify that all files are included
        self.assertIn("main.py", repo_map)
        self.assertIn("large.py", repo_map)
        self.assertIn("app.js", repo_map)
        self.assertIn("README.md", repo_map)
        
        # Check for specific code elements from each file
        self.assertIn("def main", repo_map)
        self.assertIn("class ExampleClass", repo_map)
        self.assertIn("def function_0", repo_map)
        self.assertIn("class Class_0", repo_map)
        self.assertIn("function initialize", repo_map)
        self.assertIn("class Component", repo_map)
        
        # Verify the map doesn't contain part markers
        self.assertNotIn("Repository contents (continued, part", repo_map)
    
    def test_large_file_handling(self):
        """Test that large files are included completely when splitting is disabled."""
        # Get the repository map
        repo_map = self.repo_map.get_repo_map([], [str(self.repo_dir / "src" / "large.py")])
        
        # Verify all functions and classes are included
        for i in range(100):
            self.assertIn(f"def function_{i}", repo_map)
            self.assertIn(f"class Class_{i}", repo_map)
        
        # Verify docstrings are included
        self.assertIn("Function 0 that does something", repo_map)
        self.assertIn("Class 99 for demonstration", repo_map)
    
    def test_disable_splitting_respects_minimum_token_size(self):
        """Test that disable_splitting still respects the minimum token size of 4096."""
        # Create a RepoMap with a small token size, which should be increased to 4096
        small_repo_map = RepoMap(
            root=str(self.repo_dir),
            io=self.io,
            main_model=MockModel(),
            verbose=True,
            map_tokens=100,  # This is below the minimum
            disable_splitting=True
        )
        
        # Verify the minimum token size was enforced
        self.assertEqual(small_repo_map.max_map_tokens, 4096)
        
        # Generate a map and verify it works
        repo_map = small_repo_map.get_repo_map([], self._get_all_files())
        self.assertIsNotNone(repo_map)
        self.assertGreater(len(repo_map), 0)


if __name__ == "__main__":
    unittest.main()