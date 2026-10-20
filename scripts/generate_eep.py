"""Generate protocol/eep/std/profiles.py from the official EEP definitions in .eep_cache/.

Only technical facts are written (field positions, sizes, ranges, scales, units, enum
values, conditions); no description text from the EnOcean Alliance files (see NOTICE).

All profiles of the EEP Viewer index are generated (phase 5); profiles that only point to a
shared definition become aliases.

Usage:
    python scripts/fetch_eep.py                 # download all definitions
    python scripts/generate_eep.py              # write the module
    python scripts/generate_eep.py --check      # CI: fail if the module is out of date
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".eep_cache"
TARGET = ROOT / "custom_components/enocean_eltako/protocol/eep/std/profiles.py"

INDEX = CACHE / "eep-viewer-desc.json"


def _as_list(value):
    return value if isinstance(value, list) else [value]


def all_profiles() -> list[str]:
    """Every profile in the EEP Viewer index (fetch_eep.py stores it in .eep_cache)."""
    import json

    index = json.loads(INDEX.read_text(encoding="utf-8-sig"))
    return sorted(
        f"{rorg}-{func['value'][2:].upper()}-{typ['value'][2:].upper()}"
        for rorg, entry in index.items()
        for func in _as_list(entry["function"])
        for typ in _as_list(func["type"])
    )


def reference_of(eep: str) -> str | None:
    """Profiles that only point to a shared definition (<ref>), e.g. D2-01-09 -> D2-01-00."""
    path = CACHE / f"{eep}.xml"
    if not path.exists():
        return None
    ref = ET.parse(path).getroot().find(".//type/ref")
    if ref is None or ref.find("rorg") is None:
        return None
    return "-".join(ref.findtext(tag).strip() for tag in ("rorg", "func", "type")).upper()


def _has_cases(eep: str) -> bool:
    path = CACHE / f"{eep}.xml"
    return path.exists() and ET.parse(path).getroot().find(".//case") is not None


def _int(text: str | None) -> int:
    text = text.strip()
    try:
        return int(text, 0)
    except ValueError:
        return int(text, 10)  # "07"


def _maybe_int(text: str | None) -> int | None:
    """Enum values can be bit patterns with don't-care bits ("0b11X0XXXX"); skipped."""
    if text is None:
        return None
    try:
        return _int(text)
    except ValueError:
        return None


def _num(text: str | None) -> float:
    return float(text.strip().replace("+", ""))


def _clean(text: str | None) -> str | None:
    if text is None:
        return None
    text = " ".join(text.split())
    return text or None


def _range(el: ET.Element | None) -> tuple | None:
    if el is None or el.find("min") is None or el.find("max") is None:
        return None
    return el.findtext("min"), el.findtext("max")


def _field(df: ET.Element) -> str | None:
    """A data field; a field whose ranges are prose ("20 .. 80", "2000 (or 5000)") keeps its
    position and size only, a field without position is left out."""
    try:
        return _full_field(df)
    except (AttributeError, ValueError, TypeError):
        pass
    if df.findtext("bitoffs") is None or df.findtext("bitsize") is None:
        return None
    try:
        offs, size = _int(df.findtext("bitoffs")), _int(df.findtext("bitsize"))
    except ValueError:
        return None
    shortcut, name = _shortcut(df), _clean(df.findtext("data")) or ""
    if df.find("reserved") is not None or shortcut is None:
        return None
    return f"Field({shortcut!r}, {name!r}, {offs}, {size})"


def _shortcut(df: ET.Element) -> str | None:
    """The field's shortcut; some profiles (D2-14-41) only name the field."""
    return _clean(df.findtext("shortcut")) or _clean(df.findtext("data"))


def _full_field(df: ET.Element) -> str | None:
    if df.find("reserved") is not None or _shortcut(df) is None:
        return None
    args = [
        repr(_shortcut(df)),
        repr(_clean(df.findtext("data")) or ""),
        str(_int(df.findtext("bitoffs"))),
        str(_int(df.findtext("bitsize"))),
    ]
    kwargs: list[str] = []
    unit = df.find("unit")
    if unit is not None and unit.find("ref") is not None:
        kwargs.append(f"unit_ref={_clean(unit.findtext('ref'))!r}")
    elif unit is not None and _clean(unit.text):
        kwargs.append(f"unit={_clean(unit.text)!r}")
    raw = _range(df.find("range"))
    if raw is not None:
        kwargs.append(f"raw=({_int(raw[0])}, {_int(raw[1])})")
    scale = df.find("scale")
    if scale is not None and scale.find("ref") is not None:
        kwargs.append(f"scale_ref={_clean(scale.findtext('ref'))!r}")
    elif (sc := _range(scale)) is not None:
        kwargs.append(f"scale=({_num(sc[0])!r}, {_num(sc[1])!r})")
    enum = df.find("enum")
    if enum is not None:
        values, scales, units = [], {}, {}
        for item in enum.findall("item"):
            if (value := _maybe_int(item.findtext("value"))) is None:
                continue
            values.append(value)
            if (sc := _range(item.find("scale"))) is not None:
                scales[value] = (_num(sc[0]), _num(sc[1]))
            if _clean(item.findtext("unit")):
                units[value] = _clean(item.findtext("unit"))
        if values:
            kwargs.append(f"enum={tuple(values)!r}")
        if scales:
            kwargs.append(f"enum_scale={scales!r}")
        if units:
            kwargs.append(f"enum_unit={units!r}")
    return f"Field({', '.join(args + kwargs)})"


