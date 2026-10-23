"""Telegram monitor in HA: websocket, capture service, diagnostics."""

import asyncio
import json
import time
from datetime import timedelta
from pathlib import Path

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.enocean_eltako.const import DOMAIN
from custom_components.enocean_eltako.diagnostics import async_get_config_entry_diagnostics
from custom_components.enocean_eltako.protocol import esp2
from custom_components.enocean_eltako.protocol.ids import parse_id
from custom_components.enocean_eltako.protocol.models import Protocol
from custom_components.enocean_eltako.protocol.sender_pool import SenderState
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
    assert first["event"]["history"] is True

    await entry.runtime_data.queue.submit(RadioTelegram(Rorg.RPS, b"\x30", 0xFFB74481, 0x30))
    live = await client.receive_json()
    assert live["event"]["dir"] == "tx"
    assert live["event"]["sender"] == "FF-B7-44-81"
    assert "history" not in live["event"]


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
    assert diag["sender_pool"]["start"] == "FF-B7-44-81"
    assert diag["telegrams"][-1]["sender"] == "00-21-63-43"
    assert diag["entry"]["data"]["device"]["host"] == "**REDACTED**"
    assert diag["gateway"]["connection"].startswith("**REDACTED**:")


async def test_websocket_describes_devices_and_teach_ins(hass: HomeAssistant, hass_ws_client):
    from homeassistant.config_entries import ConfigSubentryData

    from custom_components.enocean_eltako.protocol.eep.teach_in import encode_teach_in_4bs

    server = await FakeGateway(Protocol.ESP2).start()
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="FAM-USB Keller",
        unique_id="FF-B7-44-80",
        data={
            "model": "fam_usb",
            "device": {"type": "tcp", "host": "127.0.0.1", "port": server.port},
            "base_id": "FF-B7-44-80",
        },
        options={"message_delay": 0},
        subentries_data=[
            ConfigSubentryData(
                data={
                    "schema": 2,
                    "model": "switch",
                    "device_id": "05-10-A2-B3",
                    "senders": [{"profile": "central", "sender_id": "FF-B7-44-81"}],
                },
                subentry_type="device",
                title="Licht Diele",
                unique_id="05-10-A2-B3",
            ),
            ConfigSubentryData(
                data={"schema": 2, "model": "temp_humidity", "device_id": "01-82-0A-11"},
                subentry_type="device",
                title="Bad",
                unique_id="01-82-0A-11",
            ),
        ],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await server.connected.wait()
    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "enocean_eltako/telegrams/subscribe"})
    assert (await client.receive_json())["success"]

    server.push(
        esp2.Esp2Frame(esp2.HSeq.RRT, 0x05, bytes([0x70, 0, 0, 0]), 0x0510A2B3, 0x30).encode()
    )
    event = (await client.receive_json())["event"]
    assert event["gateway_name"] == "FAM-USB Keller"
    assert event["device"] == "Licht Diele"
    light = next(s for s in entry.subentries.values() if s.title == "Licht Diele")
    assert event["device_key"] == light.subentry_id
    from homeassistant.helpers import device_registry as dr

    page = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, "FF-B7-44-80_05-10-A2-B3"), entry.entry_id
    )
    assert page is not None and event["ha_device"] == page.id
    assert event["values"] == {"on": True, "channel": 1}
    assert "model" not in event  # the radio does not tell which of the FSRs it is
    assert event["models"] == ["FSR61", "FSR14", "FL62", "FSR71"]
    assert event["fields"] == [  # no sensors: the raw values
        {"label": "on", "value": True, "unit": None},
        {"label": "channel", "value": 1, "unit": None},
    ]

    climate = esp2.Esp2Frame(esp2.HSeq.RRT, 0x07, bytes.fromhex("007D7D08"), 0x01820A11)
    server.push(climate.encode())
    event = (await client.receive_json())["event"]
    assert event["fields"] == [
        {"label": "Temperature", "value": 20.0, "unit": "°C"},
        {"label": "Humidity", "value": 50.0, "unit": "%"},
    ]

    server.push(
        esp2.Esp2Frame(esp2.HSeq.RRT, 0x07, encode_teach_in_4bs("A5-02-05"), 0x01A0B0C0).encode()
    )
    event = (await client.receive_json())["event"]
    assert "device" not in event
    assert event["teach_in"] == "A5-02-05"

    # an unknown 1BS contact fits one profile; a 4BS data telegram fits too many to say
    server.push(
        esp2.Esp2Frame(esp2.HSeq.RRT, 0x06, bytes([0x09, 0, 0, 0]), 0x01A0B0C1, 0x00).encode()
    )
    event = (await client.receive_json())["event"]
    assert "device" not in event
    assert event["candidates"] == ["D5-00-01:std"]
    server.push(esp2.Esp2Frame(esp2.HSeq.RRT, 0x07, bytes.fromhex("00000009"), 0x01A0B0C2).encode())
    event = (await client.receive_json())["event"]
    assert "candidates" not in event and "teach_in" not in event

    await entry.runtime_data.queue.submit(RadioTelegram(Rorg.BS4, bytes(4), 0xFFB74481))
    event = (await client.receive_json())["event"]
    assert (event["dir"], event["device"], event["profile"]) == ("tx", "Licht Diele", "central")
    assert event["device_key"] == light.subentry_id  # the answer pairs with this command

    await client.send_json({"id": 2, "type": "enocean_eltako/gateways"})
    (status,) = (await client.receive_json())["result"]
    assert status["entry_id"] == entry.entry_id
    assert (status["title"], status["model"], status["base_id"]) == (
        "FAM-USB Keller",
        "Eltako FAM-USB",
        "FF-B7-44-80",
    )
    assert status["loaded"] and status["connected"]
    assert (status["telegrams"], status["devices"], status["queue"]) == (5, 2, 0)
    assert status["per_minute"] == 5
    await hass.config_entries.async_unload(entry.entry_id)
    await server.stop()


