# Style Guide

Consistent style is important for clean and maintainable code. Unless contradicted by the guidance below, all contributors should follow [PEP 8 – Style Guide for Python Code](https://peps.python.org/pep-0008/) and any other applicable PEP standards.

Additionally, this project uses a variety of [pre-commit](https://pre-commit.com/) hooks to automatically lint, format, and otherwise clean up code. Pull requests will not be accepted unless the pre-commit checks pass or convincing justification is provided.

---

## Line Length

Lines should be 120 characters or less.

We are no longer technologically limited to 80 characters per line. A 120 character limit works well with modern tools, improves readability, and makes better use of horizontal screen space, allowing developers to see more code at once.

## Imports

Most imports should be placed at the top of the file as stated in PEP 8; however, third-party packages may be imported within the code if they are part of an optional and non-critical workflow. Users should not be required to install unnecessary packages if they don't intend to use the associated functionality, and the program should function properly without these optional packages.

Each import should be on a separate line to minimize merge conflicts (see [reorder_python_imports](https://github.com/asottile/reorder_python_imports#why-this-style)).

Imports should be grouped into (at least) three sections: Standard Libraries, Third-party Libraries, and Internal Libraries. This is enforced by the `isort` pre-commit hook.

## Comments

terminal_sync uses Google Style docstrings. Click [here](https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html) for some examples.
