"""VLD actuators of other manufacturers: D2-01 switch/dimmer, D2-05 blind, UTE teach-in."""

import asyncio

import pytest
from homeassistant.config_entries import ConfigSubentryData
from homeassistant.core import HomeAssistant

from custom_components.enocean_eltako.protocol import esp3
from custom_components.enocean_eltako.protocol.dispatcher import DEDUP_WINDOW
from custom_components.enocean_eltako.protocol.eep.ute import (
    decode_ute_request,
    encode_ute_request,
    encode_ute_response,
)
from custom_components.enocean_eltako.protocol.telegram import RadioTelegram, Rorg
from custom_components.enocean_eltako.subentry_flow import candidates

from .test_devices import _entity, _settle, esp3_gateway  # noqa: F401

pytestmark = pytest.mark.usefixtures("socket_enabled")

SWITCH, BLIND = 0x05AA0001, 0x05AA0002
SWITCH_SENDER, BLIND_SENDER = 0xFF8A1B10, 0xFF8A1B11
PREFIX = "FF-8A-1B-00"


def _vld(model: str, device: str, sender: str, title: str, **options) -> ConfigSubentryData:
    return ConfigSubentryData(
        data={
            "schema": 2,
            "model": model,
            "device_id": device,
            "senders": [{"profile": "vld", "sender_id": sender}],
            **options,
        },
        subentry_type="device",
        title=title,
        unique_id=device,
    )


DEVICES = [
    _vld("vld_switch", "05-AA-00-01", "FF-8A-1B-10", "Licht NodOn", channel=1),
    _vld("vld_cover", "05-AA-00-02", "FF-8A-1B-11", "Rollo NodOn", channel=0),
]


def _sent(server, rorg: int, data: str, sender: int, destination: int | None = None) -> bool:
    telegram = RadioTelegram(rorg, bytes.fromhex(data), sender)
    if destination is not None:
        telegram = RadioTelegram(rorg, bytes.fromhex(data), sender, 0, destination)
    return esp3.encode_radio(telegram) in bytes(server.received)


@pytest.mark.parametrize("esp3_gateway", [DEVICES], indirect=True)
async def test_vld_switch_and_blind(hass: HomeAssistant, esp3_gateway) -> None:  # noqa: F811
    _entry, server = esp3_gateway
    light = _entity(hass, "light", f"{PREFIX}_05-AA-00-01_1_light")
    cover = _entity(hass, "cover", f"{PREFIX}_05-AA-00-02_1_cover")

    server.push(esp3.encode_radio(RadioTelegram(0xD2, bytes.fromhex("040132"), SWITCH)))
    server.push(esp3.encode_radio(RadioTelegram(0xD2, bytes.fromhex("040064"), SWITCH)))
    server.push(esp3.encode_radio(RadioTelegram(0xD2, bytes.fromhex("1E7F0004"), BLIND)))
    await _settle(hass)
    state = hass.states.get(light)
    assert state.state == "on"
    assert state.attributes["brightness"] == 128  # 50 % on channel 1; channel 0 ignored
    assert hass.states.get(cover).attributes["current_position"] == 70  # 30 % closed

    await hass.services.async_call("light", "turn_off", {"entity_id": light}, blocking=True)
    await hass.services.async_call(
        "cover", "set_cover_position", {"entity_id": cover, "position": 25}, blocking=True
    )
    await _settle(hass)  # a stop right away would replace the waiting position command
    await hass.services.async_call("cover", "stop_cover", {"entity_id": cover}, blocking=True)
    await _settle(hass)
    assert _sent(server, 0xD2, "010100", SWITCH_SENDER)  # channel 1 to 0 %
    assert _sent(server, 0xD2, "4B7F0001", BLIND_SENDER)  # 75 % closed
    assert _sent(server, 0xD2, "02", BLIND_SENDER)


@pytest.mark.parametrize("esp3_gateway", [DEVICES], indirect=True)
async def test_ute_teach_in_is_answered_while_armed(hass: HomeAssistant, esp3_gateway) -> None:  # noqa: F811
    _entry, server = esp3_gateway
    query = encode_ute_request("D2-01-12", 0x046)
    answer = encode_ute_response(decode_ute_request(query)).hex()

    server.push(esp3.encode_radio(RadioTelegram(Rorg.UTE, query, SWITCH)))
    await _settle(hass)
    assert not _sent(server, Rorg.UTE, answer, SWITCH_SENDER, SWITCH)  # not armed

    await asyncio.sleep(DEDUP_WINDOW)  # the same query again is no repetition
    button = _entity(hass, "button", f"{PREFIX}_05-AA-00-01_1_teach_in_vld")
    await hass.services.async_call("button", "press", {"entity_id": button}, blocking=True)
    server.push(esp3.encode_radio(RadioTelegram(Rorg.UTE, query, SWITCH)))
    await _settle(hass)
    assert _sent(server, Rorg.UTE, answer, SWITCH_SENDER, SWITCH)  # addressed to the actuator


def test_ute_query_suggests_the_vld_kind() -> None:
    assert candidates(Rorg.UTE, None, encode_ute_request("D2-01-12")) == ["psc", "vld_switch"]
    assert candidates(Rorg.UTE, None, encode_ute_request("D2-05-00")) == ["vld_cover"]
