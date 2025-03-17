# RepoMap

A tool for mapping and visualizing code repositories. RepoMap analyzes your codebase and builds a structured representation of files, functions, classes, and their relationships to help navigate and understand large codebases.

## Installation

```bash
pip install -r requirements.txt
python setup.py install
```

## Usage

```bash
python repomap.py <file_paths>
```

## Features

- Analyzes code repositories to identify files, functions, and classes
- Maps relationships between code elements
- Caches results for faster subsequent runs
- Supports multiple programming languages through tree-sitter

## Dependencies

- Python 3.8+
- Requires grep-ast for code parsing
- Uses networkx for relationship mapping
- Caching with diskcache

## License

MIT