"""Entities of the gateway device: connection, counters, sender IDs, reconnect."""

import asyncio

import pytest
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_component import async_update_entity

from custom_components.enocean_eltako.const import DOMAIN
from custom_components.enocean_eltako.protocol import esp2
from custom_components.enocean_eltako.protocol.models import Protocol

from .fake_gateway import FakeGateway
from .test_init import _entry

pytestmark = pytest.mark.usefixtures("socket_enabled")


def _entity_id(hass: HomeAssistant, domain: str, entry, key: str) -> str | None:
    return er.async_get(hass).async_get_entity_id(domain, DOMAIN, f"{entry.entry_id}_gateway_{key}")


@pytest.fixture
async def gateway(hass: HomeAssistant):
    server = await FakeGateway(Protocol.ESP2).start()
    entry = _entry(server.port)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await server.connected.wait()
    await hass.async_block_till_done()
    yield entry, server
    assert await hass.config_entries.async_unload(entry.entry_id)
    await server.stop()


async def test_gateway_device_names_its_manufacturer(hass: HomeAssistant, gateway) -> None:
    entry, _server = gateway
    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, entry.entry_id), entry.entry_id
    )
    assert device.manufacturer == "Eltako"
    assert device.model == "FAM-USB"


async def test_gateway_sensors(hass: HomeAssistant, gateway) -> None:
    entry, server = gateway
    connection = _entity_id(hass, "binary_sensor", entry, "connection")
    assert hass.states.get(connection).state == "on"
    telegrams = _entity_id(hass, "sensor", entry, "telegrams")
    assert hass.states.get(telegrams).state == "0"
    assert hass.states.get(_entity_id(hass, "sensor", entry, "base_id")).state == "FF-B7-44-80"
    assert hass.states.get(_entity_id(hass, "sensor", entry, "free_senders")).state == "127"
    assert _entity_id(hass, "sensor", entry, "polls_dropped") is None  # not a bus gateway

    server.push(esp2.Esp2Frame(esp2.HSeq.RRT, 0x05, bytes(4), 0x00216343, 0x30).encode())
    for _ in range(50):
        if entry.runtime_data.gateway.telegrams_received:
            break
        await asyncio.sleep(0.01)
    last = _entity_id(hass, "sensor", entry, "last_telegram")
    await async_update_entity(hass, telegrams)
    await async_update_entity(hass, last)
    assert hass.states.get(telegrams).state == "1"
    assert hass.states.get(last).state not in ("unknown", "unavailable")


async def test_gateway_address_and_byte_counters(hass: HomeAssistant, gateway) -> None:
    entry, server = gateway
    address = _entity_id(hass, "sensor", entry, "address")  # TCP gateways only
    assert hass.states.get(address).state == "127.0.0.1"
    gateway_runtime = entry.runtime_data.gateway
    assert _entity_id(hass, "sensor", entry, "bytes") is not None  # disabled by default
    seen = gateway_runtime.bytes_received  # the base ID answer

    server.push(bytes([0x55, 0, 1, 0, 0x17]))  # not a frame of ours: the decoder skips it
    server.push(esp2.Esp2Frame(esp2.HSeq.RRT, 0x05, bytes(4), 0x00216343, 0x30).encode())
    for _ in range(50):
        if gateway_runtime.telegrams_received:
            break
        await asyncio.sleep(0.01)
    assert gateway_runtime.bytes_received > seen
    assert gateway_runtime.ignored == {}


async def test_reconnect_button(hass: HomeAssistant, gateway) -> None:
    entry, server = gateway
    connection = _entity_id(hass, "binary_sensor", entry, "connection")
    seen: list[str] = []

    @callback
    def record(event: Event) -> None:
        if event.data["entity_id"] == connection:
            seen.append(event.data["new_state"].state)

    hass.bus.async_listen("state_changed", record)
    server.connected.clear()
    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": _entity_id(hass, "button", entry, "reconnect")},
        blocking=True,
    )
    await asyncio.wait_for(server.connected.wait(), 5)
    for _ in range(50):
        if entry.runtime_data.gateway.connected and seen[-1:] == ["on"]:
            break
        await asyncio.sleep(0.02)
    assert seen[0] == "off"
    assert hass.states.get(connection).state == "on"


async def test_renaming_the_entry_renames_the_gateway_device(hass: HomeAssistant, gateway) -> None:
    entry, server = gateway
    server.connected.clear()
    hass.config_entries.async_update_entry(entry, title="Funk Erdgeschoss")
    await hass.async_block_till_done()
    await asyncio.wait_for(server.connected.wait(), 5)
    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, entry.entry_id), entry.entry_id
    )
    assert device.name == "Funk Erdgeschoss"


async def test_repeater_level_is_written_on_connect(hass: HomeAssistant) -> None:
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.enocean_eltako.protocol import esp3

    server = await FakeGateway(Protocol.ESP3, base_id=0xFF8A1B00).start()
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="FF-8A-1B-00",
        data={
            "model": "mgw_eth",
            "device": {"type": "tcp", "host": "127.0.0.1", "port": server.port},
            "base_id": "FF-8A-1B-00",
        },
        options={"message_delay": 0, "repeater": "2"},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await server.connected.wait()
    for _ in range(50):
        if esp3.encode_repeater(2) in bytes(server.received):
            break
        await asyncio.sleep(0.02)
    assert esp3.encode_repeater(2) in bytes(server.received)
    assert await hass.config_entries.async_unload(entry.entry_id)
    await server.stop()


async def test_options_offer_repeater_only_for_esp3(hass: HomeAssistant, gateway) -> None:
    entry, _server = gateway  # FAM-USB, ESP2
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert "repeater" not in result["data_schema"].schema
