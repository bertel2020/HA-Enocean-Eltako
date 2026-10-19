"""Download official EEP definitions from the EnOcean Alliance EEP Viewer.

The files are the property of the EnOcean Alliance (free for non-commercial use)
and are never committed: they land in .eep_cache/ (git-ignored) and are only used
by the generator and tests during development and CI.

Usage:
    python scripts/fetch_eep.py                 # all profiles
    python scripts/fetch_eep.py A5-38-08 D2-01  # profiles or prefixes
"""

from __future__ import annotations

import json
import ssl
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

BASE = "https://tools.enocean-alliance.org/EEPViewer"
INDEX_URL = f"{BASE}/eep-viewer-desc.json"
CACHE = Path(__file__).resolve().parent.parent / ".eep_cache"
SUFFIXES = (".xml", "_test.xml")


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


def main(argv: list[str]) -> int:
    CACHE.mkdir(exist_ok=True)
    raw = _get(INDEX_URL)
    if raw is None:
        print(f"index not found: {INDEX_URL}", file=sys.stderr)
        return 1
    (CACHE / "eep-viewer-desc.json").write_bytes(raw)
    profiles = list_profiles(json.loads(raw.decode("utf-8-sig")))
    wanted = [p for p in profiles if not argv or any(p.startswith(a.upper()) for a in argv)]
    missing = 0
    queue = list(wanted)
    while queue:
        profile = queue.pop(0)
        rorg, func, typ = profile.split("-")
        for suffix in SUFFIXES:
            target = CACHE / f"{profile}{suffix}"
            if target.exists():
                continue
            data = _get(f"{BASE}/profiles/{rorg}/{func}/{typ}/{profile}{suffix}")
            if data is None:
                missing += suffix == ".xml"
                continue
            target.write_bytes(data)
        ref = _referenced_profile(CACHE / f"{profile}.xml")
        if ref and ref not in wanted:
            wanted.append(ref)
            queue.append(ref)
    print(f"{len(wanted)} profiles in {CACHE} ({missing} without definition)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
