#!/bin/bash

# Make sure we're in the project root directory
cd "$(dirname "$0")/.."

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

echo "Running ruff..."
ruff check --ignore E203,E402,E501,E266,W505,F841,F842,F401,W293,I001,UP015,C901,W291 --fix .

if command -v black &> /dev/null; then
  echo "Running black..."
  black --check .
fi

echo "Running mypy..."
mypy --no-warn-unused-ignores --no-warn-unused-configs --no-warn-return-any --no-warn-unreachable .

echo "Linting completed."