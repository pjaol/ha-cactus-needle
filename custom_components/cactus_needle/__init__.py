"""Cactus Needle integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import CactusNeedleClient
from .const import CONF_TIMEOUT, DATA_CLIENT, DEFAULT_TIMEOUT, DOMAIN, PLATFORMS
from .coordinator import CactusNeedleCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Cactus Needle from a config entry."""
    settings = {**entry.data, **entry.options}
    client = CactusNeedleClient(
        async_get_clientsession(hass),
        settings[CONF_URL],
        float(settings.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)),
    )
    coordinator = CactusNeedleCoordinator(hass, client)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        DATA_CLIENT: client,
        "coordinator": coordinator,
    }
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Cactus Needle."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload after options change."""
    await hass.config_entries.async_reload(entry.entry_id)
