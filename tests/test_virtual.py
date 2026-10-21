"""I9 virtual sensors: HA entities sent as EnOcean contact, temperature, motion, rocker."""

import pytest
from homeassistant.config_entries import ConfigSubentryData
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.enocean_eltako.device import EnOceanDevice
from custom_components.enocean_eltako.protocol import esp2
from custom_components.enocean_eltako.protocol.send_queue import Priority
from custom_components.enocean_eltako.protocol.telegram import RadioTelegram, Rorg

from .test_devices import BASE, _entity, _settle, gateway  # noqa: F401

pytestmark = pytest.mark.usefixtures("socket_enabled")

CONTACT = 0xFFB74490
TEMPERATURE = 0xFFB74491
ROCKER = 0xFFB74492


def _virtual(model: str, sender: int, title: str, profile: str, **options) -> ConfigSubentryData:
    sender_id = f"{sender:08X}"
    sender_id = "-".join(sender_id[i : i + 2] for i in range(0, 8, 2))
    return ConfigSubentryData(
        data={
            "schema": 2,
            "model": model,
            "device_id": sender_id,
            "senders": [{"profile": profile, "sender_id": sender_id}],
            **options,
        },
        subentry_type="device",
        title=title,
        unique_id=sender_id,
    )


def _sent(server, rorg: int, data: str, sender: int, status: int = 0) -> bool:
    frame = esp2.encode_radio(RadioTelegram(rorg, bytes.fromhex(data), sender, status))
    return frame in bytes(server.received)


VIRTUALS = [
    _virtual(
        "virtual_contact",
        CONTACT,
        "Fenster HA",
        "contact",
        source="binary_sensor.window",
        send_interval=0,
        when_unavailable="safe",
    ),
    _virtual(
        "virtual_temperature",
        TEMPERATURE,
        "Temperatur HA",
        "temperature",
        source="sensor.room",
        send_interval=0,
    ),
    _virtual("virtual_rocker", ROCKER, "Taster HA", "rocker"),
]


@pytest.mark.parametrize("gateway", [VIRTUALS], indirect=True)
async def test_virtual_sensors_send(hass: HomeAssistant, gateway) -> None:  # noqa: F811
    entry, server = gateway
    hass.states.async_set("binary_sensor.window", "on")  # open
    hass.states.async_set("sensor.room", "21.5", {"unit_of_measurement": "°C"})
    await _settle(hass)
    assert _sent(server, Rorg.BS1, "08", CONTACT)  # CO 0 = open, LRN 1 = data
    assert _sent(server, Rorg.BS4, "00007608", TEMPERATURE)

    hass.states.async_set("binary_sensor.window", "off")
    await _settle(hass)
    assert _sent(server, Rorg.BS1, "09", CONTACT)  # closed
    value = hass.states.get(_entity(hass, "sensor", f"{BASE}_FF-B7-44-90_1_sent_value"))
    assert value.state == "closed"

    server.received.clear()
    hass.states.async_set("binary_sensor.window", "unavailable")
    await _settle(hass)
    assert _sent(server, Rorg.BS1, "08", CONTACT)  # safe value: open

    server.received.clear()
    hass.states.async_set("sensor.room", "72.5", {"unit_of_measurement": "°F"})  # 22.5 degC
    await _settle(hass)
    assert _sent(server, Rorg.BS4, "00007008", TEMPERATURE)


@pytest.mark.parametrize("gateway", [VIRTUALS], indirect=True)
async def test_virtual_buttons(hass: HomeAssistant, gateway) -> None:  # noqa: F811
    entry, server = gateway
    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": _entity(hass, "button", f"{BASE}_FF-B7-44-92_1_press_b1")},
        blocking=True,
    )
    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": _entity(hass, "button", f"{BASE}_FF-B7-44-90_1_teach_in_contact")},
        blocking=True,
    )
    await _settle(hass)
    assert _sent(server, Rorg.RPS, "50", ROCKER, 0x30)
    assert _sent(server, Rorg.RPS, "00", ROCKER, 0x20)
    assert _sent(server, Rorg.BS1, "00", CONTACT)  # teach-in: LRN 0
    # sends only: no radio statistics
    assert _entity(hass, "sensor", f"{BASE}_FF-B7-44-90_1_rssi") is None


