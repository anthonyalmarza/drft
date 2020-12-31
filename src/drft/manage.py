import os
from typing import Optional

from django.core.management import execute_from_command_line


def manage_factory(manage_py_path: Optional[str] = None):
    """
    Usage:
        manage = manage_factory("my_project/manage.py")
        manage("migrate")

        manage = manage_factory()  # value from MANGAGE_PY_PATH envvar
        manage("mirgrate")
    :param manage_py_path: Path to the project's manage.py file.
    :return: callable
    """

    def _manage(command: str, *args):
        """
        :param command: Any valid django command e.g. migrate
        :param args: options and/or arguments to the command
        :return:
        """
        try:
            _manage_py_path = manage_py_path or os.environ["MANAGE_PY_PATH"]
        except KeyError as exc:
            raise ValueError(
                "Either call manage_factory with an explicit path or set the "
                "MANAGE_PY_PATH environment variable."
            ) from exc
        argv = [_manage_py_path, command] + list(args)
        return execute_from_command_line(argv)

    return _manage
