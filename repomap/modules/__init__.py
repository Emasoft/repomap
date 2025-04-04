"""
RepoMap modules package.

This package contains the core functionality of RepoMap, split into
modular components.
"""
from .core import RepoMap
from .models import Tag, TreeNode
from .file_utils import (
    get_rel_fname, get_mtime, find_src_files, 
    expand_globs, find_common_root, is_text_file,
    is_binary_file, is_image_file
)
from .parsers import get_tags, get_tags_raw, get_scm_fname
from .symbol_extraction import get_ranked_tags, generate_symbol_map
from .visualization import (
    format_tag_list, build_tree, render_tree,
    format_file_list_by_extension, format_token_count
)
from .map_generator import get_ranked_tags_map_uncached

__all__ = [
    # Core
    'RepoMap',
    
    # Models
    'Tag', 'TreeNode',
    
    # File utilities
    'get_rel_fname', 'get_mtime', 'find_src_files',
    'expand_globs', 'find_common_root', 'is_text_file',
    'is_binary_file', 'is_image_file',
    
    # Parsers
    'get_tags', 'get_tags_raw', 'get_scm_fname',
    
    # Symbol extraction
    'get_ranked_tags', 'generate_symbol_map',
    
    # Visualization
    'format_tag_list', 'build_tree', 'render_tree',
    'format_file_list_by_extension', 'format_token_count',
    
    # Map generation
    'get_ranked_tags_map_uncached',
]