async def test_websocket_sends_only_from_a_device_sender(hass: HomeAssistant, hass_ws_client):
    from homeassistant.config_entries import ConfigSubentryData

    server = await FakeGateway(Protocol.ESP2).start()
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="FAM-USB",
        unique_id="FF-B7-44-80",
        data={
            "model": "fam_usb",
            "device": {"type": "tcp", "host": "127.0.0.1", "port": server.port},
            "base_id": "FF-B7-44-80",
        },
        options={"message_delay": 0},
        subentries_data=[
            ConfigSubentryData(
                data={
                    "schema": 2,
                    "model": "switch",
                    "device_id": "05-10-A2-B3",
                    "senders": [{"profile": "central", "sender_id": "FF-B7-44-81"}],
                },
                subentry_type="device",
                title="Licht Diele",
                unique_id="05-10-A2-B3",
            ),
        ],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await server.connected.wait()
    client = await hass_ws_client(hass)

    await client.send_json({"id": 1, "type": "enocean_eltako/gateways"})
    (status,) = (await client.receive_json())["result"]
    assert status["senders"] == [
        {"id": "FF-B7-44-81", "device": "Licht Diele", "profile": "central"}
    ]
    # the device page lists the type and the EEP it speaks
    from homeassistant.helpers import device_registry as dr

    registered = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, "FF-B7-44-80_05-10-A2-B3"), entry.entry_id
    )
    assert (
        registered is not None and registered.model == "M5-38-08"
    )  # several FSRs: the EEP is all we know, and it is not repeated as the model ID
    assert registered.model_id is None
    # configured devices for the panel's "not heard" list: nothing heard yet
    assert status["radio_devices"] == [
        {
            "id": "05-10-A2-B3",
            "device": "Licht Diele",
            "last_seen": None,
            "silent": False,
            "eep": "M5-38-08:eltako",
            "model": "",
            "models": ["FSR61", "FSR14", "FL62", "FSR71"],
            "category": "lighting",
            "area": None,
            "entities": 3,
            "ha_device": registered.id,
            "labels": [],
            "disabled": False,
            "key": next(iter(entry.subentries)),
            "teach": [{"profile": "central", "id": "FF-B7-44-81", "ute": False}],
        }
    ]
    # senders hidden from discovery: the panel does not offer them as new devices
    assert status["hidden"] == []
    assert abs(status["server_time"] - time.time()) < 5

    async def send(msg_id: int, **fields):
        base = {"type": "enocean_eltako/send", "entry_id": entry.entry_id, "rorg": "F6"}
        await client.send_json({"id": msg_id, **base, **fields})
        return await client.receive_json()

    ok = await send(2, sender="FF-B7-44-81", data="70", status="30")
    assert ok["success"] and ok["result"]["result"] == "sent"
    history = entry.runtime_data.hub.monitor.history(entry.entry_id)
    assert [(e.direction, e.telegram.sender, e.telegram.data) for e in history] == [
        ("tx", 0xFFB74481, b"\x70")
    ]

    # a free pool ID, a foreign ID, a wrong length and bad hex are refused
    for msg_id, fields, code in (
        (3, {"sender": "FF-B7-44-90", "data": "70"}, "invalid_sender"),
        (4, {"sender": "01-02-03-04", "data": "70"}, "invalid_sender"),
        (5, {"sender": "FF-B7-44-81", "data": "7000"}, "invalid_length"),
        (6, {"sender": "FF-B7-44-81", "data": "7"}, "invalid_format"),
    ):
        reply = await send(msg_id, **fields)
        assert not reply["success"] and reply["error"]["code"] == code
    assert len(entry.runtime_data.hub.monitor.history(entry.entry_id)) == 1

    # "teach in" from the panel: the device's teach-in telegram from its sender ID
    teach = {"type": "enocean_eltako/teach_in", "entry_id": entry.entry_id}
    await client.send_json(
        {"id": 7, **teach, "device": next(iter(entry.subentries)), "profile": "central"}
    )
    reply = await client.receive_json()
    assert reply["success"] and reply["result"] == {"ute": False, "window": 0}
    await hass.async_block_till_done()
    history = entry.runtime_data.hub.monitor.history(entry.entry_id)
    assert len(history) == 2 and history[-1].telegram.sender == 0xFFB74481
    for msg_id, fields, code in (
        (8, {"device": next(iter(entry.subentries)), "profile": "rocker"}, "unknown_sender"),
        (9, {"device": "nope", "profile": "central"}, "unknown_sender"),
        (10, {"entry_id": "nope", "device": "x", "profile": "central"}, "not_found"),
    ):
        await client.send_json({"id": msg_id, **teach, **fields})
        reply = await client.receive_json()
        assert not reply["success"] and reply["error"]["code"] == code
    entry.runtime_data.hub.hidden[entry.entry_id] = {0x0199887F}
    await client.send_json({"id": 100, "type": "enocean_eltako/gateways"})
    (status,) = (await client.receive_json())["result"]
    assert status["hidden"] == ["01-99-88-7F"]
    await hass.config_entries.async_unload(entry.entry_id)
    await server.stop()


