"""Entry setup and unload."""

import asyncio
from datetime import timedelta

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


async def test_sender_pool_is_persisted(hass: HomeAssistant, hass_storage) -> None:
    from homeassistant.util import dt as dt_util
    from pytest_homeassistant_custom_component.common import async_fire_time_changed

    server = await FakeGateway(Protocol.ESP2).start()
    entry = _entry(server.port)
    entry.add_to_hass(hass)
    hass_storage[f"{DOMAIN}.senders.{entry.entry_id}"] = {
        "version": 1,
        "key": f"{DOMAIN}.senders.{entry.entry_id}",
        "data": {"allocations": {"FF-B7-44-80": {"owner": "kept", "state": "assigned"}}},
    }
    assert await hass.config_entries.async_setup(entry.entry_id)
    senders = entry.runtime_data.senders
    assert senders.pool.allocate("cover") == 0xFFB74481
    senders.async_schedule_save()
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=10))
    await hass.async_block_till_done()
    saved = hass_storage[f"{DOMAIN}.senders.{entry.entry_id}"]["data"]["allocations"]
    assert saved["FF-B7-44-81"] == {"owner": "cover", "state": "assigned"}

    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert f"{DOMAIN}.senders.{entry.entry_id}" not in hass_storage
    await server.stop()


async def test_bus_group_with_on_demand_fam14(hass: HomeAssistant) -> None:
    from custom_components.enocean_eltako.protocol.send_queue import SendResult
    from custom_components.enocean_eltako.protocol.telegram import RadioTelegram, Rorg

    fgw = await FakeGateway(Protocol.ESP2).start()
    fam = await FakeGateway(Protocol.ESP2).start()
    e_fgw = MockConfigEntry(
        domain=DOMAIN,
        title="FGW14-USB",
        unique_id="FF-AA-80-00",
        data={
            "model": "fgw14_usb",
            "device": {"type": "tcp", "host": "127.0.0.1", "port": fgw.port},
            "base_id": "FF-AA-80-00",
            "bus_group": "b1",
        },
        options={"message_delay": 0, "mode": "always"},
    )
    e_fam = MockConfigEntry(
        domain=DOMAIN,
        title="FAM14",
        unique_id="FF-80-80-00",
        data={
            "model": "fam14",
            "device": {"type": "tcp", "host": "127.0.0.1", "port": fam.port},
            "base_id": "FF-80-80-00",
            "bus_group": "b1",
        },
        options={"message_delay": 0, "mode": "on_demand"},
    )
    e_fgw.add_to_hass(hass)
    e_fam.add_to_hass(hass)
    assert await hass.config_entries.async_setup(e_fgw.entry_id)  # sets up both entries
    await hass.async_block_till_done()
    assert not e_fam.runtime_data.gateway.connected  # on demand
    bus = e_fgw.runtime_data.bus
    assert bus is e_fam.runtime_data.bus
    assert len(bus.group) == 2
    assert bus.senders.pool.allocate("fsr14") == 0x0000B000

    command = RadioTelegram(Rorg.BS4, bytes.fromhex("01000009"), 0x0000B000)
    assert await bus.group.submit(command) == SendResult.SENT
    assert not e_fam.runtime_data.gateway.connected
    await fgw.stop()  # FGW14-USB fails
    await asyncio.sleep(0.1)
    assert await bus.group.submit(command) == SendResult.SENT
    assert e_fam.runtime_data.gateway.connected
    assert bus.group.failovers == 1

    hub = e_fgw.runtime_data.hub
    assert await hass.config_entries.async_unload(e_fam.entry_id)
    assert await hass.config_entries.async_unload(e_fgw.entry_id)
    assert hub.bus_groups == {}
    await fam.stop()
