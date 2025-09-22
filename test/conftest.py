import pytest

from rich.console import Console
from rich.traceback import install
from _pytest.terminal import TerminalReporter

from test.fetch_utils import fetch_id_secret

def pytest_configure(config):
    config.addinivalue_line("markers", "integration: mark test as integration")
    install(show_locals=True)
    # Asegurarse de que el plugin terminalreporter esté registrado
    if not config.pluginmanager.getplugin("terminalreporter"):
        reporter = TerminalReporter(config)
        config.pluginmanager.register(reporter, "terminalreporter")

@pytest.fixture(scope="session")
def console():
    return Console()


@pytest.fixture(scope="session")
def secret():
    return fetch_id_secret()["id_prefix_api_secret"]


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)