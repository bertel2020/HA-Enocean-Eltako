# Changelog

All notable changes to this project are documented here, in English and German
(Deutsche Fassung weiter unten: [Deutsch](#deutsch)). The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## English

### [Unreleased]

#### Added

- **Panel, teach in:** a device with a sender ID of its own can be taught into its actuator
  from the Devices view (graduation cap), with the steps and a choice of sender ID; it sends what
  the device's teach-in button sends (websocket `enocean_eltako/teach_in`).
- **Panel, weak signal:** a hint above the Devices list counts the senders with a weak signal and
  shows only them on a click; status filter **Weak signal**.
- **Panel, send again:** the details of a sent telegram can send it once more.
- **Development:** a preview page of the panel with sample data (`scripts/panel-preview`) and a
  CI check that renders every view in a simulated browser.

#### Fixed

- **Panel in English:** milliseconds stand before AM/PM; the gateway card counts in lower case
  and in the singular for one.

### [0.1.5] - 2026-10-22

#### Added

- **Sender IDs:** the decimal value of an ID is an attribute (`decimal`) of the EnOcean ID and
  Sender ID diagnostics sensors and an own column in the panel's Sender IDs view. The view
  also shows a pool map (one square per ID, click to jump to its row), the next free ID, and
  device groups can be collapsed.
- **Swap a gateway:** reconfiguring a gateway now also asks for the model, so a defective
  gateway or a FAM-USB can be replaced by another model (for example a network gateway)
  without losing devices or sender IDs. The new gateway has to report the same base ID,
  otherwise the change is refused. Bus gateways (FGW14-USB, FAM14) swap among themselves.

#### Changed

- **Panel, Devices:** one line per device with EEP, area and entity count, also for set-up
  devices not heard yet; sortable by column, filterable by status (set up, unknown, silent),
  area, gateway and text, with pages of 25 to 200 rows. The CSV export saves the whole filtered
  list.
- **Device page:** the model of a device lists the EEP it speaks, for example "FSR61
  (M5-38-08)", so the integration page shows it in the device row. Existing devices update on
  the next start; nothing is migrated.
- **Sender IDs:** a radio gateway hands out base ID + 1 ... 127; the base ID itself is no
  longer used (127 IDs per gateway). A device that already sends from the base ID keeps
  working and is reported in the log: give it another sender ID.
- **Panel:** senders hidden from a gateway's discovery are tagged "hidden" and not offered as a
  new device; "x s ago" and last heard use the server's clock; times and numbers follow your
  profile (time format, browser or server time zone, number format); the view is remembered,
  and links like `/enocean-eltako?view=devices&sender=<ID>` open a filtered view; "Open
  device" leads to the device page; success messages disappear after 4 s; sending a rocker
  telegram can press and release; screen readers hear a lost connection and every message.
- **Panel look:** one **Filter** button opens the rarer filters, and the set ones show as chips
  with a cross above the list; the bar of the list stays on top while scrolling and shows the
  gateways' state once their cards are out of view; empty views explain what to do (send a
  telegram, reset the filters, open the integration); a compact pool map with a legend; one
  button style (filled, outlined, text); own-styled lists and checkboxes; quieter column heads.
  On phones the view tabs fit the width and the Takeover steps stand one below the other.

#### Fixed

- **Panel:** command and answer are paired by the device, not its name (two devices may share
  a name); the Takeover view goes once nothing is left, without a reload; CSV exports guard
  against spreadsheet formulas.

### [0.1.4] - 2026-10-22

#### Changed

- **Discovered devices:** senders a gateway hears but no device listens to are listed under
  **Add device → Discovered devices** of that gateway instead of as cards on the integration
  page and in the "Add hub" list. One notification per gateway announces new ones.
- **Teach-in hints:** the device form names the learn function and the rotary switch
  positions for switching actuators, dimmers and cover actuators (Eltako series 14).
- **Panel:** "Add device" on an unknown sender opens the integration page and highlights its
  gateway.
- **Panel:** the gateway cards stand only above Telegrams and Devices, a single gateway has no
  filter button; the views are tabs (arrow keys); the export button says it saves every
  telegram matching the filter; a theme or primary colour of your own becomes the accent
  colour; the takeover shows three steps (the never usable "Old IDs" step is gone), and
  "Old integration off" opens the old integration's page; durations know days; on phones
  export and clear sit in a ⋮ menu; Devices offers no send and clear, its export is a CSV of
  the sender list.

#### Added

- **Old integration on the same gateway:** a repair issue names a gateway that the old
  `eltako` integration also uses (same USB port, or same host and port).
- **Sharing device definitions:** the actions `enocean_eltako.export_custom_devices` and
  `enocean_eltako.import_custom_devices` hand definitions over as YAML text; imported ones are
  stored as files in `enocean_eltako/custom_devices/`, your own file is never changed.
- **Energy dashboard:** the action `enocean_eltako.add_energy_devices` adds the electricity
  meters of your devices (with their power sensor) to the Energy dashboard.
- **Hide sender:** senders that are not yours can be hidden (remembered per gateway) and shown
  again under **Configure → Hidden senders**. The list keeps the newest 100 senders.
- **Panel:** Devices lists your devices with no telegram in the monitor, with when they were
  last heard and whether they are silent; the Live badge shows Connecting and No connection;
  the send form gives an example of the right length per telegram type and checks the data
  before sending.

#### Fixed

- **Panel:** clearing the display twice no longer brings back the telegrams of the first clear
  after a reconnect; `/` and `P` no longer act in Sender IDs and Takeover; closing the send
  form hides its hint; Devices searches data and values like Telegrams; older browsers without
  `light-dark()` (iOS before 17.5) get the panel's colours; no status requests while the
  browser tab is hidden.

### [0.1.3] - 2026-10-22

#### Added

- **Device Proxy app:** its EnOcean gateways are discovered like those of the EnOcean Proxy app,
  titled "(Device Proxy)", with replay and the status in the panel. The update issue for old
  EnOcean Proxy versions does not apply to it (it names the version of the contract instead).
- **Moving from the EnOcean Proxy to the Device Proxy:** a gateway set up through one proxy app
  and announced by another is found by its base ID; its entry only gets the new address and
  status port, devices and entities stay

#### Fixed

- **Panel on phones:** the view tabs in the header stay on one line and scroll sideways
  instead of wrapping into a second line

### [0.1.2] - 2026-10-21

#### Changed

- **Panel:** new look like the Device Proxy app: white header with the views as tabs, rounded
  cards and buttons, its own light and dark colours that follow Home Assistant's theme
- **Documentation:** the teach-in guide lists which virtual sensor each actuator accepts

### [0.1.1] - 2026-10-21

#### Changed

- **Panel:**
  - Devices: values in one column, buttons for a sender's telegrams and for adding an unknown
    sender, sorting by name, last heard, weakest signal or most telegrams, more about unknown
    senders (telegram type, teach-in or possible profiles)
  - Sender IDs: grouped by device, blocked IDs first with their note, readable profile names
  - Takeover: after taking devices over the view moves on to checking the old IDs that are still
    in use, the mapping is shorter per device
  - the heading names the view, layouts for phones

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
  signal quality per sender, gateway cards, sender ID table, sending a telegram and adding
  unknown senders as devices.
- **Takeover from the old `eltako` integration** in the panel: preview, selection, area and
  label carry-over and a mapping of old to new entity IDs with their usage.
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

### [Unreleased]

#### Hinzugefügt

- **Panel, Einlernen:** ein Gerät mit eigener Sender-ID lässt sich in der Ansicht Geräte
  (Doktorhut) in seinen Aktor einlernen, mit Anleitung und Wahl der Sender-ID; gesendet wird
  dasselbe wie mit der Einlern-Schaltfläche des Geräts (Websocket `enocean_eltako/teach_in`).
- **Panel, schwaches Signal:** ein Hinweis über der Geräteliste zählt die Sender mit schwachem
  Signal und zeigt per Klick nur sie; Status-Filter **Schwaches Signal**.
- **Panel, nochmal senden:** die Details eines gesendeten Telegramms senden es erneut.
- **Entwicklung:** eine Vorschauseite des Panels mit Beispieldaten (`scripts/panel-preview`) und
  eine CI-Prüfung, die jede Ansicht in einem simulierten Browser zeichnet.

#### Behoben

- **Panel auf Englisch:** Millisekunden stehen vor AM/PM; die Zahlen der Gateway-Karte klein
  geschrieben und bei eins im Singular.

### [0.1.5] - 2026-10-22

#### Hinzugefügt

- **Sender-IDs:** Der Dezimalwert einer ID ist ein Attribut (`decimal`) der Diagnose-Sensoren
  EnOcean-ID und Sender-ID und eine eigene Spalte in der Ansicht Sender-IDs des Panels. Die
  Ansicht zeigt außerdem eine Pool-Karte (ein Feld pro ID, Klick springt zur Zeile) und die
  nächste freie ID; Gerätegruppen lassen sich einklappen.
- **Gateway tauschen:** Beim Neukonfigurieren eines Gateways wird jetzt auch das Modell
  abgefragt. So lässt sich ein defektes Gateway oder ein FAM-USB durch ein anderes Modell
  (z. B. ein Netzwerk-Gateway) ersetzen, ohne Geräte und Sender-IDs zu verlieren. Das neue
  Gateway muss dieselbe Base-ID melden, sonst wird der Wechsel abgelehnt. Bus-Gateways
  (FGW14-USB, FAM14) tauschen nur untereinander.

#### Geändert

- **Panel, Geräte:** Eine Zeile je Gerät mit EEP, Bereich und Entitätenzahl, auch für
  eingerichtete, noch nicht gehörte Geräte; nach Spalten sortierbar, filterbar nach Status
  (eingerichtet, unbekannt, still), Bereich, Gateway und Text, mit Seiten zu 25 bis 200 Zeilen.
  Der CSV-Export speichert die ganze gefilterte Liste.
- **Geräteseite:** Das Modell eines Geräts nennt das EEP, mit dem es funkt, zum Beispiel
  „FSR61 (M5-38-08)“, sodass die Integrationsseite es in der Geräte-Zeile zeigt. Bestehende
  Geräte ziehen beim nächsten Start nach; es wird nichts migriert.
- **Sender-IDs:** Ein Funk-Gateway vergibt Base-ID + 1 ... 127; die Base-ID selbst wird nicht
  mehr verwendet (127 IDs pro Gateway). Ein Gerät, das schon von der Base-ID sendet, läuft
  weiter und wird im Log gemeldet: ihm eine andere Sender-ID geben.
- **Panel:** In der Discovery eines Gateways ausgeblendete Sender sind als „ausgeblendet“
  markiert und werden nicht als neues Gerät angeboten; „vor x s“ und der letzte Empfang rechnen
  mit der Serveruhr; Zeiten und Zahlen folgen deinem Profil (Zeitformat, Zeitzone von Browser
  oder Server, Zahlenformat); die Ansicht wird gemerkt, und Links wie
  `/enocean-eltako?view=devices&sender=<ID>` öffnen eine gefilterte Ansicht; „Gerät öffnen“
  führt zur Geräteseite; Erfolgsmeldungen verschwinden nach 4 s; ein Taster-Telegramm lässt
  sich drücken und loslassen; Screenreader hören einen Verbindungsverlust und jede Meldung.
- **Panel-Optik:** ein Knopf **Filter** öffnet die selteneren Filter, gesetzte Filter stehen als
  Chips mit Kreuz über der Liste; die Leiste der Liste bleibt beim Scrollen oben und zeigt den
  Zustand der Gateways, sobald deren Karten aus dem Bild sind; leere Ansichten sagen, was zu tun
  ist (Telegramm senden, Filter zurücksetzen, Integration öffnen); eine kompakte Pool-Karte mit
  Legende; ein Knopfstil (gefüllt, umrandet, Text); eigene Auswahllisten und Checkboxen;
  ruhigere Spaltenköpfe. Auf dem Handy passen die Reiter in die Breite, und die Schritte der
  Übernahme stehen untereinander.

#### Behoben

- **Panel:** Befehl und Antwort werden über das Gerät gepaart, nicht über seinen Namen (zwei
  Geräte können gleich heißen); die Ansicht Übernahme verschwindet ohne Neuladen, sobald nichts
  mehr übrig ist; CSV-Exporte sind gegen Tabellenformeln abgesichert.

### [0.1.4] - 2026-10-22

#### Geändert

- **Entdeckte Geräte:** Sender, die ein Gateway hört und auf die kein Gerät hört, stehen beim
  Gateway unter **Gerät hinzufügen → Entdeckte Geräte** statt als Karten auf der Integrationsseite
  und in der Liste bei „Hub hinzufügen“. Eine Benachrichtigung pro Gateway meldet neue.
- **Anlernhinweise:** das Geräteformular nennt für Schaltaktoren, Dimmer und Rollladenaktoren
  (Eltako Baureihe 14) die Lernfunktion und die Drehschalterstellungen.
- **Panel:** „Gerät hinzufügen“ bei einem unbekannten Sender öffnet die Integrationsseite und
  hebt sein Gateway hervor.
- **Panel:** die Gateway-Karten stehen nur über Telegramme und Geräte, ein einzelnes Gateway hat
  keinen Filterknopf; die Ansichten sind Tabs (Pfeiltasten); der Export-Knopf sagt, dass er alle
  Telegramme zum Filter speichert; ein eigenes Design oder eine eigene Hauptfarbe wird zur
  Akzentfarbe; die Übernahme zeigt drei Schritte (der nie nutzbare Schritt „Alte IDs“ ist weg),
  und „Alte Integration aus“ öffnet die Seite der alten Integration; Zeitangaben kennen Tage;
  auf dem Handy stehen Exportieren und Leeren in einem ⋮-Menü; Geräte bietet kein Senden und
  Leeren, sein Export ist eine CSV der Senderliste.

#### Neu

- **Alte Integration am selben Gateway:** ein Reparaturhinweis nennt ein Gateway, das auch die
  alte Integration `eltako` nutzt (derselbe USB-Port oder derselbe Host mit Port).
- **Gerätedefinitionen weitergeben:** die Aktionen `enocean_eltako.export_custom_devices` und
  `enocean_eltako.import_custom_devices` übergeben Definitionen als YAML-Text; importierte liegen
  als Dateien in `enocean_eltako/custom_devices/`, deine eigene Datei bleibt unverändert.
- **Energie-Dashboard:** die Aktion `enocean_eltako.add_energy_devices` fügt die Stromzähler
  deiner Geräte (mit ihrem Leistungssensor) zum Energie-Dashboard hinzu.
- **Sender ausblenden:** fremde Sender lassen sich ausblenden (pro Gateway gemerkt) und unter
  **Konfigurieren → Ausgeblendete Sender** wieder anzeigen. Die Liste behält die neuesten 100
  Sender.
- **Panel:** Geräte listet deine Geräte ohne Telegramm im Monitor, mit dem letzten Empfang und
  ob sie still sind; das Live-Kennzeichen zeigt Verbinde… und Keine Verbindung; das
  Sendeformular zeigt ein Beispiel in der richtigen Länge je Telegrammtyp und prüft die Daten vor
  dem Senden.

#### Behoben

- **Panel:** zweimal Anzeige leeren holt nach einem Reconnect die Telegramme des ersten Leerens
  nicht mehr zurück; `/` und `P` wirken nicht mehr in Sender-IDs und Übernahme; Schließen des
  Sendeformulars blendet seinen Hinweis aus; Geräte durchsucht Daten und Werte wie Telegramme;
  ältere Browser ohne `light-dark()` (iOS vor 17.5) bekommen die Farben des Panels; keine
  Statusabfragen, solange der Browser-Tab verborgen ist.

### [0.1.3] - 2026-10-22

#### Neu

- **App Device Proxy:** ihre EnOcean-Gateways werden wie die der App EnOcean Proxy gefunden,
  mit dem Titel „(Device Proxy)“, Nachlieferung und Status im Panel. Der Hinweis auf eine zu
  alte EnOcean-Proxy-Version gilt für sie nicht (sie nennt stattdessen die Version der
  Schnittstelle).
- **Umstieg vom EnOcean Proxy zum Device Proxy:** Ein Gateway, das über die eine Proxy-App
  eingerichtet wurde und von der anderen gemeldet wird, wird über seine Base-ID erkannt; der
  Eintrag bekommt nur die neue Adresse und den Status-Port, Geräte und Entitäten bleiben

#### Behoben

- **Panel auf dem Handy:** Die Ansichts-Reiter in der Kopfzeile bleiben in einer Zeile und
  lassen sich seitlich wischen, statt in eine zweite Zeile umzubrechen

### [0.1.2] - 2026-10-21

#### Geändert

- **Panel:** neues Aussehen wie die Device-Proxy-App: weiße Kopfzeile mit den Ansichten als
  Reiter, runde Karten und Knöpfe, eigene helle und dunkle Farben, die dem Theme von Home
  Assistant folgen
- **Dokumentation:** die Anlernanleitung nennt, welchen virtuellen Sensor jeder Aktor annimmt

### [0.1.1] - 2026-10-21

#### Geändert

- **Panel:**
  - Geräte: Werte in einer Spalte, Knöpfe für die Telegramme eines Senders und zum Hinzufügen
    eines unbekannten Senders, Sortierung nach Name, letztem Empfang, schwächstem Signal oder
    meisten Telegrammen, mehr Angaben zu unbekannten Sendern (Telegrammtyp, Lerntelegramm oder
    mögliche Profile)
  - Sender-IDs: nach Gerät gruppiert, gesperrte IDs zuerst mit ihrem Hinweis, lesbare
    Profilnamen
  - Übernahme: nach dem Übernehmen geht es gleich zur Prüfung der alten IDs, die noch verwendet
    werden, die Zuordnung ist je Gerät kürzer
  - die Überschrift nennt die Ansicht, Darstellung für das Handy

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
  Signalqualität pro Sender, Gateway-Karten, Sender-ID-Tabelle, Telegramm senden und
  unbekannte Sender als Gerät hinzufügen.
- **Übernahme aus der alten `eltako`-Integration** im Panel: Vorschau, Auswahl, Übernahme von
  Bereich und Labels sowie eine Zuordnung alter zu neuen Entitäts-IDs mit ihrer Verwendung.
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
