"""Installation documentation: the collector and its websocket command."""

import pytest
from homeassistant.core import HomeAssistant

from custom_components.enocean_eltako.documentation import VERSION, collect
from custom_components.enocean_eltako.notes import MANUAL_FIELDS

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
    assert shown["model"] == "fam_usb" and shown["model_name"] == "Eltako FAM-USB"
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
    assert owned["FF-B7-44-91"]["ref"] == flur_row["note_key"]
    assert owned["FF-B7-44-95"] == {
        "id": "FF-B7-44-95",
        "device": None,
        "ref": "gone",
        "profile": "central",
        "state": "blocked",
    }
    assert flur_row["test_time"] is not None and meter_row["test_time"] is None
    assert shown["heard"] == [
        {"id": "00-21-63-43", "rorg": "F6", "dbm": None, "last": shown["heard"][0]["last"]}
    ]
    assert shown["hidden_senders"] == []


async def test_version_4_manual_entries_get_the_fields_of_version_5(
    hass: HomeAssistant,
    hass_storage,
    gateway,  # noqa: F811
) -> None:
    entry, _server = gateway
    await hass.config_entries.async_unload(entry.entry_id)
    hass_storage[f"enocean_eltako.notes.{entry.entry_id}"] = {
        "version": 4,
        "key": f"enocean_eltako.notes.{entry.entry_id}",
        "data": {
            "gateway": "",
            "devices": {},
            "manual": [
                {"id": "a", "name": "Taster Flur", "address": "00-12-34-56", "function": "Flur"}
            ],
        },
    }
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    notes = entry.runtime_data.hub.notes[entry.entry_id]
    (manual,) = notes.manual
    assert (manual["name"], manual["address"], manual["function"]) == (
        "Taster Flur",
        "00-12-34-56",
        "Flur",
    )
    assert [manual[k] for k in ("kind", "location", "power")] == ["", "", ""]
    await notes.async_flush()
    assert hass_storage[f"enocean_eltako.notes.{entry.entry_id}"]["version"] == 9


async def test_version_5_manual_entries_get_the_fields_of_version_6(
    hass: HomeAssistant,
    hass_storage,
    gateway,  # noqa: F811
) -> None:
    entry, _server = gateway
    await hass.config_entries.async_unload(entry.entry_id)
    hass_storage[f"enocean_eltako.notes.{entry.entry_id}"] = {
        "version": 5,
        "key": f"enocean_eltako.notes.{entry.entry_id}",
        "data": {
            "gateway": "",
            "devices": {},
            "manual": [
                {
                    **{
                        k: ""
                        for k in MANUAL_FIELDS
                        if k not in ("circuit", "fuse", "installed", "model")
                    },
                    "id": "a",
                    "name": "Taster Flur",
                    "address": "00-12-34-56",
                    "location": "Flur",
                }
            ],
        },
    }
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    notes = entry.runtime_data.hub.notes[entry.entry_id]
    (manual,) = notes.manual
    assert (manual["name"], manual["location"]) == ("Taster Flur", "Flur")
    assert [manual[k] for k in ("circuit", "fuse", "installed", "model")] == ["", "", "", ""]
    notes.set_manual(
        [{**manual, "circuit": "3", "fuse": "B16", "installed": "gestern", "model": "PTM 215"}]
    )
    assert (notes.manual[0]["circuit"], notes.manual[0]["fuse"], notes.manual[0]["model"]) == (
        "3",
        "B16",
        "PTM 215",
    )
    assert notes.manual[0]["installed"] == ""  # not a date
    await notes.async_flush()
    assert hass_storage[f"enocean_eltako.notes.{entry.entry_id}"]["version"] == 9


async def test_import_matches_manual_entries_by_address(
    hass: HomeAssistant,
    gateway,  # noqa: F811
) -> None:
    entry, _server = gateway
    notes = entry.runtime_data.hub.notes[entry.entry_id]
    notes.set_manual([{"id": "a", "name": "", "address": "00-12-34-56"}])
    taken = notes.import_from(
        {"manual": [{"name": "Taster Flur", "address": "00-12-34-56"}]}, overwrite=False
    )
    assert taken[1] == 0  # the same address: the same entry, even when it was named since
    assert len(notes.manual) == 1


