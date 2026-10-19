"""ESP3 framing."""

import pytest

from custom_components.enocean_eltako.protocol import esp3
from custom_components.enocean_eltako.protocol.telegram import RadioTelegram, Rorg


def test_crc8_known_values() -> None:
    assert esp3.crc8(bytes.fromhex("00010005")) == 0x70
    assert esp3.crc8(b"\x08") == 0x38


def test_encode_read_base_id() -> None:
    assert esp3.encode_common_command(esp3.CO_RD_IDBASE) == bytes.fromhex("5500010005700838")


def test_parse_base_id_response() -> None:
    raw = esp3.Esp3Packet(esp3.PacketType.RESPONSE, bytes.fromhex("00FF8A1B00"), b"\x0a").encode()
    (packet,) = esp3.Esp3Decoder().feed(raw)
    assert esp3.parse_base_id(packet) == 0xFF8A1B00


def test_parse_base_id_rejects_error() -> None:
    assert esp3.parse_base_id(esp3.Esp3Packet(esp3.PacketType.RESPONSE, b"\x02")) is None


def test_decode_erp1_with_optional_data() -> None:
    data = bytes.fromhex("F6 50 00 29 89 79 30".replace(" ", ""))
    optional = bytes.fromhex("01FFFFFFFF2D00")
    (packet,) = esp3.Esp3Decoder().feed(
        esp3.Esp3Packet(esp3.PacketType.RADIO_ERP1, data, optional).encode()
    )
    assert esp3.decode_radio(packet) == RadioTelegram(
        rorg=Rorg.RPS, data=b"\x50", sender=0x00298979, status=0x30, dbm=-45
    )


def test_encode_erp1_roundtrip() -> None:
    telegram = RadioTelegram(
        rorg=Rorg.VLD, data=bytes.fromhex("0100"), sender=0xFF8A1B01, destination=0x05112233
    )
    (packet,) = esp3.Esp3Decoder().feed(esp3.encode_radio(telegram))
    assert packet.optional == bytes.fromhex("0305112233FF00")
    decoded = esp3.decode_radio(packet)
    assert (decoded.rorg, decoded.data, decoded.sender, decoded.destination) == (
        Rorg.VLD,
        bytes.fromhex("0100"),
        0xFF8A1B01,
        0x05112233,
    )


@pytest.mark.parametrize("corrupt", [1, 6])  # header CRC, data CRC
def test_decoder_resyncs_after_crc_error(corrupt: int) -> None:
    good = esp3.encode_common_command(esp3.CO_RD_IDBASE)
    bad = bytearray(good)
    bad[corrupt] ^= 0xFF
    decoder = esp3.Esp3Decoder()
    packets = []
    stream = b"\x55\x00" + bytes(bad) + good
    for byte in stream:
        packets += decoder.feed(bytes([byte]))
    assert packets == [esp3.Esp3Packet(esp3.PacketType.COMMON_COMMAND, b"\x08")]
