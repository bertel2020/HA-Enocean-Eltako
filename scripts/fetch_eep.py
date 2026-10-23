"""Download official EEP definitions from the EnOcean Alliance EEP Viewer.

The files are the property of the EnOcean Alliance (free for non-commercial use)
and are never committed: they land in .eep_cache/ (git-ignored) and are only used
by the generator and tests during development and CI.

Usage:
    python scripts/fetch_eep.py                 # all profiles
    python scripts/fetch_eep.py A5-38-08 D2-01  # profiles or prefixes
    python scripts/fetch_eep.py --generated     # what generate_eep.py needs (all)
"""

from __future__ import annotations

import json
import ssl
import sys
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BASE = "https://tools.enocean-alliance.org/EEPViewer"
INDEX_URL = f"{BASE}/eep-viewer-desc.json"
CACHE = Path(__file__).resolve().parent.parent / ".eep_cache"
SUFFIXES = (".xml", "_test.xml")
ABSENT = CACHE / "absent.json"  # files the viewer answered 404 for, so a cached run skips them
WORKERS = 16


def _ssl_context() -> ssl.SSLContext:
    try:
        import certifi
    except ImportError:
        return ssl.create_default_context()
    return ssl.create_default_context(cafile=certifi.where())


def _get(url: str) -> bytes | None:
    try:
        with urllib.request.urlopen(url, context=_ssl_context(), timeout=30) as resp:
            return resp.read()
    except urllib.error.HTTPError as err:
        if err.code == 404:
            return None
        raise


def _fix_declaration(data: bytes) -> bytes:
    """Repair what the viewer serves: text before the XML declaration, files that declare
    UTF-16 but are UTF-8 (A5-09-0D), Latin-1 characters in UTF-8 (D2-14-52, a degree sign)."""
    if (start := data.find(b"<?xml")) > 0:  # BOM or blank lines before the declaration
        data = data[start:]
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        data = data.decode("latin-1").encode("utf-8")
    head = data[:100]
    if head.startswith(b"<?xml") and b'encoding="UTF-16"' in head:
        return data.replace(b'encoding="UTF-16"', b'encoding="utf-8"', 1)
    return data


def _as_list(value):
    return value if isinstance(value, list) else [value]


def list_profiles(index: dict) -> list[str]:
    """Return all profiles in the viewer index as 'RR-FF-TT'."""
    profiles = []
    for rorg, entry in index.items():
        for func in _as_list(entry["function"]):
            for typ in _as_list(func["type"]):
                profiles.append(f"{rorg}-{func['value'][2:].upper()}-{typ['value'][2:].upper()}")
    return sorted(profiles)


def _referenced_profile(path: Path) -> str | None:
    """Some profiles (e.g. D2-01-09) only point to a shared definition (D2-01-00)."""
    if not path.exists():
        return None
    ref = ET.parse(path).getroot().find(".//type/ref")
    if ref is None or ref.find("rorg") is None:
        return None
    return "-".join(ref.findtext(tag).strip() for tag in ("rorg", "func", "type")).upper()


def _load_absent() -> set[str]:
    try:
        return set(json.loads(ABSENT.read_text()))
    except (OSError, ValueError):
        return set()


def _save_absent(absent: set[str]) -> None:
    ABSENT.write_text(json.dumps(sorted(absent)))


def _fetch_profile(profile: str, absent: set[str]) -> set[str]:
    """Download what is neither cached nor known to be absent; return the new 404s."""
    rorg, func, typ = profile.split("-")
    not_found = set()
    for suffix in SUFFIXES:
        name = f"{profile}{suffix}"
        if (CACHE / name).exists() or name in absent:
            continue
        data = _get(f"{BASE}/profiles/{rorg}/{func}/{typ}/{name}")
        if data is None:
            not_found.add(name)
            continue
        (CACHE / name).write_bytes(_fix_declaration(data))
    return not_found


def main(argv: list[str]) -> int:
    if argv == ["--generated"]:
        argv = []  # generate_eep.py writes every profile of the index
    CACHE.mkdir(exist_ok=True)
    raw = _get(INDEX_URL)
    if raw is None:
        print(f"index not found: {INDEX_URL}", file=sys.stderr)
        return 1
    (CACHE / "eep-viewer-desc.json").write_bytes(raw)
    profiles = list_profiles(json.loads(raw.decode("utf-8-sig")))
    wanted = [p for p in profiles if not argv or any(p.startswith(a.upper()) for a in argv)]
    wanted += [a.upper() for a in argv if len(a) == 8 and a.upper() not in wanted]
    absent = _load_absent()
    batch = list(wanted)
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        while batch:
            for not_found in pool.map(lambda p: _fetch_profile(p, absent), batch):
                absent.update(not_found)
            refs = (_referenced_profile(CACHE / f"{p}.xml") for p in batch)
            batch = []
            for ref in refs:
                if ref and ref not in wanted:
                    wanted.append(ref)
                    batch.append(ref)
    _save_absent(absent)
    missing = sum(f"{p}.xml" in absent for p in wanted)
    print(f"{len(wanted)} profiles in {CACHE} ({missing} without definition)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