async def test_a_manual_entry_keeps_its_kind_place_and_power(
    hass: HomeAssistant,
    gateway,  # noqa: F811
    hass_ws_client,
) -> None:
    entry, _server = gateway
    notes = entry.runtime_data.hub.notes[entry.entry_id]
    client = await hass_ws_client(hass)
    ids = iter(range(1, 10))

    async def call(entries):
        await client.send_json(
            {
                "id": next(ids),
                "type": "enocean_eltako/set_manual",
                "entry_id": entry.entry_id,
                "entries": entries,
            }
        )
        return await client.receive_json()

    sensor = {
        "id": "a",
        "name": "Fensterkontakt Bad",
        "address": "05-A3-C4-E1",
        "kind": "sensor",
        "location": "Bad",
        "power": "Solar",
    }
    assert (await call([sensor]))["success"]
    assert {k: notes.manual[0][k] for k in sensor} == sensor
    # a kind that is none counts as a button
    assert (await call([{**sensor, "kind": "lamp"}]))["success"]
    assert notes.manual[0]["kind"] == ""
    # an export brings the kind, place and power back
    assert (await call([sensor]))["success"]
    export = collect(hass)
    notes.set_manual([])
    await client.send_json(
        {"id": next(ids), "type": "enocean_eltako/import_documentation", "doc": export}
    )
    assert (await client.receive_json())["success"]
    assert {k: notes.manual[0][k] for k in ("kind", "location", "power")} == {
        "kind": "sensor",
        "location": "Bad",
        "power": "Solar",
    }


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
    stored = await Store(hass, 9, f"enocean_eltako.notes.{entry.entry_id}").async_load()
    assert stored == {
        "gateway": "Keller, rechts",
        "supplies": [],
        "devices": {"05-00-00-12": {"note": "Schrank 2, Platz 4"}},
        "tests": {},
        "manual": [],
        "log": [],
        "known": {"05-00-00-12": {"name": "Waschmaschine", "senders": []}},
        "links": [],
        "link_info": {},
        "signal": {},
        "heard": {},
        "last": {},
        "migrated_to_installation": True,
        "places_synced": True,
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
    no_bus = {
        "bus_address": "",
        "feedback_id": "",
        "bus_power": "",
        "kind": "",
        "location": "",
        "power": "",
        "circuit": "",
        "fuse": "",
        "installed": "",
        "model": "",
        "bus_power_table": None,
    }
    assert gateway_doc["manual"] == [
        {
            "id": "a1",
            "name": "Taster Flur",
            "address": "00-12-34-56",
            "function": "auf Licht Flur",
            **no_bus,
        },
        {"id": "c3", "name": "Sensor Garten", "address": "", "function": "", **no_bus},
    ]

    assert (await call(2, entries, "unknown"))["error"]["code"] == "not_found"
    assert (await call(3, [{"id": "x", "name": "n" * 81}]))["success"] is False
    assert (await call(4, [{"id": "x"}] * 201))["success"] is False
    assert (await call(5, []))["success"]
    assert collect(hass)["gateways"][0]["manual"] == []

    await client.send_json({"id": 6, "type": "enocean_eltako/gateways"})
    assert (await client.receive_json())["success"]

    # a device of the Eltako bus that Home Assistant does not hold
    bus = {"id": "f3", "name": "FSR14-4x", "bus_address": "12", "bus_power": "0,5"}
    assert (await call(7, [bus]))["success"]
    (manual,) = collect(hass)["gateways"][0]["manual"]
    assert manual["bus_address"] == "12" and manual["bus_power"] == "0,5"
    assert manual["bus_power_table"] == 0.7  # the type is in the planning guide
    assert (await call(8, [{**bus, "bus_power": "viel", "bus_address": "127"}]))["success"]
    (manual,) = collect(hass)["gateways"][0]["manual"]
    assert manual["bus_power"] == "" and manual["bus_address"] == ""  # not watts, not an address


async def test_the_bus_power_supplies_are_validated_stored_and_documented(
    hass: HomeAssistant,
    gateway,  # noqa: F811
    hass_ws_client,
) -> None:
    entry, _server = gateway
    notes = entry.runtime_data.hub.notes[entry.entry_id]
    client = await hass_ws_client(hass)

    async def call(msg_id: int, supplies, entry_id: str | None = None):
        await client.send_json(
            {
                "id": msg_id,
                "type": "enocean_eltako/set_supplies",
                "entry_id": entry_id or entry.entry_id,
                "supplies": supplies,
            }
        )
        return await client.receive_json()

    two = [
        {"id": "a", "name": " FSNT14-12V ", "watts": "12", "first": "1", "last": "40"},
        {"name": "FSNT14-12V", "watts": "1,5", "first": "41", "last": "126"},
        {"id": "empty"},  # nothing written: dropped
    ]
    assert (await call(1, two))["success"]
    (shown,) = collect(hass)["gateways"]
    assert [(s["name"], s["watts"], s["first"], s["last"]) for s in shown["supplies"]] == [
        ("FSNT14-12V", "12", "1", "40"),
        ("FSNT14-12V", "1,5", "41", "126"),
    ]
    assert shown["supplies"][0]["id"] == "a" and shown["supplies"][1]["id"]  # a new one gets an ID
    # the whole list is replaced, a bad value changes nothing
    for bad in (
        {"watts": "viel"},
        {"watts": "1", "first": "0"},
        {"watts": "1", "first": "127"},
        {"watts": "1", "first": "50", "last": "40"},
        {"name": "n" * 61},
    ):
        reply = await call(2, [bad])
        assert reply["success"] is False or reply["error"]["code"] == "invalid_format"
        assert len(notes.supplies) == 2
    assert (await call(3, [], "unknown"))["error"]["code"] == "not_found"
    assert (await call(4, [{"watts": "12"}] * 9))["success"] is False  # too many
    assert (await call(5, []))["success"] and notes.supplies == []

    # an export brings the list back; one of version 2 had a single supply
    doc = {
        "version": 2,
        "gateways": [
            {
                "base_id": entry.data["base_id"],
                "supplies": two[:1],
                "devices": [{"note_key": "05-00-00-12", "bus_power": "viel"}],
            }
        ],
    }
    await client.send_json({"id": 7, "type": "enocean_eltako/import_documentation", "doc": doc})
    assert (await client.receive_json())["success"]
    assert [s["watts"] for s in notes.supplies] == ["12"]
    assert notes.device("05-00-00-12")["bus_power"] == ""  # a bad power is dropped
    old = {"base_id": entry.data["base_id"], "supply": {"name": "FSNT14", "watts": "30"}}
    await client.send_json(
        {
            "id": 8,
            "type": "enocean_eltako/import_documentation",
            "doc": {"version": 2, "gateways": [old]},
            "overwrite": True,
        }
    )
    assert (await client.receive_json())["success"]
    assert [(s["name"], s["watts"]) for s in notes.supplies] == [("FSNT14", "30")]


async def test_version_2_notes_with_one_supply_are_migrated(
    hass: HomeAssistant,
    hass_storage,
    gateway,  # noqa: F811
) -> None:
    entry, _server = gateway
    await hass.config_entries.async_unload(entry.entry_id)
    hass_storage[f"enocean_eltako.notes.{entry.entry_id}"] = {
        "version": 2,
        "key": f"enocean_eltako.notes.{entry.entry_id}",
        "data": {"gateway": "", "devices": {}, "supply": {"name": "FSNT14-12V", "watts": "12"}},
    }
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    notes = entry.runtime_data.hub.notes[entry.entry_id]
    assert [(s["name"], s["watts"], s["first"], s["last"]) for s in notes.supplies] == [
        ("FSNT14-12V", "12", "", "")
    ]
    assert notes.supplies[0]["id"]
    # version 4: the supply has a place, circuit, fuse and note too, empty until written down
    assert [notes.supplies[0][k] for k in ("location", "circuit", "fuse", "note")] == [
        "",
        "",
        "",
        "",
    ]


async def test_version_3_supplies_get_the_fields_of_version_4(
    hass: HomeAssistant,
    hass_storage,
    gateway,  # noqa: F811
) -> None:
    entry, _server = gateway
    await hass.config_entries.async_unload(entry.entry_id)
    hass_storage[f"enocean_eltako.notes.{entry.entry_id}"] = {
        "version": 3,
        "key": f"enocean_eltako.notes.{entry.entry_id}",
        "data": {
            "gateway": "",
            "devices": {},
            "supplies": [
                {"id": "s1", "name": "FSNT14-12V", "watts": "24", "first": "1", "last": "20"}
            ],
        },
    }
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    notes = entry.runtime_data.hub.notes[entry.entry_id]
    (supply,) = notes.supplies
    assert (supply["id"], supply["name"], supply["watts"], supply["first"], supply["last"]) == (
        "s1",
        "FSNT14-12V",
        "24",
        "1",
        "20",
    )
    assert [supply[k] for k in ("location", "circuit", "fuse", "note")] == ["", "", "", ""]
    await notes.async_flush()
    assert hass_storage[f"enocean_eltako.notes.{entry.entry_id}"]["version"] == 9


async def test_a_supply_keeps_its_place_circuit_fuse_and_note(
    hass: HomeAssistant,
    gateway,  # noqa: F811
    hass_ws_client,
) -> None:
    entry, _server = gateway
    notes = entry.runtime_data.hub.notes[entry.entry_id]
    client = await hass_ws_client(hass)

    ids = iter(range(1, 10))

    async def call(supplies):
        await client.send_json(
            {
                "id": next(ids),
                "type": "enocean_eltako/set_supplies",
                "entry_id": entry.entry_id,
                "supplies": supplies,
            }
        )
        return await client.receive_json()

    placed = {
        "id": "a",
        "name": "FSNT14-12V",
        "watts": "24",
        "location": "Schrank 1 · Reihe 1 · 1",
        "circuit": "K1",
        "fuse": "B10",
        "note": "neben dem FAM14",
    }
    assert (await call([placed]))["success"]
    (shown,) = collect(hass)["gateways"]
    assert {k: shown["supplies"][0][k] for k in placed} == placed
    # an entry with only a place is not empty; one too long changes nothing
    assert (await call([{"location": "Schrank 2"}]))["success"]
    assert [s["location"] for s in notes.supplies] == ["Schrank 2"]
    reply = await call([{"location": "x" * 121}])
    assert reply["success"] is False or reply["error"]["code"] == "invalid_format"
    assert [s["location"] for s in notes.supplies] == ["Schrank 2"]


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
    assert notes.devices == {"05-00-00-12": {"note": "bleibt"}} and notes.tests == {}
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
        {"title": entry.title, "matched": True, "notes": 2, "manual": 1, "links": 0}
    ]
    assert notes.gateway == "Keller" and notes.devices == {"05-00-00-12": {"note": "Schrank 2"}}
    assert [(e["name"], e["address"]) for e in notes.manual] == [("Taster", "00-12-34-56")]

    # the same file again changes nothing (no duplicates), and does not overwrite newer notes
    notes.set_device("05-00-00-12", "Schrank 3")
    again = await call(2, export)
    assert again["result"]["gateways"][0] | {"title": ""} == {
        "title": "",
        "matched": True,
        "notes": 0,
        "manual": 0,
        "links": 0,
    }
    assert notes.devices["05-00-00-12"] == {"note": "Schrank 3"} and len(notes.manual) == 1
    assert (await call(3, export, overwrite=True))["success"]
    assert notes.devices["05-00-00-12"] == {"note": "Schrank 2"}

    # a gateway of the file that is not set up here, and files that are not exports
    other = {**export, "gateways": [{**export["gateways"][0], "base_id": "FF-80-00-00"}]}
    assert (await call(4, other))["result"]["gateways"] == [
        {"title": entry.title, "base_id": "FF-80-00-00", "matched": False}
    ]
    assert (await call(5, {"version": 99, "gateways": []}))["error"][
        "code"
    ] == "unsupported_version"
    assert (await call(6, {"version": 1, "gateways": "x"}))["error"][
        "code"
    ] == "unsupported_version"
    assert (await call(7, {"version": 1, "gateways": ["x"]}))["result"]["gateways"] == []


