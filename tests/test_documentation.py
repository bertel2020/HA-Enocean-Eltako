"""Installation documentation: the collector and its websocket command."""

import pytest
from homeassistant.core import HomeAssistant

from custom_components.enocean_eltako.documentation import VERSION, collect

from .test_devices import BASE, _push, _settle, _subentry, gateway  # noqa: F401

pytestmark = pytest.mark.usefixtures("socket_enabled")


@pytest.mark.parametrize(
    "gateway",
    [
        [
            _subentry(
                "switch",
                "05-10-A2-C1",
                "Licht Flur",
                senders=[
                    {"profile": "central", "sender_id": "FF-B7-44-91"},
                    {"profile": "rocker", "sender_id": "FF-B7-44-92"},
                ],
                rocker_on_button="a0",
                rocker_off_button="a1",
                wall_switch="05-10-AA-01",
                wall_on_button="a0",
                wall_off_button="a1",
            ),
            _subentry("meter", "05-00-00-12", "Waschmaschine"),
        ]
    ],
    indirect=True,
)
async def test_collect_describes_gateway_devices_senders_and_pool(
    hass: HomeAssistant,
    gateway,  # noqa: F811
    hass_ws_client,
) -> None:
    entry, server = gateway
    _push(server, 0x05, b"\x70", 0x00216343, 0x30)  # an unknown rocker
    await _settle(hass)
    entry.runtime_data.hub.notes[entry.entry_id].set_test("05-10-A2-C1", {"central": "confirmed"})
    pool = entry.runtime_data.senders.pool
    pool.assign(0xFFB74491, "device:05-10-A2-C1:central")
    pool.assign(0xFFB74495, "device:gone:central")
    pool.release(0xFFB74495)  # a deleted device: blocked until the teach-out is confirmed
    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "enocean_eltako/documentation"})
    reply = await client.receive_json()
    assert reply["success"]
    doc = reply["result"]
    assert doc == {**collect(hass), "generated": doc["generated"]}
    assert doc["version"] == VERSION

    (shown,) = doc["gateways"]
    assert shown["entry_id"] == entry.entry_id and shown["base_id"] == BASE
    assert shown["model"] == "fam_usb"
    names = [d["name"] for d in shown["devices"]]
    assert names == ["Licht Flur", "Waschmaschine"]

    flur_row, meter_row = shown["devices"]
    assert flur_row["id"] == "05-10-A2-C1" and flur_row["virtual"] is False
    assert flur_row["wall_switch"] == {"id": "05-10-AA-01", "on": "a0", "off": "a1"}
    senders = {s["profile"]: s for s in flur_row["senders"]}
    assert senders["central"]["id"] == "FF-B7-44-91"
    assert senders["central"]["test"] == "confirmed" and senders["rocker"]["test"] is None
    assert meter_row["senders"] == [] and meter_row["wall_switch"] is None
    assert meter_row["eep"] is not None

    (pool,) = shown["pools"]
    assert pool["kind"] == "radio" and pool["start"] == "FF-B7-44-81"
    owned = {s["id"]: s for s in pool["senders"]}
    assert owned["FF-B7-44-91"]["device"] == "Licht Flur"
    assert owned["FF-B7-44-91"]["state"] == "assigned"
    assert owned["FF-B7-44-95"] == {
        "id": "FF-B7-44-95",
        "device": None,
        "profile": "central",
        "state": "blocked",
    }
    assert flur_row["test_time"] is not None and meter_row["test_time"] is None
    assert shown["heard"] == [
        {"id": "00-21-63-43", "rorg": "F6", "dbm": None, "last": shown["heard"][0]["last"]}
    ]
    assert shown["hidden_senders"] == []


