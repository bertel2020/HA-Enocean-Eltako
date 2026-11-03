"""The installation store of the Eltako bus: taking over notes version 7, the edits of the panel,
the copy the notes keep, the checks, and export/import of version 3."""

import copy

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.enocean_eltako.bus_devices import BUS_TYPES, bus_power, bus_type
from custom_components.enocean_eltako.const import DOMAIN
from custom_components.enocean_eltako.documentation import VERSION, collect
from custom_components.enocean_eltako.installation import STORAGE_KEY, get_installation
from custom_components.enocean_eltako.installation_checks import run_checks, supply_loads
from custom_components.enocean_eltako.installation_data import (
    absorb,
    address_count,
    apply_device,
    channel_values,
    check_bus,
    check_cabinet,
    check_module,
    empty,
    manual_values,
    normalize,
    parse_place,
    supply_values,
    sync_manual,
    sync_supplies,
)
from custom_components.enocean_eltako.protocol.models import Protocol

from .fake_gateway import FakeGateway
from .test_devices import BASE, _subentry, gateway  # noqa: F401

pytestmark = pytest.mark.usefixtures("socket_enabled")

GW = {"entry_id": "gw1", "title": "FAM-USB Keller", "wired": False, "bus_group": None}


def _device(key, name, model="", **fields):
    blank = {"group": "", "location": "", "bus_address": "", "feedback_id": "", "bus_power": ""}
    return {"key": key, "name": name, "model": model, **blank, **fields}


# notes version 7 as the concept describes them: two supplies with address ranges, an FSR14-4x
# whose channels share "part of", an F3Z14D written down by hand, a place as free text
LEGACY = {
    **GW,
    "devices": [
        _device(
            "05-10-A2-B3",
            "Licht Diele",
            "FSR14-4x",
            group="Licht EG 1",
            bus_address="1",
            feedback_id="00000081",
            location="Keller-Verteiler · Reihe 1 · 3",
        ),
        _device("05-10-A2-B5", "Licht Küche", "FSR14-4x", group="Licht EG 1", bus_address="2"),
        _device("05-10-A2-B6", "Licht Bad", "FSR14-4x", group="Licht EG 1", bus_address="3"),
        _device("05-10-A2-C2", "Rollladen Bad", "FSB14", bus_address="9", location="Flur EG"),
        _device("05-10-A2-B4", "Dimmer Flur", "FUD14", bus_power="0,3"),
        _device("05-22-22-22", "Fensterkontakt", ""),  # radio, not on the bus
    ],
    "supplies": [
        {"id": "s1", "name": "FSNT14-12V", "watts": "12", "first": "1", "last": "8"},
        {
            "id": "s2",
            "name": "FSNT14-12V",
            "watts": "12",
            "first": "9",
            "last": "",
            "location": "Keller-Verteiler, Reihe 1, Platz 6",
            "fuse": "F12",
        },
    ],
    "manual": [
        {"id": "m1", "name": "Taster Flur", "address": "00-12-34-56", "bus_address": ""},
        {
            "id": "m3",
            "name": "F3Z14D",
            "function": "Stromzähler Haus",
            "bus_address": "12",
            "feedback_id": "00008C0C",
            "bus_power": "",
        },
    ],
}


def _by_type(data, type_):
    return [m for m in data["modules"] if m["type"] == type_]


def test_the_catalog_knows_width_addresses_power_and_role() -> None:
    fsr = bus_type(" fsr14-4X ")
    assert (fsr.te, fsr.addresses, fsr.power, fsr.role) == (1, 4, 0.7, "actuator")
    fam = bus_type("FAM14")
    assert (fam.te, fam.addresses, fam.supply, fam.role) == (2, 0, 12.0, "master")
    assert bus_type("F3Z14D").addresses == 3 and bus_power("F3Z14D") == 0.1
    assert bus_type("FSU14").addresses == 8 and bus_type("FMSR14").addresses == 5
    assert bus_type("FTS14TG").te == 2.5 and bus_type("FUD14/800W").te == 2
    assert bus_type("DS14").role == "accessory" and bus_type("DS14").te == 0.5
    assert bus_type("FSNT14-12V/12W").role == "supply"
    assert bus_type("FSR14") is None and bus_type(None) is None
    from custom_components.enocean_eltako.bus_devices import ROLES

    assert all(t.role in ROLES for t in BUS_TYPES.values())
    assert len(BUS_TYPES) == 52
    from custom_components.enocean_eltako.bus_devices import is_bus_model

    assert is_bus_model("FSR14M-2x") and is_bus_model("BGW14") and not is_bus_model("GBA14")