async def test_import_maps_a_swapped_gateway_and_keeps_the_second_channel(
    hass: HomeAssistant,
    gateway,  # noqa: F811
    hass_ws_client,
) -> None:
    entry, _server = gateway
    notes = entry.runtime_data.hub.notes[entry.entry_id]
    notes.set_device("05-00-00-12_2", "Kanal 2, Schrank 3")
    doc = {
        "version": 1,
        "gateways": [
            {
                "title": "Altes Gateway",
                "base_id": "FF-80-00-80",
                "note": "Keller",
                "devices": [
                    {
                        "id": "05-00-00-12",
                        "note_key": "05-00-00-12_2",
                        "note": "Kanal 2, Schrank 3",
                    },
                    {"id": "05-00-00-12", "note_key": "05-00-00-12", "note": "Kanal 1"},
                    {"id": "05-00-00-13", "note": "aus einem Export von 1.4.1"},
                ],
            }
        ],
    }
    client = await hass_ws_client(hass)

    async def call(msg_id: int, **fields):
        await client.send_json(
            {"id": msg_id, "type": "enocean_eltako/import_documentation", "doc": doc, **fields}
        )
        return await client.receive_json()

    first = await call(1)
    assert first["result"]["gateways"] == [
        {"title": "Altes Gateway", "base_id": "FF-80-00-80", "matched": False}
    ]
    mapped = await call(2, gateway_map={"FF-80-00-80": entry.entry_id})
    assert mapped["result"]["gateways"][0]["matched"] is True
    assert notes.gateway == "Keller"
    assert notes.devices == {
        "05-00-00-12_2": {"note": "Kanal 2, Schrank 3"},
        "05-00-00-12": {"note": "Kanal 1"},
        "05-00-00-13": {"note": "aus einem Export von 1.4.1"},
    }
    # a map to a gateway that is not loaded changes nothing
    again = await call(3, gateway_map={"FF-80-00-80": "unknown"})
    assert again["result"]["gateways"][0]["matched"] is False
    assert notes.log[-1]["kind"] == "import"


