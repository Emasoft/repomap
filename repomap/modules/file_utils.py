#!/usr/bin/env python3
"""
File utility functions for RepoMap.
"""
import os
import re
import glob
import fnmatch
import tempfile
import subprocess
from pathlib import Path
from typing import List, Set, Optional, Any

from .config import DEFAULT_IGNORE


def get_rel_fname(root: str, fname: str) -> str:
    """Get the file name relative to the root."""
    try:
        return os.path.relpath(fname, root)
    except ValueError:
        # If can't get relative path, return the full path
        return fname


def get_mtime(fname: str) -> float:
    """Get the modification time of a file."""
    try:
        return os.path.getmtime(fname)
    except (FileNotFoundError, PermissionError, OSError):
        return 0.0


def find_src_files(
    root: str, 
    ignore_patterns: List[str] = None,
    skip_tests: bool = False,
    skip_docs: bool = False,
    skip_git: bool = False
) -> List[str]:
    """
    Find all source files in the repository.
    
    Args:
        root: Root directory to search
        ignore_patterns: Patterns of files/directories to ignore
        skip_tests: Whether to skip test files and directories
        skip_docs: Whether to skip documentation files
        skip_git: Whether to skip git-related files
        
    Returns:
        List of file paths
    """
    from .config import TEST_PATTERNS, DOC_PATTERNS, GIT_PATTERNS
    
    if ignore_patterns is None:
        ignore_patterns = list(DEFAULT_IGNORE)
    else:
        ignore_patterns = list(ignore_patterns)
    
    # Add additional patterns based on skip options
    if skip_tests:
        ignore_patterns.extend(TEST_PATTERNS)
    if skip_docs:
        ignore_patterns.extend(DOC_PATTERNS)
    if skip_git:
        ignore_patterns.extend(GIT_PATTERNS)
        
    result = []
    
    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        # Filter directories using ignore patterns
        dirnames[:] = [d for d in dirnames if not any(
            _is_match(os.path.join(dirpath, d), d, pat, root) 
            for pat in ignore_patterns
        )]
        
        # Filter files using ignore patterns
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            
            if not any(_is_match(filepath, filename, pat, root) for pat in ignore_patterns):
                result.append(filepath)
    
    return result


def _is_match(filepath: str, filename: str, pattern: str, root: str) -> bool:
    """
    Check if a file matches a pattern.
    
    Handles both simple patterns and glob patterns with ** for directory traversal.
    
    Args:
        filepath: Full path to the file
        filename: Just the filename
        pattern: Pattern to match against
        root: Root directory for relative path calculations
        
    Returns:
        True if the file matches the pattern
    """
    # Get relative path for pattern matching
    rel_path = os.path.relpath(filepath, root)
    
    # Simple filename match
    if fnmatch.fnmatch(filename, pattern):
        return True
        
    # Simple relative path match
    if fnmatch.fnmatch(rel_path, pattern):
        return True
        
    # Handle ** patterns with Path's glob support
    if '**' in pattern:
        try:
            root_path = Path(root)
            pattern_path = root_path / pattern
            file_path = Path(filepath)
            
            # Check if this file would be matched by the pattern
            return file_path.match(pattern) or any(p == file_path for p in root_path.glob(pattern))
        except (ValueError, TypeError):
            # Fall back to simple matching if glob fails
            return False
            
    return False


def is_git_url(url: str) -> bool:
    """Check if a string is a Git URL."""
    git_url_patterns = [
        r'^https?://github\.com/[\w-]+/[\w-]+$',
        r'^https?://gitlab\.com/[\w-]+/[\w-]+$',
        r'^https?://bitbucket\.org/[\w-]+/[\w-]+$',
        r'^git@github\.com:[\w-]+/[\w-]+\.git$',
        r'^git@gitlab\.com:[\w-]+/[\w-]+\.git$',
        r'^git@bitbucket\.org:[\w-]+/[\w-]+\.git$',
        r'^https?://github\.com/[\w-]+/[\w-]+\.git$',
        r'^https?://gitlab\.com/[\w-]+/[\w-]+\.git$',
        r'^https?://bitbucket\.org/[\w-]+/[\w-]+\.git$',
    ]
    for pattern in git_url_patterns:
        if re.match(pattern, url):
            return True
    return False


