from django.core.management import execute_from_command_line


def manage_factory(manage_py_path: str):
    """
    Usage:
        manage = manage_factory("my_project/manage.py")
        manage("migrate")
    :param manage_py_path: Path to the project's manage.py file.
    :return: callable
    """

    def _manage(command: str, *args):
        """
        :param command: Any valid django command e.g. migrate
        :param args: options and/or arguments to the command
        :return:
        """
        argv = [manage_py_path, command] + list(args)
        return execute_from_command_line(argv)

    return _manage
