"""The old eltako integration on the same gateway raises a repair issue."""

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.enocean_eltako.const import DOMAIN
from custom_components.enocean_eltako.old_integration import (
    async_check_old_integration,
    issue_id,
    sharing_entries,
)

SERIAL = {"type": "serial", "path": "/dev/ttyUSB0", "baudrate": 9600}
TCP = {"type": "tcp", "host": "192.0.2.10", "port": 5100}


def _new(device: dict) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title="Gateway",
        data={"model": "fam_usb", "device": device, "base_id": "FF-B7-44-80"},
    )


def _old(hass: HomeAssistant, data: dict, **kwargs) -> MockConfigEntry:
    old = MockConfigEntry(domain="eltako", data=data, **kwargs)
    old.add_to_hass(hass)
    old.mock_state(hass, ConfigEntryState.LOADED)
    return old


def _issue(hass: HomeAssistant, entry: MockConfigEntry):
    return ir.async_get(hass).async_get_issue(DOMAIN, issue_id(entry.entry_id))


async def test_same_serial_port(hass: HomeAssistant) -> None:
    entry = _new(SERIAL)
    entry.add_to_hass(hass)
    async_check_old_integration(hass, entry)
    assert _issue(hass, entry) is None  # no old integration

    _old(hass, {"serial_path": "/dev/ttyUSB1"})
    async_check_old_integration(hass, entry)
    assert _issue(hass, entry) is None  # another port

    old = _old(hass, {"serial_path": "/dev/ttyUSB0"})
    async_check_old_integration(hass, entry)
    issue = _issue(hass, entry)
    assert issue is not None
    assert issue.translation_placeholders == {"name": "Gateway", "connection": "/dev/ttyUSB0"}

    old.mock_state(hass, ConfigEntryState.NOT_LOADED)  # as after disabling it
    assert sharing_entries(hass, entry) == []
    async_check_old_integration(hass, entry)
    assert _issue(hass, entry) is None  # cleared once the old entry is off


async def test_same_host_and_port(hass: HomeAssistant) -> None:
    entry = _new(TCP)
    entry.add_to_hass(hass)
    _old(hass, {"serial_path": "192.0.2.10", "port": 5000})
    async_check_old_integration(hass, entry)
    assert _issue(hass, entry) is None  # same host, another port

    _old(hass, {"serial_path": "192.0.2.10", "port": 5100})
    async_check_old_integration(hass, entry)
    assert _issue(hass, entry).translation_placeholders["connection"] == "192.0.2.10:5100"


async def test_old_entry_not_set_up_is_no_conflict(hass: HomeAssistant) -> None:
    entry = _new(SERIAL)
    entry.add_to_hass(hass)
    old = MockConfigEntry(domain="eltako", data={"serial_path": "/dev/ttyUSB0"})
    old.add_to_hass(hass)  # not loaded
    async_check_old_integration(hass, entry)
    assert _issue(hass, entry) is None
