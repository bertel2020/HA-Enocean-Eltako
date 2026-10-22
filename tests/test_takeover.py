"""Takeover from the old eltako integration's YAML configuration."""

from unittest.mock import patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.enocean_eltako.takeover import (
    find_gateway,
    plan,
    registered_device,
    subentry_data,
)
from custom_components.enocean_eltako.usage import async_usage

from .test_devices import BASE, _subentry, gateway  # noqa: F401

pytestmark = pytest.mark.usefixtures("socket_enabled")

OLD_GATEWAY = {
    "id": 1,
    "device_type": "fam-usb",
    "base_id": BASE,
    "devices": {
        "light": [
            {
                "id": "FF-C2-4A-8F",
                "eep": "M5-38-08",
                "name": "Licht Büro",
                "sender": {"id": "FF-B7-44-B9 left", "eep": "F6-02-01"},
            },
            {
                "id": "FF-C2-4A-90",
                "eep": "A5-38-08",
                "name": "Dimmer Flur",
                "sender": {"id": "FF-B7-44-B7", "eep": "A5-38-08"},
            },
        ],
        "switch": [
            {
                "id": "FF-C2-4A-91",
                "eep": "M5-38-08",
                "name": "Steckdose",
                "sender": {"id": "FF-B7-44-BA right", "eep": "F6-02-01"},
                "invert_signal": True,
            },
            {"id": "FF-C2-4A-92", "eep": "M5-38-08", "name": "Ohne Sender"},
            {
                "id": "FF-C2-4A-97",
                "eep": "F6-02-01",
                "name": "Toggler",
                "sender": {"id": "FF-B7-44-C0", "eep": "F6-02-01"},
            },
            {
                "id": "FF-C2-4A-93",
                "eep": "M5-38-08",
                "name": "Kaputt",
                "sender": {"id": "FF-B7-44-BB middle", "eep": "F6-02-01"},
            },
        ],
        "cover": [
            {
                "id": "FF-C2-4A-94",
                "eep": "G5-3F-7F",
                "name": "Rollladen",
                "sender": {"id": "FF-B7-44-BC", "eep": "H5-3F-7F"},
                "time_opens": 25,
                "time_closes": 24,
                "time_tilts": 15,
            }
        ],
        "climate": [
            {
                "id": "FF-C2-4A-95",
                "eep": "A5-10-06",
                "name": "Heizung",
                "sender": {"id": "FF-B7-44-BD", "eep": "A5-10-06"},
                "temperature_unit": "°C",
                "cooling_mode": {
                    "sensor": {"id": "FF-00-00-01"},
                    "sender": {"id": "FF-B7-44-BE", "eep": "F6-02-01"},
                },
            }
        ],
        "binary_sensor": [
            {
                "id": "01-00-00-07",
                "eep": "D5-00-01",
                "name": "Haustür",
                "device_class": "door",
                "invert_signal": True,
            },
            {"id": "FF-C2-4A-8F", "eep": "F6-02-01", "name": "Doppelt"},
            {"id": "00-21-63-43", "eep": "F6-10-00", "name": "Fenster", "invert_signal": True},
        ],
        "sensor": [
            {"id": "05-00-00-12", "eep": "A5-12-01", "name": "Zähler"},
            {"id": "05-00-00-13", "eep": "A5-07-01", "name": "Bewegung"},
            {"id": "05-00-00-14", "eep": "A5-99-99", "name": "Unbekannt"},
        ],
        "button": [
            {
                "id": "FF-C2-4A-96",
                "eep": "F6-02-01",
                "name": "Knopf",
                "sender": {"id": "FF-B7-44-BF", "eep": "F6-02-01"},
            }
        ],
    },
}
OLD_CONFIG = {"general_settings": {}, "gateway": [OLD_GATEWAY]}


def _by_name(devices):
    return {d.name: d for d in devices}


def test_find_gateway() -> None:
    assert find_gateway(OLD_CONFIG, 0xFFB74480) is OLD_GATEWAY
    assert find_gateway({"gateway": OLD_GATEWAY}, 0xFFB74480) is OLD_GATEWAY  # single gateway
    assert find_gateway(OLD_CONFIG, 0xFF000080) is None
    assert find_gateway({"gateway": [{"base_id": "nonsense"}]}, 0xFFB74480) is None


