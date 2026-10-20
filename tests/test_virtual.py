"""I9 virtual sensors: HA entities sent as EnOcean contact, temperature, motion, rocker."""

import pytest
from homeassistant.config_entries import ConfigSubentryData
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.enocean_eltako.protocol import esp2
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
        },
    )
    assert result["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()
    data = entry.subentries[subentry.subentry_id].data
    assert data["senders"] == [{"profile": "contact", "sender_id": "FF-B7-44-81"}]
    assert data["invert"] is True
