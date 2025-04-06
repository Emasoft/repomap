import unittest
import os
from repomap.special import is_important, filter_important_files, NORMALIZED_ROOT_IMPORTANT_FILES


class TestSpecial(unittest.TestCase):
    def test_is_important_with_root_file(self):
        """Test that files in ROOT_IMPORTANT_FILES are correctly identified as important."""
        for file_path in ["README.md", "pyproject.toml", "Dockerfile"]:
            with self.subTest(file_path=file_path):
                self.assertTrue(is_important(file_path))
    
    def test_is_important_with_github_workflow(self):
        """Test that GitHub workflow files are correctly identified as important."""
        self.assertTrue(is_important(".github/workflows/test.yml"))
        self.assertTrue(is_important(".github/workflows/ci.yml"))
        
    def test_is_important_with_non_important_file(self):
        """Test that regular files are correctly identified as not important."""
        self.assertFalse(is_important("src/main.py"))
        self.assertFalse(is_important("lib/helpers.js"))
        self.assertFalse(is_important("docs/usage.md"))
        
    def test_is_important_with_similar_but_non_matching_file(self):
        """Test that files with similar names but not matching exactly are not important."""
        self.assertFalse(is_important("README-old.md"))
        self.assertFalse(is_important("requirements-dev.txt"))
        
    def test_filter_important_files(self):
        """Test filtering a list of file paths for important files."""
        file_paths = [
            "README.md",
            "src/main.py",
            ".github/workflows/test.yml",
            "docs/usage.md",
            "package.json",
            "temp/notes.txt"
        ]
        expected = ["README.md", ".github/workflows/test.yml", "package.json"]
        self.assertEqual(sorted(filter_important_files(file_paths)), sorted(expected))
        
    def test_normalization(self):
        """Test that path normalization works correctly."""
        # Test with paths that have extra slashes or different separators
        self.assertTrue(is_important("README.md//"))
        self.assertTrue(is_important("./README.md"))
        
        if os.name == 'nt':  # Windows tests
            self.assertTrue(is_important("README.md\\"))
            self.assertTrue(is_important(".\\README.md"))
            
    def test_normalized_root_important_files(self):
        """Test that NORMALIZED_ROOT_IMPORTANT_FILES is correctly created."""
        # Verify some known entries are in the normalized set
        self.assertIn(os.path.normpath("README.md"), NORMALIZED_ROOT_IMPORTANT_FILES)
        self.assertIn(os.path.normpath("pyproject.toml"), NORMALIZED_ROOT_IMPORTANT_FILES)
        self.assertIn(os.path.normpath("Dockerfile"), NORMALIZED_ROOT_IMPORTANT_FILES)
        
        # Verify the count is less than or equal to the original list
        # (normalization might combine some paths)
        from repomap.special import ROOT_IMPORTANT_FILES
        self.assertLessEqual(len(NORMALIZED_ROOT_IMPORTANT_FILES), len(ROOT_IMPORTANT_FILES))


if __name__ == "__main__":
    unittest.main()