def clone_repo(url: str, target_dir: str = None) -> str:
    """Clone a Git repository and return the path to the cloned directory."""
    import tempfile
    import subprocess
    
    if target_dir is None:
        # Create a temporary directory for the clone
        target_dir = tempfile.mkdtemp(prefix="repomap_clone_")
    
    try:
        # Clone the repository
        subprocess.run(
            ["git", "clone", "--depth", "1", url, target_dir],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return target_dir
    except subprocess.CalledProcessError as e:
        print(f"Error cloning repository: {e}")
        return ""


def expand_globs(patterns: List[str], root: str = None) -> List[str]:
    """Expand glob patterns to file paths."""
    if root is None:
        root = os.getcwd()
        
    result = []
    for pattern in patterns:
        # Check if the pattern is a Git URL
        if is_git_url(pattern):
            # Clone the repository to a temporary directory
            print(f"Cloning repository {pattern}...")
            repo_dir = clone_repo(pattern)
            if repo_dir:
                # Add all files from the cloned repository
                for dirpath, _, filenames in os.walk(repo_dir):
                    # Skip the .git directory
                    if ".git" in dirpath.split(os.path.sep):
                        continue
                    for filename in filenames:
                        result.append(os.path.join(dirpath, filename))
            else:
                print(f"Failed to clone repository {pattern}")
        # If it's a directory, add all files in it
        elif os.path.isdir(pattern):
            for dirpath, _, filenames in os.walk(pattern):
                for filename in filenames:
                    result.append(os.path.join(dirpath, filename))
        # If it's a file, add it directly
        elif os.path.isfile(pattern):
            result.append(pattern)
        # Otherwise, treat as a glob pattern
        else:
            # Use glob.glob for pattern expansion
            paths = glob.glob(pattern, recursive=True)
            if paths:
                result.extend(paths)
            # Try to handle relative paths inside the repository
            elif not os.path.isabs(pattern):
                repo_pattern = os.path.join(root, pattern)
                paths = glob.glob(repo_pattern, recursive=True)
                result.extend(paths)
    
    # Remove duplicates and sort
    return sorted(set(result))


def find_common_root(files: List[str]) -> str:
    """Find the common root directory of a list of files."""
    if not files:
        return os.getcwd()
    
    # Convert all paths to absolute
    abs_paths = [os.path.abspath(f) for f in files]
    
    # Handle Windows drive letters
    if os.name == 'nt':
        # Group by drive letter
        drives = {}
        for path in abs_paths:
            drive = os.path.splitdrive(path)[0]
            if drive in drives:
                drives[drive].append(path)
            else:
                drives[drive] = [path]
        
        # Find common root for the largest group
        if not drives:
            return os.getcwd()
        
        largest_drive = max(drives.keys(), key=lambda d: len(drives[d]))
        abs_paths = drives[largest_drive]
    
    # Split paths into components
    path_parts = [Path(p).parts for p in abs_paths]
    
    # Find common prefix
    common_parts = []
    for parts in zip(*path_parts):
        if len(set(parts)) == 1:
            common_parts.append(parts[0])
        else:
            break
    
    if not common_parts:
        return os.getcwd()
    
    # If the common path is just a file, return its directory
    common_path = os.path.join(*common_parts)
    if os.path.isfile(common_path):
        return os.path.dirname(common_path)
    
    return common_path


def is_text_file(file_path: str) -> bool:
    """Check if a file is a text file by looking at the first 8KB."""
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(8192)
        return b'\0' not in chunk
    except (IOError, OSError):
        return False


def is_binary_file(file_path: str) -> bool:
    """Check if a file is binary."""
    return not is_text_file(file_path)


def is_image_file(file_path: str) -> bool:
    """Check if a file is an image or PDF by its extension."""
    # Convert Path object to string if needed
    if isinstance(file_path, Path):
        file_path = str(file_path)
        
    # Get the lowercase extension
    ext = os.path.splitext(file_path)[1].lower()
    
    # Common image extensions and PDFs
    image_extensions = {
        '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp', '.svg', '.ico', '.pdf'
    }
    
    return ext in image_extensions
