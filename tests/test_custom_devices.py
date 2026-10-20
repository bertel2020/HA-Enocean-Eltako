"""I8: the user's own device definitions from custom_devices.yaml."""

from pathlib import Path

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import issue_registry as ir
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.enocean_eltako.const import DOMAIN
from custom_components.enocean_eltako.custom_devices import DEFINITIONS, FILE, ISSUE_ID, parse
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
