"""Subentry flow: add or reconfigure a device (catalog model, ID, senders, options)."""

from __future__ import annotations

import asyncio
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigSubentryFlow, SubentryFlowResult
from homeassistant.const import Platform
from homeassistant.helpers.selector import (
    BooleanSelector,
    EntitySelector,
    EntitySelectorConfig,
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
    OPT_OFF_BUTTON,
    OPT_ON_BUTTON,
    OPT_PLATFORM,
    OPT_ROUTING,
    OPT_SEND_INTERVAL,
    OPT_TEMPERATURE_SENSOR,
    OPT_TIME_CLOSES,
    OPT_TIME_OPENS,
    OPT_UNAVAILABLE_WHEN_SILENT,
    DeviceModel,
)
from .const import (
    CONF_DEVICE_ID,
    CONF_MODEL,
    CONF_NAME,
    CONF_PROFILE,
    CONF_SENDER_ID,
    CONF_SENDERS,
    SUBENTRY_DEVICE,
    SUBENTRY_SCHEMA,
)
from .protocol.dispatcher import ReceivedTelegram
from .protocol.ids import format_id, parse_id
from .protocol.sender_pool import SenderIdError, SenderPool

DEVICE_CLASSES = ["door", "window", "garage_door", "opening"]
LEARN_TIMEOUT = 60.0

# RORG of telegrams a device kind sends, from the first letters of its receive profile
_RORG_BY_PREFIX = {
    "F6": {0xF6},
    "M5": {0xF6},
    "G5": {0xF6, 0xA5},
    "A5": {0xA5},
    "D5": {0xD5},
    "D2": {0xD2},
}


def expected_rorgs(model: DeviceModel) -> set[int]:
    if model.receive is None:
        return set()
    rorgs = set(_RORG_BY_PREFIX.get(model.receive.eep[:2], ()))
    for extra in model.receive_extra:
        rorgs |= _RORG_BY_PREFIX.get(extra.eep[:2], set())
    return rorgs


OPTION_KEYS = (
    OPT_PLATFORM,
    OPT_TIME_OPENS,
    OPT_TIME_CLOSES,
    OPT_INVERT,
    OPT_ROUTING,
    OPT_ON_BUTTON,
    OPT_OFF_BUTTON,
    OPT_TEMPERATURE_SENSOR,
    OPT_SEND_INTERVAL,
    OPT_UNAVAILABLE_WHEN_SILENT,
)
BUTTONS = ["b0", "b1", "a0", "a1"]


def sender_owner(device_id: int, profile: str) -> str:
    return f"device:{format_id(device_id)}:{profile}"


def sender_field(profile: str) -> str:
    return f"sender_{profile}"


