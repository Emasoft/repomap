#!/usr/bin/env python3
"""
Tests for enforcing the minimum token size of 4096.
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
    
    def tool_warning(self, message):
        self.warnings.append(message)
    
    def tool_output(self, message):
        self.outputs.append(message)
    
    def tool_error(self, message):
        self.errors.append(message)
    
    def read_text(self, fname):
        return "Mock file content"


class MockModel:
    """Mock token counter for testing."""
    
    def token_count(self, text):
        return len(text) // 4


class TestMinimumTokenSize(unittest.TestCase):
    """Tests for enforcing the minimum token size of 4096."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.io = MockIO()
        self.model = MockModel()
    
    def test_init_enforces_minimum_token_size(self):
        """Test that RepoMap.__init__ enforces the minimum token size."""
        # Create RepoMap with token size smaller than minimum
        rm = RepoMap(
            root=".",
            io=self.io,
            main_model=self.model,
            map_tokens=100,  # This is below the minimum
            verbose=True
        )
        
        # Ensure the minimum token size was enforced
        self.assertEqual(rm.max_map_tokens, 4096)
        
        # Create RepoMap with token size larger than minimum
        rm = RepoMap(
            root=".",
            io=self.io,
            main_model=self.model,
            map_tokens=8192,  # This is above the minimum
            verbose=True
        )
        
        # Ensure the token size was kept as is
        self.assertEqual(rm.max_map_tokens, 8192)
    
    def test_get_ranked_tags_map_uncached_enforces_minimum(self):
        """Test that get_ranked_tags_map_uncached enforces the minimum token size."""
        rm = RepoMap(
            root=".",
            io=self.io,
            main_model=self.model,
            map_tokens=4096,
            verbose=True
        )
        
        # Mock necessary methods to avoid actual file operations
        rm.get_ranked_tags = mock.MagicMock(return_value=[])
        
        # Call with small token size
        rm.get_ranked_tags_map_uncached([], [], 100)
        
        # Verify it logs the correct token size
        token_size_mentioned = False
        for msg in self.io.outputs:
            if "Max tokens per part: 4096" in msg:
                token_size_mentioned = True
                break
        
        self.assertTrue(token_size_mentioned, "Minimum token size not enforced in get_ranked_tags_map_uncached")
    
    def test_splitting_enforces_minimum_token_size(self):
        """Test that splitting module enforces minimum token size."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as tmp:
            tmp.write(b"class Test:\n    pass\n")
            tmp_path = tmp.name
        
        try:
            # Create RepoMap with token size smaller than minimum
            rm = RepoMap(
                root=".",
                io=self.io,
                main_model=self.model,
                map_tokens=100,  # This is below the minimum
                verbose=True
            )
            
            # Generate repo map with small section
            repo_map = rm.get_repo_map([], [tmp_path])
            
            # Look for warning indicating token size is being enforced
            token_size_enforced = False
            for msg in self.io.outputs:
                if "4096" in msg:
                    token_size_enforced = True
                    break
            
            self.assertTrue(token_size_enforced, "Token size enforcement not mentioned in output")
        finally:
            # Clean up
            os.unlink(tmp_path)


if __name__ == "__main__":
    unittest.main()