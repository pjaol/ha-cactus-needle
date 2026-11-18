"""Diagnostics for Cactus Needle."""

from .const import DATA_CLIENT, DOMAIN


async def async_get_config_entry_diagnostics(hass, entry):
    """Return non-sensitive diagnostics."""
    coordinator = hass.data[DOMAIN][entry.entry_id].get("coordinator")
    return {
        "entry": {
            "data": dict(entry.data),
            "options": dict(entry.options),
        },
        "server": {
            "available": bool(coordinator and coordinator.last_update_success),
            "model": (
                coordinator.data.model
                if coordinator and coordinator.data is not None
                else None
            ),
            "server_version": (
                coordinator.data.version
                if coordinator and coordinator.data is not None
                else None
            ),
            "last_latency_ms": (
                coordinator.data.last_latency_ms
                if coordinator and coordinator.data is not None
                else None
            ),
        },
        "client_loaded": DATA_CLIENT in hass.data[DOMAIN][entry.entry_id],
    }
