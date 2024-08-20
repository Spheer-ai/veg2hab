import time

import pytest

from veg2hab.io.cli import CLIInterface

TIMED = "timed"
SLOW = "slow"
SLOW_OPTION = f"--run-{SLOW}"


def pytest_sessionstart(session: pytest.Session) -> None:
    """Configure the CLI Interface"""
    CLIInterface.get_instance()


def pytest_configure(config):
    # Expliciet definieren van markers
    config.addinivalue_line(
        "markers", f"{TIMED}: mark test as slow to run, only run with --slow"
    )
    config.addinivalue_line("markers", f"{SLOW}: mark test to show its execution time")


def pytest_addoption(parser):
    # Toevoegen SLOW_OPTION
    parser.addoption(
        SLOW_OPTION, action="store_true", default=False, help="Run slow tests"
    )


def pytest_collection_modifyitems(config, items):
    # Als SLOW_OPTION niet is gegeven, skip tests met SLOW marker
    if not config.getoption(SLOW_OPTION):
        skip_slow = pytest.mark.skip(reason=f"Need {SLOW_OPTION} option to run")
        for item in items:
            if SLOW in item.keywords:
                item.add_marker(skip_slow)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    start_time = time.time()
    outcome = yield  # This runs the test
    duration = time.time() - start_time

    if TIMED in item.keywords:
        minutes = int(duration // 60)
        seconds = duration % 60
        if minutes > 0:
            print(
                f"\nTest {item.name} took {minutes} minutes and {seconds:.4f} seconds"
            )
        else:
            print(f"\nTest {item.name} took {seconds:.4f} seconds")
