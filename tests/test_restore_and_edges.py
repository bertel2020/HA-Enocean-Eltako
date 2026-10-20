"""States restored after a restart, and edge cases of lights, switches and the heating."""

from datetime import timedelta

import pytest
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import issue_registry as ir
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
    mock_restore_cache,
)

from custom_components.enocean_eltako import climate
from custom_components.enocean_eltako.const import DOMAIN
from custom_components.enocean_eltako.protocol import esp2
from custom_components.enocean_eltako.protocol.eep.eltako import heating, switching
from custom_components.enocean_eltako.protocol.models import Protocol
from custom_components.enocean_eltako.protocol.telegram import RadioTelegram, Rorg

from .fake_gateway import FakeGateway
from .test_devices import BASE, _entity, _push, _settle, gateway  # noqa: F401

pytestmark = pytest.mark.usefixtures("socket_enabled")


def _sub(model: str, device: str, title: str, senders: list[tuple[str, str]], **options):
    from homeassistant.config_entries import ConfigSubentryData

    return ConfigSubentryData(
        data={
            "schema": 2,
            "model": model,
            "device_id": device,
            "senders": [{"profile": p, "sender_id": s} for p, s in senders],
            **options,
        },
        subentry_type="device",
        title=title,
        unique_id=device,
    )


SUBENTRIES = [
    _sub("switch", "05-00-00-01", "Licht", [("central", "FF-B7-44-81")]),
    _sub("dimmer", "05-00-00-02", "Dimmer", [("central", "FF-B7-44-82")]),
    _sub("dimmer", "05-00-00-03", "Dimmer Taster", [("rocker", "FF-B7-44-83")]),
    _sub("vld_switch", "05-00-00-04", "Steckdose", [("vld", "FF-B7-44-84")], platform="switch"),
    _sub("vld_switch", "05-00-00-05", "VLD Licht", [("vld", "FF-B7-44-85")]),
    _sub(
        "heating_actuator",
        "05-00-00-06",
        "Heizung",
        [("controller", "FF-B7-44-86")],
        temperature_sensor="sensor.raum",
        send_interval=60,
    ),
]


def uid(device: str, key: str) -> str:
    return f"{BASE}_{device}_1_{key}"


@pytest.fixture
async def restored(hass: HomeAssistant):
    mock_restore_cache(
        hass,
        [
            State("light.licht", "on"),
            State("light.dimmer", "on", {"brightness": 77}),
            State("switch.steckdose", "on"),
            State("light.vld_licht", "on", {"brightness": 128}),
            State("climate.heizung", "off", {"temperature": 19.5}),
        ],
    )
    hass.states.async_set("sensor.raum", "20.0")
    server = await FakeGateway(Protocol.ESP2).start()
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=BASE,
        data={
            "model": "fam_usb",
            "device": {"type": "tcp", "host": "127.0.0.1", "port": server.port},
            "base_id": BASE,
        },
        options={"message_delay": 0},
        subentries_data=SUBENTRIES,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    await server.connected.wait()
    yield entry, server
    await hass.config_entries.async_unload(entry.entry_id)
    await server.stop()


def _sent(server, rorg: int, data: bytes, sender: int, status: int = 0) -> bool:
    return esp2.encode_radio(RadioTelegram(rorg, data, sender, status)) in bytes(server.received)


async def test_states_are_restored(hass: HomeAssistant, restored) -> None:
    assert hass.states.get(_entity(hass, "light", uid("05-00-00-01", "light"))).state == "on"
    dimmer = hass.states.get(_entity(hass, "light", uid("05-00-00-02", "light")))
    assert dimmer.attributes["brightness"] == 77
    assert hass.states.get(_entity(hass, "switch", uid("05-00-00-04", "switch"))).state == "on"
    vld_light = hass.states.get(_entity(hass, "light", uid("05-00-00-05", "light")))
    assert vld_light.attributes["brightness"] == 128
    heater = hass.states.get(_entity(hass, "climate", uid("05-00-00-06", "climate")))
    assert heater.state == "off"
    assert heater.attributes["temperature"] == 19.5


