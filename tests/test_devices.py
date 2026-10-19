"""Device subentries: flow, entities from telegrams, commands, sender IDs."""

import asyncio

import pytest
from homeassistant.config_entries import ConfigSubentryData
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.enocean_eltako.const import DOMAIN
from custom_components.enocean_eltako.protocol import esp2
from custom_components.enocean_eltako.protocol.models import Protocol
from custom_components.enocean_eltako.protocol.telegram import RadioTelegram, Rorg

from .fake_gateway import FakeGateway

pytestmark = pytest.mark.usefixtures("socket_enabled")

BASE = "FF-B7-44-80"


def _subentry(model: str, device_id: str, title: str, **extra) -> ConfigSubentryData:
    return ConfigSubentryData(
        data={"schema": 1, "model": model, "device_id": device_id, **extra},
        subentry_type="device",
        title=title,
        unique_id=device_id,
    )


@pytest.fixture
async def gateway(hass: HomeAssistant, request):
    server = await FakeGateway(Protocol.ESP2).start()
    subentries = getattr(request, "param", [])
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=f"Eltako FAM-USB {BASE}",
        unique_id=BASE,
        data={
            "model": "fam_usb",
            "device": {"type": "tcp", "host": "127.0.0.1", "port": server.port},
            "base_id": BASE,
        },
        options={"message_delay": 0},
        subentries_data=subentries,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    await server.connected.wait()
    yield entry, server
    await hass.config_entries.async_unload(entry.entry_id)
    await server.stop()


def _push(server: FakeGateway, org: int, data: bytes, sender: int, status: int = 0) -> None:
    server.push(esp2.Esp2Frame(esp2.HSeq.RRT, org, data.ljust(4, b"\0"), sender, status).encode())


async def _settle(hass: HomeAssistant) -> None:
    await asyncio.sleep(0.05)
    await hass.async_block_till_done()


def _entity(hass: HomeAssistant, domain: str, unique_id: str) -> str:
    return er.async_get(hass).async_get_entity_id(domain, DOMAIN, unique_id)


async def test_add_switch_actuator_via_flow(hass: HomeAssistant, gateway) -> None:
    entry, server = gateway
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "device"), context={"source": "user"}
    )
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"model": "switch"}
    )
    assert result["step_id"] == "device"
    schema = result["data_schema"].schema
    sender_key = next(k for k in schema if k == "sender_id")
    assert sender_key.default() == "FF-B7-44-80"
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            "name": "Licht Diele",
            "device_id": "05-10-A2-B3",
            "sender_id": "FF-B7-44-81",
            "platform": "light",
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    await server.connected.wait()

    entity_id = _entity(hass, "light", f"{BASE}_05-10-A2-B3_1_light")
    assert entity_id == "light.licht_diele"
    _push(server, 0x05, b"\x70", 0x0510A2B3, 0x30)
    await _settle(hass)
    assert hass.states.get(entity_id).state == "on"

    await hass.services.async_call("light", "turn_off", {"entity_id": entity_id})
    await _settle(hass)
    sent = esp2.encode_radio(RadioTelegram(Rorg.BS4, bytes.fromhex("01000008"), 0xFFB74481))
    assert sent in bytes(server.received)
    pool = entry.runtime_data.senders.pool
    assert pool.get(0xFFB74481).owner == "device:05-10-A2-B3"


async def test_flow_rejects_bad_ids(hass: HomeAssistant, gateway) -> None:
    entry, _ = gateway
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "device"), context={"source": "user"}
    )
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"model": "switch"}
    )
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {"name": "x", "device_id": "05-10-A2-B3", "sender_id": "FF-00-00-01", "platform": "light"},
    )
    assert result["errors"] == {"sender_id": "sender_out_of_range"}
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {"name": "x", "device_id": "nonsense", "sender_id": "FF-B7-44-81", "platform": "light"},
    )
    assert result["errors"] == {"device_id": "invalid_id"}


