"""Sensor platform for Cactus Needle."""

from homeassistant.components.sensor import SensorEntity

from .const import DOMAIN
from .entity import CactusNeedleEntity


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([CactusNeedleModelSensor(coordinator, entry)])


class CactusNeedleModelSensor(CactusNeedleEntity, SensorEntity):
    """Show the model currently loaded by Cactus."""

    _attr_name = "Model"
    _attr_icon = "mdi:brain"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_model"

    @property
    def native_value(self):
        return self.coordinator.data.model if self.coordinator.data else None

    @property
    def extra_state_attributes(self):
        if not self.coordinator.data:
            return {}
        return {
            "server_version": self.coordinator.data.version,
            "last_latency_ms": self.coordinator.data.last_latency_ms,
        }