def test_notes_of_version_7_become_buses_modules_and_channels() -> None:
    data = empty()
    added = absorb(data, copy.deepcopy(LEGACY))
    assert added == 6  # FSR14-4x, FSB14, FUD14, two supplies, F3Z14D (the master is extra)
    (bus,) = data["buses"]
    assert bus["access"] == [{"entry_id": "gw1", "via": "radio"}] and bus["bus_group"] is None

    (fsr,) = _by_type(data, "FSR14-4x")
    assert fsr["name"] == "Licht EG 1" and fsr["first_address"] == 1
    assert [(c["n"], c["device_key"]) for c in fsr["channels"]] == [
        (1, "05-10-A2-B3"),
        (2, "05-10-A2-B5"),
        (3, "05-10-A2-B6"),
    ]
    assert fsr["channels"][0]["feedback_id"] == "00000081"
    # the place "cabinet · row · slot" is a cabinet, a row of 12 TE and a slot
    (cabinet,) = data["cabinets"]
    assert cabinet["name"] == "Keller-Verteiler"
    assert [(r["name"], r["te"]) for r in cabinet["rows"]] == [("Reihe 1", 12)]
    assert fsr["row"] == cabinet["rows"][0]["id"] and fsr["slot"] == 3.0

    (fsb,) = _by_type(data, "FSB14")
    assert fsb["first_address"] == 9 and fsb["row"] is None
    assert fsb["legacy_location"] == "Flur EG"  # no complete place: kept as text
    (fud,) = _by_type(data, "FUD14")
    assert fud["first_address"] is None and fud["power"] == "0,3"

    s1, s2 = [m for m in data["modules"] if m["role"] == "supply"]
    assert (s1["supply_id"], s1["legacy_range"], s1["supply_watts"]) == ("s1", "1-8", "12")
    assert (s2["legacy_range"], s2["fuse"]) == ("9-126", "F12")
    assert s2["row"] == cabinet["rows"][0]["id"] and s2["slot"] == 6.0  # with commas as well

    (meter,) = _by_type(data, "F3Z14D")
    assert meter["first_address"] == 12 and address_count(meter) == 3
    assert meter["channels"][0]["manual_id"] == "m3"
    assert meter["channels"][0]["function"] == "Stromzähler Haus"

    # no FAM14 written down: a placeholder master without a place
    master = next(m for m in data["modules"] if m["id"] == bus["master"])
    assert master["type"] == "FAM14" and master["placeholder"] and master["row"] is None

    # what is taken stays: the same notes again add nothing
    before = copy.deepcopy(data)
    assert absorb(data, copy.deepcopy(LEGACY)) == 0
    assert data == before


def test_a_part_of_text_makes_modules_no_bigger_than_the_type() -> None:
    data = empty()
    devices = [
        _device(f"k{i}", f"Kanal {i}", "FSR14-2x", group="Außen", bus_address=str(i))
        for i in (1, 2, 3, 4, 5)
    ]
    absorb(data, {**GW, "devices": devices, "supplies": [], "manual": []})
    modules = _by_type(data, "FSR14-2x")
    assert [(m["first_address"], [c["device_key"] for c in m["channels"]]) for m in modules] == [
        (1, ["k1", "k2"]),
        (3, ["k3", "k4"]),
        (5, ["k5"]),
    ]


def test_bus_gateways_of_one_bus_group_share_a_bus() -> None:
    data = empty()
    wired = {"wired": True, "bus_group": "abcd1234", "supplies": [], "manual": []}
    absorb(
        data, {**wired, "entry_id": "a", "title": "FGW14", "devices": [_device("x", "X", "FUD14")]}
    )
    absorb(
        data, {**wired, "entry_id": "b", "title": "FAM14", "devices": [_device("y", "Y", "FUD14")]}
    )
    (bus,) = data["buses"]
    assert bus["access"] == [{"entry_id": "a", "via": "wired"}, {"entry_id": "b", "via": "wired"}]
    assert bus["bus_group"] == "abcd1234"


def test_a_place_is_read_from_text() -> None:
    assert parse_place("Schrank 2 · Reihe 1 · 4") == ("Schrank 2", "Reihe 1", 4.0)
    assert parse_place("Schrank 2, Reihe 1, Platz 4,5") == ("Schrank 2", "Reihe 1", 4.5)
    assert parse_place("Flur EG") == ("Flur EG", "", None)
    assert parse_place("A · B · links") == ("A", "B", None)


def _placed():
    data = empty()
    absorb(data, copy.deepcopy(LEGACY))
    return data, data["cabinets"][0]["rows"][0]["id"], data["buses"][0]["id"]


def test_an_edit_is_checked_against_the_rail_and_the_addresses() -> None:
    data, row, bus = _placed()
    good = {"bus": bus, "type": "FUD14", "row": row, "slot": 1, "first_address": 20}
    module, reason = check_module(data, good)
    assert reason == "" and module["slot"] == 1.0 and module["id"]
    for change, wanted in (
        ({"slot": 1.3}, "invalid_slot"),  # half a TE is the grid
        ({"slot": 12.5}, "row_full"),
        ({"slot": 3}, "overlap"),  # the FSR14-4x sits there
        ({"slot": 4, "spacer_before": True}, "overlap"),  # its spacer takes half a TE to the left
        ({"first_address": 127}, "invalid_address"),
        ({"type": "FSR14-4x", "first_address": 124}, "address_range"),  # 124..127
        ({"bus": "nope"}, "unknown_bus"),
        ({"power": "viel"}, "invalid_power"),
        ({"te": 0.3}, "invalid_te"),
        ({"channels": [{"n": 1, "entry_id": "gw1", "device_key": "05-10-A2-B3"}]}, "device_in_use"),
        ({"channels": [{"n": 99}]}, "invalid_channel"),
    ):
        assert check_module(data, {**good, **change}) == (None, wanted), change
    # a duplicate address is kept: the checks name it
    assert check_module(data, {**good, "first_address": 1})[1] == ""
    # a cabinet's row cannot get narrower than what sits in it, a bus wants a valid base ID
    cabinet = copy.deepcopy(data["cabinets"][0])
    cabinet["rows"][0]["te"] = 4
    assert check_cabinet(data, cabinet) == (None, "row_full")
    assert check_bus(data, {"id": bus, "base_id": "nonsense"}) == (None, "invalid_base_id")
    assert check_bus(data, {"id": bus, "master": "nope"}) == (None, "unknown_master")


def test_the_notes_keep_a_copy_of_the_bus_fields() -> None:
    data, _row, _bus = _placed()
    fsr = _by_type(data, "FSR14-4x")[0]
    fsr["power"] = "0,8"
    values = channel_values(data)
    assert values[("gw1", "05-10-A2-B3")] == {
        "bus_address": "1",
        "feedback_id": "00000081",
        "bus_power": "0,8",  # the module's power on its first channel only
    }
    assert values[("gw1", "05-10-A2-B6")] == {
        "bus_address": "3",
        "feedback_id": "",
        "bus_power": "",
    }
    assert manual_values(data)[("gw1", "m3")]["bus_address"] == "12"
    s2 = supply_values(data)[("gw1", "s2")]
    assert (s2["first"], s2["last"], s2["location"]) == (
        "9",
        "126",
        "Keller-Verteiler · Reihe 1 · 6",
    )


