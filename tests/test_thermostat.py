"""Thermostat of a switching actuator: the decision table, the entity and its extras."""

from dataclasses import replace

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from custom_components.enocean_eltako.const import DOMAIN
from custom_components.enocean_eltako.protocol import esp2
from custom_components.enocean_eltako.protocol.telegram import RadioTelegram, Rorg
from custom_components.enocean_eltako.thermostat import (
    Inputs,
    Settings,
    Status,
    decide,
)

from .test_devices import BASE, _entity, _settle, _subentry, gateway  # noqa: F401

pytestmark = pytest.mark.usefixtures("socket_enabled")

SETTINGS = Settings(
    hysteresis=0.3,
    setpoint_min=16,
    setpoint_max=24,
    step=0.5,
    precision=0.1,
    min_cycle=180,
    max_run=7200,
    cooldown=900,
    active_power=50,
    blocked_after=1200,
    stale_after=1800,
)


def _inputs(**changes) -> Inputs:
    values = {
        "now": 10_000.0,
        "heating": True,
        "setpoint": 21.0,
        "temperature": 20.0,
        "temperature_age": 60.0,
        "relay_on": False,
        "changed_at": 1_000.0,
        "run_started": None,
        "cooldown_until": 0.0,
        "power": None,
        "low_power_since": None,
    }
    return Inputs(**{**values, **changes})


@pytest.mark.parametrize(
    ("changes", "relay", "status"),
    [
        # hysteresis: on at setpoint - 0.3, off at setpoint + 0.3, nothing in between
        ({"temperature": 20.6}, True, Status.HEATING),
        ({"temperature": 20.8}, None, Status.IDLE),
        ({"temperature": 20.8, "relay_on": True}, None, Status.HEATING),
        ({"temperature": 21.3, "relay_on": True}, False, Status.REACHED),
        ({"temperature": 21.3}, None, Status.REACHED),
        # mode Off switches off at once, even right after a change
        ({"heating": False, "relay_on": True, "changed_at": 9_990.0}, False, Status.OFF),
        ({"heating": False}, None, Status.OFF),
        # the shortest time on / off holds a switch back, the next check tries again
        ({"temperature": 19.0, "changed_at": 9_900.0}, None, Status.IDLE),
        ({"temperature": 22.0, "relay_on": True, "changed_at": 9_900.0}, None, Status.HEATING),
        # unknown relay: the first command is not held back
        ({"temperature": 19.0, "relay_on": None, "changed_at": None}, True, Status.HEATING),
        # no room temperature, or one that went silent: off for safety, at once
        (
            {"temperature": None, "relay_on": True, "changed_at": 9_990.0},
            False,
            Status.SENSOR_STALE,
        ),
        ({"temperature_age": 1_801.0, "relay_on": True}, False, Status.SENSOR_STALE),
        ({"temperature": None}, None, Status.SENSOR_STALE),
        # forced pause: nothing switches on, however cold
        ({"temperature": 15.0, "cooldown_until": 10_500.0}, None, Status.COOLDOWN),
        (
            {"temperature": 15.0, "cooldown_until": 10_500.0, "relay_on": True},
            False,
            Status.COOLDOWN,
        ),
        # the pause is over
        ({"temperature": 15.0, "cooldown_until": 9_999.0}, True, Status.HEATING),
    ],
)
def test_decide_table(changes, relay, status) -> None:
    decision = decide(SETTINGS, _inputs(**changes))
    assert (decision.relay, decision.status) == (relay, status)
    assert not decision.start_cooldown


def test_longest_run_starts_the_forced_pause() -> None:
    decision = decide(SETTINGS, _inputs(temperature=15.0, relay_on=True, run_started=2_000.0))
    assert (decision.relay, decision.status, decision.start_cooldown) == (
        False,
        Status.COOLDOWN,
        True,
    )
    shorter = decide(SETTINGS, _inputs(temperature=15.0, relay_on=True, run_started=3_000.0))
    assert shorter.relay is None
    assert shorter.status == Status.HEATING
    unlimited = replace(SETTINGS, max_run=0)  # 0 = no longest run
    assert decide(unlimited, _inputs(relay_on=True, run_started=0.0)).relay is None