@pytest.mark.parametrize(
    "gateway",
    [
        [
            _subentry("temp_humidity", "01-82-0A-11", "FAFT Aussen"),
            _subentry("window_handle", "00-21-63-43", "Fenstergriff"),
            _subentry("contact", "01-00-00-07", "Haustuer", device_class="door", invert=False),
            _subentry("meter", "05-00-00-12", "Waschmaschine"),
            _subentry("rocker", "00-29-89-79", "Taster"),
        ]
    ],
    indirect=True,
)
async def test_sensor_devices(hass: HomeAssistant, gateway) -> None:
    entry, server = gateway
    _push(server, 0x07, bytes.fromhex("007D7D08"), 0x01820A11)  # 50 %, 20 degC
    _push(server, 0x05, b"\xd0", 0x00216343, 0x20)  # handle tilted
    _push(server, 0x06, b"\x08", 0x01000007)  # contact open
    _push(server, 0x07, bytes.fromhex("0003E80C"), 0x05000012)  # 1000 W
    _push(server, 0x07, bytes.fromhex("00100009"), 0x05000012)  # 409.6 kWh
    _push(server, 0x05, b"\x70", 0x00298979, 0x30)  # B0 pressed
    await _settle(hass)

    def state(domain: str, device: str, key: str) -> str:
        return hass.states.get(_entity(hass, domain, f"{BASE}_{device}_1_{key}")).state

    assert float(state("sensor", "01-82-0A-11", "temperature")) == 20.0
    assert float(state("sensor", "01-82-0A-11", "humidity")) == 50.0
    assert state("sensor", "00-21-63-43", "handle") == "tilted"
    assert state("binary_sensor", "00-21-63-43", "window") == "on"
    assert state("binary_sensor", "01-00-00-07", "contact") == "on"  # open
    assert float(state("sensor", "05-00-00-12", "power")) == 1000
    assert float(state("sensor", "05-00-00-12", "energy")) == pytest.approx(409.6)
    rocker = hass.states.get(_entity(hass, "event", f"{BASE}_00-29-89-79_1_rocker"))
    assert rocker.attributes["event_type"] == "b0_pressed"


@pytest.mark.parametrize(
    "gateway",
    [
        [
            _subentry(
                "cover",
                "05-00-00-21",
                "Rollladen",
                sender_id="FF-B7-44-90",
                time_opens=20,
                time_closes=20,
            )
        ]
    ],
    indirect=True,
)
async def test_cover(hass: HomeAssistant, gateway) -> None:
    _entry, server = gateway
    entity_id = _entity(hass, "cover", f"{BASE}_05-00-00-21_1_cover")
    _push(server, 0x05, b"\x70", 0x05000021, 0x30)  # upper end position
    await _settle(hass)
    assert hass.states.get(entity_id).attributes["current_position"] == 100
    _push(server, 0x07, bytes.fromhex("0064020A"), 0x05000021)  # drove down 10 s
    await _settle(hass)
    assert hass.states.get(entity_id).attributes["current_position"] == 50

    await hass.services.async_call(
        "cover", "set_cover_position", {"entity_id": entity_id, "position": 75}
    )
    await _settle(hass)
    up_5s = esp2.encode_radio(RadioTelegram(Rorg.BS4, bytes.fromhex("00050108"), 0xFFB74490))
    assert up_5s in bytes(server.received)
    await hass.services.async_call("cover", "close_cover", {"entity_id": entity_id})
    await _settle(hass)
    down_22s = esp2.encode_radio(RadioTelegram(Rorg.BS4, bytes.fromhex("00160208"), 0xFFB74490))
    assert down_22s in bytes(server.received)


@pytest.mark.parametrize(
    "gateway",
    [[_subentry("dimmer", "05-00-00-31", "Licht Wohnzimmer", sender_id="FF-B7-44-82")]],
    indirect=True,
)
async def test_dimmer_and_teach_in(hass: HomeAssistant, gateway) -> None:
    _entry, server = gateway
    entity_id = _entity(hass, "light", f"{BASE}_05-00-00-31_1_light")
    _push(server, 0x07, bytes.fromhex("02320009"), 0x05000031)  # 50 %, on
    await _settle(hass)
    assert hass.states.get(entity_id).attributes["brightness"] == 128
    await hass.services.async_call("light", "turn_on", {"entity_id": entity_id, "brightness": 255})
    button = _entity(hass, "button", f"{BASE}_05-00-00-31_1_teach_in")
    await hass.services.async_call("button", "press", {"entity_id": button})
    await _settle(hass)
    dim_100 = esp2.encode_radio(RadioTelegram(Rorg.BS4, bytes.fromhex("02640009"), 0xFFB74482))
    teach = esp2.encode_radio(RadioTelegram(Rorg.BS4, bytes.fromhex("E0400D80"), 0xFFB74482))
    assert dim_100 in bytes(server.received)
    assert teach in bytes(server.received)


async def test_removed_device_blocks_its_sender(hass: HomeAssistant, gateway) -> None:
    entry, server = gateway
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "device"), context={"source": "user"}
    )
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"model": "switch"}
    )
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            "name": "Licht",
            "device_id": "05-10-A2-B3",
            "sender_id": "FF-B7-44-80",
            "platform": "switch",
        },
    )
    await hass.async_block_till_done()
    subentry_id = next(iter(entry.subentries))
    assert hass.config_entries.async_remove_subentry(entry, subentry_id)
    await hass.async_block_till_done()
    pool = entry.runtime_data.senders.pool
    assert pool.get(0xFFB74480).state == "blocked"
    assert pool.next_free() == 0xFFB74481
