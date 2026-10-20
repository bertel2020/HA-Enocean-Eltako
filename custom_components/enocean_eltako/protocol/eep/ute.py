"""Universal Teach-in (UTE, RORG D4), as VLD actuators (D2-01, D2-05) use it.

Request from the device, DB6...DB0 (7 bytes):
    DB6 bit 7 bidirectional, bit 6 = 0: response expected, bits 5-4 request
        (0 teach-in, 1 teach-out, 2 either), bits 3-0 command 0 (query)
    DB5 channels (0xFF all), DB4 manufacturer bits 7-0, DB3 bits 2-0 manufacturer bits 10-8,
    DB2 TYPE, DB1 FUNC, DB0 RORG
Response from the controller, addressed to the device: DB6 bit 7 = 1, bits 5-4 result
    (1 teach-in accepted, 2 teach-out accepted, 3 EEP not supported), bits 3-0 command 1;
    DB5...DB0 as in the request.
"""

from __future__ import annotations

from dataclasses import dataclass

COMMAND_QUERY = 0x0
COMMAND_RESPONSE = 0x1
REQUEST_TEACH_IN = 0
REQUEST_TEACH_OUT = 1
REQUEST_EITHER = 2
RESULT_TEACH_IN = 1
RESULT_TEACH_OUT = 2
RESULT_NOT_SUPPORTED = 3


@dataclass(frozen=True, slots=True)
class UteRequest:
    bidirectional: bool
    response_expected: bool
    request: int  # REQUEST_*
    channels: int
    manufacturer: int
    rorg: int
    func: int
    type: int
    raw: bytes

    @property
    def eep(self) -> str:
        return f"{self.rorg:02X}-{self.func:02X}-{self.type:02X}"


def decode_ute_request(data: bytes) -> UteRequest | None:
    """A teach-in query (command 0) of 7 bytes; anything else is None."""
    if len(data) != 7 or data[0] & 0x0F != COMMAND_QUERY:
        return None
    return UteRequest(
        bidirectional=bool(data[0] & 0x80),
        response_expected=not data[0] & 0x40,
        request=(data[0] >> 4) & 0x03,
        channels=data[1],
        manufacturer=((data[3] & 0x07) << 8) | data[2],
        type=data[4],
        func=data[5],
        rorg=data[6],
        raw=bytes(data),
    )


def encode_ute_response(request: UteRequest, *, accept: bool = True) -> bytes:
    """Answer a query: teach-in or teach-out (request 2: teach-in) accepted, or refused."""
    if not accept:
        result = RESULT_NOT_SUPPORTED
    elif request.request == REQUEST_TEACH_OUT:
        result = RESULT_TEACH_OUT
    else:
        result = RESULT_TEACH_IN
    return bytes([0x80 | result << 4 | COMMAND_RESPONSE]) + request.raw[1:]


def encode_ute_request(
    eep: str, manufacturer: int = 0x7FF, *, channels: int = 0xFF, request: int = REQUEST_EITHER
) -> bytes:
    """A teach-in query as a device sends it (tests, fake devices)."""
    rorg, func, type_ = (int(part, 16) for part in eep.split("-"))
    return bytes(
        [
            0x80 | request << 4 | COMMAND_QUERY,
            channels,
            manufacturer & 0xFF,
            (manufacturer >> 8) & 0x07,
            type_,
            func,
            rorg,
        ]
    )
