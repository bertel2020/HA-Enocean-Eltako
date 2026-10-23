"""Discovery: unknown senders are offered under "Add device" of the gateway."""

from datetime import timedelta

import pytest
from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.enocean_eltako.const import DOMAIN
from custom_components.enocean_eltako.discovery import CARD_DELAY
from custom_components.enocean_eltako.protocol.eep.teach_in import encode_teach_in_4bs

from .test_devices import _push, _settle, _subentry, gateway  # noqa: F401

pytestmark = pytest.mark.usefixtures("socket_enabled")


async def _menu(hass: HomeAssistant, entry):
    return await hass.config_entries.subentries.async_init(
        (entry.entry_id, "device"), context={"source": "user"}
    )


async def test_unknown_rocker_becomes_device(hass: HomeAssistant, gateway) -> None:  # noqa: F811
    entry, server = gateway
    result = await _menu(hass, entry)
    assert "discovered" not in result["menu_options"]
    hass.config_entries.subentries.async_abort(result["flow_id"])

    _push(server, 0x05, b"\x70", 0x002A0B0C, 0x30)
    _push(server, 0x05, b"\x00", 0x002A0B0C, 0x20)  # the same sender: listed once
    await _settle(hass)
    cards = await _cards(hass)
    assert len(cards) == 1  # one card for the gateway, not one per sender
    assert "1 " in cards[0]["context"]["title_placeholders"]["name"]
    result = await hass.config_entries.flow.async_configure(cards[0]["flow_id"])
    assert result["step_id"] == "discovered_senders"
    assert "00-2A-0B-0C" in result["description_placeholders"]["senders"]
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["reason"] == "discovered_hint"
    assert not await _cards(hass)  # seen: the card goes until something new is heard

    result = await _menu(hass, entry)
    assert result["menu_options"][0] == "discovered"
    configure = hass.config_entries.subentries.async_configure
    result = await configure(result["flow_id"], {"next_step_id": "discovered"})
    assert result["step_id"] == "discovered"
    (option,) = result["data_schema"].schema["device_id"].config["options"]
    assert option["value"] == "00-2A-0B-0C"
    result = await configure(result["flow_id"], {"device_id": "00-2A-0B-0C"})
    assert result["step_id"] == "learned"
    result = await configure(result["flow_id"], {"model": "rocker"})
    assert result["step_id"] == "device"
    result = await configure(result["flow_id"], {"name": "Taster Flur", "device_id": "00-2A-0B-0C"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    (subentry,) = entry.subentries.values()
    assert subentry.unique_id == "00-2A-0B-0C"
    assert subentry.data["model"] == "rocker"

    result = await _menu(hass, entry)  # set up now: no longer offered
    assert "discovered" not in result["menu_options"]


async def test_teach_in_of_generic_profile_skips_kind(hass: HomeAssistant, gateway) -> None:  # noqa: F811
    entry, server = gateway
    _push(server, 0x07, encode_teach_in_4bs("A5-13-02"), 0x01A2B3C4)
    await _settle(hass)
    result = await _menu(hass, entry)
    configure = hass.config_entries.subentries.async_configure
    result = await configure(result["flow_id"], {"next_step_id": "discovered"})
    result = await configure(result["flow_id"], {"device_id": "01-A2-B3-C4"})
    assert result["step_id"] == "device"


async def test_own_senders_and_disabled_discovery(hass: HomeAssistant, gateway) -> None:  # noqa: F811
    entry, server = gateway
    hub = entry.runtime_data.hub
    _push(server, 0x05, b"\x70", 0xFFB74485, 0x30)  # one of our own sender IDs
    await _settle(hass)
    assert not hub.discovered
    hass.config_entries.async_update_entry(entry, options={**entry.options, "discovery": False})
    await hass.async_block_till_done()
    await server.connected.wait()
    _push(server, 0x05, b"\x70", 0x002A0B0D, 0x30)
    await _settle(hass)
    assert not hub.discovered


async def test_added_device_is_no_longer_offered(hass: HomeAssistant, gateway) -> None:  # noqa: F811
    entry, server = gateway
    _push(server, 0x05, b"\x70", 0x002A0B0E, 0x30)
    await _settle(hass)
    data = _subentry("rocker", "00-2A-0B-0E", "Taster")
    hass.config_entries.async_add_subentry(
        entry,
        ConfigSubentry(
            data={**data["data"], "schema": 2},
            subentry_type="device",
            title="Taster",
            unique_id="00-2A-0B-0E",
        ),
    )
    await hass.async_block_till_done()
    result = await _menu(hass, entry)
    assert "discovered" not in result["menu_options"]


async def test_panel_offers_sender(hass: HomeAssistant, gateway, hass_ws_client) -> None:  # noqa: F811
    entry, server = gateway
    hass.config_entries.async_update_entry(entry, options={**entry.options, "discovery": False})
    await hass.async_block_till_done()
    await server.connected.wait()
    _push(server, 0x06, b"\x08", 0x01000077)
    await _settle(hass)
    assert not entry.runtime_data.hub.discovered  # discovery off: not listed by itself

    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "enocean_eltako/discover", "sender": "01-00-00-77"})
    assert (await client.receive_json())["result"] == {"entry_id": entry.entry_id}
    assert 0x01000077 in entry.runtime_data.hub.discovered

    await client.send_json({"id": 3, "type": "enocean_eltako/discover", "sender": "01-99-99-99"})
    assert (await client.receive_json())["error"]["code"] == "not_found"
    await client.send_json({"id": 4, "type": "enocean_eltako/discover", "sender": "no ID"})
    assert (await client.receive_json())["error"]["code"] == "invalid_id"


