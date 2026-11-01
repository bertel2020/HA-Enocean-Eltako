"""Property tests of the EEP codecs: any data decodes or is refused, never raises."""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from custom_components.enocean_eltako.protocol.eep import EEPRef, model
from custom_components.enocean_eltako.protocol.eep.codecs import DECODERS, decode_telegram
from custom_components.enocean_eltako.protocol.eep.std.profiles import PROFILES
from custom_components.enocean_eltako.protocol.eep.teach_in import (
    decode_teach_in_4bs,
    encode_teach_in_4bs,
)
from custom_components.enocean_eltako.protocol.eep.ute import (
    decode_ute_request,
    encode_ute_request,
)
from custom_components.enocean_eltako.protocol.telegram import RadioTelegram

STATUS = st.integers(0, 255)
ID = st.integers(0, 0xFFFFFFFF)
PROFILE_IDS = sorted(PROFILES)
DECODED = sorted(DECODERS, key=str)


@settings(max_examples=40)
@given(
    eep=st.sampled_from(PROFILE_IDS),
    data=st.binary(min_size=1, max_size=14),
    status=STATUS,
)
def test_any_data_decodes_to_values_or_nothing(eep: str, data: bytes, status: int) -> None:
    profile = PROFILES[eep]
    values = model.decode(profile, data, status)
    assert isinstance(values, dict)
    case = model.find_case(profile, data, status)
    for field in case.fields if case else ():
        model.unit_of(profile, data, field.shortcut, status)


@settings(max_examples=40)
@given(
    ref=st.sampled_from(DECODED),
    data=st.binary(min_size=1, max_size=14),
    sender=ID,
    status=STATUS,
)
def test_every_registered_decoder_accepts_any_telegram(
    ref: EEPRef, data: bytes, sender: int, status: int
) -> None:
    rorg = int(ref.eep[:2], 16)
    result = decode_telegram(ref, RadioTelegram(rorg, data, sender, status))
    assert result is None or isinstance(result, dict)


@pytest.mark.parametrize("eep", PROFILE_IDS)
@given(data=st.data())
@settings(max_examples=15, deadline=None)
def test_unscaled_fields_survive_an_encode_decode_round_trip(eep: str, data) -> None:
    profile = PROFILES[eep]
    index = data.draw(st.integers(0, len(profile.cases) - 1))
    case = profile.cases[index]
    # fields that are plain bits (no scaling); a field shared with a condition or another field
    # of the case is skipped, as one value could not hold both
    taken = [(c.offset, c.size) for c in case.conditions if not c.status]
    plain = [
        f
        for f in case.fields
        if f.raw is None and f.scale is None and f.scale_ref is None and f.size <= 16
    ]
    chosen = []
    for f in plain:
        span = (f.offset, f.size)
        if all(span[0] + span[1] <= o or o + s <= span[0] for o, s in taken):
            taken.append(span)
            chosen.append(f)
    values = {f.shortcut: data.draw(st.integers(0, 2**f.size - 1)) for f in chosen}
    encoded = model.encode(profile, values, index)
    if model.find_case(profile, encoded) is not case:
        return  # another case matches these bits first: decode answers for that one
    decoded = model.decode(profile, encoded)
    for shortcut, value in values.items():
        assert decoded.get(shortcut, value) == value


@given(
    eep=st.sampled_from(["A5-38-08", "A5-3F-7F", "A5-08-01", "A5-02-05", "A5-12-01"]),
    manufacturer=st.integers(0, 0x7FF),
)
def test_teach_in_telegrams_round_trip(eep: str, manufacturer: int) -> None:
    teach = decode_teach_in_4bs(encode_teach_in_4bs(eep, manufacturer))
    assert teach is not None and teach.eep == eep and teach.manufacturer == manufacturer


@given(data=st.binary(max_size=10))
def test_teach_in_and_ute_decoders_accept_any_bytes(data: bytes) -> None:
    decode_teach_in_4bs(data)
    request = decode_ute_request(data)
    assert request is None or request.raw == data


@given(
    rorg=st.sampled_from([0xD2, 0xD5, 0xA5, 0xF6]),
    func=st.integers(0, 255),
    type_=st.integers(0, 255),
    manufacturer=st.integers(0, 0x7FF),
    channels=st.integers(0, 255),
)
def test_ute_queries_round_trip(
    rorg: int, func: int, type_: int, manufacturer: int, channels: int
) -> None:
    eep = f"{rorg:02X}-{func:02X}-{type_:02X}"
    request = decode_ute_request(encode_ute_request(eep, manufacturer, channels=channels))
    assert request is not None
    assert (request.eep, request.manufacturer, request.channels) == (eep, manufacturer, channels)
