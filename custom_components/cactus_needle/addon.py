"""Supervisor App management for Cactus Needle."""

from __future__ import annotations

from aiohasupervisor.models import StoreAddRepository
from homeassistant.components.hassio import AddonManager
from homeassistant.components.hassio.handler import get_supervisor_client
from homeassistant.core import HomeAssistant

from .const import ADDON_NAME, ADDON_SLUG, LOGGER, REPOSITORY_URL


def _normalize_repository_url(url: str) -> str:
    """Normalize a repository URL for comparison."""
    return url.rstrip("/").removesuffix(".git")


async def async_get_repository_slug(hass: HomeAssistant) -> str | None:
    """Return this project's Supervisor repository slug when registered."""
    repositories = await get_supervisor_client(hass).store.repositories_list()
    expected = _normalize_repository_url(REPOSITORY_URL)
    for repository in repositories:
        candidates = (repository.source, repository.url)
        if any(
            _normalize_repository_url(candidate) == expected for candidate in candidates
        ):
            return repository.slug
    return None


async def async_ensure_repository(hass: HomeAssistant) -> str:
    """Register the App repository if needed and return its actual slug."""
    if slug := await async_get_repository_slug(hass):
        return slug

    client = get_supervisor_client(hass)
    await client.store.add_repository(StoreAddRepository(repository=REPOSITORY_URL))
    if slug := await async_get_repository_slug(hass):
        return slug
    raise RuntimeError("Supervisor registered the repository without returning it")


def get_addon_manager(hass: HomeAssistant, repository_slug: str) -> AddonManager:
    """Return an App manager using the Supervisor-assigned repository slug."""
    return AddonManager(
        hass,
        LOGGER,
        ADDON_NAME,
        f"{repository_slug}_{ADDON_SLUG}",
    )