async def test_add_virtual_contact_via_flow(hass: HomeAssistant, gateway) -> None:  # noqa: F811
    entry, server = gateway
    configure = hass.config_entries.subentries.async_configure
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "device"), context={"source": "user"}
    )
    result = await configure(result["flow_id"], {"next_step_id": "virtual"})
    assert result["step_id"] == "kind"
    assert "user" in result["menu_options"]  # back to the start
    result = await configure(result["flow_id"], {"next_step_id": "model_virtual_contact"})
    assert result["step_id"] == "device"
    assert "device_id" not in result["data_schema"].schema
    result = await configure(
        result["flow_id"],
        {
            "name": "Fenster Bad",
            "sender_contact": "FF-B7-44-81",
            "source": "binary_sensor.bath_window",
            "invert": False,
            "send_interval": 900,
            "when_unavailable": "skip",
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    data = result["data"]
    assert data["device_id"] == "FF-B7-44-81"
    assert data["senders"] == [{"profile": "contact", "sender_id": "FF-B7-44-81"}]
    assert data["source"] == "binary_sensor.bath_window"
    await hass.async_block_till_done()
    pool = entry.runtime_data.senders.pool
    assert pool.get(0xFFB74481).owner == "device:FF-B7-44-81:contact"

    # reconfigure: the sender is the device's ID and stays
    subentry = next(iter(entry.subentries.values()))
    result = await entry.start_subentry_reconfigure_flow(hass, subentry.subentry_id)
    assert "sender_contact" not in result["data_schema"].schema
    result = await configure(
        result["flow_id"],
        {
            "name": "Fenster Bad",
            "source": "binary_sensor.other",
            "invert": True,
            "send_interval": 0,
            "when_unavailable": "safe",
            "priority": True,
        },
    )
    assert result["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()
    data = entry.subentries[subentry.subentry_id].data
    assert data["senders"] == [{"profile": "contact", "sender_id": "FF-B7-44-81"}]
    assert data["invert"] is True
    assert data["priority"] is True


PRIORITY_CONTACT = 0xFFB74496


@pytest.mark.parametrize(
    "gateway",
    [
        [
            *VIRTUALS[:1],
            _virtual(
                "virtual_contact",
                PRIORITY_CONTACT,
                "Haustür HA",
                "contact",
                source="binary_sensor.door",
                send_interval=0,
                priority=True,
            ),
        ]
    ],
    indirect=True,
)
async def test_virtual_contact_priority(
    hass: HomeAssistant,
    gateway,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Lock-out protection: a contact with priority is queued ahead of everything else."""
    entry, server = gateway
    sent: dict[str, Priority] = {}
    original = EnOceanDevice.send

    def spy(self, data, *args, **kwargs):
        sent[self.subentry.title] = kwargs.get("priority")
        return original(self, data, *args, **kwargs)

    monkeypatch.setattr(EnOceanDevice, "send", spy)
    hass.states.async_set("binary_sensor.window", "on")
    hass.states.async_set("binary_sensor.door", "on")
    await _settle(hass)
    assert sent == {"Fenster HA": Priority.AUTOMATION, "Haustür HA": Priority.SAFETY}
    assert _sent(server, Rorg.BS1, "08", PRIORITY_CONTACT)


BRIGHTNESS = 0xFFB74493
WEATHER = 0xFFB74494
SCENE = 0xFFB74495

MORE_VIRTUALS = [
    _virtual(
        "virtual_brightness",
        BRIGHTNESS,
        "Helligkeit HA",
        "brightness",
        source="sensor.lux",
        send_interval=0,
    ),
    _virtual(
        "virtual_weather",
        WEATHER,
        "Wetter HA",
        "weather",
        weather_wind="sensor.wind",
        weather_rain="binary_sensor.rain",
        weather_brightness="sensor.lux",
        send_interval=0,
    ),
    _virtual("virtual_scene", SCENE, "Szenen HA", "rocker"),
]


def test_brightness_encoding() -> None:
    from custom_components.enocean_eltako.protocol.eep import virtual

    assert virtual.encode_brightness(50).hex() == "3200000f"  # twilight byte
    assert virtual.encode_brightness(150).hex() == "6400000f"  # 100...300 lx: 100 lx
    assert virtual.encode_brightness(300).hex() == "6401000f"  # never 0 above 300 lx
    assert virtual.encode_brightness(99999).hex() == "64ff000f"


@pytest.mark.parametrize("gateway", [MORE_VIRTUALS], indirect=True)
async def test_brightness_weather_and_scenes(hass: HomeAssistant, gateway) -> None:  # noqa: F811
    from custom_components.enocean_eltako.protocol.eep import virtual

    entry, server = gateway
    hass.states.async_set("sensor.lux", "15150", {"unit_of_measurement": "lx"})
    hass.states.async_set("sensor.wind", "36", {"unit_of_measurement": "km/h"})  # 10 m/s
    hass.states.async_set("binary_sensor.rain", "on")
    await _settle(hass)
    assert _sent(server, Rorg.BS4, "6480000f", BRIGHTNESS)  # (15150-300)/29700*255 = 127.5
    # no temperature entity: 20 degC; the brightness is also the sun on all sides
    weather = virtual.encode_weather(15150, 20.0, 10.0, night=False, rain=True)
    assert _sent(server, Rorg.BS4, weather.hex(), WEATHER)
    assert _sent(server, Rorg.BS4, virtual.encode_sun(15.15, 15.15, 15.15).hex(), WEATHER)

    server.received.clear()
    hass.states.async_set("sensor.wind", "unavailable")
    await _settle(hass)
    assert not _sent(server, Rorg.BS4, weather.hex(), WEATHER)  # nothing while unavailable

    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": _entity(hass, "button", f"{BASE}_FF-B7-44-95_1_scene_3")},
        blocking=True,
    )
    await _settle(hass)
    assert _sent(server, Rorg.RPS, "70", SCENE, 0x30)  # scene 3 = right top


async def test_add_virtual_weather_needs_an_entity(hass: HomeAssistant, gateway) -> None:  # noqa: F811
    entry, server = gateway
    configure = hass.config_entries.subentries.async_configure
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "device"), context={"source": "user"}
    )
    result = await configure(result["flow_id"], {"next_step_id": "virtual"})
    result = await configure(result["flow_id"], {"next_step_id": "model_virtual_weather"})
    assert result["step_id"] == "device"
    form = {"name": "Wetter", "sender_weather": "FF-B7-44-81", "send_interval": 900}
    result = await configure(result["flow_id"], form)
    assert result["errors"] == {"base": "weather_no_source"}
    result = await configure(result["flow_id"], {**form, "weather_wind": "sensor.wind"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["weather_wind"] == "sensor.wind"
    assert "weather_rain" not in result["data"]
    await hass.async_block_till_done()


MOTION = 0xFFB74496
EDGE_VIRTUALS = [
    _virtual(
        "virtual_motion",
        MOTION,
        "Bewegung HA",
        "motion",
        source="binary_sensor.pir",
        invert=True,
        send_interval=0,
    ),
    _virtual(
        "virtual_temperature",
        TEMPERATURE,
        "Temperatur HA",
        "temperature",
        source="sensor.room",
        send_interval=0,
    ),
    _virtual(
        "virtual_brightness",
        BRIGHTNESS,
        "Helligkeit HA",
        "brightness",
        source="sensor.lux",
        send_interval=0,
    ),
]


@pytest.mark.parametrize("gateway", [EDGE_VIRTUALS], indirect=True)
async def test_virtual_edges(hass: HomeAssistant, gateway) -> None:  # noqa: F811
    """Inverted motion; attribute changes and values that are no number send nothing."""
    entry, server = gateway
    hass.states.async_set("binary_sensor.pir", "on")
    await _settle(hass)
    assert _sent(server, Rorg.BS4, "00000008", MOTION)  # inverted: no motion
    hass.states.async_set("binary_sensor.pir", "off")
    await _settle(hass)
    assert _sent(server, Rorg.BS4, "0000ff08", MOTION)

    server.received.clear()
    hass.states.async_set("binary_sensor.pir", "off", {"friendly_name": "PIR"})
    hass.states.async_set("sensor.room", "warm", {"unit_of_measurement": "°C"})
    hass.states.async_set("sensor.lux", "bright", {"unit_of_measurement": "lx"})
    await _settle(hass)
    assert bytes(server.received) == b""
