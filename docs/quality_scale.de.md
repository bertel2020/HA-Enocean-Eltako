# Quality Scale

[English](quality_scale.md)

Selbsteinschätzung nach der [Integration Quality Scale von Home Assistant](https://developers.home-assistant.io/docs/core/integration-quality-scale/)
(Phase 5). Home Assistant bewertet Custom Integrations nicht; diese Liste hält fest, was
erledigt ist und was fehlt.

Stand: **Bronze, Silber, Gold und Platin vollständig** (Selbsteinschätzung).

## Bronze

| Regel | Status | Wo |
| --- | --- | --- |
| action-setup | erledigt | Dienste in `async_setup` registriert (`services.py`) |
| appropriate-polling | erledigt | lokal, Push; nur die Gateway-Zähler werden abgefragt |
| brands | erledigt | `brand/` |
| common-modules | erledigt | `entity.py`, `device.py`, `hub.py`, `gateway_entity.py` |
| config-flow-test-coverage | erledigt | `tests/test_config_flow.py`, `tests/test_devices.py` |
| config-flow | erledigt | Gateway-Eintrag, Geräte-Untereinträge, Optionen |
| dependency-transparency | erledigt | keine Requirements, eigene Protokollschicht |
| docs-actions | erledigt | README „Actions“ |
| docs-high-level-description | erledigt | README-Einleitung |
| docs-installation-instructions | erledigt | README „Installation“ |
| docs-removal-instructions | erledigt | README „Removal“ |
| entity-event-setup | erledigt | Listener in `async_added_to_hass` |
| entity-unique-id | erledigt | Base-ID + Geräte-ID + Schlüssel |
| has-entity-name | erledigt | alle Entitäten |
| runtime-data | erledigt | `GatewayRuntime` in `entry.runtime_data` |
| test-before-configure | erledigt | Verbindungstest und Base-ID im Config Flow |
| test-before-setup | erledigt | `ConfigEntryNotReady`, wenn das Gateway nicht antwortet |
| unique-config-entry | erledigt | Base-ID als Unique ID |

## Silber

| Regel | Status | Wo |
| --- | --- | --- |
| action-exceptions | erledigt | übersetzte `HomeAssistantError` bei Offline-Gateway und Positionen |
| config-entry-unloading | erledigt | `async_unload_entry` schließt Gateway und Queue |
| docs-configuration-parameters | erledigt | README „Gateway options and repairs“ |
| docs-installation-parameters | erledigt | README „Supported devices“ und die Flow-Texte |
| entity-unavailable | erledigt | Option pro Gerät: nicht verfügbar bei Stille (E5) |
| integration-owner | erledigt | `codeowners` im Manifest |
| log-when-unavailable | erledigt | eine Warnung pro Gateway-Ausfall, Info bei Rückkehr |
| parallel-updates | erledigt | `PARALLEL_UPDATES = 0` auf jeder Plattform (die Sendewarteschlange serialisiert) |
| reauthentication-flow | entfällt | keine Zugangsdaten |
| test-coverage | erledigt | über 95 %; die CI schlägt darunter fehl (`pytest --cov=custom_components/enocean_eltako --cov-fail-under=95`) |

## Gold

| Regel | Status | Wo |
| --- | --- | --- |
| devices | erledigt | ein Gerät pro Gateway und pro Untereintrag, über das Gateway |
| diagnostics | erledigt | `diagnostics.py` |
| discovery | erledigt | Zeroconf (MGW-ETH), Device-Proxy-App (Supervisor), erkannte EnOcean-Sender (unter „Gerät hinzufügen“) |
| discovery-update-info | erledigt | ein bekanntes MGW-ETH mit neuer Adresse oder ein Proxy-Gateway mit neuem Port wird über die Base-ID erkannt und ohne Rückfrage aktualisiert |
| docs-data-update | erledigt | lokal, Push; Gateway-Zähler alle 30 s |
| docs-examples | erledigt | Blueprints |
| docs-known-limitations | erledigt | README „Known limitations“ |
| docs-supported-devices | erledigt | `docs/devices.md` (erzeugt) |
| docs-supported-functions | erledigt | README, `docs/devices.md` |
| docs-troubleshooting | erledigt | README „Troubleshooting“ |
| docs-use-cases | erledigt | README, virtuelle Sensoren, Blueprints |
| dynamic-devices | erledigt | Untereinträge zur Laufzeit hinzufügen und entfernen |
| entity-category | erledigt | Diagnose- und Konfigurationsentitäten |
| entity-device-class | erledigt | wo es eine Geräteklasse gibt |
| entity-disabled-by-default | erledigt | laute Diagnosewerte deaktiviert |
| entity-translations | erledigt | `translations/` |
| exception-translations | erledigt | `exceptions` in den Übersetzungen |
| icon-translations | erledigt | `icons.json` für jede übersetzte Entität, Zustände und Aktionen |
| reconfiguration-flow | erledigt | Gateway und Gerät neu konfigurieren |
| repair-issues | erledigt | getrenntes Gateway, stilles Gerät, Base-ID, langsamer Bus, Telegramme, die nicht zum Profil passen |
| stale-devices | erledigt | Entfernen eines Untereintrags entfernt sein Gerät und gibt seine Sender frei |

## Platin

| Regel | Status | Wo |
| --- | --- | --- |
| async-dependency | erledigt | asyncio-Streams, `serialx` |
| inject-websession | entfällt | kein HTTP |
| strict-typing | erledigt | `mypy --strict` in der CI (`pyproject.toml`), Re-Exporte von Home Assistant erlaubt |

## Erzeugte EEP-Profile

Phase 5 erzeugt jedes Standardprofil des EEP Viewers der EnOcean Alliance (318) und prüft
es gegen die offiziellen Testcontainer. Bei 34 Profilen außerhalb des Katalogs widersprechen
sich Container und generischer Decoder (mehrere Fälle, die die Daten nicht unterscheiden
können, z. B. A5-3F-00 oder die A5-20-Ventile, oder Fehler in den Containern); sie sind in
`tests/protocol/test_eep_official.py` als `UNVERIFIED_PROFILES` markiert, bis ein Profil geprüft ist.
