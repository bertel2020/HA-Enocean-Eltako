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

> **Status: frühe Entwicklung.** Gateways lassen sich anlegen (FAM-USB,
> FGW14-USB, FAM14, MGW-ETH mit automatischer Erkennung, Symcon LAN, generisch
> ESP2/ESP3; per USB oder ser2net) und bleiben verbunden. FGW14-USB und FAM14
> am selben Bus bilden eine Bus-Gruppe mit Failover; der FAM14 kann getrennt
> bleiben, bis er gebraucht wird. Geräte werden pro Gateway angelegt, per ID
> oder durch Warten auf ein Telegramm: Schaltaktoren, Dimmer, Rollläden
> (Controller und Richtungstaster parallel), Fenstergriffe, Kontakte, Taster,
> Zähler, Sensoren, Permundo PSC132/PSC234, Raumregler und Heizungsaktoren,
> die Home Assistant regelt. Telegramme stehen in den Diagnosedaten und
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

## Unterstützte Geräte

Ein Gerät kommt unter dem Gateway mit **Gerät hinzufügen** dazu, auf einem von vier Wegen:

- **Gerät anlernen** (empfohlen): eine Taste am Gerät drücken oder den Aktor vor Ort
  schalten; die Geräteart wird aus dem Telegramm vorgeschlagen.
- **Eltako-Gerät** oder **EnOcean-Gerät anderer Hersteller**: Kategorie und Geräteart aus
  dem Katalog wählen.
- **Per EEP** (Experte): Standard-Sensorprofile werden zu einem Gerät mit einem Sensor je Wert.

Aus dem Katalog erzeugt; Details in [docs/devices.md](docs/devices.md).

<!-- devices:start -->
| Kategorie | Gerät | Hersteller | Empfängt | Sendet (Sender-Profile) | Entitäten |
| --- | --- | --- | --- | --- | --- |
| Licht und Schalten | Schaltaktor (FSR61, FSR14, FL62 …) | Eltako | `M5-38-08:eltako` | `central: A5-38-08:eltako`<br>`rocker: F6-02-01:std` | light, switch |
| Licht und Schalten | Dimmaktor (FUD14, FUD61, FD62 …) | Eltako | `A5-38-08:eltako` | `central: A5-38-08:eltako`<br>`rocker: F6-02-01:std` | light |
| Rollläden und Jalousien | Rollladen / Jalousie (FSB14, FSB61, FSB71 …) | Eltako | `G5-3F-7F:eltako` | `controller: H5-3F-7F:eltako`<br>`direction_rocker: F6-02-01:std` | cover |
| Heizung und Klima | Heizungsaktor, Home Assistant regelt (FHK14, FAE14 …) | Eltako | `M5-10-06:eltako` | `controller: A5-10-06:eltako`<br>`cooling: F6-02-01:std` | climate, sensor |
| Heizung und Klima | Raumregler (FUTH, FTR65HS …) | Eltako | `A5-10-06:eltako` | - | climate, sensor |
| Taster und Kontakte | Fenstergriff (FTKE, FFG7B …) | Eltako | `F6-10-00:std` | - | sensor, binary_sensor |
| Taster und Kontakte | Tür-/Fensterkontakt (FTK, FTKB …) | Eltako | `D5-00-01:std` | - | binary_sensor |
| Taster und Kontakte | Wippentaster (F4T55E, FT55, FT4F …) | Eltako | `F6-02-01:std` | - | event |
| Taster und Kontakte | Kontakt über Tastertelegramme (FTS14EM, Garagentor …) | Eltako | `F6-02-01:std` | - | binary_sensor |
| Sensoren | Temperatur und Feuchte (FAFT60, FFT65B …) | Eltako | `A5-04-02:std` | - | sensor |
| Sensoren | Bewegungs- und Helligkeitssensor (FBH65 …) | Eltako | `A5-08-01:eltako` | - | sensor, binary_sensor |
| Sensoren | CO2-Sensor (FCO2TF65) | Eltako | `A5-09-04:std` | - | sensor |
| Sensoren | Wetterstation (FWS61, FWG14) | Eltako | `A5-13-01:eltako` | - | sensor, binary_sensor |
| Zähler | Energiezähler (FWZ12, FSDG14, DSZ14 …) | Eltako | `A5-12-01:eltako` | - | sensor |
| Zähler | Gaszähler (F3Z14D …) | Eltako | `A5-12-02:eltako` | - | sensor |
| Zähler | Wasserzähler (F3Z14D …) | Eltako | `A5-12-03:eltako` | - | sensor |
| Licht und Schalten | Permundo PSC132 / PSC234 Zwischenstecker | Permundo | `D2-01-09:std`<br>`A5-12-01:std`<br>`M5-38-08:eltako` | `controller: A5-38-08:std` | switch, light, sensor |
| Taster und Kontakte | Wippentaster (NodOn, PEHA, Jung …) | EnOcean | `F6-02-01:std` | - | event |
| Taster und Kontakte | Fenstergriff (Hoppe SecuSignal …) | EnOcean | `F6-10-00:std` | - | sensor, binary_sensor |
| Taster und Kontakte | Tür-/Fensterkontakt (NodOn …) | EnOcean | `D5-00-01:std` | - | binary_sensor |
<!-- devices:end -->

## Blueprints

Taster melden je Taste kurzes, langes und doppeltes Drücken. Fertige Automationen:

- [Wippe schaltet und dimmt Licht](https://github.com/bertel2020/HA-Enocean-Eltako/blob/main/blueprints/automation/enocean_eltako/rocker_light.yaml) [![Importieren](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fbertel2020%2FHA-Enocean-Eltako%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fenocean_eltako%2Frocker_light.yaml)
- [Wippe steuert Rollladen](https://github.com/bertel2020/HA-Enocean-Eltako/blob/main/blueprints/automation/enocean_eltako/rocker_cover.yaml) [![Importieren](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fbertel2020%2FHA-Enocean-Eltako%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fenocean_eltako%2Frocker_cover.yaml)
- [Doppelklick ruft Szene](https://github.com/bertel2020/HA-Enocean-Eltako/blob/main/blueprints/automation/enocean_eltako/double_press_scene.yaml) [![Importieren](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fbertel2020%2FHA-Enocean-Eltako%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fenocean_eltako%2Fdouble_press_scene.yaml)
- [Rollläden zeitgesteuert kalibrieren](https://github.com/bertel2020/HA-Enocean-Eltako/blob/main/blueprints/automation/enocean_eltako/calibrate_covers.yaml) [![Importieren](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fbertel2020%2FHA-Enocean-Eltako%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fenocean_eltako%2Fcalibrate_covers.yaml)

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
