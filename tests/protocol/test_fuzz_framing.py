"""Property tests of the ESP2 and ESP3 framing: noise never stops the reader, frames survive."""

from hypothesis import given, settings
from hypothesis import strategies as st

from custom_components.enocean_eltako.protocol import esp2, esp3
from custom_components.enocean_eltako.protocol.telegram import RadioTelegram, Rorg

NOISE = st.binary(max_size=300)
CHUNKS = st.lists(st.binary(max_size=40), max_size=12)


def _split(data: bytes, cuts: list[int]) -> list[bytes]:
    points = sorted({c % (len(data) + 1) for c in cuts} | {0, len(data)})
    return [data[a:b] for a, b in zip(points, points[1:], strict=False)]


esp2_frames = st.builds(
    esp2.Esp2Frame,
    hseq=st.integers(0, 7),
    org=st.integers(0, 255),
    data=st.binary(min_size=4, max_size=4),
    sender=st.integers(0, 0xFFFFFFFF),
    status=st.integers(0, 255),
)
esp3_packets = st.builds(
    esp3.Esp3Packet,
    packet_type=st.integers(0, 255),
    data=st.binary(max_size=60),
    optional=st.binary(max_size=20),
)


@st.composite
def radio_telegrams(draw: st.DrawFn) -> RadioTelegram:
    """RPS and 1BS carry one data byte, 4BS four."""
    rorg = draw(st.sampled_from([Rorg.RPS, Rorg.BS1, Rorg.BS4]))
    return RadioTelegram(
        rorg=rorg,
        data=draw(
            st.binary(min_size=4 if rorg == Rorg.BS4 else 1, max_size=4 if rorg == Rorg.BS4 else 1)
        ),
        sender=draw(st.integers(0, 0xFFFFFFFF)),
        status=draw(st.integers(0, 255)),
    )


@given(chunks=CHUNKS)
def test_esp2_decoder_survives_noise(chunks: list[bytes]) -> None:
    decoder = esp2.Esp2Decoder()
    for chunk in chunks:
        for frame in decoder.feed(chunk):
            esp2.decode_radio(frame)  # may be None, must not raise
            esp2.is_bus_control(frame)
            esp2.parse_base_id(frame)


@given(chunks=CHUNKS)
def test_esp3_decoder_survives_noise(chunks: list[bytes]) -> None:
    decoder = esp3.Esp3Decoder()
    for chunk in chunks:
        for packet in decoder.feed(chunk):
            esp3.decode_radio(packet)
            esp3.is_ok(packet)
            esp3.parse_base_id(packet)


@given(
    frames=st.lists(esp2_frames, max_size=6), noise=NOISE, cuts=st.lists(st.integers(), max_size=8)
)
def test_esp2_frames_come_out_of_noise_and_in_any_chunking(
    frames: list[esp2.Esp2Frame], noise: bytes, cuts: list[int]
) -> None:
    stream = b"".join(f.encode() for f in frames)
    decoder = esp2.Esp2Decoder()
    out = [f for chunk in _split(stream, cuts) for f in decoder.feed(chunk)]
    assert out == frames
    # noise in front costs at most itself: a frame after it is still found
    # (noise containing the sync byte may swallow a frame start, so only the tail is asserted)
    tail = esp2.Esp2Frame(hseq=1, org=5, data=bytes(4)).encode()
    found = esp2.Esp2Decoder().feed(noise + tail + tail)
    assert found and found[-1] == esp2.Esp2Frame.from_body(tail[2:13])


@given(packets=st.lists(esp3_packets, max_size=6), cuts=st.lists(st.integers(), max_size=8))
def test_esp3_packets_survive_any_chunking(packets: list[esp3.Esp3Packet], cuts: list[int]) -> None:
    stream = b"".join(p.encode() for p in packets)
    decoder = esp3.Esp3Decoder()
    out = [p for chunk in _split(stream, cuts) for p in decoder.feed(chunk)]
    assert out == packets


@given(telegram=radio_telegrams())
@settings(max_examples=200)
def test_radio_telegrams_round_trip_through_both_protocols(telegram: RadioTelegram) -> None:
    decoded2 = esp2.decode_radio(esp2.Esp2Decoder().feed(esp2.encode_radio(telegram))[0])
    assert decoded2 is not None
    assert (decoded2.rorg, decoded2.sender, decoded2.status) == (
        telegram.rorg,
        telegram.sender,
        telegram.status,
    )
    assert decoded2.data == telegram.data
    decoded3 = esp3.decode_radio(esp3.Esp3Decoder().feed(esp3.encode_radio(telegram))[0])
    assert decoded3 is not None
    assert (decoded3.rorg, decoded3.data, decoded3.sender, decoded3.status) == (
        telegram.rorg,
        telegram.data,
        telegram.sender,
        telegram.status,
    )
