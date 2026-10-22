"""Action add_energy_devices: electricity meters as individual devices in the Energy dashboard."""

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError

from custom_components.enocean_eltako.const import DOMAIN

from .test_devices import _entity, _push, _settle, _subentry, gateway  # noqa: F401

pytestmark = pytest.mark.usefixtures("socket_enabled")

BASE = "FF-B7-44-80"
METERS = [
    [
        _subentry("meter", "05-00-00-12", "Waschmaschine"),
        _subentry("temp_humidity", "01-82-0A-11", "FAFT Aussen"),
    ]
]


class FakeManager:
    def __init__(self) -> None:
        self.data = {"energy_sources": [], "device_consumption": []}

    async def async_update(self, update: dict) -> None:
        self.data = {**self.data, **update}


async def _call(hass: HomeAssistant, **data):
    return await hass.services.async_call(
        DOMAIN, "add_energy_devices", data, blocking=True, return_response=True
    )


@pytest.mark.parametrize("gateway", METERS, indirect=True)
async def test_meters_are_added_once(
    hass: HomeAssistant,
    gateway,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entry, server = gateway
    _push(server, 0x07, bytes.fromhex("0003E80C"), 0x05000012)
    _push(server, 0x07, bytes.fromhex("00100009"), 0x05000012)
    await _settle(hass)
    manager = FakeManager()

    async def get_manager(_hass: HomeAssistant) -> FakeManager:
        return manager

    # the real manager needs the recorder; the preferences themselves are plain data
    hass.config.components.add("energy")
    monkeypatch.setattr("homeassistant.components.energy.data.async_get_manager", get_manager)
    energy = _entity(hass, "sensor", f"{BASE}_05-00-00-12_1_energy")
    power = _entity(hass, "sensor", f"{BASE}_05-00-00-12_1_power")

    result = await _call(hass)
    assert result == {"added": [energy]}

    assert manager.data["device_consumption"] == [{"stat_consumption": energy, "stat_rate": power}]
    assert await _call(hass, config_entry_id=entry.entry_id) == {"added": []}  # nothing twice


async def test_needs_energy_dashboard(hass: HomeAssistant) -> None:
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(DOMAIN, "add_energy_devices", {}, blocking=True)
