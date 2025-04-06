"""
Pytest configuration and fixtures.
"""
import os
import sys
import tempfile
from pathlib import Path

import pytest

# Add the parent directory to sys.path to allow proper imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        original_dir = os.getcwd()
        try:
            yield Path(temp_dir)
        finally:
            os.chdir(original_dir)


@pytest.fixture
def sample_python_file(temp_dir):
    """Create a simple Python file for testing."""
    file_path = temp_dir / "test_file.py"
    content = """
# Sample Python file for testing
def test_function():
    \"\"\"Test docstring.\"\"\"
    return "Hello, world!"

class TestClass:
    def __init__(self):
        self.value = 42
        
    def test_method(self):
        return self.value
"""
    file_path.write_text(content)
    return file_path