"""
Basic tests for RepoMap
"""

import unittest
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from repomap import RepoMap, find_src_files


class TestRepoMap(unittest.TestCase):
    """Test RepoMap functionality"""

    def test_import(self):
        """Test that RepoMap can be imported"""
        self.assertIsNotNone(RepoMap)
        self.assertIsNotNone(find_src_files)
    
    def test_find_src_files(self):
        """Test finding source files"""
        # This test assumes it's run from the project root
        files = find_src_files('.')
        self.assertGreater(len(files), 0)
    
    def test_init_repomap(self):
        """Test RepoMap initialization"""
        rm = RepoMap(root=".")
        self.assertIsNotNone(rm)


if __name__ == '__main__':
    unittest.main()