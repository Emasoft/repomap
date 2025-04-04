"""
InputOutput module for handling file operations and output.
"""

import os
import sys
from pathlib import Path
from typing import Optional, TextIO, Union, Dict, Any, List


class InputOutput:
    """
    Helper class for input/output operations used by RepoMap.
    Handles file reading, writing, and logging operations.
    """

    def __init__(self,
                 stdout: TextIO = sys.stdout,
                 stderr: TextIO = sys.stderr,
                 quiet: bool = False):
        """
        Initialize the InputOutput class.

        Args:
            stdout: Stream to use for standard output
            stderr: Stream to use for error output
            quiet: Whether to suppress normal output
        """
        self.stdout = stdout
        self.stderr = stderr
        self.quiet = quiet
        self.file_cache: Dict[str, str] = {}

    def read_text(self, file_path: Union[str, Path]) -> Optional[str]:
        """
        Read text from a file.

        Args:
            file_path: Path to the file to read

        Returns:
            The file contents as a string, or None if the file cannot be read
        """
        file_path_str = str(file_path)
        if file_path_str in self.file_cache:
            return self.file_cache[file_path_str]

        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
                self.file_cache[file_path_str] = content
                return content
        except Exception as e:
            self.tool_error(f"Failed to read {file_path}: {e}")
            return None

    def write_text(self, file_path: Union[str, Path], content: str) -> bool:
        """
        Write text to a file.

        Args:
            file_path: Path to the file to write
            content: Content to write to the file

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create parent directories if they don't exist
            os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            # Update cache
            self.file_cache[str(file_path)] = content
            return True
        except Exception as e:
            self.tool_error(f"Failed to write to {file_path}: {e}")
            return False

    def list_files(self, directory: Union[str, Path],
                  extensions: Optional[List[str]] = None,
                  recursive: bool = True) -> List[str]:
        """
        List files in a directory, optionally filtered by extension.

        Args:
            directory: Directory to list files from
            extensions: Optional list of file extensions to include (e.g. ['.py', '.js'])
            recursive: Whether to recursively list files in subdirectories

        Returns:
            List of file paths (as strings)
        """
        result = []
        dir_path = Path(directory)

        try:
            if not dir_path.exists() or not dir_path.is_dir():
                self.tool_warning(f"Directory does not exist: {directory}")
                return []

            if recursive:
                for root, _, files in os.walk(dir_path):
                    for filename in files:
                        file_path = os.path.join(root, filename)
                        if extensions is None or any(file_path.endswith(ext) for ext in extensions):
                            result.append(file_path)
            else:
                for item in dir_path.iterdir():
                    if item.is_file():
                        if extensions is None or any(str(item).endswith(ext) for ext in extensions):
                            result.append(str(item))

            return result
        except Exception as e:
            self.tool_error(f"Error listing files in {directory}: {e}")
            return []

    def tool_output(self, message: str):
        """
        Print an output message.

        Args:
            message: Message to print
        """
        if not self.quiet:
            print(message, file=self.stdout)

    def tool_error(self, message: str):
        """
        Print an error message.

        Args:
            message: Error message to print
        """
        print(f"ERROR: {message}", file=self.stderr)

    def tool_warning(self, message: str):
        """
        Print a warning message.

        Args:
            message: Warning message to print
        """
        print(f"WARNING: {message}", file=self.stderr)

    def confirm_ask(self, message: str, default: str = "y", subject: Optional[str] = None) -> bool:
        """
        Ask the user for confirmation. For CLI usage, always returns True.

        Args:
            message: Message to display
            default: Default response
            subject: Optional subject of confirmation

        Returns:
            Always True for CLI usage
        """
        return True


# Create a default I/O handler for easier imports
default_io = InputOutput()