def test_plan_actuators() -> None:
    devices = _by_name(plan(OLD_GATEWAY))
    light = devices["Licht Büro"]
    assert (light.model, light.senders) == ("switch", {"rocker": 0xFFB744B9})
    assert light.data == {"platform": "light", "rocker_on_button": "a0", "rocker_off_button": "a1"}
    dimmer = devices["Dimmer Flur"]
    assert (dimmer.model, dimmer.senders, dimmer.data) == ("dimmer", {"central": 0xFFB744B7}, {})
    socket = devices["Steckdose"]  # right rocker; invert_signal reverses commands and state
    assert socket.data == {
        "platform": "switch",
        "invert": True,
        "rocker_on_button": "b0",
        "rocker_off_button": "b1",
    }
    assert devices["Toggler"].reason == "takeover_unsupported"  # reports as a rocker
    cover = devices["Rollladen"]
    assert cover.senders == {"controller": 0xFFB744BC}
    assert cover.data == {"time_opens": 25.0, "time_closes": 24.0, "tilt_time": 1.5}
    heating = devices["Heizung"]
    assert heating.model == "heating_actuator"
    assert heating.senders == {"controller": 0xFFB744BD, "cooling": 0xFFB744BE}
    assert devices["Ohne Sender"].reason == "takeover_no_sender"
    assert devices["Kaputt"].reason == "takeover_bad_sender"
    knopf = devices["Knopf"]  # the old button platform: a virtual rocker with its sender's ID
    assert (knopf.model, knopf.senders, knopf.target_id) == (
        "virtual_rocker",
        {"rocker": 0xFFB744BF},
        0xFFB744BF,
    )
    assert knopf.data == {"buttons": ["a0"]}  # "left": the old code pressed 0x30
    data = subentry_data(knopf, knopf.senders)
    assert (data["device_id"], data["buttons"]) == ("FF-B7-44-BF", ["a0"])


def _old_button(**conf) -> dict:
    return {"devices": {"button": [{"id": "FF-C2-4A-AE", "eep": "F6-02-01", **conf}]}}


def test_plan_button_side() -> None:
    right = plan(_old_button(sender={"id": "FF-B7-44-C0 right", "eep": "F6-02-01"}))[0]
    assert (right.senders, right.data) == ({"rocker": 0xFFB744C0}, {"buttons": ["b0"]})  # 0x70


def test_plan_button_without_usable_sender() -> None:
    assert plan(_old_button())[0].reason == "takeover_no_sender"
    broken = plan(_old_button(sender={"id": "nonsense"}))[0]
    assert (broken.model, broken.reason) == (None, "takeover_bad_sender")


def test_plan_sensors() -> None:
    devices = _by_name(plan(OLD_GATEWAY))
    door = devices["Haustür"]
    assert (door.model, door.data) == ("contact", {"device_class": "door", "invert": True})
    assert devices["Zähler"].model == "meter"
    window = devices["Fenster"]
    assert (window.model, window.data) == ("window_handle", {"invert": True})
    motion = devices["Bewegung"]
    assert (motion.model, motion.data) == ("eep", {"eep": "A5-07-01:std"})
    assert devices["Unbekannt"].reason == "takeover_unsupported"
    assert devices["Doppelt"].reason == "takeover_duplicate"


def test_plan_tolerates_broken_config() -> None:
    assert plan({}) == []
    assert plan({"devices": "nonsense"}) == []
    broken = {"devices": {"sensor": ["nonsense", {"id": "xx"}, {"eep": "A5-12-01"}]}}
    assert plan(broken) == []
    single = {"devices": {"sensor": {"id": "05-00-00-12", "eep": "A5-12-01"}}}
    assert [d.name for d in plan(single)] == ["05-00-00-12"]  # the ID when unnamed
    cover = {
        "devices": {
            "cover": [
                {
                    "id": "05-00-00-22",
                    "eep": "G5-3F-7F",
                    "sender": {"id": "FF-B7-44-81 right", "eep": "F6-02-01"},
                }
            ]
        }
    }
    (device,) = plan(cover)
    assert device.senders == {"direction_rocker": 0xFFB74481}
    assert device.data == {"rocker_on_button": "b0", "rocker_off_button": "b1"}


def test_subentry_data() -> None:
    light = _by_name(plan(OLD_GATEWAY))["Licht Büro"]
    assert subentry_data(light, light.senders) == {
        "schema": 3,
        "model": "switch",
        "device_id": "FF-C2-4A-8F",
        "platform": "light",
        "rocker_on_button": "a0",
        "rocker_off_button": "a1",
        "senders": [{"profile": "rocker", "sender_id": "FF-B7-44-B9"}],
    }
    motion = _by_name(plan(OLD_GATEWAY))["Bewegung"]
    assert "senders" not in subentry_data(motion, {})


