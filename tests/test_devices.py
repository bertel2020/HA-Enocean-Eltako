"""Device subentries: flow, entities from telegrams, commands, sender IDs."""

import asyncio

import pytest
from homeassistant.config_entries import ConfigEntryState, ConfigSubentryData
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.enocean_eltako.catalog import CATALOG
from custom_components.enocean_eltako.config_flow import EnOceanEltakoConfigFlow
from custom_components.enocean_eltako.const import DOMAIN, SUBENTRY_SCHEMA
from custom_components.enocean_eltako.protocol import esp2
from custom_components.enocean_eltako.protocol.eep.teach_in import encode_teach_in_4bs
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


async def _choose_model(hass: HomeAssistant, flow_id: str, model: str):
    """From the first menu through manufacturer, category and kind to the address menu."""
    entry = CATALOG[model]
    configure = hass.config_entries.subentries.async_configure
    result = await configure(flow_id, {"next_step_id": entry.group})
    result = await configure(flow_id, {"next_step_id": f"{entry.group}_{entry.category}"})
    if result["step_id"] == "kind":
        result = await configure(flow_id, {"next_step_id": f"model_{model}"})
    assert result["step_id"] == "address"
    return result


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
    result = await _choose_model(hass, result["flow_id"], "switch")
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"next_step_id": "device"}
    )
    assert result["step_id"] == "device"
    schema = result["data_schema"].schema
    keys = [k for k in schema if str(k).startswith("sender_")]
    assert keys == ["sender_rocker", "sender_central"]  # the rocker first, it gets the suggestion
    assert keys[0].description["suggested_value"] == "FF-B7-44-81"
    assert not keys[1].description
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            "name": "Licht Diele",
            "device_id": "05-10-A2-B3",
            "sender_central": "FF-B7-44-81",
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
    assert pool.get(0xFFB74481).owner == "device:05-10-A2-B3:central"


async def test_switch_actuator_with_rocker_only(hass: HomeAssistant, gateway) -> None:
    """The central command is optional: without it the actuator switches by rocker presses."""
    entry, server = gateway
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "device"), context={"source": "user"}
    )
    result = await _choose_model(hass, result["flow_id"], "switch")
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"next_step_id": "device"}
    )
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {"name": "Licht Flur", "device_id": "05-10-A2-B4", "platform": "light"},
    )
    assert result["errors"] == {"base": "sender_none"}
    schema = result["data_schema"].schema
    sender_key = next(k for k in schema if k == "sender_rocker")
    assert sender_key.description["suggested_value"] == ""  # stays cleared
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            "name": "Licht Flur",
            "device_id": "05-10-A2-B4",
            "sender_rocker": "FF-B7-44-8F",
            "platform": "light",
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["senders"] == [{"profile": "rocker", "sender_id": "FF-B7-44-8F"}]
    assert result["data"]["rocker_on_button"] == "a0"  # the collapsed section's defaults
    assert result["data"]["rocker_off_button"] == "a1"
    await hass.async_block_till_done()
    await server.connected.wait()

    entity_id = _entity(hass, "light", f"{BASE}_05-10-A2-B4_1_light")
    await hass.services.async_call("light", "turn_on", {"entity_id": entity_id})
    await _settle(hass)
    press = esp2.encode_radio(RadioTelegram(Rorg.RPS, b"\x30", 0xFFB7448F, 0x30))
    assert press in bytes(server.received)
    assert entry.runtime_data.senders.pool.get(0xFFB74480) is None
    assert _entity(hass, "button", f"{BASE}_05-10-A2-B4_1_teach_in_central") is None


@pytest.mark.parametrize(
    "gateway",
    [
        [
            _subentry(
                "switch",
                "05-10-A2-B5",
                "Licht Büro",
                senders=[
                    {"profile": "central", "sender_id": "FF-B7-44-81"},
                    {"profile": "rocker", "sender_id": "FF-B7-44-8F"},
                ],
                platform="light",
            )
        ]
    ],
    indirect=True,
)
async def test_reconfigure_drops_central_command(hass: HomeAssistant, gateway) -> None:
    entry, _ = gateway
    pool = entry.runtime_data.senders.pool
    pool.assign(0xFFB74481, "device:05-10-A2-B5:central")
    pool.assign(0xFFB7448F, "device:05-10-A2-B5:rocker")
    subentry_id = next(iter(entry.subentries))
    result = await entry.start_subentry_reconfigure_flow(hass, subentry_id)
    assert result["step_id"] == "reconfigure"
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {"name": "Licht Büro", "sender_rocker": "FF-B7-44-8F", "platform": "light"},
    )
    assert result["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()
    assert entry.subentries[subentry_id].data["senders"] == [
        {"profile": "rocker", "sender_id": "FF-B7-44-8F"}
    ]
    assert entry.runtime_data.senders.pool.get(0xFFB74481).state == "blocked"

    # a device without the central command is not offered a new one from the pool
    result = await entry.start_subentry_reconfigure_flow(hass, subentry_id)
    sender_key = next(k for k in result["data_schema"].schema if k == "sender_central")
    assert sender_key.description is None or not sender_key.description.get("suggested_value")


@pytest.mark.parametrize(
    "gateway",
    [
        [
            _subentry(
                "switch",
                "05-10-A2-B6",
                "Licht Bad",
                senders=[{"profile": "rocker", "sender_id": "FF-B7-44-8E"}],
                platform="light",
                rocker_on_button="a0",
                rocker_off_button="a1",
            ),
            _subentry(
                "cover",
                "05-00-00-24",
                "Rollladen Bad",
                senders=[{"profile": "direction_rocker", "sender_id": "FF-B7-44-8D"}],
                routing="direction_rocker",
                time_opens=20,
                time_closes=20,
                rocker_on_button="b1",
                rocker_off_button="b0",
            ),
        ]
    ],
    indirect=True,
)
async def test_rocker_sender_buttons(hass: HomeAssistant, gateway) -> None:
    """The rocker sender presses the chosen buttons: left rocker, or up and down swapped."""
    _entry, server = gateway

    def press(code: int, sender: int) -> bytes:
        return esp2.encode_radio(RadioTelegram(Rorg.RPS, bytes([code]), sender, 0x30))

    light = _entity(hass, "light", f"{BASE}_05-10-A2-B6_1_light")
    await hass.services.async_call("light", "turn_on", {"entity_id": light})
    await hass.services.async_call("light", "turn_off", {"entity_id": light})
    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": _entity(hass, "button", f"{BASE}_05-10-A2-B6_1_teach_in_rocker")},
    )
    cover = _entity(hass, "cover", f"{BASE}_05-00-00-24_1_cover")
    await hass.services.async_call("cover", "open_cover", {"entity_id": cover})
    await _settle(hass)
    received = bytes(server.received)
    assert received.count(press(0x30, 0xFFB7448E)) == 2  # on and the teach-in
    assert press(0x10, 0xFFB7448E) in received
    assert press(0x70, 0xFFB7448E) not in received
    assert press(0x50, 0xFFB7448D) in received  # B1 opens


@pytest.mark.parametrize(
    "gateway",
    [
        [
            _subentry(
                "switch",
                "05-10-A2-B7",
                "Licht Keller",
                senders=[{"profile": "rocker", "sender_id": "FF-B7-44-8C"}],
                platform="light",
                rocker_on_button="b0",
                rocker_off_button="b1",
                wall_switch="FE-D8-12-34",
                wall_on_button="a0",
                wall_off_button="a0",
            )
        ]
    ],
    indirect=True,
)
async def test_reconfigure_sections(hass: HomeAssistant, gateway) -> None:
    """Rocker buttons and wall switch sit in collapsed sections; the data stays flat."""
    entry, _ = gateway
    entry.runtime_data.senders.pool.assign(0xFFB7448C, "device:05-10-A2-B7:rocker")
    subentry_id = next(iter(entry.subentries))
    result = await entry.start_subentry_reconfigure_flow(hass, subentry_id)
    schema = result["data_schema"].schema
    sections = {
        str(k): v for k, v in schema.items() if str(k) in ("rocker_buttons", "wall_switch_settings")
    }
    assert list(sections) == ["rocker_buttons", "wall_switch_settings"]
    assert all(v.options["collapsed"] for v in sections.values())
    wall = {str(k): k.description for k in sections["wall_switch_settings"].schema.schema}
    assert wall["wall_switch"] == {"suggested_value": "FE-D8-12-34"}
    rocker = {str(k): k.description for k in sections["rocker_buttons"].schema.schema}
    assert rocker["rocker_on_button"] == {"suggested_value": "b0"}
    rocker_key = next(k for k in schema if str(k) == "rocker_buttons")
    assert rocker_key.default() == {
        "rocker_on_button": "b0",
        "rocker_off_button": "b1",
    }  # prefilled

    user_input = {
        "name": "Licht Keller",
        "sender_rocker": "FF-B7-44-8C",
        "platform": "light",
        "rocker_buttons": {"rocker_on_button": "a0", "rocker_off_button": "a1"},
        "wall_switch_settings": {"wall_switch": "nonsense"},
    }
    result = await hass.config_entries.subentries.async_configure(result["flow_id"], user_input)
    assert result["errors"] == {"base": "wall_switch_invalid_id"}
    user_input["wall_switch_settings"] = {"wall_switch": "fed81235", "wall_on_button": "b0"}
    result = await hass.config_entries.subentries.async_configure(result["flow_id"], user_input)
    assert result["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()
    data = entry.subentries[subentry_id].data
    assert "rocker_buttons" not in data and "wall_switch_settings" not in data
    assert (data["rocker_on_button"], data["rocker_off_button"]) == ("a0", "a1")
    assert (data["wall_switch"], data["wall_on_button"], data["wall_off_button"]) == (
        "FE-D8-12-35",
        "b0",
        "a1",
    )


@pytest.mark.parametrize(
    "gateway",
    [[_subentry("switch", "05-10-A2-B8", "Licht Flur", platform="light")]],
    indirect=True,
)
async def test_options_of_a_loaded_gateway(hass: HomeAssistant, gateway) -> None:
    """Saving the settings of a loaded gateway with devices reloads it once."""
    entry, server = gateway
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"message_delay": 20, "discovery": False}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    await server.connected.wait()
    assert entry.options["message_delay"] == 20 and entry.options["discovery"] is False
    assert entry.state is ConfigEntryState.LOADED

    # a receive-only actuator: switching it says why it cannot
    light = _entity(hass, "light", f"{BASE}_05-10-A2-B8_1_light")
    with pytest.raises(HomeAssistantError) as err:
        await hass.services.async_call("light", "turn_on", {"entity_id": light}, blocking=True)
    assert err.value.translation_key == "device_no_sender"


