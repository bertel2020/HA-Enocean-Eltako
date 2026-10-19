"""Generate docs/devices.md and the device table in README.md / README.de.md from the catalog.

Usage:
    python scripts/gen_device_docs.py           # write
    python scripts/gen_device_docs.py --check   # CI: fail if out of date
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from custom_components.enocean_eltako.catalog import CATALOG  # noqa: E402

COMPONENT = ROOT / "custom_components/enocean_eltako"
DOC = ROOT / "docs/devices.md"
START, END = "<!-- devices:start -->", "<!-- devices:end -->"
HEADERS = {
    "en": ("Device", "Manufacturer", "Receives", "Sends (sender profiles)", "Entities"),
    "de": ("Gerät", "Hersteller", "Empfängt", "Sendet (Sender-Profile)", "Entitäten"),
}


def _names(lang: str) -> dict[str, str]:
    data = json.loads((COMPONENT / f"translations/{lang}.json").read_text(encoding="utf-8"))
    return data["selector"]["device_model"]["options"]


def table(lang: str) -> str:
    names = _names(lang)
    lines = [
        "| " + " | ".join(HEADERS[lang]) + " |",
        "| " + " | ".join("---" for _ in HEADERS[lang]) + " |",
    ]
    for model in CATALOG.values():
        receive = [str(model.receive)] if model.receive else []
        receive += [str(r) for r in model.receive_extra]
        senders = [f"{p.id}: {p.eep}" for p in model.senders]
        platforms = ", ".join(p.value for p in model.platforms)
        cells = (
            names.get(model.id, model.id),
            model.manufacturer,
            "<br>".join(f"`{r}`" for r in receive) or "-",
            "<br>".join(f"`{s}`" for s in senders) or "-",
            platforms,
        )
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def doc() -> str:
    return (
        "# Supported devices\n\n"
        "Generated from the device catalog by `scripts/gen_device_docs.py`; do not edit.\n"
        "Every profile is named as EEP plus variant (`std` = EnOcean Alliance definition,\n"
        "`eltako` = Eltako variant documented in `protocol/eep/eltako/`).\n\n" + table("en")
    )


def with_table(text: str, lang: str) -> str:
    head, _, rest = text.partition(START)
    _, _, tail = rest.partition(END)
    return f"{head}{START}\n{table(lang)}{END}{tail}"


def main(argv: list[str]) -> int:
    targets = {
        DOC: doc(),
        ROOT / "README.md": with_table((ROOT / "README.md").read_text(encoding="utf-8"), "en"),
        ROOT / "README.de.md": with_table(
            (ROOT / "README.de.md").read_text(encoding="utf-8"), "de"
        ),
    }
    stale = [p for p, text in targets.items() if not p.exists() or p.read_text("utf-8") != text]
    if "--check" in argv:
        if stale:
            print("out of date: " + ", ".join(str(p.relative_to(ROOT)) for p in stale))
            print("run python scripts/gen_device_docs.py")
            return 1
        print("device docs are up to date")
        return 0
    DOC.parent.mkdir(exist_ok=True)
    for path in stale:
        path.write_text(targets[path], encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