def test_what_older_views_write_is_taken_over() -> None:
    data, _row, _bus = _placed()
    fsr = _by_type(data, "FSR14-4x")[0]
    # the address of the third channel moves the module: its addresses are consecutive
    device = _device("05-10-A2-B6", "Licht Bad", "FSR14-4x")
    assert apply_device(data, GW, device, {"bus_address": "7"})
    assert fsr["first_address"] == 5
    assert apply_device(data, GW, device, {"feedback_id": "00000083", "bus_power": "0,9"})
    assert fsr["channels"][2]["feedback_id"] == "00000083" and fsr["power"] == "0,9"
    assert not apply_device(data, GW, device, {"feedback_id": "00000083"})  # nothing new
    # a device not yet on the bus gets a module of its own once it has a bus field
    other = _device("05-99-00-01", "Neu", "FTN14")
    assert not apply_device(data, GW, other, {"bus_address": ""})
    assert apply_device(data, GW, other, {"bus_address": "30"})
    assert _by_type(data, "FTN14")[0]["first_address"] == 30

    # supplies: changed, removed, added
    supplies = [
        {"id": "s1", "name": "FSNT14-12V/12W", "watts": "12", "first": "1", "last": "10"},
        {"id": "s3", "name": "SNT12", "watts": "12", "first": "11", "last": "126"},
    ]
    assert sync_supplies(data, GW, supplies)
    found = {m["supply_id"]: m for m in data["modules"] if m["supply_id"]}
    assert set(found) == {"s1", "s3"} and found["s1"]["legacy_range"] == "1-10"
    assert found["s1"]["type"] == "FSNT14-12V/12W"

    # entries by hand: the bus address moves, another is taken, one without an address goes
    manual = [
        {"id": "m3", "name": "F3Z14D", "function": "Zähler", "bus_address": "40"},
        {"id": "m4", "name": "FSU14", "bus_address": "50"},
    ]
    assert sync_manual(data, GW, manual)
    assert _by_type(data, "F3Z14D")[0]["first_address"] == 40
    assert _by_type(data, "F3Z14D")[0]["channels"][0]["function"] == "Zähler"
    assert _by_type(data, "FSU14")[0]["first_address"] == 50
    assert sync_manual(data, GW, [{"id": "m3", "name": "F3Z14D", "bus_address": ""}])
    assert not _by_type(data, "F3Z14D") and not _by_type(data, "FSU14")


def test_normalize_keeps_what_fits() -> None:
    data, row, bus = _placed()
    dirty = copy.deepcopy(data)
    dirty["modules"][0]["row"] = "gone"
    dirty["modules"][0]["first_address"] = 999
    dirty["modules"].append({"no": "id"})
    dirty["buses"][0]["master"] = "gone"
    clean = normalize(dirty)
    assert clean["modules"][0]["row"] is None and clean["modules"][0]["first_address"] is None
    assert len(clean["modules"]) == len(data["modules"]) and clean["buses"][0]["master"] is None
    assert normalize(None) == empty() and normalize(normalize(data)) == normalize(data)


def test_the_checks_name_what_is_wrong() -> None:
    data, row, bus = _placed()
    fsr = _by_type(data, "FSR14-4x")[0]
    module, _ = check_module(
        data,
        {
            "bus": bus,
            "type": "FSR14-2x",
            "first_address": 3,  # its channel 1 has the address of the FSR14-4x's channel 3
            "channels": [
                {"n": 1, "name": "Außenlicht", "feedback_id": "00000081"},
                {"n": 2, "unused": True},
            ],
        },
    )
    data["modules"].append(module)
    devices = {
        ("gw1", "05-10-A2-B3"): {"name": "Licht Diele", "model": "FSR14-4x", "bus": True},
        ("gw1", "05-10-A2-B5"): {"name": "Licht Küche", "model": "FSR14-4x", "bus": True},
        ("gw1", "05-77-00-01"): {"name": "Neuer Aktor", "model": "FSR14-2x", "bus": True},
        ("gw1", "05-22-22-22"): {"name": "Fensterkontakt", "model": "", "bus": False},
    }
    result = run_checks(data, devices, {"gw1"})
    assert result["unassigned"] == [{"entry_id": "gw1", "device_key": "05-77-00-01"}]
    found = {i["code"]: i for i in result["buses"][bus]["items"]}
    assert found["address_twice"]["args"] == {"address": 3}
    assert found["address_twice"]["targets"] == [
        {"type": "channel", "id": f"{fsr['id']}:3"},
        {"type": "channel", "id": f"{module['id']}:1"},
    ]
    assert found["feedback_twice"]["args"] == {"feedback_id": "00000081"}
    assert found["no_address"]["level"] == "warning"  # the FUD14
    # the third FSR14-4x channel, the FSB14 and the FUD14 are no longer in Home Assistant
    assert {"type": "channel", "id": f"{fsr['id']}:3"} in found["ha_missing"]["targets"]
    assert found["ha_missing"]["args"] == {"count": 3}
    assert found["documented_only"]["args"] == {"count": 1}  # the unused channel does not count
    assert found["gaps"]["args"] == {"ranges": ["4-8", "10-11"], "highest": 12}
    assert found["master_placeholder"]["level"] == "info"
    assert found["unassigned"]["args"] == {"count": 1}
    assert found["no_place"]["level"] == "warning"
    assert "no_master" not in found and "two_masters" not in found
    assert result["buses"][bus]["duplicates"] == [3]


