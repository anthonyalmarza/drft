import toml
from drft import __version__


def test_version():
    version = toml.load("./pyproject.toml")["tool"]["poetry"]["version"]
    assert __version__ == version
