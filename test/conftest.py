import pytest

from rich.console import Console
from rich.traceback import install

from test.fetch_utils import fetch_id_secret

def pytest_configure(config):
    config.addinivalue_line("markers", "integration: mark test as integration")
    install(show_locals=True)

@pytest.fixture(scope="session")
def console():
    return Console()


@pytest.fixture(scope="session")
def secret():
    return fetch_id_secret()["id_prefix_api_secret"]