@pytest.mark.parametrize(
    ("changes", "status"),
    [
        # relay on and the load takes power: heating
        ({"relay_on": True, "temperature": 20.8, "power": 1_900.0}, Status.HEATING),
        # relay on, no power for a while but not long: idle (the convector's own thermostat)
        (
            {
                "relay_on": True,
                "temperature": 20.8,
                "power": 0.0,
                "low_power_since": 9_500.0,
            },
            Status.IDLE,
        ),
        # relay on, no power for longer than allowed, room below the setpoint: blocked
        (
            {
                "relay_on": True,
                "temperature": 20.8,
                "power": 0.0,
                "low_power_since": 8_000.0,
            },
            Status.BLOCKED,
        ),
        # no power but the room is warm enough: the convector rightly rests
        (
            {
                "relay_on": True,
                "temperature": 21.2,
                "power": 0.0,
                "low_power_since": 8_000.0,
            },
            Status.IDLE,
        ),
    ],
)
def test_power_tells_whether_it_really_heats(changes, status) -> None:
    assert decide(SETTINGS, _inputs(**changes)).status == status


def test_settings_from_options_use_defaults_and_minutes() -> None:
    settings = Settings.from_options({"hysteresis": 0.5, "min_cycle": 5, "max_run": 90})
    assert settings.hysteresis == 0.5
    assert settings.min_cycle == 300
    assert settings.max_run == 5_400
    assert settings.cooldown == 900  # default 15 min
    assert settings.setpoint_max == 24


THERMOSTAT = {
    "platform": "switch",
    "senders": [{"profile": "central", "sender_id": "FF-B7-44-81"}],
    "thermostat": True,
    "thermostat_sensor": "sensor.room_temperature",
    "humidity_sensor": "sensor.room_humidity",
    "min_cycle": 0,  # the tests switch back and forth within a second
}
PREFIX = f"{BASE}_05-10-A2-B9_1"
ON = esp2.encode_radio(RadioTelegram(Rorg.BS4, bytes.fromhex("01000009"), 0xFFB74481))
OFF = esp2.encode_radio(RadioTelegram(Rorg.BS4, bytes.fromhex("01000008"), 0xFFB74481))


@pytest.mark.parametrize(
    "gateway",
    [
        [
            _subentry("switch", "05-10-A2-B9", "Konvektor Bad", **THERMOSTAT),
            _subentry("switch", "05-10-A2-BA", "Konvektor ohne", platform="switch"),
        ]
    ],
    indirect=True,
)
async def test_thermostat_regulates_and_reports(hass: HomeAssistant, gateway) -> None:  # noqa: F811
    entry, server = gateway
    climate = _entity(hass, "climate", f"{PREFIX}_thermostat")
    assert climate is not None
    assert _entity(hass, "climate", f"{BASE}_05-10-A2-BA_1_thermostat") is None  # off: none

    # no room temperature yet: relay off, reported as a safety state, a repair issue says so
    state = hass.states.get(climate)
    assert state.attributes["status"] == "sensor_stale"
    assert state.attributes.get("current_humidity") is None
    issues = ir.async_get(hass)
    assert issues.async_get_issue(DOMAIN, f"thermostat_stale_{BASE}_05-10-A2-B9")

    # the first reading: an 18 °C room against the default setpoint of 21 °C asks for heat
    server.received.clear()
    hass.states.async_set("sensor.room_humidity", "51")
    hass.states.async_set("sensor.room_temperature", "18.04")
    await _settle(hass)
    assert ON in bytes(server.received)
    state = hass.states.get(climate)
    assert state.attributes["current_temperature"] == 18.0  # rounded to 0.1
    assert state.attributes["current_humidity"] == 51
    assert state.attributes["min_temp"] == 16
    assert state.attributes["max_temp"] == 24
    assert issues.async_get_issue(DOMAIN, f"thermostat_stale_{BASE}_05-10-A2-B9") is None

    # the relay is on through the sender; without a meter on the load "on" counts as heating
    await hass.services.async_call(
        "climate", "set_temperature", {"entity_id": climate, "temperature": 21}, blocking=True
    )
    await _settle(hass)
    state = hass.states.get(climate)
    assert state.attributes["hvac_action"] == "heating"
    assert state.attributes["temperature"] == 21

    # the setpoint stays inside the limits
    await hass.services.async_call(
        "climate", "set_temperature", {"entity_id": climate, "temperature": 24}, blocking=True
    )
    assert hass.states.get(climate).attributes["temperature"] == 24

    # warm enough: off
    server.received.clear()
    hass.states.async_set("sensor.room_temperature", "24.6")
    await _settle(hass)
    assert OFF in bytes(server.received)
    assert hass.states.get(climate).attributes["hvac_action"] == "idle"

    # mode Off: relay off, action off
    await hass.services.async_call(
        "climate", "set_hvac_mode", {"entity_id": climate, "hvac_mode": "off"}, blocking=True
    )
    await _settle(hass)
    state = hass.states.get(climate)
    assert state.state == "off"
    assert state.attributes["hvac_action"] == "off"

    # the extra entities follow the controller
    run = _entity(hass, "sensor", f"{PREFIX}_thermostat_run")
    heating = _entity(hass, "binary_sensor", f"{PREFIX}_thermostat_heating")
    blocked = _entity(hass, "binary_sensor", f"{PREFIX}_thermostat_blocked")
    assert None not in (run, heating, blocked)
    assert hass.states.get(heating).state == "off"
    assert hass.states.get(blocked).state == "off"