class DeviceSubentryFlow(ConfigSubentryFlow):
    """Add a device: model, then name, ID, senders and options. Reconfigure: all but the ID."""

    def __init__(self) -> None:
        self._model: DeviceModel | None = None
        self._learn_task: asyncio.Task[ReceivedTelegram | None] | None = None
        self._learned: ReceivedTelegram | None = None

    def _loaded(self) -> bool:
        entry = self._get_entry()
        return getattr(entry, "runtime_data", None) is not None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        if not self._loaded():
            return self.async_abort(reason="gateway_not_loaded")
        if user_input is not None:
            self._model = CATALOG[user_input[CONF_MODEL]]
            return await self.async_step_address()
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

    async def async_step_address(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Listen for a telegram or type the ID."""
        return self.async_show_menu(step_id="address", menu_options=["learn", "device"])

    async def async_step_learn(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Wait up to LEARN_TIMEOUT for a telegram from a sender not set up yet."""
        if self._learn_task is None:
            self._learn_task = self.hass.async_create_task(self._async_wait_for_telegram())
        if not self._learn_task.done():
            return self.async_show_progress(
                step_id="learn",
                progress_action="learn",
                progress_task=self._learn_task,
                description_placeholders={"seconds": str(int(LEARN_TIMEOUT))},
            )
        self._learned = self._learn_task.result()
        self._learn_task = None
        if self._learned is None:
            return self.async_show_progress_done(next_step_id="learn_timeout")
        return self.async_show_progress_done(next_step_id="device")

    async def async_step_learn_timeout(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        return self.async_show_menu(step_id="learn_timeout", menu_options=["learn", "device"])

    async def _async_wait_for_telegram(self) -> ReceivedTelegram | None:
        assert self._model is not None
        rorgs = expected_rorgs(self._model)
        dispatcher = self._get_entry().runtime_data.hub.dispatcher
        future: asyncio.Future[ReceivedTelegram] = self.hass.loop.create_future()

        def heard(received: ReceivedTelegram) -> None:
            if not future.done() and (not rorgs or received.telegram.rorg in rorgs):
                future.set_result(received)

        remove = dispatcher.add_unknown_listener(heard)
        try:
            async with asyncio.timeout(LEARN_TIMEOUT):
                return await future
        except TimeoutError:
            return None
        finally:
            remove()

    async def async_step_device(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        assert self._model is not None
        entry = self._get_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            device_id = None
            try:
                device_id = parse_id(user_input[CONF_DEVICE_ID])
            except ValueError:
                errors[CONF_DEVICE_ID] = "invalid_id"
            else:
                if any(s.unique_id == format_id(device_id) for s in entry.subentries.values()):
                    errors[CONF_DEVICE_ID] = "already_configured"
            if device_id is not None and not errors:
                result = await self._async_save(user_input, device_id, {}, errors)
                if result is not None:
                    return self.async_create_entry(
                        title=user_input[CONF_NAME], data=result, unique_id=format_id(device_id)
                    )
        schema = {
            vol.Required(CONF_NAME): TextSelector(),
            vol.Required(CONF_DEVICE_ID): TextSelector(),
            **self._fields(self._model, {}),
        }
        if user_input is None and self._learned is not None:
            user_input = {CONF_DEVICE_ID: format_id(self._learned.sender)}
        return self._form("device", schema, user_input, errors)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        if not self._loaded():
            return self.async_abort(reason="gateway_not_loaded")
        subentry = self._get_reconfigure_subentry()
        data = dict(subentry.data)
        self._model = model = CATALOG[data[CONF_MODEL]]
        device_id = parse_id(data[CONF_DEVICE_ID])
        current = {s[CONF_PROFILE]: s[CONF_SENDER_ID] for s in data.get(CONF_SENDERS, ())}
        errors: dict[str, str] = {}
        if user_input is not None:
            result = await self._async_save(user_input, device_id, current, errors)
            if result is not None:
                return self.async_update_and_abort(
                    self._get_entry(), subentry, title=user_input[CONF_NAME], data=result
                )
        suggested = {
            CONF_NAME: subentry.title,
            **{k: data[k] for k in (*OPTION_KEYS, OPT_DEVICE_CLASS) if k in data},
            **{sender_field(p): s for p, s in current.items()},
        }
        schema = {vol.Required(CONF_NAME): TextSelector(), **self._fields(model, current)}
        return self._form("reconfigure", schema, user_input or suggested, errors)

    def _form(
        self,
        step_id: str,
        schema: dict[Any, Any],
        values: dict[str, Any] | None,
        errors: dict[str, str],
    ) -> SubentryFlowResult:
        assert self._model is not None
        model = self._model
        return self.async_show_form(
            step_id=step_id,
            data_schema=self.add_suggested_values_to_schema(vol.Schema(schema), values),
            errors=errors,
            description_placeholders={
                "examples": model.examples,
                "receive": str(model.receive) if model.receive else "-",
                "send": ", ".join(f"{p.id} ({p.eep})" for p in model.senders) or "-",
            },
        )

    def _pool(self) -> SenderPool:
        return self._get_entry().runtime_data.senders.pool

    def _fields(self, model: DeviceModel, current: dict[str, str]) -> dict[Any, Any]:
        """Sender IDs (first profile required, suggested from the pool) and model options."""
        schema: dict[Any, Any] = {}
        for index, profile in enumerate(model.senders):
            field = sender_field(profile.id)
            if index == 0:
                suggested = current.get(profile.id)
                if suggested is None and (free := self._pool().next_free()) is not None:
                    suggested = format_id(free)
                key = vol.Required(field, default=suggested) if suggested else vol.Required(field)
            else:
                key = vol.Optional(field)
            schema[key] = TextSelector()
        if model.id in ("switch", "psc"):
            default = Platform.LIGHT.value if model.id == "switch" else Platform.SWITCH.value
            schema[vol.Required(OPT_PLATFORM, default=default)] = SelectSelector(
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
        if OPT_ROUTING in model.options:
            schema[vol.Required(OPT_ROUTING, default=model.senders[0].id)] = SelectSelector(
                SelectSelectorConfig(
                    options=[*(p.id for p in model.senders), "both"],
                    translation_key=OPT_ROUTING,
                )
            )
        if OPT_TEMPERATURE_SENSOR in model.options:
            schema[vol.Required(OPT_TEMPERATURE_SENSOR)] = EntitySelector(
                EntitySelectorConfig(domain="sensor", device_class="temperature")
            )
            schema[vol.Required(OPT_SEND_INTERVAL, default=60)] = NumberSelector(
                NumberSelectorConfig(
                    min=10, max=600, step=10, unit_of_measurement="s", mode=NumberSelectorMode.BOX
                )
            )
        if OPT_ON_BUTTON in model.options:
            schema[vol.Required(OPT_ON_BUTTON, default="b0")] = SelectSelector(
                SelectSelectorConfig(options=BUTTONS, translation_key="rocker_button")
            )
            schema[vol.Required(OPT_OFF_BUTTON, default="b1")] = SelectSelector(
                SelectSelectorConfig(
                    options=[*BUTTONS, "released"], translation_key="rocker_button"
                )
            )
        if OPT_DEVICE_CLASS in model.options:
            schema[vol.Required(OPT_DEVICE_CLASS, default="window")] = SelectSelector(
                SelectSelectorConfig(options=DEVICE_CLASSES, translation_key=OPT_DEVICE_CLASS)
            )
        if OPT_INVERT in model.options:
            schema[vol.Required(OPT_INVERT, default=False)] = BooleanSelector()
        if model.interval:
            schema[vol.Required(OPT_UNAVAILABLE_WHEN_SILENT, default=False)] = BooleanSelector()
        return schema

    async def _async_save(
        self,
        user_input: dict[str, Any],
        device_id: int,
        current: dict[str, str],
        errors: dict[str, str],
    ) -> dict[str, Any] | None:
        """Validate and assign sender IDs; returns the subentry data or None on errors."""
        assert self._model is not None
        model = self._model
        pool = self._pool()
        wanted: dict[str, int] = {}
        for profile in model.senders:
            text = (user_input.get(sender_field(profile.id)) or "").strip()
            if not text:
                continue
            try:
                sender = parse_id(text)
            except ValueError:
                errors[sender_field(profile.id)] = "sender_invalid_id"
                continue
            if sender in wanted.values():
                errors[sender_field(profile.id)] = "sender_in_use"
                continue
            wanted[profile.id] = sender
        if errors:
            return None
        released = {
            p: parse_id(s)
            for p, s in current.items()
            if p not in wanted or format_id(wanted[p]) != s
        }
        assigned: list[int] = []
        for profile, sender in wanted.items():
            if current.get(profile) == format_id(sender):
                continue
            try:
                pool.assign(sender, sender_owner(device_id, profile))
            except SenderIdError as err:
                errors[sender_field(profile)] = f"sender_{err.reason}"
                continue
            assigned.append(sender)
        if errors:
            for sender in assigned:  # roll back this attempt
                pool.release(sender)
                pool.confirm_teach_out(sender)
            return None
        for sender in released.values():
            pool.release(sender)  # blocked until the teach-out is confirmed
        # saved now: changing subentries reloads the entry and the pool with it
        await self._get_entry().runtime_data.senders.async_save()
        data: dict[str, Any] = {
            "schema": SUBENTRY_SCHEMA,
            CONF_MODEL: model.id,
            CONF_DEVICE_ID: format_id(device_id),
        }
        if wanted:
            data[CONF_SENDERS] = [
                {CONF_PROFILE: p, CONF_SENDER_ID: format_id(s)} for p, s in wanted.items()
            ]
        for key in OPTION_KEYS:
            if key in user_input:
                data[key] = user_input[key]
        if user_input.get(OPT_DEVICE_CLASS):
            data[OPT_DEVICE_CLASS] = user_input[OPT_DEVICE_CLASS]
        return data


SUBENTRY_FLOWS = {SUBENTRY_DEVICE: DeviceSubentryFlow}