async def test_websocket_lists_and_frees_sender_ids(hass: HomeAssistant, hass_ws_client):
    from homeassistant.config_entries import ConfigSubentryData

    server = await FakeGateway(Protocol.ESP2).start()
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="FAM-USB",
        unique_id="FF-B7-44-80",
        data={
            "model": "fam_usb",
            "device": {"type": "tcp", "host": "127.0.0.1", "port": server.port},
            "base_id": "FF-B7-44-80",
        },
        subentries_data=[
            ConfigSubentryData(
                data={
                    "schema": 2,
                    "model": "switch",
                    "device_id": "05-10-A2-B3",
                    "senders": [{"profile": "central", "sender_id": "FF-B7-44-81"}],
                },
                subentry_type="device",
                title="Licht Diele",
                unique_id="05-10-A2-B3",
            ),
        ],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await server.connected.wait()
    pool = entry.runtime_data.senders.pool
    pool.assign(0xFFB74481, "device:05-10-A2-B3:central")
    pool.assign(0xFFB74482, "device:gone:controller")
    pool.release(0xFFB74482)
    client = await hass_ws_client(hass)

    await client.send_json({"id": 1, "type": "enocean_eltako/sender_pools"})
    (result,) = (await client.receive_json())["result"]
    assert (result["id"], result["kind"], result["title"]) == (
        f"radio:{entry.entry_id}",
        "radio",
        "FAM-USB",
    )
    assert (result["start"], result["end"], result["size"]) == ("FF-B7-44-81", "FF-B7-44-FF", 127)
    assert result["free"] == 125
    assert result["first"] == 0xFFB74481
    assert result["next_free"] == "FF-B7-44-83"
    assert result["unavailable"] == []
    assert result["rows"] == [
        {
            "id": "FF-B7-44-81",
            "decimal": 0xFFB74481,
            "device": "Licht Diele",
            "ref": "05-10-A2-B3",
            "profile": "central",
            "state": "assigned",
        },
        {
            "id": "FF-B7-44-82",
            "decimal": 0xFFB74482,
            "device": None,
            "ref": "gone",
            "profile": "controller",
            "state": "blocked",
        },
    ]

    async def free(msg_id: int, sender: str, pool_id: str | None = None):
        await client.send_json(
            {
                "id": msg_id,
                "type": "enocean_eltako/sender_pools/free",
                "pool": pool_id or result["id"],
                "sender": sender,
            }
        )
        return await client.receive_json()

    # an assigned ID, an unused one, bad input and an unknown pool are refused
    for msg_id, sender, pool_id, code in (
        (2, "FF-B7-44-81", None, "not_blocked"),
        (3, "FF-B7-44-90", None, "not_blocked"),
        (4, "nope", None, "invalid_id"),
        (5, "FF-B7-44-82", "radio:unknown", "not_found"),
    ):
        reply = await free(msg_id, sender, pool_id)
        assert not reply["success"] and reply["error"]["code"] == code
    assert pool.get(0xFFB74482) is not None

    assert (await free(6, "FF-B7-44-82"))["success"]
    assert pool.get(0xFFB74482) is None and pool.get(0xFFB74481) is not None

    async def free_all(msg_id: int, **extra):
        await client.send_json(
            {
                "id": msg_id,
                "type": "enocean_eltako/sender_pools/free_all",
                "pool": result["id"],
                **extra,
            }
        )
        return await client.receive_json()

    # a listed assigned ID refuses the whole request, nothing is freed
    for sender in (0xFFB74483, 0xFFB74484):
        pool.assign(sender, f"device:gone{sender}:controller")
        pool.release(sender)
    reply = await free_all(7, senders=["FF-B7-44-83", "FF-B7-44-81"])
    assert not reply["success"] and reply["error"]["code"] == "not_blocked"
    assert pool.get(0xFFB74483) is not None
    reply = await free_all(8, senders=["nope"])
    assert not reply["success"] and reply["error"]["code"] == "invalid_id"
    # the listed ones only, then all that are left
    reply = await free_all(9, senders=["FF-B7-44-83"])
    assert reply["result"] == {"freed": 1}
    assert pool.get(0xFFB74483) is None and pool.get(0xFFB74484) is not None
    reply = await free_all(10)
    assert reply["result"] == {"freed": 1}
    assert pool.get(0xFFB74484) is None and pool.get(0xFFB74481) is not None
    reply = await free_all(11)
    assert reply["result"] == {"freed": 0}
    await hass.config_entries.async_unload(entry.entry_id)
    await server.stop()


