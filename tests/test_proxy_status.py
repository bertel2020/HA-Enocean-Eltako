"""Gateways through the Device Proxy app show the app's status in the panel."""

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.enocean_eltako.const import DOMAIN
from custom_components.enocean_eltako.protocol.models import Protocol
from custom_components.enocean_eltako.proxy_status import summarize

from .fake_gateway import FakeGateway
from .test_init import _entry

pytestmark = pytest.mark.usefixtures("socket_enabled")

STATUS = {
    "app": "device_proxy",
    "api": 1,
    "version": "0.2.0",
    "gateways": [
        {
            "name": "FAM-USB",
            "port": 0,  # set per test
            "connected": True,
            "clients": [{"peer": "172.30.32.1", "replay": True}, {"peer": "10.0.0.5"}],
            "duty_cycle": {"of_limit": 3.2, "telegrams": 41},
            "stats": {"replayed": 7},
            "exclusive_peer": None,
        },
        {"name": "other", "port": 1},
    ],
}


def test_summarize_picks_the_gateway_by_port() -> None:
    status = {**STATUS, "gateways": [{**STATUS["gateways"][0], "port": 9100}]}
    assert summarize(status, 9100) == {
        "app": "Device Proxy",
        "api": 1,
        "version": "0.2.0",
        "name": "FAM-USB",
        "connected": True,
        "programs": 2,
        "duty_of_limit": 3.2,
        "telegrams_sent": 41,
        "replayed": 7,
        "exclusive_peer": None,
        "via_fallback": False,
        "fallback_name": None,
        "fallback_ready": None,
    }
    assert summarize(status, 9101) is None


def test_summarize_tells_when_a_fallback_gateway_stands_in() -> None:
    gateway = {**STATUS["gateways"][0], "port": 9100, "active": "fallback"}
    fallback = {"name": "FAM-USB 2", "ready": True, "not_ready": None, "base_id": "FF-B7-44-80"}
    result = summarize({**STATUS, "gateways": [{**gateway, "fallback": fallback}]}, 9100)
    assert result is not None
    assert (result["via_fallback"], result["fallback_name"], result["fallback_ready"]) == (
        True,
        "FAM-USB 2",
        True,
    )
    resting = summarize(
        {**STATUS, "gateways": [{**gateway, "active": "main", "fallback": {"ready": False}}]}, 9100
    )
    assert resting is not None and resting["via_fallback"] is False
    assert resting["fallback_ready"] is False


async def test_panel_status_includes_the_proxy(
    hass: HomeAssistant, aioclient_mock, hass_ws_client
) -> None:
    server = await FakeGateway(Protocol.ESP2).start()
    status = {**STATUS, "gateways": [{**STATUS["gateways"][0], "port": server.port}]}
    aioclient_mock.get("http://127.0.0.1:9199/api/status", json=status)
    entry = _entry(server.port)
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(entry, options={"proxy_replay": True})
    assert await hass.config_entries.async_setup(entry.entry_id)
    await server.connected.wait()
    await hass.async_block_till_done()
    assert entry.runtime_data.proxy["programs"] == 2
    assert entry.runtime_data.proxy["app"] == "Device Proxy"

    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "enocean_eltako/gateways"})
    (gateway,) = (await client.receive_json())["result"]
    assert gateway["via_proxy"] is True
    assert gateway["proxy"]["duty_of_limit"] == 3.2

    await hass.config_entries.async_unload(entry.entry_id)
    await server.stop()


async def test_the_connection_sensor_tells_when_the_fallback_stands_in(
    hass: HomeAssistant, aioclient_mock
) -> None:
    server = await FakeGateway(Protocol.ESP2).start()
    gateway = {**STATUS["gateways"][0], "port": server.port, "active": "fallback"}
    gateway["fallback"] = {"name": "FAM-USB 2", "ready": True}
    aioclient_mock.get("http://127.0.0.1:9199/api/status", json={**STATUS, "gateways": [gateway]})
    entry = _entry(server.port)
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(entry, options={"proxy_replay": True})
    assert await hass.config_entries.async_setup(entry.entry_id)
    await server.connected.wait()
    await hass.async_block_till_done()
    entity_id = er.async_get(hass).async_get_entity_id(
        "binary_sensor", DOMAIN, f"{entry.entry_id}_gateway_connection"
    )
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None and state.state == "on"  # connected to the app all along
    assert state.attributes["via_fallback"] is True
    assert state.attributes["fallback"] == "FAM-USB 2"
    assert state.attributes["fallback_ready"] is True

    await hass.config_entries.async_unload(entry.entry_id)
    await server.stop()


async def test_no_fallback_attributes_without_a_fallback(
    hass: HomeAssistant, aioclient_mock
) -> None:
    server = await FakeGateway(Protocol.ESP2).start()
    status = {**STATUS, "gateways": [{**STATUS["gateways"][0], "port": server.port}]}
    aioclient_mock.get("http://127.0.0.1:9199/api/status", json=status)
    entry = _entry(server.port)
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(entry, options={"proxy_replay": True})
    assert await hass.config_entries.async_setup(entry.entry_id)
    await server.connected.wait()
    await hass.async_block_till_done()
    entity_id = er.async_get(hass).async_get_entity_id(
        "binary_sensor", DOMAIN, f"{entry.entry_id}_gateway_connection"
    )
    state = hass.states.get(entity_id or "")
    assert state is not None and "via_fallback" not in state.attributes

    await hass.config_entries.async_unload(entry.entry_id)
    await server.stop()