@pytest.mark.parametrize(
    "gateway",
    [
        [
            _subentry(
                "switch",
                "05-10-A2-B9",
                "Konvektor Bad",
                **{**THERMOSTAT, "thermostat_attributes": False, "thermostat_entities": False},
            )
        ]
    ],
    indirect=True,
)
async def test_thermostat_extras_can_be_switched_off(hass: HomeAssistant, gateway) -> None:  # noqa: F811
    climate = _entity(hass, "climate", f"{PREFIX}_thermostat")
    assert "status" not in hass.states.get(climate).attributes
    assert _entity(hass, "sensor", f"{PREFIX}_thermostat_run") is None
    assert _entity(hass, "binary_sensor", f"{PREFIX}_thermostat_heating") is None


@pytest.mark.parametrize(
    "gateway",
    [
        [
            {
                **_subentry("switch", "05-10-A2-B9", "Konvektor Bad", **THERMOSTAT),
                "subentry_id": "switch-bad",
            },
            _subentry("meter", "05-20-30-40", "Konvektor Zähler", part_of="switch-bad"),
        ]
    ],
    indirect=True,
)
async def test_thermostat_reads_the_power_of_the_meter_on_its_load(
    hass: HomeAssistant,
    gateway,  # noqa: F811
) -> None:
    entry, server = gateway
    climate = _entity(hass, "climate", f"{PREFIX}_thermostat")
    device = entry.runtime_data.devices["switch-bad"]
    controller = device.thermostat
    assert controller.has_meter  # found through the meter's "belongs to device"

    hass.states.async_set("sensor.room_temperature", "18.0")
    await hass.services.async_call(
        "climate", "set_temperature", {"entity_id": climate, "temperature": 21}, blocking=True
    )
    await _settle(hass)
    # relay on, the meter reports no power at all yet: heating is not confirmed
    controller._meter_values({"DT": 1, "MR": 0.0})  # noqa: SLF001
    await _settle(hass)
    state = hass.states.get(climate)
    assert state.attributes["power"] == 0.0
    assert state.attributes["hvac_action"] == "idle"  # on, but the load takes no power
    controller._meter_values({"DT": 1, "MR": 1_950.0})  # noqa: SLF001
    await _settle(hass)
    state = hass.states.get(climate)
    assert state.attributes["power"] == 1_950.0
    assert state.attributes["hvac_action"] == "heating"


