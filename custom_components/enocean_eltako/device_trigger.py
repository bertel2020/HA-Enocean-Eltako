"""Device triggers for rocker gestures (E6): button x gesture."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components.device_automation import DEVICE_TRIGGER_BASE_SCHEMA
from homeassistant.components.homeassistant.triggers import event as event_trigger
from homeassistant.const import CONF_DEVICE_ID, CONF_DOMAIN, CONF_PLATFORM, CONF_TYPE
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.trigger import TriggerActionType, TriggerInfo
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .event import EVENT_BUTTON
from .gestures import EVENT_TYPES

CONF_SUBTYPE = "subtype"
BUTTONS = ("a0", "a1", "b0", "b1")

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {vol.Required(CONF_TYPE): vol.In(EVENT_TYPES), vol.Required(CONF_SUBTYPE): vol.In(BUTTONS)}
)


def _is_rocker(hass: HomeAssistant, device_id: str) -> bool:
    device = dr.async_get(hass).async_get(device_id)
    if device is None:
        return False
    identifiers = {i for d, i in device.identifiers if d == DOMAIN}
    for entry in hass.config_entries.async_loaded_entries(DOMAIN):
        for rocker in entry.runtime_data.devices.values():
            if rocker.model.kind == "rocker" and rocker.unique_prefix in identifiers:
                return True
    return False


async def async_get_triggers(hass: HomeAssistant, device_id: str) -> list[dict[str, Any]]:
    if not _is_rocker(hass, device_id):
        return []
    return [
        {
            CONF_PLATFORM: "device",
            CONF_DOMAIN: DOMAIN,
            CONF_DEVICE_ID: device_id,
            CONF_TYPE: event_type,
            CONF_SUBTYPE: button,
        }
        for button in BUTTONS
        for event_type in EVENT_TYPES
    ]


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: TriggerActionType,
    trigger_info: TriggerInfo,
) -> CALLBACK_TYPE:
    event_config = event_trigger.TRIGGER_SCHEMA(
        {
            event_trigger.CONF_PLATFORM: "event",
            event_trigger.CONF_EVENT_TYPE: EVENT_BUTTON,
            event_trigger.CONF_EVENT_DATA: {
                CONF_DEVICE_ID: config[CONF_DEVICE_ID],
                "button": config[CONF_SUBTYPE],
                "type": config[CONF_TYPE],
            },
        }
    )
    return await event_trigger.async_attach_trigger(
        hass, event_config, action, trigger_info, platform_type="device"
    )
