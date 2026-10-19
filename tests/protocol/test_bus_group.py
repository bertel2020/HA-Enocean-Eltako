"""Bus group: failover and on-demand members."""

import asyncio

import pytest

from custom_components.enocean_eltako.protocol import esp2
from custom_components.enocean_eltako.protocol.bus_group import BusGroup, BusMember
from custom_components.enocean_eltako.protocol.gateway import Gateway
from custom_components.enocean_eltako.protocol.models import Protocol
from custom_components.enocean_eltako.protocol.send_queue import SendQueue, SendResult
from custom_components.enocean_eltako.protocol.telegram import RadioTelegram, Rorg
from custom_components.enocean_eltako.protocol.transport import TcpConnection

from ..fake_gateway import FakeGateway

pytestmark = pytest.mark.usefixtures("socket_enabled")

CMD = RadioTelegram(Rorg.BS4, bytes.fromhex("01000009"), 0x0000B001)


async def _member(server: FakeGateway, name: str, on_demand: bool = False, idle=300.0):
    gw = Gateway(Protocol.ESP2, TcpConnection("127.0.0.1", server.port))
    queue = SendQueue(gw.send, is_connected=lambda: gw.connected, delay=0)
    queue.start()
    return BusMember(name, name, gw, queue, on_demand=on_demand, idle_timeout=idle)


async def _cleanup(*members: BusMember) -> None:
    for m in members:
        m.cancel_idle()
        await m.queue.stop()
        await m.gateway.close()


async def test_sends_over_connected_fgw14_and_leaves_fam14_alone() -> None:
    fgw, fam = await FakeGateway(Protocol.ESP2).start(), await FakeGateway(Protocol.ESP2).start()
    m_fgw = await _member(fgw, "fgw14")
    m_fam = await _member(fam, "fam14", on_demand=True)
    await m_fgw.gateway.connect()
    group = BusGroup("bus")
    group.add(m_fam)
    group.add(m_fgw)
    assert await group.submit(CMD) == SendResult.SENT
    await asyncio.sleep(0.05)
    assert bytes(fgw.received).endswith(esp2.encode_radio(CMD))
    assert not m_fam.connected
    await _cleanup(m_fgw, m_fam)
    await fgw.stop()
    await fam.stop()


async def test_failover_connects_fam14_on_demand_and_idles_out() -> None:
    fgw, fam = await FakeGateway(Protocol.ESP2).start(), await FakeGateway(Protocol.ESP2).start()
    m_fgw = await _member(fgw, "fgw14")
    m_fam = await _member(fam, "fam14", on_demand=True, idle=0.1)
    await fgw.stop()  # FGW14-USB offline
    group = BusGroup("bus")
    group.add(m_fgw)
    group.add(m_fam)
    assert await group.submit(CMD) == SendResult.SENT
    assert m_fam.connected
    assert group.failovers == 1
    await asyncio.sleep(0.05)
    assert bytes(fam.received).endswith(esp2.encode_radio(CMD))
    await asyncio.sleep(0.2)
    assert not m_fam.connected  # idle timeout
    await _cleanup(m_fgw, m_fam)
    await fam.stop()


async def test_failover_on_unconfirmed() -> None:
    a, b = await FakeGateway(Protocol.ESP2).start(), await FakeGateway(Protocol.ESP2).start()
    m_a, m_b = await _member(a, "a"), await _member(b, "b")
    await m_a.gateway.connect()
    await m_b.gateway.connect()
    group = BusGroup("bus")
    group.add(m_a)
    group.add(m_b)
    result = await group.submit(CMD, expect=lambda t: False, timeout=0.01)
    assert result == SendResult.UNCONFIRMED
    assert group.failovers == 1
    await asyncio.sleep(0.05)
    assert esp2.encode_radio(CMD) in bytes(b.received)
    await _cleanup(m_a, m_b)
    await a.stop()
    await b.stop()


async def test_all_offline_fails_and_pause_holds() -> None:
    server = await FakeGateway(Protocol.ESP2).start()
    port = server.port
    await server.stop()
    member = await _member(server, "fam14", on_demand=True)
    member.gateway.connection = TcpConnection("127.0.0.1", port)
    group = BusGroup("bus")
    remove = group.add(member)
    assert await group.submit(CMD) == SendResult.FAILED
    group.pause()
    group.resume()
    remove()
    assert len(group) == 0
    await _cleanup(member)
