import pytest

from rich.console import Console
from rich.traceback import install

def pytest_configure(config):
    config.addinivalue_line("markers", "integration: mark test as integration")
    install(show_locals=True)

@pytest.fixture(scope="session")
def console():
    return Console()