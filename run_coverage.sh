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

# Clean up previous coverage data
coverage erase

# Run tests with coverage
python -m coverage run -m unittest discover tests/

# Generate reports
echo "==== Coverage Report ===="
python -m coverage report
python -m coverage html

# Calculate total coverage
COVERAGE_OUTPUT=$(python -m coverage report)
TOTAL_LINE=$(echo "$COVERAGE_OUTPUT" | grep "TOTAL")
COVERAGE_PERCENT=$(echo "$TOTAL_LINE" | awk '{print $4}' | sed 's/%//')

# Compare with target
TARGET=80
echo ""
echo "==== Coverage Analysis ===="
echo "Current coverage: $COVERAGE_PERCENT%"
echo "Target coverage: $TARGET%"

if (( $(echo "$COVERAGE_PERCENT < $TARGET" | bc -l) )); then
  echo "⚠️  Coverage is below the target of $TARGET%"
  echo "   See detailed report at: coverage_html_report/index.html"
  exit 1
else
  echo "✅ Coverage meets or exceeds the target of $TARGET%"
  echo "   See detailed report at: coverage_html_report/index.html"
  exit 0
fi