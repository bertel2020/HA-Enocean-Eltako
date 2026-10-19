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

> **Status: frühe Entwicklung.** Gateways lassen sich anlegen (FAM-USB,
> FGW14-USB, FAM14, MGW-ETH mit automatischer Erkennung, Symcon LAN, generisch
> ESP2/ESP3; per USB oder ser2net) und bleiben verbunden. FGW14-USB und FAM14
> am selben Bus bilden eine Bus-Gruppe mit Failover; der FAM14 kann getrennt
> bleiben, bis er gebraucht wird. Geräte werden pro Gateway angelegt
> (Schaltaktoren, Dimmer, Rollläden, Fenstergriffe, Kontakte, Taster, Zähler
> und Sensoren aus dem Katalog). Telegramme stehen in den Diagnosedaten und
> lassen sich mit der Aktion `enocean_eltako.capture` mitschneiden. Noch nicht
> mit echter Hardware getestet. Nicht produktiv einsetzen. Die bestehende
> Integration `eltako` läuft parallel weiter; diese hier hat die eigene
> Domain `enocean_eltako`.

Eine neu geschriebene Integration für Eltako (Baureihe 14 am Bus und Funk) und
andere EnOcean-Geräte. Ziele:

- **Nur über die Oberfläche:** ein Eintrag pro Gateway, ein Untereintrag pro
  Gerät, kein YAML
- **Gateways:** FGW14-USB und FAM14 am RS485-Bus (als Bus-Gruppe mit
  Failover), FAM-USB, PioTek MGW-ETH, Symcon EnOcean LAN Gateway; jedes
  USB-Gateway auch über ser2net (TCP)
- **Alle EEPs inkl. VLD**, Standardprofile erzeugt aus den offiziellen
  Definitionen der EnOcean Alliance; Eltako-Varianten streng getrennt
- **Rollläden** (FSB14/61/71) mit Controller- und Richtungstaster-Sender
  parallel, Positionsverfolgung und Kalibrierung an den Endlagen
- **Anlernen, Discovery, Telegramm-Monitor**, Import aus dem Bus-Speicher des
  FAM14 und ein Übernahme-Assistent für die alte Integration `eltako`
- **Keine fremden EnOcean-Bibliotheken:** keine zusätzlichen Pakete; serielle
  Ports laufen über die Port-Auswahl und die Seriell-Bibliothek von Home
  Assistant (usb-Integration), damit gehen auch serielle ESPHome-Proxys

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

## Entwicklung

```bash
python -m pip install -r requirements_test.txt
ruff check custom_components tests scripts
python scripts/check_protocol_imports.py
python -m pytest
```

`python scripts/fetch_eep.py --generated` und danach
`python scripts/generate_eep.py` erzeugen die Standardprofile neu.
`python scripts/fetch_eep.py` lädt die offiziellen EEP-Definitionen nach
`.eep_cache/`. Diese Dateien gehören der EnOcean Alliance und werden nie
eingecheckt (siehe [NOTICE](NOTICE)).

## Dank

Diese Integration ist neu geschrieben, wäre aber ohne die Arbeit und Erfahrung
dieser Projekte und ihrer Autoren nicht entstanden:

- [grimmpp/home-assistant-eltako](https://github.com/grimmpp/home-assistant-eltako)
  (Philipp Grimm): die bisherige Eltako-Integration; dort wiederum Dank an
  chrysn und Johannes Bosecker für die erste Version sowie an Cedric Van Labeke
  und LHBL2003.
- [grimmpp/eltako14bus](https://github.com/grimmpp/eltako14bus): ursprünglich
  von Christian Amsüss und Energy Harvesting Solutions (2016–2020),
  weiterentwickelt von Philipp Grimm.
- [grimmpp/esp2_gateway_adapter](https://github.com/grimmpp/esp2_gateway_adapter)
  (Philipp Grimm).
- [kipe/enocean](https://github.com/kipe/enocean) (Kimmo Huoman).
- [grimmpp/enocean-device-manager](https://github.com/grimmpp/enocean-device-manager)
  (eo_man).

Aus diesen Projekten wurde kein Code übernommen. Lizenzpflichten stehen in
[LICENSE](LICENSE) und [NOTICE](NOTICE).

## Lizenz

[MIT](LICENSE). EnOcean ist eine eingetragene Marke der EnOcean GmbH, Eltako
der Eltako GmbH. Dieses Projekt steht mit keinem der beiden Unternehmen in
Verbindung.