@pytest.mark.parametrize(
    "gateway",
    [[_subentry("meter", "05-00-00-12", "Waschmaschine")]],
    indirect=True,
)
async def test_notes_are_saved_shown_and_kept(
    hass: HomeAssistant,
    gateway,  # noqa: F811
    hass_ws_client,
    hass_storage,
) -> None:
    from homeassistant.helpers.storage import Store

    entry, _server = gateway
    device = next(iter(entry.runtime_data.devices.values()))
    client = await hass_ws_client(hass)

    async def call(msg_id: int, **fields):
        await client.send_json({"id": msg_id, "entry_id": entry.entry_id, **fields})
        return await client.receive_json()

    kind = "enocean_eltako/set_note"
    assert (await call(1, type=kind, text="Keller, rechts"))["success"]
    key = device.subentry.subentry_id
    assert (await call(2, type=kind, device=key, text="  Schrank 2, Platz 4  "))["success"]
    assert (await call(3, type=kind, device="nope", text="x"))["error"]["code"] == "unknown_device"
    assert (await call(4, type=kind, text="x", **{"entry_id": "unknown"}))["error"][
        "code"
    ] == "not_found"
    too_long = await call(5, type=kind, text="x" * 501)
    assert too_long["success"] is False

    (gateway_doc,) = collect(hass)["gateways"]
    assert gateway_doc["note"] == "Keller, rechts"
    assert gateway_doc["devices"][0]["note"] == "Schrank 2, Platz 4"
    details = await call(6, type="enocean_eltako/device_details", device=key)
    assert details["result"]["note"] == "Schrank 2, Platz 4"

    # unloading writes what waits for its delayed save; a reload reads it back
    await hass.config_entries.async_unload(entry.entry_id)
    stored = await Store(hass, 1, f"enocean_eltako.notes.{entry.entry_id}").async_load()
    assert stored == {
        "gateway": "Keller, rechts",
        "devices": {"05-00-00-12": "Schrank 2, Platz 4"},
        "tests": {},
        "manual": [],
    }
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    (again,) = collect(hass)["gateways"]
    assert again["note"] == "Keller, rechts"

    # an empty text removes a device's note
    device = next(iter(entry.runtime_data.devices.values()))
    entry.runtime_data.hub.notes[entry.entry_id].set_device("05-00-00-12", "")
    assert collect(hass)["gateways"][0]["devices"][0]["note"] == ""


async def test_manual_entries_are_validated_stored_and_documented(
    hass: HomeAssistant,
    gateway,  # noqa: F811
    hass_ws_client,
) -> None:
    entry, _server = gateway
    client = await hass_ws_client(hass)

    async def call(msg_id: int, entries, entry_id: str | None = None):
        await client.send_json(
            {
                "id": msg_id,
                "type": "enocean_eltako/set_manual",
                "entry_id": entry_id or entry.entry_id,
                "entries": entries,
            }
        )
        return await client.receive_json()

    entries = [
        {
            "id": "a1",
            "name": "  Taster Flur ",
            "address": "00-12-34-56",
            "function": "auf Licht Flur",
        },
        {"id": "b2", "name": "", "address": "", "function": ""},  # nothing written: dropped
        {"id": "c3", "name": "Sensor Garten"},
    ]
    assert (await call(1, entries))["success"]
    (gateway_doc,) = collect(hass)["gateways"]
    assert gateway_doc["manual"] == [
        {"id": "a1", "name": "Taster Flur", "address": "00-12-34-56", "function": "auf Licht Flur"},
        {"id": "c3", "name": "Sensor Garten", "address": "", "function": ""},
    ]

    assert (await call(2, entries, "unknown"))["error"]["code"] == "not_found"
    assert (await call(3, [{"id": "x", "name": "n" * 81}]))["success"] is False
    assert (await call(4, [{"id": "x"}] * 201))["success"] is False
    assert (await call(5, []))["success"]
    assert collect(hass)["gateways"][0]["manual"] == []

    await client.send_json({"id": 6, "type": "enocean_eltako/gateways"})
    assert (await client.receive_json())["success"]


