"""Services: capture telegrams to a JSONL file (usable as test fixture), energy dashboard."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import cast

import probatio as vol
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_call_later
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .custom_devices import async_import, export_yaml
from .hub import async_get_hub
from .protocol.monitor import MonitorEntry

SERVICE_CAPTURE = "capture"
SERVICE_ADD_ENERGY = "add_energy_devices"
SERVICE_EXPORT_DEFINITIONS = "export_custom_devices"
SERVICE_IMPORT_DEFINITIONS = "import_custom_devices"
ATTR_IDS = "ids"
ATTR_YAML = "yaml"
ATTR_OVERWRITE = "overwrite"
ATTR_DURATION = "duration"
ATTR_ENTRY_ID = "config_entry_id"

CAPTURE_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_DURATION, default=60): vol.All(int, vol.Range(min=1, max=3600)),
        vol.Optional(ATTR_ENTRY_ID): str,
    }
)


EXPORT_SCHEMA = vol.Schema({vol.Optional(ATTR_IDS): [str]})
IMPORT_SCHEMA = vol.Schema(
    {vol.Required(ATTR_YAML): str, vol.Optional(ATTR_OVERWRITE, default=False): bool}
)
ADD_ENERGY_SCHEMA = vol.Schema({vol.Optional(ATTR_ENTRY_ID): str})
ENERGY_SUFFIX_TOTAL = "_energy_total"


def energy_candidates(
    registry: er.EntityRegistry, entry_id: str | None
) -> list[tuple[er.RegistryEntry, str | None]]:
    """Energy meters of our devices with the power sensor of the same device, if it has one.

    A meter with a day and a night tariff has a total sensor (off by default): it is used
    alone when enabled, otherwise both tariff counters count separately. Gas and water meters
    are not electricity and stay out.
    """
    ours = [
        e
        for e in registry.entities.values()
        if e.platform == DOMAIN
        and e.domain == "sensor"
        and e.disabled_by is None
        and (entry_id is None or e.config_entry_id == entry_id)
    ]
    energy = [e for e in ours if (e.device_class or e.original_device_class) == "energy"]
    powers: dict[str, list[str]] = {}
    for e in ours:
        if e.device_id and (e.device_class or e.original_device_class) == "power":
            powers.setdefault(e.device_id, []).append(e.entity_id)
    totals = {e.device_id for e in energy if e.unique_id.endswith(ENERGY_SUFFIX_TOTAL)}
    result = []
    for e in energy:
        if e.device_id in totals and not e.unique_id.endswith(ENERGY_SUFFIX_TOTAL):
            continue
        rate = powers.get(e.device_id or "", [])
        result.append((e, rate[0] if len(rate) == 1 else None))
    return result


def _write(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(lines), encoding="utf-8")


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    async def capture(call: ServiceCall) -> ServiceResponse:
        """Record telegrams for `duration` seconds, then write them; returns the file path."""
        entry_id = call.data.get(ATTR_ENTRY_ID)
        stamp = dt_util.now().strftime("%Y%m%d-%H%M%S")
        path = Path(hass.config.path(DOMAIN, f"capture-{stamp}.jsonl"))
        lines: list[str] = []

        @callback
        def record(entry: MonitorEntry) -> None:
            if entry_id is None or entry.gateway == entry_id:
                lines.append(json.dumps(entry.as_dict()) + "\n")

        unsubscribe = async_get_hub(hass).monitor.subscribe(record)

        async def finish(_now: datetime) -> None:
            unsubscribe()
            await hass.async_add_executor_job(_write, path, lines)

        async_call_later(hass, call.data[ATTR_DURATION], finish)
        return {"path": str(path)}

    async def add_energy_devices(call: ServiceCall) -> ServiceResponse:
        """Add the energy meters to the Energy dashboard as individual devices."""
        if "energy" not in hass.config.components:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="energy_not_loaded"
            )
        from homeassistant.components.energy.data import (
            DeviceConsumption,
            EnergyPreferencesUpdate,
            async_get_manager,
        )

        manager = await async_get_manager(hass)
        prefs = manager.data
        assert prefs is not None
        devices: list[DeviceConsumption] = list(prefs["device_consumption"])
        known = {d["stat_consumption"] for d in devices}
        added: list[str] = []
        for entity, rate in energy_candidates(er.async_get(hass), call.data.get(ATTR_ENTRY_ID)):
            if entity.entity_id in known:
                continue
            device: DeviceConsumption = {"stat_consumption": entity.entity_id}
            if rate:
                device["stat_rate"] = rate
            devices.append(device)
            added.append(entity.entity_id)
        if added:
            await manager.async_update(
                cast(EnergyPreferencesUpdate, {"device_consumption": devices})
            )
        return cast(ServiceResponse, {"added": added})

    async def export_custom_devices(call: ServiceCall) -> ServiceResponse:
        """The own device definitions as YAML text to share (all, or the named ones)."""
        return {"yaml": export_yaml(call.data.get(ATTR_IDS))}

    async def import_custom_devices(call: ServiceCall) -> ServiceResponse:
        """Store shared definitions as files of their own; own custom_devices.yaml stays."""
        result = await async_import(hass, call.data[ATTR_YAML], call.data[ATTR_OVERWRITE])
        return cast(
            ServiceResponse,
            {"imported": result.imported, "skipped": result.skipped, "errors": result.errors},
        )

    hass.services.async_register(
        DOMAIN,
        SERVICE_EXPORT_DEFINITIONS,
        export_custom_devices,
        schema=EXPORT_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_IMPORT_DEFINITIONS,
        import_custom_devices,
        schema=IMPORT_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_ADD_ENERGY,
        add_energy_devices,
        schema=ADD_ENERGY_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CAPTURE,
        capture,
        schema=CAPTURE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
