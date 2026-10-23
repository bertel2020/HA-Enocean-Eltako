"""Stored data: every step of the migration from the oldest layout up to the current one."""

import pytest
from homeassistant.config_entries import ConfigEntryState, ConfigSubentry, ConfigSubentryData
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.enocean_eltako import async_migrate_entry
from custom_components.enocean_eltako.config_flow import EnOceanEltakoConfigFlow
from custom_components.enocean_eltako.const import DOMAIN, SUBENTRY_SCHEMA

from .test_devices import BASE, _subentry, gateway  # noqa: F401

pytestmark = pytest.mark.usefixtures("socket_enabled")

DATA = {
    "model": "fam_usb",
    "device": {"type": "tcp", "host": "127.0.0.1", "port": 1},
    "base_id": BASE,
}


def _entry(minor_version: int, subentries: list[ConfigSubentryData], version: int = 1):
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id=BASE,
        version=version,
        minor_version=minor_version,
        data=DATA,
        subentries_data=subentries,
    )


async def test_oldest_layout_reaches_the_current_one(hass: HomeAssistant) -> None:
    """1.1 data passes every step in one go; devices the catalog no longer knows survive."""
    entry = _entry(
        1,
        [
            ConfigSubentryData(
                data={
                    "schema": 1,
                    "model": "switch",
                    "device_id": "00-2A-0B-0C",
                    "sender_id": "FF-B7-44-81",
                },
                subentry_type="device",
                title="Taster",
                unique_id="00-2A-0B-0C",
            ),
            ConfigSubentryData(
                data={"schema": 1, "model": "gone_model", "device_id": "01-00-00-08"},
                subentry_type="device",
                title="Altes Modell",
                unique_id="01-00-00-08",
            ),
        ],
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is not ConfigEntryState.MIGRATION_ERROR
    assert entry.minor_version == EnOceanEltakoConfigFlow.MINOR_VERSION
    data = {s.title: s.data for s in entry.subentries.values()}
    assert all(d["schema"] == SUBENTRY_SCHEMA for d in data.values())
    assert data["Taster"]["senders"][0]["sender_id"] == "FF-B7-44-81"
    assert data["Taster"]["senders"][0]["profile"] == "central"  # 1.2 result, passed on to 1.3
    assert "rocker_on_button" not in data["Taster"]  # no rocker sender, nothing to keep
    assert data["Altes Modell"]["model"] == "gone_model"  # kept, not dropped or crashing


async def test_current_data_is_left_alone(hass: HomeAssistant, gateway) -> None:  # noqa: F811
    entry, _ = gateway
    sub = _subentry("rocker", "00-2A-0B-0C", "Taster")
    hass.config_entries.async_add_subentry(
        entry,
        ConfigSubentry(
            data={**sub["data"], "schema": SUBENTRY_SCHEMA},
            subentry_type="device",
            title="Taster",
            unique_id="00-2A-0B-0C",
        ),
    )
    await hass.async_block_till_done()
    before = {s.title: dict(s.data) for s in entry.subentries.values()}
    assert await async_migrate_entry(hass, entry)
    assert {s.title: dict(s.data) for s in entry.subentries.values()} == before
    assert entry.minor_version == EnOceanEltakoConfigFlow.MINOR_VERSION


async def test_newer_data_is_refused(hass: HomeAssistant) -> None:
    """A downgrade (entry from a newer major version) is not migrated."""
    entry = _entry(1, [], version=2)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.MIGRATION_ERROR


async def test_cover_routing_both_becomes_one_sender(hass: HomeAssistant) -> None:
    """1.4 -> 1.5: "both" keeps the controller, or the only sender a cover has."""

    def cover(title: str, device_id: str, profiles: list[str], routing: str) -> ConfigSubentryData:
        return ConfigSubentryData(
            data={
                "schema": 4,
                "model": "cover",
                "device_id": device_id,
                "senders": [
                    {"profile": p, "sender_id": f"FF-B7-44-{0x80 + i:02X}"}
                    for i, p in enumerate(profiles)
                ],
                "routing": routing,
            },
            subentry_type="device",
            title=title,
            unique_id=device_id,
        )

    entry = _entry(
        4,
        [
            cover("Beide", "05-00-00-30", ["controller", "direction_rocker"], "both"),
            cover("Nur Taster", "05-00-00-31", ["direction_rocker"], "both"),
            cover(
                "Taster gewählt",
                "05-00-00-32",
                ["controller", "direction_rocker"],
                "direction_rocker",
            ),
        ],
    )
    entry.add_to_hass(hass)
    assert await async_migrate_entry(hass, entry)
    data = {s.title: s.data for s in entry.subentries.values()}
    assert data["Beide"]["routing"] == "controller"
    assert data["Nur Taster"]["routing"] == "direction_rocker"
    assert data["Taster gewählt"]["routing"] == "direction_rocker"  # a chosen one stays
    assert all(d["schema"] == SUBENTRY_SCHEMA for d in data.values())
    assert entry.minor_version == EnOceanEltakoConfigFlow.MINOR_VERSION
