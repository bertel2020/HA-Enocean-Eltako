"""Optional gateway prefix in entity IDs (eno_gw1, eno_gw2 ...)."""

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.enocean_eltako.const import DOMAIN
from custom_components.enocean_eltako.protocol.models import Protocol

from .fake_gateway import FakeGateway
from .test_devices import _subentry

pytestmark = pytest.mark.usefixtures("socket_enabled")

BASE = "FF-B7-44-80"


async def _setup(hass: HomeAssistant, options: dict) -> tuple[MockConfigEntry, FakeGateway]:
    server = await FakeGateway(Protocol.ESP2).start()
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="FAM USB",
        unique_id=BASE,
        data={
            "model": "fam_usb",
            "device": {"type": "tcp", "host": "127.0.0.1", "port": server.port},
            "base_id": BASE,
        },
        options={"message_delay": 0, **options},
        subentries_data=[_subentry("switch", "05-10-A2-B8", "Licht Flur", platform="light")],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    await server.connected.wait()
    return entry, server


def _ids(hass: HomeAssistant, entry: MockConfigEntry) -> set[str]:
    return {
        e.entity_id for e in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
    }


def _prefix_sensor(hass: HomeAssistant, entry: MockConfigEntry) -> str | None:
    unique_id = f"{entry.entry_id}_gateway_entity_prefix"
    return er.async_get(hass).async_get_entity_id("sensor", DOMAIN, unique_id)


async def _teardown(hass: HomeAssistant, entry: MockConfigEntry, server: FakeGateway) -> None:
    await hass.config_entries.async_unload(entry.entry_id)
    await server.stop()


async def test_without_prefix_home_assistant_names_entities(hass: HomeAssistant) -> None:
    entry, server = await _setup(hass, {})
    ids = _ids(hass, entry)
    assert "light.licht_flur" in ids
    assert "sensor.licht_flur_enocean_id" in ids
    assert "binary_sensor.fam_usb_connection" in ids
    assert not any("eno_gw" in i for i in ids)
    assert _prefix_sensor(hass, entry) is None  # the gateway shows a prefix only when it has one
    await _teardown(hass, entry, server)


async def test_prefix_on_new_entities(hass: HomeAssistant) -> None:
    entry, server = await _setup(hass, {"entity_prefix": True, "gateway_number": 2})
    ids = _ids(hass, entry)
    assert "light.eno_gw2_licht_flur" in ids
    assert "sensor.eno_gw2_licht_flur_enocean_id" in ids
    assert "binary_sensor.eno_gw2_fam_usb_connection" in ids
    assert hass.states.get("light.eno_gw2_licht_flur") is not None
    sensor = _prefix_sensor(hass, entry)
    assert sensor == "sensor.eno_gw2_fam_usb_entity_id_prefix"
    assert hass.states.get(sensor).state == "eno_gw2"
    await _teardown(hass, entry, server)


async def test_options_rename_existing_entities(hass: HomeAssistant) -> None:
    entry, server = await _setup(hass, {})
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["data_schema"]({})["gateway_number"] == 1  # first free number
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "message_delay": 0,
            "discovery": True,
            "entity_prefix": True,
            "gateway_number": 1.0,
            "rename_entities": True,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["gateway_number"] == 1
    assert "rename_entities" not in entry.options
    await hass.async_block_till_done()
    ids = _ids(hass, entry)
    assert "light.eno_gw1_licht_flur" in ids
    assert "binary_sensor.eno_gw1_fam_usb_connection" in ids
    assert "light.licht_flur" not in ids
    assert hass.states.get("light.eno_gw1_licht_flur") is not None
    assert hass.states.get(_prefix_sensor(hass, entry)).state == "eno_gw1"

    # and back: prefix off, renamed again
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "message_delay": 0,
            "discovery": True,
            "entity_prefix": False,
            "gateway_number": 1,
            "rename_entities": True,
        },
    )
    await hass.async_block_till_done()
    assert "light.licht_flur" in _ids(hass, entry)
    assert _prefix_sensor(hass, entry) is None  # removed with the prefix
    await _teardown(hass, entry, server)


async def test_options_without_rename_keep_existing_ids(hass: HomeAssistant) -> None:
    entry, server = await _setup(hass, {})
    result = await hass.config_entries.options.async_init(entry.entry_id)
    await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"message_delay": 0, "discovery": True, "entity_prefix": True, "gateway_number": 1},
    )
    await hass.async_block_till_done()
    assert "light.licht_flur" in _ids(hass, entry)  # registered before: Home Assistant keeps it
    await _teardown(hass, entry, server)


async def test_gateway_number_taken(hass: HomeAssistant) -> None:
    other = MockConfigEntry(
        domain=DOMAIN, data={"model": "fam_usb"}, options={"entity_prefix": True}
    )
    other.add_to_hass(hass)
    entry = MockConfigEntry(domain=DOMAIN, data={"model": "fam_usb"})
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["data_schema"]({})["gateway_number"] == 2  # 1 is taken
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"message_delay": 10, "discovery": True, "entity_prefix": True, "gateway_number": 1},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"gateway_number": "gateway_number_taken"}
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"message_delay": 10, "discovery": True, "entity_prefix": True, "gateway_number": 2},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["gateway_number"] == 2
