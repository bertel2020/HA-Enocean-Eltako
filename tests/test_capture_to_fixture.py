"""scripts/capture_to_fixture.py: anonymous fixtures from captures."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import capture_to_fixture as tool  # noqa: E402


def _line(time: str, sender: str, destination: str = "FF-FF-FF-FF", gateway: str = "abc") -> str:
    return json.dumps(
        {
            "time": time,
            "gateway": gateway,
            "dir": "rx",
            "rorg": "F6",
            "data": "70",
            "sender": sender,
            "status": "30",
            "destination": destination,
            "dbm": -61,
            "duplicate": False,
        }
    )


def test_ids_gateways_and_times_are_replaced() -> None:
    lines, mapping = tool.anonymise(
        [
            _line("2026-11-01T10:00:00.000+00:00", "00-21-63-43"),
            _line("2026-11-01T10:00:02.500+00:00", "FF-B7-44-81", "00-21-63-43", "other"),
            _line("2026-11-01T10:00:03.000+00:00", "00-21-63-43"),
        ]
    )
    entries = [json.loads(line) for line in lines]
    assert [e["sender"] for e in entries] == ["05-00-00-01", "FF-80-00-01", "05-00-00-01"]
    assert entries[1]["destination"] == "05-00-00-01"
    assert entries[0]["destination"] == "FF-FF-FF-FF"  # broadcast stays
    assert [e["gateway"] for e in entries] == ["gw1", "gw2", "gw1"]
    assert entries[0]["time"] == "2000-01-01T00:00:00.000+00:00"
    assert entries[1]["time"] == "2000-01-01T00:00:02.500+00:00"
    assert (entries[0]["data"], entries[0]["status"], entries[0]["dbm"]) == ("70", "30", -61)
    assert mapping == {"00-21-63-43": "05-00-00-01", "FF-B7-44-81": "FF-80-00-01"}
    assert "00-21-63-43" not in "".join(lines)


def test_empty_capture_and_command_line(tmp_path: Path) -> None:
    assert tool.anonymise([]) == ([], {})
    source, target = tmp_path / "capture.jsonl", tmp_path / "out" / "fixture.jsonl"
    source.write_text(_line("2026-11-01T10:00:00.000+00:00", "00-21-63-43") + "\n\n")
    assert tool.main([str(source), str(target)]) == 0
    assert json.loads(target.read_text())["sender"] == "05-00-00-01"