def test_the_event_log_notes_what_changed_between_loads() -> None:
    from custom_components.enocean_eltako.notes import MAX_LOG, Notes

    notes = Notes.__new__(Notes)  # no store needed for the bookkeeping
    notes.known, notes.log = {}, []
    notes._save = lambda: None
    first = {"a": ("Licht", ["FF-B7-44-81"]), "b": ("Dimmer", [])}
    notes.sync_known(first)
    assert notes.log == []  # the first load is the baseline
    notes.sync_known({"a": ("Licht", ["FF-B7-44-82"]), "c": ("Neu", [])})
    kinds = [(e["kind"], e["device"]) for e in notes.log]
    assert kinds == [
        ("sender_assigned", "a"),
        ("sender_removed", "a"),
        ("device_added", "c"),
        ("device_removed", "b"),
    ]
    for i in range(MAX_LOG + 20):
        notes.add_log("teach_in", "a", str(i))
    assert len(notes.log) == MAX_LOG and notes.log[-1]["detail"] == str(MAX_LOG + 19)


@pytest.mark.parametrize(
    "gateway",
    [[_subentry("meter", "05-00-00-12", "Waschmaschine")]],
    indirect=True,
)
async def test_typed_fields_are_validated_stored_and_documented(
    hass: HomeAssistant,
    gateway,  # noqa: F811
    hass_ws_client,
) -> None:
    entry, _server = gateway
    notes = entry.runtime_data.hub.notes[entry.entry_id]
    device = next(iter(entry.runtime_data.devices.values()))
    key = device.subentry.subentry_id
    client = await hass_ws_client(hass)

    async def call(msg_id: int, items, entry_id: str | None = None):
        await client.send_json(
            {
                "id": msg_id,
                "type": "enocean_eltako/set_fields",
                "entry_id": entry_id or entry.entry_id,
                "items": items,
            }
        )
        return await client.receive_json()

    values = {
        "location": " Schrank 2, Reihe 1, Platz 4 ",
        "circuit": "Klemme 12",
        "fuse": "F3 B16",
        "group": "Waschküche",
        "bus_address": "1",
        "feedback_id": "00000081",
        "installed": "2026-10-01",
        "revision": "2214",
        "power": "Netz",
        "note": "Waschküche",
    }
    reply = await call(1, [{"device": key, "values": values}])
    assert reply["result"] == {"saved": 1, "rejected": []}
    row = collect(hass)["gateways"][0]["devices"][0]
    # a device with a bus address is a channel on the bus: its place is the module's, written
    # the structured way (cabinet · row · slot)
    assert row["location"] == "Schrank 2 · Reihe 1 · 4" and row["installed"] == "2026-10-01"
    assert row["bus_address"] == "1" and row["feedback_id"] == "00000081"
    assert row["group"] == "Waschküche"
    assert all(row[f] for f in values)

    # one bad value rejects that device's whole edit; an unknown device is rejected as well
    bad = await call(2, [{"device": key, "values": {"fuse": "F4", "installed": "gestern"}}])
    assert bad["result"] == {"saved": 0, "rejected": [key]}
    assert notes.device("05-00-00-12")["fuse"] == "F3 B16"
    missing = await call(3, [{"device": "nope", "values": {"fuse": "F4"}}])
    assert missing["result"] == {"saved": 0, "rejected": ["nope"]}
    assert (await call(4, [], "unknown"))["error"]["code"] == "not_found"
    unknown_field = await call(5, [{"device": key, "values": {"colour": "red"}}])
    assert unknown_field["success"] is False
    too_long = await call(6, [{"device": key, "values": {"fuse": "x" * 41}}])
    assert too_long["success"] is False

    # clearing every field removes the device's entry
    await call(7, [{"device": key, "values": dict.fromkeys(values, "")}])
    assert notes.devices == {}

    # the import takes over all typed fields and drops a bad date
    doc = {
        "version": 1,
        "gateways": [
            {
                "base_id": entry.data["base_id"],
                "devices": [{"note_key": "05-00-00-12", **values, "installed": "gestern"}],
            }
        ],
    }
    await client.send_json({"id": 8, "type": "enocean_eltako/import_documentation", "doc": doc})
    assert (await client.receive_json())["result"]["gateways"][0]["notes"] == 9
    assert notes.device("05-00-00-12")["circuit"] == "Klemme 12"
    assert notes.device("05-00-00-12")["installed"] == ""


