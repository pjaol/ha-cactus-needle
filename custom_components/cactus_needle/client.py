"""Async client for the Cactus playground HTTP API."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from aiohttp import ClientError, ClientSession


class CactusNeedleError(Exception):
    """Base Cactus Needle client error."""


class CactusNeedleConnectionError(CactusNeedleError):
    """Cactus Needle could not be reached."""


@dataclass(slots=True)
class CactusStatus:
    """Cactus server status."""

    available: bool
    model: str | None = None
    version: str | None = None
    last_latency_ms: float | None = None


TOOLS: list[dict[str, Any]] = [
    {
        "name": "control_home",
        "description": "Control exactly one Home Assistant entity or area now.",
        "parameters": {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": (
                        "Device, entity, area, or room name exactly as spoken "
                        "by the user."
                    ),
                },
                "action": {
                    "type": "string",
                    "enum": ["turn_on", "turn_off", "toggle"],
                },
            },
            "required": ["target", "action"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_home_state",
        "description": (
            "Read the current state of exactly one Home Assistant entity or area."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": (
                        "Device, entity, area, or room name exactly as spoken "
                        "by the user."
                    ),
                }
            },
            "required": ["target"],
            "additionalProperties": False,
        },
    },
    {
        "name": "fallback",
        "description": (
            "Use the general conversation agent when no Home Assistant device "
            "action or state query is requested."
        ),
        "parameters": {
            "type": "object",
            "properties": {"reason": {"type": "string"}},
            "required": ["reason"],
            "additionalProperties": False,
        },
    },
]


class CactusNeedleClient:
    """Client for a persistent Cactus playground server."""

    def __init__(self, session: ClientSession, base_url: str, timeout: float) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    async def status(self) -> CactusStatus:
        """Return server availability and loaded model."""
        try:
            async with asyncio.timeout(self._timeout):
                response = await self._session.get(f"{self._base_url}/health")
                if response.status == 404:
                    response = await self._session.get(f"{self._base_url}/model")
                    response.raise_for_status()
                    payload = await response.json()
                    return CactusStatus(True, payload.get("name"))
                response.raise_for_status()
                payload = await response.json()
        except (TimeoutError, ClientError, ValueError) as err:
            raise CactusNeedleConnectionError(str(err)) from err
        stats = payload.get("stats") or {}
        return CactusStatus(
            True,
            payload.get("model"),
            payload.get("version"),
            stats.get("last_latency_ms"),
        )

    async def complete(self, query: str) -> dict[str, Any]:
        """Classify one utterance."""
        try:
            async with asyncio.timeout(self._timeout):
                response = await self._session.post(
                    f"{self._base_url}/complete",
                    json={"tools": TOOLS, "query": query},
                )
                response.raise_for_status()
                payload = await response.json()
        except (TimeoutError, ClientError, ValueError) as err:
            raise CactusNeedleConnectionError(str(err)) from err
        if not isinstance(payload, dict):
            raise CactusNeedleError("Cactus returned a non-object response")
        return payload

    async def reset(self) -> None:
        """Close and reinitialize the in-memory Cactus agent."""
        try:
            async with asyncio.timeout(self._timeout):
                response = await self._session.post(f"{self._base_url}/reset")
                response.raise_for_status()
        except (TimeoutError, ClientError) as err:
            raise CactusNeedleConnectionError(str(err)) from err
