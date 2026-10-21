"""Generate docs/devices.md and docs/devices.de.md from the device catalog.

Usage:
    python scripts/gen_device_docs.py           # write
    python scripts/gen_device_docs.py --check   # CI: fail if out of date
"""

# ruff: noqa: E501

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from custom_components.enocean_eltako.catalog import (  # noqa: E402
    CATALOG,
    CATEGORIES,
    GROUP_VIRTUAL,
    GROUPS,
)
from custom_components.enocean_eltako.protocol.eep.std.profiles import PROFILES  # noqa: E402

COMPONENT = ROOT / "custom_components/enocean_eltako"
DOCS = ROOT / "docs"
HEADERS = {
    "en": ("Category", "Device", "Manufacturer", "Receives", "Sends (sender profiles)", "Entities"),
    "de": ("Kategorie", "Gerät", "Hersteller", "Empfängt", "Sendet (Sender-Profile)", "Entitäten"),
}


def _translations(lang: str) -> dict:
    return json.loads((COMPONENT / f"translations/{lang}.json").read_text(encoding="utf-8"))


def _category(data: dict, group: str, category: str) -> str:
    steps = data["config_subentries"]["device"]["step"]
    if group == GROUP_VIRTUAL:  # no category menu: the entry of the start menu
        return steps["user"]["menu_options"][GROUP_VIRTUAL]
    return steps[group]["menu_options"][f"{group}_{category}"]


def table(lang: str) -> str:
    data = _translations(lang)
    names = data["selector"]["device_model"]["options"]
    models = sorted(
        CATALOG.values(),
        key=lambda m: ((*GROUPS, GROUP_VIRTUAL).index(m.group), CATEGORIES.index(m.category)),
    )
    lines = [
        "| " + " | ".join(HEADERS[lang]) + " |",
        "| " + " | ".join("---" for _ in HEADERS[lang]) + " |",
    ]
    for model in models:
        receive = [str(model.receive)] if model.receive else []
        receive += [str(r) for r in model.receive_extra]
        senders = [f"{p.id}: {p.eep}" for p in model.senders]
        platforms = ", ".join(p.value for p in model.platforms)
        cells = (
            _category(data, model.group, model.category),
            names.get(model.id, model.id),
            model.manufacturer,
            "<br>".join(f"`{r}`" for r in receive) or "-",
            "<br>".join(f"`{s}`" for s in senders) or "-",
            platforms,
        )
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


