"""Config flow for Cactus Needle."""

from __future__ import annotations

from typing import Any

import probatio
from homeassistant.components import conversation
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_URL
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
from homeassistant.helpers.service_info.hassio import HassioServiceInfo

from .client import CactusNeedleClient, CactusNeedleError
from .const import (
    CONF_FALLBACK_AGENT,
    CONF_TIMEOUT,
    DEFAULT_TIMEOUT,
    DEFAULT_URL,
    DOMAIN,
)


def _schema(defaults: dict[str, Any]) -> probatio.Schema:
    return probatio.Schema(
        {
            probatio.Required(
                CONF_URL, default=defaults.get(CONF_URL, DEFAULT_URL)
            ): TextSelector(TextSelectorConfig(type=TextSelectorType.URL)),
            probatio.Optional(
                CONF_FALLBACK_AGENT,
                default=defaults.get(CONF_FALLBACK_AGENT),
            ): EntitySelector(EntitySelectorConfig(domain=conversation.DOMAIN)),
            probatio.Required(
                CONF_TIMEOUT, default=defaults.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)
            ): NumberSelector(
                NumberSelectorConfig(
                    min=1,
                    max=30,
                    step=0.5,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement="s",
                )
            ),
        }
    )


async def _validate(hass, data: dict[str, Any]) -> None:
    client = CactusNeedleClient(
        async_get_clientsession(hass),
        data[CONF_URL].strip(),
        float(data[CONF_TIMEOUT]),
    )
    await client.status()


class CactusNeedleConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a Cactus Needle config flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._hassio_discovery: HassioServiceInfo | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            user_input[CONF_URL] = user_input[CONF_URL].strip().rstrip("/")
            self._async_abort_entries_match({CONF_URL: user_input[CONF_URL]})
            try:
                await _validate(self.hass, user_input)
            except CactusNeedleError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(title="Cactus Needle", data=user_input)
        return self.async_show_form(
            step_id="user",
            data_schema=_schema(user_input or {}),
            errors=errors,
        )

    async def async_step_hassio(
        self, discovery_info: HassioServiceInfo
    ) -> ConfigFlowResult:
        """Handle discovery from the Cactus Needle App."""
        await self.async_set_unique_id(discovery_info.uuid)
        self._abort_if_unique_id_configured()
        host = discovery_info.config["host"]
        port = int(discovery_info.config["port"])
        url = f"http://{host}:{port}"
        for entry in self._async_current_entries():
            if entry.data.get(CONF_URL) == url or entry.options.get(CONF_URL) == url:
                return self.async_abort(reason="already_configured")
        self._hassio_discovery = discovery_info
        self.context.update(
            {
                "title_placeholders": {"name": discovery_info.name},
                "configuration_url": (
                    f"homeassistant://config/app/{discovery_info.slug}/info"
                ),
            }
        )
        return await self.async_step_hassio_confirm()

    async def async_step_hassio_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm a discovered Cactus Needle App."""
        if self._hassio_discovery is None:
            return self.async_abort(reason="cannot_connect")
        host = self._hassio_discovery.config["host"]
        port = int(self._hassio_discovery.config["port"])
        data = {
            CONF_URL: f"http://{host}:{port}",
            CONF_TIMEOUT: DEFAULT_TIMEOUT,
        }
        errors: dict[str, str] = {}
        if user_input is not None:
            if fallback := user_input.get(CONF_FALLBACK_AGENT):
                data[CONF_FALLBACK_AGENT] = fallback
            try:
                await _validate(self.hass, data)
            except CactusNeedleError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=self._hassio_discovery.name,
                    data=data,
                )
        return self.async_show_form(
            step_id="hassio_confirm",
            data_schema=probatio.Schema(
                {
                    probatio.Optional(CONF_FALLBACK_AGENT): EntitySelector(
                        EntitySelectorConfig(domain=conversation.DOMAIN)
                    )
                }
            ),
            description_placeholders={"app": self._hassio_discovery.name},
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return CactusNeedleOptionsFlow(config_entry)


class CactusNeedleOptionsFlow(OptionsFlow):
    """Handle Cactus Needle options."""

    def __init__(self, config_entry) -> None:
        self._entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        current = {**self._entry.data, **self._entry.options}
        if user_input is not None:
            user_input[CONF_URL] = user_input[CONF_URL].strip().rstrip("/")
            try:
                await _validate(self.hass, user_input)
            except CactusNeedleError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=_schema(user_input or current),
            errors=errors,
        )
