import contextlib
import os


@contextlib.contextmanager
def set_env(**environ):
    """
    After https://stackoverflow.com/questions/2059482/temporarily-modify-the-current-processs-environment

    Temporarily set the process environment variables.

    Usage:

    with set_env(ENV_VAR=VALUE):
        *do things here, ENV_VAR will have value VALUE*

    *outside of the with block, ENV_VAR will have its original value*
    """
    old_environ = dict(os.environ)
    os.environ.update(environ)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(old_environ)
