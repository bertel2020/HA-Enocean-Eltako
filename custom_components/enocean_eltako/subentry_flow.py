"""Subentry flow: add or reconfigure a device (catalog model, ID, senders, options)."""

from __future__ import annotations

import asyncio
import time
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
    CONTROLLER,
    EEP_OPTIONS,
    EEP_TO_MODEL,
    GENERIC_EEP,
    GENERIC_EEPS,
    GROUP_ELTAKO,
    GROUP_ENOCEAN,
    GROUPS,
    OPT_CALIBRATION,
    OPT_DEVICE_CLASS,
    OPT_DOUBLE_PRESS,
    OPT_INVERT,
    OPT_LONG_PRESS,
    OPT_OFF_BUTTON,
    OPT_ON_BUTTON,
    OPT_PLATFORM,
    OPT_ROUTING,
    OPT_SEND_INTERVAL,
    OPT_STATUS_REQUEST,
    OPT_TEMPERATURE_SENSOR,
    OPT_TIME_CLOSES,
    OPT_TIME_OPENS,
    OPT_UNAVAILABLE_WHEN_SILENT,
    DeviceModel,
    categories_of,
    generic_model,
    model_for,
    models_in,
)
from .const import (
    CONF_DEVICE_ID,
    CONF_EEP,
    CONF_MODEL,
    CONF_NAME,
    CONF_PROFILE,
    CONF_SENDER_ID,
    CONF_SENDERS,
    SUBENTRY_DEVICE,
    SUBENTRY_SCHEMA,
)
from .protocol.dispatcher import ReceivedTelegram
from .protocol.eep import EEPRef
from .protocol.eep.eltako import shutter
from .protocol.eep.teach_in import MANUFACTURER_ELTAKO, TeachIn4BS, decode_teach_in_4bs
from .protocol.ids import format_id, parse_id
from .protocol.sender_pool import SenderIdError, SenderPool
from .protocol.telegram import Rorg

DEVICE_CLASSES = ["door", "window", "garage_door", "opening"]
LEARN_TIMEOUT = 60.0
MEASURE_MAX_RUN = 120  # seconds a measuring run may last (the click stops it earlier)
DRIVEN_TIME_WAIT = 3.0  # seconds to wait for the actuator's driven-time report

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


def _receives(model: DeviceModel, eep: str) -> bool:
    return any(r.eep == eep for r in (model.receive, *model.receive_extra) if r is not None)