@pytest.fixture
def old_yaml():
    """configuration.yaml as the takeover reads it; tests set "config" or "error"."""
    state: dict = {"config": {}}

    async def load(_hass):
        if "error" in state:
            raise state["error"]
        return state["config"]

    with patch("custom_components.enocean_eltako.takeover.async_hass_config_yaml", load):
        yield state


def _old_device(hass: HomeAssistant, old_entry, name: str, device_id: str, area: str | None):
    """A device and its entities of the old integration, as its registry entries look."""
    devices = dr.async_get(hass)
    device = devices.async_get_or_create(
        config_entry_id=old_entry.entry_id, identifiers={("eltako", device_id)}, name=name
    )
    if area:
        devices.async_update_device(device.id, area_id=ar.async_get(hass).async_create(area).id)
    registry = er.async_get(hass)
    unique = "eltako_gw1_" + device_id.lower().replace("-", "_")
    light = registry.async_get_or_create(
        "light",
        "eltako",
        unique,
        config_entry=old_entry,
        device_id=device.id,
        suggested_object_id=unique,
    )
    registry.async_update_entity(light.entity_id, labels={"matter_hub"})
    registry.async_get_or_create(
        "sensor",
        "eltako",
        f"{unique}_id",
        config_entry=old_entry,
        device_id=device.id,
        original_name="Id",
        suggested_object_id=f"{unique}_id",
    )
    return light.entity_id


async def _ws(hass_ws_client, hass, msg_id: int, type_: str, **fields):
    client = await hass_ws_client(hass)
    await client.send_json({"id": msg_id, "type": f"enocean_eltako/takeover/{type_}", **fields})
    return await client.receive_json()


async def test_takeover_status(hass: HomeAssistant, gateway, hass_ws_client, old_yaml) -> None:  # noqa: F811
    assert (await _ws(hass_ws_client, hass, 1, "status"))["result"] == {"available": False}
    old_yaml["config"] = {"eltako": OLD_CONFIG}
    assert (await _ws(hass_ws_client, hass, 2, "status"))["result"] == {"available": True}
    old_yaml["config"] = {}  # no configuration, but entities the old integration left behind
    old = MockConfigEntry(domain="eltako")
    old.add_to_hass(hass)
    _old_device(hass, old, "Licht Büro", "FF-C2-4A-8F", None)
    assert (await _ws(hass_ws_client, hass, 3, "status"))["result"] == {"available": True}


async def test_takeover_errors(hass: HomeAssistant, gateway, old_yaml, hass_ws_client) -> None:  # noqa: F811
    entry, _ = gateway
    reply = await _ws(hass_ws_client, hass, 1, "preview", entry_id=entry.entry_id)
    assert reply["error"]["code"] == "no_config"
    old_yaml["config"] = {"eltako": {"gateway": [{**OLD_GATEWAY, "base_id": "FF-80-00-00"}]}}
    reply = await _ws(hass_ws_client, hass, 2, "preview", entry_id=entry.entry_id)
    assert reply["error"]["code"] == "no_gateway"
    reply = await _ws(hass_ws_client, hass, 3, "preview", entry_id="unknown")
    assert reply["error"]["code"] == "gateway_not_loaded"
    old_yaml["error"] = OSError("no configuration.yaml")
    reply = await _ws(hass_ws_client, hass, 4, "run", entry_id=entry.entry_id, devices=[])
    assert reply["error"]["code"] == "no_config"


