#!/bin/bash

# Make sure we're in the project root directory
cd "$(dirname "$0")"

# Parse command line arguments
publish=0
increment="patch"
push=0

while [[ $# -gt 0 ]]; do
    case $1 in
        --publish)
            publish=1
            shift
            ;;
        --increment)
            increment=$2
            shift 2
            ;;
        --push)
            push=1
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--publish] [--increment patch|minor|major] [--push]"
            exit 1
            ;;
    esac
done

# Use conda to activate the environment
# Note: This expects that the user has already configured conda
# and has created a RepoMap environment
if command -v conda &> /dev/null; then
  ENV_NAME="RepoMap"
  echo "Using conda environment: $ENV_NAME"
  eval "$(conda shell.bash hook)"
  conda activate $ENV_NAME
else
  echo "Conda not found. Please install miniconda or anaconda."
  exit 1
fi

# Step 1: Run tests with coverage
echo "Running tests with coverage..."
coverage erase
python -m coverage run -m pytest tests/

# Step 2: Check coverage threshold (set to 45% for now, can be increased later)
echo "Checking coverage threshold..."
coverage report --fail-under=45
if [ $? -ne 0 ]; then
  echo "Tests failed or coverage below threshold. Build aborted."
  exit 1
fi

# Step 3: Increment version if requested
if [[ "$increment" != "none" ]]; then
    echo "Incrementing version ($increment)..."
    bumpversion $increment
    if [ $? -ne 0 ]; then
        echo "Error: Failed to increment version"
        exit 1
    fi
    echo "Version incremented successfully."
fi

# Step 4: Build the package
echo "Building package..."
python -m build
if [ $? -ne 0 ]; then
    echo "Error: Build failed"
    exit 1
fi

echo "Build completed successfully."

# Step 5: Publish to PyPI if requested
if [ $publish -eq 1 ]; then
    echo "Publishing to PyPI..."
    if [ -z "$PYPI_API_TOKEN" ]; then
        echo "Error: PYPI_API_TOKEN environment variable not set"
        exit 1
    fi
    python -m twine upload --username __token__ --password $PYPI_API_TOKEN dist/*
    if [ $? -ne 0 ]; then
        echo "Error: Failed to publish to PyPI"
        exit 1
    fi
    echo "Package published to PyPI successfully."
else
    echo "To publish to PyPI, run:"
    echo "  PYPI_API_TOKEN=your_token python -m twine upload dist/*"
    echo "Or run this script with --publish flag:"
    echo "  ./build_and_publish.sh --publish"
fi

# Step 6: Push to GitHub if requested
if [ $push -eq 1 ]; then
    echo "Pushing to GitHub..."
    # Check if GITHUB_PERSONAL_TOKEN is set
    if [ -z "$GITHUB_PERSONAL_TOKEN" ]; then
        echo "Warning: GITHUB_PERSONAL_TOKEN environment variable not set, pushing with current credentials"
        git push origin master --tags
    else
        # Set up a temporary config with the token
        git config --local credential.helper "!f() { echo username=x-access-token; echo password=$GITHUB_PERSONAL_TOKEN; }; f"
        git push origin master --tags
    fi
    if [ $? -ne 0 ]; then
        echo "Error: Failed to push to GitHub"
        exit 1
    fi
    echo "Changes pushed to GitHub successfully."
else
    echo "To push to GitHub, run:"
    echo "  git push origin master --tags"
    echo "Or run this script with --push flag:"
    echo "  ./build_and_publish.sh --push"
fi

echo "All tasks completed successfully."