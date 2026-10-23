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


@pytest.mark.parametrize("fake", [Protocol.ESP3], indirect=True)
async def test_commands_ignore_radio_responses(fake: FakeGateway, monkeypatch) -> None:
    """ESP3 answers each radio telegram with RET_OK; that is no answer to a command."""
    monkeypatch.setattr(gateway, "RESPONSE_SETTLE", 0.05)
    gw = Gateway(fake.protocol, TcpConnection("127.0.0.1", fake.port))
    await gw.connect()
    await fake.connected.wait()
    radio_ok = esp3.Esp3Packet(esp3.PacketType.RESPONSE, b"\x00")
    assert not gw._codec.answers_base_id(radio_ok)
    assert await gw.read_base_id() == 0xFFB74480

    await gw.send(RadioTelegram(Rorg.RPS, b"\x30", 0xFFB74481))
    started = asyncio.get_running_loop().time()
    fake.push(radio_ok.encode())
    assert await gw.write_repeater(1)
    assert asyncio.get_running_loop().time() - started >= 0.04  # waited for the radio answer
    await gw.close()


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


async def test_run_reconnects_after_server_restart(monkeypatch, caplog) -> None:
    monkeypatch.setattr(gateway, "RECONNECT_DELAYS", (0.05,))
    monkeypatch.setattr(gateway, "STABLE_AFTER", 0.1)
    server = await FakeGateway(Protocol.ESP3).start()
    port = server.port
    changes: list[bool] = []
    gw = Gateway(
        Protocol.ESP3, TcpConnection("127.0.0.1", port), on_connection_change=changes.append
    )
    task = asyncio.create_task(gw.run())
    await asyncio.wait_for(server.connected.wait(), 2)
    await server.stop()  # like a ser2net restart
    await asyncio.sleep(0.2)  # several reconnect attempts fail meanwhile
    assert not gw.connected
    server = await FakeGateway(Protocol.ESP3).start(port)
    await asyncio.wait_for(server.connected.wait(), 2)
    assert gw.connected
    assert await gw.read_base_id() == 0xFFB74480
    await asyncio.sleep(0.2)  # "restored" once the connection held
    await gw.close()
    await asyncio.wait_for(task, 1)
    await server.stop()
    assert changes == [True, False, True, False]
    # one warning for the outage, attempts at debug level, one info when it is back
    warnings = [r for r in caplog.records if r.levelname == "WARNING"]
    assert len(warnings) == 1
    assert any("restored" in r.getMessage() for r in caplog.records if r.levelname == "INFO")


async def test_esp3_ignores_non_radio_packets() -> None:
    received: list[RadioTelegram] = []
    gw = Gateway(Protocol.ESP3, TcpConnection("x", 0), on_telegram=received.append)
    gw._handle(esp3.Esp3Packet(esp3.PacketType.EVENT, b"\x02"))
    assert received == []


async def test_missing_serial_port_raises_oserror() -> None:
    from custom_components.enocean_eltako.protocol.transport import SerialConnection

    with pytest.raises(OSError):
        await Gateway(Protocol.ESP2, SerialConnection("/dev/does-not-exist", 9600)).connect()


@pytest.mark.parametrize("fake", [Protocol.ESP2], indirect=True)
async def test_bus_polling_is_dropped_before_dispatch(fake: FakeGateway) -> None:
    received: list[RadioTelegram] = []
    gw = Gateway(fake.protocol, TcpConnection("127.0.0.1", fake.port), on_telegram=received.append)
    await gw.connect()
    await fake.connected.wait()
    for address in range(1, 21):
        fake.push(esp2.Esp2Frame(esp2.HSeq.TCT, esp2.BUS_POLL, bytes(4), 0, address).encode())
        fake.push(esp2.Esp2Frame(esp2.HSeq.RMT, esp2.BUS_EMPTY, bytes(4)).encode())
    fake.push(esp2.Esp2Frame(esp2.HSeq.RMT, 0x07, bytes.fromhex("01000009"), 0x12, 0).encode())
    for _ in range(100):
        if received:
            break
        await asyncio.sleep(0.01)
    assert [t.sender for t in received] == [0x12]
    assert gw.polls_dropped == 40
    assert await gw.read_base_id() == 0xFFB74480  # bus traffic does not answer the command
    await gw.close()


