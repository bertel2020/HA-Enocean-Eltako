"""Takeover from the old eltako integration's YAML configuration."""

from unittest.mock import patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.enocean_eltako.takeover import find_gateway, plan, subentry_data

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
    assert devices["Knopf"].reason == "takeover_unsupported"


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


async def _start(hass: HomeAssistant, entry):
    result = await hass.config_entries.options.async_init(entry.entry_id)
    return await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "takeover"}
    )


@pytest.mark.parametrize(
    "gateway",
    [[_subentry("meter", "05-00-00-12", "Waschmaschine")]],
    indirect=True,
)
async def test_takeover_flow(hass: HomeAssistant, gateway, old_yaml) -> None:  # noqa: F811
    entry, server = gateway
    old_yaml["config"] = {"eltako": OLD_CONFIG}
    pool = entry.runtime_data.senders.pool
    pool.assign(0xFFB744BA, "device:FF-00-00-99:rocker")  # taken by another device
    result = await _start(hass, entry)
    assert result["step_id"] == "takeover"
    rows = result["description_placeholders"]["rows"]
    assert "| FF-C2-4A-8F | Licht Büro | light M5-38-08 |" in rows
    assert "| 05-00-00-12 | Zähler | sensor A5-12-01 | - |" in rows  # already set up
    default = next(iter(result["data_schema"].schema)).default()
    assert "05-00-00-12" not in default and "FF-C2-4A-96" not in default
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"devices": ["FF-C2-4A-8F", "FF-C2-4A-91", "01-00-00-07"]}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "takeover_done"
    assert result["description_placeholders"]["count"] == "3"
    assert "FF-B7-44-BA (Steckdose): in_use" in result["description_placeholders"]["skipped"]
    await hass.async_block_till_done()
    await server.connected.wait()
    assert entry.state is ConfigEntryState.LOADED
    data = {s.title: dict(s.data) for s in entry.subentries.values()}
    assert data["Licht Büro"]["senders"] == [{"profile": "rocker", "sender_id": "FF-B7-44-B9"}]
    assert "senders" not in data["Steckdose"]
    assert data["Haustür"]["device_class"] == "door"
    pool = entry.runtime_data.senders.pool
    assert pool.get(0xFFB744B9).owner == "device:FF-C2-4A-8F:rocker"
    assert len(entry.runtime_data.devices) == 4  # the meter and the three new ones


async def test_takeover_aborts(hass: HomeAssistant, gateway, old_yaml) -> None:  # noqa: F811
    entry, _ = gateway
    result = await _start(hass, entry)
    assert result["reason"] == "takeover_no_config"
    old_yaml["config"] = {"eltako": {"gateway": [{**OLD_GATEWAY, "base_id": "FF-80-00-00"}]}}
    result = await _start(hass, entry)
    assert result["reason"] == "takeover_no_gateway"
    assert result["description_placeholders"]["found"] == "FF-80-00-00"
    old_yaml["error"] = OSError("no configuration.yaml")
    result = await _start(hass, entry)
    assert result["reason"] == "takeover_no_config"
    del old_yaml["error"]
    old_yaml["config"] = {"eltako": OLD_CONFIG}
    result = await _start(hass, entry)
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"devices": []})
    assert result["reason"] == "senders_unchanged"
