"""Constants for Cactus Needle."""

from typing import Final

DOMAIN: Final = "cactus_needle"
PLATFORMS: Final = ["binary_sensor", "button", "conversation", "sensor"]

CONF_FALLBACK_AGENT: Final = "fallback_agent"
CONF_TIMEOUT: Final = "timeout"

DEFAULT_URL: Final = "http://macmini:18080"
DEFAULT_TIMEOUT: Final = 5.0

DATA_CLIENT: Final = "client"