@pytest.mark.parametrize(
    "gateway",
    [[_subentry("meter", "05-00-00-12", "Waschmaschine")]],
    indirect=True,
)
async def test_takeover_view(hass: HomeAssistant, gateway, old_yaml, hass_ws_client) -> None:  # noqa: F811
    entry, server = gateway
    old_yaml["config"] = {"eltako": OLD_CONFIG}
    old = MockConfigEntry(domain="eltako", state=ConfigEntryState.LOADED)
    old.add_to_hass(hass)
    old_light = _old_device(hass, old, "Licht Büro", "FF-C2-4A-8F", "Büro")
    registry = er.async_get(hass)
    old_device = dr.async_get(hass).async_get(registry.async_get(old_light).device_id)
    dr.async_get(hass).async_update_device(old_device.id, name_by_user="Schreibtisch")
    registry.async_update_entity(old_light, icon="mdi:desk-lamp")
    entry.runtime_data.senders.pool.assign(0xFFB744BA, "device:FF-00-00-99:rocker")  # taken

    preview = (await _ws(hass_ws_client, hass, 1, "preview", entry_id=entry.entry_id))["result"]
    assert preview["old_active"] is True
    devices: dict = {}
    for d in preview["devices"]:
        devices.setdefault(d["id"], d)  # an ID listed twice: the first entry is the device
    assert devices["FF-C2-4A-8F"]["ready"] and devices["FF-C2-4A-8F"]["area"] == "Büro"
    assert devices["FF-C2-4A-8F"]["labels"] == ["matter_hub"]
    assert devices["FF-C2-4A-8F"]["carry"] == ["area", "icons", "labels", "names"]
    assert devices["FF-C2-4A-8F"]["used"] == 0
    assert not devices["05-00-00-12"]["ready"]  # already set up
    assert devices["05-00-00-12"]["reason"] == "takeover_exists"
    assert devices["FF-C2-4A-96"]["ready"]  # a button: becomes a virtual rocker

    ran = (
        await _ws(
            hass_ws_client,
            hass,
            2,
            "run",
            entry_id=entry.entry_id,
            devices=["FF-C2-4A-8F", "FF-C2-4A-91", "01-00-00-07", "05-00-00-12", "FF-C2-4A-96"],
            carry=["area", "labels"],
        )
    )["result"]
    # the meter was already there; only Licht Büro had something to carry over
    assert (ran["count"], ran["carried"]) == (4, 1)
    assert "FF-B7-44-BA (Steckdose): in_use" in ran["skipped"][0]
    await server.connected.wait()
    assert entry.state is ConfigEntryState.LOADED
    assert len(entry.runtime_data.devices) == 5
    assert entry.runtime_data.senders.pool.get(0xFFB744B9).owner == "device:FF-C2-4A-8F:rocker"
    # the button became a virtual rocker under its sender's ID
    assert entry.runtime_data.senders.pool.get(0xFFB744BF).owner == "device:FF-B7-44-BF:rocker"

    # the new device sits in the old device's area and its main entity has the old labels
    (device,) = (d for d in entry.runtime_data.devices.values() if d.subentry.title == "Licht Büro")
    registered = registered_device(hass, entry, device)
    assert ar.async_get(hass).async_get_area(registered.area_id).name == "Büro"
    main = next(
        e
        for e in er.async_entries_for_device(er.async_get(hass), registered.id)
        if e.original_name is None
    )
    assert main.labels == {"matter_hub"}
    assert registered.name_by_user is None and main.icon is None  # not chosen

    mapping = (await _ws(hass_ws_client, hass, 3, "mapping", entry_id=entry.entry_id))["result"]
    assert mapping["old_active"] is True
    rows = {r["old"]: r for r in mapping["rows"]}
    assert rows[old_light]["new"] == main.entity_id and rows[old_light]["primary"]
    assert rows[old_light]["taken"] and rows[old_light]["area"] == "Büro"
    assert rows[old_light]["device"] == "Licht Büro"
    id_row = rows[old_light.replace("light.", "sensor.") + "_id"]
    # the new ID sensor replaces it, although it is disabled by default
    assert id_row["new"] == "sensor.licht_buro_enocean_id"
    assert id_row["usage"] == {"automation": [], "script": [], "scene": [], "dashboard": []}
    assert mapping["missing"]["FF-C2-4A-8F"] == ["icons", "names"]

    # carried over later: what is missing gets filled in, set values stay
    reply = await _ws(
        hass_ws_client, hass, 4, "carry", entry_id=entry.entry_id, carry=["names", "icons"]
    )
    assert reply["result"] == {"carried": 1}
    assert dr.async_get(hass).async_get(registered.id).name_by_user == "Schreibtisch"
    assert er.async_get(hass).async_get(main.entity_id).icon == "mdi:desk-lamp"
    mapping = (await _ws(hass_ws_client, hass, 5, "mapping", entry_id=entry.entry_id))["result"]
    assert mapping["missing"]["FF-C2-4A-8F"] == []
    reply = await _ws(hass_ws_client, hass, 6, "carry", entry_id=entry.entry_id, carry=["names"])
    assert reply["result"] == {"carried": 0}  # nothing left to do
    reply = await _ws(hass_ws_client, hass, 7, "carry", entry_id=entry.entry_id, carry=["x"])
    assert reply["error"]["code"] == "invalid_format"


