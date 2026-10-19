"""Gateway connection against a fake TCP gateway."""

import asyncio

import pytest

from custom_components.enocean_eltako.protocol import esp2, esp3, gateway
from custom_components.enocean_eltako.protocol.gateway import Gateway
from custom_components.enocean_eltako.protocol.models import Protocol
from custom_components.enocean_eltako.protocol.telegram import RadioTelegram, Rorg
from custom_components.enocean_eltako.protocol.transport import TcpConnection

from ..fake_gateway import FakeGateway

pytestmark = pytest.mark.usefixtures("socket_enabled")


@pytest.fixture
async def fake(request):
    server = await FakeGateway(request.param).start()
    yield server
    await server.stop()


@pytest.mark.parametrize("fake", [Protocol.ESP2, Protocol.ESP3], indirect=True)
async def test_read_base_id(fake: FakeGateway) -> None:
    gw = Gateway(fake.protocol, TcpConnection("127.0.0.1", fake.port))
    await gw.connect()
    assert await gw.read_base_id() == 0xFFB74480
    await gw.close()
    assert not gw.connected


@pytest.mark.parametrize("fake", [Protocol.ESP2], indirect=True)
async def test_read_base_id_times_out(fake: FakeGateway) -> None:
    fake.base_id = None
    gw = Gateway(fake.protocol, TcpConnection("127.0.0.1", fake.port))
    await gw.connect()
    assert await gw.read_base_id(timeout=0.1) is None
    await gw.close()


@pytest.mark.parametrize("fake", [Protocol.ESP2], indirect=True)
async def test_receive_and_send(fake: FakeGateway) -> None:
    received: list[RadioTelegram] = []
    gw = Gateway(fake.protocol, TcpConnection("127.0.0.1", fake.port), on_telegram=received.append)
    await gw.connect()
    await fake.connected.wait()
    fake.push(
        esp2.Esp2Frame(esp2.HSeq.RRT, 0x05, bytes([0x70, 0, 0, 0]), 0x00216343, 0x30).encode()
    )
    for _ in range(50):
        if received:
            break
        await asyncio.sleep(0.01)
    assert received == [RadioTelegram(Rorg.RPS, b"\x70", 0x00216343, 0x30)]

    telegram = RadioTelegram(Rorg.RPS, b"\x10", 0xFFB74481, 0x30)
    await gw.send(telegram)
    await asyncio.sleep(0.05)
    assert bytes(fake.received).endswith(esp2.encode_radio(telegram))
    await gw.close()


async def test_send_when_disconnected_raises() -> None:
    gw = Gateway(Protocol.ESP3, TcpConnection("127.0.0.1", 1))
    with pytest.raises(ConnectionError):
        await gw.send(RadioTelegram(Rorg.RPS, b"\x10", 1))


async def test_connect_refused_raises() -> None:
    server = await FakeGateway(Protocol.ESP3).start()
    port = server.port
    await server.stop()
    with pytest.raises(OSError):
        await Gateway(Protocol.ESP3, TcpConnection("127.0.0.1", port)).connect()


async def test_run_reconnects_after_server_restart(monkeypatch) -> None:
    monkeypatch.setattr(gateway, "RECONNECT_DELAYS", (0.05,))
    server = await FakeGateway(Protocol.ESP3).start()
    port = server.port
    changes: list[bool] = []
    gw = Gateway(
        Protocol.ESP3, TcpConnection("127.0.0.1", port), on_connection_change=changes.append
    )
    task = asyncio.create_task(gw.run())
    await asyncio.wait_for(server.connected.wait(), 2)
    await server.stop()  # like a ser2net restart
    await asyncio.sleep(0.2)
    assert not gw.connected
    server = await FakeGateway(Protocol.ESP3).start(port)
    await asyncio.wait_for(server.connected.wait(), 2)
    assert gw.connected
    assert await gw.read_base_id() == 0xFFB74480
    await gw.close()
    await asyncio.wait_for(task, 1)
    await server.stop()
    assert changes == [True, False, True, False]


async def test_esp3_ignores_non_radio_packets() -> None:
    received: list[RadioTelegram] = []
    gw = Gateway(Protocol.ESP3, TcpConnection("x", 0), on_telegram=received.append)
    gw._handle(esp3.Esp3Packet(esp3.PacketType.EVENT, b"\x02"))
    assert received == []
