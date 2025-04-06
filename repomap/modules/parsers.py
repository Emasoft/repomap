#!/usr/bin/env python3
"""
Code parsing and tag extraction for RepoMap.
"""
import os
import re
import sys
import subprocess
import importlib
from pathlib import Path
from typing import List, Dict, Tuple, Set, Optional, Any, Union

from .config import LANGUAGE_EXTENSIONS
from .models import Tag
from .file_utils import get_rel_fname


def get_scm_fname(language: str, query_name: str = "tags") -> Optional[str]:
    """Get the path to a tree-sitter query file."""
    # List of places to look for query files
    query_dirs = [
        # First check local paths
        os.path.join("queries", "tree-sitter-languages"),
        os.path.join("queries", "tree-sitter-language-pack"),
        
        # Then check package paths
        os.path.join(os.path.dirname(__file__), "..", "queries", "tree-sitter-languages"),
        os.path.join(os.path.dirname(__file__), "..", "queries", "tree-sitter-language-pack"),
    ]
    
    # Add paths from importlib.resources if available
    try:
        import importlib.resources
        try:
            # Python 3.9+
            files = importlib.resources.files("repomap")
            
            # Try the built-in queries from the package
            query_dirs.append(str(files / "queries" / "tree-sitter-languages"))
            query_dirs.append(str(files / "queries" / "tree-sitter-language-pack"))
        except (AttributeError, ImportError):
            # Python 3.6-3.8
            query_dirs.append(importlib.resources.resource_filename("repomap", "queries/tree-sitter-languages"))
            query_dirs.append(importlib.resources.resource_filename("repomap", "queries/tree-sitter-language-pack"))
    except ImportError:
        pass
    
    # Try to find the query file in the various locations
    for query_dir in query_dirs:
        scm_fname = os.path.join(query_dir, f"{language}-{query_name}.scm")
        
        if os.path.isfile(scm_fname):
            return scm_fname
    
    return None


def get_tags_raw(fname: str, rel_fname: str, io: Any, verbose: bool = False) -> List[Tag]:
    """
    Extract raw tags from a file.
    
    This uses tree-sitter or grep_ast to extract tags from a file.
    """
    if not os.path.isfile(fname):
        if verbose:
            io.tool_warning(f"File not found: {fname}")
        return []
        
    # Determine file extension and language
    ext = os.path.splitext(fname)[1].lower()
    language = None
    
    # Map extension to language
    for lang, extensions in LANGUAGE_EXTENSIONS.items():
        if ext in extensions:
            language = lang
            break
    
    if not language:
        if verbose:
            io.tool_warning(f"Unknown language for file: {fname}")
        return []
    
    # Try to use grep_ast for tag extraction
    try:
        import grep_ast
        
        # Find the query file
        scm_fname = get_scm_fname(language)
        if not scm_fname:
            if verbose:
                io.tool_warning(f"No tree-sitter queries found for language: {language}")
            return []
            
        try:
            # Extract tags using grep_ast
            tags = []
            
            # Read the query file
            with open(scm_fname, "r") as f:
                query = f.read()
            
            # Use grep_ast to extract matches
            for match in grep_ast.ast_grep(fname, query):
                name = match.get("name", "")
                kind = match.get("kind", "")
                line = match.get("line", 1)
                
                if name and kind:
                    tags.append(Tag(
                        rel_fname=rel_fname,
                        fname=fname,
                        line=line,
                        name=name,
                        kind=kind
                    ))
            
            return tags
                
        except Exception as e:
            if verbose:
                io.tool_warning(f"Error parsing {fname}: {e}")
            return []
            
    except ImportError:
        # Fall back to simple regex extraction if grep_ast is not available
        if verbose:
            io.tool_warning("grep_ast not available, using regex fallback")
        
        try:
            with open(fname, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
                
            tags = []
            
            # Simple regex patterns for common constructs
            patterns = {
                "python": {
                    "class": r"^class\s+(\w+)",
                    "function": r"^def\s+(\w+)",
                    "method": r"^\s+def\s+(\w+)",
                },
                "javascript": {
                    "class": r"^class\s+(\w+)",
                    "function": r"^function\s+(\w+)",
                    "method": r"^\s+(\w+)\s*\([^)]*\)\s*{",
                },
                "typescript": {
                    "class": r"^class\s+(\w+)",
                    "function": r"^function\s+(\w+)",
                    "method": r"^\s+(\w+)\s*\([^)]*\)\s*{",
                    "interface": r"^interface\s+(\w+)",
                },
            }
            
            # Use language-specific patterns if available, otherwise use generic ones
            lang_patterns = patterns.get(language, {})
            
            for line_num, line in enumerate(content.splitlines(), 1):
                for kind, pattern in lang_patterns.items():
                    match = re.match(pattern, line)
                    if match:
                        name = match.group(1)
                        tags.append(Tag(
                            rel_fname=rel_fname,
                            fname=fname,
                            line=line_num,
                            name=name,
                            kind=kind
                        ))
            
            return tags
                
        except Exception as e:
            if verbose:
                io.tool_warning(f"Error parsing {fname} with regex: {e}")
            return []
            
    return []


def get_tags(fname: str, rel_fname: str, cache, io: Any, verbose: bool = False) -> List[Tag]:
    """
    Get tags for a file, using the cache if available.
    
    This is a wrapper around get_tags_raw that handles caching.
    """
    if not os.path.isfile(fname):
        return []
    
    # Get file modification time for cache validation
    mtime = os.path.getmtime(fname)
    
    # Try to get from cache first
    cached_tags = cache.get_cached_tags(rel_fname, mtime)
    if cached_tags is not None:
        return cached_tags
    
    # Extract tags and cache them
    tags = get_tags_raw(fname, rel_fname, io, verbose)
    cache.save_tags_to_cache(rel_fname, mtime, tags)
    
    return tags
