#!/bin/bash

# Make sure we're in the project root directory
cd "$(dirname "$0")"

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
coverage erase
python -m coverage run -m pytest tests/

# Step 2: Check coverage threshold (set to 45% for now, can be increased later)
coverage report --fail-under=45
if [ $? -ne 0 ]; then
  echo "Tests failed or coverage below threshold. Build aborted."
  exit 1
fi

# Step 3: Increment version automatically using semantic versioning
bumpversion patch  # Use 'major', 'minor', or 'patch' accordingly

# Step 4: Build the package
python -m build

# Step 5: Publish the package to PyPI (commented out for safety, uncomment when ready)
# python -m twine upload dist/* -u __token__ -p $PYPI_API_TOKEN

# Step 6: Push changes including new version and tags to GitHub (commented out for safety)
# git push origin main --tags

echo "Build completed successfully."
echo "To publish, uncomment the twine upload and git push commands in this script."