async def test_version_1_notes_are_migrated(hass: HomeAssistant, hass_storage, gateway) -> None:  # noqa: F811
    from custom_components.enocean_eltako.notes import Notes

    hass_storage["enocean_eltako.notes.legacy"] = {
        "version": 1,
        "minor_version": 1,
        "key": "enocean_eltako.notes.legacy",
        "data": {
            "gateway": "Keller",
            "devices": {"05-00-00-12": "Schrank 2", "05-00-00-13": "Schrank 3"},
            "tests": {},
            "manual": [],
        },
    }
    notes = Notes(hass, "legacy")
    await notes.async_load()
    assert notes.gateway == "Keller"
    assert notes.devices == {
        "05-00-00-12": {"note": "Schrank 2"},
        "05-00-00-13": {"note": "Schrank 3"},
    }
    assert notes.device("05-00-00-12")["location"] == ""
    # a stored version 2 is read as it is
    await notes.async_flush()
    assert hass_storage["enocean_eltako.notes.legacy"]["version"] == 9


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
            )
        ]
    ],
    indirect=True,
)
async def test_links_are_assigned_declared_or_entered_each_with_its_evidence(
    hass: HomeAssistant,
    gateway,  # noqa: F811
    hass_ws_client,
) -> None:
    entry, _server = gateway
    notes = entry.runtime_data.hub.notes[entry.entry_id]
    notes.set_test("05-10-A2-C1", {"central": "confirmed", "rocker": "unconfirmed"})
    notes.add_log("teach_in", "05-10-A2-C1", "Licht Flur: central", "central")
    client = await hass_ws_client(hass)

    async def call(msg_id: int, type_: str, **fields):
        await client.send_json(
            {"id": msg_id, "type": f"enocean_eltako/{type_}", "entry_id": entry.entry_id, **fields}
        )
        return await client.receive_json()

    def links():
        return {link["key"]: link for link in collect(hass)["gateways"][0]["links"]}

    shown = links()
    central = shown["assigned|05-10-A2-C1|central"]
    assert (central["from_id"], central["to_id"], central["status"]) == (
        "FF-B7-44-91",
        "05-10-A2-C1",
        "confirmed",
    )
    assert central["teach_in"] is not None and central["tested"] is not None
    rocker = shown["assigned|05-10-A2-C1|rocker"]
    assert rocker["status"] == "no_answer" and rocker["teach_in"] is None
    wall = shown["declared|05-10-A2-C1|05-10-AA-01"]
    assert (wall["status"], wall["role"], wall["from_kind"]) == ("declared", "a0 / a1", "wall")

    # an entered link: a button taught in directly, written down; one without a target is dropped
    entered = [
        {
            "id": "k1",
            "from_id": "00-12-34-56",
            "from_name": "Taster Flur links",
            "to_key": "05-10-A2-C1",
            "role": "rocker",
            "learn": "Funktion 0",
        },
        {"id": "k2", "from_id": "00-99-99-99"},  # nowhere to
    ]
    reply = await call(1, "set_links", links=entered)
    assert reply["success"]
    manual = links()["entered|k1"]
    assert (manual["source"], manual["status"]) == ("entered", "entered")
    assert (manual["to_id"], manual["to_name"]) == ("05-10-A2-C1", "Licht Flur")  # found by address
    assert "entered|k2" not in links()
    entered[0]["to_key"] = ""
    entered[0]["to_name"] = "Fremder Aktor"
    assert (await call(2, "set_links", links=entered))["success"]
    assert links()["entered|k1"]["to_name"] == "Fremder Aktor"

    # the learn position of a derived link
    key = "assigned|05-10-A2-C1|central"
    assert (await call(3, "set_link_learn", link_key=key, learn=" Funktion 45 "))["success"]
    assert links()[key]["learn"] == "Funktion 45"
    assert (await call(4, "set_link_learn", link_key=key, learn=""))["success"]
    assert links()[key]["learn"] == ""
    assert (await call(5, "set_links", links=[{"id": "x", "learn": "y" * 81}]))["success"] is False
    await client.send_json(
        {"id": 6, "type": "enocean_eltako/set_links", "entry_id": "unknown", "links": []}
    )
    assert (await client.receive_json())["error"]["code"] == "not_found"
    await client.send_json(
        {
            "id": 7,
            "type": "enocean_eltako/set_link_learn",
            "entry_id": "unknown",
            "link_key": "a",
            "learn": "",
        }
    )
    assert (await client.receive_json())["error"]["code"] == "not_found"

    # an export brings the entered link and the learn positions back, without duplicates
    notes.set_link_learn(key, "Funktion 45")
    export = collect(hass)
    notes.set_links([])
    notes.set_link_learn(key, "")
    await client.send_json({"id": 8, "type": "enocean_eltako/import_documentation", "doc": export})
    imported = (await client.receive_json())["result"]["gateways"][0]
    assert imported["links"] == 2  # the entered link and the learn position
    assert [e["to_name"] for e in notes.links] == ["Fremder Aktor"]
    assert notes.link_info[key] == {"learn": "Funktion 45"}
    await client.send_json({"id": 9, "type": "enocean_eltako/import_documentation", "doc": export})
    again = (await client.receive_json())["result"]["gateways"][0]
    assert again["links"] == 0 and len(notes.links) == 1  # nothing twice


