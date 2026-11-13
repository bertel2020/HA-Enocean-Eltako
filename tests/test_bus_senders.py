"""Sender IDs of a bus group (00-00-B0-xx): suggested, assigned, rolled back and released like
the radio ones, and shared by every gateway of the group."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.enocean_eltako.const import DOMAIN
from custom_components.enocean_eltako.protocol import esp2
from custom_components.enocean_eltako.protocol.models import Protocol
from custom_components.enocean_eltako.protocol.send_queue import SendResult
from custom_components.enocean_eltako.protocol.telegram import RadioTelegram, Rorg

from .fake_gateway import FakeGateway
from .test_devices import _choose_model, _entity, _settle, _subentry

pytestmark = pytest.mark.usefixtures("socket_enabled")


@pytest.fixture(autouse=True)
def _short_bus_confirmation(monkeypatch) -> None:
    """The fake gateway never confirms: do not wait the 12 s of a real FAM14 per attempt."""
    from custom_components.enocean_eltako import device

    monkeypatch.setattr(device, "BUS_CONFIRM_TIMEOUT", 0.05)


B0 = 0x0000B000


def _entry(title: str, model: str, base: str, port: int, mode: str, subentries=()):
    return MockConfigEntry(
        domain=DOMAIN,
        title=title,
        unique_id=base,
        data={
            "model": model,
            "device": {"type": "tcp", "host": "127.0.0.1", "port": port},
            "base_id": base,
            "bus_group": "b1",
        },
        options={"message_delay": 0, "mode": mode},
        subentries_data=list(subentries),
    )


@pytest.fixture
async def bus(hass: HomeAssistant, request):
    """An FGW14-USB (always on) and a FAM14 (on demand) in one bus group."""
    fgw = await FakeGateway(Protocol.ESP2).start()
    fam = await FakeGateway(Protocol.ESP2).start()
    request.node.fgw_server = fgw
    own, other = getattr(request, "param", ((), ()))
    e_fgw = _entry("FGW14-USB", "fgw14_usb", "FF-AA-80-00", fgw.port, "always", own)
    e_fam = _entry("FAM14", "fam14", "FF-80-80-00", fam.port, "on_demand", other)
    e_fgw.add_to_hass(hass)
    e_fam.add_to_hass(hass)
    assert await hass.config_entries.async_setup(e_fgw.entry_id)
    await hass.async_block_till_done()
    yield e_fgw, e_fam
    await hass.config_entries.async_unload(e_fam.entry_id)
    await hass.config_entries.async_unload(e_fgw.entry_id)
    await fgw.stop()
    await fam.stop()


async def _add_switch(hass: HomeAssistant, entry, device_id: str, **fields):
    configure = hass.config_entries.subentries.async_configure
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "device"), context={"source": "user"}
    )
    result = await _choose_model(hass, result["flow_id"], "switch")
    result = await configure(result["flow_id"], {"next_step_id": "device"})
    return result, await configure(
        result["flow_id"],
        {"name": "Licht", "device_id": device_id, "platform": "switch", **fields},
    )


async def test_new_device_is_suggested_a_bus_id(hass: HomeAssistant, bus) -> None:
    e_fgw, _ = bus
    result = await hass.config_entries.subentries.async_init(
        (e_fgw.entry_id, "device"), context={"source": "user"}
    )
    result = await _choose_model(hass, result["flow_id"], "switch")
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"next_step_id": "device"}
    )
    schema = result["data_schema"].schema
    first = next(k for k in schema if str(k).startswith("sender_"))  # the rocker gets it
    assert first.description["suggested_value"] == "00-00-B0-00"


async def test_device_assigns_and_removal_blocks_a_bus_id(hass: HomeAssistant, bus) -> None:
    e_fgw, _ = bus
    pool = e_fgw.runtime_data.bus.senders.pool
    _, result = await _add_switch(hass, e_fgw, "05-10-A2-B3", sender_central="00-00-B0-05")
    assert result["type"] == "create_entry"
    await hass.async_block_till_done()
    assert pool.get(B0 + 5).owner == "device:05-10-A2-B3:central"
    assert e_fgw.runtime_data.senders.pool.get(B0 + 5) is None  # not the radio pool

    assert hass.config_entries.async_remove_subentry(e_fgw, next(iter(e_fgw.subentries)))
    await hass.async_block_till_done()
    assert pool.get(B0 + 5).state == "blocked"
    assert pool.next_free() == B0


async def test_failed_save_restores_the_bus_pool(hass: HomeAssistant, bus) -> None:
    e_fgw, _ = bus
    pool = e_fgw.runtime_data.bus.senders.pool
    pool.assign(B0 + 1, "device:05-10-A2-B6:central")  # another device
    _, result = await _add_switch(
        hass, e_fgw, "05-10-A2-B3", sender_central="00-00-B0-02", sender_rocker="00-00-B0-01"
    )
    assert result["type"] == "form" and result["errors"]
    assert pool.get(B0 + 2) is None  # the first ID of the failed attempt was rolled back
    assert pool.get(B0 + 1).owner == "device:05-10-A2-B6:central"


@pytest.mark.parametrize(
    "bus",
    [
        (
            (),
            (
                _subentry(
                    "switch",
                    "05-10-A2-B5",
                    "Licht Büro",
                    senders=[{"profile": "central", "sender_id": "00-00-B0-03"}],
                    platform="switch",
                ),
            ),
        )
    ],
    indirect=True,
)
async def test_reload_keeps_ids_of_devices_on_other_group_members(hass: HomeAssistant, bus) -> None:
    """The device sits on the FAM14, the pool is shared: the FGW14-USB reloading must not
    block the ID of a device it does not own."""
    e_fgw, e_fam = bus
    pool = e_fgw.runtime_data.bus.senders.pool
    pool.assign(B0 + 3, "device:05-10-A2-B5:central")
    pool.assign(B0 + 4, "device:05-10-A2-B9:central")  # a device nobody has any more
    assert await hass.config_entries.async_reload(e_fgw.entry_id)
    await hass.async_block_till_done()
    pool = e_fgw.runtime_data.bus.senders.pool
    assert pool.get(B0 + 3).state == "assigned"
    assert pool.get(B0 + 4).state == "blocked"


@pytest.mark.parametrize(
    "bus",
    [
        (
            (
                _subentry(
                    "switch",
                    "05-10-A2-B5",
                    "Bus light",
                    senders=[
                        {"profile": "central", "sender_id": "00-00-B0-03"},
                        {"profile": "rocker", "sender_id": "FF-AA-80-0F"},
                    ],
                    platform="light",
                ),
            ),
            (),
        )
    ],
    indirect=True,
)
async def test_command_from_a_bus_id_goes_over_the_bus_group(
    hass: HomeAssistant, bus, request
) -> None:
    """A device sends from its bus ID through the group's gateway, with the bus ID as sender."""
    e_fgw, _ = bus
    server = request.node.fgw_server
    await server.connected.wait()
    device = next(iter(e_fgw.runtime_data.devices.values()))
    assert device.senders["central"] in e_fgw.runtime_data.bus.senders.pool
    light = _entity(hass, "light", f"{e_fgw.unique_id}_05-10-A2-B5_1_light")
    await hass.services.async_call("light", "turn_on", {"entity_id": light})
    await _settle(hass)
    sent = esp2.encode_radio(RadioTelegram(Rorg.BS4, bytes.fromhex("01000009"), 0x0000B003, 0))
    assert sent in bytes(server.received)


