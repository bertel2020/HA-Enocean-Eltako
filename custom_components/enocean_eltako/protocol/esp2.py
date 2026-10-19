"""ESP2: fixed 14-byte frames (A5 5A, header, ORG, 4 data bytes, ID, status, checksum)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from .telegram import RadioTelegram, Rorg

SYNC = b"\xa5\x5a"
FRAME_LEN = 14
LENGTH = 0x0B


class HSeq(IntEnum):
    """Header sequence (upper three bits of the header byte)."""

    RRT = 0b000  # receive radio telegram
    TRT = 0b011  # transmit radio telegram
    RMT = 0b100  # receive message telegram (gateway answer)
    TCT = 0b101  # transmit command telegram (gateway command)


# ESP2 ORG <-> RORG; ESP2 knows no VLD/MSC/UTE.
ORG_TO_RORG = {0x05: Rorg.RPS, 0x06: Rorg.BS1, 0x07: Rorg.BS4}
RORG_TO_ORG = {rorg: org for org, rorg in ORG_TO_RORG.items()}

# TCM120 commands (TCT) and messages (RMT), as used by FAM-USB.
CMD_RD_IDBASE = 0x58
MSG_INF_IDBASE = 0x98
MSG_OK = 0x58
MSG_ERR = 0x19


def checksum(body: bytes) -> int:
    """Sum of header ... status, modulo 256."""
    return sum(body) & 0xFF


@dataclass(frozen=True, slots=True)
class Esp2Frame:
    """One ESP2 frame without sync and checksum."""

    hseq: int
    org: int
    data: bytes  # DATA_BYTE3 ... DATA_BYTE0
    sender: int = 0
    status: int = 0

    def encode(self) -> bytes:
        body = bytes(
            [(self.hseq << 5) | LENGTH, self.org, *self.data, *self.sender.to_bytes(4, "big")]
        ) + bytes([self.status])
        return SYNC + body + bytes([checksum(body)])

    @classmethod
    def from_body(cls, body: bytes) -> Esp2Frame:
        return cls(
            hseq=body[0] >> 5,
            org=body[1],
            data=bytes(body[2:6]),
            sender=int.from_bytes(body[6:10], "big"),
            status=body[10],
        )


class Esp2Decoder:
    """Incremental decoder: feed raw bytes, get complete frames; resyncs on garbage."""

    def __init__(self) -> None:
        self._buf = bytearray()
        self.dropped = 0

    def feed(self, chunk: bytes) -> list[Esp2Frame]:
        self._buf += chunk
        frames: list[Esp2Frame] = []
        while True:
            start = self._buf.find(SYNC)
            if start < 0:
                # keep a trailing A5, it may be the first sync byte
                keep = 1 if self._buf.endswith(SYNC[:1]) else 0
                self.dropped += len(self._buf) - keep
                del self._buf[: len(self._buf) - keep]
                return frames
            if start:
                self.dropped += start
                del self._buf[:start]
            if len(self._buf) < FRAME_LEN:
                return frames
            body = bytes(self._buf[2:13])
            if body[0] & 0x1F != LENGTH or checksum(body) != self._buf[13]:
                self.dropped += 1
                del self._buf[:1]
                continue
            del self._buf[:FRAME_LEN]
            frames.append(Esp2Frame.from_body(body))


def decode_radio(frame: Esp2Frame) -> RadioTelegram | None:
    """Radio telegram from an RRT/TRT frame, or from an RMT frame with ORG 05/06/07.

    On the Eltako RS485 bus, actors answer the FAM14 poll with RMT frames laid out like
    radio telegrams (data, sender ID, status). None for gateway and bus control messages.
    """
    if frame.hseq not in (HSeq.RRT, HSeq.TRT, HSeq.RMT) or frame.org not in ORG_TO_RORG:
        return None
    rorg = ORG_TO_RORG[frame.org]
    data = frame.data if rorg == Rorg.BS4 else frame.data[:1]
    return RadioTelegram(rorg=rorg, data=data, sender=frame.sender, status=frame.status)


# Eltako bus control (TCT requests, RMT answers), distinguished by ORG.
BUS_DISCOVERY = 0xF0
BUS_MEMORY = 0xF1
BUS_EMPTY = 0xF8  # "nothing to send" answer to a poll
BUS_POLL = 0xFC
BUS_POLL_FORCED = 0xFE
BUS_LOCK = 0xFF  # address FF locks, 00 unlocks


def is_bus_control(frame: Esp2Frame) -> bool:
    """Polls, empty answers and other bus management frames of the FAM14 bus."""
    return frame.hseq in (HSeq.TCT, HSeq.RMT) and frame.org >= BUS_DISCOVERY


def encode_radio(telegram: RadioTelegram) -> bytes:
    """TRT frame for a radio telegram; ESP2 carries RPS, 1BS and 4BS only."""
    if telegram.rorg not in RORG_TO_ORG:
        raise ValueError(f"ESP2 cannot send RORG {telegram.rorg:02X}")
    expected = 4 if telegram.rorg == Rorg.BS4 else 1
    if len(telegram.data) != expected:
        raise ValueError(f"RORG {telegram.rorg:02X} needs {expected} data bytes")
    return Esp2Frame(
        hseq=HSeq.TRT,
        org=RORG_TO_ORG[telegram.rorg],
        data=telegram.data.ljust(4, b"\x00"),
        sender=telegram.sender,
        status=telegram.status,
    ).encode()


def encode_command(command: int) -> bytes:
    """TCT frame for a gateway command without parameters."""
    return Esp2Frame(hseq=HSeq.TCT, org=command, data=bytes(4)).encode()


def parse_base_id(frame: Esp2Frame) -> int | None:
    """Base ID from an INF_IDBASE answer, else None."""
    if frame.hseq == HSeq.RMT and frame.org == MSG_INF_IDBASE:
        return int.from_bytes(frame.data, "big")
    return None
