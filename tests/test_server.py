"""Tests for the standalone Needle service."""

from __future__ import annotations

import json
import threading
from http.client import HTTPConnection

import pytest

from cactus_needle.server import create_server, validate_completion


class FakeEngine:
    name = "needle-test"

    def health(self):
        return {"status": "ok", "model": self.name}

    def complete(self, tools, query):
        return {"success": True, "tools": tools, "query": query}

    def reset(self):
        self.reset_called = True


@pytest.fixture
def service():
    engine = FakeEngine()
    server = create_server("127.0.0.1", 0, engine)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield engine, server.server_address[1]
    server.shutdown()
    server.server_close()
    thread.join()


def request(port, method, path, body=None):
    connection = HTTPConnection("127.0.0.1", port, timeout=2)
    raw = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"} if raw else {}
    connection.request(method, path, raw, headers)
    response = connection.getresponse()
    payload = json.loads(response.read())
    connection.close()
    return response.status, payload


def test_health(service):
    _, port = service
    status, payload = request(port, "GET", "/health")
    assert status == 200
    assert payload["status"] == "ok"


def test_complete(service):
    _, port = service
    status, payload = request(
        port,
        "POST",
        "/complete",
        {"tools": [{"name": "test"}], "query": "hello"},
    )
    assert status == 200
    assert payload["query"] == "hello"


def test_reset(service):
    engine, port = service
    status, payload = request(port, "POST", "/reset")
    assert status == 200
    assert payload == {"ok": True}
    assert engine.reset_called


@pytest.mark.parametrize(
    "payload",
    [None, {}, {"tools": [], "query": ""}, {"tools": {}, "query": "hi"}],
)
def test_validation_rejects_bad_payload(payload):
    with pytest.raises(ValueError):
        validate_completion(payload)
