"""Discovery: unknown senders become discovered-device cards that add a subentry."""

import pytest
from homeassistant.config_entries import SOURCE_IGNORE, SOURCE_INTEGRATION_DISCOVERY
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.enocean_eltako.const import DOMAIN
from custom_components.enocean_eltako.protocol.eep.teach_in import encode_teach_in_4bs

from .test_devices import BASE, _push, _settle, _subentry, gateway  # noqa: F401

pytestmark = pytest.mark.usefixtures("socket_enabled")


def _discovered(hass: HomeAssistant) -> dict[str, dict]:
    return {
        flow["context"]["unique_id"]: flow
        for flow in hass.config_entries.flow.async_progress_by_handler(DOMAIN)
        if flow["context"]["source"] == SOURCE_INTEGRATION_DISCOVERY
    }


async def test_unknown_rocker_becomes_device(hass: HomeAssistant, gateway) -> None:  # noqa: F811
    entry, server = gateway
    _push(server, 0x05, b"\x70", 0x002A0B0C, 0x30)
    _push(server, 0x05, b"\x00", 0x002A0B0C, 0x20)  # the same sender: one card only
    await _settle(hass)
    flows = _discovered(hass)
    assert list(flows) == ["device_00-2A-0B-0C"]
    flow = flows["device_00-2A-0B-0C"]
    assert flow["context"]["title_placeholders"] == {"name": "00-2A-0B-0C"}

    configure = hass.config_entries.flow.async_configure
    result = await configure(flow["flow_id"])
    assert result["step_id"] == "discovered"
    assert result["description_placeholders"]["gateway"] == entry.title
    result = await configure(flow["flow_id"], {"model": "rocker"})
    assert result["step_id"] == "discovered_device"
    result = await configure(flow["flow_id"], {"name": "Taster Flur"})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "device_added"
    await hass.async_block_till_done()
    (subentry,) = entry.subentries.values()
    assert subentry.title == "Taster Flur"
    assert subentry.unique_id == "00-2A-0B-0C"
    assert subentry.data["model"] == "rocker"


async def test_teach_in_of_generic_profile_skips_kind(hass: HomeAssistant, gateway) -> None:  # noqa: F811
    entry, server = gateway
    _push(server, 0x07, encode_teach_in_4bs("A5-13-02"), 0x01A2B3C4)
    await _settle(hass)
    flow = _discovered(hass)["device_01-A2-B3-C4"]
    result = await hass.config_entries.flow.async_configure(flow["flow_id"])
    assert result["step_id"] == "discovered_device"
    result = await hass.config_entries.flow.async_configure(
        flow["flow_id"], {"name": "Wetter", "fields": []}
    )
    assert result["reason"] == "device_added"
    await hass.async_block_till_done()
    (subentry,) = entry.subentries.values()
    assert subentry.data["eep"] == "A5-13-02:std"


async def test_ignored_sender_is_not_offered_again(hass: HomeAssistant, gateway) -> None:  # noqa: F811
    entry, server = gateway
    _push(server, 0x06, b"\x08", 0x01000099)
    await _settle(hass)
    flow = _discovered(hass)["device_01-00-00-99"]
    hass.config_entries.flow.async_abort(flow["flow_id"])
    await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_IGNORE},
        data={"unique_id": "device_01-00-00-99", "title": "01-00-00-99"},
    )
    entry.runtime_data.hub.discovered.clear()  # as after a restart
    _push(server, 0x06, b"\x00", 0x01000099)
    await _settle(hass)
    assert _discovered(hass) == {}


async def test_own_senders_and_disabled_discovery(hass: HomeAssistant, gateway) -> None:  # noqa: F811
    entry, server = gateway
    _push(server, 0x05, b"\x70", 0xFFB74485, 0x30)  # one of our own sender IDs
    await _settle(hass)
    assert _discovered(hass) == {}
    hass.config_entries.async_update_entry(entry, options={**entry.options, "discovery": False})
    _push(server, 0x05, b"\x70", 0x002A0B0D, 0x30)
    await _settle(hass)
    assert _discovered(hass) == {}


async def test_card_disappears_when_device_added(hass: HomeAssistant, gateway) -> None:  # noqa: F811
    entry, server = gateway
    _push(server, 0x05, b"\x70", 0x002A0B0E, 0x30)
    await _settle(hass)
    assert "device_00-2A-0B-0E" in _discovered(hass)
    from homeassistant.config_entries import ConfigSubentry

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
    assert _discovered(hass) == {}


async def test_panel_adds_sender_as_device(hass: HomeAssistant, gateway, hass_ws_client) -> None:  # noqa: F811
    entry, server = gateway
    hass.config_entries.async_update_entry(entry, options={**entry.options, "discovery": False})
    await hass.async_block_till_done()
    await server.connected.wait()
    _push(server, 0x06, b"\x08", 0x01000077)
    await _settle(hass)
    assert _discovered(hass) == {}  # discovery off: no card by itself

    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "enocean_eltako/discover", "sender": "01-00-00-77"})
    result = (await client.receive_json())["result"]
    flow = _discovered(hass)["device_01-00-00-77"]
    assert result == {"flow_id": flow["flow_id"]}

    await client.send_json({"id": 2, "type": "enocean_eltako/discover", "sender": "01000077"})
    assert (await client.receive_json())["result"] == {"reason": "already_in_progress"}
    await client.send_json({"id": 3, "type": "enocean_eltako/discover", "sender": "01-99-99-99"})
    assert (await client.receive_json())["error"]["code"] == "not_found"


async def test_panel_add_without_card_keeps_sender_open(
    hass: HomeAssistant,
    gateway,  # noqa: F811
    hass_ws_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No fitting kind: the panel reports it and automatic discovery may still offer it."""
    entry, server = gateway
    hass.config_entries.async_update_entry(entry, options={**entry.options, "discovery": False})
    await hass.async_block_till_done()
    await server.connected.wait()
    _push(server, 0x06, b"\x08", 0x01000078)
    await _settle(hass)

    monkeypatch.setattr("custom_components.enocean_eltako.config_flow.candidates", lambda *a: [])
    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "enocean_eltako/discover", "sender": "01-00-00-78"})
    assert (await client.receive_json())["result"] == {"reason": "no_matching_kind"}
    assert 0x01000078 not in entry.runtime_data.hub.discovered

    monkeypatch.undo()
    await client.send_json({"id": 2, "type": "enocean_eltako/discover", "sender": "01-00-00-78"})
    assert "flow_id" in (await client.receive_json())["result"]
    assert 0x01000078 in entry.runtime_data.hub.discovered
