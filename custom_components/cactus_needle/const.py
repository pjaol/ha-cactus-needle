"""Constants for Cactus Needle."""

import logging
from typing import Final

DOMAIN: Final = "cactus_needle"
PLATFORMS: Final = ["binary_sensor", "button", "conversation", "sensor"]
LOGGER = logging.getLogger(__package__)

ADDON_NAME: Final = "Cactus Needle"
ADDON_SLUG: Final = "cactus_needle"
REPOSITORY_URL: Final = "https://github.com/pjaol/ha-cactus-needle"

CONF_FALLBACK_AGENT: Final = "fallback_agent"
CONF_TIMEOUT: Final = "timeout"

DEFAULT_URL: Final = "http://macmini:18080"
DEFAULT_TIMEOUT: Final = 5.0
ADDON_READY_INTERVAL: Final = 5
ADDON_READY_ATTEMPTS: Final = 120

DATA_CLIENT: Final = "client"
