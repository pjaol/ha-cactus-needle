#!/usr/bin/env python3
"""Small production HTTP wrapper around Cactus Needle.

The server deliberately exposes only health, model metadata, completion, and
reset. Model upload and fine-tuning are not network-accessible.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import threading
import time
from dataclasses import asdict, dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

try:
    from importlib.metadata import version

    SERVER_VERSION = version("cactus-compute")
except Exception:  # pragma: no cover - metadata differs in source checkouts
    SERVER_VERSION = "unknown"

LOGGER = logging.getLogger("cactus_needle_server")
MAX_BODY_BYTES = 256 * 1024
MAX_QUERY_CHARS = 4096
MAX_TOOLS = 64


@dataclass
class RuntimeStats:
    """Non-sensitive runtime statistics."""

    requests: int = 0
    errors: int = 0
    resets: int = 0
    last_latency_ms: float | None = None


class NeedleEngine:
    """Thread-safe persistent Needle model."""

    def __init__(self, weights: str | None = None, generation: int = 3) -> None:
        self.weights = weights
        self.generation = generation
        self.name = Path(weights).name if weights else f"needle-{generation} (base)"
        self.lock = threading.Lock()
        self.tools_json: str | None = None
        self.agent: Any = None
        self.started = time.monotonic()
        self.stats = RuntimeStats()

    def load(self) -> None:
        """Load the default model once at service startup."""
        from cactus import Cactus

        with self.lock:
            self.agent = Cactus(
                tools=[],
                weights=self.weights,
                generation=self.generation,
                stateless=True,
            )
            self.tools_json = "[]"

    def complete(self, tools: list[dict[str, Any]], query: str) -> dict[str, Any]:
        """Complete one routing request."""
        from cactus import Cactus

        tools_json = json.dumps(tools, sort_keys=True, separators=(",", ":"))
        started = time.monotonic()
        with self.lock:
            try:
                if self.agent is None or self.tools_json != tools_json:
                    if self.agent is not None:
                        self.agent.close()
                    self.agent = Cactus(
                        tools=tools,
                        weights=self.weights,
                        generation=self.generation,
                        stateless=True,
                    )
                    self.tools_json = tools_json
                else:
                    self.agent.reset()
                result = self.agent.complete(query)
                self.stats.requests += 1
                self.stats.last_latency_ms = round(
                    (time.monotonic() - started) * 1000, 2
                )
                return result
            except Exception:
                self.stats.errors += 1
                raise

    def reset(self) -> None:
        """Unload the current agent; the next request reloads it."""
        with self.lock:
            if self.agent is not None:
                self.agent.close()
            self.agent = None
            self.tools_json = None
            self.stats.resets += 1

    def health(self) -> dict[str, Any]:
        """Return non-sensitive service health."""
        return {
            "status": "ok",
            "service": "cactus-needle-ha",
            "version": SERVER_VERSION,
            "model": self.name,
            "generation": self.generation,
            "loaded": self.agent is not None,
            "uptime_seconds": round(time.monotonic() - self.started, 1),
            "stats": asdict(self.stats),
        }

    def close(self) -> None:
        """Close native resources."""
        self.reset()


def _error(message: str) -> dict[str, str]:
    return {"error": message}


def validate_completion(payload: Any) -> tuple[list[dict[str, Any]], str]:
    """Validate a completion request without interpreting tool schemas."""
    if not isinstance(payload, dict):
        raise ValueError("request body must be a JSON object")
    query = payload.get("query")
    tools = payload.get("tools")
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")
    if len(query) > MAX_QUERY_CHARS:
        raise ValueError(f"query exceeds {MAX_QUERY_CHARS} characters")
    if not isinstance(tools, list):
        raise ValueError("tools must be a JSON array")
    if len(tools) > MAX_TOOLS:
        raise ValueError(f"tools exceeds {MAX_TOOLS} entries")
    if not all(isinstance(tool, dict) for tool in tools):
        raise ValueError("every tool must be a JSON object")
    return tools, query.strip()


def make_handler(engine: NeedleEngine) -> type[BaseHTTPRequestHandler]:
    """Build a request handler bound to one engine."""

    class Handler(BaseHTTPRequestHandler):
        server_version = "CactusNeedleHA/1"

        def _send_json(self, status: HTTPStatus, payload: Any) -> None:
            data = json.dumps(payload, separators=(",", ":")).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def _read_json(self) -> Any:
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError as err:
                raise ValueError("invalid Content-Length") from err
            if length <= 0 or length > MAX_BODY_BYTES:
                raise ValueError(f"body must be 1..{MAX_BODY_BYTES} bytes")
            try:
                return json.loads(self.rfile.read(length))
            except json.JSONDecodeError as err:
                raise ValueError("invalid JSON") from err

        def do_GET(self) -> None:  # noqa: N802
            path = self.path.partition("?")[0]
            if path == "/health":
                self._send_json(HTTPStatus.OK, engine.health())
            elif path == "/version":
                self._send_json(
                    HTTPStatus.OK,
                    {"service": "cactus-needle-ha", "version": SERVER_VERSION},
                )
            elif path == "/model":
                self._send_json(HTTPStatus.OK, {"name": engine.name})
            else:
                self._send_json(HTTPStatus.NOT_FOUND, _error("not found"))

        def do_POST(self) -> None:  # noqa: N802
            path = self.path.partition("?")[0]
            try:
                if path == "/complete":
                    tools, query = validate_completion(self._read_json())
                    self._send_json(HTTPStatus.OK, engine.complete(tools, query))
                elif path == "/reset":
                    engine.reset()
                    self._send_json(HTTPStatus.OK, {"ok": True})
                else:
                    self._send_json(HTTPStatus.NOT_FOUND, _error("not found"))
            except ValueError as err:
                self._send_json(HTTPStatus.BAD_REQUEST, _error(str(err)))
            except Exception:
                LOGGER.exception("Needle request failed")
                self._send_json(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    _error("inference failed; see server logs"),
                )

        def log_message(self, fmt: str, *args: Any) -> None:
            LOGGER.debug("%s - %s", self.address_string(), fmt % args)

    return Handler


def create_server(host: str, port: int, engine: NeedleEngine) -> ThreadingHTTPServer:
    """Create the threaded HTTP server."""
    return ThreadingHTTPServer((host, port), make_handler(engine))


def main() -> None:
    """Run the service."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=18080)
    parser.add_argument("--weights", default=os.environ.get("CACTUS_WEIGHTS") or None)
    parser.add_argument("--generation", type=int, default=3)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    engine = NeedleEngine(args.weights, args.generation)
    LOGGER.info("Loading %s", engine.name)
    engine.load()
    server = create_server(args.host, args.port, engine)

    def stop(_signum: int, _frame: Any) -> None:
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    LOGGER.info("Ready on http://%s:%d", args.host, args.port)
    try:
        server.serve_forever()
    finally:
        engine.close()
        server.server_close()


if __name__ == "__main__":
    main()