async def test_panel_registered_with_frontend(hass: HomeAssistant):
    from unittest.mock import AsyncMock, MagicMock, patch

    from custom_components.enocean_eltako import panel

    hass.http = MagicMock(async_register_static_paths=AsyncMock())
    hass.config.components.add("frontend")
    with patch.object(panel.panel_custom, "async_register_panel", AsyncMock()) as register:
        await panel.async_register_panel(hass)
    kwargs = register.call_args.kwargs
    assert kwargs["frontend_url_path"] == "enocean-eltako"
    assert kwargs["require_admin"] is True
    assert kwargs["module_url"].startswith("/enocean_eltako_static/monitor-panel.js?v=")
    assert panel.PANEL_FILE.is_file()


async def test_websocket_device_details(hass: HomeAssistant, hass_ws_client) -> None:
    """The devices view opens a row: what is known of the device, as the panel shows it."""
    from homeassistant.config_entries import ConfigSubentryData

    server = await FakeGateway(Protocol.ESP2).start()
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="FAM-USB Keller",
        unique_id="FF-B7-44-80",
        data={
            "model": "fam_usb",
            "device": {"type": "tcp", "host": "127.0.0.1", "port": server.port},
            "base_id": "FF-B7-44-80",
        },
        options={"message_delay": 0},
        subentries_data=[
            ConfigSubentryData(
                data={
                    "schema": 4,
                    "model": "switch",
                    "device_id": "05-10-A2-B3",
                    "senders": [{"profile": "central", "sender_id": "FF-B7-44-81"}],
                    "platform": "light",
                    "invert": False,
                    "model_name": "FSR14-4x",
                },
                subentry_type="device",
                title="Licht Diele",
                unique_id="05-10-A2-B3",
            ),
        ],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await server.connected.wait()
    client = await hass_ws_client(hass)
    key = next(iter(entry.subentries))
    server.push(
        esp2.Esp2Frame(esp2.HSeq.RRT, 0x05, bytes([0x70, 0, 0, 0]), 0x0510A2B3, 0x30).encode()
    )
    await asyncio.sleep(0.05)
    await hass.async_block_till_done()

    await client.send_json(
        {
            "id": 1,
            "type": "enocean_eltako/device_details",
            "entry_id": entry.entry_id,
            "device": key,
        }
    )
    details = (await client.receive_json())["result"]
    assert details["key"] == key and details["gateway_name"] == "FAM-USB Keller"
    assert details["model"] == "FSR14-4x" and details["model_name"] == "FSR14-4x"
    assert "FSR14-2x" in details["models"]
    assert details["eep"] == "M5-38-08:eltako" and details["telegrams"] == 1
    assert details["senders"] == [{"profile": "central", "id": "FF-B7-44-81", "ute": False}]
    assert details["commands"]["sent"] == 0  # an actuator: statistics, none yet
    assert details["settings"] == {"platform": "light", "invert": False}  # identity left out
    assert {e["entity_id"].split(".")[0] for e in details["entities"]} >= {"light"}

    for msg_id, fields, code in (
        (2, {"entry_id": "nope", "device": key}, "not_found"),
        (3, {"entry_id": entry.entry_id, "device": "nope"}, "unknown_device"),
    ):
        await client.send_json({"id": msg_id, "type": "enocean_eltako/device_details", **fields})
        reply = await client.receive_json()
        assert not reply["success"] and reply["error"]["code"] == code
    await hass.config_entries.async_unload(entry.entry_id)
    await server.stop()


