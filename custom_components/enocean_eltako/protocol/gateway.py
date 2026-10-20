"""Gateway connection: framing, base ID query, receive loop and reconnect."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from collections.abc import Awaitable, Callable

from . import esp2, esp3
from .models import Protocol
from .telegram import RadioTelegram
from .transport import Connection, open_connection

_LOGGER = logging.getLogger(__name__)

RECONNECT_DELAYS = (1, 2, 5, 10, 30, 60)

Opener = Callable[[Connection], Awaitable[tuple[asyncio.StreamReader, asyncio.StreamWriter]]]


REPLAY_BLOCK = b"EOPX TS "  # start of the EnOcean Proxy replay with reception times
REPLAY_END = b"EOPX END\n"


class _Codec:
    """Protocol-specific framing behind one interface."""

    def __init__(self, protocol: Protocol) -> None:
        self.protocol = protocol
        self.decoder = esp2.Esp2Decoder() if protocol is Protocol.ESP2 else esp3.Esp3Decoder()

    def base_id_request(self) -> bytes:
        if self.protocol is Protocol.ESP2:
            return esp2.encode_command(esp2.CMD_RD_IDBASE)
        return esp3.encode_common_command(esp3.CO_RD_IDBASE)

    def base_id(self, item: esp2.Esp2Frame | esp3.Esp3Packet) -> int | None:
        if isinstance(item, esp2.Esp2Frame):
            return esp2.parse_base_id(item)
        return esp3.parse_base_id(item)

    def answers_base_id(self, item: esp2.Esp2Frame | esp3.Esp3Packet) -> bool:
        """ESP3 answers in order; ESP2 also sends unrelated messages (OK, INF_INIT, bus)."""
        if isinstance(item, esp2.Esp2Frame):
            return item.hseq == esp2.HSeq.RMT and item.org in (esp2.MSG_INF_IDBASE, esp2.MSG_ERR)
        return item.packet_type == esp3.PacketType.RESPONSE

    def is_noise(self, item: esp2.Esp2Frame | esp3.Esp3Packet) -> bool:
        """Bus polling and empty answers: dropped before they reach the dispatcher."""
        return isinstance(item, esp2.Esp2Frame) and esp2.is_bus_control(item)

    def radio(self, item: esp2.Esp2Frame | esp3.Esp3Packet) -> RadioTelegram | None:
        if isinstance(item, esp2.Esp2Frame):
            return esp2.decode_radio(item)
        return esp3.decode_radio(item)

    def encode_radio(self, telegram: RadioTelegram) -> bytes:
        if self.protocol is Protocol.ESP2:
            return esp2.encode_radio(telegram)
        return esp3.encode_radio(telegram)


class Gateway:
    """One gateway on a serial or TCP connection.

    connect() opens the stream and starts reading; run() keeps it connected until close().
    Received radio telegrams go to on_telegram. send() is the low-level write used by the
    send queue, never called directly by entities.
    """

    def __init__(
        self,
        protocol: Protocol,
        connection: Connection,
        *,
        on_telegram: Callable[[RadioTelegram], None] | None = None,
        on_connection_change: Callable[[bool], None] | None = None,
        opener: Opener = open_connection,
        hello: bytes = b"",
        on_replayed: Callable[[RadioTelegram, float], None] | None = None,
    ) -> None:
        self.protocol = protocol
        self.connection = connection
        self._on_telegram = on_telegram
        self._on_connection_change = on_connection_change
        self._opener = opener
        self._hello = hello  # sent first after every connect (EnOcean Proxy replay request)
        self._on_replayed = on_replayed
        self._codec = _Codec(protocol)
        self._writer: asyncio.StreamWriter | None = None
        self._reader_task: asyncio.Task[None] | None = None
        self._disconnected = asyncio.Event()
        self._disconnected.set()
        self._closing = False
        self._command_lock = asyncio.Lock()
        self._response: asyncio.Future[esp2.Esp2Frame | esp3.Esp3Packet] | None = None
        self._response_match: Callable[[esp2.Esp2Frame | esp3.Esp3Packet], bool] | None = None
        self.telegrams_received = 0
        self.polls_dropped = 0
        self.last_telegram: float | None = None  # time.time() of the last radio telegram
        self._outage_logged = False  # one warning per outage, then debug until it is back

    @property
    def connected(self) -> bool:
        return not self._disconnected.is_set()

    async def connect(self, timeout: float = 10) -> None:
        """Open the connection; raises OSError or TimeoutError."""
        self._codec = _Codec(self.protocol)
        async with asyncio.timeout(timeout):
            reader, self._writer = await self._opener(self.connection)
        if self._hello:
            self._writer.write(self._hello)
        self._disconnected.clear()
        self._reader_task = asyncio.create_task(self._read_loop(reader))
        if self._outage_logged:
            _LOGGER.info("Connection to %s restored", self.connection)
            self._outage_logged = False
        else:
            _LOGGER.debug("Connected to %s", self.connection)
        if self._on_connection_change:
            self._on_connection_change(True)

    async def run(self) -> None:
        """Stay connected until close(), reconnecting with backoff."""
        attempt = 0
        while not self._closing:
            if not self.connected:
                try:
                    await self.connect()
                except (OSError, TimeoutError) as err:
                    delay = RECONNECT_DELAYS[min(attempt, len(RECONNECT_DELAYS) - 1)]
                    attempt += 1
                    self._log_outage(
                        "Cannot connect to %s (%s), retrying in %s s", self.connection, err, delay
                    )
                    await asyncio.sleep(delay)
                    continue
                attempt = 0
            await self._disconnected.wait()

    async def read_base_id(self, timeout: float = 3) -> int | None:
        """Ask the gateway for its base ID; None if it does not answer."""
        response = await self._command(
            self._codec.base_id_request(), timeout, self._codec.answers_base_id
        )
        return self._codec.base_id(response) if response is not None else None

    async def write_repeater(self, level: int, timeout: float = 3) -> bool:
        """ESP3 gateways: set the repeater (0 off, 1 or 2 levels); True when acknowledged."""
        if self.protocol is not Protocol.ESP3:
            raise ValueError("only ESP3 gateways have a repeater command")
        response = await self._command(
            esp3.encode_repeater(level),
            timeout,
            lambda item: (
                isinstance(item, esp3.Esp3Packet) and item.packet_type == esp3.PacketType.RESPONSE
            ),
        )
        return isinstance(response, esp3.Esp3Packet) and esp3.is_ok(response)

    async def send(self, telegram: RadioTelegram) -> None:
        """Write one radio telegram; raises ConnectionError when not connected."""
        await self._write(self._codec.encode_radio(telegram))

    async def close(self) -> None:
        """Disconnect for good; run() returns."""
        self._closing = True
        await self._disconnect()

    async def disconnect(self) -> None:
        """Disconnect without stopping for good (on-demand gateways)."""
        await self._disconnect()

    async def _command(
        self,
        frame: bytes,
        timeout: float,
        match: Callable[[esp2.Esp2Frame | esp3.Esp3Packet], bool],
    ) -> esp2.Esp2Frame | esp3.Esp3Packet | None:
        async with self._command_lock:
            self._response = asyncio.get_running_loop().create_future()
            self._response_match = match
            try:
                await self._write(frame)
                async with asyncio.timeout(timeout):
                    return await self._response
            except TimeoutError:
                return None
            finally:
                self._response = None
                self._response_match = None

    async def _write(self, data: bytes) -> None:
        if self._writer is None or not self.connected:
            raise ConnectionError(f"{self.connection} is not connected")
        self._writer.write(data)
        await self._writer.drain()

    async def _read_loop(self, reader: asyncio.StreamReader) -> None:
        pending = bytearray() if self._hello else None  # a replay block may come first
        try:
            while chunk := await reader.read(1024):
                if pending is not None:
                    pending += chunk
                    chunk, done = self._take_replay(pending)
                    if not done:
                        continue
                    pending = None
                for item in self._codec.decoder.feed(chunk):
                    self._handle(item)
        except OSError as err:
            self._log_outage("Connection to %s lost: %s", self.connection, err)
        if not self._disconnected.is_set():
            # stream ended by the other side (EOF or error), not by _disconnect()
            self._log_outage("Connection to %s closed", self.connection)
            await self._disconnect()

    def _take_replay(self, buffer: bytearray) -> tuple[bytes, bool]:
        """EnOcean Proxy replay with reception times: "EOPX TS <n>", n lines
        "<unix time> <hex frame>", "EOPX END". Returns the bytes after the block and whether
        the start of the stream is settled (no block, or the block complete)."""
        head = bytes(buffer[: len(REPLAY_BLOCK)])
        if not REPLAY_BLOCK.startswith(head) and not head.startswith(REPLAY_BLOCK):
            return bytes(buffer), True  # an older proxy or none: binary from the start
        if len(buffer) < len(REPLAY_BLOCK):
            return b"", False
        end = buffer.find(REPLAY_END)
        if end < 0:
            return b"", False
        block, rest = bytes(buffer[:end]), bytes(buffer[end + len(REPLAY_END) :])
        replayed = 0
        for line in block.decode("ascii", "replace").splitlines()[1:]:
            stamp, _, hex_frame = line.partition(" ")
            try:
                items = self._codec.decoder.feed(bytes.fromhex(hex_frame))
                received_at = float(stamp)
            except ValueError:
                continue
            for item in items:
                if (telegram := self._codec.radio(item)) is None:
                    continue
                replayed += 1
                if self._on_replayed is not None:
                    self._on_replayed(telegram, received_at)
                elif self._on_telegram is not None:
                    self._on_telegram(telegram)
        _LOGGER.info("%s: %d telegrams replayed by the EnOcean Proxy", self.connection, replayed)
        return rest, True

    def _log_outage(self, message: str, *args: object) -> None:
        """Warn once per outage; repeats (reconnect attempts, flapping port) only at debug."""
        if self._outage_logged:
            _LOGGER.debug(message, *args)
            return
        _LOGGER.warning(message, *args)
        self._outage_logged = True

    def _handle(self, item: esp2.Esp2Frame | esp3.Esp3Packet) -> None:
        if (
            self._response is not None
            and not self._response.done()
            and self._response_match is not None
            and self._response_match(item)
        ):
            self._response.set_result(item)
            return
        if self._codec.is_noise(item):
            self.polls_dropped += 1
            return
        telegram = self._codec.radio(item)
        if telegram is None:
            return
        self.telegrams_received += 1
        self.last_telegram = time.time()
        if self._on_telegram:
            try:
                self._on_telegram(telegram)
            except Exception:
                _LOGGER.exception("Error handling telegram %s", telegram)

    async def _disconnect(self) -> None:
        was_connected = self.connected
        self._disconnected.set()
        task, self._reader_task = self._reader_task, None
        if task is not None and task is not asyncio.current_task():
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        writer, self._writer = self._writer, None
        if writer is not None:
            writer.close()
            with contextlib.suppress(OSError):
                await writer.wait_closed()
        if was_connected and self._on_connection_change:
            self._on_connection_change(False)