@pytest.mark.parametrize(
    "bus",
    [
        (
            (
                _subentry(
                    "switch",
                    "05-10-A2-B5",
                    "Bus light",
                    senders=[{"profile": "central", "sender_id": "00-00-B0-03"}],
                    platform="light",
                ),
                _subentry(
                    "cover",
                    "05-10-A2-B6",
                    "Bus cover",
                    senders=[{"profile": "controller", "sender_id": "00-00-B0-04"}],
                ),
            ),
            (),
        )
    ],
    indirect=True,
)
async def test_bus_commands_wait_for_the_slow_fam14_confirmation(
    hass: HomeAssistant, bus, request
) -> None:
    """The FAM14 polls the actuators: up to 10 s, so a bus command waits longer and a run
    command of a cover is never repeated."""
    from custom_components.enocean_eltako.device import BUS_CONFIRM_TIMEOUT
    from custom_components.enocean_eltako.protocol.send_queue import MAX_RETRIES

    e_fgw, _ = bus
    await request.node.fgw_server.connected.wait()
    group = e_fgw.runtime_data.bus.group
    calls = []

    async def submit(telegram, priority, **kwargs):
        calls.append(kwargs)
        return SendResult.SENT

    group.submit = submit
    devices = {d.model.kind: d for d in e_fgw.runtime_data.devices.values()}
    devices["switch"].send(b"\x01\x00\x00\x09", profile="central")
    devices["cover"].send(b"\x00\x0a\x01\x09", profile="controller")
    await _settle(hass)
    assert [(c["timeout"], c["retries"]) for c in calls] == [
        (BUS_CONFIRM_TIMEOUT, MAX_RETRIES),
        (BUS_CONFIRM_TIMEOUT, 0),
    ]


