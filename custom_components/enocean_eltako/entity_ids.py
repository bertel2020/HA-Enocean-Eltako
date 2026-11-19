"""Optional gateway prefix in entity IDs: light.eno_gw1_kitchen instead of light.kitchen.

Off by default: Home Assistant then builds entity IDs from device and entity name. With the
prefix on, new entities suggest "eno_gw<number> <device> <entity>" as their entity ID;
Home Assistant keeps it from then on like any other. Existing entities are renamed only on
request (rename_entities), since automations and dashboards are not adapted with them.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
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


def own_prefix(options: Mapping[str, Any]) -> str:
    """The prefix of the gateway's own entities: always there, whatever the option says."""
    return f"eno_gw{int(options.get(CONF_GATEWAY_NUMBER, 1))}"


def taken_gateway_numbers(
    hass: HomeAssistant, entry: ConfigEntry | None, extra: Iterable[ConfigEntry] = ()
) -> set[int]:
    """Numbers the other gateways use: every gateway has one (its own entities carry it)."""
    others = {e.entry_id: e for e in (*hass.config_entries.async_entries(DOMAIN), *extra)}
    if entry is not None:
        others.pop(entry.entry_id, None)
    return {
        int(number)
        for other in others.values()
        if (number := other.options.get(CONF_GATEWAY_NUMBER)) is not None
        or (number := 1 if other.options.get(CONF_ENTITY_PREFIX) else None) is not None
    }


def free_gateway_number(hass: HomeAssistant, entry: ConfigEntry | None) -> int:
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
    # The gateway's own entities: the prefix already names the gateway, so the device name
    # (the gateway's) would only repeat it - and could name hardware that gets swapped.
    _prefix_names_device = False

    @callback
    def add_to_platform_start(
        self, hass: HomeAssistant, platform: EntityPlatform, parallel_updates: Any
    ) -> None:
        super().add_to_platform_start(hass, platform, parallel_updates)
        options = self._gateway_entry.options
        prefix = own_prefix(options) if self._prefix_names_device else gateway_prefix(options)
        if prefix is None:
            return  # Home Assistant's own entity ID
        info = self.device_info or {}
        device = (
            None
            if self._prefix_names_device
            else _device_name(hass, info.get("identifiers", set()), info.get("name"))
        )
        name = self.name if isinstance(self.name, str) else None
        # taken over by Home Assistant only for an entity it has not registered yet
        self.entity_id = f"{platform.domain}.{object_id(prefix, device, name)}"


@callback
def rename_entities(
    hass: HomeAssistant,
    entry: ConfigEntry,
    options: Mapping[str, Any],
    only: Callable[[er.RegistryEntry], bool] | None = None,
) -> int:
    """Rename the gateway's entities (only those `only` accepts) to the scheme of options;
    the number renamed."""
    entities = er.async_get(hass)
    devices = dr.async_get(hass)
    prefix = gateway_prefix(options)
    renamed = 0
    for reg in er.async_entries_for_config_entry(entities, entry.entry_id):
        if only is not None and not only(reg):
            continue
        device = devices.async_get(reg.device_id) if reg.device_id else None
        own = device is not None and (DOMAIN, entry.entry_id) in device.identifiers
        device_name = (device.name_by_user or device.name) if device and not own else None
        wanted = object_id(
            own_prefix(options) if own else prefix, device_name, reg.name or reg.original_name
        )
        if not wanted or reg.entity_id == f"{reg.domain}.{wanted}":
            continue
        new_id = entities.async_get_available_entity_id(
            reg.domain, wanted, current_entity_id=reg.entity_id
        )
        if new_id != reg.entity_id:
            entities.async_update_entity(reg.entity_id, new_entity_id=new_id)
            renamed += 1
    return renamed