@pytest.mark.parametrize("block", [True, False])
async def test_proxy_replay_with_reception_times(block: bool) -> None:
    """The Device Proxy sends a text block with reception times; without one the stream starts."""
    frame = esp2.Esp2Frame(esp2.HSeq.RRT, 0x05, bytes([0x70, 0, 0, 0]), 0x00216343, 0x30)
    live = esp2.Esp2Frame(esp2.HSeq.RRT, 0x05, bytes([0x50, 0, 0, 0]), 0x00216343, 0x30)
    request = asyncio.Event()

    async def proxy(reader, writer) -> None:
        assert await reader.readline() == b"EOPX REPLAY TS\n"
        request.set()
        if block:
            text = f"EOPX TS 1\n1700000000.250 {frame.encode().hex()}\nEOPX END\n".encode()
            writer.write(text[:9])  # in pieces, the binary stream right behind
            await writer.drain()
            await asyncio.sleep(0.02)
            writer.write(text[9:] + live.encode())
        else:
            writer.write(live.encode())
        await writer.drain()
        await reader.read()  # until the gateway closes the connection
        writer.close()

    server = await asyncio.start_server(proxy, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    replayed: list[tuple[RadioTelegram, float]] = []
    received: list[RadioTelegram] = []
    done: list[int] = []
    gw = Gateway(
        Protocol.ESP2,
        TcpConnection("127.0.0.1", port),
        on_telegram=received.append,
        on_replayed=lambda telegram, at: replayed.append((telegram, at)),
        on_replay_done=lambda: done.append(len(replayed)),
        hello=b"EOPX REPLAY TS\n",
    )
    await gw.connect()
    await asyncio.wait_for(request.wait(), 2)
    for _ in range(100):
        if received:
            break
        await asyncio.sleep(0.01)
    await gw.close()
    server.close()
    await server.wait_closed()
    assert [t.data for t in received] == [b"\x50"]  # the live telegram
    if block:
        assert [(t.data, at) for t, at in replayed] == [(b"\x70", 1700000000.25)]
        assert done == [1]  # once, after the last replayed telegram
    else:
        assert replayed == []
        assert done == []


async def test_proxy_replay_without_end_is_skipped(monkeypatch) -> None:
    """A replay block that never ends must not swallow the live telegrams behind it."""
    monkeypatch.setattr(gateway, "REPLAY_MAX_BYTES", 64)
    live = esp2.Esp2Frame(esp2.HSeq.RRT, 0x05, bytes([0x50, 0, 0, 0]), 0x00216343, 0x30)

    async def proxy(reader, writer) -> None:
        await reader.readline()
        writer.write(b"EOPX TS 5\n1700000000.250 a55a0b05\n" + bytes(64) + live.encode())
        await writer.drain()
        await reader.read()
        writer.close()

    server = await asyncio.start_server(proxy, "127.0.0.1", 0)
    received: list[RadioTelegram] = []
    gw = Gateway(
        Protocol.ESP2,
        TcpConnection("127.0.0.1", server.sockets[0].getsockname()[1]),
        on_telegram=received.append,
        hello=b"EOPX REPLAY TS\n",
    )
    await gw.connect()
    for _ in range(100):
        if received:
            break
        await asyncio.sleep(0.01)
    await gw.close()
    server.close()
    await server.wait_closed()
    assert [t.data for t in received] == [b"\x50"]


async def test_flapping_connection_warns_once_and_backs_off(monkeypatch, caplog) -> None:
    """A port that opens and drops at once (held by another program): one warning, no
    "restored", and the attempts slow down instead of reconnecting at once."""
    monkeypatch.setattr(gateway, "RECONNECT_DELAYS", (0.02, 0.05, 0.1))
    accepted = 0

    async def drop(_reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        nonlocal accepted
        accepted += 1
        writer.close()

    server = await asyncio.start_server(drop, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    gw = Gateway(Protocol.ESP3, TcpConnection("127.0.0.1", port))
    task = asyncio.create_task(gw.run())
    await asyncio.sleep(0.5)
    await gw.close()
    await asyncio.wait_for(task, 1)
    server.close()
    warnings = [r for r in caplog.records if r.levelname == "WARNING"]
    assert len(warnings) == 1
    assert not any("restored" in r.getMessage() for r in caplog.records)
    assert 3 <= accepted <= 10  # backoff: no tight reconnect loop
