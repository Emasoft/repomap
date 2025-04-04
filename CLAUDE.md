# RepoMap Development Guide
Project Template: `https://github.com/allenai/python-package-template`
License: Apache 2.0
Author: Emasoft
Name: repomap

## Project requirements
- Use of conda virtual environment
- use of git and github cli tools to manage the versioning
- automated testing
- strict coverage enforcement
- semantic versioning
- automatic version increments
- both local and remote PyPI automatic package deployment (using github workflows)
- template aligned with the `allenai/python-package-template` (url: `https://github.com/allenai/python-package-template`)
- Use scripts and tools to run tests, check coverage, updates your version file, commits the changes, and creates a Git tag automatically.
- Increments version using bumpversion
- Automatically run the following linters before building: ruff, mypy, shellcheck
- Project is tailored for running on mac os Sequoia with python versions from 3.9 to 3.14

## Environment Setup with Conda

The RepoMap project uses Conda for environment management. Follow these steps:

### 1. Initial Conda Setup

If you don't have conda installed:
```bash
brew install miniconda  # For macOS
```

### 2. Environment Management

```bash
# List all available environments
conda doctor
conda env list
conda info

# Create a new environment for this project
conda create -n RepoMap python=3.9

# Activate the environment
conda activate RepoMap

# Deactivate when done
conda deactivate
```

### 3. Install Dependencies and Tools

With the RepoMap environment activated:
```bash
# Install project dependencies
pip install -r requirements.txt
pip install -e .

# Install development tools
pip install pytest pytest-cov coverage build twine bumpversion ruff mypy black
```

### 4. Using Environment in Scripts
Shell scripts are all in the ./scripts folder.
All shell scripts in this project (run_coverage.sh, build_and_publish.sh, etc.) are configured to:
1. Automatically activate the "RepoMap" conda environment
2. Execute within that environment
3. No need to manually activate the environment before running scripts

> **Note:** Conda does not use .venv or venv local subfolders. The environment is stored in the conda installation directory.

## Running RepoMap
```bash
repomap <file_paths>             # Using installed command
python -m repomap <file_paths>   # Module execution
```

## Command-line Options
```bash
repomap --verbose <file_paths>   # Enable verbose output
repomap --tokens 4096 <files>    # Set token limit for map size
repomap --debug <file_paths>     # Show debug info about language parsers
repomap --help                   # Show all options
```

## Code Editing
- If you need to examine or modify the code, create or move files and folders, prefer writing and executing quick python scripts to using shell command.
- Write quick python scripts to do any task you need, since python is more reliable.
- **IMPORTANT**: Always use the `repomap/ast_parser.py` script to determine the exact start and ending line of functions or classes you want to read or edit. First run it in signatures-only mode to list all elements in the source file, then use the name of the function/class to run it again in full mode to get the exact line numbers. This prevents errors caused by viewing random code sections and getting truncated functions or classes.
- Always delete the quick python scripts you wrote after using them successfully to complete the task or step they were created for. Do not clutter the repo folder with useless temporary python scripts.
- Be sure to commit to git often and revert back if you found that a change broke the working code or caused a regression.
- Always make tests before writing new functions, working in a way similar to the Test-Driven-Development methodology. TTD is the optimal way to add new features or change the existing ones. If unittest is not enough, use pytest with fixtures.
- Document every change to the project and its current state of development in an .md file dedicated in the project folder. Keep it always updated, so you can read it to get an immediate review of the project status and development targets in progress.

## Debugging and Troubleshooting
- If no map is generated, use `--verbose` to see detailed logs
- Use `--debug` to check which language parsers are available
- Check that query files exist in the `repomap/queries/` directory
- Look for cache issues in the `.repomap.tags.cache.v4` directory

## Testing

### Running Tests Using Included Scripts

```bash
# Run all tests with coverage analysis
./scripts/run_coverage.sh

# Run linting checks
./scripts/lint.sh

# Run tests, coverage, and build process
./scripts/build_and_publish.sh
```

### Running Tests Manually

Make sure the RepoMap conda environment is activated:

```bash
conda activate RepoMap

# Run tests using pytest with coverage
python -m pytest tests/ --cov=repomap
python -m coverage run -m pytest tests/
coverage report

```

## Code Style Guidelines
- **Imports**: Standard library first, third-party packages second, local modules last
- **Naming**: Classes use CamelCase, functions/variables use snake_case, constants use UPPER_CASE
- **Docstrings**: Use for documenting functions (see utils.py for examples)
- **Error Handling**: Use try/except with specific exception types; implement fallback mechanisms
- **Caching**: Follow versioning pattern for breaking changes (see CACHE_VERSION)

## Structure
- Main functionality in repomap.py (RepoMap class)
- Helper utilities in utils.py (Spinner, temp directories, etc.)
- Special file filtering in special.py
- Debug utilities in dump.py
- Language queries in repomap/queries/tree-sitter-language-pack/
- Tests in tests/ directory (unit, CLI, and integration tests)
- Test data samples in tests/samples/
- Test data files in tests/data/
- Coverage reports in tests/coverage/

## Project Dependencies
- Always use Homebrew and Pip3 to install dependencies. But activate the right conda virtual environment first.
- Core: diskcache, pygments, tqdm, networkx, importlib-resources
- Parsing: grep-ast, tree-sitter and language packs
- Token handling: tiktoken, tokenizers
- Utilities: pydantic, typer, twine, bumpversion
- Linter: ruff, mypy, shellcheck
- Testing: unittest (built-in), pytest, pytest-cov, coverage

