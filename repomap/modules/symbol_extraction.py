#!/usr/bin/env python3
"""
Symbol extraction and processing for RepoMap.
"""
import os
import re
from collections import defaultdict, Counter
from typing import List, Dict, Set, Tuple, Any, Optional

from .models import Tag


def get_ranked_tags(tags: List[Tag], 
                   chat_rel_fnames: Set[str] = None, 
                   mentioned_fnames: Set[str] = None,
                   mentioned_idents: Set[str] = None) -> Tuple[List[Tag], Dict[str, int]]:
    """
    Rank tags based on various criteria.
    
    Args:
        tags: List of tags extracted from files
        chat_rel_fnames: Set of file names mentioned in the chat
        mentioned_fnames: Set of additional file names to highlight
        mentioned_idents: Set of identifiers mentioned in the chat
        
    Returns:
        Tuple of (ranked_tags, importance_scores)
    """
    if chat_rel_fnames is None:
        chat_rel_fnames = set()
    if mentioned_fnames is None:
        mentioned_fnames = set()
    if mentioned_idents is None:
        mentioned_idents = set()
    
    # Track which tags define which symbols
    defines = defaultdict(set)
    definitions = defaultdict(set)
    
    # Find all mentions and definitions
    for tag in tags:
        key = (tag.rel_fname, tag.name, tag.kind)
        
        # Track which file defines each symbol
        defines[tag.name].add(tag.rel_fname)
        definitions[key].add(tag)
    
    # Compute importance scores
    scores = defaultdict(int)
    
    for tag in tags:
        # Base score for being a symbol
        scores[tag] = 1
        
        # Bonus for being in a chat file
        if tag.rel_fname in chat_rel_fnames:
            scores[tag] += 10
        
        # Bonus for being in a mentioned file
        if tag.rel_fname in mentioned_fnames:
            scores[tag] += 5
        
        # Bonus for being a mentioned identifier
        if tag.name in mentioned_idents:
            scores[tag] += 10
        
        # Bonus for declarations
        if tag.kind in ["class", "function", "method", "variable", "constant", 
                      "interface", "enum", "struct", "module"]:
            scores[tag] += 3
        
        # Special bonus for main functions
        if tag.name == "main" and tag.kind == "function":
            scores[tag] += 5
    
    # Sort by score (descending) and then by line number (ascending)
    ranked_tags = sorted(
        tags, 
        key=lambda t: (-scores[t], t.rel_fname, t.line)
    )
    
    return ranked_tags, scores


def generate_symbol_map(ranked_tags: List[Tag], 
                       scores: Dict[Tag, int], 
                       max_tokens: int,
                       token_counter=None) -> str:
    """
    Generate a map of symbols from ranked tags.
    
    Args:
        ranked_tags: List of ranked tags
        scores: Dictionary of importance scores
        max_tokens: Maximum number of tokens to include
        token_counter: Function to count tokens in a string
        
    Returns:
        String containing the symbol map
    """
    if token_counter is None:
        # Default token counter (rough estimate)
        token_counter = lambda s: len(s) // 4
    
    # Group tags by file
    files = defaultdict(list)
    for tag in ranked_tags:
        files[tag.rel_fname].append(tag)
    
    # Sort files by importance (sum of tag scores)
    file_scores = {
        fname: sum(scores[tag] for tag in tags)
        for fname, tags in files.items()
    }
    
    # Sort by score and then by name
    sorted_files = sorted(
        files.keys(), 
        key=lambda f: (-file_scores[f], f)
    )
    
    # Build the map
    result = ["Repository symbols:"]
    token_count = token_counter("\n".join(result))
    
    for fname in sorted_files:
        # Check if adding this file would exceed the token limit
        file_line = f"\nFile: {fname}"
        file_tokens = token_counter(file_line)
        
        if token_count + file_tokens > max_tokens:
            break
            
        result.append(file_line)
        token_count += file_tokens
        
        # Sort tags by line number
        file_tags = sorted(files[fname], key=lambda t: t.line)
        
        for tag in file_tags:
            # Format the tag
            tag_line = f"  {tag.line}: {tag.kind} {tag.name}"
            tag_tokens = token_counter(tag_line)
            
            if token_count + tag_tokens > max_tokens:
                # Add ellipsis to indicate truncation
                result.append("  ...")
                token_count += token_counter("  ...")
                break
                
            result.append(tag_line)
            token_count += tag_tokens
    
    # Add note about token limit if necessary
    if token_count >= max_tokens:
        result.append("\n(Symbol map truncated due to token limit)")
    
    return "\n".join(result)