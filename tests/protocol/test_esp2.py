"""ESP2 framing."""

from custom_components.enocean_eltako.protocol import esp2
from custom_components.enocean_eltako.protocol.telegram import RadioTelegram, Rorg

# FAM-USB answer to RD_IDBASE with base ID FF-B7-44-80
INF_IDBASE = bytes.fromhex("A55A8B98FFB744800000000000")
INF_IDBASE += bytes([esp2.checksum(INF_IDBASE[2:])])
# Rocker switch (RPS 0x70) from 00-21-63-43, status 0x30
RPS_RX = bytes.fromhex("A55A0B0570000000002163433000")
RPS_RX = RPS_RX[:13] + bytes([esp2.checksum(RPS_RX[2:13])])


def test_checksum_matches_known_frame() -> None:
    assert esp2.encode_command(esp2.CMD_RD_IDBASE) == bytes.fromhex("A55AAB5800000000000000000003")


def test_decode_base_id_answer() -> None:
    (frame,) = esp2.Esp2Decoder().feed(INF_IDBASE)
    assert frame.hseq == esp2.HSeq.RMT
    assert esp2.parse_base_id(frame) == 0xFFB74480
    assert esp2.decode_radio(frame) is None


def test_decode_rps() -> None:
    (frame,) = esp2.Esp2Decoder().feed(RPS_RX)
    assert esp2.decode_radio(frame) == RadioTelegram(
        rorg=Rorg.RPS, data=b"\x70", sender=0x00216343, status=0x30
    )


def test_decode_4bs_keeps_all_data_bytes() -> None:
    raw = esp2.Esp2Frame(esp2.HSeq.RRT, 0x07, bytes.fromhex("0000FF0F"), 0x0195A1B2, 0).encode()
    (frame,) = esp2.Esp2Decoder().feed(raw)
    assert esp2.decode_radio(frame).data == bytes.fromhex("0000FF0F")


def test_decoder_resyncs_and_splits_chunks() -> None:
    decoder = esp2.Esp2Decoder()
    stream = b"\x00\xa5\x13" + RPS_RX + b"\xa5\x5a\x0b\x05" + INF_IDBASE
    frames = []
    for i in range(0, len(stream), 3):
        frames += decoder.feed(stream[i : i + 3])
    assert [f.hseq for f in frames] == [esp2.HSeq.RRT, esp2.HSeq.RMT]
    assert decoder.dropped > 0


def test_decoder_drops_bad_checksum() -> None:
    bad = RPS_RX[:13] + bytes([(RPS_RX[13] + 1) & 0xFF])
    assert esp2.Esp2Decoder().feed(bad + RPS_RX) != []
    assert len(esp2.Esp2Decoder().feed(bad)) == 0


def test_encode_radio_roundtrip() -> None:
    telegram = RadioTelegram(rorg=Rorg.BS4, data=bytes.fromhex("01020308"), sender=0xFFB74481)
    raw = esp2.encode_radio(telegram)
    assert raw[2] == 0x6B  # TRT, length 11
    (frame,) = esp2.Esp2Decoder().feed(raw)
    assert esp2.decode_radio(frame) == telegram


def test_encode_radio_rejects_vld() -> None:
    import pytest

    with pytest.raises(ValueError):
        esp2.encode_radio(RadioTelegram(rorg=Rorg.VLD, data=b"\x01", sender=1))
