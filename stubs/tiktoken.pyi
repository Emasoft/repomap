"""Type stubs for tiktoken module."""

from typing import Any, Dict, List, Optional, Union, Callable

def get_encoding(encoding_name: str) -> "Encoding":
    """Get the encoding object for a given encoding name."""
    ...

class Encoding:
    """Encoding object for tiktoken."""
    
    def __init__(self, name: str = "", pat_str: str = "", mergeable_ranks: Dict[bytes, int] = None,
                 special_tokens: Dict[str, int] = None) -> None:
        """Create an Encoding object."""
        ...
    
    def encode(self, text: str, allowed_special: Union[str, List[str], set, Dict[str, int]] = None,
               disallowed_special: Union[str, List[str], set] = None) -> List[int]:
        """Encode a string into tokens."""
        ...
    
    def encode_ordinary(self, text: str) -> List[int]:
        """Encode a string into tokens, ignoring special tokens."""
        ...
    
    def decode(self, tokens: List[int]) -> str:
        """Decode tokens into a string."""
        ...
    
    def decode_single_token_bytes(self, token: int) -> bytes:
        """Decode a single token into bytes."""
        ...
    
    def decode_bytes(self, tokens: List[int]) -> bytes:
        """Decode tokens into bytes."""
        ...
    
    @property
    def name(self) -> str:
        """Get the name of the encoding."""
        ...

def get_max_token_length(model: str) -> int:
    """Get the maximum token length for a given model."""
    ...

def encoding_for_model(model_name: str) -> Encoding:
    """Get the encoding object for a given model name."""
    ...