@pytest.mark.parametrize(
    "gateway",
    [[_subentry("meter", "05-00-00-12", "Waschmaschine")]],
    indirect=True,
)
async def test_signal_data_and_unknown_senders_survive_a_restart(
    hass: HomeAssistant,
    gateway,  # noqa: F811
) -> None:
    from homeassistant.helpers.storage import Store

    from custom_components.enocean_eltako.notes import MAX_HEARD
    from custom_components.enocean_eltako.protocol.telegram import RadioTelegram, Rorg
    from custom_components.enocean_eltako.websocket import heard_by

    entry, _server = gateway
    notes = entry.runtime_data.hub.notes[entry.entry_id]
    dispatcher = entry.runtime_data.hub.dispatcher

    def hear(gateway_id: str, data: bytes, status: int, dbm: int | None) -> None:
        dispatcher.dispatch(gateway_id, RadioTelegram(Rorg.BS4, data, 0x05000012, status, dbm=dbm))

    for i in range(3):
        hear("other", bytes([0, 3, i, 0x0C]), 0x00, -70)
    hear(entry.entry_id, bytes([0, 3, 9, 0x0C]), 0x01, -85)
    # an unknown sender
    dispatcher.dispatch(entry.entry_id, RadioTelegram(Rorg.RPS, b"\x70", 0x00216343, 0x30, dbm=-71))
    await hass.async_block_till_done()

    # many telegrams, one waiting write; the flush on unload takes it
    assert notes._signal_timer is not None
    assert notes.signal["05-00-00-12"]["other"]["count"] == 3
    assert notes.heard["00-21-63-43"]["rorg"] == "F6"
    await hass.config_entries.async_unload(entry.entry_id)
    assert notes._signal_timer is None
    stored = await Store(hass, 9, f"enocean_eltako.notes.{entry.entry_id}").async_load()
    assert stored["signal"]["05-00-00-12"]["other"]["direct"] == 3
    # the last telegram of each sender is kept, also of the unknown one
    assert stored["last"]["05-00-00-12"]["data"] == "0003090C"
    assert (
        stored["last"]["05-00-00-12"]["status"] == 1 and stored["last"]["05-00-00-12"]["dbm"] == -85
    )
    assert (
        stored["last"]["00-21-63-43"]["rorg"] == "F6"
        and stored["last"]["00-21-63-43"]["data"] == "70"
    )
    assert stored["heard"]["00-21-63-43"]["dbm"] == -71

    # after the restart the gateways' view of the device and the unknown sender are still there
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    device = next(iter(entry.runtime_data.devices.values()))
    heard = {g["entry_id"]: g for g in heard_by(device)["gateways"]}
    assert heard["other"]["count"] == 3 and heard["other"]["rssi"] == -70
    assert heard[entry.entry_id]["direct"] == 0  # a repeated telegram
    assert heard_by(device)["best"] == "other"
    (gateway_doc,) = collect(hass)["gateways"]
    assert [h["id"] for h in gateway_doc["heard"]] == ["00-21-63-43"]  # not in memory, but kept

    # once hidden an unknown sender is no longer listed; forgetting a device drops its signal
    entry.runtime_data.hub.hidden[entry.entry_id] = {0x00216343}
    assert collect(hass)["gateways"][0]["heard"] == []
    notes = entry.runtime_data.hub.notes[entry.entry_id]
    notes.signal["gone"] = {"x": {"count": 1, "direct": 0, "rssi": None, "last": 1.0}}
    assert notes.prune({"05-00-00-12"}) == 0 and "gone" not in notes.signal
    for i in range(MAX_HEARD + 1):
        notes.remember_heard(f"01-00-00-{i:02X}", "F6", None, float(i))
    assert len(notes.heard) == MAX_HEARD  # the oldest went