async def test_flow_rejects_bad_ids(hass: HomeAssistant, gateway) -> None:
    entry, _ = gateway
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "device"), context={"source": "user"}
    )
    result = await _choose_model(hass, result["flow_id"], "switch")
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"next_step_id": "device"}
    )
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            "name": "x",
            "device_id": "05-10-A2-B3",
            "sender_central": "FF-00-00-01",
            "platform": "light",
        },
    )
    assert result["errors"] == {"sender_central": "sender_out_of_range"}
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            "name": "x",
            "device_id": "nonsense",
            "sender_central": "FF-B7-44-81",
            "platform": "light",
        },
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
            _subentry(
                "rocker_contact",
                "00-31-00-01",
                "Garagentor",
                on_button="b0",
                off_button="released",
                device_class="garage_door",
            ),
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
    _push(server, 0x05, b"\x70", 0x00310001, 0x30)  # garage door contact: B0 = on
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
    rocker = hass.states.get(_entity(hass, "event", f"{BASE}_00-29-89-79_1_button_b0"))
    assert rocker.attributes["event_type"] == "pressed"
    registry = dr.async_get(hass)
    sensor = registry.async_get_device_by_identifier(
        (DOMAIN, f"{BASE}_01-82-0A-11"), entry.entry_id
    )
    assert sensor.via_device_id == entry.runtime_data.gateway_device_id
    assert registry.async_get(sensor.via_device_id).identifiers == {(DOMAIN, entry.entry_id)}
    assert state("binary_sensor", "00-31-00-01", "contact") == "on"
    _push(server, 0x05, b"\x00", 0x00310001, 0x20)  # release = off
    await _settle(hass)
    assert state("binary_sensor", "00-31-00-01", "contact") == "off"


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
    [
        [
            _subentry(
                "dimmer",
                "05-00-00-31",
                "Licht Wohnzimmer",
                senders=[{"profile": "central", "sender_id": "FF-B7-44-82"}],
            )
        ]
    ],
    indirect=True,
)
async def test_dimmer_and_teach_in(hass: HomeAssistant, gateway) -> None:
    _entry, server = gateway
    entity_id = _entity(hass, "light", f"{BASE}_05-00-00-31_1_light")
    _push(server, 0x07, bytes.fromhex("02320009"), 0x05000031)  # 50 %, on
    await _settle(hass)
    assert hass.states.get(entity_id).attributes["brightness"] == 128
    await hass.services.async_call("light", "turn_on", {"entity_id": entity_id, "brightness": 255})
    button = _entity(hass, "button", f"{BASE}_05-00-00-31_1_teach_in_central")
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
    result = await _choose_model(hass, result["flow_id"], "switch")
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"next_step_id": "device"}
    )
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            "name": "Licht",
            "device_id": "05-10-A2-B3",
            "sender_central": "FF-B7-44-82",
            "platform": "switch",
        },
    )
    await hass.async_block_till_done()
    subentry_id = next(iter(entry.subentries))
    assert hass.config_entries.async_remove_subentry(entry, subentry_id)
    await hass.async_block_till_done()
    pool = entry.runtime_data.senders.pool
    assert pool.get(0xFFB74482).state == "blocked"
    assert pool.next_free() == 0xFFB74481


@pytest.mark.parametrize(
    "gateway",
    [
        [
            _subentry(
                "cover",
                "05-00-00-22",
                "Jalousie",
                senders=[
                    {"profile": "controller", "sender_id": "FF-B7-44-91"},
                    {"profile": "direction_rocker", "sender_id": "FF-B7-44-92"},
                ],
                routing="direction_rocker",
                time_opens=20,
                time_closes=20,
            )
        ]
    ],
    indirect=True,
)
async def test_cover_with_controller_and_direction_rocker(hass: HomeAssistant, gateway) -> None:
    _entry, server = gateway
    entity_id = _entity(hass, "cover", f"{BASE}_05-00-00-22_1_cover")
    await hass.services.async_call("cover", "open_cover", {"entity_id": entity_id})
    await _settle(hass)
    received = bytes(server.received)
    controller_up = esp2.encode_radio(
        RadioTelegram(Rorg.BS4, bytes.fromhex("00160108"), 0xFFB74491)
    )
    rocker_up = esp2.encode_radio(RadioTelegram(Rorg.RPS, b"\x70", 0xFFB74492, 0x30))
    rocker_release = esp2.encode_radio(RadioTelegram(Rorg.RPS, b"\x00", 0xFFB74492, 0x20))
    # one sender moves it: the direction rocker, not the controller as well
    assert rocker_up in received and rocker_release in received
    assert controller_up not in received
    for key in ("controller", "direction_rocker"):
        assert _entity(hass, "button", f"{BASE}_05-00-00-22_1_teach_in_{key}")

    # the actuator stopped and reports its driven time: Stop no longer presses the rocker,
    # which would start the cover again
    _push(server, 0x07, bytes.fromhex("0064010A"), 0x05000022)  # drove 10.0 s up
    await _settle(hass)
    server.received.clear()
    await hass.services.async_call("cover", "stop_cover", {"entity_id": entity_id})
    await _settle(hass)
    assert rocker_up not in bytes(server.received)


@pytest.mark.parametrize(
    "gateway",
    [[_subentry("cover", "05-00-00-22", "Jalousie", routing="controller")]],
    indirect=True,
)
async def test_cover_automation_mode(hass: HomeAssistant, gateway) -> None:
    """Every cover has a mode for the user's own automations: Both until chosen otherwise."""
    entity_id = _entity(hass, "select", f"{BASE}_05-00-00-22_1_automation_mode")
    state = hass.states.get(entity_id)
    assert state is not None and state.state == "both"
    assert state.attributes["options"] == ["off", "morning", "evening", "both"]
    await hass.services.async_call(
        "select", "select_option", {"entity_id": entity_id, "option": "morning"}, blocking=True
    )
    assert hass.states.get(entity_id).state == "morning"


async def test_reconfigure_device(hass: HomeAssistant, gateway) -> None:
    entry, _ = gateway
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "device"), context={"source": "user"}
    )
    result = await _choose_model(hass, result["flow_id"], "cover")
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"next_step_id": "device"}
    )
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            "name": "Rollladen",
            "device_id": "05-00-00-23",
            "sender_controller": "FF-B7-44-81",
            "time_opens": 20,
            "time_closes": 21,
            "routing": "controller",
        },
    )
    await hass.async_block_till_done()
    subentry_id = next(iter(entry.subentries))
    result = await entry.start_subentry_reconfigure_flow(hass, subentry_id)
    assert result["step_id"] == "cover_menu"
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"next_step_id": "settings"}
    )
    assert result["step_id"] == "reconfigure"
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            "name": "Rollladen Büro",
            "sender_controller": "FF-B7-44-81",
            "sender_direction_rocker": "FF-B7-44-82",
            "time_opens": 25,
            "time_closes": 21,
            "routing": "direction_rocker",
        },
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()
    subentry = entry.subentries[subentry_id]
    assert subentry.title == "Rollladen Büro"
    assert subentry.data["senders"] == [
        {"profile": "controller", "sender_id": "FF-B7-44-81"},
        {"profile": "direction_rocker", "sender_id": "FF-B7-44-82"},
    ]
    assert subentry.data["time_opens"] == 25
    pool = entry.runtime_data.senders.pool
    assert pool.get(0xFFB74482).owner == "device:05-00-00-23:direction_rocker"

    # dropping the rocker blocks its ID until the teach-out is confirmed
    result = await entry.start_subentry_reconfigure_flow(hass, subentry_id)
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"next_step_id": "settings"}
    )
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            "name": "Rollladen Büro",
            "sender_controller": "FF-B7-44-81",
            "time_opens": 25,
            "time_closes": 21,
            "routing": "controller",
        },
    )
    await hass.async_block_till_done()
    assert entry.runtime_data.senders.pool.get(0xFFB74482).state == "blocked"


async def test_migrate_subentries_to_sender_list(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=BASE,
        version=1,
        minor_version=1,
        data={
            "model": "fam_usb",
            "device": {"type": "tcp", "host": "127.0.0.1", "port": 1},
            "base_id": BASE,
        },
        subentries_data=[
            ConfigSubentryData(
                data={
                    "schema": 1,
                    "model": "switch",
                    "device_id": "05-10-A2-B3",
                    "sender_id": "FF-B7-44-81",
                    "platform": "light",
                },
                subentry_type="device",
                title="Licht",
                unique_id="05-10-A2-B3",
            ),
            ConfigSubentryData(
                data={"schema": 1, "model": "contact", "device_id": "01-00-00-07"},
                subentry_type="device",
                title="Kontakt",
                unique_id="01-00-00-07",
            ),
        ],
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)  # retries: gateway offline
    await hass.async_block_till_done()
    assert entry.minor_version == EnOceanEltakoConfigFlow.MINOR_VERSION
    by_title = {s.title: s.data for s in entry.subentries.values()}
    assert by_title["Licht"]["senders"] == [{"profile": "central", "sender_id": "FF-B7-44-81"}]
    assert "sender_id" not in by_title["Licht"]
    assert "rocker_on_button" not in by_title["Licht"]  # no rocker sender
    assert by_title["Kontakt"]["schema"] == SUBENTRY_SCHEMA and "senders" not in by_title["Kontakt"]