def candidates(rorg: int, teach_in: TeachIn4BS | None) -> list[str]:
    """Catalog kinds a heard telegram may come from; a 4BS teach-in names its EEP and
    manufacturer, so Eltako entries come first for Eltako devices."""
    if teach_in is not None:
        kinds = [m for m in CATALOG.values() if _receives(m, teach_in.eep)]
        if kinds:
            eltako = teach_in.manufacturer == MANUFACTURER_ELTAKO
            kinds.sort(key=lambda m: (m.group == GROUP_ELTAKO) != eltako)
            return [m.id for m in kinds]
    return [m.id for m in CATALOG.values() if rorg in expected_rorgs(m)]


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
    OPT_STATUS_REQUEST,
    OPT_LONG_PRESS,
    OPT_DOUBLE_PRESS,
    OPT_CALIBRATION,
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
        self._settings_chosen = False
        self._measure_task: asyncio.Task[bool] | None = None
        self._measured: dict[str, float] = {}
        self._run_started = 0.0
        self._learn_task: asyncio.Task[ReceivedTelegram | None] | None = None
        self._learned: ReceivedTelegram | None = None
        self._kinds: list[str] = []
        self._group = GROUP_ELTAKO
        self._back = "user"  # step the "back" entry of the next menu returns to

    def _loaded(self) -> bool:
        entry = self._get_entry()
        return getattr(entry, "runtime_data", None) is not None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """How to add the device: listen for it, pick it from the catalog, or by EEP."""
        if not self._loaded():
            return self.async_abort(reason="gateway_not_loaded")
        self._model = None  # also when coming back: learning then suggests the kind
        return self.async_show_menu(step_id="user", menu_options=["learn", *GROUPS, "eep"])

    async def async_step_eltako(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        return self._category_menu(GROUP_ELTAKO)

    async def async_step_enocean(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        return self._category_menu(GROUP_ENOCEAN)

    def _category_menu(self, group: str) -> SubentryFlowResult:
        self._group = group
        return self.async_show_menu(
            step_id=group, menu_options=[*(f"{group}_{c}" for c in categories_of(group)), "user"]
        )

    async def _async_category(self, group: str, category: str) -> SubentryFlowResult:
        """One kind in the category: take it; several: ask which."""
        self._kinds = [m.id for m in models_in(group, category)]
        if len(self._kinds) == 1:
            return await self._async_chosen(CATALOG[self._kinds[0]], back=group)
        return await self.async_step_kind()

    async def async_step_kind(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Kinds of the chosen category, examples as descriptions; back to the categories."""
        return self.async_show_menu(
            step_id="kind", menu_options=[*(f"model_{k}" for k in self._kinds), self._group]
        )

    async def _async_chosen(self, model: DeviceModel, back: str) -> SubentryFlowResult:
        self._model = model
        self._back = back
        return await self.async_step_address()

    def _model_form(
        self, step_id: str, kinds: list[str], placeholders: dict[str, str] | None = None
    ) -> SubentryFlowResult:
        return self.async_show_form(
            step_id=step_id,
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_MODEL): SelectSelector(
                        SelectSelectorConfig(
                            options=kinds,
                            translation_key="device_model",
                            mode=SelectSelectorMode.LIST,
                        )
                    )
                }
            ),
            description_placeholders=placeholders,
        )

    async def async_step_eep(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """By EEP: standard sensor profiles as a generic device, the rest via the catalog."""
        if user_input is not None:
            option = user_input[CONF_EEP]
            if option in EEP_TO_MODEL:
                return await self._async_chosen(CATALOG[EEP_TO_MODEL[option]], back="eep")
            return await self._async_chosen(generic_model(EEP_OPTIONS[option]), back="eep")
        return self.async_show_form(
            step_id="eep",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EEP): SelectSelector(
                        SelectSelectorConfig(
                            options=list(EEP_OPTIONS),
                            translation_key=CONF_EEP,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
        )

    async def async_step_address(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Listen for a telegram or type the ID."""
        return self.async_show_menu(step_id="address", menu_options=["learn", "device", self._back])

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
        if self._model is None:
            return self.async_show_progress_done(next_step_id="learned")
        return self.async_show_progress_done(next_step_id="device")

    async def async_step_learned(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Heard a new sender before the kind was chosen: offer the kinds that fit."""
        assert self._learned is not None
        if user_input is not None:
            self._model = CATALOG[user_input[CONF_MODEL]]
            return await self.async_step_device()
        telegram = self._learned.telegram
        teach_in = decode_teach_in_4bs(telegram.data) if telegram.rorg == Rorg.BS4 else None
        if teach_in is not None and teach_in.eep in GENERIC_EEPS:
            fitting = [m for m in CATALOG.values() if _receives(m, teach_in.eep)]
            if not fitting:  # no catalog entry decodes it: generic device
                self._model = generic_model(EEPRef(teach_in.eep, "std"))
                return await self.async_step_device()
        kinds = candidates(telegram.rorg, teach_in)
        if len(kinds) == 1:
            self._model = CATALOG[kinds[0]]
            return await self.async_step_device()
        return self._model_form(
            "learned",
            kinds,
            {
                "device_id": format_id(self._learned.sender),
                "eep": teach_in.eep if teach_in else f"{telegram.rorg:02X}",
            },
        )

    async def async_step_learn_timeout(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        if self._model is None:  # kind not chosen yet: listen again or pick it
            return self.async_show_menu(
                step_id="learn_timeout", menu_options=["learn", *GROUPS, "eep"]
            )
        return self.async_show_menu(
            step_id="learn_timeout", menu_options=["learn", "device", self._back]
        )

    async def _async_wait_for_telegram(self) -> ReceivedTelegram | None:
        rorgs = expected_rorgs(self._model) if self._model is not None else set()
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
        self._model = model = model_for(data)
        device_id = parse_id(data[CONF_DEVICE_ID])
        current = {s[CONF_PROFILE]: s[CONF_SENDER_ID] for s in data.get(CONF_SENDERS, ())}
        errors: dict[str, str] = {}
        if user_input is None and model.kind == "cover" and not self._settings_chosen:
            return self.async_show_menu(step_id="cover_menu", menu_options=["settings", "measure"])
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

    async def async_step_cover_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        return self.async_show_menu(step_id="cover_menu", menu_options=["settings", "measure"])

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        self._settings_chosen = True
        return await self.async_step_reconfigure()

    # I5: travel time assistant -------------------------------------------------------------

    def _cover_device(self) -> Any:
        subentry = self._get_reconfigure_subentry()
        return self._get_entry().runtime_data.devices.get(subentry.subentry_id)

    async def async_step_measure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Explain, then open fully and wait for the anchor."""
        device = self._cover_device()
        if device is None or not device.has_sender(CONTROLLER.id):
            return self.async_abort(reason="measure_needs_controller")
        if user_input is None:
            return self.async_show_form(step_id="measure", data_schema=vol.Schema({}))
        self._measured = {}
        return await self.async_step_measure_open()

    async def async_step_measure_open(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        device = self._cover_device()
        if self._measure_task is None:
            self._measure_task = self.hass.async_create_task(self._async_open_fully(device))
        if not self._measure_task.done():
            return self.async_show_progress(
                step_id="measure_open",
                progress_action="measure_open",
                progress_task=self._measure_task,
            )
        ok = self._measure_task.result()
        self._measure_task = None
        if not ok:
            return self.async_show_progress_done(next_step_id="measure_failed")
        return self.async_show_progress_done(next_step_id="measure_down")

    async def async_step_measure_failed(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        return self.async_abort(reason="measure_failed")

    async def async_step_measure_down(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        return await self._async_measure_run("measure_down", down=True, user_input=user_input)

    async def async_step_measure_up(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        return await self._async_measure_run("measure_up", down=False, user_input=user_input)

    async def _async_measure_run(
        self, step_id: str, down: bool, user_input: dict[str, Any] | None
    ) -> SubentryFlowResult:
        """Start the run when the form shows; the click stops it and takes the driven time."""
        device = self._cover_device()
        if user_input is None:
            self._run_started = time.monotonic()
            device.send(
                shutter.encode_command(shutter.DOWN if down else shutter.UP, MEASURE_MAX_RUN),
                profile=CONTROLLER.id,
                key="move",
                confirm=False,
            )
            return self.async_show_form(step_id=step_id, data_schema=vol.Schema({}))
        wall = time.monotonic() - self._run_started
        waiter = self._wait_for(device, lambda v: "driven_time" in v)
        device.send(shutter.encode_command(shutter.STOP), profile=CONTROLLER.id, confirm=False)
        try:
            async with asyncio.timeout(DRIVEN_TIME_WAIT):
                driven = (await waiter)["driven_time"]
        except TimeoutError:
            driven = round(wall, 1)  # no report: the click time is still within ~0.3 s
        self._measured["time_closes" if down else "time_opens"] = driven
        if down:
            return await self.async_step_measure_up()
        return await self.async_step_measure_result()

    async def async_step_measure_result(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        if user_input is not None:
            subentry = self._get_reconfigure_subentry()
            return self.async_update_and_abort(
                self._get_entry(), subentry, data={**subentry.data, **self._measured}
            )
        return self.async_show_form(
            step_id="measure_result",
            data_schema=vol.Schema({}),
            description_placeholders={
                "time_opens": f"{self._measured.get('time_opens', 0):.1f}",
                "time_closes": f"{self._measured.get('time_closes', 0):.1f}",
            },
        )

    async def _async_open_fully(self, device: Any) -> bool:
        waiter = self._wait_for(
            device,
            lambda v: (
                v.get("state") == "open" or (v.get("direction") == "up" and "driven_time" in v)
            ),
        )
        device.send(
            shutter.encode_command(shutter.UP, MEASURE_MAX_RUN),
            profile=CONTROLLER.id,
            key="move",
            confirm=False,
        )
        try:
            async with asyncio.timeout(MEASURE_MAX_RUN + 10):
                await waiter
        except TimeoutError:
            return False
        return True

    def _wait_for(self, device: Any, predicate: Any) -> asyncio.Future[dict[str, Any]]:
        future: asyncio.Future[dict[str, Any]] = self.hass.loop.create_future()
        remove = None

        def listener(values: dict[str, Any]) -> None:
            if not future.done() and predicate(values):
                future.set_result(values)

        remove = device.add_listener(listener)
        future.add_done_callback(lambda _f: remove())
        return future

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
                "examples": model.examples or "-",
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
        if model.kind in ("switch", "psc"):
            default = Platform.LIGHT.value if model.kind == "switch" else Platform.SWITCH.value
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
        if OPT_CALIBRATION in model.options:
            schema[vol.Required(OPT_CALIBRATION, default="passive")] = SelectSelector(
                SelectSelectorConfig(
                    options=["passive", "before_move"], translation_key=OPT_CALIBRATION
                )
            )
        if OPT_DEVICE_CLASS in model.options:
            schema[vol.Required(OPT_DEVICE_CLASS, default="window")] = SelectSelector(
                SelectSelectorConfig(options=DEVICE_CLASSES, translation_key=OPT_DEVICE_CLASS)
            )
        if OPT_INVERT in model.options:
            schema[vol.Required(OPT_INVERT, default=False)] = BooleanSelector()
        if OPT_LONG_PRESS in model.options:
            for opt, default in ((OPT_LONG_PRESS, 0.6), (OPT_DOUBLE_PRESS, 0.4)):
                schema[vol.Required(opt, default=default)] = NumberSelector(
                    NumberSelectorConfig(
                        min=0.1,
                        max=3,
                        step=0.1,
                        unit_of_measurement="s",
                        mode=NumberSelectorMode.BOX,
                    )
                )
        if OPT_STATUS_REQUEST in model.options:
            schema[vol.Required(OPT_STATUS_REQUEST, default=False)] = BooleanSelector()
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
        if model.id == GENERIC_EEP and model.receive is not None:
            data[CONF_EEP] = str(model.receive)
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


def _category_step(group: str, category: str) -> Any:
    async def step(
        self: DeviceSubentryFlow, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        return await self._async_category(group, category)

    return step


def _model_step(model_id: str) -> Any:
    async def step(
        self: DeviceSubentryFlow, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        return await self._async_chosen(CATALOG[model_id], back="kind")

    return step


# menu options are steps: async_step_eltako_lighting, ..., async_step_model_switch, ...
for _model_id in CATALOG:
    setattr(DeviceSubentryFlow, f"async_step_model_{_model_id}", _model_step(_model_id))
for _group in GROUPS:
    for _category in categories_of(_group):
        setattr(
            DeviceSubentryFlow,
            f"async_step_{_group}_{_category}",
            _category_step(_group, _category),
        )

SUBENTRY_FLOWS = {SUBENTRY_DEVICE: DeviceSubentryFlow}