@pytest.mark.parametrize(
    "bus",
    [
        (
            (
                _subentry(
                    "switch",
                    "05-10-A2-B5",
                    "Bus light",
                    senders=[{"profile": "central", "sender_id": "00-00-B0-03"}],
                    platform="light",
                ),
            ),
            (),
        )
    ],
    indirect=True,
)
async def test_swapping_the_only_bus_gateway_keeps_the_bus_ids(
    hass: HomeAssistant, bus, request
) -> None:
    """The group's pool is dropped with its last member and read again from the store when the
    reconfigured gateway joins: the devices keep their IDs, which stay assigned."""
    e_fgw, e_fam = bus
    await hass.config_entries.async_unload(e_fam.entry_id)  # the FGW14-USB is the only member
    store = e_fgw.runtime_data.bus.senders
    store.pool.assign(B0 + 3, "device:05-10-A2-B5:central")
    await store.async_save()

    server = request.node.fgw_server
    result = await e_fgw.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"model": "fgw14_usb"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "tcp"}
    )
    with patch(
        "custom_components.enocean_eltako.config_flow.probe_gateway",
        AsyncMock(return_value=0xFFAA8000),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"host": "127.0.0.1", "port": server.port}
        )
    assert result["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()

    pool = e_fgw.runtime_data.bus.senders.pool
    allocation = pool.get(B0 + 3)
    assert (allocation.owner, allocation.state) == ("device:05-10-A2-B5:central", "assigned")


async def test_takeover_assigns_bus_sender_ids_from_the_bus_pool(hass: HomeAssistant, bus) -> None:
    from custom_components.enocean_eltako.takeover import TakeoverDevice, async_take_over

    e_fgw, _ = bus
    device = TakeoverDevice(
        device_id=0x0510A2B3,
        name="Licht",
        old="light EEP",
        model="switch",
        data={"platform": "switch"},
        senders={"central": B0 + 7},
    )
    result = await async_take_over(hass, e_fgw, [device], carry=set())
    assert result.count == 1
    assert result.skipped == []  # not "out_of_range": the ID is in the bus range
    pool = e_fgw.runtime_data.bus.senders.pool
    assert pool.get(B0 + 7).owner == "device:05-10-A2-B3:central"
    assert e_fgw.runtime_data.senders.pool.get(B0 + 7) is None  # not the radio pool