async def test_hide_and_show_again(hass: HomeAssistant, gateway) -> None:  # noqa: F811
    entry, server = gateway
    hub = entry.runtime_data.hub
    _push(server, 0x05, b"\x70", 0x002A0B0F, 0x30)
    await _settle(hass)
    result = await _menu(hass, entry)
    configure = hass.config_entries.subentries.async_configure
    result = await configure(result["flow_id"], {"next_step_id": "discovered"})
    result = await configure(result["flow_id"], {"device_id": "00-2A-0B-0F", "hide": True})
    assert result["reason"] == "sender_hidden"
    assert hub.hidden[entry.entry_id] == {0x002A0B0F}
    assert not await _cards(hass)  # nothing left to announce

    _push(server, 0x05, b"\x00", 0x002A0B0F, 0x20)  # still hidden when heard again
    await _settle(hass)
    result = await _menu(hass, entry)
    assert "discovered" not in result["menu_options"]
    hass.config_entries.subentries.async_abort(result["flow_id"])

    options = await hass.config_entries.options.async_init(entry.entry_id)
    assert options["type"] is FlowResultType.MENU
    options = await hass.config_entries.options.async_configure(
        options["flow_id"], {"next_step_id": "hidden"}
    )
    late = await hass.config_entries.options.async_init(entry.entry_id)  # still open at unload
    late = await hass.config_entries.options.async_configure(
        late["flow_id"], {"next_step_id": "hidden"}
    )
    options = await hass.config_entries.options.async_configure(
        options["flow_id"], {"again": ["00-2A-0B-0F"]}
    )
    assert options["reason"] == "senders_shown"
    assert not hub.hidden[entry.entry_id]
    _push(server, 0x05, b"\x70", 0x002A0B0F, 0x30)
    await _settle(hass)
    result = await _menu(hass, entry)
    assert "discovered" in result["menu_options"]
    hass.config_entries.subentries.async_abort(result["flow_id"])

    await hass.config_entries.async_unload(entry.entry_id)
    late = await hass.config_entries.options.async_configure(late["flow_id"], {"again": []})
    assert late["reason"] == "gateway_not_loaded"


async def test_list_is_capped(hass: HomeAssistant, gateway) -> None:  # noqa: F811
    from custom_components.enocean_eltako.discovery import MAX_DISCOVERED

    entry, server = gateway
    for n in range(MAX_DISCOVERED + 5):
        _push(server, 0x05, b"\x70", 0x00300000 + n, 0x30)
    await _settle(hass)
    assert len(entry.runtime_data.hub.discovered) == MAX_DISCOVERED


async def _cards(hass: HomeAssistant):
    """The discovery cards in progress, after the short delay that takes bursts together."""
    await hass.async_block_till_done()
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=CARD_DELAY + 1))
    await hass.async_block_till_done()
    return [
        flow
        for flow in hass.config_entries.flow.async_progress_by_handler(DOMAIN)
        if flow["context"].get("source") == "integration_discovery"
    ]


async def test_card_follows_the_count(hass: HomeAssistant, gateway) -> None:  # noqa: F811
    entry, server = gateway
    _push(server, 0x05, b"\x70", 0x002A0B10, 0x30)
    await _settle(hass)
    (card,) = await _cards(hass)
    assert "1" in card["context"]["title_placeholders"]["name"]
    _push(server, 0x05, b"\x70", 0x002A0B11, 0x30)
    _push(server, 0x05, b"\x70", 0x002A0B12, 0x30)
    await _settle(hass)
    (again,) = await _cards(hass)  # replaced, not added
    assert again["flow_id"] != card["flow_id"]
    assert "3" in again["context"]["title_placeholders"]["name"]
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert not await _cards(hass)