async def test_dimmers_and_vld_switch(hass: HomeAssistant, restored) -> None:
    _entry, server = restored
    dimmer = _entity(hass, "light", uid("05-00-00-02", "light"))
    rocker_dimmer = _entity(hass, "light", uid("05-00-00-03", "light"))
    socket = _entity(hass, "switch", uid("05-00-00-04", "switch"))
    for service, entity_id in (
        ("turn_on", dimmer),
        ("turn_off", dimmer),
        ("turn_on", rocker_dimmer),
        ("turn_off", rocker_dimmer),
    ):
        await hass.services.async_call("light", service, {"entity_id": entity_id}, blocking=True)
        await _settle(hass)
    await hass.services.async_call("switch", "turn_off", {"entity_id": socket}, blocking=True)
    await _settle(hass)
    await hass.services.async_call("switch", "turn_on", {"entity_id": socket}, blocking=True)
    await _settle(hass)
    assert _sent(server, Rorg.BS4, switching.encode_dim(30), 0xFFB74482)  # restored 77 -> 30 %
    assert _sent(server, Rorg.BS4, switching.encode_dim(0, on=False), 0xFFB74482)
    # without the central sender a dimmer can only be switched by its rocker
    assert _sent(server, Rorg.RPS, b"\x70", 0xFFB74483, 0x30)
    assert _sent(server, Rorg.RPS, b"\x50", 0xFFB74483, 0x30)
    assert _sent(server, 0xD2, bytes.fromhex("010000"), 0xFFB74484)
    assert _sent(server, 0xD2, bytes.fromhex("010064"), 0xFFB74484)

    _push(server, 0x07, bytes.fromhex("02280009"), 0x05000002)  # dimmer reports 40 %
    _push(server, 0x05, b"\x50", 0x05000001, 0x30)  # switching actuator reports off
    _push(server, 0xD2, bytes.fromhex("040000"), 0x05000004)  # VLD over ESP2: socket off
    await _settle(hass)
    assert hass.states.get(dimmer).attributes["brightness"] == 102
    assert hass.states.get(_entity(hass, "light", uid("05-00-00-01", "light"))).state == "off"
    assert hass.states.get(socket).state == "off"


async def test_heating_cycle_and_silence_repair(hass: HomeAssistant, restored, monkeypatch) -> None:
    _entry, server = restored
    heater = _entity(hass, "climate", uid("05-00-00-06", "climate"))
    issue_id = f"climate_silent_{BASE}_05-00-00-06"
    assert _sent(server, Rorg.BS4, heating.encode_controller(0, 20.0), 0xFFB74486)  # off

    hass.states.async_set("sensor.raum", "not a number")  # ignored, last value stays
    await hass.services.async_call(
        "climate", "set_hvac_mode", {"entity_id": heater, "hvac_mode": "heat"}, blocking=True
    )
    await _settle(hass)
    assert _sent(server, Rorg.BS4, heating.encode_controller(19.5, 20.0), 0xFFB74486)

    # gateway gone: telegrams fail, after SILENCE_REPAIR a repair issue appears
    monkeypatch.setattr(climate, "SILENCE_REPAIR", 0)
    await server.stop()
    await _settle(hass)
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=61))
    await hass.async_block_till_done()
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is not None


def test_eltako_switching_telegrams() -> None:
    assert switching.decode_switch_status(b"\x70") == {"on": True}
    assert switching.decode_switch_status(b"\x50") == {"on": False}
    assert switching.decode_switch_status(b"\x30") is None
    assert switching.decode_switch_status(b"\x70\x00") is None
    assert switching.encode_switch_status(False) == b"\x50"
    assert switching.encode_switch(True, lock=True) == bytes.fromhex("0100000D")
    assert switching.decode_dim_status(bytes.fromhex("01000009")) == {"on": True}
    assert switching.decode_dim_status(bytes.fromhex("03000009")) is None
    assert switching.decode_dim_status(bytes.fromhex("02500000")) is None  # teach-in


@pytest.mark.parametrize(
    "gateway",
    [
        [
            _sub(
                "cover",
                "05-00-00-22",
                "Jalousie",
                [("controller", "FF-B7-44-91")],
                time_opens=20,
                time_closes=20,
                tilt_time=1.5,
            )
        ]
    ],
    indirect=True,
)
async def test_blind_tilt_and_stop(hass: HomeAssistant, gateway) -> None:  # noqa: F811
    from homeassistant.exceptions import HomeAssistantError

    from custom_components.enocean_eltako.protocol.eep.eltako import shutter

    _entry, server = gateway
    entity_id = _entity(hass, "cover", uid("05-00-00-22", "cover"))
    call = hass.services.async_call
    with pytest.raises(HomeAssistantError):  # position unknown before the first anchor
        await call("cover", "set_cover_position", {"entity_id": entity_id, "position": 40}, True)
    with pytest.raises(HomeAssistantError):
        await call(
            "cover", "set_cover_tilt_position", {"entity_id": entity_id, "tilt_position": 50}, True
        )

    _push(server, 0x05, b"\x70", 0x05000022, 0x30)  # upper end: slats open
    await _settle(hass)
    assert hass.states.get(entity_id).attributes["current_tilt_position"] == 100
    await call("cover", "close_cover_tilt", {"entity_id": entity_id}, blocking=True)
    await _settle(hass)
    turn = shutter.encode_command(shutter.DOWN, 1.5)
    assert _sent(server, Rorg.BS4, turn, 0xFFB74491)
    await call("cover", "stop_cover_tilt", {"entity_id": entity_id}, blocking=True)
    await _settle(hass)
    assert _sent(server, Rorg.BS4, shutter.encode_command(shutter.STOP), 0xFFB74491)
    await call("cover", "open_cover_tilt", {"entity_id": entity_id}, blocking=True)
    await _settle(hass)