@pytest.mark.parametrize(
    "gateway",
    [[_subentry("meter", "05-00-00-12", "Waschmaschine")]],
    indirect=True,
)
async def test_notes_of_deleted_devices_can_be_forgotten(
    hass: HomeAssistant,
    gateway,  # noqa: F811
    hass_ws_client,
) -> None:
    entry, _server = gateway
    notes = entry.runtime_data.hub.notes[entry.entry_id]
    notes.set_device("05-00-00-12", "bleibt")
    notes.set_device("05-00-00-99", "Gerät gelöscht")
    notes.set_test("05-00-00-98", {"central": "confirmed"})  # a result without a note
    client = await hass_ws_client(hass)

    async def call(msg_id: int, entry_id: str | None = None):
        await client.send_json(
            {
                "id": msg_id,
                "type": "enocean_eltako/prune_notes",
                "entry_id": entry_id or entry.entry_id,
            }
        )
        return await client.receive_json()

    await client.send_json({"id": 1, "type": "enocean_eltako/gateways"})
    status = await client.receive_json()
    assert status["result"][0]["orphan_notes"] == 2

    assert (await call(2, "unknown"))["error"]["code"] == "not_found"
    assert (await call(3))["result"] == {"removed": 1}
    assert notes.devices == {"05-00-00-12": "bleibt"} and notes.tests == {}
    assert (await call(4))["result"] == {"removed": 0}  # nothing left to forget


@pytest.mark.parametrize(
    "gateway",
    [[_subentry("meter", "05-00-00-12", "Waschmaschine")]],
    indirect=True,
)
async def test_notes_come_back_from_an_export(
    hass: HomeAssistant,
    gateway,  # noqa: F811
    hass_ws_client,
) -> None:
    entry, _server = gateway
    notes = entry.runtime_data.hub.notes[entry.entry_id]
    notes.set_gateway("Keller")
    notes.set_device("05-00-00-12", "Schrank 2")
    notes.set_manual([{"id": "a", "name": "Taster", "address": "00-12-34-56", "function": "Flur"}])
    export = collect(hass)

    # a new setup: nothing written yet
    notes.set_gateway("")
    notes.set_device("05-00-00-12", "")
    notes.set_manual([])
    client = await hass_ws_client(hass)

    async def call(msg_id: int, doc, **fields):
        await client.send_json(
            {"id": msg_id, "type": "enocean_eltako/import_documentation", "doc": doc, **fields}
        )
        return await client.receive_json()

    reply = await call(1, export)
    assert reply["result"]["gateways"] == [
        {"title": entry.title, "matched": True, "notes": 2, "manual": 1}
    ]
    assert notes.gateway == "Keller" and notes.devices == {"05-00-00-12": "Schrank 2"}
    assert [(e["name"], e["address"]) for e in notes.manual] == [("Taster", "00-12-34-56")]

    # the same file again changes nothing (no duplicates), and does not overwrite newer notes
    notes.set_device("05-00-00-12", "Schrank 3")
    again = await call(2, export)
    assert again["result"]["gateways"][0] | {"title": ""} == {
        "title": "",
        "matched": True,
        "notes": 0,
        "manual": 0,
    }
    assert notes.devices["05-00-00-12"] == "Schrank 3" and len(notes.manual) == 1
    assert (await call(3, export, overwrite=True))["success"]
    assert notes.devices["05-00-00-12"] == "Schrank 2"

    # a gateway of the file that is not set up here, and files that are not exports
    other = {**export, "gateways": [{**export["gateways"][0], "base_id": "FF-80-00-00"}]}
    assert (await call(4, other))["result"]["gateways"] == [
        {"title": entry.title, "matched": False}
    ]
    assert (await call(5, {"version": 99, "gateways": []}))["error"][
        "code"
    ] == "unsupported_version"
    assert (await call(6, {"version": 1, "gateways": "x"}))["error"][
        "code"
    ] == "unsupported_version"
    assert (await call(7, {"version": 1, "gateways": ["x"]}))["result"]["gateways"] == []
