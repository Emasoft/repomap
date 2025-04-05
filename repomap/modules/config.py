#!/usr/bin/env python3
"""
Configuration constants and settings for RepoMap.
"""
import sqlite3
import os
import re
from pathlib import Path

# Cache configuration
CACHE_VERSION = 3
SQLITE_ERRORS = (sqlite3.OperationalError, sqlite3.DatabaseError, OSError)

# Minimum token size
MIN_TOKEN_SIZE = 4096

# Default files to include/exclude
DEFAULT_IGNORE = [
    '.git', '.hg', '.svn', '.DS_Store', 
    'node_modules', 'venv', '.venv', '__pycache__', 
    '*.pyc', '.repomap.tags.cache*',
    '.temp', 'temp_*', '**/temp_*'
]

# Patterns for test files and directories
TEST_PATTERNS = [
    '**/test_*.py', '**/tests/**', '**/test/**', '**/testing/**',
    '**/*_test.py', '**/*_test.js', '**/*_test.ts', 
    '**/*.test.js', '**/*.test.ts', '**/*.spec.js', '**/*.spec.ts',
    '**/jest.config.js', '**/pytest.ini', '**/conftest.py',
    '**/unittest/**', '**/jasmine/**', '**/karma.conf.js'
]

# Patterns for documentation files and directories
DOC_PATTERNS = [
    '**/docs/**', '**/doc/**', '**/documentation/**',
    '**/*.md', '**/*.rst', '**/*.txt', '**/man/**',
    '**/examples/**', '**/README*', '**/CHANGELOG*', 
    '**/LICENSE*', '**/CONTRIBUTING*'
]

# Patterns for git-related files and directories
GIT_PATTERNS = [
    '**/.git/**', '**/.github/**', '**/.gitignore', '**/.gitattributes',
    '**/.gitmodules', '**/CODEOWNERS'
]

# Language to file extension mappings
LANGUAGE_EXTENSIONS = {
    'python': ['.py'],
    'javascript': ['.js'],
    'typescript': ['.ts', '.tsx'],
    'java': ['.java'],
    'c': ['.c', '.h'],
    'cpp': ['.cpp', '.hpp', '.cc', '.hh', '.cxx', '.hxx'],
    'csharp': ['.cs'],
    'go': ['.go'],
    'ruby': ['.rb'],
    'rust': ['.rs'],
    'php': ['.php'],
    'swift': ['.swift'],
}

# File important paths patterns
IMPORTANT_FILE_PATTERNS = [
    r"^\.github/workflows/.*\.ya?ml$",
    r"^\.gitlab-ci\.ya?ml$",
    r"^\.circleci/config\.ya?ml$",
    r"^\.travis\.ya?ml$",
    r"^appveyor\.ya?ml$",
    r"^Dockerfile$",
    r"^docker-compose\.ya?ml$",
    r"^Makefile$",
    r"^CMakeLists\.txt$",
    r"^package\.json$",
    r"^pyproject\.toml$",
    r"^setup\.py$",
    r"^requirements\.txt$",
    r"^Cargo\.toml$",
    r"^build\.gradle$",
    r"^pom\.xml$",
    r"^webpack\.config\.js$",
    r"^tsconfig\.json$",
    r"^vite\.config\.js$",
    r"^\.npmrc$",
]

# Root important file names
ROOT_IMPORTANT_FILES = {
    "README.md", 
    "LICENSE", 
    ".gitignore",
    ".dockerignore",
    ".editorconfig",
    ".env.example",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
    "CODE_OF_CONDUCT.md",
}

# File count multiplier for map token allocation
FILE_COUNT_MULTIPLIER = 8