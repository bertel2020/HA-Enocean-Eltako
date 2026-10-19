"""Device subentries: flow, entities from telegrams, commands, sender IDs."""

import asyncio

import pytest
from homeassistant.config_entries import ConfigSubentryData
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.enocean_eltako.catalog import CATALOG
from custom_components.enocean_eltako.const import DOMAIN
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
    sender_key = next(k for k in schema if k == "sender_central")
    assert sender_key.default() == "FF-B7-44-80"
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
            "sender_central": "FF-B7-44-80",
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
                routing="both",
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
    assert controller_up in received and rocker_up in received and rocker_release in received
    for key in ("controller", "direction_rocker"):
        assert _entity(hass, "button", f"{BASE}_05-00-00-22_1_teach_in_{key}")


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
            "sender_controller": "FF-B7-44-80",
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
            "sender_controller": "FF-B7-44-80",
            "sender_direction_rocker": "FF-B7-44-81",
            "time_opens": 25,
            "time_closes": 21,
            "routing": "both",
        },
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()
    subentry = entry.subentries[subentry_id]
    assert subentry.title == "Rollladen Büro"
    assert subentry.data["senders"] == [
        {"profile": "controller", "sender_id": "FF-B7-44-80"},
        {"profile": "direction_rocker", "sender_id": "FF-B7-44-81"},
    ]
    assert subentry.data["time_opens"] == 25
    pool = entry.runtime_data.senders.pool
    assert pool.get(0xFFB74481).owner == "device:05-00-00-23:direction_rocker"

    # dropping the rocker blocks its ID until the teach-out is confirmed
    result = await entry.start_subentry_reconfigure_flow(hass, subentry_id)
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"next_step_id": "settings"}
    )
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            "name": "Rollladen Büro",
            "sender_controller": "FF-B7-44-80",
            "time_opens": 25,
            "time_closes": 21,
            "routing": "controller",
        },
    )
    await hass.async_block_till_done()
    assert entry.runtime_data.senders.pool.get(0xFFB74481).state == "blocked"


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
    assert entry.minor_version == 2
    by_title = {s.title: s.data for s in entry.subentries.values()}
    assert by_title["Licht"]["senders"] == [{"profile": "central", "sender_id": "FF-B7-44-81"}]
    assert "sender_id" not in by_title["Licht"]
    assert by_title["Kontakt"]["schema"] == 2 and "senders" not in by_title["Kontakt"]


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
    from homeassistant.helpers import issue_registry as ir

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
    assert result["step_id"] == "measure_result"
    assert result["description_placeholders"] == {"time_opens": "25.0", "time_closes": "23.0"}
    result = await hass.config_entries.subentries.async_configure(result["flow_id"], {})
    assert result["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()
    data = entry.subentries[subentry_id].data
    assert (data["time_opens"], data["time_closes"]) == (25.0, 23.0)


async def _init_flow(hass: HomeAssistant, entry):
    return await hass.config_entries.subentries.async_init(
        (entry.entry_id, "device"), context={"source": "user"}
    )


async def test_add_device_menus(hass: HomeAssistant, gateway) -> None:
    entry, _server = gateway
    configure = hass.config_entries.subentries.async_configure
    result = await _init_flow(hass, entry)
    assert result["menu_options"] == ["learn", "eltako", "enocean", "eep"]
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
        "eltako",
    ]

    # only one kind in the category: straight to the address
    result = await _init_flow(hass, entry)
    result = await configure(result["flow_id"], {"next_step_id": "enocean"})
    assert result["menu_options"] == ["enocean_lighting", "enocean_buttons", "user"]
    result = await configure(result["flow_id"], {"next_step_id": "enocean_lighting"})
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
    assert result["menu_options"] == ["learn", "eltako", "enocean", "eep"]


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
    assert result["menu_options"] == ["learn", "eltako", "enocean", "eep"]
    # a single kind goes straight to the address; back leads to the categories
    result = await configure(flow_id, {"next_step_id": "enocean"})
    result = await configure(flow_id, {"next_step_id": "enocean_lighting"})
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
