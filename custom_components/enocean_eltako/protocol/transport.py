"""Byte transports: USB serial (pyserial-asyncio-fast) and TCP (asyncio streams, e.g. ser2net)."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class SerialConnection:
    path: str
    baudrate: int

    def as_dict(self) -> dict[str, Any]:
        return {"type": "serial", "path": self.path, "baudrate": self.baudrate}

    def __str__(self) -> str:
        return f"{self.path} @ {self.baudrate}"


@dataclass(frozen=True, slots=True)
class TcpConnection:
    host: str
    port: int

    def as_dict(self) -> dict[str, Any]:
        return {"type": "tcp", "host": self.host, "port": self.port}

    def __str__(self) -> str:
        return f"{self.host}:{self.port}"


Connection = SerialConnection | TcpConnection


def connection_from_dict(data: dict[str, Any]) -> Connection:
    """Inverse of as_dict(); raises ValueError for unknown types."""
    if data.get("type") == "serial":
        return SerialConnection(path=data["path"], baudrate=int(data["baudrate"]))
    if data.get("type") == "tcp":
        return TcpConnection(host=data["host"], port=int(data["port"]))
    raise ValueError(f"unknown connection type: {data.get('type')!r}")


async def open_connection(
    connection: Connection,
) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    """Open the byte stream; raises OSError (serial errors included) on failure."""
    if isinstance(connection, TcpConnection):
        return await asyncio.open_connection(connection.host, connection.port)
    from serial_asyncio_fast import open_serial_connection

    return await open_serial_connection(url=connection.path, baudrate=connection.baudrate)
