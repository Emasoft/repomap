#!/usr/bin/env python3
"""
Data models and structures used by RepoMap.
"""
from collections import namedtuple

# Tag data structure for code symbols
Tag = namedtuple("Tag", ["rel_fname", "fname", "line", "name", "kind"])

class TreeNode:
    """Node in a file system tree representation."""
    def __init__(self, name, is_dir=False):
        self.name = name
        self.is_dir = is_dir
        self.children = {}
        self.content = ""
    
    def add_child(self, name, is_dir=False):
        """Add a child node."""
        if name not in self.children:
            self.children[name] = TreeNode(name, is_dir)
        return self.children[name]
    
    def print_tree(self, prefix="", is_last=True, max_depth=5, current_depth=0):
        """Print the tree recursively."""
        if current_depth > max_depth:
            return ""
            
        connector = "└── " if is_last else "├── "
        result = prefix + connector + self.name + ("/" if self.is_dir else "") + "\n"
        
        # New prefix for children
        new_prefix = prefix + ("    " if is_last else "│   ")
        
        # Sort children: directories first, then files
        sorted_children = sorted(
            [(name, node) for name, node in self.children.items()],
            key=lambda x: (not x[1].is_dir, x[0].lower())
        )
        
        for i, (name, child) in enumerate(sorted_children):
            is_last_child = i == len(sorted_children) - 1
            result += child.print_tree(new_prefix, is_last_child, max_depth, current_depth + 1)
            
        return result