async def test_usage_finds_automations_scenes_and_dashboards(hass: HomeAssistant) -> None:
    assert await async_setup_component(
        hass,
        "automation",
        {
            "automation": {
                "id": "abends",
                "alias": "Licht abends",
                "trigger": {"platform": "state", "entity_id": "input_boolean.x", "to": "on"},
                "action": {"service": "light.turn_on", "target": {"entity_id": "light.alt"}},
            }
        },
    )
    await hass.async_block_till_done()

    class Dashboard:
        config = {"title": "Unser Zuhause"}

        async def async_load(self, force):
            return {"views": [{"cards": [{"type": "button", "entity": "light.alt"}]}]}

    class Broken:
        async def async_load(self, force):
            raise ValueError("not loadable")

    from homeassistant.components.lovelace.const import LOVELACE_DATA

    class Data:
        dashboards = {"home": Dashboard(), "bad": Broken()}

    hass.data[LOVELACE_DATA] = Data()
    usage = await async_usage(hass, ["light.alt", "light.alt_2", "light.unused"])
    assert usage["light.alt"]["automation"] == [
        {"name": "Licht abends", "path": "/config/automation/edit/abends"}
    ]
    assert usage["light.alt"]["dashboard"] == [{"name": "Unser Zuhause", "path": "/home"}]
    assert usage["light.alt"]["scene"] == usage["light.alt"]["script"] == []
    assert usage["light.alt_2"]["dashboard"] == []  # no prefix match
    assert usage["light.unused"] == {"automation": [], "script": [], "scene": [], "dashboard": []}


def test_new_entity_for_an_old_one() -> None:
    from types import SimpleNamespace as Entry

    from custom_components.enocean_eltako.takeover import new_entity as _new_entity

    light = Entry(
        domain="light", original_name=None, original_device_class=None, translation_key=None
    )
    id_sensor = Entry(
        domain="sensor",
        original_name="EnOcean ID",
        original_device_class=None,
        translation_key="enocean_id",
    )
    temp = Entry(
        domain="sensor",
        original_name="Temperature",
        original_device_class="temperature",
        translation_key=None,
    )
    other_temp = Entry(
        domain="sensor",
        original_name="Temperature 2",
        original_device_class="temperature",
        translation_key=None,
    )
    old_id = Entry(
        domain="sensor",
        original_name="Id",
        original_device_class=None,
        unique_id="eltako_gw1_ff_c2_4a_a2_id",
    )
    old_temp = Entry(
        domain="sensor",
        original_name="T",
        original_device_class="temperature",
        unique_id="eltako_gw1_ff_c2_4a_a2_temperature",
    )
    new = [light, id_sensor, temp]
    old_main = Entry(domain="switch")
    assert _new_entity(old_main, old_main, new) is light
    assert _new_entity(old_id, None, new) is id_sensor  # the old "Id" sensor
    assert _new_entity(old_temp, None, new) is temp  # the one sensor of its kind
    assert _new_entity(old_temp, None, [temp, other_temp]) is None  # two: not guessed


def test_carry_changes_fill_in_and_never_overwrite() -> None:
    from types import SimpleNamespace as Entry

    from custom_components.enocean_eltako.takeover import Carried, carry_changes

    hidden, disabled = er.RegistryEntryHider.USER, er.RegistryEntryDisabler.USER
    old_main = Entry(
        entity_id="light.alt",
        labels={"a"},
        name="Schreibtisch",
        icon=None,
        hidden_by=None,
        disabled_by=None,
        options={"conversation": {"should_expose": False}, "cloud.alexa": {}},
    )
    new_main = Entry(
        entity_id="light.neu",
        original_name=None,
        labels=set(),
        name="Eigener",  # set on the new one: stays
        icon=None,
        hidden_by=None,
        disabled_by=None,
        options={"conversation": {"should_expose": True}},
    )
    carried = Carried(area_id="kitchen", entities=[old_main], main=old_main)
    old_main.icon = "mdi:lamp"
    old_main.hidden_by, old_main.disabled_by = hidden, disabled
    assert carried.available() == {"area", "labels", "voice", "names", "icons", "visibility"}

    device = Entry(id="dev", area_id="living_room", labels=set(), name_by_user=None)
    changes = carry_changes(carried, device, [new_main])
    assert "area" not in changes  # the new device has an area of its own
    assert "names" not in changes  # and its entity a name of its own
    assert [c.values for c in changes["labels"]] == [{"labels": {"a"}}]
    assert [c.values for c in changes["icons"]] == [{"icon": "mdi:lamp"}]
    assert [c.values for c in changes["visibility"]] == [
        {"hidden_by": hidden},
        {"disabled_by": disabled},
    ]
    assert [c.values for c in changes["voice"]] == [{"assistant": "conversation", "should": False}]
    assert Carried().available() == set()
