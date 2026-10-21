# Changelog

All notable changes to this project are documented here, in English and German
(Deutsche Fassung weiter unten: [Deutsch](#deutsch)). The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## English

### [0.1.0] - 2026-10-21

First version of the integration.

#### Added

- **Gateways:** Eltako FGW14-USB, FAM14 and FAM-USB, PioTek MGW-ETH (found through zeroconf), Symcon
  EnOcean LAN Gateway and generic ESP2/ESP3 gateways. Serial ports use
  Home Assistant's port picker, TCP (ser2net, LAN gateways) is supported too. Several gateways
  work side by side, and the FAM14 bus can be used through bus groups with failover.
- **Configuration only through the UI:** one config entry per gateway, one subentry per device.
  Devices are added by learning the ID from a telegram, by category and kind, or by EEP.
  Reconfigure is available for gateways and devices.
- **Devices:** switching and dimming actuators (also channel 2 of two-channel actuators),
  covers with position, vent slots and slat tilt, heating actuators and room controllers
  (with cooling mode), meters (electricity, gas, water, energy dashboard ready), window
  handles, contacts, wall switches, weather and air quality sensors, Permundo PSC plugs and
  all standard EEP profiles as generic devices. [docs/devices.md](docs/devices.md) lists them.
- **Several senders per actuator** (central command, rocker, controller, direction rocker),
  with a sender ID pool: IDs are taken from base ID + 0...127 and stay blocked until the
  teach-out is confirmed.
- **Covers:** position tracking that anchors on end positions, a travel time assistant and
  calibration (also on a schedule through a blueprint).
- **Rocker gestures** (single, double, long press) with device triggers, plus blueprints for
  lights, covers, scenes and calibration.
- **Virtual devices:** Home Assistant sends as a contact (also with priority for lock-out
  protection), temperature, motion and brightness sensor, weather station, scene button or
  rocker with selectable buttons.
- **Telegram monitor panel:** live telegram list with details, filters, sorting, exports,
  signal quality per sender, gateway cards, sending a telegram and adding unknown senders as
  devices. Also:
  - a device view with one line per sender, sortable
  - the sender IDs of each device, blocked ones first
  - a layout for phones
- **Takeover from the old `eltako` integration** in the panel, in guided steps: preview,
  selection, area and label carry-over and a mapping of old to new entity IDs with their usage.
- **Gateway care:** last-seen monitoring, state reconciliation at startup, repairs for an
  unstable or silent connection, diagnostic sensors and diagnostics download.
- **EnOcean Proxy** gateways are set up through Supervisor discovery.
- Translations in German and English, brand images, German and English READMEs and a user
  guide.

#### Notes

- The protocol layer (ESP2/ESP3, EEPs, FAM14 bus) is implemented in this repository without
  EnOcean or Eltako libraries.
- The official EnOcean Alliance files are not part of the repository (see [NOTICE](NOTICE)).

## Deutsch

Das Format folgt [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).

### [0.1.0] - 2026-10-21

Erste Version der Integration.

#### Hinzugefügt

- **Gateways:** Eltako FGW14-USB, FAM14 und FAM-USB, PioTek MGW-ETH (per Zeroconf gefunden), Symcon
  EnOcean LAN Gateway und generische ESP2/ESP3-Gateways. Serielle
  Anschlüsse laufen über die Portauswahl von Home Assistant, TCP (ser2net, LAN-Gateways) wird
  ebenfalls unterstützt. Mehrere Gateways arbeiten nebeneinander, und der FAM14-Bus lässt sich
  über Busgruppen mit Ausfallsicherung nutzen.
- **Einrichtung nur über die Oberfläche:** ein Config-Eintrag pro Gateway, ein Subentry pro
  Gerät. Geräte werden über das Einlernen der ID aus einem Telegramm, nach Kategorie und Art
  oder über das EEP hinzugefügt. Gateways und Geräte lassen sich neu konfigurieren.
- **Geräte:** Schalt- und Dimmaktoren (auch Kanal 2 von Zweikanalaktoren), Rollläden mit
  Position, Lüftungsschlitzen und Lamellenneigung, Heizungsaktoren und Raumregler (mit
  Kühlbetrieb), Zähler (Strom, Gas, Wasser, bereit für das Energie-Dashboard), Fenstergriffe,
  Kontakte, Wandtaster, Wetter- und Luftqualitätssensoren, Permundo-PSC-Zwischenstecker und
  alle Standard-EEP-Profile als generische Geräte. Die Liste steht in
  [docs/devices.de.md](docs/devices.de.md).
- **Mehrere Sender pro Aktor** (Zentralbefehl, Wippe, Controller, Richtungswippe) mit einem
  Sender-ID-Pool: IDs kommen aus Base-ID + 0...127 und bleiben gesperrt, bis das Auslernen
  bestätigt ist.
- **Rollläden:** Positionsverfolgung mit Ankern an den Endlagen, Laufzeit-Assistent und
  Kalibrierung (auch zeitgesteuert über einen Blueprint).
- **Wippengesten** (einfach, doppelt, lang) mit Gerätetriggern sowie Blueprints für Lichter,
  Rollläden, Szenen und Kalibrierung.
- **Virtuelle Geräte:** Home Assistant sendet als Kontakt (auch mit Priorität für den
  Aussperrschutz), Temperatur-, Bewegungs- und Helligkeitssensor, Wetterstation,
  Szenentaster oder Wippe mit wählbaren Tasten.
- **Telegramm-Monitor im Panel:** Live-Liste mit Details, Filtern, Sortierung, Export,
  Signalqualität pro Sender, Gateway-Karten, Telegramm senden und unbekannte Sender als Gerät
  hinzufügen. Dazu:
  - eine Geräteansicht mit einer Zeile je Sender, sortierbar
  - die Sender-IDs jedes Geräts, gesperrte zuerst
  - eine Darstellung für das Handy
- **Übernahme aus der alten `eltako`-Integration** im Panel, in geführten Schritten: Vorschau,
  Auswahl, Übernahme von Bereich und Labels sowie eine Zuordnung alter zu neuen Entitäts-IDs mit
  ihrer Verwendung.
- **Gateway-Pflege:** Überwachung der letzten Meldung, Zustandsabgleich beim Start, Reparaturen
  bei instabiler oder stummer Verbindung, Diagnosesensoren und Diagnose-Download.
- **EnOcean-Proxy-Gateways** werden über die Supervisor-Erkennung eingerichtet.
- Übersetzungen auf Deutsch und Englisch, Markenbilder, deutsche und englische READMEs sowie
  ein Benutzerhandbuch.

#### Hinweise

- Die Protokollschicht (ESP2/ESP3, EEPs, FAM14-Bus) ist in diesem Repository ohne EnOcean-
  oder Eltako-Bibliotheken umgesetzt.
- Die offiziellen Dateien der EnOcean Alliance gehören nicht zum Repository (siehe
  [NOTICE](NOTICE)).
