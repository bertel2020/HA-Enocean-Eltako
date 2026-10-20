"""UTE teach-in query and response (RORG D4)."""

from custom_components.enocean_eltako.protocol.eep.ute import (
    REQUEST_EITHER,
    REQUEST_TEACH_OUT,
    decode_ute_request,
    encode_ute_request,
    encode_ute_response,
)


def test_request_round_trip() -> None:
    data = encode_ute_request("D2-01-12", 0x046, channels=2)
    assert data.hex() == "a0024600120 1d2".replace(" ", "")
    request = decode_ute_request(data)
    assert request.eep == "D2-01-12"
    assert (request.manufacturer, request.channels) == (0x046, 2)
    assert request.bidirectional and request.response_expected
    assert request.request == REQUEST_EITHER


def test_response_accepts_teach_in_and_teach_out() -> None:
    request = decode_ute_request(encode_ute_request("D2-05-00"))
    assert encode_ute_response(request).hex() == "91ffff07000 5d2".replace(" ", "")
    out = decode_ute_request(encode_ute_request("D2-05-00", request=REQUEST_TEACH_OUT))
    assert encode_ute_response(out)[0] == 0xA1
    assert encode_ute_response(request, accept=False)[0] == 0xB1


def test_not_a_query() -> None:
    assert decode_ute_request(bytes(6)) is None
    assert decode_ute_request(bytes([0x91]) + bytes(6)) is None  # a response
