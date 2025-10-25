# Contributing Guide

Thank you for your interest in Symphra Scheduler! This guide explains how to set up your environment and contribute effectively.

## Development Environment Setup

### 1. Fork and Clone

```bash
# Fork the repository to your GitHub account
# Then clone to local
git clone https://github.com/your-username/symphra-scheduler.git
cd symphra-scheduler

# Add upstream
git remote add upstream https://github.com/getaix/symphra-scheduler.git
```

### 2. Install uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 3. Install dependencies

```bash
# Create a virtual env and install all dependencies
uv sync --all-groups --extra all
```

### 4. Install hooks

```bash
# Install pre-commit hooks (optional)
uv run pre-commit install
```

## Development Workflow

### 1. Create a branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

### 2. Write code

- Follow existing code style
- Add necessary type hints
- Write Chinese comments and docstrings
- Ensure all tests pass

### 3. Run tests

```bash
# Run all tests
uv run pytest

# Run tests with coverage report
uv run pytest --cov=symphra_scheduler --cov-report=html

# Open the coverage report
open htmlcov/index.html
```

### 4. Code checks

```bash
# Ruff lint
uv run ruff check symphra_scheduler/

# Ruff format check
uv run ruff format --check symphra_scheduler/

# Auto-fix
uv run ruff check --fix symphra_scheduler/
uv run ruff format symphra_scheduler/

# Type check
uv run mypy symphra_scheduler/
```

### 5. Commit code

```bash
# Stage changes
git add .

# Commit (use meaningful messages)
git commit -m "feat: add new feature XXX"
# or
git commit -m "fix: fix issue XXX"
```

Commit message conventions:
- `feat:` - new feature
- `fix:` - bug fix
- `docs:` - documentation update
- `test:` - tests
- `refactor:` - code refactor
- `chore:` - build/tooling

### 6. Push and create PR

```bash
# Push to your fork
git push origin feature/your-feature-name

# Then create a Pull Request on GitHub
```

## Code Guidelines

### Python code

- Use Python 3.11+
- 100% type hint coverage
- Follow PEP 8
- Max line length: 100 characters

### Comments and docstrings

- All public APIs must have docstrings
- Docstrings should be in Chinese
- Use Google-style docstrings

Example:

```python
def my_function(param1: str, param2: int) -> bool:
    """Short description.

    Detailed explanation of what the function does.

    Args:
        param1: Description of the first parameter
        param2: Description of the second parameter

    Returns:
        Description of the return value

    Raises:
        ValueError: When this error is raised

    示例:
        >>> result = my_function("test", 42)
        >>> print(result)
        True
    """
    pass
```

### Tests

- All new features must include tests
- Keep coverage at 80%+
- Use pytest and pytest-asyncio
- Test function names use Chinese descriptions

Example:

```python
import pytest
from symphra_scheduler import Scheduler

class TestScheduler:
    """调度器测试类。"""

    def test_scheduler_creation(self):
        """测试调度器创建。"""
        scheduler = Scheduler()
        assert scheduler is not None

    @pytest.mark.asyncio
    async def test_scheduler_start_stop(self):
        """测试调度器启动和停止。"""
        scheduler = Scheduler()
        # test logic
```

## Documentation

### Preview locally

```bash
# Install doc dependencies
uv pip install -e '.[docs]'

# Start docs server
uv run mkdocs serve

# Open http://127.0.0.1:8000
```

### Build docs

```bash
uv run mkdocs build
```

### Structure

```
docs/
├── index.md                 # Overview
├── quickstart.md            # Quickstart
├── guides/                  # Guides
│   ├── logging.md
│   ├── monitoring.md
│   └── backends.md
├── api/                     # API docs
│   ├── scheduler.md
│   ├── task.md
│   └── ...
└── changelog.md             # Changelog
```

## Release Process (Maintainers)

### 1. Update version

Edit `pyproject.toml`:

```toml
[project]
version = "1.0.0"  # update version
```

### 2. Update CHANGELOG

Add the new version changes to `CHANGELOG.md`.

### 3. Create tag

```bash
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0
```

### 4. Automatic release

After pushing the tag, GitHub Actions will automatically:
- Run all tests
- Build distributions
- Publish to PyPI

### 5. Manual release (optional)

```bash
# Build distributions
uv build

# Check distributions
twine check dist/*

# Upload to PyPI
twine upload dist/*
```

## Reporting Issues

### Bug Reports

When creating an issue, please include:

1. Problem description — clear and concise
2. Reproduction steps — detailed steps
3. Expected behavior — what you expected
4. Actual behavior — what happened
5. Environment:
   - Python version
   - Symphra Scheduler version
   - Operating system
6. Relevant logs — errors, stack traces, etc.

### Feature Requests

When creating an issue, please include:

1. Feature description — what you want
2. Use case — why you need it
3. Suggested implementation — your ideas (optional)

## Code of Conduct

- Respect all contributors
- Keep discussions friendly and constructive
- Newcomers are welcome
- Respond to PRs and Issues in a timely manner

## Getting Help

If you have questions:

1. Read the [documentation](https://getaix.github.io/symphra-scheduler)
2. Search existing [Issues](https://github.com/getaix/symphra-scheduler/issues)
3. Create a new Issue to ask

## Acknowledgements

Thanks to all developers contributing to Symphra Scheduler! Your work makes the project better.

---

Thanks again for your contribution! 🎉
