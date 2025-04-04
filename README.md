# RepoMap

⚠️ **WARNING: This repository is a work in progress and incomplete. Please do not use or download this code yet.** ⚠️

A tool for mapping and visualizing code repositories. RepoMap analyzes your codebase and builds a structured representation of files, functions, classes, and their relationships to help navigate and understand large codebases.

## Project Status

This project is currently under active development and is not ready for use:

- Core functionality is being implemented
- Tests are being developed and fixed
- Documentation is incomplete
- The API is subject to change without notice

Please check back later for a stable release.

## Planned Features

- Analyzes code repositories to identify files, functions, and classes
- Maps relationships between code elements
- Caches results for faster subsequent runs
- Supports multiple programming languages through tree-sitter
- Token-aware splitting for integration with LLMs

## Dependencies

- Python 3.8+
- Requires grep-ast for code parsing
- Uses networkx for relationship mapping
- Caching with diskcache

## Acknowledgements

This project includes code derived from or inspired by [Aider](https://github.com/Aider-AI/aider), an open-source AI pair programming tool that lets developers collaborate with large language models (LLMs) on coding projects. Some of the repository mapping and codebase analysis techniques were adapted from Aider's implementation.

We are grateful to the Aider project and its contributors for their excellent work. If you're interested in AI-assisted programming, please check out the Aider project.

## License

Apache License 2.0 - See the [LICENSE](LICENSE) file for details.

This project contains code derived from the [Aider project](https://github.com/Aider-AI/aider), which is also licensed under the Apache License 2.0.