def test_the_bus_table_of_the_planning_guide_and_the_bus_addresses() -> None:
    from custom_components.enocean_eltako.bus_devices import ADDRESSES, POWER, bus_power
    from custom_components.enocean_eltako.notes import valid_bus_address

    assert bus_power("FSR14-4x") == 0.7 and bus_power(" fsr14-2X ") == 0.14
    assert bus_power("FUD14/800 W") == 0.2  # spaces and case do not matter
    assert bus_power("F3Z14D") == 0.1  # the operating manual of 10/2026 gives it
    assert bus_power("FLUD14") is None  # "–" in the table: no value, not zero
    assert bus_power("FSR14") is None  # the type does not say 2x or 4x
    assert bus_power(None) is None and bus_power("") is None
    assert all(0 < watts <= 1 for watts in POWER.values())
    assert ADDRESSES == 126
    assert [valid_bus_address(a) for a in ("1", "126", "0", "127", "01", "1-1", "abc", "")] == [
        True,
        True,
        False,
        False,
        True,
        False,
        False,
        False,
    ]


@pytest.mark.parametrize(
    "gateway",
    [[_subentry("futh", "FF-80-1C-00", "FUTH Bad"), _subentry("meter", "05-00-00-12", "Zähler")]],
    indirect=True,
)
async def test_a_device_with_several_ids_lists_each_with_its_profile(
    hass: HomeAssistant,
    gateway,  # noqa: F811
) -> None:
    (shown,) = collect(hass)["gateways"]
    futh = next(d for d in shown["devices"] if d["name"] == "FUTH Bad")
    assert futh["ids"] == [
        {"id": "FF-80-1C-01", "eep": "A5-10-06:eltako"},
        {"id": "FF-80-1C-10", "eep": "F6-02-01:eltako"},
        {"id": "FF-80-1C-11", "eep": "F6-02-01:eltako"},
        {"id": "FF-80-1C-12", "eep": "A5-10-12:std"},
    ]
    assert next(d for d in shown["devices"] if d["name"] == "Zähler")["ids"] == []


