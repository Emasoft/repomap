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
        
    def chunk_text_by_tokens(self, text, max_tokens_per_chunk):
        """
        Split text into chunks, each with approximately max_tokens_per_chunk tokens.
        
        This method ensures that no line is split across chunk boundaries.
        
        Args:
            text: Text to split
            max_tokens_per_chunk: Maximum tokens per chunk
            
        Returns:
            List of text chunks
        """
        # If the text is already small enough, return as is
        total_tokens = self.token_count(text)
        if total_tokens <= max_tokens_per_chunk:
            return [text]
        
        lines = text.splitlines(keepends=True)
        chunks = []
        current_chunk = []
        current_chunk_tokens = 0
        
        for line in lines:
            line_tokens = self.token_count(line)
            
            # If this single line is too large, we need to split it
            if line_tokens > max_tokens_per_chunk:
                # First, add the current chunk if not empty
                if current_chunk:
                    chunks.append("".join(current_chunk))
                    current_chunk = []
                    current_chunk_tokens = 0
                
                # Split the large line at character boundaries
                # This is a fallback for extremely long lines
                chunks_needed = (line_tokens + max_tokens_per_chunk - 1) // max_tokens_per_chunk
                chars_per_chunk = len(line) // chunks_needed
                
                for i in range(0, len(line), chars_per_chunk):
                    chunk = line[i:i+chars_per_chunk]
                    chunks.append(chunk)
            
            # If adding this line would exceed the limit, start a new chunk
            elif current_chunk_tokens + line_tokens > max_tokens_per_chunk:
                # Save the current chunk
                chunks.append("".join(current_chunk))
                # Start a new chunk with this line
                current_chunk = [line]
                current_chunk_tokens = line_tokens
            else:
                # Add the line to the current chunk
                current_chunk.append(line)
                current_chunk_tokens += line_tokens
        
        # Add the last chunk if there's anything left
        if current_chunk:
            chunks.append("".join(current_chunk))
        
        return chunks


def get_token_counter(model_name: Optional[str] = None) -> Model:
    """
    Get a token counter for the specified model.

    Args:
        model_name: Optional name of the model to use, defaults to "gpt-3.5-turbo"

    Returns:
        A Model instance that can count tokens
    """
    return Model(model_name or "gpt-3.5-turbo")