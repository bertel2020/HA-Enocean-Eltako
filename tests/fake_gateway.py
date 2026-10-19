"""A fake ESP2/ESP3 gateway on 127.0.0.1 for tests (ser2net-style TCP)."""

from __future__ import annotations

import asyncio

from custom_components.enocean_eltako.protocol import esp2, esp3
from custom_components.enocean_eltako.protocol.models import Protocol


class FakeGateway:
    """Answers base ID requests, records writes, can push telegrams and drop clients."""

    def __init__(self, protocol: Protocol, base_id: int | None = 0xFFB74480) -> None:
        self.protocol = protocol
        self.base_id = base_id
        self.received = bytearray()
        self.port = 0
        self._server: asyncio.Server | None = None
        self._writers: list[asyncio.StreamWriter] = []
        self.connected = asyncio.Event()

    async def start(self, port: int = 0) -> FakeGateway:
        self._server = await asyncio.start_server(self._client, "127.0.0.1", port)
        self.port = self._server.sockets[0].getsockname()[1]
        return self

    async def stop(self) -> None:
        self.drop_clients()
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()

    def drop_clients(self) -> None:
        for writer in self._writers:
            writer.close()
        self._writers.clear()
        self.connected.clear()

    def push(self, raw: bytes) -> None:
        for writer in self._writers:
            writer.write(raw)

    async def _client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self._writers.append(writer)
        self.connected.set()
        while data := await reader.read(1024):
            self.received += data
            if self.base_id is None:
                continue
            if data == esp2.encode_command(esp2.CMD_RD_IDBASE):
                writer.write(
                    esp2.Esp2Frame(
                        esp2.HSeq.RMT, esp2.MSG_INF_IDBASE, self.base_id.to_bytes(4, "big")
                    ).encode()
                )
            elif data[:7] == esp3.encode_repeater(0)[:7]:  # CO_WR_REPEATER header
                writer.write(esp3.Esp3Packet(esp3.PacketType.RESPONSE, b"\x00").encode())
            elif data == esp3.encode_common_command(esp3.CO_RD_IDBASE):
                writer.write(
                    esp3.Esp3Packet(
                        esp3.PacketType.RESPONSE, b"\x00" + self.base_id.to_bytes(4, "big")
                    ).encode()
                )
