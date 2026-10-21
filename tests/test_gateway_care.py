"""E3 sender ID page and base ID check, E11 slow bus confirmations."""

import asyncio

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import issue_registry as ir

from custom_components.enocean_eltako.const import DOMAIN
from custom_components.enocean_eltako.health import _check_bus_confirmations, slow_bus_issue_id
from custom_components.enocean_eltako.protocol.models import Protocol

from .fake_gateway import FakeGateway
from .test_devices import _subentry, gateway  # noqa: F401
from .test_init import _entry

pytestmark = pytest.mark.usefixtures("socket_enabled")

SWITCH = [_subentry("switch", "05-10-A2-B3", "Licht Diele", sender_id="FF-B7-44-81")]


async def test_base_id_change_raises_repair(hass: HomeAssistant) -> None:
    server = await FakeGateway(Protocol.ESP2, base_id=0xFF001100).start()
    entry = _entry(server.port)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    issue_id = f"base_id_changed_{entry.entry_id}"
    for _ in range(100):
        if ir.async_get(hass).async_get_issue(DOMAIN, issue_id):
            break
        await asyncio.sleep(0.01)
    issue = ir.async_get(hass).async_get_issue(DOMAIN, issue_id)
    assert issue is not None
    assert issue.translation_placeholders["reported"] == "FF-00-11-00"
    assert issue.translation_placeholders["configured"] == "FF-B7-44-80"
    await hass.config_entries.async_unload(entry.entry_id)
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None
    await server.stop()


@pytest.mark.parametrize("gateway", [SWITCH], indirect=True)
async def test_sender_page_lists_and_frees(hass: HomeAssistant, gateway) -> None:  # noqa: F811
    entry, _server = gateway
    pool = entry.runtime_data.senders.pool
    pool.assign(0xFFB74481, "device:05-10-A2-B3:central")  # as the device flow does
    pool.assign(0xFFB74490, "device:01-02-03-04:central")
    pool.release(0xFFB74490)  # removed device: blocked until the teach-out is confirmed

    options = hass.config_entries.options
    result = await options.async_init(entry.entry_id)
    assert result["menu_options"] == ["settings", "senders", "takeover"]
    result = await options.async_configure(result["flow_id"], {"next_step_id": "senders"})
    rows = result["description_placeholders"]["rows"]
    assert "| FF-B7-44-81 | Licht Diele | central |" in rows
    assert "| FF-B7-44-90 | 01-02-03-04 | central |" in rows
    assert result["description_placeholders"]["free"] == "126"

    result = await options.async_configure(result["flow_id"], {"free": ["FF-B7-44-90"]})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "senders_freed"
    assert pool.get(0xFFB74490) is None
    assert pool.get(0xFFB74481) is not None


@pytest.mark.parametrize("gateway", [SWITCH], indirect=True)
async def test_slow_bus_confirmations_raise_repair(hass: HomeAssistant, gateway) -> None:  # noqa: F811
    entry, _server = gateway
    (device,) = entry.runtime_data.devices.values()
    issue_id = slow_bus_issue_id(entry.entry_id)
    device.stats.latencies.extend([0.4, 3.5, 4.0, 5.0])
    _check_bus_confirmations(hass, entry)
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None  # too few samples
    device.stats.latencies.append(6.0)
    _check_bus_confirmations(hass, entry)
    issue = ir.async_get(hass).async_get_issue(DOMAIN, issue_id)
    assert issue.translation_placeholders["seconds"] == "4.0"
    device.stats.latencies.extend([0.3] * 10)
    _check_bus_confirmations(hass, entry)
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None


async def test_silent_gateway_repair(hass: HomeAssistant, monkeypatch) -> None:
    """A gateway that accepts the connection but never answers raises a repair; it clears itself."""
    from homeassistant.helpers import issue_registry as ir

    from custom_components.enocean_eltako import health

    monkeypatch.setattr(health, "PROBE_AFTER", 0)
    monkeypatch.setattr(health, "PROBE_TIMEOUT", 0.2)
    server = await FakeGateway(Protocol.ESP2, base_id=None).start()
    entry = _entry(server.port)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await server.connected.wait()
    await hass.async_block_till_done()
    issue_id = health.silent_issue_id(entry.entry_id)
    registry = ir.async_get(hass)
    try:
        for _ in range(150):  # the check after connecting waits 3 s for the answer
            if registry.async_get_issue(DOMAIN, issue_id):
                break
            await asyncio.sleep(0.05)
        issue = registry.async_get_issue(DOMAIN, issue_id)
        assert issue.translation_key == "gateway_silent"

        server.base_id = 0xFFB74480  # it answers now: the next check clears the repair
        entry.runtime_data.health_check()
        for _ in range(100):
            if registry.async_get_issue(DOMAIN, issue_id) is None:
                break
            await asyncio.sleep(0.02)
        assert registry.async_get_issue(DOMAIN, issue_id) is None
    finally:
        assert await hass.config_entries.async_unload(entry.entry_id)
        await server.stop()