async def test_migrate_rocker_buttons_explicit(hass: HomeAssistant) -> None:
    """1.3: devices with a rocker sender keep pressing B0/B1, the new default is A0/A1."""

    def device(model: str, device_id: str, profile: str, **extra) -> ConfigSubentryData:
        return ConfigSubentryData(
            data={
                "schema": 2,
                "model": model,
                "device_id": device_id,
                "senders": [{"profile": profile, "sender_id": "FF-B7-44-8F"}],
                **extra,
            },
            subentry_type="device",
            title=device_id,
            unique_id=device_id,
        )

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=BASE,
        version=1,
        minor_version=2,
        data={
            "model": "fam_usb",
            "device": {"type": "tcp", "host": "127.0.0.1", "port": 1},
            "base_id": BASE,
        },
        subentries_data=[
            device("switch", "05-10-A2-B3", "rocker"),
            device("switch", "05-10-A2-B4", "rocker", rocker_on_button="a0"),
            device("cover", "05-00-00-23", "direction_rocker"),
            device("switch", "05-10-A2-B5", "central"),
        ],
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)  # retries: gateway offline
    await hass.async_block_till_done()
    assert entry.minor_version == EnOceanEltakoConfigFlow.MINOR_VERSION
    data = {s.title: s.data for s in entry.subentries.values()}
    assert {k: data["05-10-A2-B3"][k] for k in ("rocker_on_button", "rocker_off_button")} == {
        "rocker_on_button": "b0",
        "rocker_off_button": "b1",
    }
    assert data["05-10-A2-B4"]["rocker_on_button"] == "a0"  # chosen ones stay
    assert data["05-00-00-23"]["rocker_off_button"] == "b1"
    assert "rocker_on_button" not in data["05-10-A2-B5"]
    assert all(d["schema"] == SUBENTRY_SCHEMA for d in data.values())


async def _start_device_flow(hass: HomeAssistant, entry, model: str):
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "device"), context={"source": "user"}
    )
    result = await _choose_model(hass, result["flow_id"], model)
    assert result["type"] is FlowResultType.MENU
    return result


async def test_learn_device_id_from_telegram(hass: HomeAssistant, gateway) -> None:
    entry, server = gateway
    result = await _start_device_flow(hass, entry, "contact")
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"next_step_id": "learn"}
    )
    assert result["type"] is FlowResultType.SHOW_PROGRESS
    _push(server, 0x05, b"\x70", 0x00298979, 0x30)  # RPS: wrong kind, ignored
    _push(server, 0x06, b"\x09", 0x01000099)  # 1BS contact
    await _settle(hass)
    result = await hass.config_entries.subentries.async_configure(result["flow_id"])
    assert result["step_id"] == "device"
    device_id = next(k for k in result["data_schema"].schema if k == "device_id")
    assert device_id.description["suggested_value"] == "01-00-00-99"


async def test_learn_timeout_offers_retry(hass: HomeAssistant, gateway, monkeypatch) -> None:
    from custom_components.enocean_eltako import subentry_flow

    monkeypatch.setattr(subentry_flow, "LEARN_TIMEOUT", 0.05)
    entry, _server = gateway
    result = await _start_device_flow(hass, entry, "contact")
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"next_step_id": "learn"}
    )
    await _settle(hass)
    result = await hass.config_entries.subentries.async_configure(result["flow_id"])
    assert result["step_id"] == "learn_timeout"
    assert result["menu_options"] == ["learn", "device", "kind"]


@pytest.fixture
async def esp3_gateway(hass: HomeAssistant, request):
    """MGW-ETH-like ESP3 gateway (VLD telegrams need ESP3)."""
    server = await FakeGateway(Protocol.ESP3, base_id=0xFF8A1B00).start()
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="PioTek MGW-ETH FF-8A-1B-00",
        unique_id="FF-8A-1B-00",
        data={
            "model": "mgw_eth",
            "device": {"type": "tcp", "host": "127.0.0.1", "port": server.port},
            "base_id": "FF-8A-1B-00",
        },
        options={"message_delay": 0},
        subentries_data=request.param,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    await server.connected.wait()
    yield entry, server
    await hass.config_entries.async_unload(entry.entry_id)
    await server.stop()


@pytest.mark.parametrize(
    "esp3_gateway",
    [
        [
            _subentry(
                "psc",
                "05-1A-2B-3C",
                "Zwischenstecker",
                senders=[{"profile": "controller", "sender_id": "FF-8A-1B-05"}],
                platform="switch",
            )
        ]
    ],
    indirect=True,
)
async def test_psc_switch_status_and_meter(hass: HomeAssistant, esp3_gateway) -> None:
    from custom_components.enocean_eltako.protocol import esp3

    _entry, server = esp3_gateway
    psc = 0x051A2B3C
    prefix = "FF-8A-1B-00_05-1A-2B-3C_1"
    server.push(esp3.encode_radio(RadioTelegram(0xD2, bytes.fromhex("0460E4"), psc)))
    server.push(esp3.encode_radio(RadioTelegram(Rorg.BS4, bytes.fromhex("00002A0C"), psc)))
    await _settle(hass)
    switch = _entity(hass, "switch", f"{prefix}_switch")
    assert hass.states.get(switch).state == "on"
    assert float(hass.states.get(_entity(hass, "sensor", f"{prefix}_power")).state) == 42
    await hass.services.async_call("switch", "turn_off", {"entity_id": switch})
    await _settle(hass)
    off = esp3.encode_radio(RadioTelegram(Rorg.BS4, bytes.fromhex("02000008"), 0xFF8A1B05))
    assert off in bytes(server.received)
    server.push(esp3.encode_radio(RadioTelegram(0xD2, bytes.fromhex("046080"), psc)))
    await _settle(hass)
    assert hass.states.get(switch).state == "off"


@pytest.mark.parametrize(
    "esp3_gateway",
    [[_subentry("psc", "01-90-8C-14", "Zwischenstecker", platform="switch")]],
    indirect=True,
)
async def test_psc_meter_from_vld_measurement(hass: HomeAssistant, esp3_gateway) -> None:
    """Telegrams recorded from a PSC234 at a MGW-ETH: D2-01 energy (Wh) and power (W) next to
    the A5-12-01 power telegram."""
    from custom_components.enocean_eltako.protocol import esp3

    _entry, server = esp3_gateway
    psc = 0x01908C14
    prefix = "FF-8A-1B-00_01-90-8C-14_1"

    def push(rorg: int, data: str) -> None:
        server.push(esp3.encode_radio(RadioTelegram(rorg, bytes.fromhex(data), psc)))

    # only the D2-01 power so far: it is the fallback for the power sensor
    push(0xD2, "07600000004C")
    await _settle(hass)
    power = _entity(hass, "sensor", f"{prefix}_power")
    energy = _entity(hass, "sensor", f"{prefix}_energy")
    assert float(hass.states.get(power).state) == 76

    push(0xD2, "0720000DE14D")  # 909 645 Wh
    push(Rorg.BS4, "0000470C")  # A5-12-01: 71 W
    await _settle(hass)
    assert float(hass.states.get(energy).state) == pytest.approx(909.645)
    assert float(hass.states.get(power).state) == 71

    # the A5-12-01 power wins now; a later D2-01 power does not make the state flap
    push(0xD2, "07600000004C")
    await _settle(hass)
    assert float(hass.states.get(power).state) == 71
    # the 10-minute A5 counter (0.1 kWh steps) does not override the finer D2-01 energy
    push(Rorg.BS4, "00238609")  # 9094 / 10 = 909.4 kWh
    await _settle(hass)
    assert float(hass.states.get(energy).state) == pytest.approx(909.645)


@pytest.mark.parametrize(
    "gateway",
    [[_subentry("room_controller", "05-00-00-41", "FUTH Bad")]],
    indirect=True,
)
async def test_room_controller_climate_is_read_only(hass: HomeAssistant, gateway) -> None:
    _entry, server = gateway
    _push(server, 0x07, bytes.fromhex("007F8009"), 0x05000041)
    await _settle(hass)
    state = hass.states.get(_entity(hass, "climate", f"{BASE}_05-00-00-41_1_climate"))
    assert state.state == "heat"
    assert state.attributes["temperature"] == pytest.approx(19.9, abs=0.1)
    assert state.attributes["current_temperature"] == pytest.approx(19.9, abs=0.2)
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "climate",
            "set_temperature",
            {"entity_id": state.entity_id, "temperature": 23},
            blocking=True,
        )


@pytest.fixture
def room_sensor(hass: HomeAssistant):
    hass.states.async_set("sensor.bad_temperatur", "20.0", {"device_class": "temperature"})


@pytest.mark.parametrize(
    "gateway",
    [
        [
            _subentry(
                "heating_actuator",
                "05-00-00-51",
                "Heizung Bad",
                senders=[{"profile": "controller", "sender_id": "FF-B7-44-A0"}],
                temperature_sensor="sensor.bad_temperatur",
                send_interval=60,
            )
        ]
    ],
    indirect=True,
)
async def test_heating_actuator_controlled_by_ha(hass: HomeAssistant, room_sensor, gateway) -> None:
    from datetime import timedelta

    from homeassistant.helpers import issue_registry as ir
    from homeassistant.util import dt as dt_util
    from pytest_homeassistant_custom_component.common import async_fire_time_changed

    from custom_components.enocean_eltako.protocol.eep.eltako import heating

    _entry, server = gateway
    entity_id = _entity(hass, "climate", f"{BASE}_05-00-00-51_1_climate")
    await _settle(hass)
    first = heating.encode_controller(21.0, 20.0)
    assert esp2.encode_radio(RadioTelegram(Rorg.BS4, first, 0xFFB744A0)) in bytes(server.received)

    await hass.services.async_call(
        "climate", "set_temperature", {"entity_id": entity_id, "temperature": 22.5}
    )
    await _settle(hass)
    sent = esp2.encode_radio(
        RadioTelegram(Rorg.BS4, heating.encode_controller(22.5, 20.0), 0xFFB744A0)
    )
    assert sent in bytes(server.received)

    _push(server, 0x05, b"\x70", 0x05000051, 0x30)  # actuator: normal operation
    await _settle(hass)
    assert hass.states.get(entity_id).attributes["hvac_action"] == "heating"
    mode = hass.states.get(_entity(hass, "sensor", f"{BASE}_05-00-00-51_1_heating_mode"))
    assert mode.state == "normal"

    await hass.services.async_call(
        "climate", "set_hvac_mode", {"entity_id": entity_id, "hvac_mode": "off"}
    )
    await _settle(hass)
    off = esp2.encode_radio(RadioTelegram(Rorg.BS4, heating.encode_controller(0, 20.0), 0xFFB744A0))
    assert off in bytes(server.received)
    assert not ir.async_get(hass).issues

    # the room sensor fails: nothing more is sent, the actuator falls back to its fault mode
    hass.states.async_set("sensor.bad_temperatur", "unavailable")
    server.received.clear()
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=61))
    await _settle(hass)
    assert hass.states.get(entity_id).attributes["current_temperature"] is None
    assert not server.received


