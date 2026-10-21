<p align="center"><picture><source media="(prefers-color-scheme: dark)" srcset="custom_components/enocean_eltako/brand/dark_logo.png"><img src="custom_components/enocean_eltako/brand/logo.png" alt="EnOcean Eltako Logo" width="350"></picture></p>

<h1 align="center">EnOcean Eltako für Home Assistant</h1>

<p align="center">
  Eltako- und EnOcean-Geräte in Home Assistant, komplett über die Oberfläche eingerichtet.
</p>

<p align="center">
  <a href="https://github.com/hacs/integration"><img src="https://img.shields.io/badge/HACS-Custom-41BDF5.svg" alt="HACS Custom"></a>
  <a href="https://www.home-assistant.io/"><img src="https://img.shields.io/badge/Home%20Assistant-Custom%20Integration-18BCF2.svg?logo=home-assistant&logoColor=white" alt="Home Assistant"></a>
  <a href="https://github.com/bertel2020/HA-Enocean-Eltako/releases"><img src="https://img.shields.io/github/v/release/bertel2020/HA-Enocean-Eltako?sort=semver&include_prereleases" alt="Release"></a>
  <a href="https://github.com/bertel2020/HA-Enocean-Eltako/actions/workflows/validate.yml"><img src="https://github.com/bertel2020/HA-Enocean-Eltako/actions/workflows/validate.yml/badge.svg" alt="Validate"></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/bertel2020/HA-Enocean-Eltako" alt="Lizenz"></a>
</p>

<p align="center">
  <a href="https://buymeacoffee.com/bertel2020"><img src="https://img.shields.io/badge/Buy%20Me%20a%20Coffee-support-FFDD00?logo=buy-me-a-coffee&logoColor=black" alt="Buy Me a Coffee"></a>
  <a href="https://ko-fi.com/bertel2020"><img src="https://img.shields.io/badge/Ko--fi-support-FF5E5B?logo=ko-fi&logoColor=white" alt="Ko-fi"></a>
  <a href="https://paypal.me/RobertoMartins"><img src="https://img.shields.io/badge/PayPal-donate-00457C?logo=paypal&logoColor=white" alt="PayPal"></a>
</p>

<p align="center"><em><a href="README.md">English version</a></em></p>

> **Status: frühe Entwicklung.** Noch nicht mit echter Hardware getestet; nicht produktiv
> einsetzen. Die bestehende Integration `eltako` läuft parallel weiter; diese hier hat die
> eigene Domain `enocean_eltako`.

EnOcean Eltako bindet Eltako-Geräte (Baureihe 14 am Bus und Funk) und andere EnOcean-Geräte in Home Assistant ein. Die Integration ist neu geschrieben, braucht keine fremde EnOcean-Bibliothek und wird komplett über die Oberfläche eingerichtet: ein Eintrag pro Gateway, ein Untereintrag pro Gerät, kein YAML.

## Highlights

- **Gateways:** Eltako FGW14-USB und FAM14 (RS485-Bus, als Bus-Gruppe mit Failover), FAM-USB, PioTek MGW-ETH, Symcon EnOcean LAN Gateway sowie generische ESP2-/ESP3-Gateways; jedes USB-Gateway auch über ser2net (TCP).
- **Geräte:** Schaltaktoren, Dimmer, Rollläden, Heizungsaktoren und Raumregler, Fenstergriffe, Kontakte, Taster, Zähler, Sensoren, Permundo-Zwischenstecker und VLD-Aktoren. Jedes Standardprofil von EnOcean lässt sich als generisches Gerät anlegen. Vollständige Liste: [docs/devices.de.md](docs/devices.de.md).
- **Rollläden** mit Controller- und Richtungstaster-Sender parallel, Positionsverfolgung, Lüftungsschlitzen, Lamellenstellung und Laufzeit-Assistent.
- **Virtuelle Sensoren:** Home-Assistant-Entitäten als EnOcean-Kontakt, -Bewegungsmelder, -Temperatur, -Helligkeit, -Wetter oder -Taster senden, z. B. für die Beschattungsautomatik eines Aktors.
- **Anlernen, Discovery und ein Live-Telegramm-Monitor** im Seitenleisten-Panel **EnOcean**, dazu Mitschnitt und Diagnosedaten für Fehlerberichte.
- **Übernahme** der Geräte der alten Integration `eltako`, ohne die Aktoren neu einzulernen.
- **Sicherheit bleibt im Aktor:** Wind-, Regen-, Frost- und Aussperrschutz werden nie ersetzt.

