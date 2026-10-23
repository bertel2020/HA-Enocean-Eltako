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


def test_weather_station_display() -> None:
    """Whole lux for dawn and sun, one decimal for the wind, rain without a leak sensor's class."""
    from custom_components.enocean_eltako.binary_sensor import BINARY_SENSORS

    dawn = _value("weather", "dawn", {"DWS": 998.6})
    assert dawn == 999 and isinstance(dawn, int)
    assert _value("weather", "dawn", {}) is None
    by_key = {d.key: d for d in SENSORS["weather"]}
    for key in ("dawn", "sun_west", "sun_south", "sun_east"):
        assert by_key[key].suggested_display_precision == 0
    assert by_key["wind_speed"].suggested_display_precision == 1
    assert [(d.key, d.device_class) for d in BINARY_SENSORS["weather"]] == [
        ("rain", None),
        ("rain_recent", None),
    ]


def test_sunniest_side() -> None:
    sun = {"SNW": 6.0, "SNS": 12.0, "SNE": 6.0}
    assert _value("weather", "sun_side", sun) == "south"
    assert _value("weather", "sun_side", {"SNW": 40.0, "SNS": 12.0, "SNE": 6.0}) == "west"
    assert _value("weather", "sun_side", {"SNW": 6.0, "SNS": 6.0, "SNE": 6.0}) == "south"  # a tie
    assert _value("weather", "sun_side", {"SNW": 1.0, "SNS": 1.9, "SNE": 0.0}) == "none"
    assert _value("weather", "sun_side", {"DWS": 500.0}) is None  # the other telegram


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


@pytest.fixture
async def weather(hass: HomeAssistant):
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
            _sub("weather", "05-13-00-01", "Wetter", [], rain_hold=1),
            _sub("weather", "05-13-00-02", "Wetter ohne Nachlauf", [], rain_hold=0),
        ],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    await server.connected.wait()
    yield server
    await hass.config_entries.async_unload(entry.entry_id)
    await server.stop()


async def test_weather_sun_side_and_rain_recently(hass: HomeAssistant, weather) -> None:
    from datetime import timedelta

    from homeassistant.util import dt as dt_util
    from pytest_homeassistant_custom_component.common import async_fire_time_changed

    def state(device: str, platform: str, key: str) -> str:
        return hass.states.get(_entity(hass, platform, uid(device, key))).state

    for device, hold in (("05-13-00-01", True), ("05-13-00-02", False)):
        sender = int(device.replace("-", ""), 16)
        _push(weather, BS4, bytes([0x40, 0x80, 0x10, 0x1A]), sender)  # raining
        _push(weather, BS4, bytes([0x10, 0x30, 0x10, 0x28]), sender)  # sun: south is the highest
        await _settle(hass)
        assert state(device, "binary_sensor", "rain") == "on"
        assert state(device, "binary_sensor", "rain_recent") == "on"
        assert state(device, "sensor", "sun_side") == "south"
        _push(weather, BS4, bytes([0x40, 0x80, 0x10, 0x18]), sender)  # the rain has stopped
        await _settle(hass)
        assert state(device, "binary_sensor", "rain") == "off"
        # with a hold the recent rain stays on until it has run out; without, it ends at once
        assert state(device, "binary_sensor", "rain_recent") == ("on" if hold else "off")
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=30))
    await hass.async_block_till_done()
    assert state("05-13-00-01", "binary_sensor", "rain_recent") == "on"
    _push(
        weather, BS4, bytes([0x40, 0x80, 0x10, 0x1A]), 0x05130001
    )  # rain again: the hold restarts
    _push(weather, BS4, bytes([0x40, 0x80, 0x10, 0x18]), 0x05130001)
    await _settle(hass)
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=90))
    await hass.async_block_till_done()
    assert state("05-13-00-01", "binary_sensor", "rain_recent") == "off"
