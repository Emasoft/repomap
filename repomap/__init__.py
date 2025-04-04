"""
RepoMap: A tool for mapping and visualizing code repositories

RepoMap analyzes your codebase and builds a structured representation of files,
functions, classes, and their relationships to help navigate and understand large
codebases.

Copyright 2023-2025 Emasoft

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import os
import sys
from pathlib import Path

__version__ = "0.1.0"

# Add constants for backwards compatibility
CACHE_VERSION = 3

# Core functionality (backwards compatibility)
from .repomap import RepoMap, Tag
from .models import Model, get_token_counter
from .io_utils import InputOutput, default_io

# Importing main function for backward compatibility
try:
    from .repomap import main
except ImportError:
    from .__main__ import main

# For backward compatibility
def filename_to_lang(filename):
    """Map filename to language."""
    ext = os.path.splitext(filename)[1].lower()
    ext_to_lang = {
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'typescript',
        '.java': 'java',
        '.c': 'c',
        '.h': 'c',
        '.cpp': 'cpp',
        '.hpp': 'cpp',
        '.cs': 'csharp',
        '.rs': 'rust',
        '.go': 'go',
        '.rb': 'ruby',
        '.php': 'php',
        '.sh': 'bash',
        '.html': 'html',
        '.css': 'css',
        '.md': 'markdown',
        '.json': 'json',
        '.yml': 'yaml',
        '.yaml': 'yaml',
        '.xml': 'xml'
    }
    return ext_to_lang.get(ext)

# New modular exports
# Import specific utilities from modules
from .modules.models import TreeNode, Tag
from .modules.file_utils import (
    get_rel_fname, get_mtime, find_src_files,
    expand_globs, find_common_root, is_text_file,
    is_binary_file, is_image_file
)
from .modules.parsers import get_tags, get_tags_raw, get_scm_fname
from .modules.visualization import (
    format_tag_list, format_file_list_by_extension, format_token_count
)

try:
    from grep_ast.tsl import get_language, get_parser
except ImportError:
    # Fall back to dummy implementations
    def get_language(lang_id):
        return None
    
    def get_parser(lang_id):
        return None

__all__ = [
    # Core
    "RepoMap", "Tag", "TreeNode",
    "Model", "get_token_counter",
    "InputOutput", "default_io",
    "main", "CACHE_VERSION",
    
    # File utilities
    "find_src_files", "get_rel_fname", "get_mtime", 
    "expand_globs", "find_common_root",
    "is_text_file", "is_binary_file", "is_image_file",
    "filename_to_lang",
    
    # Parsing
    "get_tags", "get_tags_raw", "get_scm_fname",
    "get_language", "get_parser",
    
    # Visualization
    "format_tag_list", "format_file_list_by_extension", "format_token_count"
]