@pytest.mark.parametrize(
    "gateway",
    [
        [
            _subentry(
                "switch",
                "05-10-A2-B9",
                "Konvektor Bad",
                platform="switch",
                senders=[{"profile": "central", "sender_id": "FF-B7-44-81"}],
            )
        ]
    ],
    indirect=True,
)
async def test_thermostat_form_validates_and_saves(hass: HomeAssistant, gateway) -> None:  # noqa: F811
    entry, _server = gateway
    subentry_id = next(iter(entry.subentries))
    assert _entity(hass, "climate", f"{PREFIX}_thermostat") is None  # off by default
    base = {
        "name": "Konvektor Bad",
        "sender_central": "FF-B7-44-81",
        "platform": "switch",
    }

    async def submit(section: dict):
        flow = await entry.start_subentry_reconfigure_flow(hass, subentry_id)
        return await hass.config_entries.subentries.async_configure(
            flow["flow_id"], {**base, "thermostat_settings": section}
        )

    # switched on without a room temperature sensor
    result = await submit({"thermostat": True})
    assert result["errors"] == {"base": "thermostat_no_sensor"}
    # the lowest setpoint must be below the highest
    result = await submit(
        {
            "thermostat": True,
            "thermostat_sensor": "sensor.room_temperature",
            "setpoint_min": 24,
            "setpoint_max": 20,
        }
    )
    assert result["errors"] == {"base": "thermostat_setpoint_range"}
    # a longest run needs a forced pause
    result = await submit(
        {
            "thermostat": True,
            "thermostat_sensor": "sensor.room_temperature",
            "max_run": 120,
            "cooldown": 0,
        }
    )
    assert result["errors"] == {"base": "thermostat_no_cooldown"}

    # saved: the options are flat in the subentry, the thermostat entity appears
    hass.states.async_set("sensor.room_temperature", "19")
    result = await submit(
        {
            "thermostat": True,
            "thermostat_sensor": "sensor.room_temperature",
            "hysteresis": 0.5,
            "max_run": 120,
            "cooldown": 15,
        }
    )
    assert result["type"] == "abort"
    await hass.async_block_till_done()
    data = dict(next(iter(entry.subentries.values())).data)
    assert data["thermostat"] is True
    assert data["thermostat_sensor"] == "sensor.room_temperature"
    assert data["hysteresis"] == 0.5
    assert data["schema"] == 7
    assert _entity(hass, "climate", f"{PREFIX}_thermostat") is not None

    # switched off again: the thermostat and its extras are removed
    result = await submit({"thermostat": False})
    assert result["type"] == "abort"
    await hass.async_block_till_done()
    assert _entity(hass, "climate", f"{PREFIX}_thermostat") is None
    assert _entity(hass, "sensor", f"{PREFIX}_thermostat_run") is None


@pytest.mark.parametrize(
    "gateway",
    [[_subentry("switch", "05-10-A2-B9", "Konvektor Bad", **THERMOSTAT)]],
    indirect=True,
)
async def test_the_restored_mode_is_known_before_the_controller_decides(
    hass: HomeAssistant,
    gateway,  # noqa: F811
) -> None:
    from custom_components.enocean_eltako.thermostat import ThermostatController

    entry, _server = gateway
    device = next(iter(entry.runtime_data.devices.values()))
    hass.states.async_set("sensor.room_temperature", "15")
    controller = ThermostatController(hass, device)
    sent: list[bool] = []
    controller._send = lambda relay, now: sent.append(relay)  # type: ignore[method-assign]
    controller.start()  # the extra entities start it before the climate entity restores
    assert sent == []  # the defaults (21 °C, heating) must not switch the relay on
    controller.restore(None, False)  # last mode: off
    assert True not in sent
    controller.stop()


def test_a_rocker_telegram_with_an_impossible_code_is_ignored() -> None:
    from custom_components.enocean_eltako.binary_sensor import _rocker_contact

    value = _rocker_contact("a0", "a1")
    assert value({"EB": 1, "R1": 7, "NU": 1}) is None  # three bits, only 0...3 are buttons
    assert value({"EB": 1, "R1": 3, "NU": 0}) is None  # several buttons at once
    assert value({"EB": 1, "R1": 1, "NU": 1}) is True  # a0