@pytest.mark.parametrize(
    "gateway",
    [
        [
            _subentry(
                "heating_actuator",
                "05-00-00-53",
                "Heizung Flur",
                senders=[{"profile": "controller", "sender_id": "FF-B7-44-A3"}],
            )
        ]
    ],
    indirect=True,
)
async def test_heating_actuator_with_its_thermostat(hass: HomeAssistant, gateway) -> None:
    """Without a temperature entity: setpoint only, the room temperature from the actuator."""
    from custom_components.enocean_eltako.protocol.eep.eltako import heating

    _entry, server = gateway
    entity_id = _entity(hass, "climate", f"{BASE}_05-00-00-53_1_climate")
    await _settle(hass)
    setpoint_only = esp2.encode_radio(
        RadioTelegram(Rorg.BS4, bytes.fromhex("00860008"), 0xFFB744A3)  # 21 degC, DB1 = 0
    )
    assert setpoint_only in bytes(server.received)
    _push(server, 0x07, bytes.fromhex("0086820F"), 0x05000053)  # acknowledgement, 19.6 degC
    await _settle(hass)
    assert hass.states.get(entity_id).attributes["current_temperature"] == 19.6
    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": _entity(hass, "button", f"{BASE}_05-00-00-53_1_teach_in_controller")},
    )
    await _settle(hass)
    teach_in = esp2.encode_radio(RadioTelegram(Rorg.BS4, heating.TEACH_IN, 0xFFB744A3))
    assert heating.TEACH_IN.hex() == "40300d85"
    assert teach_in in bytes(server.received)


@pytest.mark.parametrize(
    "gateway",
    [
        [
            _subentry(
                "switch",
                "05-10-A2-B9",
                "Freigabe",
                senders=[{"profile": "central", "sender_id": "FF-B7-44-8B"}],
                platform="switch",
                invert=True,
            ),
            _subentry("window_handle", "00-21-63-44", "Fenster", invert=True),
        ]
    ],
    indirect=True,
)
async def test_inverted_switch_and_window_handle(hass: HomeAssistant, gateway) -> None:
    """Reversed relay logic: commands and state swapped; a window handle reads on = closed."""
    from custom_components.enocean_eltako.protocol.eep.eltako import switching

    _entry, server = gateway
    switch = _entity(hass, "switch", f"{BASE}_05-10-A2-B9_1_switch")
    await hass.services.async_call("switch", "turn_on", {"entity_id": switch})
    await _settle(hass)
    relay_off = RadioTelegram(Rorg.BS4, switching.encode_switch(False), 0xFFB7448B)
    assert esp2.encode_radio(relay_off) in bytes(server.received)
    _push(server, 0x05, b"\x50", 0x0510A2B9, 0x30)  # the relay reports off
    await _settle(hass)
    assert hass.states.get(switch).state == "on"
    _push(server, 0x05, b"\xf0", 0x00216344, 0x20)  # handle closed
    await _settle(hass)
    window = _entity(hass, "binary_sensor", f"{BASE}_00-21-63-44_1_window")
    assert hass.states.get(window).state == "on"


def test_heating_controller_telegram() -> None:
    from custom_components.enocean_eltako.protocol.eep.eltako import heating

    assert heating.encode_controller(20.0, 20.0).hex() == "00807f08"
    assert heating.encode_controller(20.0, 20.0, night_setback=2).hex() == "0c807f08"
    assert heating.decode_status(b"\x50") == {"mode": "night_setback"}
    assert heating.decode_status(bytes.fromhex("007F800F")) == {
        "setpoint": 19.9,
        "temperature": 19.9,
    }


@pytest.mark.parametrize(
    "gateway",
    [[_subentry("meter", "05-00-00-12", "Waschmaschine", unavailable_when_silent=True)]],
    indirect=True,
)
async def test_last_seen_and_silence_repair(hass: HomeAssistant, gateway, monkeypatch) -> None:
    import time as time_module

    from homeassistant.helpers import issue_registry as ir

    from custom_components.enocean_eltako import health

    entry, server = gateway
    prefix = f"{BASE}_05-00-00-12_1"
    _push(server, 0x07, bytes.fromhex("0003E80C"), 0x05000012)
    await _settle(hass)
    last_seen = er.async_get(hass).async_get(_entity(hass, "sensor", f"{prefix}_last_seen"))
    assert last_seen.disabled_by is er.RegistryEntryDisabler.INTEGRATION  # logbook noise
    device = next(iter(entry.runtime_data.devices.values()))
    assert device.stats.telegrams == 1 and device.stats.last_seen is not None
    power = _entity(hass, "sensor", f"{prefix}_power")

    later = time_module.time() + 3 * 600 + 60
    monkeypatch.setattr(health.time, "time", lambda: later)
    entry.runtime_data.health_check()
    await hass.async_block_till_done()
    issue = ir.async_get(hass).async_get_issue(DOMAIN, f"device_silent_{BASE}_05-00-00-12")
    assert issue is not None and issue.translation_key == "device_silent"
    assert hass.states.get(power).state == "unavailable"

    _push(server, 0x07, bytes.fromhex("0003E70C"), 0x05000012)  # heard again: 999 W
    await _settle(hass)
    assert float(hass.states.get(power).state) == 999
    monkeypatch.undo()
    entry.runtime_data.health_check()
    await hass.async_block_till_done()
    assert ir.async_get(hass).async_get_issue(DOMAIN, f"device_silent_{BASE}_05-00-00-12") is None


@pytest.mark.parametrize(
    "esp3_gateway",
    [[_subentry("temp_humidity", "01-82-0A-11", "FAFT")]],
    indirect=True,
)
async def test_rssi_from_esp3(hass: HomeAssistant, esp3_gateway) -> None:
    from custom_components.enocean_eltako.protocol import esp3

    _entry, server = esp3_gateway
    data = bytes.fromhex("A5007D7D08") + (0x01820A11).to_bytes(4, "big") + b"\x01"
    for dbm in (0x2D, 0x40):
        optional = bytes.fromhex("01FFFFFFFF") + bytes([dbm]) + b"\x00"
        server.push(esp3.Esp3Packet(esp3.PacketType.RADIO_ERP1, data, optional).encode())
        await asyncio.sleep(0.25)  # beyond the dispatcher's duplicate window
    await _settle(hass)
    unique = "FF-8A-1B-00_01-82-0A-11_1_rssi"
    entity_id = _entity(hass, "sensor", unique)
    er.async_get(hass).async_update_entity(entity_id, disabled_by=None)
    device = next(iter(_entry.runtime_data.devices.values()))
    assert device.stats.rssi == -64
    assert (device.stats.rssi_min, device.stats.rssi_max) == (-64, -45)
    assert device.stats.repeat_count == 1


@pytest.mark.parametrize(
    "gateway",
    [
        [
            _subentry(
                "switch",
                "05-00-00-61",
                "Licht FL62",
                platform="light",
                status_request=True,
                senders=[{"profile": "central", "sender_id": "FF-B7-44-B0"}],
            )
        ]
    ],
    indirect=True,
)
async def test_state_request_and_assumed_state(hass: HomeAssistant, gateway) -> None:
    _entry, server = gateway
    await _settle(hass)
    query = esp2.encode_radio(RadioTelegram(Rorg.BS4, bytes.fromhex("00000008"), 0xFFB744B0))
    assert query in bytes(server.received)
    entity_id = _entity(hass, "light", f"{BASE}_05-00-00-61_1_light")
    assert hass.states.get(entity_id).attributes.get("assumed_state") is True
    _push(server, 0x05, b"\x50", 0x05000061, 0x30)
    await _settle(hass)
    state = hass.states.get(entity_id)
    assert state.state == "off"
    assert "assumed_state" not in state.attributes


@pytest.mark.parametrize(
    "gateway",
    [[_subentry("rocker", "00-29-89-80", "NodOn", long_press=0.2, double_press=0.1)]],
    indirect=True,
)
async def test_rocker_gestures_and_device_triggers(hass: HomeAssistant, gateway) -> None:
    from homeassistant.helpers import device_registry as dr

    from custom_components.enocean_eltako.device_trigger import async_get_triggers

    entry, server = gateway
    events: list[tuple[str, str]] = []
    hass.bus.async_listen(
        "enocean_eltako_button", lambda e: events.append((e.data["button"], e.data["type"]))
    )
    rocker = 0x00298980

    async def tap(data: bytes, hold: float = 0.0) -> None:
        _push(server, 0x05, data, rocker, 0x30)
        await asyncio.sleep(hold or 0.02)
        _push(server, 0x05, b"\x00", rocker, 0x20)
        await asyncio.sleep(0.02)

    await tap(b"\x70")  # B0 short
    await asyncio.sleep(0.2)
    await tap(b"\x30", hold=0.3)  # A0 long
    await tap(b"\x50")  # B1 double
    await tap(b"\x50")
    await asyncio.sleep(0.2)
    await hass.async_block_till_done()
    assert ("b0", "short_press") in events
    assert ("a0", "long_press") in events
    assert ("b1", "double_press") in events
    assert ("b1", "short_press") not in events
    state = hass.states.get(_entity(hass, "event", f"{BASE}_00-29-89-80_1_button_b1"))
    assert state.attributes["event_type"] == "double_press"

    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, f"{BASE}_00-29-89-80"), entry.entry_id
    )
    triggers = await async_get_triggers(hass, device.id)
    assert {"type": "long_press", "subtype": "a0"}.items() <= next(
        t for t in triggers if t["type"] == "long_press" and t["subtype"] == "a0"
    ).items()
    assert len(triggers) == 4 * 6


