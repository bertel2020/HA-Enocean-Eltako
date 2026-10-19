"""Telegram monitor in HA: websocket, capture service, diagnostics."""

import asyncio
import json
from datetime import timedelta
from pathlib import Path

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.enocean_eltako.const import DOMAIN
from custom_components.enocean_eltako.diagnostics import async_get_config_entry_diagnostics
from custom_components.enocean_eltako.protocol import esp2
from custom_components.enocean_eltako.protocol.models import Protocol
from custom_components.enocean_eltako.protocol.telegram import RadioTelegram, Rorg

from .fake_gateway import FakeGateway

pytestmark = pytest.mark.usefixtures("socket_enabled")

SWITCH = esp2.Esp2Frame(esp2.HSeq.RRT, 0x05, bytes([0x70, 0, 0, 0]), 0x00216343, 0x30).encode()


@pytest.fixture
async def setup(hass: HomeAssistant):
    server = await FakeGateway(Protocol.ESP2).start()
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Eltako FAM-USB FF-B7-44-80",
        unique_id="FF-B7-44-80",
        data={
            "model": "fam_usb",
            "device": {"type": "tcp", "host": "127.0.0.1", "port": server.port},
            "base_id": "FF-B7-44-80",
        },
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await server.connected.wait()
    yield entry, server
    await hass.config_entries.async_unload(entry.entry_id)
    await server.stop()


async def _until(predicate) -> None:
    for _ in range(100):
        if predicate():
            return
        await asyncio.sleep(0.01)
    raise AssertionError("condition not met")


async def test_websocket_streams_history_and_live(hass: HomeAssistant, setup, hass_ws_client):
    entry, server = setup
    monitor = entry.runtime_data.hub.monitor
    server.push(SWITCH)
    await _until(lambda: monitor.history(entry.entry_id))

    client = await hass_ws_client(hass)
    await client.send_json(
        {
            "id": 1,
            "type": "enocean_eltako/telegrams/subscribe",
            "entry_id": entry.entry_id,
            "history": 10,
        }
    )
    assert (await client.receive_json())["success"]
    first = await client.receive_json()
    assert first["event"]["sender"] == "00-21-63-43"
    assert first["event"]["dir"] == "rx"

    await entry.runtime_data.queue.submit(RadioTelegram(Rorg.RPS, b"\x30", 0xFFB74481, 0x30))
    live = await client.receive_json()
    assert live["event"]["dir"] == "tx"
    assert live["event"]["sender"] == "FF-B7-44-81"


async def test_capture_writes_jsonl(hass: HomeAssistant, setup, tmp_path: Path):
    entry, server = setup
    hass.config.config_dir = str(tmp_path)
    response = await hass.services.async_call(
        DOMAIN, "capture", {"duration": 5}, blocking=True, return_response=True
    )
    server.push(SWITCH)
    await _until(lambda: entry.runtime_data.hub.monitor.history(entry.entry_id))
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=6))
    await hass.async_block_till_done()
    lines = Path(response["path"]).read_text().splitlines()
    assert Path(response["path"]).parent == tmp_path / DOMAIN
    assert json.loads(lines[0])["data"] == "70"


async def test_diagnostics(hass: HomeAssistant, setup):
    entry, server = setup
    server.push(SWITCH)
    await _until(lambda: entry.runtime_data.gateway.telegrams_received)
    diag = await async_get_config_entry_diagnostics(hass, entry)
    assert diag["gateway"]["connected"] is True
    assert diag["gateway"]["telegrams_received"] == 1
    assert diag["dispatcher"]["received"] >= 1
    assert diag["send_queue"]["length"] == 0
    assert diag["sender_pool"]["start"] == "FF-B7-44-80"
    assert diag["telegrams"][-1]["sender"] == "00-21-63-43"
