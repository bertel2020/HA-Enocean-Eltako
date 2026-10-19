"""Subentry flow: add a device to a gateway (catalog model, ID, sender ID, options)."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigSubentryFlow, SubentryFlowResult
from homeassistant.const import Platform
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)

from .catalog import (
    CATALOG,
    OPT_DEVICE_CLASS,
    OPT_INVERT,
    OPT_PLATFORM,
    OPT_TIME_CLOSES,
    OPT_TIME_OPENS,
    DeviceModel,
)
from .const import (
    CONF_DEVICE_ID,
    CONF_MODEL,
    CONF_NAME,
    CONF_SENDER_ID,
    SUBENTRY_DEVICE,
    SUBENTRY_SCHEMA,
)
from .protocol.ids import format_id, parse_id
from .protocol.sender_pool import SenderIdError

DEVICE_CLASSES = ["door", "window", "garage_door", "opening"]


def sender_owner(device_id: int) -> str:
    return f"device:{format_id(device_id)}"


class DeviceSubentryFlow(ConfigSubentryFlow):
    """Add a device: choose the model, then ID, sender and model options."""

    def __init__(self) -> None:
        self._model: DeviceModel | None = None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        entry = self._get_entry()
        if not hasattr(entry, "runtime_data") or entry.runtime_data is None:
            return self.async_abort(reason="gateway_not_loaded")
        if user_input is not None:
            self._model = CATALOG[user_input[CONF_MODEL]]
            return await self.async_step_device()
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_MODEL): SelectSelector(
                        SelectSelectorConfig(
                            options=list(CATALOG),
                            translation_key="device_model",
                            mode=SelectSelectorMode.LIST,
                        )
                    )
                }
            ),
        )

    async def async_step_device(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        assert self._model is not None
        model = self._model
        entry = self._get_entry()
        pool = entry.runtime_data.senders.pool
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                device_id = parse_id(user_input[CONF_DEVICE_ID])
            except ValueError:
                errors[CONF_DEVICE_ID] = "invalid_id"
            else:
                if any(s.unique_id == format_id(device_id) for s in entry.subentries.values()):
                    errors[CONF_DEVICE_ID] = "already_configured"
            sender_id = None
            if model.actuator and not errors:
                try:
                    sender_id = parse_id(user_input[CONF_SENDER_ID])
                    pool.assign(sender_id, sender_owner(device_id))
                except ValueError as err:
                    reason = err.reason if isinstance(err, SenderIdError) else "invalid_id"
                    errors[CONF_SENDER_ID] = f"sender_{reason}"
            if not errors:
                # saved now: creating the subentry reloads the entry and the pool with it
                await entry.runtime_data.senders.async_save()
                data: dict[str, Any] = {
                    "schema": SUBENTRY_SCHEMA,
                    CONF_MODEL: model.id,
                    CONF_DEVICE_ID: format_id(device_id),
                }
                if sender_id is not None:
                    data[CONF_SENDER_ID] = format_id(sender_id)
                for key in (OPT_PLATFORM, OPT_TIME_OPENS, OPT_TIME_CLOSES, OPT_INVERT):
                    if key in user_input:
                        data[key] = user_input[key]
                if user_input.get(OPT_DEVICE_CLASS):
                    data[OPT_DEVICE_CLASS] = user_input[OPT_DEVICE_CLASS]
                return self.async_create_entry(
                    title=user_input[CONF_NAME], data=data, unique_id=format_id(device_id)
                )

        schema: dict[Any, Any] = {
            vol.Required(CONF_NAME): TextSelector(),
            vol.Required(CONF_DEVICE_ID): TextSelector(),
        }
        if model.actuator:
            suggested = pool.next_free()
            key = (
                vol.Required(CONF_SENDER_ID, default=format_id(suggested))
                if suggested is not None
                else vol.Required(CONF_SENDER_ID)
            )
            schema[key] = TextSelector()
        if len(model.platforms) > 1 and model.id == "switch":
            schema[vol.Required(OPT_PLATFORM, default=Platform.LIGHT.value)] = SelectSelector(
                SelectSelectorConfig(
                    options=[Platform.LIGHT.value, Platform.SWITCH.value],
                    translation_key=OPT_PLATFORM,
                )
            )
        if OPT_TIME_OPENS in model.options:
            for opt in (OPT_TIME_OPENS, OPT_TIME_CLOSES):
                schema[vol.Required(opt, default=30)] = NumberSelector(
                    NumberSelectorConfig(
                        min=1,
                        max=300,
                        step=0.1,
                        unit_of_measurement="s",
                        mode=NumberSelectorMode.BOX,
                    )
                )
        if OPT_DEVICE_CLASS in model.options:
            schema[vol.Required(OPT_DEVICE_CLASS, default="window")] = SelectSelector(
                SelectSelectorConfig(options=DEVICE_CLASSES, translation_key=OPT_DEVICE_CLASS)
            )
        if OPT_INVERT in model.options:
            schema[vol.Required(OPT_INVERT, default=False)] = BooleanSelector()
        return self.async_show_form(
            step_id="device",
            data_schema=self.add_suggested_values_to_schema(vol.Schema(schema), user_input),
            errors=errors,
            description_placeholders={
                "examples": model.examples,
                "receive": str(model.receive) if model.receive else "-",
                "send": str(model.send) if model.send else "-",
            },
        )


SUBENTRY_FLOWS = {SUBENTRY_DEVICE: DeviceSubentryFlow}
