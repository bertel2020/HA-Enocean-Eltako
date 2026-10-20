"""Subentry flow: add or reconfigure a device (catalog model, ID, senders, options)."""

from __future__ import annotations

import asyncio
import time
from typing import Any, cast

import probatio as vol
from homeassistant.config_entries import ConfigSubentryFlow, SubentryFlowResult
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import section
from homeassistant.helpers.selector import (
    BooleanSelector,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)
from homeassistant.helpers.translation import async_get_translations

from .catalog import (
    CATALOG,
    CONTROLLER,
    CUSTOM,
    EEP_OPTIONS,
    EEP_TO_MODEL,
    GENERIC_EEP,
    GENERIC_EEPS,
    GROUP_ELTAKO,
    GROUP_ENOCEAN,
    GROUP_VIRTUAL,
    GROUPS,
    OPT_CALIBRATION,
    OPT_CHANNEL,
    OPT_DEVICE_CLASS,
    OPT_DOUBLE_PRESS,
    OPT_FIELDS,
    OPT_INVERT,
    OPT_LONG_PRESS,
    OPT_OFF_BUTTON,
    OPT_ON_BUTTON,
    OPT_PLATFORM,
    OPT_ROCKER_OFF,
    OPT_ROCKER_ON,
    OPT_ROUTING,
    OPT_SEND_INTERVAL,
    OPT_SOURCE,
    OPT_STATUS_REQUEST,
    OPT_TEMPERATURE_SENSOR,
    OPT_TENTHS,
    OPT_TILT_TIME,
    OPT_TIME_CLOSES,
    OPT_TIME_OPENS,
    OPT_UNAVAILABLE_WHEN_SILENT,
    OPT_VENT_TIME,
    OPT_WALL_OFF,
    OPT_WALL_ON,
    OPT_WALL_SWITCH,
    OPT_WEATHER_BRIGHTNESS,
    OPT_WEATHER_RAIN,
    OPT_WEATHER_TEMPERATURE,
    OPT_WEATHER_WIND,
    OPT_WHEN_UNAVAILABLE,
    WEATHER_SOURCES,
    DeviceModel,
    categories_of,
    custom_model,
    eep_choice,
    generic_fields,
    generic_model,
    model_for,
    models_in,
)
from .const import (
    CONF_CUSTOM,
    CONF_DEVICE_ID,
    CONF_EEP,
    CONF_MODEL,
    CONF_NAME,
    CONF_PROFILE,
    CONF_SENDER_ID,
    CONF_SENDERS,
    DOMAIN,
    SUBENTRY_DEVICE,
    SUBENTRY_SCHEMA,
)
from .custom_devices import DEFINITIONS
from .protocol.dispatcher import ReceivedTelegram
from .protocol.eep import EEPRef
from .protocol.eep.eltako import shutter
from .protocol.eep.teach_in import MANUFACTURER_ELTAKO, TeachIn4BS, decode_teach_in_4bs
from .protocol.eep.ute import decode_ute_request
from .protocol.ids import format_id, parse_id
from .protocol.models import MODELS
from .protocol.sender_pool import SenderIdError, SenderPool
from .protocol.telegram import Rorg

DEVICE_CLASSES = ["door", "window", "garage_door", "opening"]
# I9: entities a virtual sensor can follow
SOURCE_SELECTORS = {
    "virtual_contact": EntitySelectorConfig(domain=["binary_sensor", "input_boolean", "switch"]),
    "virtual_motion": EntitySelectorConfig(domain=["binary_sensor", "input_boolean"]),
    "virtual_temperature": EntitySelectorConfig(
        domain=["sensor", "input_number"], device_class="temperature"
    ),
    "virtual_brightness": EntitySelectorConfig(
        domain=["sensor", "input_number"], device_class="illuminance"
    ),
}
WEATHER_SELECTORS = {
    OPT_WEATHER_TEMPERATURE: EntitySelectorConfig(
        domain=["sensor", "input_number"], device_class="temperature"
    ),
    OPT_WEATHER_WIND: EntitySelectorConfig(
        domain=["sensor", "input_number"], device_class="wind_speed"
    ),
    OPT_WEATHER_RAIN: EntitySelectorConfig(domain=["binary_sensor", "input_boolean"]),
    OPT_WEATHER_BRIGHTNESS: EntitySelectorConfig(
        domain=["sensor", "input_number"], device_class="illuminance"
    ),
}
WHEN_UNAVAILABLE = ["skip", "safe"]
DEFAULT_VIRTUAL_INTERVAL = 900  # seconds, as Eltako sensors repeat their state
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
    "D2": {0xD2, 0xD4},  # VLD actuators teach in by UTE
}