def test_supplies_feed_by_address_range_or_by_place() -> None:
    data, row, bus = _placed()
    loads = supply_loads(data, data["buses"][0])
    assert loads["mode"] == "range"  # supply s1 has no place
    s1, s2 = loads["supplies"]
    assert (s1["range"], s2["range"]) == ("1-8", "9-126")
    assert s1["load"] == 0.7  # the FSR14-4x, once
    assert s2["load"] == 0.52  # FSB14 at 9 and F3Z14D at 12
    assert s2["without_value"] == []
    # every supply placed (and the master): sections between separator bridges
    master = next(m for m in data["modules"] if m["id"] == data["buses"][0]["master"])
    s1_module = next(m for m in data["modules"] if m["supply_id"] == "s1")
    master.update(row=row, slot=1.0, placeholder=False)  # FAM14, 2 TE: slots 1 and 2
    s1_module.update(row=row, slot=4.0)
    fsr = _by_type(data, "FSR14-4x")[0]
    fsr["separator_after"] = True  # TB14 right of the FSR14-4x at 3
    loads = supply_loads(data, data["buses"][0])
    assert loads["mode"] == "place"
    first, second = loads["supplies"]
    assert first["modules"] == [master["id"]] and first["load"] == 1.5  # FAM14 0.8 + FSR14-4x
    assert second["modules"] == [
        s1_module["id"],
        next(m["id"] for m in data["modules"] if m["supply_id"] == "s2"),
    ]
    assert second["capacity"] == 24 and second["load"] == 0
    # the unplaced modules with an address are fed by none
    assert len(loads["unfed"]) == 2  # FSB14 and F3Z14D
    # overloaded
    fsr["power"] = "13"
    assert supply_loads(data, data["buses"][0])["supplies"][0]["state"] == "over"
    found = {i["code"] for i in run_checks(data, {}, set())["buses"][bus]["items"]}
    assert "supply_over" in found


# ---- with Home Assistant -------------------------------------------------------------------


BUS_DEVICES = [
    _subentry("switch", "05-10-A2-B3", "Licht Diele", model_name="FSR14-4x"),
    _subentry("switch", "05-10-A2-B5", "Licht Küche", model_name="FSR14-4x"),
    _subentry("meter", "05-00-00-12", "Waschmaschine"),
]


async def test_notes_of_version_7_are_taken_over_when_the_gateway_loads(
    hass: HomeAssistant,
    hass_storage,
) -> None:
    server = await FakeGateway(Protocol.ESP2).start()
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="FAM-USB Keller",
        unique_id=BASE,
        data={
            "model": "fam_usb",
            "device": {"type": "tcp", "host": "127.0.0.1", "port": server.port},
            "base_id": BASE,
        },
        options={"message_delay": 0},
        subentries_data=BUS_DEVICES,
    )
    entry.add_to_hass(hass)
    hass_storage[f"enocean_eltako.notes.{entry.entry_id}"] = {
        "version": 7,
        "key": f"enocean_eltako.notes.{entry.entry_id}",
        "data": {
            "gateway": "",
            "devices": {
                "05-10-A2-B3": {"bus_address": "1", "group": "Licht EG", "location": "UV · R1 · 3"},
                "05-10-A2-B5": {"bus_address": "2", "group": "Licht EG", "feedback_id": "82"},
            },
            "supplies": [
                {"id": "s1", "name": "FSNT14-12V", "watts": "12", "first": "1", "last": "8"}
            ],
            "manual": [{"id": "m3", "name": "F3Z14D", "bus_address": "12", "function": "Zähler"}],
        },
    }
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    notes = entry.runtime_data.hub.notes[entry.entry_id]
    assert notes.migrated
    installation = get_installation(hass)
    data = installation.data
    (fsr,) = _by_type(data, "FSR14-4x")
    assert [c["device_key"] for c in fsr["channels"]] == ["05-10-A2-B3", "05-10-A2-B5"]
    assert fsr["slot"] == 3.0 and data["cabinets"][0]["name"] == "UV"
    assert _by_type(data, "F3Z14D")[0]["first_address"] == 12
    # the notes keep their values (a readable copy)
    assert notes.device("05-10-A2-B5")["feedback_id"] == "82" and len(notes.supplies) == 1
    await notes.async_flush()
    await installation.async_flush()
    assert hass_storage[f"enocean_eltako.notes.{entry.entry_id}"]["version"] == 8
    assert hass_storage[f"enocean_eltako.notes.{entry.entry_id}"]["data"][
        "migrated_to_installation"
    ]
    assert hass_storage[STORAGE_KEY]["version"] == 1
    assert hass_storage[STORAGE_KEY]["data"]["modules"] == data["modules"]

    # once taken over, a reload takes nothing again
    modules = copy.deepcopy(data["modules"])
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert get_installation(hass).data["modules"] == modules
    await hass.config_entries.async_unload(entry.entry_id)
    await server.stop()