## Installation

### Über HACS (empfohlen)

[![HACS-Repository in My Home Assistant öffnen](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=bertel2020&repository=HA-Enocean-Eltako&category=integration)
[![EnOcean Eltako zu My Home Assistant hinzufügen](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=enocean_eltako)

1. Über den ersten Button das EnOcean-Eltako-Repository in HACS öffnen.
2. **EnOcean Eltako** herunterladen und Home Assistant neu starten.
3. Über den zweiten Button die Integration hinzufügen. Alternativ in Home
   Assistant **Einstellungen → Geräte & Dienste → Integration hinzufügen →
   EnOcean Eltako** öffnen.

Falls der erste Button nicht funktioniert, in HACS unter **Integrationen →
Benutzerdefinierte Repositories** `https://github.com/bertel2020/HA-Enocean-Eltako`
als Kategorie **Integration** eintragen.

### Manuell

Das Verzeichnis `custom_components/enocean_eltako` nach
`/config/custom_components/enocean_eltako` kopieren und Home Assistant neu
starten.

## Schnellstart

1. Die Integration pro Gateway einmal hinzufügen und Modell und Anbindung wählen (USB-Port oder Host und Port).
2. Unter dem Gateway **Gerät hinzufügen** wählen: das Gerät durch Tastendruck anlernen oder aus dem Katalog aussuchen. Sender, die das Gateway von selbst hört, erscheinen als **entdeckt**-Karten.
3. Im Seitenleisten-Panel **EnOcean** Telegramme live beobachten und Sender-IDs prüfen.

Jeder Schritt, alle Gerätearten, das Panel, die Übernahme, Blueprints, bekannte Einschränkungen und die Fehlersuche stehen im **[Benutzerhandbuch](docs/USER-GUIDE.de.md)**.

## Dokumentation

- [Benutzerhandbuch](docs/USER-GUIDE.de.md)
- [Unterstützte Geräte](docs/devices.de.md)
- [Einlernfunktionen der Eltako-Aktoren Baureihe 14](docs/teach_in.de.md)

## Entwicklung

```bash
python -m pip install -r requirements_test.txt
ruff check custom_components tests scripts
mypy
python scripts/check_protocol_imports.py
python -m pytest
```

`python scripts/gen_device_docs.py` erzeugt [docs/devices.de.md](docs/devices.de.md) und [docs/devices.md](docs/devices.md) aus dem Gerätekatalog neu. `python scripts/fetch_eep.py --generated` und danach `python scripts/generate_eep.py` erzeugen die Standardprofile neu; `python scripts/fetch_eep.py` lädt die offiziellen EEP-Definitionen nach `.eep_cache/`. Diese Dateien gehören der EnOcean Alliance und werden nie eingecheckt (siehe [NOTICE](NOTICE)).

## Dank

Diese Integration ist neu geschrieben, wäre aber ohne die Arbeit und Erfahrung dieser Projekte und ihrer Autoren nicht entstanden:

- [grimmpp/home-assistant-eltako](https://github.com/grimmpp/home-assistant-eltako) (Philipp Grimm): die bisherige Eltako-Integration; dort wiederum Dank an chrysn und Johannes Bosecker für die erste Version sowie an Cedric Van Labeke und LHBL2003.
- [grimmpp/eltako14bus](https://github.com/grimmpp/eltako14bus): ursprünglich von Christian Amsüss und Energy Harvesting Solutions (2016–2020), weiterentwickelt von Philipp Grimm.
- [grimmpp/esp2_gateway_adapter](https://github.com/grimmpp/esp2_gateway_adapter) (Philipp Grimm).
- [kipe/enocean](https://github.com/kipe/enocean) (Kimmo Huoman).
- [grimmpp/enocean-device-manager](https://github.com/grimmpp/enocean-device-manager) (eo_man).

Aus diesen Projekten wurde kein Code übernommen. Lizenzpflichten stehen in [LICENSE](LICENSE) und [NOTICE](NOTICE).

## Lizenz

[MIT](LICENSE). EnOcean ist eine eingetragene Marke der EnOcean GmbH, Eltako der Eltako GmbH. Dieses Projekt steht mit keinem der beiden Unternehmen in Verbindung.
