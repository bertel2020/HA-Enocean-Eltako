"""Turn a capture of the `enocean_eltako.capture` action into an anonymous test fixture.

Usage:
    python scripts/capture_to_fixture.py capture-20261101-120000.jsonl tests/fixtures/ftke.jsonl

Sender and destination IDs are replaced by stable placeholders (IDs in the gateway's base ID
range stay in that range, so the sender pool logic still applies), gateway names by `gw1`, `gw2`
and the time stamps by an offset from a fixed date. The telegram data, status and signal strength
are kept, as they are what the decoders need. The mapping is printed to stderr and never written.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

BROADCAST = "FF-FF-FF-FF"
KEEP = {"00-00-00-00", BROADCAST}
EPOCH = datetime(2000, 1, 1, tzinfo=UTC)


def anonymise(lines: list[str]) -> tuple[list[str], dict[str, str]]:
    """The fixture lines for the capture lines, and the mapping that was applied."""
    entries = [json.loads(line) for line in lines if line.strip()]
    ids: dict[str, str] = {}
    gateways: dict[str, str] = {}

    def alias(value: str) -> str:
        if value in KEEP:
            return value
        if value not in ids:
            base = value.startswith("FF-")
            number = sum(1 for v in ids.values() if v.startswith("FF-") == base) + 1
            ids[value] = f"FF-80-00-{number:02X}" if base else f"05-00-00-{number:02X}"
        return ids[value]

    first = min((datetime.fromisoformat(e["time"]) for e in entries), default=EPOCH)
    out = []
    for entry in entries:
        offset = datetime.fromisoformat(entry["time"]) - first
        entry["time"] = (EPOCH + timedelta(seconds=offset.total_seconds())).isoformat(
            timespec="milliseconds"
        )
        entry["gateway"] = gateways.setdefault(entry["gateway"], f"gw{len(gateways) + 1}")
        entry["sender"] = alias(entry["sender"])
        entry["destination"] = alias(entry["destination"])
        out.append(json.dumps(entry) + "\n")
    return out, ids


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("capture", type=Path, help="capture-*.jsonl from the capture action")
    parser.add_argument("fixture", type=Path, help="where to write the anonymous fixture")
    args = parser.parse_args(argv)
    lines, mapping = anonymise(args.capture.read_text(encoding="utf-8").splitlines())
    args.fixture.parent.mkdir(parents=True, exist_ok=True)
    args.fixture.write_text("".join(lines), encoding="utf-8")
    print(f"{len(lines)} telegrams -> {args.fixture}", file=sys.stderr)
    for real, fake in mapping.items():
        print(f"  {real} -> {fake}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
