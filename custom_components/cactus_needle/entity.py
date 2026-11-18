"""Shared Cactus Needle entity helpers."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CactusNeedleCoordinator


class CactusNeedleEntity(CoordinatorEntity[CactusNeedleCoordinator]):
    """Base entity for Cactus Needle."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: CactusNeedleCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Cactus Needle",
            manufacturer="Cactus Compute",
            model="Needle intent router",
        )
