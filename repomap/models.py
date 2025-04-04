"""
Models module for token counting support.
"""
from typing import Optional, Union


class Model:
    """
    Language model interface for token counting.
    In a standalone usage, this provides basic token counting functionality.
    When used within an application, it may be replaced with a more sophisticated implementation.
    """

    def __init__(self, model_name: str = "gpt-3.5-turbo"):
        """
        Initialize the model.

        Args:
            model_name: Name of the model to use
        """
        self.model_name = model_name

        # Try to import tiktoken for better token counting
        try:
            import tiktoken
            self.encoding = tiktoken.encoding_for_model(model_name)
            self._count_tokens = self._count_tokens_tiktoken
        except (ImportError, KeyError):
            # Fallback to approximate token counting
            self._count_tokens = self._count_tokens_approx

    def token_count(self, text: str) -> int:
        """
        Count the number of tokens in the given text.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        return self._count_tokens(text)

    def _count_tokens_tiktoken(self, text: str) -> int:
        """
        Count tokens using tiktoken.
        """
        return len(self.encoding.encode(text))

    def _count_tokens_approx(self, text: str) -> int:
        """
        Approximate token count based on character count.
        Typically, 1 token is about 4 characters of English text.
        """
        return max(1, len(text) // 4)  # Ensure at least 1 token


def get_token_counter(model_name: Optional[str] = None) -> Model:
    """
    Get a token counter for the specified model.

    Args:
        model_name: Optional name of the model to use, defaults to "gpt-3.5-turbo"

    Returns:
        A Model instance that can count tokens
    """
    return Model(model_name or "gpt-3.5-turbo")
