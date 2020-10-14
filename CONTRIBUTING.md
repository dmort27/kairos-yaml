# Contributing

This is a guide for contributing to this project. Due to the small size and informal nature of development, some things in here are recommendations instead of requirements. Parts that are required will be prefixed with _Required_. Some requirements are not marked because they are automatically enforced by other requirements.

This document and all appropriate configuration files are mutable. Changes should be made if needed.

## General

Most relevant guidelines would be redundant to include here. Some points are included in this document for emphasis or convenience. In general, the following sources cover most relevant practices:

- [ISI Boston development advice](https://paper.dropbox.com/folder/show/ISI-Boston-e.1gg8YzoPEhbTkrhvQwJ2zzy60o53gTY4qOR2Fskl5nzICtv7afqa)
- [Contributing to FlexNLP](https://github.com/isi-vista/isi-flexnlp/blob/master/docs/coding_standards.rst)

In general, try to be internally consistent. This project does not need to adhere to strict standards in all cases, but self-consistency is an informal standard to adhere to.

## Coding process

Branch names, commit messages, issues, and pull requests should all be descriptive with appropriate spelling, grammar, and style.

Commit messages should follow the style outlined in "[How to Write a Git Commit Message](https://chris.beams.io/posts/git-commit/)". In most cases only a single line is necessary, as additional detail can be put in a PR.

For non-trivial fixes, an issue should generally be created, especially if an experiment's results need to be documented somewhere.

If a new branch is created for an issue, the branch name should start with the issue number. For example, a branch for issue #42, "Lorem ipsum dolor sit amet", should be called something like `42-lorem-ipsum`.

When changes are made to code, the appropriate documentation should be updated.

When refactoring or documenting, make sure to fully understand what is going on. Unintentional changes or incorrect documentation could be worse than leaving code as-is.

### Pull Requests

_Currently, all development is being done a single branch. This will change once it is more mature._

Most development should be done on separate branches that are merged with PRs.

Fill in the PR description and include the following:

- Mention of related issue, if one exists
- Summary of changes made
- Explanation behind changes, such as problem being solved, rationale for choosing specific solution, etc.
- Testing done to verify changes, when needed

Before submitting a pull request (and before merge, if changes have been made), ensure `make precommit` runs without warnings.

_Required_: Each PR requires passing CI tests and at least one approving review.

### Git

_Required_: Never `git push --force` because it can accidentally overwrite new commits. If similar behavior is desired, `git push --force-with-lease`.

If the commit history is messy and the change is not complex enough to warrant complete history, probably squash the commits:

- Example: `git rebase -i HEAD~5`, where `5` is the number of previous commits to review and possibly squash
- Squashing can easily cause issues. If you don't deeply understand squashing, just squash everything after a given commit into that commit.
- Don't squash too frequently. If you make changes to a PR, then it would be good to see exactly what the revisions are. As a rule of thumb, if squashing is desired, squash before the PR and before merging.

In most cases, rebase before merging. The following commands are an example of rebasing:

- `git checkout master`
- `git pull`
- `git checkout example-branch`
- `git rebase origin/master`
- `git push --force-with-lease`

## Coding conventions

To check code quality, run `make check`. Before committing, run `make precommit` to format and check code.

_(Not set up yet)_ Travis CI is set up to automatically check code in the repository. PRs cannot be merged unless all checks pass. If checks do not pass, then either the code or the check themselves need to be changed.

All files should use Linux-style newlines.

Indentation should be with spaces, not tabs. Most files should be indented with 2 spaces, with Python being the main exception.

The maximum line length is 100 characters.

### Python

Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) except for the maximum line length.

Use double quotes, except where it would require more escapes than using single quotes.

Imports of the form `from _ import _` and `import _` should be sorted together. In addition, multiple imports in a single line should be sorted.

For documentation, use type annotation and Google-style documentation comments ([Google Python Style Guide - 3.8 Comments and Docstrings](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)). When using type annotations, be as general as possible (e.g. prefer `Mapping` over `Dict` and `Sequence` over `List`). Using immutable types such as `Mapping` means the type checker can warn if the code modifies an object that it shouldn't be modifying.

The following tools are used for automatic formatting and checking:

- [Black](https://black.readthedocs.io/en/stable/) autoformats code.
- [flake8](https://flake8.pycqa.org/en/stable/) checks code formatting and style.
- [isort](https://isort.readthedocs.io/en/stable/) sorts and checks imports.
- [mypy](http://mypy-lang.org/) checks types.
- [pydocstyle](http://www.pydocstyle.org/en/stable/) checks code documentation formatting and style.
- [pylint](https://www.pylint.org/) checks code formatting and style.

### Shell

_Required_: All shell scripts must be written in Bash.

Use the shebang `#!/usr/bin/env bash` to ensure the proper version of Bash is used.

Start files with `set -euxo pipefail` to prevent common errors.

Use [Shellcheck](https://www.shellcheck.net/) to catch errors and improve style.

### Markdown

Follow [GitHub-Flavored Markdown](https://github.github.com/gfm/).

Formatting is checked with Prettier (see later section).

### YAML

YAML is automatically checked with [yamllint](https://yamllint.readthedocs.io/en/stable/index.html).

Formatting is checked with Prettier (see later section).

### Prettier

[Prettier](https://prettier.io/) should be manually used to automatically format and check Markdown and YAML files. It should be called with `make prettier-fix` for formatting and `make prettier-check` for checking. While it could be used automatically, there are currently some issues that prevent its easy integration.

## Testing

In most cases, running the program is the only testing needed.

A manual test plans should be written.

There is currently no automated testing, but it might be useful in the future.
