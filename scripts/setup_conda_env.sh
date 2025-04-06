#!/bin/bash

# Set the environment name 
ENV_NAME="RepoMap"

# Check if conda is installed
if ! command -v conda &> /dev/null; then
    echo "Conda not found. Please install miniconda or anaconda."
    exit 1
fi

# Create conda environment if it doesn't exist
if ! conda env list | grep -q "^$ENV_NAME "; then
    echo "Creating conda environment '$ENV_NAME'..."
    conda create -y -n $ENV_NAME python=3.12
else
    echo "Conda environment '$ENV_NAME' already exists."
fi

# Activate the environment
eval "$(conda shell.bash hook)"
conda activate $ENV_NAME

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt
pip install -e .

# Install development tools
echo "Installing development tools..."
pip install pytest pytest-cov coverage build twine bumpversion ruff mypy black

echo "Conda environment '$ENV_NAME' is ready!"
echo "To activate it, run: conda activate $ENV_NAME"