@pytest.mark.parametrize("gateway", [BUS_DEVICES], indirect=True)
async def test_the_panel_edits_the_bus_and_the_notes_follow(
    hass: HomeAssistant,
    gateway,  # noqa: F811
    hass_ws_client,
) -> None:
    entry, _server = gateway
    notes = entry.runtime_data.hub.notes[entry.entry_id]
    client = await hass_ws_client(hass)
    ids = iter(range(1, 100))

    async def call(type_, **fields):
        await client.send_json({"id": next(ids), "type": f"enocean_eltako/{type_}", **fields})
        return await client.receive_json()

    # the bus devices were taken over at the first load (two FSR14-4x without an address)
    first = (await call("installation"))["result"]
    assert set(first) == {"installation", "checks", "types", "observed"}
    (bus,) = first["installation"]["buses"]
    assert bus["access"] == [{"entry_id": entry.entry_id, "via": "radio"}]
    assert len(_by_type(first["installation"], "FSR14-4x")) == 2
    assert first["types"]["FSR14-4X"]["addresses"] == 4

    # a cabinet with a row, then one module with both channels at addresses 5 and 6
    reply = await call(
        "installation/set",
        kind="cabinet",
        item={"name": "Keller", "rows": [{"name": "Reihe 1", "te": 12}]},
    )
    assert reply["success"], reply
    row = reply["result"]["installation"]["cabinets"][0]["rows"][0]["id"]
    for module in _by_type(reply["result"]["installation"], "FSR14-4x"):
        assert (await call("installation/remove", kind="module", item_id=module["id"]))["success"]
    channels = [
        {"n": 1, "entry_id": entry.entry_id, "device_key": "05-10-A2-B3", "feedback_id": "81"},
        {"n": 2, "entry_id": entry.entry_id, "device_key": "05-10-A2-B5"},
        {"n": 3, "name": "Licht Keller", "function": "Licht"},
    ]
    module = {"bus": bus["id"], "type": "FSR14-4x", "row": row, "slot": 2, "first_address": 5}
    reply = await call("installation/set", kind="module", item={**module, "channels": channels})
    assert reply["success"], reply
    module_id = reply["result"]["id"]
    assert notes.device("05-10-A2-B3")["bus_address"] == "5"
    assert notes.device("05-10-A2-B3")["feedback_id"] == "81"
    assert notes.device("05-10-A2-B5")["bus_address"] == "6"

    # refused: overlap, a channel already taken, a bad address; nothing changes
    for item, code in (
        ({**module, "type": "FUD14", "slot": 2}, "overlap"),
        ({**module, "slot": 5, "channels": channels[:1]}, "device_in_use"),
        ({**module, "id": module_id, "first_address": 125, "channels": channels}, "address_range"),
    ):
        reply = await call("installation/set", kind="module", item=item)
        assert reply["error"]["code"] == code
    assert notes.device("05-10-A2-B5")["bus_address"] == "6"

    # an older view writes an address: the module moves and the other channel follows
    reply = await call(
        "set_fields",
        entry_id=entry.entry_id,
        items=[
            {
                "device": entry.runtime_data.devices and _key(entry, "05-10-A2-B5"),
                "values": {"bus_address": "8"},
            }
        ],
    )
    assert reply["result"]["saved"] == 1
    assert (
        next(m for m in get_installation(hass).data["modules"] if m["id"] == module_id)[
            "first_address"
        ]
        == 7
    )
    assert notes.device("05-10-A2-B3")["bus_address"] == "7"

    # the older bus view's supplies are modules; a change in the store goes back to the notes
    supplies = [{"id": "s1", "name": "FSNT14-12V", "watts": "12", "first": "1", "last": "40"}]
    assert (await call("set_supplies", entry_id=entry.entry_id, supplies=supplies))["success"]
    supply = next(m for m in get_installation(hass).data["modules"] if m["supply_id"] == "s1")
    assert supply["legacy_range"] == "1-40"
    reply = await call(
        "installation/set",
        kind="module",
        item={**supply, "legacy_range": "1-20", "row": row, "slot": 1},
    )
    assert reply["success"], reply
    assert (notes.supplies[0]["last"], notes.supplies[0]["location"]) == (
        "20",
        "Keller · Reihe 1 · 1",
    )

    # an entry by hand with a bus address is a channel; its name comes back from the panel
    manual = [{"id": "m1", "name": "F3Z14D", "function": "Zähler", "bus_address": "40"}]
    assert (await call("set_manual", entry_id=entry.entry_id, entries=manual))["success"]
    (meter,) = _by_type(get_installation(hass).data, "F3Z14D")
    assert meter["first_address"] == 40 and meter["channels"][0]["manual_id"] == "m1"
    meter["channels"][0]["name"] = "Stromzähler Haus"
    assert (await call("installation/set", kind="module", item=meter))["success"]
    assert notes.manual[0]["name"] == "Stromzähler Haus"
    assert (await call("installation/remove", kind="module", item_id=meter["id"]))["success"]
    assert notes.manual == []  # the documented device was removed

    # removing a module clears the copy in the notes
    assert (await call("installation/remove", kind="module", item_id=module_id))["success"]
    assert notes.device("05-10-A2-B3")["bus_address"] == ""
    assert (await call("installation/remove", kind="module", item_id="nope"))["error"][
        "code"
    ] == "not_found"

    # a bus: renamed with its master's base ID; one with modules is not removed
    reply = await call(
        "installation/set", kind="bus", item={**bus, "name": "Hausbus", "base_id": "ff-9a-1c-80"}
    )
    assert reply["result"]["installation"]["buses"][0]["base_id"] == "FF-9A-1C-80"
    assert (await call("installation/remove", kind="bus", item_id=bus["id"]))["error"][
        "code"
    ] == "not_empty"
    reply = await call("installation/set", kind="bus", item={"name": "Garage"})
    other = reply["result"]["id"]
    assert len(reply["result"]["installation"]["buses"]) == 2
    assert (await call("installation/remove", kind="bus", item_id=other))["success"]
    # a cabinet removed: its modules keep no place
    cabinet = get_installation(hass).data["cabinets"][0]["id"]
    assert (await call("installation/remove", kind="cabinet", item_id=cabinet))["success"]
    assert (
        next(m for m in get_installation(hass).data["modules"] if m["supply_id"] == "s1")["row"]
        is None
    )
    assert (await call("installation/set", kind="nonsense", item={}))["success"] is False


def _key(entry, unique_id: str) -> str:
    return next(s.subentry_id for s in entry.subentries.values() if s.unique_id == unique_id)