## Linters commands:
bash: `shellcheck --severity=error --extended-analysis=true" --lint-cmd`
python: `ruff check --ignore E203,E402,E501,E266,W505,F841,F842,F401,W293,I001,UP015,C901,W291 --isolated --fix --output-format full`
python: `mypy --no-warn-unused-ignores --no-warn-unused-configs --no-warn-return-any --no-warn-unreachable --show-error-context --show-error-end --pretty --install-types --no-color-output --non-interactive`

## Testing Stack and CI/CD

RepoMap uses a comprehensive testing and CI/CD pipeline:

### Local Testing and Coverage Tools

- **pytest** - Main testing framework
- **coverage.py** - Code coverage measurement
- **pytest-cov** - Pytest integration with coverage
- **ruff** - Fast Python linter
- **mypy** - Static type checker


### Continuous Integration

GitHub Actions workflows are configured to:
1. Run tests on multiple Python versions
2. Enforce code quality through linting and type checking
3. Generate coverage reports
4. Build and verify the package

### Coverage Reporting

The project is set up to:
1. Automatically generate coverage reports during CI/CD
2. Generate local HTML reports for detailed analysis
3. Enforce minimum coverage thresholds

### Using the Coverage Tools

```bash
# Run the coverage script
./scripts/run_coverage.sh

# View the HTML report
open tests/coverage/index.html

# Generate XML report for CI integration
coverage xml
```

---

## GitHub Setup and Automation

### Step 6: Install GitHub CLI and Authenticate

```bash
brew install gh
echo $GITHUB_PERSONAL_TOKEN | gh auth login --with-token
```

### Step 7: Create a New Repository from the Template

```bash
gh repo create <your-repo-name> --template allenai/python-package-template --private
cd <your-repo-name>
```

### Step 8: Personalize the Repository

Run the provided setup script:

```bash
python scripts/setup.py
```

### Step 9: Configure Git User

```bash
git config user.name "Emasoft"
git config user.email "713559+Emasoft@users.noreply.github.com"
```

### Step 10: Push Initial Commit

```bash
git add .
git commit -m "Initial commit"
git branch -M main
git push -u origin main
```

---

## Generate Tokens and Configure GitHub Secrets

### Generate PyPI API Token

1. Go to [PyPI account settings](https://pypi.org/manage/account/).
2. Under the **API tokens** tab, click **Add API token**.
3. Name the token clearly (e.g., `<your-package-name>-token`) and set its scope to the specific package.
4. Copy the generated token immediately (it will be shown only once).

### Configure GitHub Secrets

In your GitHub repository, navigate to **Settings > Secrets and Variables > Actions** and add these secrets:

- **`PYPI_API_TOKEN`** (the token generated above)
- **`GITHUB_PERSONAL_TOKEN`** (your GitHub personal access token)
- **`CODECOV_TOKEN`** (token from [Codecov](https://codecov.io))

The following tokens are also available locally as environment variables secrets:
- **`PYPI_API_TOKEN`** (PyPi token)
- **`GITHUB_PERSONAL_TOKEN`** (GitHub personal access token)
- **`CODECOV_TOKEN`** (token from [Codecov](https://codecov.io))

Never expose or write explicitly to file any of the above tokens. They must stay secret.

---

## Automated Scripts

RepoMap includes several utility scripts to automate common development tasks:

### 1. Environment Setup

Use `./scripts/setup_conda_env.sh` to create and configure the conda environment:

```bash
./scripts/setup_conda_env.sh
```

This script:
- Creates a "RepoMap" conda environment if it doesn't exist
- Installs all project dependencies
- Installs development tools

### 2. Code Coverage

Use `./scripts/run_coverage.sh` to run tests and generate coverage reports:

```bash
./scripts/run_coverage.sh
```

This script:
- Activates the RepoMap conda environment
- Runs all tests with coverage
- Generates console and HTML reports

### 3. Linting and Code Quality

Use `./scripts/lint.sh` to run linting checks:

```bash
./scripts/lint.sh
```

This script:
- Activates the RepoMap conda environment
- Runs ruff for linting
- Runs black for code formatting (if installed)
- Runs mypy for type checking

### 4. Build and Publish

Use `./scripts/build_and_publish.sh` to build, test, and potentially publish the package:

```bash
./scripts/build_and_publish.sh
```

This script:
- Activates the RepoMap conda environment
- Runs tests with coverage
- Verifies coverage meets the threshold
- Increments version using bumpversion
- Builds the package
- (Optionally, when uncommented) Publishes to PyPI
- (Optionally, when uncommented) Pushes changes to GitHub

To enable publishing, edit the script to uncomment the publishing steps.

### GitHub Actions Workflow for PyPI Deployment

Create `.github/workflows/publish.yml`:

```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install pytest pytest-cov coverage build twine
      - name: Run tests and coverage
        run: |
          pytest --cov=my_package tests/
          coverage report --fail-under=80
      - name: Build package
        run: |
          python -m build
      - name: Publish to PyPI
        run: |
          python -m twine upload dist/* -u __token__ -p ${{ secrets.PYPI_API_TOKEN }}
```

---

## Automate Version Increments with Semantic Versioning

Install `bumpversion` locally:

```bash
pip install bumpversion
```

Configure `bumpversion` in your project root (`setup.cfg`):

```ini
[bumpversion]
current_version = 0.0.1
commit = True
tag = True

[bumpversion:file:my_package/version.py]
```

Increment version using:

```bash
bumpversion patch  # or minor / major
```



---




