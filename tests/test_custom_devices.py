"""I8: the user's own device definitions from custom_devices.yaml."""

from pathlib import Path

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component
from homeassistant.util.yaml import parse_yaml
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.enocean_eltako.const import DOMAIN
from custom_components.enocean_eltako.custom_devices import (
    DEFINITIONS,
    FILE,
    ISSUE_ID,
    async_import,
    async_load,
    export_yaml,
    parse,
)
from custom_components.enocean_eltako.protocol.models import Protocol

from .fake_gateway import FakeGateway
from .test_devices import BASE, _entity, _push, _settle
from .test_restore_and_edges import _sub, uid

pytestmark = pytest.mark.usefixtures("socket_enabled")

YAML = """
devices:
  - id: acme_climate
    name: Acme room sensor
    manufacturer: Acme
    eep: a5-04-01
    sensors:
      - field: TMP
        device_class: temperature
      - field: HUM
        name: Feuchte
        device_class: humidity
    binary_sensors:
      - field: TSN
        name: Temperature available
        on: 1
"""
BS4 = 0x07  # ESP2 ORG of a 4BS telegram
SENSOR = 0x0520CC01
# HUM 125 -> 50 %, TMP 125 -> 20 degC, DB0: LRN bit set (data), TSN 1
DATA = bytes([0x00, 0x7D, 0x7D, 0x0A])


def test_parse_reports_errors_and_keeps_valid_definitions() -> None:
    definitions, errors = parse(
        {
            "devices": [
                {"id": "ok", "name": "OK", "eep": "A5-02-05", "sensors": [{"field": "TMP"}]},
                {"id": "bad_eep", "name": "X", "eep": "A5-99-99", "sensors": [{"field": "TMP"}]},
                {"id": "bad_field", "name": "X", "eep": "A5-02-05", "sensors": [{"field": "NO"}]},
                {
                    "id": "bad_class",
                    "name": "X",
                    "eep": "A5-02-05",
                    "sensors": [{"field": "TMP", "device_class": "warmth"}],
                },
                {"id": "empty", "name": "X", "eep": "A5-02-05"},
                {"name": "no id", "eep": "A5-02-05"},
                {"id": "ok", "name": "again", "eep": "A5-02-05", "sensors": [{"field": "TMP"}]},
            ]
        }
    )
    assert list(definitions) == ["ok"]
    assert definitions["ok"].sensors[0].name == "Temperature"  # the EEP's name by default
    assert len(errors) == 6
    assert any("A5-99-99" in e for e in errors)
    assert any("'NO'" in e for e in errors)
    assert any("warmth" in e for e in errors)
    assert parse(None) == ({}, [])
    assert parse(["x"])[1] == ["the file needs a list 'devices'"]


def test_parse_reports_malformed_entries() -> None:
    """Each malformed part names its place; the definition is left out."""
    tmp = {"field": "TMP"}
    definitions, errors = parse(
        {
            "devices": [
                "not a mapping",
                {"id": " ", "name": "X", "eep": "A5-02-05", "sensors": [tmp]},
                {"id": "no_list", "name": "X", "eep": "A5-02-05", "sensors": "TMP"},
                {"id": "no_field", "name": "X", "eep": "A5-02-05", "sensors": [{"name": "T"}]},
                {"id": "twice", "name": "X", "eep": "A5-02-05", "sensors": [tmp, tmp]},
                {"id": "interval", "name": "X", "eep": "A5-02-05", "interval": 0, "sensors": [tmp]},
                {
                    "id": "on",
                    "name": "X",
                    "eep": "A5-04-01",
                    "binary_sensors": [{"field": "TSN", "on": "yes"}],
                },
                {
                    "id": "ok",
                    "name": "OK",
                    "eep": "a5-02-05",
                    "interval": 600,
                    "sensors": [{"field": "TMP", "unit": "°C", "state_class": "measurement"}],
                },
            ]
        }
    )
    assert list(definitions) == ["ok"]
    assert definitions["ok"].interval == 600
    assert definitions["ok"].sensors[0].unit == "°C"
    for message in (
        "devices[0]: must be a mapping",
        "devices[1]: id must be a text",
        "no_list: must be a list",
        "no_field[0]: needs a field",
        "twice[1]: field 'TMP' used twice",
        "interval: interval must be a number of seconds",
        "on[0]: on must be a number",
    ):
        assert any(e.startswith(message) for e in errors), message


