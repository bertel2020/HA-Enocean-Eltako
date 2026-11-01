"""Device triggers for rocker gestures."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.enocean_eltako import device_trigger
from custom_components.enocean_eltako.const import DOMAIN
from custom_components.enocean_eltako.gestures import EVENT_TYPES


def _entry_with(kind: str, prefix: str) -> SimpleNamespace:
    rocker = SimpleNamespace(model=SimpleNamespace(kind=kind), unique_prefix=prefix)
    return SimpleNamespace(runtime_data=SimpleNamespace(devices={"sub": rocker}))


def _device(hass: HomeAssistant, identifier: str) -> str:
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)
    return (
        dr.async_get(hass)
        .async_get_or_create(config_entry_id=entry.entry_id, identifiers={(DOMAIN, identifier)})
        .id
    )


async def test_unknown_device_has_no_triggers(hass: HomeAssistant) -> None:
    assert await device_trigger.async_get_triggers(hass, "missing") == []


async def test_rocker_offers_every_button_and_gesture(hass: HomeAssistant) -> None:
    device_id = _device(hass, "rocker1")
    with patch.object(
        hass.config_entries, "async_loaded_entries", return_value=[_entry_with("rocker", "rocker1")]
    ):
        triggers = await device_trigger.async_get_triggers(hass, device_id)
    assert len(triggers) == len(device_trigger.BUTTONS) * len(EVENT_TYPES)
    assert {t["subtype"] for t in triggers} == set(device_trigger.BUTTONS)


async def test_non_rocker_device_has_no_triggers(hass: HomeAssistant) -> None:
    device_id = _device(hass, "light1")
    with patch.object(
        hass.config_entries, "async_loaded_entries", return_value=[_entry_with("light", "light1")]
    ):
        assert await device_trigger.async_get_triggers(hass, device_id) == []


async def test_attach_trigger_listens_for_the_button_event(hass: HomeAssistant) -> None:
    config = {"device_id": "abc", "type": EVENT_TYPES[0], "subtype": "a0"}
    with patch.object(
        device_trigger.event_trigger, "async_attach_trigger", AsyncMock(return_value=lambda: None)
    ) as attach:
        await device_trigger.async_attach_trigger(hass, config, AsyncMock(), {})
    event_config = attach.call_args.args[1]
    assert event_config["event_data"] == {
        "device_id": "abc",
        "button": "a0",
        "type": EVENT_TYPES[0],
    }