@pytest.mark.parametrize("gateway", [BUS_DEVICES], indirect=True)
async def test_the_export_of_version_3_brings_the_bus_back(
    hass: HomeAssistant,
    gateway,  # noqa: F811
    hass_ws_client,
) -> None:
    entry, _server = gateway
    notes = entry.runtime_data.hub.notes[entry.entry_id]
    installation = get_installation(hass)
    bus = installation.data["buses"][0]["id"]
    installation.set_cabinet({"name": "Keller", "rows": [{"name": "Reihe 1"}]})
    for module in _by_type(installation.data, "FSR14-4x"):
        installation.remove_module(module["id"])
    module, reason = installation.set_module(
        {
            "bus": bus,
            "type": "FSR14-4x",
            "first_address": 1,
            "row": installation.data["cabinets"][0]["rows"][0]["id"],
            "slot": 3,
            "channels": [{"n": 1, "entry_id": entry.entry_id, "device_key": "05-10-A2-B3"}],
        }
    )
    assert reason == ""
    export = copy.deepcopy(collect(hass))
    assert export["version"] == VERSION == 3
    assert export["installation"] == installation.data
    assert export["installation_checks"]["buses"][bus]["used"] == 1

    client = await hass_ws_client(hass)
    ids = iter(range(1, 20))

    async def call(doc, **fields):
        await client.send_json(
            {"id": next(ids), "type": "enocean_eltako/import_documentation", "doc": doc, **fields}
        )
        return await client.receive_json()

    # a new start: nothing documented; the export takes it all back, mapped to this gateway
    saved = copy.deepcopy(installation.data)
    installation.remove_module(module["id"])
    assert notes.device("05-10-A2-B3")["bus_address"] == ""
    moved = copy.deepcopy(export)
    moved["gateways"][0]["entry_id"] = "old-entry"
    for m in moved["installation"]["modules"]:
        for c in m["channels"]:
            c["entry_id"] = "old-entry"
    reply = await call(moved, overwrite=True)
    assert reply["success"] and reply["result"]["modules"] >= 1
    assert installation.data["modules"] == saved["modules"]
    assert notes.device("05-10-A2-B3")["bus_address"] == "1"
    # without overwrite an installation that is documented stays
    other = copy.deepcopy(export)
    other["installation"]["modules"][0]["name"] = "aus der Datei"
    assert (await call(other))["result"]["modules"] == 0
    assert all(m["name"] != "aus der Datei" for m in installation.data["modules"])


@pytest.mark.parametrize("gateway", [BUS_DEVICES], indirect=True)
async def test_an_export_of_version_2_runs_through_the_same_migration(
    hass: HomeAssistant,
    gateway,  # noqa: F811
    hass_ws_client,
) -> None:
    entry, _server = gateway
    installation = get_installation(hass)
    for module in _by_type(installation.data, "FSR14-4x"):
        installation.remove_module(module["id"])
    doc = {
        "version": 2,
        "gateways": [
            {
                "base_id": entry.data["base_id"],
                "devices": [
                    {"note_key": "05-10-A2-B3", "bus_address": "1", "group": "Licht EG"},
                    {"note_key": "05-10-A2-B5", "bus_address": "2", "group": "Licht EG"},
                ],
                "supplies": [{"id": "s9", "name": "FSNT14-12V", "watts": "12", "first": "1"}],
                "manual": [{"id": "x", "name": "F3Z14D", "bus_address": "12"}],
            }
        ],
    }
    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "enocean_eltako/import_documentation", "doc": doc})
    reply = await client.receive_json()
    assert reply["success"] and reply["result"]["modules"] == 3  # FSR14-4x, supply, F3Z14D
    (fsr,) = _by_type(installation.data, "FSR14-4x")
    assert [c["device_key"] for c in fsr["channels"]] == ["05-10-A2-B3", "05-10-A2-B5"]
    assert (
        next(m for m in installation.data["modules"] if m["supply_id"])["legacy_range"] == "1-126"
    )
    assert _by_type(installation.data, "F3Z14D")[0]["first_address"] == 12


def _rail():
    """A cabinet with two rows: FAM14 (2 TE), FSNT14 and FUD14 side by side, row 2 with FSB14."""
    data = empty()
    absorb(data, {**GW, "devices": [_device("x", "X", "FUD14")], "supplies": [], "manual": []})
    bus = data["buses"][0]["id"]
    data["cabinets"] = [
        {
            "id": "c1",
            "name": "UV",
            "area_id": None,
            "note": "",
            "rows": [
                {"id": "r1", "name": "R1", "te": 12, "next": {"kind": "", "length_m": None}},
                {"id": "r2", "name": "R2", "te": 12, "next": {"kind": "", "length_m": None}},
            ],
        }
    ]
    master = next(m for m in data["modules"] if m["id"] == data["buses"][0]["master"])
    master.update(row="r1", slot=1.0, placeholder=False)
    fud = _by_type(data, "FUD14")[0]
    fud.update(row="r1", slot=4.0, first_address=1, power="7")  # 7 W: the section is warm
    supply, _ = check_module(data, {"bus": bus, "type": "FSNT14-12V/12W", "row": "r1", "slot": 3})
    data["modules"].append(supply)
    fsb, _ = check_module(
        data, {"bus": bus, "type": "FSB14", "row": "r2", "slot": 1, "first_address": 5}
    )
    data["modules"].append(fsb)
    return data, bus, master, supply, fud, fsb