async def test_websocket_set_model(hass: HomeAssistant, hass_ws_client) -> None:
    """The devices view picks a device's model; empty clears it; a kind without models refuses."""
    from homeassistant.config_entries import ConfigSubentryData

    server = await FakeGateway(Protocol.ESP2).start()
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="FAM-USB Keller",
        unique_id="FF-B7-44-80",
        data={
            "model": "fam_usb",
            "device": {"type": "tcp", "host": "127.0.0.1", "port": server.port},
            "base_id": "FF-B7-44-80",
        },
        options={"message_delay": 0},
        subentries_data=[
            ConfigSubentryData(
                data={
                    "schema": 4,
                    "model": "switch",
                    "device_id": "05-10-A2-B3",
                    "senders": [{"profile": "central", "sender_id": "FF-B7-44-81"}],
                },
                subentry_type="device",
                title="Licht Diele",
                unique_id="05-10-A2-B3",
            ),
            ConfigSubentryData(
                data={"schema": 4, "model": "weather", "device_id": "FF-85-EF-81"},
                subentry_type="device",
                title="Wetter",
                unique_id="FF-85-EF-81",
            ),
            ConfigSubentryData(
                data={"schema": 4, "model": "co2", "device_id": "01-82-0A-11"},
                subentry_type="device",
                title="Bad",
                unique_id="01-82-0A-11",
            ),
        ],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await server.connected.wait()
    client = await hass_ws_client(hass)
    by_title = {s.title: sid for sid, s in entry.subentries.items()}

    async def call(msg_id: int, title: str, model_name: str, **extra):
        await client.send_json(
            {
                "id": msg_id,
                "type": "enocean_eltako/set_model",
                "entry_id": entry.entry_id,
                "device": by_title.get(title, title),
                "model_name": model_name,
                **extra,
            }
        )
        return await client.receive_json()

    reply = await call(1, "Licht Diele", " FSR14-4x ")
    assert reply["success"] and reply["result"] == {"model_name": "FSR14-4x"}
    await hass.async_block_till_done()
    assert entry.subentries[by_title["Licht Diele"]].data["model_name"] == "FSR14-4x"

    # the entry reloaded with the change; a pick not among the models is fine, empty clears it
    assert (await call(2, "Licht Diele", "FSR14-4x special"))["success"]
    await hass.async_block_till_done()
    assert entry.subentries[by_title["Licht Diele"]].data["model_name"] == "FSR14-4x special"
    assert (await call(3, "Licht Diele", ""))["result"] == {"model_name": ""}
    await hass.async_block_till_done()
    assert "model_name" not in entry.subentries[by_title["Licht Diele"]].data

    for msg_id, title, code in (
        (4, "Bad", "no_models"),
        (5, "nope", "unknown_device"),
    ):
        reply = await call(msg_id, title, "X")
        assert not reply["success"] and reply["error"]["code"] == code
    reply = await call(6, "Licht Diele", "x" * 65)
    assert not reply["success"] and reply["error"]["code"] == "invalid_format"
    await hass.config_entries.async_unload(entry.entry_id)
    await server.stop()


