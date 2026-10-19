"""Import of the old `eltako:` YAML: plan and flow."""

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.enocean_eltako.legacy_import import build_plan, find_legacy_config
from custom_components.enocean_eltako.protocol.ids import format_id

from .test_devices import BASE, _subentry, gateway  # noqa: F401

pytestmark = pytest.mark.usefixtures("socket_enabled")

OLD_GATEWAY = {
    "id": 1,
    "device_type": "fam-usb",
    "base_id": "FF-B7-44-80",
    "name": "FAM-USB",
    "devices": {
        "light": [
            {
                "id": "05-00-00-01",
                "eep": "M5-38-08",
                "name": "Licht Diele",
                "sender": {"id": "FF-B7-44-90", "eep": "A5-38-08"},
            },
            {
                "id": "05-00-00-02",
                "eep": "A5-38-08",
                "name": "Dimmer",
                "sender": {"id": "FF-AA-80-01", "eep": "A5-38-08"},  # other gateway's range
            },
        ],
        "switch": [
            {
                "id": "05-00-00-03",
                "eep": "M5-38-08",
                "name": "Steckdose",
                "sender": {"id": "FF-B7-44-91", "eep": "F6-02-01"},
            }
        ],
        "cover": [
            {
                "id": "05-00-00-04",
                "eep": "G5-3F-7F",
                "name": "Rollladen",
                "sender": {"id": "FF-B7-44-92", "eep": "H5-3F-7F"},
                "time_closes": 25,
                "time_opens": 27,
            }
        ],
        "binary_sensor": [
            {"id": "FE-00-00-05 left", "eep": "F6-02-01", "name": "Taster"},
            {"id": "FE-00-00-05 right", "eep": "F6-02-01", "name": "Taster rechts"},
            {
                "id": "01-00-00-06",
                "eep": "D5-00-01",
                "name": "Tür",
                "device_class": "door",
                "invert_signal": True,
            },
            {"id": "01-00-00-07", "eep": "A5-08-01", "name": "FBH Flur"},
            {"id": "01-00-00-09", "eep": "A5-30-01", "name": "Eingang"},
        ],
        "sensor": [
            {"id": "01-00-00-07", "eep": "A5-08-01", "name": "FBH Flur Helligkeit"},
            {"id": "01-00-00-08", "eep": "A5-09-0C", "name": "Luftqualität"},
            {"id": "05-00-00-12", "eep": "A5-12-01", "name": "Zähler"},
        ],
        "climate": [
            {
                "id": "05-00-00-10",
                "eep": "A5-10-06",
                "name": "Bad",
                "temperature_unit": "°C",
                "sender": {"id": "FF-B7-44-93", "eep": "A5-10-06"},
                "thermostat": {"id": "05-00-00-11", "eep": "A5-10-06"},
            }
        ],
    },
}


def test_find_legacy_config_also_in_packages() -> None:
    block = {"gateway": [OLD_GATEWAY]}
    assert find_legacy_config({"eltako": block}) is block
    assert find_legacy_config({"homeassistant": {"packages": {"eno": {"eltako": block}}}}) is block
    assert find_legacy_config({"light": []}) is None


def test_plan_maps_kinds_senders_and_options() -> None:
    plan = build_plan(OLD_GATEWAY, existing_ids={"05-00-00-12"})
    by_id = {format_id(d.device_id): d for d in plan.create}
    assert by_id["05-00-00-01"].kind == "switch"
    assert by_id["05-00-00-01"].options["platform"] == "light"
    assert by_id["05-00-00-01"].senders == {"central": 0xFFB74490}
    assert by_id["05-00-00-02"].kind == "dimmer"
    assert by_id["05-00-00-03"].options["platform"] == "switch"
    assert by_id["05-00-00-03"].senders == {"rocker": 0xFFB74491}
    cover = by_id["05-00-00-04"]
    assert cover.kind == "cover" and cover.senders == {"controller": 0xFFB74492}
    assert cover.options == {"time_opens": 27, "time_closes": 25, "routing": "controller"}
    assert by_id["FE-00-00-05"].kind == "rocker"  # left and right: one device
    assert by_id["01-00-00-06"].options == {"device_class": "door", "invert": True}
    assert by_id["01-00-00-07"].kind == "fbh"  # binary sensor + sensor merged
    assert by_id["05-00-00-10"].kind == "heating_actuator"
    assert by_id["05-00-00-11"].kind == "room_controller"  # its wall thermostat
    assert plan.existing == ["Zähler"]
    assert sorted(plan.skipped) == [
        "Eingang (binary_sensor A5-30-01)",
        "Luftqualität (sensor A5-09-0C)",
    ]


async def test_import_flow_creates_the_devices(hass: HomeAssistant, gateway, monkeypatch) -> None:  # noqa: F811
    from custom_components.enocean_eltako import import_flow

    async def fake_config(_hass):
        return {"eltako": {"gateway": [OLD_GATEWAY]}}

    monkeypatch.setattr(import_flow, "async_hass_config_yaml", fake_config)
    entry, _server = gateway
    reloads = []
    original = hass.config_entries.async_reload

    async def counting_reload(entry_id):
        reloads.append(entry_id)
        return await original(entry_id)

    monkeypatch.setattr(hass.config_entries, "async_reload", counting_reload)
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "import"), context={"source": "user"}
    )
    assert result["step_id"] == "preview"
    assert result["description_placeholders"]["create_count"] == "10"
    result = await hass.config_entries.subentries.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "imported"
    assert "Bad" in result["description_placeholders"]["heating"]
    assert "Dimmer: FF-AA-80-01" in result["description_placeholders"]["dropped"]
    await hass.async_block_till_done()
    titles = {s.title: s for s in entry.subentries.values()}
    assert len(titles) == 10
    assert titles["Licht Diele"].data["senders"] == [
        {"profile": "central", "sender_id": "FF-B7-44-90"}
    ]
    assert "senders" not in titles["Dimmer"].data
    assert len(entry.runtime_data.devices) == 10
    assert entry.runtime_data.senders.pool.get(0xFFB74490).owner == "device:05-00-00-01:central"
    assert len(reloads) <= 1  # the subentries did not reload the entry one by one

    # a second run finds nothing new
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "import"), context={"source": "user"}
    )
    assert result["reason"] == "nothing_to_import"


async def test_import_flow_without_old_config(hass: HomeAssistant, gateway, monkeypatch) -> None:  # noqa: F811
    from custom_components.enocean_eltako import import_flow

    async def fake_config(_hass):
        return {}

    monkeypatch.setattr(import_flow, "async_hass_config_yaml", fake_config)
    entry, _server = gateway
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "import"), context={"source": "user"}
    )
    assert result["reason"] == "no_old_config"
