# RepoMap Development Guide

## Setup and Installation
```bash
pip install -r requirements.txt  # Install dependencies
pip install -e .                 # Install in development mode
```

## Running RepoMap
```bash
python -m repomap <file_paths>   # Generate repo map for specified files
```

## Development Commands
```bash
black .                          # Format code
isort .                          # Sort imports
mypy repomap                     # Type checking
pytest                           # Run tests
```

## Code Style Guidelines
- **Imports**: Standard library first, third-party packages second, local modules last
- **Naming**: Classes use CamelCase, functions/variables use snake_case, constants use UPPER_CASE
- **Docstrings**: Use for documenting functions (see utils.py for examples)
- **Error Handling**: Use try/except with specific exception types; implement fallback mechanisms
- **Caching**: Follow versioning pattern for breaking changes (see CACHE_VERSION)

## Structure
- Main functionality in RepoMap class
- Helper utilities in utils.py (Spinner, temp directories, etc.)
- Special file filtering in special.py
- Debug utilities in dump.py

## Project Dependencies
- Primary: diskcache, pygments, tqdm, networkx, importlib-resources
- Required: grep-ast (for parsing code repositories)
- Development: black, isort, mypy, pytest (configured in pyproject.toml)