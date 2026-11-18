"""Conversation platform for Cactus Needle."""

from __future__ import annotations

import logging
from typing import Any, Literal, override

from homeassistant.components import conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import MATCH_ALL
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.intent import IntentResponseType

from .client import CactusNeedleClient, CactusNeedleError
from .const import CONF_FALLBACK_AGENT, DATA_CLIENT, DOMAIN

_LOGGER = logging.getLogger(__name__)

ACTION_TEXT = {
    "turn_on": "turn on {target}",
    "turn_off": "turn off {target}",
    "toggle": "toggle {target}",
}


async def async_setup_entry(
    hass,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Cactus Needle conversation entity."""
    async_add_entities([CactusNeedleConversationEntity(config_entry)])


class CactusNeedleConversationEntity(
    conversation.ConversationEntity, conversation.AbstractConversationAgent
):
    """Normalize commands with Needle, then delegate execution to HA."""

    _attr_has_entity_name = True
    _attr_name = "Cactus Needle"
    _attr_supported_features = conversation.ConversationEntityFeature.CONTROL

    def __init__(self, entry: ConfigEntry) -> None:
        self.entry = entry
        self._attr_unique_id = entry.entry_id

    @property
    @override
    def supported_languages(self) -> list[str] | Literal["*"]:
        return MATCH_ALL

    @override
    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        conversation.async_set_agent(self.hass, self.entry, self)

    @override
    async def async_will_remove_from_hass(self) -> None:
        conversation.async_unset_agent(self.hass, self.entry)
        await super().async_will_remove_from_hass()

    @override
    async def _async_handle_message(
        self,
        user_input: conversation.ConversationInput,
        chat_log: conversation.ChatLog,
    ) -> conversation.ConversationResult:
        client: CactusNeedleClient = self.hass.data[DOMAIN][self.entry.entry_id][
            DATA_CLIENT
        ]
        try:
            result = await client.complete(user_input.text)
            call = self._first_valid_call(result)
        except CactusNeedleError as err:
            _LOGGER.warning("Needle unavailable; using fallback agent: %s", err)
            call = None

        if call is None or call["name"] == "fallback":
            return await self._delegate(user_input, user_input.text, fallback=True)

        arguments = call["arguments"]
        target = str(arguments.get("target", "")).strip()
        if not target:
            return await self._delegate(user_input, user_input.text, fallback=True)

        if call["name"] == "get_home_state":
            normalized = f"what is the state of {target}"
        else:
            action = arguments.get("action")
            template = ACTION_TEXT.get(action)
            if template is None:
                return await self._delegate(user_input, user_input.text, fallback=True)
            normalized = template.format(target=target)

        native_result = await self._delegate(user_input, normalized, fallback=False)
        if native_result.response.response_type is not IntentResponseType.ERROR:
            return native_result
        _LOGGER.debug("Native agent rejected normalized command %r", normalized)
        return await self._delegate(user_input, user_input.text, fallback=True)

    @staticmethod
    def _first_valid_call(result: dict[str, Any]) -> dict[str, Any] | None:
        calls = result.get("function_calls")
        if not result.get("success") or not isinstance(calls, list) or not calls:
            return None
        call = calls[0]
        if not isinstance(call, dict) or call.get("name") not in {
            "control_home",
            "get_home_state",
            "fallback",
        }:
            return None
        if not isinstance(call.get("arguments"), dict):
            return None
        return call

    async def _delegate(
        self,
        user_input: conversation.ConversationInput,
        text: str,
        *,
        fallback: bool,
    ) -> conversation.ConversationResult:
        agent_id = conversation.HOME_ASSISTANT_AGENT
        if fallback:
            settings = {**self.entry.data, **self.entry.options}
            configured = settings.get(CONF_FALLBACK_AGENT)
            if configured and configured != self.entity_id:
                agent_id = configured
        return await conversation.async_converse(
            self.hass,
            text=text,
            conversation_id=user_input.conversation_id,
            context=user_input.context,
            language=user_input.language,
            agent_id=agent_id,
            device_id=user_input.device_id,
            satellite_id=user_input.satellite_id,
            extra_system_prompt=user_input.extra_system_prompt,
        )
