"""ID helpers."""

import pytest

from custom_components.enocean_eltako.protocol.ids import format_id, is_valid_base_id, parse_id


@pytest.mark.parametrize(
    "text",
    ["FF-B7-44-80", "ff:b7:44:80", "FFB74480", " FF-B7-44-80 ", "FF B7 44 80", "0xFFB74480"],
)
def test_parse_id(text: str) -> None:
    assert parse_id(text) == 0xFFB74480


@pytest.mark.parametrize(
    "text",
    ["", "FF-B7-44", "GG-00-00-00", "FF-B7-44-80-00", "FF-B7:44 80", "0xFF-B7-44-80", "FFB7-4480"],
)
def test_parse_id_rejects(text: str) -> None:
    with pytest.raises(ValueError):
        parse_id(text)


def test_format_id() -> None:
    assert format_id(0x00216343) == "00-21-63-43"


@pytest.mark.parametrize(
    ("value", "valid"),
    [
        (0xFFB74480, True),
        (0xFF800000, True),
        (0xFFFFFF80, True),
        (0xFFB74481, False),
        (0x00216300, False),
        (0xFFFFFFFF, False),
    ],
)
def test_is_valid_base_id(value: int, valid: bool) -> None:
    assert is_valid_base_id(value) is valid
