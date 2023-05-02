# Developer Guide

Thank you for your interest in contributing to terminal_sync!

If you haven't already done so, we recommend you start by learning [how terminal_sync has evolved](architecture.md#design-evolution) and [how terminal_sync currently works](architecture.md#how-terminal_sync-works). This will help explain some of the design decisions and orient you to the codebase.

When you're ready to start coding, you'll follow this general process:

1. Fork the repo
2. Clone your fork
3. [Setup your environment](#setting-up-your-environment)
    1. Install PDM
    2. Use PDM to install all dependencies
    3. Install pre-commit
4. Write code or make changes
5. Write tests
6. [Run tests](#pytest)
7. Update [documentation](#documentation) and the CHANGELOG
8. Commit code (...fix any [pre-commit](#pre-commit) failures, re-add, and re-commit code)
9. Submit a pull request

---

## Tools

- Git
- Python 3.10+ and pip
- [PDM](https://pdm.fming.dev/latest/)
      - This is a package dependency manager and general project management utility, similar to Poetry
- [pre-commit](https://pre-commit.com/)
      - A framework for managing multi-language pre-commit hooks
      - This is used to automate tedious tasks and enforce consistent standards
- Code editor
      - [Visual Studio Code](https://code.visualstudio.com/) with the [Python extension](https://marketplace.visualstudio.com/items?itemName=ms-python.python) (recommended)

---

## Setting Up Your Environment

### PDM

```bash
# Install PDM
pip install pdm

# Install all dependencies
pdm install

# Install pre-commit hooks
pdm run pre-commit install
```

Use `pdm list` to display a list of installed dependencies and their versions or `pdm list --graph` to display this information in tree format with sub-dependencies appropriately nested.

### Integrated Development Environment (IDE)

While it's not required, we recommend using Visual Studio Code (VS Code) as your IDE. To configure VS Code, create a file named `terminal_sync.code-workspace` in the root project directory. Add the following to it, then run `pdm code`. This will start your VS Code instance within the PDM environment, allowing it to find locally installed packages without additional configuration.

```json
{
    "folders": [
        {
            "path": "."
        }
    ],
    "settings": {
        "python.defaultInterpreterPath": ".\\.venv\\Scripts\\python.exe"
    }
}
```

While developing, you'll typically run the server through your IDE to enable features like the debugger; however, if you need to start the server from command-line, use `pdm serve` or `pdm run python -m terminal_sync`.

### pytest

To run tests, use `pdm test` or `pdm run pytest`.

### pre-commit

pre-commit, as the name may suggest, only checks files that are tracked by git; be sure to `git add` any relevant files before running the checks.

The pre-commit configuration and hooks are contained in `.pre-commit-config.yaml`.

By default, pre-commit will run when you make a commit; however, you can also run the checks manually using `pdm check` or `pdm run pre-commit run --all-files`.

### Documentation

The terminal_sync documentation is written in Markdown, located under `docs/`, built using `mkdocs`, hosted using GitHub Pages, and automatically deployed using a GitHub Actions workflow (`.github/workflows/documentation.yml`).

To view the documentation locally, run `pdm docs` or `pdm run mkdocs serve [--dev-addr <IP>:<PORT>]`.

## Conventions

Whenever possible, use `pyproject.toml` for all external tool configurations, including pre-commit hooks. This centralizes the configuration settings and ensures consistency in case developers run the same tool manually and with pre-commit.

Please refer to the [Style Guide](style_guide.md) for stylistic conventions.
