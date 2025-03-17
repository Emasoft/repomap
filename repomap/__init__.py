"""
RepoMap - A tool for mapping and visualizing code repositories
"""

from pathlib import Path
import sys
import os

# Import directly from the module
from .repomap import RepoMap, find_src_files, get_random_color

__version__ = '0.1.0'
__all__ = ['RepoMap', 'find_src_files', 'get_random_color']