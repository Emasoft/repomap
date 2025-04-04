#!/usr/bin/env python3
"""
Visualization and formatting utilities for RepoMap.
"""
import os
import re
import random
from collections import defaultdict
from typing import List, Dict, Set, Any, Optional, Tuple, Union

from .models import Tag, TreeNode
from .file_utils import get_rel_fname


def get_random_color() -> str:
    """Generate a random color for visualization."""
    r = random.randint(100, 240)
    g = random.randint(100, 240)
    b = random.randint(100, 240)
    return f"#{r:02x}{g:02x}{b:02x}"


def format_tag_list(tags: List[Tag]) -> str:
    """Format a list of tags for display."""
    result = []
    
    # Group tags by file
    file_tags = defaultdict(list)
    for tag in tags:
        file_tags[tag.rel_fname].append(tag)
    
    # Sort files
    sorted_files = sorted(file_tags.keys())
    
    for file in sorted_files:
        result.append(f"File: {file}")
        
        # Sort tags by line number
        sorted_tags = sorted(file_tags[file], key=lambda t: t.line)
        
        for tag in sorted_tags:
            result.append(f"  Line {tag.line}: {tag.kind} {tag.name}")
        
        result.append("")
    
    return "\n".join(result)


def build_tree(root: str, files: List[str]) -> TreeNode:
    """Build a tree representation of the repository."""
    if not files:
        return None
        
    tree_root = TreeNode("Repository Root", True)
    
    for file in files:
        try:
            if not os.path.exists(file):
                continue
                
            rel_path = get_rel_fname(root, file)
            parts = rel_path.split(os.sep)
            
            current = tree_root
            # Process all directories in the path
            for i, part in enumerate(parts):
                if i < len(parts) - 1:
                    current = current.add_child(part, True)
                else:
                    # Last part is the file
                    current.add_child(part, False)
        except Exception:
            pass
    
    return tree_root


def render_tree(tree: TreeNode, max_depth: int = 5) -> str:
    """Render a tree as a string."""
    if not tree:
        return "No files found."
        
    return f"Repository Tree:\n{tree.print_tree(max_depth=max_depth)}"


def format_file_list_by_extension(files: List[str], root: str) -> str:
    """Format a list of files grouped by extension."""
    if not files:
        return "No files found."
    
    # Group by extension
    by_ext = defaultdict(list)
    
    for file in files:
        rel_path = get_rel_fname(root, file)
        ext = os.path.splitext(rel_path)[1]
        if not ext:
            ext = "no extension"
        by_ext[ext].append(rel_path)
    
    # Sort extensions and files within each extension
    result = ["Repository contents:"]
    result.append("")
    
    for ext in sorted(by_ext.keys()):
        ext_display = ext
        if ext == "no extension":
            ext_display = "files without extension"
        else:
            ext_display = f"{ext} files"
            
        result.append(f"{ext_display}:")
        
        for file in sorted(by_ext[ext]):
            result.append(f"  {file}")
            
        result.append("")
    
    return "\n".join(result)


def format_token_count(count: int) -> str:
    """Format a token count."""
    if count < 1000:
        return str(count)
    elif count < 10000:
        return f"{count / 1000:.1f}k"
    else:
        return f"{count // 1000}k"