"""Table-driven EEP model: fields, cases, conditions; generic decode and encode.

Bit offsets count from the most significant bit of the data bytes (official EEP notation):
offset 0 is DB3 bit 7 of a 4BS telegram, or bit 7 of the single data byte of RPS/1BS.
Status-field offsets count from bit 7 of the status byte.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class Field:
    shortcut: str
    name: str
    offset: int
    size: int
    unit: str | None = None
    raw: tuple[int, int] | None = None  # raw range
    scale: tuple[float, float] | None = None  # scaled range, linear between raw ends
    enum: tuple[int, ...] | None = None  # valid values of an enumeration
    scale_ref: str | None = None  # scale taken from the enum item of another field
    unit_ref: str | None = None  # unit taken from the enum item of another field
    enum_scale: dict[int, tuple[float, float]] = field(default_factory=dict)
    enum_unit: dict[int, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Condition:
    offset: int
    size: int
    value: int
    status: bool = False  # condition on a status-byte field instead of a data field


@dataclass(frozen=True, slots=True)
class Case:
    fields: tuple[Field, ...]
    conditions: tuple[Condition, ...] = ()


@dataclass(frozen=True, slots=True)
class Profile:
    eep: str  # "A5-04-02"
    rorg: int
    cases: tuple[Case, ...]

    @property
    def data_length(self) -> int:
        if self.rorg == 0xA5:
            return 4
        if self.rorg in (0xF6, 0xD5):
            return 1
        # VLD: as long as the furthest field of any case
        return max(((f.offset + f.size + 7) // 8 for c in self.cases for f in c.fields), default=1)


def get_bits(data: bytes, offset: int, size: int) -> int:
    value = int.from_bytes(data, "big")
    return (value >> (len(data) * 8 - offset - size)) & ((1 << size) - 1)


def set_bits(data: bytearray, offset: int, size: int, value: int) -> None:
    total = len(data) * 8
    shift = total - offset - size
    mask = ((1 << size) - 1) << shift
    current = int.from_bytes(data, "big")
    current = (current & ~mask) | ((value << shift) & mask)
    data[:] = current.to_bytes(len(data), "big")


def _matches(case: Case, data: bytes, status: int) -> bool:
    for cond in case.conditions:
        source = bytes([status]) if cond.status else data
        if cond.offset + cond.size > len(source) * 8:
            return False
        if get_bits(source, cond.offset, cond.size) != cond.value:
            return False
    return True


def find_case(profile: Profile, data: bytes, status: int = 0) -> Case | None:
    """The first case whose conditions match; a case without conditions is the fallback
    (A5-38-08 lists command 1 unconditioned before commands 2...7)."""
    fallback = None
    for case in profile.cases:
        if not case.conditions:
            fallback = fallback or case
        elif _matches(case, data, status):
            return case
    return fallback


def _scale(raw_value: int, raw: tuple[int, int], scale: tuple[float, float]) -> float:
    (r0, r1), (s0, s1) = raw, scale
    if r1 == r0:
        return s0
    return s0 + (raw_value - r0) * (s1 - s0) / (r1 - r0)


def decode(profile: Profile, data: bytes, status: int = 0) -> dict[str, Any]:
    """Field values by shortcut: scaled floats for ranges, ints for enums and raw fields."""
    case = find_case(profile, data, status)
    if case is None:
        return {}
    fields = [f for f in case.fields if f.offset + f.size <= len(data) * 8]  # VLD: variable length
    raw = {f.shortcut: get_bits(data, f.offset, f.size) for f in fields}
    values: dict[str, Any] = {}
    for f in fields:
        value: Any = raw[f.shortcut]
        if f.scale_ref is not None and f.raw is not None:
            ref_field = next((r for r in fields if r.shortcut == f.scale_ref), None)
            ref_scale = ref_field.enum_scale.get(raw[f.scale_ref]) if ref_field else None
            if ref_scale is not None:
                value = _scale(value, f.raw, ref_scale)
        elif f.raw is not None and f.scale is not None:
            value = _scale(value, f.raw, f.scale)
        values[f.shortcut] = value
    return values


def unit_of(profile: Profile, data: bytes, shortcut: str, status: int = 0) -> str | None:
    """Unit of a field, resolving a unit reference (e.g. A5-12-01 MR -> DT)."""
    case = find_case(profile, data, status)
    if case is None:
        return None
    f = next((f for f in case.fields if f.shortcut == shortcut), None)
    if f is None:
        return None
    if f.unit_ref is not None:
        ref = next((r for r in case.fields if r.shortcut == f.unit_ref), None)
        if ref is not None:
            return ref.enum_unit.get(get_bits(data, ref.offset, ref.size))
    return f.unit


def encode(profile: Profile, values: dict[str, Any], case_index: int = 0) -> bytes:
    """Build data bytes from field values (scaled values are converted back to raw)."""
    case = profile.cases[case_index]
    length = profile.data_length
    if profile.rorg == 0xD2:  # VLD: each command has its own length
        bits = [f.offset + f.size for f in case.fields] + [
            c.offset + c.size for c in case.conditions if not c.status
        ]
        length = max((b + 7) // 8 for b in bits) if bits else 1
    data = bytearray(length)
    for cond in case.conditions:
        if not cond.status:
            set_bits(data, cond.offset, cond.size, cond.value)
    for f in case.fields:
        if f.shortcut not in values:
            continue
        value = values[f.shortcut]
        if f.raw is not None and f.scale is not None and f.scale_ref is None:
            (r0, r1), (s0, s1) = f.raw, f.scale
            value = round(r0 + (float(value) - s0) * (r1 - r0) / (s1 - s0)) if s1 != s0 else r0
            value = max(min(r0, r1), min(max(r0, r1), value))
        set_bits(data, f.offset, f.size, int(value))
    return bytes(data)