TEXT = {
    "en": {
        "title": "Supported devices",
        "other": "Deutsch",
        "other_link": "devices.de.md",
        "intro": (
            "Generated from the device catalog by `scripts/gen_device_docs.py`; do not edit.\n"
            "Every profile is named as EEP plus variant (`std` = EnOcean Alliance definition,\n"
            "`eltako` = Eltako variant documented in `protocol/eep/eltako/`)."
        ),
        "gateways": "Gateways",
        "gateways_text": "One config entry per gateway. Serial gateways connect over USB or, through\n"
        "ser2net or the Device Proxy app, over TCP.",
        "gateway_cols": ("Gateway", "Connection"),
        "gateway_rows": (
            (
                "fgw14_usb",
                "Eltako series 14 bus (RS485) over USB; forms a bus group with the FAM14",
            ),
            ("fam14", "Eltako series 14 bus (RS485); may stay disconnected until it is needed"),
            ("fam_usb", "USB radio gateway (ESP2)"),
            ("mgw_eth", "Network (TCP, ESP3), found automatically"),
            ("symcon_lan", "Network (TCP, ESP3)"),
            ("esp3", "Any ESP3 gateway over USB or TCP"),
            ("esp2", "Any ESP2 gateway over USB or TCP"),
        ),
        "devices": "Devices of the catalog",
        "devices_text": (
            "Receives: telegrams the device sends to Home Assistant. Sends: sender profiles\n"
            "Home Assistant uses to control it, each with its own sender ID from the gateway's pool."
        ),
        "more": "Beyond the catalog",
        "more_text": (
            "- **By EEP** (expert): all {count} standard profiles of the EnOcean Alliance can be added\n"
            "  as a device with one sensor per value. Profiles outside the catalog are not checked\n"
            "  against hardware.\n"
            "- **Own definition**: sensors you describe in `/config/enocean_eltako/custom_devices.yaml`.\n"
            "- **Discovered senders**: every unknown sender a gateway hears is offered as a card\n"
            "  with a suggested kind.\n\n"
            "How to add each kind: [User Guide](USER-GUIDE.md). Learn function to set on an Eltako\n"
            "series 14 actuator for each teach-in button: [teach_in.md](teach_in.md)."
        ),
    },
    "de": {
        "title": "Unterstützte Geräte",
        "other": "English",
        "other_link": "devices.md",
        "intro": (
            "Aus dem Gerätekatalog von `scripts/gen_device_docs.py` erzeugt; nicht von Hand ändern.\n"
            "Jedes Profil heißt EEP plus Variante (`std` = Definition der EnOcean Alliance,\n"
            "`eltako` = Eltako-Variante, dokumentiert in `protocol/eep/eltako/`)."
        ),
        "gateways": "Gateways",
        "gateways_text": "Ein Eintrag pro Gateway. Serielle Gateways verbinden per USB oder, über ser2net\n"
        "oder die App Device Proxy, per TCP.",
        "gateway_cols": ("Gateway", "Anbindung"),
        "gateway_rows": (
            (
                "fgw14_usb",
                "Eltako-Bus der Baureihe 14 (RS485) per USB; bildet mit dem FAM14 eine Bus-Gruppe",
            ),
            (
                "fam14",
                "Eltako-Bus der Baureihe 14 (RS485); kann getrennt bleiben, bis er gebraucht wird",
            ),
            ("fam_usb", "USB-Funkgateway (ESP2)"),
            ("mgw_eth", "Netzwerk (TCP, ESP3), wird automatisch gefunden"),
            ("symcon_lan", "Netzwerk (TCP, ESP3)"),
            ("esp3", "Beliebiges ESP3-Gateway per USB oder TCP"),
            ("esp2", "Beliebiges ESP2-Gateway per USB oder TCP"),
        ),
        "devices": "Geräte des Katalogs",
        "devices_text": (
            "Empfängt: Telegramme, die das Gerät an Home Assistant sendet. Sendet: Sender-Profile,\n"
            "mit denen Home Assistant es steuert, je mit eigener Sender-ID aus dem Pool des Gateways."
        ),
        "more": "Über den Katalog hinaus",
        "more_text": (
            "- **Per EEP** (Experte): alle {count} Standardprofile der EnOcean Alliance lassen sich als\n"
            "  Gerät mit einem Sensor je Wert anlegen. Profile außerhalb des Katalogs sind nicht mit\n"
            "  Hardware geprüft.\n"
            "- **Eigene Definition**: Sensoren, die du in `/config/enocean_eltako/custom_devices.yaml`\n"
            "  beschreibst.\n"
            "- **Entdeckte Sender**: jeder unbekannte Sender, den ein Gateway hört, erscheint als Karte\n"
            "  mit einem Vorschlag für die Geräteart.\n\n"
            "Wie jede Art angelegt wird: [Benutzerhandbuch](USER-GUIDE.de.md). Welche Einlernfunktion am\n"
            "Eltako-Aktor der Baureihe 14 zu welchem Einlern-Button gehört: [teach_in.de.md](teach_in.de.md)."
        ),
    },
}


def doc(lang: str) -> str:
    text = TEXT[lang]
    names = _translations(lang)["selector"]["model"]["options"]
    gateways = [
        "| " + " | ".join(text["gateway_cols"]) + " |",
        "| --- | --- |",
        *(f"| {names[key]} | {how} |" for key, how in text["gateway_rows"]),
    ]
    return (
        f"# {text['title']}\n\n"
        f"[{text['other']}]({text['other_link']})\n\n"
        f"{text['intro']}\n\n"
        f"## {text['gateways']}\n\n{text['gateways_text']}\n\n" + "\n".join(gateways) + "\n\n"
        f"## {text['devices']}\n\n{text['devices_text']}\n\n{table(lang)}\n"
        f"## {text['more']}\n\n" + text["more_text"].format(count=len(PROFILES)) + "\n"
    )


def main(argv: list[str]) -> int:
    targets = {
        DOCS / "devices.md": doc("en"),
        DOCS / "devices.de.md": doc("de"),
    }
    stale = [p for p, text in targets.items() if not p.exists() or p.read_text("utf-8") != text]
    if "--check" in argv:
        if stale:
            print("out of date: " + ", ".join(str(p.relative_to(ROOT)) for p in stale))
            print("run python scripts/gen_device_docs.py")
            return 1
        print("device docs are up to date")
        return 0
    DOCS.mkdir(exist_ok=True)
    for path in stale:
        path.write_text(targets[path], encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