def test_the_rail_checks_air_terminator_and_row_links() -> None:
    data, bus, master, supply, fud, fsb = _rail()
    found = {i["code"]: i for i in run_checks(data, {}, set())["buses"][bus]["items"]}
    # FAM14 (1-2), FSNT14 (3), FUD14 (4) side by side, the FSNT14's section over 6 W
    assert "supply_air_left" in found and "supply_air_fam14" in found
    assert found["fud14_spacer"]["targets"] == [{"type": "module", "id": fud["id"]}]
    assert found["terminator_missing"]["targets"] == [{"type": "module", "id": fsb["id"]}]
    assert found["row_link_missing"]["targets"] == [{"type": "row", "id": "r1"}]
    # a long bridge left of the FUD14, a BBV14 to row 2, the resistor at the last device
    fud["spacer_before"] = True
    fud["slot"] = 4.5
    data["cabinets"][0]["rows"][0]["next"]["kind"] = "bbv14"
    fud["terminator"] = True
    codes = {i["code"] for i in run_checks(data, {}, set())["buses"][bus]["items"]}
    assert "fud14_spacer" not in codes and "row_link_missing" not in codes
    assert "terminator_not_last" in codes  # the FSB14 in row 2 is the end of the bus
    fsb["terminator"] = True
    assert "terminator_twice" in {
        i["code"] for i in run_checks(data, {}, set())["buses"][bus]["items"]
    }


def test_supply_sections_by_place_are_named_and_fall_back_to_ranges() -> None:
    data, bus, master, supply, fud, fsb = _rail()
    loads = supply_loads(data, data["buses"][0])
    assert loads["mode"] == "place"
    # cut at the cabinet end only: one section with FAM14 and FSNT14 (24 W)
    (section,) = loads["supplies"]
    assert section["section"] == "A" and section["capacity"] == 24
    assert set(section["members"]) == {master["id"], fud["id"], fsb["id"]}
    # a separator bridge right of the FSNT14: the FUD14 and the FSB14 hang on the FSNT14
    master["separator_after"] = True
    first, second = supply_loads(data, data["buses"][0])["supplies"]
    assert (first["section"], first["modules"], first["capacity"]) == ("A", [master["id"]], 12)
    assert second["modules"] == [supply["id"]] and second["load"] == 7.42
    # a supply without a place: the address ranges decide again
    supply["row"], supply["slot"] = None, None
    assert supply_loads(data, data["buses"][0])["mode"] == "range"


def test_modules_are_arranged_with_the_arrows() -> None:
    from custom_components.enocean_eltako.installation_data import move_module

    data, bus, master, supply, fud, fsb = _rail()
    assert move_module(data, supply["id"], 1) == ""  # swapped with the FUD14 on its right
    assert (fud["slot"], supply["slot"]) == (3.0, 4.0)
    assert move_module(data, supply["id"], 1) == ""  # last in the row: half a TE to the right
    assert supply["slot"] == 4.5
    assert move_module(data, master["id"], -1) == "row_full"  # nothing left of slot 1
    assert master["slot"] == 1.0
    fsb["slot"] = 12.0
    assert move_module(data, fsb["id"], 1) == "row_full" and fsb["slot"] == 12.0
    assert move_module(data, "nope", 1) == "not_found"


@pytest.mark.parametrize("gateway", [BUS_DEVICES], indirect=True)
async def test_the_panel_moves_a_module(hass: HomeAssistant, gateway, hass_ws_client) -> None:  # noqa: F811
    installation = get_installation(hass)
    installation.set_cabinet({"name": "UV", "rows": [{"name": "R1", "te": 4}]})
    row = installation.data["cabinets"][0]["rows"][0]["id"]
    a, b = _by_type(installation.data, "FSR14-4x")
    installation.set_module({**a, "row": row, "slot": 1})
    installation.set_module({**b, "row": row, "slot": 2})
    client = await hass_ws_client(hass)
    await client.send_json(
        {"id": 1, "type": "enocean_eltako/installation/move", "module_id": a["id"], "direction": 1}
    )
    reply = await client.receive_json()
    assert reply["success"]
    slots = {m["id"]: m["slot"] for m in reply["result"]["installation"]["modules"] if m["row"]}
    assert slots == {a["id"]: 2.0, b["id"]: 1.0}
    await client.send_json(
        {"id": 2, "type": "enocean_eltako/installation/move", "module_id": b["id"], "direction": -1}
    )
    assert (await client.receive_json())["error"]["code"] == "row_full"


def test_what_was_heard_is_compared_with_the_documentation() -> None:
    data, bus, master, supply, fud, fsb = _rail()  # FUD14 at address 1, FSB14 at 5
    fsb["channels"] = [
        {"n": 1, "entry_id": None, "device_key": None, "manual_id": None, "name": "Rollladen"}
        | {"function": "", "feedback_id": "", "unused": False}
    ]
    seen = {
        "seconds": 60,
        "base_id": "FF-9A-1C-80",
        "candidates": [],
        "answers": {"1": {"sender": "FF-9A-1C-81"}, "7": {"sender": "FF-9A-1C-87"}},
    }
    items = run_checks(data, {}, set(), {bus: seen})["buses"][bus]["items"]
    found = {i["code"]: i for i in items}
    assert found["heard_undocumented"]["targets"] == [{"type": "heard", "id": "7"}]
    assert found["heard_undocumented"]["args"]["assumed"] is True
    # the FSB14's channel did not answer within 60 s
    assert found["documented_silent"]["targets"] == [{"type": "channel", "id": f"{fsb['id']}:1"}]
    assert "base_id_candidate" not in found
    # a short session says nothing about silence; without a base ID a candidate is named
    short = {**seen, "seconds": 0, "base_id": None, "candidates": [["FF-9A-1C-80", 2]]}
    codes = {i["code"]: i for i in run_checks(data, {}, set(), {bus: short})["buses"][bus]["items"]}
    assert "documented_silent" not in codes
    assert codes["base_id_candidate"]["args"]["base_id"] == "FF-9A-1C-80"


