"""Byte transports: serial ports (serialx) and TCP (asyncio streams, e.g. ser2net).

serialx is the serial library of Home Assistant's usb integration. Besides local devices it
opens the URLs HA's serial port picker offers, e.g. ESPHome serial proxies.
"""

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
    """Open the byte stream; raises OSError (serial errors as ConnectionError) on failure."""
    if isinstance(connection, TcpConnection):
        return await asyncio.open_connection(connection.host, connection.port)
    from serialx import SerialException, open_serial_connection

    try:
        return await open_serial_connection(url=connection.path, baudrate=connection.baudrate)
    except SerialException as err:
        raise ConnectionError(f"{connection}: {err}") from err
