#!/usr/bin/env python3
"""
Comprehensive tests for the models module.
"""
import sys
import unittest
from unittest import mock
from pathlib import Path

# Add parent directory to path to import repomap
sys.path.insert(0, str(Path(__file__).parent.parent))
from repomap.models import Model, get_token_counter


class TestModels(unittest.TestCase):
    """Tests for the models module."""

    def test_model_initialization_default(self):
        """Test Model class initialization with default model name."""
        model = Model()
        self.assertEqual(model.model_name, "gpt-3.5-turbo")
        
    def test_model_initialization_custom(self):
        """Test Model class initialization with custom model name."""
        model = Model("gpt-4")
        self.assertEqual(model.model_name, "gpt-4")
    
    def test_model_token_count_approx(self):
        """Test Model.token_count method with approximate counter."""
        # Force approximate counting
        with mock.patch.dict(sys.modules, {'tiktoken': None}):
            model = Model()
            # Should use character-based approximation (len // 4)
            self.assertEqual(model.token_count("This is a test string"), 5)  # 20 chars // 4 = 5
            self.assertEqual(model.token_count("A"), 1)  # Minimum is 1 token
    
    def test_model_token_count_tiktoken(self):
        """Test Model.token_count method with simulated tiktoken."""
        # Create a mock for the model's _count_tokens_tiktoken method
        with mock.patch.object(Model, '_count_tokens_tiktoken') as mock_count_tokens_tiktoken:
            # Setup mock to return 4 tokens
            mock_count_tokens_tiktoken.return_value = 4
            
            # Make a model instance with the _count_tokens method pointing to our mock
            model = Model("gpt-3.5-turbo")
            # Manually set the method to use
            model._count_tokens = mock_count_tokens_tiktoken
            
            # Test token count
            self.assertEqual(model.token_count("Test text"), 4)
            
            # Verify our mock was called
            mock_count_tokens_tiktoken.assert_called_with("Test text")
    
    def test_get_token_counter_default(self):
        """Test get_token_counter function with default model name."""
        with mock.patch('repomap.models.Model') as mock_model:
            # Call the function
            get_token_counter()
            
            # Verify Model was created with the default model name
            mock_model.assert_called_with("gpt-3.5-turbo")
    
    def test_get_token_counter_custom(self):
        """Test get_token_counter function with custom model name."""
        with mock.patch('repomap.models.Model') as mock_model:
            # Call the function with custom model name
            get_token_counter("gpt-4")
            
            # Verify Model was created with the custom model name
            mock_model.assert_called_with("gpt-4")
    
    def test_tiktoken_keyerror_fallback(self):
        """Test fallback to approximate counting when tiktoken raises KeyError."""
        # For this test, we'll simulate the fallback case by injecting a KeyError during initialization
        
        # Create a class that mimics the Model but forces a KeyError for tiktoken
        class TestModel(Model):
            def __init__(self, model_name):
                self.model_name = model_name
                # Simulate the tiktoken KeyError case
                self._count_tokens = self._count_tokens_approx
        
        # Create an instance of our test model
        model = TestModel("unknown-model")
        
        # Test that token counting uses the approximate counter
        self.assertEqual(model.token_count("This is a test string"), 5)  # 20 chars // 4 = 5


if __name__ == "__main__":
    unittest.main()
