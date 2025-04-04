# Publishing Guide for RepoMap

This document describes how to build, test, and publish the RepoMap package to PyPI.

## Prerequisites

- Make sure you have the conda environment set up:
  ```bash
  conda activate RepoMap
  ```

- Ensure all dependencies are installed:
  ```bash
  pip install -r requirements.txt
  pip install -e .
  ```

- For publishing, you need to have the PyPI token set as an environment variable:
  ```bash
  export PYPI_API_TOKEN=your_token_here
  ```

- For GitHub operations, you need to have the GitHub token set:
  ```bash
  export GITHUB_PERSONAL_TOKEN=your_token_here
  ```

## Building and Publishing Locally

### Using the build script

The project includes a build script that handles testing, version increments, building, and publishing:

```bash
# Run tests and build without publishing
./build_and_publish.sh

# Increment version (patch, minor, or major)
./build_and_publish.sh --increment patch

# Build and publish to PyPI
./build_and_publish.sh --publish

# Build, publish, and push to GitHub
./build_and_publish.sh --publish --push
```

### Manual steps

If you prefer to run the steps manually:

1. Run tests with coverage:
   ```bash
   coverage run -m pytest tests/
   coverage report --fail-under=45
   ```

2. Increment version using bumpversion:
   ```bash
   bumpversion patch  # or 'minor' or 'major'
   ```

3. Build the package:
   ```bash
   python -m build
   ```

4. Publish to PyPI:
   ```bash
   python -m twine upload --username __token__ --password $PYPI_API_TOKEN dist/*
   ```

5. Push to GitHub:
   ```bash
   git push origin master --tags
   ```

## GitHub Actions Workflows

This project uses GitHub Actions to automate testing, building, and publishing:

### Automated Testing

The `python-ci.yml` workflow runs on every push to `master` and `dev` branches and on pull requests to `master` and `release` branches. It:

1. Runs tests on multiple Python versions
2. Performs linting with ruff
3. Checks types with mypy
4. Generates a coverage report
5. Builds and verifies the package

### Publishing to PyPI

The `publish.yml` workflow can be triggered in two ways:

1. Automatically when a release is published on GitHub
2. Manually through the GitHub Actions interface with a choice of version increment type

This workflow:
1. Runs tests and coverage checks
2. Performs linting and type checking
3. Increments the version if triggered manually
4. Builds the package
5. Publishes to PyPI using the stored secret token
6. Pushes changes back to GitHub if needed

## Version Management

We use [bump2version](https://github.com/c4urself/bump2version) to handle version increments. The current version is defined in:

- `repomap/__init__.py` as `__version__`
- `pyproject.toml` as `version`
- `setup.py` as `version`

When you run `bumpversion patch` (or minor/major), it updates all these files and creates a git tag automatically.

## Release Checklist

Before publishing a new version:

1. Make sure all tests pass with good coverage
2. Update the CHANGELOG.md with notable changes
3. Check that documentation is up to date
4. Verify that the package builds correctly
5. Test the package installation in a clean environment

## Troubleshooting

If you encounter issues during publishing:

- Check that token environment variables are set correctly
- Ensure you have the latest setuptools, build, and twine packages
- Verify that all required files are included in MANIFEST.in
- Check the GitHub Actions logs for detailed error messages