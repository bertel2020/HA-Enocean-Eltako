"""Entry setup and unload."""

import asyncio

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.enocean_eltako.const import DOMAIN
from custom_components.enocean_eltako.protocol.models import Protocol

from .fake_gateway import FakeGateway

pytestmark = pytest.mark.usefixtures("socket_enabled")


def _entry(port: int) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id="FF-B7-44-80",
        data={
            "model": "fam_usb",
            "device": {"type": "tcp", "host": "127.0.0.1", "port": port},
            "base_id": "FF-B7-44-80",
        },
    )


async def test_setup_and_unload(hass: HomeAssistant) -> None:
    server = await FakeGateway(Protocol.ESP2).start()
    entry = _entry(server.port)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    gateway = entry.runtime_data.gateway
    assert gateway.connected
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED
    assert not gateway.connected
    await server.stop()


async def test_setup_retries_when_gateway_is_offline(hass: HomeAssistant) -> None:
    server = await FakeGateway(Protocol.ESP2).start()
    port = server.port
    await server.stop()
    entry = _entry(port)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_usb_integration_attributes_serial_port(hass: HomeAssistant) -> None:
    """HA's usb integration shows which entry uses a port; it looks at ("device", "path")."""
    from homeassistant.components.usb.consumers import _async_get_config_entry_consumers

    path = "/dev/serial/by-id/usb-EnOcean_FAM-USB"
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Eltako FAM-USB FF-B7-44-80",
        data={
            "model": "fam_usb",
            "device": {"type": "serial", "path": path, "baudrate": 9600},
            "base_id": "FF-B7-44-80",
        },
    )
    entry.add_to_hass(hass)
    consumers = await _async_get_config_entry_consumers(hass, set())
    assert [c.config_entry_id for c in consumers[path]] == [entry.entry_id]


async def test_received_telegrams_reach_the_dispatcher(hass: HomeAssistant) -> None:
    from custom_components.enocean_eltako.protocol import esp2
    from custom_components.enocean_eltako.protocol.telegram import RadioTelegram, Rorg

    server = await FakeGateway(Protocol.ESP2).start()
    entry = _entry(server.port)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await server.connected.wait()
    got = []
    entry.runtime_data.hub.dispatcher.add_listener(0x00216343, got.append)
    server.push(
        esp2.Esp2Frame(esp2.HSeq.RRT, 0x05, bytes([0x70, 0, 0, 0]), 0x00216343, 0x30).encode()
    )
    for _ in range(50):
        if got:
            break
        await asyncio.sleep(0.01)
    assert got[0].telegram == RadioTelegram(Rorg.RPS, b"\x70", 0x00216343, 0x30)
    assert got[0].gateway == entry.entry_id
    assert await hass.config_entries.async_unload(entry.entry_id)
    await server.stop()


async def test_send_queue_writes_to_the_gateway(hass: HomeAssistant) -> None:
    from custom_components.enocean_eltako.protocol import esp2
    from custom_components.enocean_eltako.protocol.send_queue import SendResult
    from custom_components.enocean_eltako.protocol.telegram import RadioTelegram, Rorg

    server = await FakeGateway(Protocol.ESP2).start()
    entry = _entry(server.port)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await server.connected.wait()
    telegram = RadioTelegram(Rorg.RPS, b"\x30", 0xFFB74481, 0x30)
    assert await entry.runtime_data.queue.submit(telegram) == SendResult.SENT
    await asyncio.sleep(0.05)
    assert bytes(server.received).endswith(esp2.encode_radio(telegram))
    assert await hass.config_entries.async_unload(entry.entry_id)
    await server.stop()
