#!/usr/bin/env python3
"""
File utility functions for RepoMap.
"""
import os
import re
import glob
import fnmatch
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


def find_src_files(root: str, ignore_patterns: List[str] = None) -> List[str]:
    """Find all source files in the repository."""
    if ignore_patterns is None:
        ignore_patterns = DEFAULT_IGNORE
        
    result = []
    
    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        # Filter directories using ignore patterns
        dirnames[:] = [d for d in dirnames if not any(
            fnmatch.fnmatch(d, pat) or fnmatch.fnmatch(os.path.join(dirpath, d), pat)
            for pat in ignore_patterns
        )]
        
        # Filter files using ignore patterns
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(filepath, root)
            
            if not any(fnmatch.fnmatch(filename, pat) or fnmatch.fnmatch(rel_path, pat) 
                      for pat in ignore_patterns):
                result.append(filepath)
    
    return result


def expand_globs(patterns: List[str], root: str = None) -> List[str]:
    """Expand glob patterns to file paths."""
    if root is None:
        root = os.getcwd()
        
    result = []
    for pattern in patterns:
        # If it's a directory, add all files in it
        if os.path.isdir(pattern):
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