async def test_unreadable_file_raises_issue(hass: HomeAssistant) -> None:
    _write(hass, "devices: [unclosed\n")
    assert await async_load(hass) == {}
    issue = ir.async_get(hass).async_get_issue(DOMAIN, ISSUE_ID)
    assert issue is not None
    assert issue.translation_placeholders["errors"]
    _write(hass, YAML)
    assert list(await async_load(hass)) == ["acme_climate"]
    assert ir.async_get(hass).async_get_issue(DOMAIN, ISSUE_ID) is None


def _entry(server: FakeGateway, **data) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id=BASE,
        data={
            "model": "fam_usb",
            "device": {"type": "tcp", "host": "127.0.0.1", "port": server.port},
            "base_id": BASE,
        },
        options={"message_delay": 0},
        **data,
    )


@pytest.fixture(autouse=True)
def config_dir(hass: HomeAssistant, tmp_path: Path) -> None:
    """The definitions file goes to a fresh directory, not the shared testing config."""
    hass.config.config_dir = str(tmp_path)


@pytest.fixture
async def server():
    gateway = await FakeGateway(Protocol.ESP2).start()
    yield gateway
    await gateway.stop()


def _write(hass: HomeAssistant, text: str) -> None:
    path = Path(hass.config.path(FILE))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


async def test_custom_device_sensors(hass: HomeAssistant, server) -> None:
    _write(hass, YAML)
    entry = _entry(
        server,
        subentries_data=[
            _sub("custom", "05-20-CC-01", "Raum", [], custom="acme_climate", eep="A5-04-01:std")
        ],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    await server.connected.wait()
    _push(server, BS4, DATA, SENSOR)
    await _settle(hass)
    temperature = hass.states.get(_entity(hass, "sensor", uid("05-20-CC-01", "custom_tmp")))
    assert float(temperature.state) == pytest.approx(20.0, abs=0.2)
    assert temperature.attributes["device_class"] == "temperature"
    assert temperature.attributes["unit_of_measurement"] == "°C"
    humidity = hass.states.get(_entity(hass, "sensor", uid("05-20-CC-01", "custom_hum")))
    assert float(humidity.state) == pytest.approx(50.0)
    assert humidity.attributes["friendly_name"] == "Raum Feuchte"
    available = _entity(hass, "binary_sensor", uid("05-20-CC-01", "custom_tsn"))
    assert hass.states.get(available).state == "on"
    device = entry.runtime_data.devices[next(iter(entry.subentries))]
    assert device.device_info["manufacturer"] == "Acme"
    assert device.last_telegram.data == DATA
    assert ir.async_get(hass).async_get_issue(DOMAIN, ISSUE_ID) is None
    await hass.config_entries.async_unload(entry.entry_id)


async def test_missing_definition_falls_back_to_generic(hass: HomeAssistant, server) -> None:
    _write(hass, "devices:\n  - id: broken\n    name: X\n    eep: A5-04-01\n")
    entry = _entry(
        server,
        subentries_data=[
            _sub("custom", "05-20-CC-01", "Raum", [], custom="acme_climate", eep="A5-04-01:std")
        ],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    await server.connected.wait()
    assert ir.async_get(hass).async_get_issue(DOMAIN, ISSUE_ID) is not None
    _push(server, BS4, DATA, SENSOR)
    await _settle(hass)
    generic = hass.states.get(_entity(hass, "sensor", uid("05-20-CC-01", "eep_tmp")))
    assert float(generic.state) == pytest.approx(20.0, abs=0.2)
    await hass.config_entries.async_unload(entry.entry_id)


async def test_add_custom_device_via_flow(hass: HomeAssistant, server) -> None:
    _write(hass, YAML)
    entry = _entry(server)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert "acme_climate" in DEFINITIONS
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "device"), context={"source": config_entries.SOURCE_USER}
    )
    assert "custom" in result["menu_options"]
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"next_step_id": "custom"}
    )
    assert result["step_id"] == "custom"
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"custom": "acme_climate"}
    )
    assert result["step_id"] == "address"
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"next_step_id": "device"}
    )
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"name": "Raum", "device_id": "05-20-CC-01"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    subentry = next(iter(entry.subentries.values()))
    assert subentry.data["model"] == "custom"
    assert subentry.data["custom"] == "acme_climate"
    assert subentry.data["eep"] == "A5-04-01:std"
    await hass.async_block_till_done()  # the new subentry reloads the entry
    await hass.config_entries.async_unload(entry.entry_id)