@pytest.mark.parametrize(
    "gateway", [[_subentry("meter", "05-00-00-13", "Proxon TWWP")]], indirect=True
)
async def test_meter_tariffs_total_and_backward_jump(hass: HomeAssistant, gateway) -> None:
    _entry, server = gateway
    meter = 0x05000013
    prefix = f"{BASE}_05-00-00-13_1"
    registry = er.async_get(hass)
    for key in ("energy_tariff_1", "energy_total"):
        registry.async_update_entity(_entity(hass, "sensor", f"{prefix}_{key}"), disabled_by=None)
    server.connected.clear()  # wait for the connection of the reloaded entry
    await hass.config_entries.async_reload(_entry.entry_id)
    await hass.async_block_till_done()
    await server.connected.wait()

    async def send(data: str) -> None:
        _push(server, 0x07, bytes.fromhex(data), meter)
        await asyncio.sleep(0.25)

    await send("00100009")  # day tariff 409.6 kWh
    await send("00010019")  # night tariff 25.6 kWh
    await send("000FFF09")  # backwards: dropped
    await _settle(hass)

    def value(key: str) -> float:
        return float(hass.states.get(_entity(hass, "sensor", f"{prefix}_{key}")).state)

    assert value("energy") == pytest.approx(409.6)
    assert value("energy_tariff_1") == pytest.approx(25.6)
    assert value("energy_total") == pytest.approx(435.2)


@pytest.mark.parametrize(
    "gateway",
    [
        [
            _subentry(
                "cover",
                "05-00-00-24",
                "Rollladen Bad",
                senders=[{"profile": "controller", "sender_id": "FF-B7-44-93"}],
                time_opens=20,
                time_closes=20,
                calibration="before_move",
            )
        ]
    ],
    indirect=True,
)
async def test_cover_calibrates_before_uncertain_move(hass: HomeAssistant, gateway) -> None:
    _entry, server = gateway
    entity_id = _entity(hass, "cover", f"{BASE}_05-00-00-24_1_cover")
    accuracy = _entity(hass, "sensor", f"{BASE}_05-00-00-24_1_position_accuracy")
    _push(server, 0x07, bytes.fromhex("0064020A"), 0x05000024)  # 10 s down, position unknown
    await _settle(hass)
    cover = _entry.runtime_data.devices[next(iter(_entry.runtime_data.devices))].cover_entity
    cover.position.position = 50  # pretend a vague position
    assert cover.position.inaccuracy > 10

    task = hass.async_create_task(
        hass.services.async_call(
            "cover", "set_cover_position", {"entity_id": entity_id, "position": 75}, blocking=True
        )
    )
    await asyncio.sleep(0.1)  # not block_till_done: the move waits for the anchor
    full_up = esp2.encode_radio(RadioTelegram(Rorg.BS4, bytes.fromhex("00160108"), 0xFFB74493))
    assert full_up in bytes(server.received)
    _push(server, 0x07, bytes.fromhex("00DC010A"), 0x05000024)  # FSB: drove 22 s up
    await asyncio.wait_for(task, 5)
    await _settle(hass)
    down_5s = esp2.encode_radio(RadioTelegram(Rorg.BS4, bytes.fromhex("00050208"), 0xFFB74493))
    assert down_5s in bytes(server.received)
    assert float(hass.states.get(accuracy).state) == 0
    assert hass.states.get(entity_id).attributes["last_calibrated"] is not None

    calibrate = hass.async_create_task(
        hass.services.async_call(
            "enocean_eltako", "calibrate_cover", {"entity_id": entity_id}, blocking=True
        )
    )
    await asyncio.sleep(0.3)  # beyond the duplicate window of the last identical report
    _push(server, 0x07, bytes.fromhex("00DC010A"), 0x05000024)  # nearer end: up again
    await asyncio.wait_for(calibrate, 5)

    # the button: the run goes on after the press, bound to the entry
    server.received.clear()
    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": _entity(hass, "button", f"{BASE}_05-00-00-24_1_calibrate")},
        blocking=True,
    )
    await asyncio.sleep(0.1)
    assert full_up in bytes(server.received)
    await hass.config_entries.async_unload(_entry.entry_id)  # cancels the waiting run


@pytest.mark.parametrize(
    "gateway",
    [
        [
            _subentry(
                "cover",
                "05-00-00-26",
                "Rollladen Gaube",
                senders=[{"profile": "controller", "sender_id": "FF-B7-44-95"}],
                time_opens=15.3,
                time_closes=15.3,
            )
        ]
    ],
    indirect=True,
)
async def test_cover_full_run_rounds_up(hass: HomeAssistant, gateway) -> None:
    """15.3 s travel + 2 s margin: 18 s, not 17 s, so the reported driven time anchors."""
    _entry, server = gateway
    cover = _entity(hass, "cover", f"{BASE}_05-00-00-26_1_cover")
    await hass.services.async_call("cover", "open_cover", {"entity_id": cover})
    await _settle(hass)
    up = esp2.encode_radio(RadioTelegram(Rorg.BS4, bytes.fromhex("00120108"), 0xFFB74495))
    assert up in bytes(server.received)
    _push(server, 0x07, bytes.fromhex("00B4010A"), 0x05000026)  # drove 18.0 s up
    await _settle(hass)
    state = hass.states.get(cover)
    assert (state.attributes["current_position"], state.attributes["inaccuracy"]) == (100, 0)


@pytest.mark.parametrize(
    "gateway",
    [
        [
            _subentry(
                "cover",
                "05-00-00-25",
                "Rollladen Gast",
                senders=[{"profile": "controller", "sender_id": "FF-B7-44-94"}],
                time_opens=30,
                time_closes=30,
            )
        ]
    ],
    indirect=True,
)
async def test_travel_time_assistant_gateway_reloaded(hass: HomeAssistant, gateway) -> None:
    """The entry reloads while measuring: the flow stops with a hint instead of an error."""
    entry, server = gateway
    subentry_id = next(iter(entry.subentries))
    result = await entry.start_subentry_reconfigure_flow(hass, subentry_id)
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"next_step_id": "measure"}
    )
    result = await hass.config_entries.subentries.async_configure(result["flow_id"], {})
    await asyncio.sleep(0.05)
    _push(server, 0x05, b"\x70", 0x05000025, 0x30)  # upper end reached
    await asyncio.sleep(0.05)
    result = await hass.config_entries.subentries.async_configure(result["flow_id"])
    assert result["step_id"] == "measure_down"
    await hass.config_entries.async_unload(entry.entry_id)
    result = await hass.config_entries.subentries.async_configure(result["flow_id"], {})
    assert result["reason"] == "measure_interrupted"


