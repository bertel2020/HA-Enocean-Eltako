"""Catalog kinds for VOC, digital inputs (A5-30-01/03) and the D2-14 multisensors."""

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.enocean_eltako.const import DOMAIN
from custom_components.enocean_eltako.protocol.models import Protocol
from custom_components.enocean_eltako.sensor import SENSORS

from .fake_gateway import FakeGateway
from .test_devices import BASE, _entity, _push, _settle
from .test_restore_and_edges import _sub, uid

pytestmark = pytest.mark.usefixtures("socket_enabled")

BS4 = 0x07  # ESP2 ORG of a 4BS telegram


def _value(kind: str, key: str, values: dict) -> object:
    return next(d for d in SENSORS[kind] if d.key == key).value_fn(values)


def test_voc_scale_and_unit() -> None:
    assert _value("voc", "voc", {"Conc": 500.0, "SCM": 1}) == 50.0  # x0.1
    assert _value("voc", "voc", {"Conc": 500.0, "SCM": 3}) == 5000.0
    assert _value("tvoc", "voc", {"Conc": 80.0, "SCM": 2, "Unit": 1}) is None
    assert _value("tvoc", "voc_mass", {"Conc": 80.0, "SCM": 2, "Unit": 1}) == 80.0


def test_multisensor_scaling_both_profiles() -> None:
    for fields in (
        {"TMP10": 600, "HUM": 101, "ILL": 350, "ACC_X": 500},
        {"temperature": 600, "humidity": 101, "Illumination": 350, "Acceleration X": 500},
    ):
        assert _value("multisensor", "temperature", fields) == 20.0
        assert _value("multisensor", "humidity", fields) == 50.5
        assert _value("multisensor", "illuminance", fields) == 350.0
        assert _value("multisensor", "acceleration_x", fields) == 0.0
    assert _value("multisensor", "temperature", {"TMP10": 1023}) is None  # invalid


@pytest.fixture
async def sensors(hass: HomeAssistant):
    server = await FakeGateway(Protocol.ESP2).start()
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=BASE,
        data={
            "model": "fam_usb",
            "device": {"type": "tcp", "host": "127.0.0.1", "port": server.port},
            "base_id": BASE,
        },
        options={"message_delay": 0},
        subentries_data=[
            _sub("voc", "05-30-00-01", "Luft", []),
            _sub("digital_input", "05-30-00-02", "Tor", [], device_class="garage_door"),
            _sub("digital_inputs", "05-30-00-03", "Melder", []),
        ],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    await server.connected.wait()
    yield server
    await hass.config_entries.async_unload(entry.entry_id)
    await server.stop()


async def test_entities(hass: HomeAssistant, sensors) -> None:
    server = sensors
    _push(server, BS4, bytes.fromhex("01F40209"), 0x05300001)  # 500 x0.1 ppb
    _push(server, BS4, bytes.fromhex("0064FF08"), 0x05300002)  # battery low, contact open
    _push(server, BS4, bytes.fromhex("00800508"), 0x05300003)  # DI2 and DI0 high
    await _settle(hass)
    voc = hass.states.get(_entity(hass, "sensor", uid("05-30-00-01", "voc")))
    assert float(voc.state) == 50.0
    assert voc.attributes["unit_of_measurement"] == "ppb"
    gate = hass.states.get(_entity(hass, "binary_sensor", uid("05-30-00-02", "contact")))
    assert gate.state == "on"
    assert gate.attributes["device_class"] == "garage_door"
    battery = hass.states.get(_entity(hass, "binary_sensor", uid("05-30-00-02", "battery")))
    assert battery.state == "on"
    assert battery.attributes["device_class"] == "battery"  # not the contact's option
    inputs = [
        hass.states.get(_entity(hass, "binary_sensor", uid("05-30-00-03", f"input_{n}"))).state
        for n in range(4)
    ]
    assert inputs == ["on", "off", "on", "off"]