@pytest.mark.parametrize(
    "gateway",
    [[_subentry("meter", "05-00-00-12", "Waschmaschine")]],
    indirect=True,
)
async def test_the_documentation_tells_when_a_device_was_heard_and_how_well(
    hass: HomeAssistant,
    gateway,  # noqa: F811
) -> None:
    from custom_components.enocean_eltako.protocol.telegram import RadioTelegram, Rorg

    entry, _server = gateway
    dispatcher = entry.runtime_data.hub.dispatcher
    (device_doc,) = collect(hass)["gateways"][0]["devices"]
    # nothing heard yet
    assert device_doc["signal"] == {"last": None, "rssi": None, "repeater_only": False}

    for i in range(3):
        dispatcher.dispatch(
            entry.entry_id,
            RadioTelegram(Rorg.BS4, bytes([0, 3, i, 0x0C]), 0x05000012, 0x00, dbm=-71),
        )
    await hass.async_block_till_done()
    (device_doc,) = collect(hass)["gateways"][0]["devices"]
    assert device_doc["signal"]["rssi"] == -71
    assert device_doc["signal"]["last"] is not None
    assert device_doc["signal"]["repeater_only"] is False


@pytest.mark.parametrize(
    "gateway",
    [[_subentry("meter", "05-00-00-12", "Waschmaschine")]],
    indirect=True,
)
async def test_a_device_that_is_not_virtual_follows_nothing(
    hass: HomeAssistant,
    gateway,  # noqa: F811
) -> None:
    (device_doc,) = collect(hass)["gateways"][0]["devices"]
    assert device_doc["follows"] == [] and device_doc["virtual"] is False