@pytest.mark.parametrize(
    "gateway",
    [
        [
            _subentry(
                "cover",
                "05-00-00-25",
                "Rollladen Gast",
                senders=[{"profile": "controller", "sender_id": "FF-B7-44-94"}],
                time_opens=30,
                time_closes=30,
            )
        ]
    ],
    indirect=True,
)
async def test_travel_time_assistant(hass: HomeAssistant, gateway) -> None:
    entry, server = gateway
    actuator = 0x05000025
    subentry_id = next(iter(entry.subentries))
    result = await entry.start_subentry_reconfigure_flow(hass, subentry_id)
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"next_step_id": "measure"}
    )
    assert result["step_id"] == "measure"
    result = await hass.config_entries.subentries.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.SHOW_PROGRESS
    await asyncio.sleep(0.05)
    _push(server, 0x05, b"\x70", actuator, 0x30)  # upper end reached
    await asyncio.sleep(0.05)
    result = await hass.config_entries.subentries.async_configure(result["flow_id"])
    assert result["step_id"] == "measure_down"
    await asyncio.sleep(0.05)
    down = esp2.encode_radio(RadioTelegram(Rorg.BS4, bytes.fromhex("00780208"), 0xFFB74494))
    assert down in bytes(server.received)  # down for up to 120 s

    async def click_and_report(report: str):
        flow = hass.async_create_task(
            hass.config_entries.subentries.async_configure(result["flow_id"], {})
        )
        await asyncio.sleep(0.05)
        _push(server, 0x07, bytes.fromhex(report), actuator)
        return await flow

    result = await click_and_report("00E6020A")  # drove 23.0 s down
    assert result["step_id"] == "measure_up"
    result = await click_and_report("00FA010A")  # drove 25.0 s up
    assert result["step_id"] == "measure_extra"
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"measure_extra": "none"}
    )
    assert result["step_id"] == "measure_result"
    assert result["description_placeholders"] == {
        "time_opens": "25.0",
        "time_closes": "23.0",
        "vent_time": "–",
        "tilt_time": "–",
    }
    result = await hass.config_entries.subentries.async_configure(result["flow_id"], {})
    assert result["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()
    data = entry.subentries[subentry_id].data
    assert (data["time_opens"], data["time_closes"]) == (25.0, 23.0)


@pytest.mark.parametrize(
    "gateway",
    [
        [
            _subentry(
                "cover",
                "05-00-00-26",
                "Rollladen Küche",
                senders=[{"profile": "controller", "sender_id": "FF-B7-44-95"}],
                time_opens=30,
                time_closes=30,
            )
        ]
    ],
    indirect=True,
)
async def test_travel_time_assistant_measures_vent_slots(hass: HomeAssistant, gateway) -> None:
    entry, server = gateway
    actuator = 0x05000026
    subentry_id = next(iter(entry.subentries))
    configure = hass.config_entries.subentries.async_configure
    result = await entry.start_subentry_reconfigure_flow(hass, subentry_id)
    result = await configure(result["flow_id"], {"next_step_id": "measure"})
    result = await configure(result["flow_id"], {})
    await asyncio.sleep(0.05)
    _push(server, 0x05, b"\x70", actuator, 0x30)  # upper end reached
    await asyncio.sleep(0.05)
    result = await configure(result["flow_id"])
    assert result["step_id"] == "measure_down"

    async def click_and_report(report: str):
        flow = hass.async_create_task(configure(result["flow_id"], {}))
        await asyncio.sleep(0.05)
        _push(server, 0x07, bytes.fromhex(report), actuator)
        return await flow

    result = await click_and_report("00E6020A")  # 23.0 s down
    result = await click_and_report("00FA010A")  # 25.0 s up
    assert result["step_id"] == "measure_extra"
    result = await configure(result["flow_id"], {"measure_extra": "vent_time"})
    assert result["type"] is FlowResultType.SHOW_PROGRESS  # closing fully
    await asyncio.sleep(0.05)
    _push(server, 0x05, b"\x50", actuator, 0x30)  # lower end reached
    await asyncio.sleep(0.05)
    result = await configure(result["flow_id"])
    assert result["step_id"] == "measure_vent"
    result = await click_and_report("0028010A")  # 4.0 s up: slots open
    assert result["step_id"] == "measure_result"
    assert result["description_placeholders"]["vent_time"] == "4.0 s"
    result = await configure(result["flow_id"], {})
    assert result["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()
    assert entry.subentries[subentry_id].data["vent_time"] == 4.0


@pytest.mark.parametrize(
    "gateway",
    [
        [
            _subentry(
                "cover",
                "05-00-00-27",
                "Rollladen Flur",
                senders=[{"profile": "controller", "sender_id": "FF-B7-44-96"}],
                time_opens=20,
                time_closes=20,
            )
        ]
    ],
    indirect=True,
)
async def test_calibrate_only_if_inaccurate(hass: HomeAssistant, gateway) -> None:
    entry, server = gateway
    entity_id = _entity(hass, "cover", f"{BASE}_05-00-00-27_1_cover")
    cover = entry.runtime_data.devices[next(iter(entry.runtime_data.devices))].cover_entity
    full_up = esp2.encode_radio(RadioTelegram(Rorg.BS4, bytes.fromhex("00160108"), 0xFFB74496))
    full_down = esp2.encode_radio(RadioTelegram(Rorg.BS4, bytes.fromhex("00160208"), 0xFFB74496))

    cover.position.anchor(30)  # exact: skipped
    sent = len(server.received)
    await hass.services.async_call(
        "enocean_eltako",
        "calibrate_cover",
        {"entity_id": entity_id, "only_if_inaccurate": True},
        blocking=True,
    )
    assert len(server.received) == sent

    cover.position.position = None  # unknown: calibrated, towards the open end, never closed
    cover.position.inaccuracy = 100
    task = hass.async_create_task(
        hass.services.async_call(
            "enocean_eltako",
            "calibrate_cover",
            {"entity_id": entity_id, "only_if_inaccurate": True},
            blocking=True,
        )
    )
    await asyncio.sleep(0.1)
    assert full_up in bytes(server.received)
    assert full_down not in bytes(server.received)
    _push(server, 0x07, bytes.fromhex("00DC010A"), 0x05000027)  # FSB: drove 22 s up
    await asyncio.wait_for(task, 5)


async def _init_flow(hass: HomeAssistant, entry):
    return await hass.config_entries.subentries.async_init(
        (entry.entry_id, "device"), context={"source": "user"}
    )


async def test_add_device_menus(hass: HomeAssistant, gateway) -> None:
    entry, _server = gateway
    configure = hass.config_entries.subentries.async_configure
    result = await _init_flow(hass, entry)
    assert result["menu_options"] == ["learn", "eltako", "enocean", "virtual", "eep"]
    eltako = await configure(result["flow_id"], {"next_step_id": "eltako"})
    assert eltako["menu_options"] == [
        "eltako_lighting",
        "eltako_covers",
        "eltako_climate",
        "eltako_buttons",
        "eltako_sensors",
        "eltako_meters",
        "user",
    ]
    result = await configure(eltako["flow_id"], {"next_step_id": "eltako_buttons"})
    assert result["step_id"] == "kind"
    assert result["menu_options"] == [
        "model_window_handle",
        "model_contact",
        "model_rocker",
        "model_rocker_contact",
        "model_digital_input",
        "model_digital_inputs",
        "eltako",
    ]

    # only one kind in the category: straight to the address
    result = await _init_flow(hass, entry)
    result = await configure(result["flow_id"], {"next_step_id": "enocean"})
    assert result["menu_options"] == [
        "enocean_lighting",
        "enocean_covers",
        "enocean_buttons",
        "user",
    ]
    result = await configure(result["flow_id"], {"next_step_id": "enocean_covers"})
    assert result["step_id"] == "address"


async def test_learn_first_suggests_the_kind(hass: HomeAssistant, gateway) -> None:
    entry, server = gateway
    configure = hass.config_entries.subentries.async_configure
    result = await _init_flow(hass, entry)
    result = await configure(result["flow_id"], {"next_step_id": "learn"})
    assert result["type"] is FlowResultType.SHOW_PROGRESS
    _push(server, 0x06, b"\x09", 0x01000099)  # 1BS contact
    await _settle(hass)
    result = await configure(result["flow_id"])
    assert result["step_id"] == "learned"
    assert result["description_placeholders"]["device_id"] == "01-00-00-99"
    options = result["data_schema"].schema["model"].config["options"]
    assert options == ["contact", "enocean_contact"]
    result = await configure(result["flow_id"], {"model": "contact"})
    assert result["step_id"] == "device"
    device_id = next(k for k in result["data_schema"].schema if k == "device_id")
    assert device_id.description["suggested_value"] == "01-00-00-99"


async def test_learn_first_single_fit_skips_the_choice(hass: HomeAssistant, gateway) -> None:
    entry, server = gateway
    configure = hass.config_entries.subentries.async_configure
    result = await _init_flow(hass, entry)
    result = await configure(result["flow_id"], {"next_step_id": "learn"})
    # 4BS teach-in A5-04-02 from Eltako: only the temperature/humidity entry decodes it
    _push(server, 0x07, encode_teach_in_4bs("A5-04-02"), 0x01820A11)
    await _settle(hass)
    result = await configure(result["flow_id"])
    assert result["step_id"] == "device"
    assert "A5-04-02:std" in result["description_placeholders"]["receive"]


async def test_add_generic_device_by_eep(hass: HomeAssistant, gateway) -> None:
    entry, server = gateway
    configure = hass.config_entries.subentries.async_configure
    result = await _init_flow(hass, entry)
    result = await configure(result["flow_id"], {"next_step_id": "eep"})
    assert result["step_id"] == "eep"
    result = await configure(result["flow_id"], {"eep": "std_a5_04_02"})
    result = await configure(result["flow_id"], {"next_step_id": "device"})
    result = await configure(result["flow_id"], {"name": "Fremdsensor", "device_id": "05-11-22-33"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    subentry = next(s for s in entry.subentries.values() if s.title == "Fremdsensor")
    assert subentry.data["model"] == "eep"
    assert subentry.data["eep"] == "A5-04-02:std"
    await hass.async_block_till_done()

    _push(server, 0x07, bytes.fromhex("007D7D08"), 0x05112233)
    await _settle(hass)
    prefix = f"{BASE}_05-11-22-33_1"
    temperature = hass.states.get(_entity(hass, "sensor", f"{prefix}_eep_tmp"))
    humidity = hass.states.get(_entity(hass, "sensor", f"{prefix}_eep_hum"))
    assert float(temperature.state) == 20.0
    assert temperature.attributes["unit_of_measurement"] == "°C"
    assert float(humidity.state) == 50.0
    assert _entity(hass, "sensor", f"{prefix}_eep_lrnb") is None


async def test_any_standard_profile_by_typed_code(hass: HomeAssistant, gateway) -> None:
    """Phase 5: every standard profile can be added; a typed code is accepted."""
    entry, server = gateway
    configure = hass.config_entries.subentries.async_configure
    result = await _init_flow(hass, entry)
    result = await configure(result["flow_id"], {"next_step_id": "eep"})
    options = {o["value"] for o in result["data_schema"].schema["eep"].config["options"]}
    assert {"std_a5_04_02", "std_a5_02_05", "std_d2_14_41", "eltako_m5_38_08"} <= options
    result = await configure(result["flow_id"], {"eep": "zz-99"})
    assert result["errors"] == {"eep": "unknown_eep"}
    result = await configure(result["flow_id"], {"eep": "a5 02 05"})
    result = await configure(result["flow_id"], {"next_step_id": "device"})
    result = await configure(result["flow_id"], {"name": "Fühler", "device_id": "05-11-22-44"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["eep"] == "A5-02-05:std"
    await hass.async_block_till_done()

    _push(server, 0x07, bytes.fromhex("00007608"), 0x05112244)
    await _settle(hass)
    temperature = hass.states.get(_entity(hass, "sensor", f"{BASE}_05-11-22-44_1_eep_tmp"))
    assert float(temperature.state) == pytest.approx(21.49, abs=0.01)


async def test_eltako_eep_opens_the_catalog_entry(hass: HomeAssistant, gateway) -> None:
    entry, _server = gateway
    configure = hass.config_entries.subentries.async_configure
    result = await _init_flow(hass, entry)
    result = await configure(result["flow_id"], {"next_step_id": "eep"})
    result = await configure(result["flow_id"], {"eep": "eltako_g5_3f_7f"})
    result = await configure(result["flow_id"], {"next_step_id": "device"})
    assert result["description_placeholders"]["receive"] == "G5-3F-7F:eltako"
    assert "time_opens" in result["data_schema"].schema


async def test_learn_first_timeout_offers_the_catalog(
    hass: HomeAssistant, gateway, monkeypatch
) -> None:
    from custom_components.enocean_eltako import subentry_flow

    monkeypatch.setattr(subentry_flow, "LEARN_TIMEOUT", 0.05)
    entry, _server = gateway
    result = await _init_flow(hass, entry)
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"next_step_id": "learn"}
    )
    await _settle(hass)
    result = await hass.config_entries.subentries.async_configure(result["flow_id"])
    assert result["step_id"] == "learn_timeout"
    assert result["menu_options"] == ["learn", "eltako", "enocean", "virtual", "eep"]


async def test_back_entries_return_to_the_previous_menu(hass: HomeAssistant, gateway) -> None:
    entry, _server = gateway
    configure = hass.config_entries.subentries.async_configure
    result = await _init_flow(hass, entry)
    flow_id = result["flow_id"]
    result = await configure(flow_id, {"next_step_id": "eltako"})
    result = await configure(flow_id, {"next_step_id": "eltako_buttons"})
    result = await configure(flow_id, {"next_step_id": "model_rocker"})
    assert result["menu_options"] == ["learn", "device", "kind"]
    result = await configure(flow_id, {"next_step_id": "kind"})  # back to the kinds
    assert result["step_id"] == "kind"
    result = await configure(flow_id, {"next_step_id": "eltako"})  # back to the categories
    assert result["step_id"] == "eltako"
    result = await configure(flow_id, {"next_step_id": "user"})  # back to the start
    assert result["menu_options"] == ["learn", "eltako", "enocean", "virtual", "eep"]
    # a single kind goes straight to the address; back leads to the categories
    result = await configure(flow_id, {"next_step_id": "enocean"})
    result = await configure(flow_id, {"next_step_id": "enocean_covers"})
    assert result["menu_options"] == ["learn", "device", "enocean"]
    # by EEP: back to the profile choice
    result = await configure(flow_id, {"next_step_id": "enocean"})
    result = await configure(flow_id, {"next_step_id": "user"})
    result = await configure(flow_id, {"next_step_id": "eep"})
    result = await configure(flow_id, {"eep": "std_a5_04_02"})
    result = await configure(flow_id, {"next_step_id": "eep"})
    assert result["step_id"] == "eep"


@pytest.mark.parametrize(
    "gateway",
    [[_subentry("switch", "05-00-00-31", "Steckdose", platform="switch")]],
    indirect=True,
)
async def test_type_change_removes_the_old_entity(hass: HomeAssistant, gateway) -> None:
    entry, _server = gateway
    registry = er.async_get(hass)
    unique_id = f"{BASE}_05-00-00-31_1_light"
    registry.async_get_or_create("light", DOMAIN, unique_id, config_entry=entry)
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert registry.async_get_entity_id("light", DOMAIN, unique_id) is None
    assert _entity(hass, "switch", f"{BASE}_05-00-00-31_1_switch") is not None


@pytest.mark.parametrize(
    "gateway",
    [[_subentry("psc", "FF-85-EF-81", "Zwischenstecker", platform="switch")]],
    indirect=True,
)
async def test_psc_state_over_fam_usb(hass: HomeAssistant, gateway) -> None:
    """FAM-USB passes the PSC's D2-01-09 status as ESP2 ORG 0xD2."""
    _entry, server = gateway
    switch = _entity(hass, "switch", f"{BASE}_FF-85-EF-81_1_switch")
    _push(server, 0xD2, bytes.fromhex("0460E400"), 0xFF85EF81)
    await _settle(hass)
    assert hass.states.get(switch).state == "on"
    _push(server, 0xD2, bytes.fromhex("04608000"), 0xFF85EF81)
    await _settle(hass)
    assert hass.states.get(switch).state == "off"


@pytest.mark.parametrize(
    "gateway", [[_subentry("contact", "01-00-00-07", "Fenster")]], indirect=True
)
async def test_enocean_id_sensor(hass: HomeAssistant, gateway) -> None:
    entry, _server = gateway
    registry = er.async_get(hass)
    entity_id = _entity(hass, "sensor", f"{BASE}_01-00-00-07_1_enocean_id")
    assert registry.async_get(entity_id).disabled_by is er.RegistryEntryDisabler.INTEGRATION
    registry.async_update_entity(entity_id, disabled_by=None)
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "01-00-00-07"


@pytest.mark.parametrize(
    "gateway",
    [
        [
            _subentry(
                "switch",
                "05-00-00-32",
                "Licht",
                senders=[
                    {"profile": "central", "sender_id": "FF-B7-44-81"},
                    {"profile": "rocker", "sender_id": "FF-B7-44-82"},
                ],
            )
        ]
    ],
    indirect=True,
)
async def test_sender_id_sensors(hass: HomeAssistant, gateway) -> None:
    prefix = f"{BASE}_05-00-00-32_1"
    central = hass.states.get(_entity(hass, "sensor", f"{prefix}_sender_id_central"))
    rocker = hass.states.get(_entity(hass, "sensor", f"{prefix}_sender_id_rocker"))
    assert central.state == "FF-B7-44-81"
    assert rocker.state == "FF-B7-44-82"


@pytest.mark.parametrize(
    "gateway",
    [
        [
            _subentry(
                "switch",
                "05-00-00-33",
                "Flur",
                senders=[{"profile": "central", "sender_id": "FF-B7-44-83"}],
            )
        ]
    ],
    indirect=True,
)
async def test_removed_sender_profile_drops_its_entities(hass: HomeAssistant, gateway) -> None:
    entry, _server = gateway
    registry = er.async_get(hass)
    prefix = f"{BASE}_05-00-00-33_1"
    registry.async_get_or_create("sensor", DOMAIN, f"{prefix}_sender_id_rocker", config_entry=entry)
    registry.async_get_or_create("button", DOMAIN, f"{prefix}_teach_in_rocker", config_entry=entry)
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert registry.async_get_entity_id("sensor", DOMAIN, f"{prefix}_sender_id_rocker") is None
    assert registry.async_get_entity_id("button", DOMAIN, f"{prefix}_teach_in_rocker") is None
    assert _entity(hass, "sensor", f"{prefix}_sender_id_central") is not None


@pytest.mark.parametrize(
    "gateway",
    [
        [
            _subentry("water_meter", "05-00-00-13", "Wasser"),
            _subentry("gas_meter", "05-00-00-14", "Gas"),
        ]
    ],
    indirect=True,
)
async def test_gas_and_water_meters(hass: HomeAssistant, gateway) -> None:
    _entry, server = gateway
    _push(server, 0x07, bytes.fromhex("00303909"), 0x05000013)  # 1234.5 m3
    _push(server, 0x07, bytes.fromhex("00000F0D"), 0x05000013)  # 1.5 l/s
    _push(server, 0x07, bytes.fromhex("0000648F"), 0x05000014)  # serial number telegram: dropped
    await _settle(hass)
    water = f"{BASE}_05-00-00-13_1"
    assert float(hass.states.get(_entity(hass, "sensor", f"{water}_volume")).state) == 1234.5
    assert float(hass.states.get(_entity(hass, "sensor", f"{water}_flow")).state) == 1.5
    gas = hass.states.get(_entity(hass, "sensor", f"{BASE}_05-00-00-14_1_volume"))
    assert gas.state == "unknown"
    assert gas.attributes["device_class"] == "gas"


async def test_generic_device_shows_chosen_fields(hass: HomeAssistant, gateway) -> None:
    entry, server = gateway
    configure = hass.config_entries.subentries.async_configure
    result = await _init_flow(hass, entry)
    result = await configure(result["flow_id"], {"next_step_id": "eep"})
    result = await configure(result["flow_id"], {"eep": "std_a5_04_02"})
    result = await configure(result["flow_id"], {"next_step_id": "device"})
    options = result["data_schema"].schema["fields"].config["options"]
    assert [o["value"] for o in options] == ["eep_hum", "eep_tmp", "eep_tsn"]
    result = await configure(
        result["flow_id"],
        {"name": "Nur Temperatur", "device_id": "05-11-22-34", "fields": ["eep_tmp"]},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    prefix = f"{BASE}_05-11-22-34_1"
    assert _entity(hass, "sensor", f"{prefix}_eep_tmp") is not None
    assert _entity(hass, "sensor", f"{prefix}_eep_hum") is None


@pytest.mark.parametrize(
    "gateway",
    [
        [
            _subentry(
                "heating_actuator",
                "05-00-00-52",
                "Heizung Wohnen",
                senders=[
                    {"profile": "controller", "sender_id": "FF-B7-44-A1"},
                    {"profile": "cooling", "sender_id": "FF-B7-44-A2"},
                ],
                temperature_sensor="sensor.bad_temperatur",
                send_interval=60,
            )
        ]
    ],
    indirect=True,
)
async def test_heating_actuator_cooling(hass: HomeAssistant, room_sensor, gateway) -> None:
    _entry, server = gateway
    entity_id = _entity(hass, "climate", f"{BASE}_05-00-00-52_1_climate")
    await _settle(hass)
    assert hass.states.get(entity_id).attributes["hvac_modes"] == ["heat", "cool", "off"]
    press = esp2.encode_radio(RadioTelegram(Rorg.RPS, b"\x50", 0xFFB744A2, 0x30))
    assert press not in bytes(server.received)
    await hass.services.async_call(
        "climate", "set_hvac_mode", {"entity_id": entity_id, "hvac_mode": "cool"}
    )
    await _settle(hass)
    assert press in bytes(server.received)
    _push(server, 0x05, b"\x70", 0x05000052, 0x30)  # actuator: normal operation
    await _settle(hass)
    assert hass.states.get(entity_id).attributes["hvac_action"] == "cooling"


@pytest.mark.parametrize(
    "gateway",
    [
        [
            _subentry(
                "cover",
                "05-00-00-22",
                "Jalousie",
                senders=[{"profile": "controller", "sender_id": "FF-B7-44-94"}],
                time_opens=40,
                time_closes=40,
                tilt_time=1.5,
                run_time_tenths=True,
            )
        ]
    ],
    indirect=True,
)
async def test_blind_tilt(hass: HomeAssistant, gateway) -> None:
    from custom_components.enocean_eltako.protocol.eep.eltako import shutter

    _entry, server = gateway
    entity_id = _entity(hass, "cover", f"{BASE}_05-00-00-22_1_cover")
    assert hass.states.get(entity_id).attributes["device_class"] == "blind"
    _push(server, 0x05, b"\x70", 0x05000022, 0x30)  # upper end position: slats open
    await _settle(hass)
    assert hass.states.get(entity_id).attributes["current_tilt_position"] == 100
    await hass.services.async_call(
        "cover", "set_cover_tilt_position", {"entity_id": entity_id, "tilt_position": 40}
    )
    await _settle(hass)
    turn = shutter.encode_command(shutter.DOWN, 0.9, tenths=True)  # 100 ms resolution
    assert turn[3] & 0x02
    assert esp2.encode_radio(RadioTelegram(Rorg.BS4, turn, 0xFFB74494)) in bytes(server.received)
    _push(server, 0x07, bytes.fromhex("0009020A"), 0x05000022)  # drove down 0.9 s
    await _settle(hass)
    state = hass.states.get(entity_id)
    assert state.attributes["current_tilt_position"] == 40
    assert state.attributes["current_position"] == 100


@pytest.mark.parametrize(
    "gateway", [[_subentry("meter", "05-00-00-15", "Zähler Küche")]], indirect=True
)
async def test_meter_serial_number(hass: HomeAssistant, gateway) -> None:
    _entry, server = gateway
    prefix = f"{BASE}_05-00-00-15_1"
    _push(server, 0x07, bytes.fromhex("1B0A008F"), 0x05000015)  # S1 S0 00
    _push(server, 0x07, bytes.fromhex("3D2C018F"), 0x05000015)  # S3 S2 01
    await _settle(hass)
    serial = hass.states.get(_entity(hass, "sensor", f"{prefix}_serial_number"))
    assert serial.state == "0A 1B 2C 3D"
    power = hass.states.get(_entity(hass, "sensor", f"{prefix}_power"))
    assert power.state == "unknown"  # the serial telegrams are no power readings


async def test_device_form_shows_teach_in_hint(hass: HomeAssistant, gateway) -> None:
    entry, _server = gateway
    configure = hass.config_entries.subentries.async_configure
    result = await _init_flow(hass, entry)
    result = await _choose_model(hass, result["flow_id"], "psc")
    result = await configure(result["flow_id"], {"next_step_id": "device"})
    assert "PSC132" in result["description_placeholders"]["hint"]
    result = await _init_flow(hass, entry)
    result = await _choose_model(hass, result["flow_id"], "contact")
    result = await configure(result["flow_id"], {"next_step_id": "device"})
    assert result["description_placeholders"]["hint"] == ""  # sensors need no teach-in
    for kind, needle in (("switch", "FSR14"), ("dimmer", "FUD14"), ("cover", "FSB14")):
        result = await _init_flow(hass, entry)
        result = await _choose_model(hass, result["flow_id"], kind)
        result = await configure(result["flow_id"], {"next_step_id": "device"})
        hint = result["description_placeholders"]["hint"]
        assert needle in hint and "LRN" in hint  # the learn function and switch positions


async def test_unstable_connection_repair(hass: HomeAssistant, gateway, monkeypatch) -> None:
    """A connection that keeps dropping (a port in use twice) raises a repair issue."""
    import time as time_module

    from homeassistant.helpers import issue_registry as ir

    from custom_components.enocean_eltako import health

    entry, server = gateway
    runtime = entry.runtime_data
    server.drop_clients()
    for _ in range(50):
        if runtime.drops:
            break
        await asyncio.sleep(0.01)
    assert len(runtime.drops) == 1
    issue_id = f"connection_unstable_{entry.entry_id}"
    registry = ir.async_get(hass)
    runtime.health_check()
    assert registry.async_get_issue(DOMAIN, issue_id) is None  # one drop is no pattern

    runtime.drops.extend([time_module.time()] * 2)
    runtime.health_check()
    issue = registry.async_get_issue(DOMAIN, issue_id)
    assert issue.translation_key == "connection_unstable"
    assert issue.translation_placeholders["drops"] == "3"

    MockConfigEntry(domain="eltako", title="Eltako", state=ConfigEntryState.LOADED).add_to_hass(
        hass
    )
    runtime.health_check()
    issue = registry.async_get_issue(DOMAIN, issue_id)
    assert issue.translation_key == "connection_unstable_users"
    assert issue.translation_placeholders["users"] == "Eltako (eltako)"

    later = time_module.time() + health.UNSTABLE_WINDOW + 1
    monkeypatch.setattr(health.time, "time", lambda: later)
    runtime.health_check()
    assert registry.async_get_issue(DOMAIN, issue_id) is None


async def test_two_channel_actuator(hass: HomeAssistant, gateway) -> None:
    """Two channels under one ID: two devices, each with its own status codes and senders."""
    entry, server = gateway
    configure = hass.config_entries.subentries.async_configure
    for name, channel, sender in (("Kanal 1", "1", "FF-B7-44-8A"), ("Kanal 2", "2", "FF-B7-44-89")):
        result = await hass.config_entries.subentries.async_init(
            (entry.entry_id, "device"), context={"source": "user"}
        )
        result = await _choose_model(hass, result["flow_id"], "switch")
        result = await configure(result["flow_id"], {"next_step_id": "device"})
        assert "status_channel_settings" in [str(k) for k in result["data_schema"].schema]
        result = await configure(
            result["flow_id"],
            {
                "name": name,
                "device_id": "05-10-A2-C0",
                "sender_central": sender,
                "platform": "switch",
                "status_channel_settings": {"status_channel": channel},
            },
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        await hass.async_block_till_done()
    assert {s.unique_id for s in entry.subentries.values()} == {"05-10-A2-C0", "05-10-A2-C0_2"}
    # a third device on the same channel is refused
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "device"), context={"source": "user"}
    )
    result = await _choose_model(hass, result["flow_id"], "switch")
    result = await configure(result["flow_id"], {"next_step_id": "device"})
    result = await configure(
        result["flow_id"],
        {
            "name": "Doppelt",
            "device_id": "05-10-A2-C0",
            "platform": "switch",
            "sender_rocker": "FF-B7-44-88",
            "status_channel_settings": {"status_channel": "2"},
        },
    )
    assert result["errors"] == {"device_id": "already_configured"}
    await server.connected.wait()

    one = _entity(hass, "switch", f"{BASE}_05-10-A2-C0_1_switch")
    two = _entity(hass, "switch", f"{BASE}_05-10-A2-C0_2_switch")
    _push(server, 0x05, b"\x30", 0x0510A2C0, 0x30)  # channel 2 on
    await _settle(hass)
    assert hass.states.get(two).state == "on"
    assert hass.states.get(one).state != "on"
    _push(server, 0x05, b"\x70", 0x0510A2C0, 0x30)  # channel 1 on
    _push(server, 0x05, b"\x10", 0x0510A2C0, 0x30)  # channel 2 off
    await _settle(hass)
    assert (hass.states.get(one).state, hass.states.get(two).state) == ("on", "off")
    devices = {d.subentry.title: d for d in entry.runtime_data.devices.values()}
    channel_two = devices["Kanal 2"]
    assert channel_two.unique_prefix == f"{BASE}_05-10-A2-C0_2"
    status = RadioTelegram(Rorg.RPS, b"\x70", 0x0510A2C0, 0x30)
    assert not channel_two.own_channel(status)  # no confirmation from the other channel
    assert devices["Kanal 1"].own_channel(status)
    pool = entry.runtime_data.senders.pool
    assert pool.get(0xFFB74489).owner == "device:05-10-A2-C0_2:central"

    subentry_id = next(i for i, s in entry.subentries.items() if s.unique_id == "05-10-A2-C0_2")
    result = await entry.start_subentry_reconfigure_flow(hass, subentry_id)
    assert "status_channel_settings" not in [str(k) for k in result["data_schema"].schema]
    result = await configure(
        result["flow_id"],
        {"name": "Kanal 2", "sender_central": "FF-B7-44-89", "platform": "switch"},
    )
    assert result["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()
    assert entry.subentries[subentry_id].data["status_channel"] == "2"  # stays


async def test_migrate_model_name_field(hass: HomeAssistant) -> None:
    """1.4: the optional model name is new, nothing to convert; only the schema moves on."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=BASE,
        version=1,
        minor_version=3,
        data={
            "model": "fam_usb",
            "device": {"type": "tcp", "host": "127.0.0.1", "port": 1},
            "base_id": BASE,
        },
        subentries_data=[
            ConfigSubentryData(
                data={"schema": 3, "model": "switch", "device_id": "05-10-A2-B3"},
                subentry_type="device",
                title="Licht",
                unique_id="05-10-A2-B3",
            ),
        ],
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)  # retries: gateway offline
    await hass.async_block_till_done()
    assert entry.minor_version == EnOceanEltakoConfigFlow.MINOR_VERSION  # passes on to the latest
    (subentry,) = entry.subentries.values()
    assert subentry.data == {
        "schema": SUBENTRY_SCHEMA,
        "model": "switch",
        "device_id": "05-10-A2-B3",
    }


async def test_model_name_is_chosen_typed_and_shown(hass: HomeAssistant, gateway) -> None:
    """The type is not on the air: the user may pick it (or type another), display only."""
    entry, _ = gateway
    configure = hass.config_entries.subentries.async_configure
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "device"), context={"source": "user"}
    )
    result = await _choose_model(hass, result["flow_id"], "switch")
    result = await configure(result["flow_id"], {"next_step_id": "device"})
    field = next(k for k in result["data_schema"].schema if k == "model_name")
    config = result["data_schema"].schema[field].config
    assert "FSR14-4x" in config["options"] and "FSR61NP-230V" in config["options"]
    assert config["custom_value"] is True
    result = await configure(
        result["flow_id"],
        {
            "name": "TWWP Freigabe PV",
            "device_id": "05-10-A2-B3",
            "sender_central": "FF-B7-44-81",
            "platform": "switch",
            "model_name": " FSR14-4x ",
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["model_name"] == "FSR14-4x"
    await hass.async_block_till_done()
    page = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, f"{BASE}_05-10-A2-B3"), entry.entry_id
    )
    assert page is not None and page.model == "FSR14-4x"

    # a model of its own is typed in; leaving it empty stores nothing
    subentry_id = next(iter(entry.subentries))
    result = await entry.start_subentry_reconfigure_flow(hass, subentry_id)
    suggested = {str(k): k.description for k in result["data_schema"].schema if k == "model_name"}
    assert suggested["model_name"]["suggested_value"] == "FSR14-4x"
    result = await configure(
        result["flow_id"],
        {
            "name": "TWWP Freigabe PV",
            "sender_central": "FF-B7-44-81",
            "platform": "switch",
            "model_name": "",
        },
    )
    assert result["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()
    assert "model_name" not in entry.subentries[subentry_id].data


def test_catalog_models_of_the_kinds() -> None:
    """The models to pick come with the kinds that share an EEP; FWG14 is the FWG14MS."""
    assert CATALOG["contact"].example_list == ("FTK", "FTKB")
    assert CATALOG["weather"].models == ("FWS61", "FWS61-24V DC", "FWG14MS")
    assert CATALOG["weather"].example_list == ("FWS61", "FWG14MS")
    for kind in ("switch", "dimmer", "cover", "heating_actuator"):
        assert CATALOG[kind].models
    # every model the user may pick is a plain type designation, no free-form text
    assert all(m == m.strip() and m for c in CATALOG.values() for m in c.models)