def _conditions(case: ET.Element) -> list[str]:
    cond = case.find("condition")
    if cond is None:
        return _command_condition(case)
    out = []
    for c in cond:
        if c.findtext("bitoffs") is None:
            continue  # <direction>: device to controller (1) or back (2), cases stay in order
        status = c.tag == "statusfield"
        out.append(
            f"Condition({_int(c.findtext('bitoffs'))}, {_int(c.findtext('bitsize'))}, "
            f"{_int(c.findtext('value'))}{', status=True' if status else ''})"
        )
    return out


def _command_condition(case: ET.Element) -> list[str]:
    """Cases told apart only by a command field with one enum value (D2-01 CMD, A5-38-08 COM)."""
    for df in case.findall("datafield"):
        if _clean(df.findtext("shortcut")) not in ("CMD", "COM"):
            continue
        values = [
            v for item in df.iter("item") if (v := _maybe_int(item.findtext("value"))) is not None
        ]
        if len(values) == 1:
            return [
                f"Condition({_int(df.findtext('bitoffs'))}, {_int(df.findtext('bitsize'))}, "
                f"{values[0]})"
            ]
    return []


def generate_profile(eep: str) -> str:
    root = ET.parse(CACHE / f"{eep}.xml").getroot()
    rorg = _int(root.findtext(".//rorg/number"))
    cases = []
    for case in root.iter("case"):
        fields = [f for df in case.findall("datafield") if (f := _field(df))]
        conds = _conditions(case)
        cases.append(
            "        Case(\n            fields=(\n"
            + "".join(f"                {f},\n" for f in fields)
            + "            ),\n"
            + (
                "            conditions=("
                + ", ".join(conds)
                + ("," if len(conds) == 1 else "")
                + "),\n"
                if conds
                else ""
            )
            + "        ),\n"
        )
    return (
        f'    "{eep}": Profile(\n        "{eep}",\n        0x{rorg:02X},\n        (\n'
        + "".join("    " + c.replace("\n", "\n    ").rstrip(" ") for c in cases)
        + "        ),\n    ),\n"
    )


def render() -> str:
    profiles, references = [], {}
    for eep in all_profiles():
        if (target := reference_of(eep)) is not None and target != eep:
            references[eep] = target
        elif _has_cases(eep):
            profiles.append(eep)
    parts = []
    for eep in list(profiles):
        try:
            parts.append(generate_profile(eep))
        except (AttributeError, ValueError, TypeError) as err:  # incomplete definition
            print(f"skipped {eep}: {err!r}", file=sys.stderr)
            profiles.remove(eep)
    references = {a: t for a, t in references.items() if t in profiles}
    body = "".join(parts)
    return (
        '"""Standard EEP profiles: technical facts from the EnOcean Alliance EEP Viewer.\n\n'
        f"Generated by scripts/generate_eep.py on {date.today().isoformat()}. Do not edit.\n"
        '"""\n\n'
        "# ruff: noqa: E501\n\n"
        "from ..model import Case, Condition, Field, Profile\n\n"
        "PROFILES: dict[str, Profile] = {\n"
        + body
        + "}\n"
        + "".join(
            f'PROFILES["{alias}"] = PROFILES["{target}"]\n' for alias, target in references.items()
        )
    )


def _without_date(text: str) -> list[str]:
    return [line for line in text.splitlines() if not line.startswith("Generated by ")]


def _format(path: Path) -> None:
    import subprocess

    subprocess.run(["ruff", "format", "-q", str(path)], check=False)


def main(argv: list[str]) -> int:
    if not INDEX.exists():
        print("missing .eep_cache (run fetch_eep.py)", file=sys.stderr)
        return 1
    if "--check" in argv:
        fresh = CACHE / "profiles_check.py"
        fresh.write_text(render(), encoding="utf-8")
        _format(fresh)
        if _without_date(fresh.read_text(encoding="utf-8")) != _without_date(
            TARGET.read_text(encoding="utf-8")
        ):
            print(f"{TARGET.relative_to(ROOT)} is out of date: run generate_eep.py")
            return 1
        print("generated EEP profiles are up to date")
        return 0
    TARGET.write_text(render(), encoding="utf-8")
    _format(TARGET)
    print(f"wrote {TARGET.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
