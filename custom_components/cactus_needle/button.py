"""Button platform for Cactus Needle."""

from homeassistant.components.button import ButtonEntity

from .const import DOMAIN
from .entity import CactusNeedleEntity


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([CactusNeedleResetButton(coordinator, entry)])


class CactusNeedleResetButton(CactusNeedleEntity, ButtonEntity):
    """Reset the in-memory Cactus agent."""

    _attr_name = "Reset model"
    _attr_icon = "mdi:restart"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_reset"

    async def async_press(self) -> None:
        await self.coordinator.client.reset()
        await self.coordinator.async_request_refresh()