@pytest.mark.parametrize("gateway", [BUS_DEVICES], indirect=True)
async def test_the_bus_is_read_by_listening_only(
    hass: HomeAssistant,
    gateway,  # noqa: F811
    hass_ws_client,
) -> None:
    entry, _server = gateway
    notes = entry.runtime_data.hub.notes[entry.entry_id]
    installation = get_installation(hass)
    bus = installation.data["buses"][0]["id"]
    installation.set_bus({**installation.data["buses"][0], "base_id": "FF-9A-1C-80"})
    # confirmation telegrams the FAM14 sent by radio earlier: addresses 1 and 2
    notes.remember_last("FF-9A-1C-81", entry.entry_id, 0xF6, b"\x70", 0x30, -60, 100.0)
    notes.remember_last("FF-9A-1C-82", entry.entry_id, 0xF6, b"\x50", 0x30, -61, 101.0)
    sent_before = len(entry.runtime_data.queue)
    client = await hass_ws_client(hass)
    await client.send_json(
        {"id": 1, "type": "enocean_eltako/installation/listen", "bus_id": bus, "seconds": 0}
    )
    assert (await client.receive_json())["success"] is False  # no opt-in: refused
    await client.send_json(
        {
            "id": 2,
            "type": "enocean_eltako/installation/listen",
            "bus_id": bus,
            "seconds": 0,
            "opt_in": True,
        }
    )
    assert (await client.receive_json())["success"]
    done = await client.receive_json()
    assert done["event"]["type"] == "done"
    seen = done["event"]["observed"][bus]
    assert sorted(seen["answers"]) == ["1", "2"]
    assert seen["answers"]["1"]["kind"] == "on" and seen["answers"]["2"]["kind"] == "off"
    codes = {i["code"] for i in done["event"]["checks"]["buses"][bus]["items"]}
    assert "heard_undocumented" in codes  # the FSR14-4x modules have no address yet
    assert len(entry.runtime_data.queue) == sent_before  # nothing was sent
    await client.send_json(
        {
            "id": 3,
            "type": "enocean_eltako/installation/listen",
            "bus_id": "nope",
            "seconds": 0,
            "opt_in": True,
        }
    )
    assert (await client.receive_json())["error"]["code"] == "not_found"


@pytest.mark.parametrize("gateway", [BUS_DEVICES], indirect=True)
async def test_listening_hears_live_telegrams_and_can_be_stopped(
    hass: HomeAssistant,
    gateway,  # noqa: F811
    hass_ws_client,
) -> None:
    from .test_devices import _push, _settle

    entry, server = gateway
    installation = get_installation(hass)
    bus = installation.data["buses"][0]
    installation.set_bus({**bus, "base_id": "FF-9A-1C-80"})
    listeners = len(entry.runtime_data.hub.dispatcher._listeners.get(None, ()))
    client = await hass_ws_client(hass)
    msg = {"type": "enocean_eltako/installation/listen", "bus_id": bus["id"], "opt_in": True}
    await client.send_json({"id": 1, **msg, "seconds": 1})
    assert (await client.receive_json())["success"]
    _push(server, 0x05, b"\x70", 0xFF9A1C83, 0x30)  # the FAM14 radios address 3: on
    await _settle(hass)
    progress = await client.receive_json()
    assert progress["event"]["type"] == "progress" and progress["event"]["left"] == 0
    done = await client.receive_json()
    assert done["event"]["observed"][bus["id"]]["answers"]["3"]["kind"] == "on"
    assert len(entry.runtime_data.hub.dispatcher._listeners.get(None, ())) == listeners
    # a long session stopped by the panel: its listener goes
    await client.send_json({"id": 2, **msg, "seconds": 120})
    assert (await client.receive_json())["success"]
    assert len(entry.runtime_data.hub.dispatcher._listeners.get(None, ())) == listeners + 1
    await client.send_json({"id": 3, "type": "unsubscribe_events", "subscription": 2})
    assert (await client.receive_json())["success"]
    await _settle(hass)
    assert len(entry.runtime_data.hub.dispatcher._listeners.get(None, ())) == listeners


def test_a_loaded_power_supply_wants_air_as_the_fam14_manual_says() -> None:
    data, bus, master, supply, fud, fsb = _rail()

    def codes():
        return {i["code"]: i for i in run_checks(data, {}, set())["buses"][bus]["items"]}

    load = supply_loads(data, data["buses"][0])["supplies"][0]["load"]
    assert load > 6  # FAM14 0.8 + FUD14 7 + FSB14 0.42
    found = codes()
    # above 4 W: half a TE on the FSNT14's left side; above 6 W: half a TE to the FAM14
    assert found["supply_air_left"]["targets"] == [
        {"type": "module", "id": supply["id"]},
        {"type": "module", "id": master["id"]},
    ]
    assert found["supply_air_left"]["args"] == {"load": load, "watts": 4.0}
    assert found["supply_air_fam14"]["args"]["watts"] == 6.0
    # a DS14 between FAM14 and FSNT14: half a TE of air, both rules met
    supply["spacer_before"], supply["slot"] = True, 3.5
    fud["slot"] = 4.5
    assert "supply_air_left" not in codes() and "supply_air_fam14" not in codes()
    # between 4 and 6 W only the left side counts
    supply["spacer_before"], supply["slot"], fud["slot"] = False, 3.0, 4.0
    fud["power"] = "4"
    assert "supply_air_left" in codes() and "supply_air_fam14" not in codes()
    fud["power"] = "2"  # below 4 W: no air needed
    assert "supply_air_left" not in codes()
    # the FSNT14 first in its row has no neighbour on its left
    fud["power"] = "7"
    master["row"], master["slot"] = "r2", 3.0
    assert "supply_air_left" not in codes() and "supply_air_fam14" not in codes()
