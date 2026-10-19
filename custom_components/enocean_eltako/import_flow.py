"""Subentry flow "import": devices of the old `eltako:` YAML become device subentries."""

from __future__ import annotations

from types import MappingProxyType
from typing import Any

import voluptuous as vol
from homeassistant.config import async_hass_config_yaml
from homeassistant.config_entries import ConfigSubentry, ConfigSubentryFlow, SubentryFlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)
from homeassistant.helpers.translation import async_get_translations

from .const import (
    CONF_BASE_ID,
    CONF_DEVICE_ID,
    CONF_MODEL,
    CONF_PROFILE,
    CONF_SENDER_ID,
    CONF_SENDERS,
    DOMAIN,
    SUBENTRY_DEVICE,
    SUBENTRY_SCHEMA,
)
from .legacy_import import (
    ImportPlan,
    PlannedDevice,
    build_plan,
    find_legacy_config,
    gateway_label,
    legacy_gateways,
)
from .protocol.ids import format_id, parse_id
from .protocol.sender_pool import SenderIdError, SenderPool
from .subentry_flow import sender_owner

CONF_GATEWAY = "gateway"
IMPORTING = f"{DOMAIN}_importing"  # entry IDs whose reload waits until the import is done


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "-"


class ImportSubentryFlow(ConfigSubentryFlow):
    """Read the old configuration, show what becomes of it, create all devices at once."""

    def __init__(self) -> None:
        self._gateways: list[dict[str, Any]] = []
        self._gateway: dict[str, Any] = {}
        self._plan = ImportPlan()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        entry = self._get_entry()
        if getattr(entry, "runtime_data", None) is None:
            return self.async_abort(reason="gateway_not_loaded")
        try:
            config = await async_hass_config_yaml(self.hass)
        except HomeAssistantError:
            return self.async_abort(reason="config_unreadable")
        block = find_legacy_config(config)
        self._gateways = legacy_gateways(block) if block else []
        if not self._gateways:
            return self.async_abort(reason="no_old_config")
        if len(self._gateways) == 1:
            return await self._async_preview(self._gateways[0])
        return await self.async_step_gateway()

    async def async_step_gateway(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Several old gateways: whose devices belong to this one?"""
        if user_input is not None:
            return await self._async_preview(self._gateways[int(user_input[CONF_GATEWAY])])
        base_id = self._get_entry().data[CONF_BASE_ID]
        default = next(
            (str(i) for i, g in enumerate(self._gateways) if _same_id(g.get("base_id"), base_id)),
            "0",
        )
        options = [
            SelectOptionDict(value=str(i), label=gateway_label(g))
            for i, g in enumerate(self._gateways)
        ]
        return self.async_show_form(
            step_id="gateway",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_GATEWAY, default=default): SelectSelector(
                        SelectSelectorConfig(options=options, mode=SelectSelectorMode.LIST)
                    )
                }
            ),
        )

    async def _async_preview(self, gateway: dict[str, Any]) -> SubentryFlowResult:
        self._gateway = gateway
        existing = {s.unique_id for s in self._get_entry().subentries.values() if s.unique_id}
        self._plan = build_plan(gateway, existing)
        if not self._plan.create:
            return self.async_abort(
                reason="nothing_to_import",
                description_placeholders={
                    "existing": str(len(self._plan.existing)),
                    "skipped": _bullets(self._plan.skipped),
                },
            )
        return await self.async_step_preview()

    async def async_step_preview(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        if user_input is not None:
            return await self._async_import()
        kinds = await self._kind_names()
        plan = self._plan
        return self.async_show_form(
            step_id="preview",
            data_schema=vol.Schema({}),
            description_placeholders={
                "gateway": gateway_label(self._gateway),
                "create_count": str(len(plan.create)),
                "create": _bullets(
                    [
                        f"{d.name} ({format_id(d.device_id)}): {kinds.get(d.kind, d.kind)}"
                        for d in plan.create
                    ]
                ),
                "existing_count": str(len(plan.existing)),
                "skipped_count": str(len(plan.skipped)),
                "skipped": _bullets(plan.skipped),
            },
        )

    async def _kind_names(self) -> dict[str, str]:
        translations = await async_get_translations(
            self.hass, self.hass.config.language, "selector", [DOMAIN]
        )
        prefix = f"component.{DOMAIN}.selector.device_model.options."
        return {k.removeprefix(prefix): v for k, v in translations.items() if k.startswith(prefix)}

    async def _async_import(self) -> SubentryFlowResult:
        """All subentries in one go; the entry reloads once at the end."""
        entry = self._get_entry()
        runtime = entry.runtime_data
        importing: set[str] = self.hass.data.setdefault(IMPORTING, set())
        importing.add(entry.entry_id)
        dropped: list[str] = []
        try:
            for device in self._plan.create:
                senders = self._assign_senders(device, dropped)
                data: dict[str, Any] = {
                    "schema": SUBENTRY_SCHEMA,
                    CONF_MODEL: device.kind,
                    CONF_DEVICE_ID: format_id(device.device_id),
                    **device.options,
                }
                if senders:
                    data[CONF_SENDERS] = senders
                self.hass.config_entries.async_add_subentry(
                    entry,
                    ConfigSubentry(
                        data=MappingProxyType(data),
                        subentry_type=SUBENTRY_DEVICE,
                        title=device.name,
                        unique_id=format_id(device.device_id),
                    ),
                )
        finally:
            importing.discard(entry.entry_id)
        await runtime.senders.async_save()
        if runtime.bus is not None:
            await runtime.bus.senders.async_save()
        self.hass.config_entries.async_schedule_reload(entry.entry_id)
        heating = [d.name for d in self._plan.create if d.needs_temperature_sensor]
        return self.async_abort(
            reason="imported",
            description_placeholders={
                "count": str(len(self._plan.create)),
                "heating": _bullets(heating),
                "dropped": _bullets(dropped),
            },
        )

    def _assign_senders(self, device: PlannedDevice, dropped: list[str]) -> list[dict[str, str]]:
        """Keep the old sender IDs (the actuators know them) when a pool of ours holds them."""
        runtime = self._get_entry().runtime_data
        pools: list[SenderPool] = [runtime.senders.pool]
        if runtime.bus is not None:
            pools.append(runtime.bus.senders.pool)
        senders = []
        for profile, sender in device.senders.items():
            pool = next((p for p in pools if sender in p), None)
            if pool is None:
                dropped.append(f"{device.name}: {format_id(sender)}")
                continue
            try:
                pool.assign(sender, sender_owner(device.device_id, profile))
            except SenderIdError:
                dropped.append(f"{device.name}: {format_id(sender)}")
                continue
            senders.append({CONF_PROFILE: profile, CONF_SENDER_ID: format_id(sender)})
        return senders


def _same_id(text: Any, base_id: str) -> bool:
    try:
        return parse_id(str(text)) == parse_id(base_id)
    except ValueError:
        return False
