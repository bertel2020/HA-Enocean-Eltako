"""Optional gateway prefix in entity IDs: light.eno_gw1_kitchen instead of light.kitchen.

Off by default: Home Assistant then builds entity IDs from device and entity name. With the
prefix on, new entities suggest "eno_gw<number> <device> <entity>" as their entity ID;
Home Assistant keeps it from then on like any other. Existing entities are renamed only on
request (rename_entities), since automations and dashboards are not adapted with them.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import EntityPlatform
from homeassistant.util import slugify

from .const import CONF_ENTITY_PREFIX, CONF_GATEWAY_NUMBER, DOMAIN


def gateway_prefix(options: Mapping[str, Any]) -> str | None:
    """The prefix ("eno_gw1") when the gateway's entity IDs carry it, else None."""
    if not options.get(CONF_ENTITY_PREFIX):
        return None
    return f"eno_gw{int(options.get(CONF_GATEWAY_NUMBER, 1))}"


def taken_gateway_numbers(hass: HomeAssistant, entry: ConfigEntry) -> set[int]:
    """Numbers the other gateways use in their entity IDs."""
    return {
        int(other.options.get(CONF_GATEWAY_NUMBER, 1))
        for other in hass.config_entries.async_entries(DOMAIN)
        if other.entry_id != entry.entry_id and other.options.get(CONF_ENTITY_PREFIX)
    }


def free_gateway_number(hass: HomeAssistant, entry: ConfigEntry) -> int:
    taken = taken_gateway_numbers(hass, entry)
    return next(n for n in range(1, len(taken) + 2) if n not in taken)


def object_id(prefix: str | None, device_name: str | None, entity_name: str | None) -> str:
    return slugify(" ".join(p for p in (prefix, device_name, entity_name) if p))


def _device_name(
    hass: HomeAssistant, identifiers: set[tuple[str, str]], fallback: str | None
) -> str | None:
    device = dr.async_get(hass).async_get_device(identifiers=identifiers)
    if device is None:
        return fallback
    return device.name_by_user or device.name


class PrefixedEntityId(Entity):
    """Suggests the prefixed entity ID when the entity is added for the first time."""

    _gateway_entry: ConfigEntry

    @callback
    def add_to_platform_start(
        self, hass: HomeAssistant, platform: EntityPlatform, parallel_updates: Any
    ) -> None:
        super().add_to_platform_start(hass, platform, parallel_updates)
        if (prefix := gateway_prefix(self._gateway_entry.options)) is None:
            return  # Home Assistant's own entity ID
        info = self.device_info or {}
        device = _device_name(hass, info.get("identifiers", set()), info.get("name"))
        name = self.name if isinstance(self.name, str) else None
        # taken over by Home Assistant only for an entity it has not registered yet
        self.entity_id = f"{platform.domain}.{object_id(prefix, device, name)}"


@callback
def rename_entities(hass: HomeAssistant, entry: ConfigEntry, options: Mapping[str, Any]) -> int:
    """Rename the gateway's entities to the scheme of options; the number renamed."""
    entities = er.async_get(hass)
    devices = dr.async_get(hass)
    prefix = gateway_prefix(options)
    renamed = 0
    for reg in er.async_entries_for_config_entry(entities, entry.entry_id):
        device = devices.async_get(reg.device_id) if reg.device_id else None
        device_name = (device.name_by_user or device.name) if device else None
        wanted = object_id(prefix, device_name, reg.name or reg.original_name)
        if not wanted or reg.entity_id == f"{reg.domain}.{wanted}":
            continue
        new_id = entities.async_get_available_entity_id(
            reg.domain, wanted, current_entity_id=reg.entity_id
        )
        if new_id != reg.entity_id:
            entities.async_update_entity(reg.entity_id, new_entity_id=new_id)
            renamed += 1
    return renamed