def expected_rorgs(model: DeviceModel) -> set[int]:
    if model.receive is None:
        return set()
    rorgs = set(_RORG_BY_PREFIX.get(model.receive.eep[:2], ()))
    for extra in model.receive_extra:
        rorgs |= _RORG_BY_PREFIX.get(extra.eep[:2], set())
    return rorgs


def receives(model: DeviceModel, eep: str) -> bool:
    return any(r.eep == eep for r in (model.receive, *model.receive_extra) if r is not None)


def candidates(rorg: int, teach_in: TeachIn4BS | None, data: bytes = b"") -> list[str]:
    """Catalog kinds a heard telegram may come from; a 4BS teach-in names its EEP and
    manufacturer, so Eltako entries come first for Eltako devices; a UTE query (VLD
    actuators) names its EEP, matched by RORG and FUNC (D2-01-12 -> D2-01-00)."""
    if rorg == Rorg.UTE and (request := decode_ute_request(data)) is not None:
        family = request.eep[:5]
        return [m.id for m in CATALOG.values() if m.receive and m.receive.eep[:5] == family]
    if teach_in is not None:
        kinds = [m for m in CATALOG.values() if receives(m, teach_in.eep)]
        if kinds:
            eltako = teach_in.manufacturer == MANUFACTURER_ELTAKO
            kinds.sort(key=lambda m: (m.group == GROUP_ELTAKO) != eltako)
            return [m.id for m in kinds]
    return [m.id for m in CATALOG.values() if rorg in expected_rorgs(m)]


OPTION_KEYS = (
    OPT_PLATFORM,
    OPT_FIELDS,
    OPT_VENT_TIME,
    OPT_TILT_TIME,
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
    OPT_TENTHS,
    OPT_SOURCE,
    OPT_WHEN_UNAVAILABLE,
    OPT_CHANNEL,
    OPT_WALL_SWITCH,
    OPT_WALL_ON,
    OPT_WALL_OFF,
    OPT_ROCKER_ON,
    OPT_ROCKER_OFF,
    *WEATHER_SOURCES,
)
BUTTONS = ["b0", "b1", "a0", "a1"]
# collapsed sections of rarely needed fields; the subentry data stays flat
SECTION_ROCKER = "rocker_buttons"
SECTION_WALL = "wall_switch_settings"
SECTIONS = {
    SECTION_ROCKER: (OPT_ROCKER_ON, OPT_ROCKER_OFF),
    SECTION_WALL: (OPT_WALL_SWITCH, OPT_WALL_ON, OPT_WALL_OFF),
}


def flatten_sections(values: dict[str, Any]) -> dict[str, Any]:
    """Form input with the fields of its sections moved to the top level."""
    flat = {k: v for k, v in values.items() if k not in SECTIONS}
    for name in SECTIONS:
        flat.update(values.get(name) or {})
    return flat


def nest_sections(values: dict[str, Any]) -> dict[str, Any]:
    """Flat values grouped like the form: section fields under their section."""
    nested = {k: v for k, v in values.items() if not any(k in f for f in SECTIONS.values())}
    for name, fields in SECTIONS.items():
        nested[name] = {k: values[k] for k in fields if k in values}
    return nested


def _buttons_section(fields: dict[Any, Any], buttons: tuple[tuple[str, str], ...]) -> section:
    """A collapsed section: the given fields plus one rocker button choice per option."""
    for opt, default in buttons:
        fields[vol.Required(opt, default=default)] = SelectSelector(
            SelectSelectorConfig(options=BUTTONS, translation_key="rocker_button")
        )
    return section(vol.Schema(fields), {"collapsed": True})


