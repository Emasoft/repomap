# RepoMap Design Documentation

This directory contains design documents, architecture notes, and development status information for the RepoMap project.

## Contents

- `LARGE_REPO_HANDLING.md` - Strategies for handling large repositories
- `coverage_summary.md` - Summary of code coverage metrics
- `test_infrastructure_status.md` - Status of the test infrastructure
- `conversion_summary.md` - Summary of the code refactoring
- `fix_summary.md` - Summary of fixes implemented

## Project Structure

RepoMap is organized in a modular architecture:

- `repomap/` - Main package directory
  - `modules/` - Core modules
    - `core.py` - Core RepoMap class implementation
    - `cache.py` - Cache management
    - `config.py` - Configuration constants
    - `file_utils.py` - File handling utilities
    - `map_generator.py` - Repository map generation
    - `models.py` - Data models
    - `parsers.py` - Code parsing and symbol extraction
    - `symbol_extraction.py` - Symbol processing
    - `visualization.py` - Map formatting
  - `queries/` - Tree-sitter query files for language parsing
  - Other core files

- `tests/` - Test suite
- `samples/` - Sample files for testing
- `scripts/` - Utility scripts

## Development Roadmap

1. Expand language support through additional tree-sitter query files
2. Improve visualization of large codebases
3. Add more comprehensive test coverage
4. Enhance documentation