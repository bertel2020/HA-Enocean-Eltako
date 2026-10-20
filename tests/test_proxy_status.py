"""Gateways through the EnOcean Proxy app show the app's status in the panel."""

import pytest
from homeassistant.core import HomeAssistant

from custom_components.enocean_eltako.protocol.models import Protocol
from custom_components.enocean_eltako.proxy_status import summarize

from .fake_gateway import FakeGateway
from .test_init import _entry

pytestmark = pytest.mark.usefixtures("socket_enabled")

STATUS = {
    "version": "0.4.0",
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
        "version": "0.4.0",
        "name": "FAM-USB",
        "connected": True,
        "programs": 2,
        "duty_of_limit": 3.2,
        "telegrams_sent": 41,
        "replayed": 7,
        "exclusive_peer": None,
    }
    assert summarize(status, 9101) is None


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

    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "enocean_eltako/gateways"})
    (gateway,) = (await client.receive_json())["result"]
    assert gateway["via_proxy"] is True
    assert gateway["proxy"]["duty_of_limit"] == 3.2

    await hass.config_entries.async_unload(entry.entry_id)
    await server.stop()
