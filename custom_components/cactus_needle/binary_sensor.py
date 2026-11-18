"""Binary sensor platform for Cactus Needle."""

from homeassistant.components.binary_sensor import BinarySensorEntity

from .const import DOMAIN
from .entity import CactusNeedleEntity


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([CactusNeedleConnectionSensor(coordinator, entry)])


class CactusNeedleConnectionSensor(CactusNeedleEntity, BinarySensorEntity):
    """Report whether the Cactus server is reachable."""

    _attr_name = "Server"
    _attr_icon = "mdi:cactus"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_server"

    @property
    def is_on(self) -> bool:
        return self.coordinator.last_update_success
