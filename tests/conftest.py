import pytest

from veg2hab.io.cli import CLIInterface


def pytest_sessionstart(session: pytest.Session) -> None:
    """Configure the CLI Interface"""
    CLIInterface.get_instance()
