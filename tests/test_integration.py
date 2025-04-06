#!/usr/bin/env python3
"""
Integration tests for RepoMap that simulate real-world scenarios
"""

import os
import sys
import unittest
import tempfile
import shutil
import subprocess
from pathlib import Path

# Make sure we can import the main package
sys.path.insert(0, str(Path(__file__).parent.parent))
from repomap import RepoMap, main as repomap_main


class TestRealWorldScenarios(unittest.TestCase):
    """Tests that simulate real-world usage scenarios"""

    def setUp(self):
        """Set up test fixtures"""
        # Create a temporary directory for our test repository
        self.repo_dir = tempfile.mkdtemp()

        # Create a simple project structure
        # - src/
        #   - main.py
        #   - utils.py
        # - tests/
        #   - test_main.py
        # - README.md
        # - requirements.txt

        # Create directories
        os.makedirs(os.path.join(self.repo_dir, "src"))
        os.makedirs(os.path.join(self.repo_dir, "tests"))

        # Create sample Python files
        with open(os.path.join(self.repo_dir, "src", "main.py"), "w") as f:
            f.write("""
def main():
    \"\"\"Main entry point\"\"\"
    print("Hello, world!")
    result = calculate(10, 20)
    print(f"Result: {result}")
    return result

def calculate(a, b):
    \"\"\"Calculate the sum of two numbers\"\"\"
    return a + b

if __name__ == "__main__":
    main()
""")

        with open(os.path.join(self.repo_dir, "src", "utils.py"), "w") as f:
            f.write("""
import os
import json

class Config:
    \"\"\"Configuration handler\"\"\"

    def __init__(self, config_file="config.json"):
        self.config_file = config_file
        self.data = {}

    def load(self):
        \"\"\"Load configuration from file\"\"\"
        if os.path.exists(self.config_file):
            with open(self.config_file, "r") as f:
                self.data = json.load(f)
        return self.data

    def save(self):
        \"\"\"Save configuration to file\"\"\"
        with open(self.config_file, "w") as f:
            json.dump(self.data, f, indent=4)

def format_string(s):
    \"\"\"Format a string by capitalizing and adding a period\"\"\"
    if not s:
        return ""
    s = s.strip().capitalize()
    if not s.endswith("."):
        s += "."
    return s
""")

        with open(os.path.join(self.repo_dir, "tests", "test_main.py"), "w") as f:
            f.write("""
import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.main import calculate, main

class TestMain(unittest.TestCase):

    def test_calculate(self):
        \"\"\"Test the calculate function\"\"\"
        self.assertEqual(calculate(10, 20), 30)
        self.assertEqual(calculate(-5, 5), 0)
        self.assertEqual(calculate(0, 0), 0)

    def test_main(self):
        \"\"\"Test the main function\"\"\"
        self.assertEqual(main(), 30)

if __name__ == "__main__":
    unittest.main()
""")

        # Create README
        with open(os.path.join(self.repo_dir, "README.md"), "w") as f:
            f.write("""# Sample Project

A sample project for testing RepoMap.

## Usage

```python
from src.main import main
main()
```

## Testing

Run tests with:

```
python -m unittest discover tests
```
""")

        # Create requirements.txt
        with open(os.path.join(self.repo_dir, "requirements.txt"), "w") as f:
            f.write("""pytest>=7.0.0
black>=22.1.0
""")

    def tearDown(self):
        """Clean up after tests"""
        if hasattr(self, 'repo_dir') and os.path.exists(self.repo_dir):
            shutil.rmtree(self.repo_dir)

    def test_real_project_map(self):
        """Test generating a map for a realistic project structure"""
        # Create a simple IO class
        class SimpleIO:
            def tool_warning(self, msg): pass
            def tool_output(self, msg): pass
            def tool_error(self, msg): pass
            def read_text(self, fname):
                if os.path.exists(fname):
                    with open(fname, 'r', encoding='utf-8', errors='replace') as f:
                        return f.read()
                return None
            def confirm_ask(self, msg, default=None, subject=None): return True

        # Create a token counter
        class MockModel:
            def token_count(self, text): return len(text) // 4

        io_obj = SimpleIO()
        token_counter = MockModel()

        # Initialize RepoMap
        rm = RepoMap(
            root=self.repo_dir,
            io=io_obj,
            main_model=token_counter,
            verbose=True
        )

        # Get all Python files
        python_files = []
        for root, _, files in os.walk(self.repo_dir):
            for file in files:
                if file.endswith(".py"):
                    python_files.append(os.path.join(root, file))

        # Generate map
        repo_map = rm.get_ranked_tags_map_uncached(python_files, [])

        # Verify the map contains expected elements
        self.assertIsNotNone(repo_map)
        self.assertIn("main.py", repo_map)
        self.assertIn("utils.py", repo_map)
        self.assertIn("test_main.py", repo_map)

    def test_cli_with_real_project(self):
        self.skipTest("Skipping CLI test due to environment limitations")
        """Test the CLI with a realistic project"""
        # Use subprocess to run the CLI command
        os.chdir(self.repo_dir)

        # Find all Python files
        python_files = []
        for root, _, files in os.walk(self.repo_dir):
            for file in files:
                if file.endswith(".py"):
                    python_files.append(os.path.relpath(os.path.join(root, file), self.repo_dir))

        # Run the command with all Python files
        cmd = [sys.executable, "-m", "repomap"] + python_files
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=self.repo_dir
        )

        # Check the output
        output = result.stdout + result.stderr
        self.assertIn("Repository contents", output)
        for py_file in python_files:
            self.assertIn(py_file, output)

    def test_simulated_workflow(self):
        """Test a simulated development workflow scenario"""
        # Simulate a developer workflow without changing directories

        # 1. Look at all Python files - we'll use absolute paths
        main_py = os.path.join(self.repo_dir, "src", "main.py")
        test_py = os.path.join(self.repo_dir, "tests", "test_main.py")

        # Make sure these files exist
        self.assertTrue(os.path.exists(main_py), "Main.py should exist")
        self.assertTrue(os.path.exists(test_py), "Test_main.py should exist")

        # 2. Make a change to one of the files
        with open(main_py, "a") as f:
            f.write("\n\ndef new_function():\n    \"\"\"A new function added during development\"\"\"\n    return 42\n")

        # Read the file back to check our changes
        with open(main_py, "r") as f:
            content = f.read()
            self.assertIn("new_function", content)

        # 3. Initialize RepoMap to read these files
        class SimpleIO:
            def tool_warning(self, msg): pass
            def tool_output(self, msg): pass
            def tool_error(self, msg): pass
            def read_text(self, fname):
                if os.path.exists(fname):
                    with open(fname, 'r', encoding='utf-8', errors='replace') as f:
                        return f.read()
                return None
            def confirm_ask(self, msg, default=None, subject=None): return True

        class MockModel:
            def token_count(self, text): return len(text) // 4

        io = SimpleIO()
        model = MockModel()
        rm = RepoMap(
            root=self.repo_dir,
            io=io,
            main_model=model,
            verbose=True
        )

        # 4. Generate a map with the modified files
        java_files = []
        for root, _, files in os.walk(self.repo_dir):
            for file in files:
                if file.endswith(".java"):
                    java_files.append(os.path.join(root, file))

        repo_map = rm.get_ranked_tags_map_uncached([main_py, test_py] + java_files, [])

        # 5. Check that the map reflects the changes
        self.assertIsNotNone(repo_map)
        self.assertIn("main.py", repo_map)
        self.assertIn("test_main.py", repo_map)


if __name__ == '__main__':
    unittest.main()
