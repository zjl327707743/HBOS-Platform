"""Knowledge-domain tests use fake providers and no real network."""
import socket
import pytest

@pytest.fixture(autouse=True)
def no_provider_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError('Synthetic test attempted an actual network connection')
    monkeypatch.setattr(socket.socket, 'connect', blocked)
    monkeypatch.setattr(socket.socket, 'connect_ex', blocked)
