"""
RepoMap API for programmatic usage.

This module provides simple functions to use RepoMap as a library.
"""

import os
from typing import Dict, List, Optional, Tuple

from .io_utils import InputOutput, default_io
from .models import get_token_counter
from .repomap import RepoMap


def generate_map(
    paths: List[str],
    output_dir: str = "output",
    token_limit: int = 8192,
    verbose: bool = False,
    no_split: bool = False,
    io: Optional[InputOutput] = None,
) -> Tuple[str, List[str]]:
    """
    Generate a repository map for the given paths.

    Args:
        paths: List of file or directory paths to include in the map
        output_dir: Directory to save output files
        token_limit: Maximum tokens per part
        verbose: Whether to output verbose logging
        no_split: Whether to generate a single file regardless of size
        io: Optional InputOutput instance for custom I/O handling

    Returns:
        Tuple containing (first part content, list of output file paths)
    """
    io = io or default_io

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # If no_split is specified, set token limit to a large value
    if no_split:
        token_limit = 1000000

    # Initialize the token counter
    model = get_token_counter()

    # Initialize RepoMap
    rm = RepoMap(
        root=".",
        io=io,
        verbose=verbose,
        main_model=model,
        map_tokens=token_limit
    )

    # Get the repository name
    repo_name = os.path.basename(os.path.abspath("."))
    repo_name = repo_name.replace(" ", "_").lower()

    # Generate the repository map
    repo_map = rm.get_repo_map([], paths)

    # Find the generated files
    part_files = []
    if no_split:
        # For no_split, create a single file
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(output_dir, f"repomap_{repo_name}_{timestamp}.txt")

        if io.write_text(output_file, repo_map):
            part_files = [output_file]
    else:
        # For split output, find all parts
        import glob
        part_files = sorted(glob.glob(os.path.join(output_dir, f"repomap_{repo_name}_part*.txt")))

    return repo_map, part_files


def process_directory(
    directory: str,
    extensions: Optional[List[str]] = None,
    output_dir: str = "output",
    token_limit: int = 8192,
    verbose: bool = False,
    no_split: bool = False
) -> Tuple[str, List[str]]:
    """
    Process a directory and generate a repository map.

    Args:
        directory: Directory to process
        extensions: Optional list of file extensions to include (e.g. ['.py', '.js'])
        output_dir: Directory to save output files
        token_limit: Maximum tokens per part
        verbose: Whether to output verbose logging
        no_split: Whether to generate a single file regardless of size

    Returns:
        Tuple containing (first part content, list of output file paths)
    """
    io = InputOutput(quiet=not verbose)

    # List files in the directory
    if extensions:
        paths = []
        for ext in extensions:
            paths.extend(io.list_files(directory, [ext]))
    else:
        paths = io.list_files(directory)

    # Generate the map
    return generate_map(
        paths=paths,
        output_dir=output_dir,
        token_limit=token_limit,
        verbose=verbose,
        no_split=no_split,
        io=io
    )


def get_file_symbols(file_path: str, verbose: bool = False) -> Dict:
    """
    Extract symbols (functions, classes, etc.) from a single file.

    Args:
        file_path: Path to the file to analyze
        verbose: Whether to output verbose logging

    Returns:
        Dictionary of symbols with their line numbers and types
    """
    io = InputOutput(quiet=not verbose)
    model = get_token_counter()

    # Initialize RepoMap
    rm = RepoMap(
        root=os.path.dirname(file_path) or ".",
        io=io,
        verbose=verbose,
        main_model=model
    )

    # Get tags for the file
    rel_fname = os.path.basename(file_path)
    tags = list(rm.get_tags(file_path, rel_fname))

    # Convert tags to a dictionary
    symbols = {}
    for tag in tags:
        if tag.kind == "def":  # Only include definitions
            symbol_key = f"{tag.name}:{tag.line}"
            if symbol_key not in symbols:
                symbols[symbol_key] = {
                    "name": tag.name,
                    "line": tag.line,
                    "kind": tag.kind
                }

    return symbols
