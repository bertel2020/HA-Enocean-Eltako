"""ESP3: 0x55, header (data length, optional length, packet type), CRC8H, data, optional, CRC8D."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from .ids import BROADCAST
from .telegram import RadioTelegram

SYNC = 0x55
HEADER_LEN = 4


class PacketType(IntEnum):
    RADIO_ERP1 = 0x01
    RESPONSE = 0x02
    RADIO_SUB_TEL = 0x03
    EVENT = 0x04
    COMMON_COMMAND = 0x05
    SMART_ACK_COMMAND = 0x06
    REMOTE_MAN_COMMAND = 0x07
    RADIO_MESSAGE = 0x09
    RADIO_ERP2 = 0x0A


class ReturnCode(IntEnum):
    OK = 0x00
    ERROR = 0x01
    NOT_SUPPORTED = 0x02
    WRONG_PARAM = 0x03
    OPERATION_DENIED = 0x04


CO_RD_VERSION = 0x03
CO_RD_IDBASE = 0x08
CO_WR_REPEATER = 0x09  # REP_ENABLE (0/1), REP_LEVEL (0, 1 or 2)


def _table() -> list[int]:
    table = []
    for byte in range(256):
        crc = byte
        for _ in range(8):
            crc = ((crc << 1) ^ 0x07) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
        table.append(crc)
    return table


_CRC8 = _table()


def crc8(data: bytes) -> int:
    """CRC-8 with polynomial x^8 + x^2 + x + 1 (0x07), init 0."""
    crc = 0
    for byte in data:
        crc = _CRC8[crc ^ byte]
    return crc


@dataclass(frozen=True, slots=True)
class Esp3Packet:
    packet_type: int
    data: bytes
    optional: bytes = b""

    def encode(self) -> bytes:
        header = len(self.data).to_bytes(2, "big") + bytes([len(self.optional), self.packet_type])
        payload = self.data + self.optional
        return bytes([SYNC]) + header + bytes([crc8(header)]) + payload + bytes([crc8(payload)])


class Esp3Decoder:
    """Incremental decoder: feed raw bytes, get complete packets; resyncs on CRC errors."""

    def __init__(self) -> None:
        self._buf = bytearray()
        self.dropped = 0

    def feed(self, chunk: bytes) -> list[Esp3Packet]:
        self._buf += chunk
        packets: list[Esp3Packet] = []
        while True:
            start = self._buf.find(SYNC)
            if start < 0:
                self.dropped += len(self._buf)
                self._buf.clear()
                return packets
            if start:
                self.dropped += start
                del self._buf[:start]
            if len(self._buf) < 1 + HEADER_LEN + 1:
                return packets
            header = bytes(self._buf[1:5])
            if crc8(header) != self._buf[5]:
                self.dropped += 1
                del self._buf[:1]
                continue
            data_len = int.from_bytes(header[:2], "big")
            opt_len = header[2]
            total = 6 + data_len + opt_len + 1
            if len(self._buf) < total:
                return packets
            payload = bytes(self._buf[6 : total - 1])
            if crc8(payload) != self._buf[total - 1]:
                self.dropped += 1
                del self._buf[:1]
                continue
            del self._buf[:total]
            packets.append(Esp3Packet(header[3], payload[:data_len], payload[data_len:]))


def decode_radio(packet: Esp3Packet) -> RadioTelegram | None:
    """Radio telegram from a RADIO_ERP1 packet, else None."""
    if packet.packet_type != PacketType.RADIO_ERP1 or len(packet.data) < 6:
        return None
    data, opt = packet.data, packet.optional
    destination, dbm = BROADCAST, None
    if len(opt) >= 6:
        destination = int.from_bytes(opt[1:5], "big")
        dbm = -opt[5]
    return RadioTelegram(
        rorg=data[0],
        data=bytes(data[1:-5]),
        sender=int.from_bytes(data[-5:-1], "big"),
        status=data[-1],
        destination=destination,
        dbm=dbm,
    )


def encode_radio(telegram: RadioTelegram) -> bytes:
    """RADIO_ERP1 packet; optional data: send subtelegrams 3, destination, dBm FF, no security."""
    data = (
        bytes([telegram.rorg])
        + telegram.data
        + telegram.sender.to_bytes(4, "big")
        + bytes([telegram.status])
    )
    optional = b"\x03" + telegram.destination.to_bytes(4, "big") + b"\xff\x00"
    return Esp3Packet(PacketType.RADIO_ERP1, data, optional).encode()


def encode_common_command(code: int, params: bytes = b"") -> bytes:
    return Esp3Packet(PacketType.COMMON_COMMAND, bytes([code]) + params).encode()


def encode_repeater(level: int) -> bytes:
    """CO_WR_REPEATER: level 0 switches repeating off, 1 or 2 repeats once or twice."""
    if level not in (0, 1, 2):
        raise ValueError(f"repeater level must be 0, 1 or 2, not {level}")
    return encode_common_command(CO_WR_REPEATER, bytes([1 if level else 0, level]))


def is_ok(packet: Esp3Packet) -> bool:
    return packet.packet_type == PacketType.RESPONSE and packet.data[:1] == bytes([ReturnCode.OK])


def parse_base_id(packet: Esp3Packet) -> int | None:
    """Base ID from the RESPONSE to CO_RD_IDBASE (RET_OK + 4 bytes), else None."""
    if (
        packet.packet_type == PacketType.RESPONSE
        and len(packet.data) >= 5
        and packet.data[0] == ReturnCode.OK
    ):
        return int.from_bytes(packet.data[1:5], "big")
    return None
