# Contributing to geompy-display

Thank you for your interest in contributing to geompy-display! This document provides guidelines and instructions for developers.

---

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Setup](#development-setup)
4. [Code Style & Standards](#code-style--standards)
5. [Making Changes](#making-changes)
6. [Commit Guidelines](#commit-guidelines)
7. [Pull Requests](#pull-requests)
8. [Testing](#testing)
9. [Documentation](#documentation)
10. [Pre-commit Configuration](#pre-commit-configuration)

---

## Code of Conduct

Be respectful, inclusive, and professional in all interactions. We are committed to providing a welcoming environment for all contributors.

---

## Getting Started

### Prerequisites

- Python 3.8+
- conda (for managing pythocc-core dependency)
- Git

### Fork & Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/<your-username>/geompy-display.git
cd geompy-display
```

---

## Development Setup

### 1. Create a Conda Environment

```bash
# Create environment with pythocc-core
conda create -n geompy-dev python=3.10 -c conda-forge pythocc-core
conda activate geompy-dev
```

### 2. Install in Development Mode

```bash
# Install package and development dependencies
pip install -e .
pip install pytest pytest-cov ruff mypy
```

### 3. Verify Installation

```bash
# Test that imports work
python -c "from geompy_display import OCCDisplay, ViewCubeConfig; print('OK')"
```

### 4. Set Up Pre-commit Hooks

Pre-commit hooks automatically run checks before each commit to catch issues early:

```bash
# Install pre-commit framework
pip install pre-commit

# Install git hooks from .pre-commit-config.yaml
pre-commit install

# (Optional) Run all checks against all files manually
pre-commit run --all-files
```

This will automatically run Black, type checking, linting, and other checks before each commit — no manual steps needed.

---

## Code Style & Standards

### Type Hints

- **All** function parameters and return types must have type hints
- Use PEP 563 deferred annotations: `from __future__ import annotations` at module top
- Use `TYPE_CHECKING` blocks for type-only imports (avoid circular imports)

```python
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from OCC.Core.AIS import AIS_InteractiveContext
    from PySide6.QtWidgets import QMainWindow

def my_function(ctx: AIS_InteractiveContext, win: QMainWindow) -> None:
    pass
```

### Docstrings

- Use **Google-style** docstrings compatible with MkDocs mkdocstrings
- All public classes, methods, and functions must have docstrings
- Include `Args`, `Returns`, `Raises`, and `Examples` sections where applicable

```python
def display_shape(self, shape: object, update: bool = True) -> object:
    """Display a TopoDS shape in the viewer.

    Wraps the shape in an AIS_Shape and displays it in the context.

    Args:
        shape: OCC TopoDS shape to display.
        update: If True, update the viewer immediately.

    Returns:
        The AIS_Shape display object for further manipulation.

    Raises:
        RuntimeError: If the context is not initialized.

    Examples:
        >>> from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox
        >>> shape = BRepPrimAPI_MakeBox(10, 20, 30).Shape()
        >>> ais = display.DisplayShape(shape)
    """
```

### Code Formatting

- Use **Ruff** for formatting and linting (Black-compatible, line length: 88 characters)
- Pre-commit hooks will format automatically on commit
- Manual formatting:

```bash
ruff format geompy_display/
ruff check --fix geompy_display/
```

### Naming Conventions

- **Classes**: `PascalCase` (e.g., `OCCDisplay`, `ViewCube`)
- **Functions/Methods**: `snake_case` (e.g., `display_shape`, `on_ready`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `GLYPHS`, `POSITIONS`)
- **Private members**: Leading underscore (e.g., `_ais_cube`, `_init_scene`)

### Import Organization

Group imports in this order:

1. `from __future__ import` statements
2. Standard library imports
3. Third-party imports (OCC, PySide6)
4. Local imports
5. `TYPE_CHECKING` block

```python
from __future__ import annotations

import logging
import sys
from typing import Callable, TYPE_CHECKING

from OCC.Core.AIS import AIS_Shape
from PySide6.QtWidgets import QMainWindow

from .viewcube_config import ViewCubeConfig
from .glyphs import GLYPHS

if TYPE_CHECKING:
    from OCC.Core.AIS import AIS_InteractiveContext
```

---

## Making Changes

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
# or for bug fixes:
git checkout -b fix/issue-description
```

### 2. Make Your Changes

- Keep commits small and focused
- Write clear, descriptive commit messages
- Ensure all code follows the style guidelines

### 3. Pre-commit Checks

When you try to commit, pre-commit hooks will automatically:
- Format code with **Ruff** (Black-compatible)
- Lint with **Ruff** (checks code quality)
- Run **mypy** type checking
- Check for trailing whitespace, debug statements, etc.

If any checks fail, fix the issues and commit again:

```bash
# Pre-commit will run automatically on `git commit`
git add .
git commit -m "feat: your feature"

# If checks fail, pre-commit will show errors
# Fix them and re-run:
git commit -m "feat: your feature"
```

If you need to run checks manually:

```bash
# Format and lint with ruff
ruff check --fix geompy_display/
ruff format geompy_display/

# Type check
mypy geompy_display/

# Or run all pre-commit checks
pre-commit run --all-files
```

---

## Commit Guidelines

Use structured commit messages following **Conventional Commits**:

```
<type>: <subject>

<body>

<footer>
```

### Types

- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Code style (formatting, missing semicolons, etc.)
- **refactor**: Code refactoring without feature/bug changes
- **perf**: Performance improvements
- **test**: Test additions or modifications
- **chore**: Build, dependency, or tooling changes

### Example Commits

```
feat: add ViewCube corner offset computation

Add _corner_offset() function to compute world-space cube position
based on viewport dimensions and camera view. Implements responsive
sizing (10% of smaller viewport dimension) for adaptive layout.

Closes #15

---

fix: resolve duplicate docstring in DisplayShape method

The DisplayShape method had overlapping docstrings causing parsing
issues. Removed duplicate docstring while preserving complete
documentation.

---

docs: improve type hints with TYPE_CHECKING blocks

Add TYPE_CHECKING imports to display.py and viewcube.py for better
IDE support. Maintains zero runtime overhead while enabling full
type checking.
```

---

## Pull Requests

### Before Submitting

- [ ] Branch is up-to-date with `main`
- [ ] All tests pass
- [ ] Code is formatted with Black
- [ ] Type checking passes (`mypy`)
- [ ] No unused imports
- [ ] Docstrings are complete and accurate

### PR Description Template

```markdown
## Description

Brief description of changes.

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Related Issues

Closes #123

## Testing

Describe how you tested these changes.

## Checklist

- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex logic
- [ ] Documentation updated
- [ ] Type hints added
- [ ] No new warnings generated
```

### Review Process

1. At least one maintainer review is required
2. Address any requested changes
3. Merge when approved

---

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=geompy_display

# Run specific test file
pytest tests/test_viewcube.py
```

### Writing Tests

- Place tests in `tests/` directory
- Use descriptive test names: `test_<function>_<scenario>`
- Test both happy paths and error cases

```python
def test_viewcube_config_validation():
    """Test that invalid colors raise ValueError."""
    with pytest.raises(ValueError):
        ViewCubeConfig(silver=(2.0, 0.5, 0.5))  # Out of range

def test_corner_offset_top_right():
    """Test corner offset computation for top-right position."""
    result = _corner_offset("top-right", 25.0, 5.0, viewer_widget)
    assert result[0] > 0  # dx positive
    assert result[1] == 0  # dy always 0
```

---

## Documentation

### Module Docstrings

Every module should have a docstring at the top describing its purpose:

```python
"""ViewCube builder and manager for OCC viewer orientation cube.

Manages the construction, positioning, and rendering of a 3D orientation cube
with labeled faces (FRONT, BACK, LEFT, RIGHT, TOP, BOTTOM). Provides automatic
zoom-adaptive line width rendering and screen-corner positioning.

Core Functions:
    _translate: Translate a shape in 3D space.
    _build_text_edges: Build text geometry from stroke glyphs.

Main Class:
    ViewCube: Builds and manages the cube visualization.
"""
```

### Class Docstrings

Include a description of the class, its purpose, and key attributes:

```python
class ViewCube:
    """Builder and manager for 3D orientation cube with labeled faces.

    Constructs a chamfered cube with labeled faces positioned in a screen corner.
    Handles scaling to world-space and zoom-adaptive line width rendering.

    Attributes:
        cfg: ViewCubeConfig controlling appearance and position.
        _ais_cube: AIS_Shape for the cube body (set by show()).
    """
```

### Building Documentation

If using MkDocs:

```bash
pip install mkdocs mkdocs-material mkdocstrings
mkdocs serve
```

---

## Pre-commit Configuration

The project includes a `.pre-commit-config.yaml` file that defines automatic code checks run before each commit.

### Hooks Configured

The project uses **Ruff** (a modern, fast Python linter/formatter):
- **ruff**: Linting and import sorting
- **ruff-format**: Code formatting (Black-compatible)
- **mypy**: Type checking

Plus general pre-commit hooks:
- Trailing whitespace detection
- End-of-file fixers
- YAML/JSON/TOML validation
- Private key detection
- Debug statement detection

### Manual Hook Management

```bash
# Run pre-commit on all files
pre-commit run --all-files

# Run specific hook
pre-commit run ruff --all-files
pre-commit run mypy --all-files

# Bypass pre-commit temporarily (not recommended)
git commit --no-verify

# Update hooks to latest versions
pre-commit autoupdate

# Clean up hook environments
pre-commit clean
```

### Manual Tool Usage

Even without pre-commit, you can run tools manually:

```bash
# Format and lint with ruff
ruff check --fix geompy_display/
ruff format geompy_display/

# Type checking
mypy geompy_display/
```

### Customizing Hooks

Edit `.pre-commit-config.yaml` to:
- Add or remove hooks
- Change hook arguments
- Update hook versions

See `.pre-commit-config.yaml` for current configuration.

---

## Questions?

- Open an issue for bug reports
- Check existing issues before creating new ones
- Contact maintainers for questions about the project direction

---

## License

By contributing, you agree that your contributions will be licensed under the same MIT License as the project.

Thank you for contributing! 🎉