def sender_owner(device_id: int, profile: str) -> str:
    return f"device:{format_id(device_id)}:{profile}"


def sender_field(profile: str) -> str:
    return f"sender_{profile}"


class DeviceForm:
    """Device form shared by the subentry flow and the discovery flow: fields, save.

    The flow provides hass, _model, _get_entry() (the gateway entry) and the FlowHandler API.
    """

    hass: HomeAssistant
    _device_model: DeviceModel | None
    _custom = ""  # I8: id of the chosen definition
    _get_entry: Any

    async def _teach_hint(self, model: DeviceModel) -> str:
        """How to put this kind into learn mode, for actuators (translated, may be empty)."""
        if not model.senders:
            return ""
        translations = await async_get_translations(
            self.hass, self.hass.config.language, "selector", [DOMAIN]
        )
        prefix = f"component.{DOMAIN}.selector.teach_hint.options."
        hint = translations.get(prefix + model.kind) or translations.get(prefix + "default", "")
        if MODELS[self._get_entry().data[CONF_MODEL]].bus and model.group != GROUP_VIRTUAL:
            # E11: bus actors confirm a taught-in controller only with the FAM14 switch at 2
            hint = f"{hint} {translations.get(prefix + 'bus', '')}".strip()
        return hint

    async def _form(
        self,
        step_id: str,
        schema: dict[Any, Any],
        values: dict[str, Any] | None,
        errors: dict[str, str],
    ) -> Any:
        assert self._device_model is not None
        model = self._device_model
        if errors and values is not None and model.any_sender:  # a cleared sender stays empty
            values = {**{sender_field(p.id): "" for p in model.senders}, **values}
        return self.async_show_form(  # type: ignore[attr-defined]
            step_id=step_id,
            data_schema=self.add_suggested_values_to_schema(  # type: ignore[attr-defined]
                vol.Schema(schema), values
            ),
            errors=errors,
            description_placeholders={
                "examples": model.examples or "-",
                "receive": str(model.receive) if model.receive else "-",
                "send": ", ".join(f"{p.id} ({p.eep})" for p in model.senders) or "-",
                "hint": await self._teach_hint(model),
            },
        )

    def _pool(self) -> SenderPool:
        return cast(SenderPool, self._get_entry().runtime_data.senders.pool)

    def _fields(self, model: DeviceModel, current: dict[str, str]) -> dict[Any, Any]:
        """Sender IDs (first suggested from the pool, required unless any one will do), options."""
        schema: dict[Any, Any] = {}
        virtual_fixed = model.group == GROUP_VIRTUAL and bool(current)
        for index, profile in enumerate(() if virtual_fixed else model.senders):
            field = sender_field(profile.id)
            if index == 0:
                suggested = current.get(profile.id)
                if not current and (free := self._pool().next_free()) is not None:
                    suggested = format_id(free)
                key: vol.Required | vol.Optional
                if model.any_sender:  # suggested only, so it can be left empty
                    key = vol.Optional(field, description={"suggested_value": suggested})
                elif suggested:
                    key = vol.Required(field, default=suggested)
                else:
                    key = vol.Required(field)
            else:
                key = vol.Optional(field)
            schema[key] = TextSelector()
        if model.kind in ("switch", "psc", "vld_switch"):
            default = Platform.SWITCH.value if model.kind == "psc" else Platform.LIGHT.value
            schema[vol.Required(OPT_PLATFORM, default=default)] = SelectSelector(
                SelectSelectorConfig(
                    options=[Platform.LIGHT.value, Platform.SWITCH.value],
                    translation_key=OPT_PLATFORM,
                )
            )
        if model.id == GENERIC_EEP and model.receive is not None:
            fields = generic_fields(model.receive.eep)
            schema[vol.Required(OPT_FIELDS, default=[k for k, _f in fields])] = SelectSelector(
                SelectSelectorConfig(
                    options=[SelectOptionDict(value=k, label=f.name) for k, f in fields],
                    multiple=True,
                    mode=SelectSelectorMode.LIST,
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
        if OPT_VENT_TIME in model.options:
            for opt in (OPT_VENT_TIME, OPT_TILT_TIME):
                schema[vol.Required(opt, default=0)] = NumberSelector(
                    NumberSelectorConfig(
                        min=0,
                        max=10,
                        step=0.1,
                        unit_of_measurement="s",
                        mode=NumberSelectorMode.BOX,
                    )
                )
        if OPT_CHANNEL in model.options:
            schema[vol.Required(OPT_CHANNEL, default=0)] = NumberSelector(
                NumberSelectorConfig(min=0, max=29, step=1, mode=NumberSelectorMode.BOX)
            )
        for opt, selector in WEATHER_SELECTORS.items():
            if opt in model.options:
                schema[vol.Optional(opt)] = EntitySelector(selector)
        if OPT_SOURCE in model.options or OPT_WEATHER_TEMPERATURE in model.options:
            if OPT_SOURCE in model.options:
                schema[vol.Required(OPT_SOURCE)] = EntitySelector(SOURCE_SELECTORS[model.kind])
            schema[vol.Required(OPT_SEND_INTERVAL, default=DEFAULT_VIRTUAL_INTERVAL)] = (
                NumberSelector(
                    NumberSelectorConfig(
                        min=0,
                        max=3600,
                        step=60,
                        unit_of_measurement="s",
                        mode=NumberSelectorMode.BOX,
                    )
                )
            )
        if OPT_WHEN_UNAVAILABLE in model.options:
            schema[vol.Required(OPT_WHEN_UNAVAILABLE, default="skip")] = SelectSelector(
                SelectSelectorConfig(options=WHEN_UNAVAILABLE, translation_key=OPT_WHEN_UNAVAILABLE)
            )
        if OPT_ROUTING in model.options:
            schema[vol.Required(OPT_ROUTING, default=model.senders[0].id)] = SelectSelector(
                SelectSelectorConfig(
                    options=[*(p.id for p in model.senders), "both"],
                    translation_key=OPT_ROUTING,
                )
            )
        if OPT_TEMPERATURE_SENSOR in model.options:
            schema[vol.Optional(OPT_TEMPERATURE_SENSOR)] = EntitySelector(
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
        if OPT_TENTHS in model.options:
            schema[vol.Required(OPT_TENTHS, default=False)] = BooleanSelector()
        if OPT_DEVICE_CLASS in model.options:
            schema[vol.Required(OPT_DEVICE_CLASS, default="window")] = SelectSelector(
                SelectSelectorConfig(options=DEVICE_CLASSES, translation_key=OPT_DEVICE_CLASS)
            )
        if OPT_INVERT in model.options:
            schema[vol.Required(OPT_INVERT, default=False)] = BooleanSelector()
        if OPT_LONG_PRESS in model.options:
            for opt, seconds in ((OPT_LONG_PRESS, 0.6), (OPT_DOUBLE_PRESS, 0.4)):
                schema[vol.Required(opt, default=seconds)] = NumberSelector(
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
        if OPT_ROCKER_ON in model.options:
            schema[vol.Optional(SECTION_ROCKER, default={})] = _buttons_section(
                {}, ((OPT_ROCKER_ON, "a0"), (OPT_ROCKER_OFF, "a1"))
            )
        if OPT_WALL_SWITCH in model.options:
            schema[vol.Optional(SECTION_WALL, default={})] = _buttons_section(
                {vol.Optional(OPT_WALL_SWITCH): TextSelector()},
                ((OPT_WALL_ON, "a0"), (OPT_WALL_OFF, "a1")),
            )
        return schema

    async def _async_save(
        self,
        user_input: dict[str, Any],
        device_id: int,
        current: dict[str, str],
        errors: dict[str, str],
    ) -> dict[str, Any] | None:
        """Validate and assign sender IDs; returns the subentry data or None on errors."""
        assert self._device_model is not None
        user_input = flatten_sections(user_input)
        model = self._device_model
        pool = self._pool()
        wanted: dict[str, int] = {}
        for sender_profile in model.senders:
            field = sender_field(sender_profile.id)
            text = (user_input.get(field) or "").strip()
            if not text:
                continue
            try:
                sender = parse_id(text)
            except ValueError:
                errors[field] = "sender_invalid_id"
                continue
            if sender in wanted.values():
                errors[field] = "sender_in_use"
                continue
            wanted[sender_profile.id] = sender
        if model.any_sender and not wanted and not errors:
            errors["base"] = "sender_none"
        if OPT_WEATHER_TEMPERATURE in model.options and not any(
            user_input.get(key) for key in WEATHER_SOURCES
        ):
            errors["base"] = "weather_no_source"
        if wall_switch := (user_input.get(OPT_WALL_SWITCH) or "").strip():
            try:
                user_input = {**user_input, OPT_WALL_SWITCH: format_id(parse_id(wall_switch))}
            except ValueError:
                errors["base"] = "wall_switch_invalid_id"  # a field in a section
        else:
            user_input = {k: v for k, v in user_input.items() if k != OPT_WALL_SWITCH}
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
        if model.id in (GENERIC_EEP, CUSTOM) and model.receive is not None:
            data[CONF_EEP] = str(model.receive)  # I8: the fallback when a definition is gone
        if model.id == CUSTOM:
            data[CONF_CUSTOM] = self._custom
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


class DeviceSubentryFlow(DeviceForm, ConfigSubentryFlow):
    """Add a device: model, then name, ID, senders and options. Reconfigure: all but the ID."""

    def __init__(self) -> None:
        self._device_model: DeviceModel | None = None
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
        self._device_model = None  # also when coming back: learning then suggests the kind
        custom = [CUSTOM] if DEFINITIONS else []  # I8: the user's own definitions
        return self.async_show_menu(
            step_id="user", menu_options=["learn", *GROUPS, GROUP_VIRTUAL, "eep", *custom]
        )

    async def async_step_custom(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """I8: a device of the user's definitions (custom_devices.yaml)."""
        if user_input is not None:
            self._custom = user_input[CONF_CUSTOM]
            return await self._async_chosen(custom_model(DEFINITIONS[self._custom]), back="custom")
        return self.async_show_form(
            step_id="custom",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CUSTOM): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                SelectOptionDict(value=d.id, label=f"{d.name} ({d.eep.eep})")
                                for d in DEFINITIONS.values()
                            ],
                            mode=SelectSelectorMode.LIST,
                        )
                    )
                }
            ),
        )

    async def async_step_virtual(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """I9: Home Assistant sends as a sensor or rocker; the kinds, back to the start."""
        self._kinds = [m.id for m in CATALOG.values() if m.group == GROUP_VIRTUAL]
        self._group = "user"
        return await self.async_step_kind()

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
        self._device_model = model
        self._back = back
        if model.group == GROUP_VIRTUAL:  # its ID is its own sender ID
            return await self.async_step_device()
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
        """By EEP: standard profiles as a generic device, the rest via the catalog.

        The list starts with the named choices, then every standard profile by its code; the
        field filters as you type, and a typed code ("A5-04-02") is accepted too.
        """
        errors: dict[str, str] = {}
        if user_input is not None:
            option = eep_choice(user_input[CONF_EEP])
            if option is None:
                errors[CONF_EEP] = "unknown_eep"
            elif option in EEP_TO_MODEL:
                return await self._async_chosen(CATALOG[EEP_TO_MODEL[option]], back="eep")
            else:
                return await self._async_chosen(generic_model(EEP_OPTIONS[option]), back="eep")
        return self.async_show_form(
            step_id="eep",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EEP): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                SelectOptionDict(value=option, label=str(ref.eep))
                                for option, ref in EEP_OPTIONS.items()
                            ],
                            translation_key=CONF_EEP,
                            mode=SelectSelectorMode.DROPDOWN,
                            custom_value=True,
                        )
                    )
                }
            ),
            errors=errors,
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
        if self._device_model is None:
            return self.async_show_progress_done(next_step_id="learned")
        return self.async_show_progress_done(next_step_id="device")

    async def async_step_learned(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Heard a new sender before the kind was chosen: offer the kinds that fit."""
        assert self._learned is not None
        if user_input is not None:
            self._device_model = CATALOG[user_input[CONF_MODEL]]
            return await self.async_step_device()
        telegram = self._learned.telegram
        teach_in = decode_teach_in_4bs(telegram.data) if telegram.rorg == Rorg.BS4 else None
        if teach_in is not None and teach_in.eep in GENERIC_EEPS:
            fitting = [m for m in CATALOG.values() if receives(m, teach_in.eep)]
            if not fitting:  # no catalog entry decodes it: generic device
                self._device_model = generic_model(EEPRef(teach_in.eep, "std"))
                return await self.async_step_device()
        kinds = candidates(telegram.rorg, teach_in, telegram.data)
        if len(kinds) == 1:
            self._device_model = CATALOG[kinds[0]]
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
        if self._device_model is None:  # kind not chosen yet: listen again or pick it
            return self.async_show_menu(
                step_id="learn_timeout", menu_options=["learn", *GROUPS, GROUP_VIRTUAL, "eep"]
            )
        return self.async_show_menu(
            step_id="learn_timeout", menu_options=["learn", "device", self._back]
        )

    async def _async_wait_for_telegram(self) -> ReceivedTelegram | None:
        rorgs = expected_rorgs(self._device_model) if self._device_model is not None else set()
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
        assert self._device_model is not None
        entry = self._get_entry()
        errors: dict[str, str] = {}
        virtual = self._device_model.group == GROUP_VIRTUAL
        id_field = sender_field(self._device_model.senders[0].id) if virtual else CONF_DEVICE_ID
        if user_input is not None:
            device_id = None
            try:
                device_id = parse_id(user_input[id_field])
            except ValueError:
                errors[id_field] = "sender_invalid_id" if virtual else "invalid_id"
            else:
                if any(s.unique_id == format_id(device_id) for s in entry.subentries.values()):
                    errors[id_field] = "already_configured"
            if device_id is not None and not errors:
                result = await self._async_save(user_input, device_id, {}, errors)
                if result is not None:
                    return self.async_create_entry(
                        title=user_input[CONF_NAME], data=result, unique_id=format_id(device_id)
                    )
        schema = {
            vol.Required(CONF_NAME): TextSelector(),
            **({} if virtual else {vol.Required(CONF_DEVICE_ID): TextSelector()}),
            **self._fields(self._device_model, {}),
        }
        if user_input is None and self._learned is not None:
            user_input = {CONF_DEVICE_ID: format_id(self._learned.sender)}
        form: SubentryFlowResult = await self._form("device", schema, user_input, errors)
        return form

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        if not self._loaded():
            return self.async_abort(reason="gateway_not_loaded")
        subentry = self._get_reconfigure_subentry()
        data = dict(subentry.data)
        self._device_model = model = model_for(data)
        self._custom = data.get(CONF_CUSTOM, "")
        device_id = parse_id(data[CONF_DEVICE_ID])
        current = {s[CONF_PROFILE]: s[CONF_SENDER_ID] for s in data.get(CONF_SENDERS, ())}
        errors: dict[str, str] = {}
        if user_input is None and model.kind == "cover" and not self._settings_chosen:
            return self.async_show_menu(step_id="cover_menu", menu_options=["settings", "measure"])
        if user_input is not None:
            if model.group == GROUP_VIRTUAL:  # the sender is the device's ID: it stays
                user_input = {**user_input, **{sender_field(p): s for p, s in current.items()}}
            result = await self._async_save(user_input, device_id, current, errors)
            if result is not None:
                return self.async_update_and_abort(
                    self._get_entry(), subentry, title=user_input[CONF_NAME], data=result
                )
        suggested = nest_sections(
            {
                CONF_NAME: subentry.title,
                **{k: data[k] for k in (*OPTION_KEYS, OPT_DEVICE_CLASS) if k in data},
                **{sender_field(p): s for p, s in current.items()},
            }
        )
        schema = {vol.Required(CONF_NAME): TextSelector(), **self._fields(model, current)}
        form: SubentryFlowResult = await self._form(
            "reconfigure", schema, user_input or suggested, errors
        )
        return form

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
