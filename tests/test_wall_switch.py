"""I4: actuators without status feedback take their state from a taught-in wall switch."""

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.enocean_eltako.const import DOMAIN
from custom_components.enocean_eltako.device import wall_switch_state
from custom_components.enocean_eltako.protocol.models import Protocol

from .fake_gateway import FakeGateway
from .test_devices import BASE, _entity, _push, _settle
from .test_restore_and_edges import _sub, uid

pytestmark = pytest.mark.usefixtures("socket_enabled")

RPS = 0x05  # ESP2 ORG of an F6 telegram
WALL = 0x0510AA01
WALL_TOGGLE = 0x0510AA02
PRESS_A0, PRESS_A1, PRESS_B0, RELEASE = b"\x30", b"\x10", b"\x70", b"\x00"


def test_wall_switch_state() -> None:
    assert wall_switch_state(1, "a0", "a1", None) is True  # R1=1 is A0
    assert wall_switch_state(0, "a0", "a1", True) is False
    assert wall_switch_state(3, "a0", "a1", True) is None  # another button
    assert wall_switch_state(3, "b0", "b0", None) is True  # toggle
    assert wall_switch_state(3, "b0", "b0", True) is False
    assert wall_switch_state(7, "a0", "a1", None) is None


@pytest.fixture
async def actuators(hass: HomeAssistant):
    server = await FakeGateway(Protocol.ESP2).start()
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=BASE,
        data={
            "model": "fam_usb",
            "device": {"type": "tcp", "host": "127.0.0.1", "port": server.port},
            "base_id": BASE,
        },
        options={"message_delay": 0},
        subentries_data=[
            _sub(
                "switch",
                "05-00-00-11",
                "Flur",
                [("central", "FF-B7-44-91")],
                wall_switch="05-10-AA-01",
                wall_on_button="a0",
                wall_off_button="a1",
            ),
            _sub(
                "switch",
                "05-00-00-12",
                "Keller",
                [("central", "FF-B7-44-92")],
                platform="switch",
                wall_switch="05-10-AA-02",
                wall_on_button="b0",
                wall_off_button="b0",
            ),
        ],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    await server.connected.wait()
    yield server
    await hass.config_entries.async_unload(entry.entry_id)
    await server.stop()


async def test_wall_switch_sets_assumed_state(hass: HomeAssistant, actuators) -> None:
    server = actuators
    light = _entity(hass, "light", uid("05-00-00-11", "light"))
    _push(server, RPS, PRESS_A0, WALL, 0x30)
    await _settle(hass)
    state = hass.states.get(light)
    assert state.state == "on"
    assert state.attributes["assumed_state"] is True  # a press is no confirmation
    _push(server, RPS, RELEASE, WALL, 0x20)
    _push(server, RPS, PRESS_A1, WALL, 0x30)
    await _settle(hass)
    assert hass.states.get(light).state == "off"


async def test_wall_switch_toggles(hass: HomeAssistant, actuators) -> None:
    server = actuators
    switch = _entity(hass, "switch", uid("05-00-00-12", "switch"))
    for expected in ("on", "off", "on"):
        _push(server, RPS, PRESS_B0, WALL_TOGGLE, 0x30)
        await _settle(hass)
        assert hass.states.get(switch).state == expected
        _push(server, RPS, RELEASE, WALL_TOGGLE, 0x20)
        await _settle(hass)
