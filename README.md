# DRFT

> _Django REST Framework Toolkit (DRFT)_

[![Code style: black][black-badge]][black-repo]
[![codecov][codecov-badge]][codecov-page]
![Build][gh-build-badge]

## Installation

`pip install drft`

## Local Development

### Pyenv
It's recommended that you use `pyenv`, which you can read about more [here][pyenv].

[pyenv-installer][pyenv-installer]
```bash
curl -L https://github.com/pyenv/pyenv-installer/raw/master/bin/pyenv-installer | bash
```

### Install Poetry

This project uses poetry, which you can read more about [here][poetry].
Install it using the following command.

```bash
curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python -
```
More instructions [here][poetry-installation]

### Install the dependencies:

```shell
poetry install
```

Install pre-commit hooks:

```shell
poetry run pre-commit install --hook-type commit-msg
poetry run pre-commit install
```

### Running Tests:

```shell
tox
```


[black-badge]: https://img.shields.io/badge/code%20style-black-000000.svg
[black-repo]: https://github.com/psf/black
[codecov-badge]: https://codecov.io/gh/anthonyalmarza/drft/branch/main/graph/badge.svg?token=JRCC98L3FG
[codecov-page]: https://codecov.io/gh/anthonyalmarza/drft
[gh-build-badge]: https://github.com/anthonyalmarza/drft/workflows/Build/badge.svg

[poetry]: https://python-poetry.org
[poetry-installation]: https://python-poetry.org/docs/#installation

[pyenv]: https://github.com/pyenv/pyenv
[pyenv-installer]: https://github.com/pyenv/pyenv-installer
