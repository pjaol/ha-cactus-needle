"""Status coordinator for Cactus Needle."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import CactusNeedleClient, CactusNeedleError, CactusStatus

_LOGGER = logging.getLogger(__name__)


class CactusNeedleCoordinator(DataUpdateCoordinator[CactusStatus]):
    """Poll the local Cactus server."""

    def __init__(self, hass, client: CactusNeedleClient) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            name="Cactus Needle",
            update_interval=timedelta(seconds=30),
        )
        self.client = client

    async def _async_update_data(self) -> CactusStatus:
        try:
            return await self.client.status()
        except CactusNeedleError as err:
            raise UpdateFailed(str(err)) from err