async def test_websocket_remove_devices(hass: HomeAssistant, hass_ws_client) -> None:
    """The devices view removes devices at once: one reload, their sender IDs stay blocked."""
    from homeassistant.config_entries import ConfigSubentryData

    server = await FakeGateway(Protocol.ESP2).start()
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="FAM-USB Keller",
        unique_id="FF-B7-44-80",
        data={
            "model": "fam_usb",
            "device": {"type": "tcp", "host": "127.0.0.1", "port": server.port},
            "base_id": "FF-B7-44-80",
        },
        options={"message_delay": 0},
        subentries_data=[
            ConfigSubentryData(
                data={
                    "schema": 4,
                    "model": "switch",
                    "device_id": "05-10-A2-B3",
                    "senders": [{"profile": "central", "sender_id": "FF-B7-44-81"}],
                },
                subentry_type="device",
                title="Licht Diele",
                unique_id="05-10-A2-B3",
            ),
            ConfigSubentryData(
                data={"schema": 4, "model": "weather", "device_id": "FF-85-EF-81"},
                subentry_type="device",
                title="Wetter",
                unique_id="FF-85-EF-81",
            ),
            ConfigSubentryData(
                data={"schema": 4, "model": "co2", "device_id": "01-82-0A-11"},
                subentry_type="device",
                title="Bad",
                unique_id="01-82-0A-11",
            ),
        ],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await server.connected.wait()
    client = await hass_ws_client(hass)
    by_title = {s.title: sid for sid, s in entry.subentries.items()}

    async def call(msg_id: int, devices: list[str], entry_id: str | None = None):
        await client.send_json(
            {
                "id": msg_id,
                "type": "enocean_eltako/remove_devices",
                "entry_id": entry_id or entry.entry_id,
                "devices": devices,
            }
        )
        return await client.receive_json()

    for msg_id, devices, entry_id, code in (
        (1, ["nope"], None, "unknown_device"),
        (2, [by_title["Bad"], "nope"], None, "unknown_device"),
        (3, [by_title["Bad"]], "nope", "not_found"),
    ):
        reply = await call(msg_id, devices, entry_id)
        assert not reply["success"] and reply["error"]["code"] == code
    assert len(entry.subentries) == 3  # a refused request removes nothing

    from custom_components.enocean_eltako.subentry_flow import sender_owner

    store = entry.runtime_data.senders
    store.pool.assign(parse_id("FF-B7-44-81"), sender_owner(parse_id("05-10-A2-B3"), "central"))
    await store.async_save()
    reply = await call(4, [by_title["Licht Diele"], by_title["Bad"], by_title["Bad"]])
    assert reply["success"] and reply["result"] == {"removed": 2}
    await hass.async_block_till_done()
    assert [s.title for s in entry.subentries.values()] == ["Wetter"]
    assert entry.state is ConfigEntryState.LOADED
    # the removed device's sender ID is blocked, not free, until its teach-out is confirmed
    pool = entry.runtime_data.senders.pool
    assert pool.get(parse_id("FF-B7-44-81")).state is SenderState.BLOCKED
    await hass.config_entries.async_unload(entry.entry_id)
    await server.stop()
