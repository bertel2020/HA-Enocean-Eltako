"""Entry setup and unload."""

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.enocean_eltako.const import DOMAIN
from custom_components.enocean_eltako.protocol.models import Protocol

from .fake_gateway import FakeGateway

pytestmark = pytest.mark.usefixtures("socket_enabled")


def _entry(port: int) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id="FF-B7-44-80",
        data={
            "model": "fam_usb",
            "connection": {"type": "tcp", "host": "127.0.0.1", "port": port},
            "base_id": "FF-B7-44-80",
        },
    )


async def test_setup_and_unload(hass: HomeAssistant) -> None:
    server = await FakeGateway(Protocol.ESP2).start()
    entry = _entry(server.port)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    gateway = entry.runtime_data
    assert gateway.connected
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED
    assert not gateway.connected
    await server.stop()


async def test_setup_retries_when_gateway_is_offline(hass: HomeAssistant) -> None:
    server = await FakeGateway(Protocol.ESP2).start()
    port = server.port
    await server.stop()
    entry = _entry(port)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_RETRY