async def test_export_and_import_roundtrip(hass: HomeAssistant, tmp_path: Path) -> None:
    """A definition exported as text can be imported elsewhere; own definitions stay."""
    hass.config.config_dir = str(tmp_path)
    own = tmp_path / FILE
    own.parent.mkdir(parents=True)
    own.write_text(YAML, encoding="utf-8")
    await async_load(hass)
    assert list(DEFINITIONS) == ["acme_climate"]

    exported = export_yaml(["acme_climate"])
    assert "acme_climate" in exported and "Feuchte" in exported
    assert parse(parse_yaml(exported)) == (DEFINITIONS, [])  # what is exported is valid

    other = exported.replace("acme_climate", "acme_copy")
    result = await async_import(hass, other, overwrite=False)
    assert result.imported == ["acme_copy"] and not result.errors
    assert (tmp_path / "enocean_eltako/custom_devices/acme_copy.yaml").exists()
    assert set(DEFINITIONS) == {"acme_climate", "acme_copy"}
    assert own.read_text(encoding="utf-8") == YAML  # the own file is untouched

    again = await async_import(hass, other, overwrite=False)
    assert again.skipped == {"acme_copy": "exists"}
    assert (await async_import(hass, other, overwrite=True)).imported == ["acme_copy"]
    clash = await async_import(hass, exported, overwrite=True)
    assert clash.skipped == {"acme_climate": "own_file"}  # never replaces the own file
    bad = await async_import(hass, exported.replace("acme_climate", "../evil"), overwrite=True)
    assert bad.skipped == {"../evil": "invalid_id"}
    assert (await async_import(hass, "devices: [", overwrite=False)).errors
    assert (await async_import(hass, "devices: 5", overwrite=False)).errors


async def test_actions_return_yaml(hass: HomeAssistant, tmp_path: Path) -> None:
    hass.config.config_dir = str(tmp_path)
    await async_setup_component(hass, DOMAIN, {})
    own = tmp_path / FILE
    own.parent.mkdir(parents=True)
    own.write_text(YAML, encoding="utf-8")
    await async_load(hass)
    exported = await hass.services.async_call(
        DOMAIN, "export_custom_devices", {}, blocking=True, return_response=True
    )
    assert "acme_climate" in exported["yaml"]
    imported = await hass.services.async_call(
        DOMAIN,
        "import_custom_devices",
        {"yaml": exported["yaml"].replace("acme_climate", "acme_two")},
        blocking=True,
        return_response=True,
    )
    assert imported["imported"] == ["acme_two"]


async def test_writing_actions_need_an_admin(hass: HomeAssistant, hass_read_only_user) -> None:
    from homeassistant.core import Context
    from homeassistant.exceptions import Unauthorized

    await async_setup_component(hass, DOMAIN, {})
    context = Context(user_id=hass_read_only_user.id)
    for service, data in (
        ("import_custom_devices", {"yaml": "devices: []"}),
        ("capture", {"duration": 5}),
        ("add_energy_devices", {}),
    ):
        with pytest.raises(Unauthorized):
            await hass.services.async_call(DOMAIN, service, data, blocking=True, context=context)
