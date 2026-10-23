"""The weather blueprints run: their templates see the covers' automation mode and the sensors."""

import shutil
from datetime import timedelta
from pathlib import Path

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
    async_mock_service,
)


@pytest.fixture
def expected_lingering_timers() -> bool:
    return True  # the time triggers of the blueprints wait for tomorrow


SOURCE = Path(__file__).parents[1] / "blueprints/automation/enocean_eltako"


def _entity(hass: HomeAssistant, domain: str, name: str, device_id: str | None = None) -> str:
    entry = er.async_get(hass).async_get_or_create(
        domain, "test", name, suggested_object_id=name, device_id=device_id
    )
    return entry.entity_id


async def _cover(hass: HomeAssistant, name: str, mode: str, position: int = 100) -> str:
    config = MockConfigEntry(domain="test")
    config.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=config.entry_id, identifiers={("test", name)}
    )
    cover = _entity(hass, "cover", name, device.id)
    select = _entity(hass, "select", f"{name}_mode", device.id)
    hass.states.async_set(cover, "open", {"current_position": position})
    hass.states.async_set(select, mode)
    return cover


async def _setup(hass: HomeAssistant, blueprint: str, inputs: dict) -> None:
    target = Path(hass.config.path("blueprints/automation/enocean_eltako"))
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy(SOURCE / f"{blueprint}.yaml", target / f"{blueprint}.yaml")
    assert await async_setup_component(
        hass,
        "automation",
        {
            "automation": {
                "use_blueprint": {"path": f"enocean_eltako/{blueprint}.yaml", "input": inputs}
            }
        },
    )
    await hass.async_block_till_done()


async def _wait(hass: HomeAssistant, minutes: int) -> None:
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=minutes))
    await hass.async_block_till_done()


async def test_sun_shading(hass: HomeAssistant) -> None:
    calls = async_mock_service(hass, "cover", "set_cover_position")
    shaded = await _cover(hass, "wohnen", "both")
    off = await _cover(hass, "bad", "off")
    sun = _entity(hass, "sensor", "sun_south")
    warm = _entity(hass, "sensor", "temperature")
    hass.states.async_set(sun, "0")
    hass.states.async_set(warm, "12")
    await _setup(
        hass,
        "sun_shading",
        {
            "covers": [shaded, off],
            "sun_sensor": sun,
            "temperature_sensor": warm,
            "min_temperature": 18,
            "shade_position": 30,
        },
    )

    hass.states.async_set(sun, "30000")  # strong, but too cold to shade
    await hass.async_block_till_done()
    await _wait(hass, 6)
    assert not calls

    hass.states.async_set(sun, "0")
    await hass.async_block_till_done()
    hass.states.async_set(warm, "22")
    hass.states.async_set(sun, "30000")
    await hass.async_block_till_done()
    await _wait(hass, 6)
    assert [(c.data["entity_id"], c.data["position"]) for c in calls] == [([shaded], 30)]

    # the sun is gone: only a cover still in the shading position is opened again
    calls.clear()
    hass.states.async_set(shaded, "open", {"current_position": 55})  # moved by hand
    hass.states.async_set(sun, "1000")
    await hass.async_block_till_done()
    await _wait(hass, 20)
    assert not calls
    hass.states.async_set(shaded, "open", {"current_position": 30})
    hass.states.async_set(sun, "30000")
    await hass.async_block_till_done()
    hass.states.async_set(sun, "1000")
    await hass.async_block_till_done()
    await _wait(hass, 40)
    assert [(c.data["entity_id"], c.data["position"]) for c in calls] == [([shaded], 100)]


async def test_dusk_dawn(hass: HomeAssistant, freezer) -> None:
    freezer.move_to("2026-06-02T03:00:00+00:00")  # evening in the test time zone (US/Pacific)
    calls = async_mock_service(hass, "cover", "set_cover_position")
    lights = async_mock_service(hass, "homeassistant", "turn_on")
    off_lights = async_mock_service(hass, "homeassistant", "turn_off")
    evening = await _cover(hass, "abend", "evening")
    morning = await _cover(hass, "morgen", "morning")
    both = await _cover(hass, "beides", "both")
    dawn = _entity(hass, "sensor", "dawn")
    hass.states.async_set(dawn, "300")
    lamp = _entity(hass, "light", "lampe")
    hass.states.async_set(lamp, "off")
    await _setup(
        hass,
        "dusk_dawn",
        {"dawn_sensor": dawn, "covers": [evening, morning, both], "lights": [lamp]},
    )

    hass.states.async_set(dawn, "5")
    await hass.async_block_till_done()
    await _wait(hass, 11)
    assert [(c.data["entity_id"], c.data["position"]) for c in calls] == [([evening, both], 0)]
    assert [c.data["entity_id"] for c in lights] == [[lamp]]

    calls.clear()
    freezer.move_to("2026-06-02T15:00:00+00:00")  # morning, 08:00 local
    hass.states.async_set(dawn, "200")
    await hass.async_block_till_done()
    await _wait(hass, 11)
    # the morning time trigger and the bright-for-a-while trigger may both fire: same command twice
    assert {(tuple(c.data["entity_id"]), c.data["position"]) for c in calls} == {
        ((morning, both), 100)
    }
    assert {tuple(c.data["entity_id"]) for c in off_lights} == {(lamp,)}


@pytest.mark.parametrize(
    ("window", "rain", "expected"),
    [("on", "on", "window"), ("off", "on", None)],
)
async def test_weather_warning(
    hass: HomeAssistant, window: str, rain: str, expected: str | None
) -> None:
    notices = async_mock_service(hass, "test", "notify")
    handle = _entity(hass, "binary_sensor", "fenstergriff")
    rain_sensor = _entity(hass, "binary_sensor", "regen")
    hass.states.async_set(handle, "off", {"friendly_name": "Fenstergriff Essen"})
    hass.states.async_set(rain_sensor, "off")
    await _setup(
        hass,
        "weather_warning",
        {
            "windows": [handle],
            "rain": rain_sensor,
            "notify": [
                {
                    "action": "test.notify",
                    "data": {"message": "{{ message }}", "reason": "{{ reason }}"},
                }
            ],
        },
    )
    hass.states.async_set(rain_sensor, rain)  # it starts to rain
    await hass.async_block_till_done()
    hass.states.async_set(handle, window, {"friendly_name": "Fenstergriff Essen"})
    await hass.async_block_till_done()
    if expected is None:
        assert not notices
        return
    assert notices and notices[-1].data["reason"] == expected
    assert "Fenstergriff Essen" in notices[-1].data["message"]
