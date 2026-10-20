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
> die Home Assistant regelt. Telegramme erscheinen live im Seitenleisten-Panel
> **EnOcean** und in den Diagnosedaten und lassen sich mit der Aktion
> `enocean_eltako.capture` mitschneiden. Noch nicht
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
- **Virtuelle Sensoren:** HA-Entitäten als EnOcean-Kontakt, -Bewegungsmelder, -Temperatur
  oder -Taster senden
- **Anlernen, Discovery, Telegramm-Monitor**, Import aus dem Bus-Speicher des
  FAM14 und ein Übernahme-Assistent für die alte Integration `eltako`
- **Keine fremden EnOcean-Bibliotheken:** keine zusätzlichen Pakete; serielle
  Ports laufen über die Port-Auswahl und die Seriell-Bibliothek von Home
  Assistant (usb-Integration), damit gehen auch serielle ESPHome-Proxys

## Unterstützte Geräte

Ein Gerät kommt unter dem Gateway mit **Gerät hinzufügen** dazu, auf einem von sechs Wegen:

- **Gerät anlernen** (empfohlen): eine Taste am Gerät drücken oder den Aktor vor Ort
  schalten; die Geräteart wird aus dem Telegramm vorgeschlagen.
- **Eltako-Gerät** oder **EnOcean-Gerät anderer Hersteller**: Kategorie und Geräteart aus
  dem Katalog wählen.
- **Virtueller Sensor**: Home Assistant sendet selbst als Fensterkontakt (D5-00-01),
  Bewegungsmelder (A5-07-01), Temperaturfühler (A5-02-05), Helligkeitssensor (FAH60-Format),
  Wetterstation (FWS61-Format: Temperatur, Wind, Regen, Helligkeit aus beliebigen Entitäten),
  Taster (F6-02-01) oder Szenentaster (Szenen 1–4, z. B. FSB14 Einlernfunktion 180/200) mit
  eigener Sender-ID. Ein HA-Luxsensor steuert so die Beschattungsautomatik eines FSB14, ein
  Wetterdienst dessen Wind- und Regenalarm. So senkt ein HA-Fensterkontakt den Heizungsaktor ab oder eine HA-Temperatur dient
  als Raumfühler. Gesendet wird bei jeder Änderung der gewählten Entität und alle 15 min
  (einstellbar); ist die Entität nicht verfügbar, kann ein Kontakt den sicheren Wert „offen“
  senden. Eingelernt wird über den Button auf der Geräteseite, dort steht auch der zuletzt
  gesendete Wert.
- **Per EEP** (Experte): Jedes der 318 Standardprofile der EnOcean Alliance wird zu einem Gerät
  mit einem Sensor je Wert; ein Code wie `A5-04-02` findet es direkt.
- **Eigene Definition**: Geräte, die du selbst in
  `/config/enocean_eltako/custom_devices.yaml` beschreibst (siehe unten).

Noch einfacher: Jeder Sender, den das Gateway hört und der noch nicht eingerichtet ist,
erscheint als **entdeckt**-Karte auf der Integrationsseite. **Hinzufügen** schlägt die
Geräteart vor und trägt die ID ein; **Ignorieren** blendet fremde Sender (z. B. vom
Nachbarn) dauerhaft aus. In den Optionen des Gateways lässt sich die Discovery abschalten.

**Schaltaktoren ohne Rückmeldung** (z. B. ältere oder reine 230-V-Aktoren): unter
**Wandtaster** die ID eines im Aktor eingelernten Tasters eintragen und die Tasten für Ein und
Aus wählen (dieselbe Taste für beides schaltet um). Seine Tastendrücke setzen dann den Zustand in
Home Assistant, als angenommen markiert, bis der Aktor sich selbst meldet.

### Eigene Gerätedefinitionen

Einen Sensor, den der Katalog nicht kennt, in `/config/enocean_eltako/custom_devices.yaml`
beschreiben: ein Standard-EEP und welche seiner Felder Sensoren und Binärsensoren werden, mit
Namen, Geräteklassen und Einheiten. Danach den Gateway-Eintrag neu laden; **Gerät hinzufügen →
Eigene Definition** listet die Definitionen.

```yaml
devices:
  - id: acme_climate
    name: Acme room sensor
    manufacturer: Acme
    eep: A5-04-01
    interval: 600          # optional: Sekunden zwischen Telegrammen (Stille-Erkennung)
    sensors:
      - field: TMP         # Feldkürzel des Profils
        device_class: temperature
      - field: HUM
        name: Humidity     # optional, sonst der Name aus dem EEP
        device_class: humidity
        unit: "%"          # optional, sonst die Einheit aus dem EEP
    binary_sensors:
      - field: TSN
        on: 1              # optional, sonst jeder Wert außer 0
```

Fehler erscheinen als Reparaturhinweis mit jeder einzelnen Stelle; die übrigen Definitionen
werden trotzdem geladen. Fällt eine Definition weg, laufen ihre Geräte als generische
EEP-Geräte weiter. Geräte per EEP oder Definition haben einen Diagnosesensor **Rohdaten**
(standardmäßig deaktiviert) mit den Bytes des letzten Telegramms, um die Felder zu prüfen.

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
| Taster und Kontakte | Digitaleingang (FSM60B) | Eltako | `A5-30-01:std` | - | binary_sensor |
| Taster und Kontakte | Vier Digitaleingänge und Temperatur (FHMB) | Eltako | `A5-30-03:std` | - | binary_sensor, sensor |
| Sensoren | Temperatur und Feuchte (FAFT60, FFT65B …) | Eltako | `A5-04-02:std` | - | sensor |
| Sensoren | Bewegungs- und Helligkeitssensor (FBH65 …) | Eltako | `A5-08-01:eltako` | - | sensor, binary_sensor |
| Sensoren | VOC-Sensor (FLT58) | Eltako | `A5-09-05:std` | - | sensor |
| Sensoren | TVOC-Sensor (FLGTF) | Eltako | `A5-09-0C:std` | - | sensor |
| Sensoren | Multisensor (VLD D2-14-40) (FMS55SB) | Eltako | `D2-14-40:std` | - | sensor |
| Sensoren | Multisensor mit Kontakt (VLD D2-14-41) (FMMS44SB) | Eltako | `D2-14-41:std` | - | sensor, binary_sensor |
| Sensoren | CO2-Sensor (FCO2TF65) | Eltako | `A5-09-04:std` | - | sensor |
| Sensoren | Wetterstation (FWS61, FWG14) | Eltako | `A5-13-01:eltako` | - | sensor, binary_sensor |
| Zähler | Energiezähler (FWZ12, FSDG14, DSZ14 …) | Eltako | `A5-12-01:eltako` | - | sensor |
| Zähler | Gaszähler (F3Z14D …) | Eltako | `A5-12-02:eltako` | - | sensor |
| Zähler | Wasserzähler (F3Z14D …) | Eltako | `A5-12-03:eltako` | - | sensor |
| Licht und Schalten | Permundo PSC132 / PSC234 Zwischenstecker | Permundo | `D2-01-09:std`<br>`A5-12-01:std`<br>`M5-38-08:eltako` | `controller: A5-38-08:std` | switch, light, sensor |
| Licht und Schalten | Schalt- oder Dimmaktor (VLD D2-01) | EnOcean | `D2-01-00:std` | `vld: D2-01-00:std` | light, switch |
| Rollläden und Jalousien | Rollladenaktor (VLD D2-05) | EnOcean | `D2-05-00:std` | `vld: D2-05-00:std` | cover |
| Taster und Kontakte | Wippentaster (NodOn, PEHA, Jung …) | EnOcean | `F6-02-01:std` | - | event |
| Taster und Kontakte | Fenstergriff (Hoppe SecuSignal …) | EnOcean | `F6-10-00:std` | - | sensor, binary_sensor |
| Taster und Kontakte | Tür-/Fensterkontakt (NodOn …) | EnOcean | `D5-00-01:std` | - | binary_sensor |
| Virtueller Sensor (Home Assistant sendet) | Virtueller Fensterkontakt | Home Assistant | - | `contact: D5-00-01:std` | button, sensor |
| Virtueller Sensor (Home Assistant sendet) | Virtueller Temperaturfühler | Home Assistant | - | `temperature: A5-02-05:std` | button, sensor |
| Virtueller Sensor (Home Assistant sendet) | Virtueller Bewegungsmelder | Home Assistant | - | `motion: A5-07-01:std` | button, sensor |
| Virtueller Sensor (Home Assistant sendet) | Virtueller Helligkeitssensor (FAH60) | Home Assistant | - | `brightness: A5-06-01:eltako` | button, sensor |
| Virtueller Sensor (Home Assistant sendet) | Virtuelle Wetterstation (FWS61) | Home Assistant | - | `weather: A5-13-01:eltako` | button, sensor |
| Virtueller Sensor (Home Assistant sendet) | Virtueller Szenentaster (Szenen 1–4) | Home Assistant | - | `rocker: F6-02-01:std` | button |
| Virtueller Sensor (Home Assistant sendet) | Virtueller Taster | Home Assistant | - | `rocker: F6-02-01:std` | button |
<!-- devices:end -->

## Panel EnOcean

Das Seitenleisten-Panel **EnOcean** (nur für Administratoren) zeigt oben eine kompakte
Zusammenfassung je Gateway: Verbindung, Telegramme pro Minute, letztes Telegramm, Geräte
und freie Sender-IDs. **Telegramme** filtert auf das jeweilige Gateway. **Details** zeigt
Anschluss, Sendewarteschlange und unbestätigte Befehle. Bei einem Gateway über EnOcean Proxy
stehen dort auch Proxy-Version, verbundene Programme, Funkbelegung gegenüber dem 1-%-Limit
und eine Sendesperre während eines Mitschnitts.

Darunter erscheint jedes empfangene und gesendete Telegramm live in einer Tabelle, das
neueste oben, 50 je Seite: Zeit, Richtung, Gerätename (oder „Unbekannter Sender“) mit
Sender-ID, Telegrammtyp, die entschlüsselten Werte mit Namen und Einheit wie bei den
Entitäten („Leistung 15 W“), die Signalstärke und bei mehreren Gateways das Gateway. Ein
Klick auf einen Spaltenkopf sortiert nach Zeit, Richtung, Sender, Typ, Signal oder Gateway
(auf dem Handy: die Sortierliste). Seiten fassen 25, 50, 100 oder 200 Zeilen; Seitengröße und
Sortierung merkt sich der Browser. Auf einer späteren Seite verschieben neue Telegramme die
Zeilen nicht: Die Seite bleibt, ein Knopf springt zu den neuen. Telegramme pro Minute zählen die
empfangenen Telegramme der letzten Minute.
Gesendete Telegramme nennen Gerät und Sender-Profil; beim Lerntelegramm eines unbekannten
Senders steht die EEP dabei. Ein Klick auf ein Telegramm zeigt Rohdaten, Status, Ziel und
Signal in dBm oder filtert auf diesen Sender. Bei unbekannten Sendern öffnet dort
**Gerät hinzufügen** die zugehörige Entdeckt-Karte.

Suchen nach Gerät, ID (mit oder ohne Bindestriche), Wertname oder Daten (Taste `/`), nur
Empfangenes oder Gesendetes, ein Gateway oder ein Telegrammtyp (RPS, 1BS, 4BS, VLD …), nur
unbekannte Sender oder mit Wiederholungen; **Filter zurücksetzen** hebt
alles auf. Anhalten sammelt weiter (bis zu 1.000) und zeigt, wie viele Telegramme
eingetroffen sind; Exportieren speichert die sichtbaren als JSON-Zeilen. Solange in der Liste
Text markiert ist, etwa um eine ID zu kopieren, warten neue Telegramme, bis die Markierung
endet. Das Panel lädt die letzten 200 Telegramme der laufenden Sitzung und hält bis zu
1.000; nach einem Verbindungsabbruch oder langer Zeit im Hintergrund-Tab ergänzt es nur, was
fehlt. Anzeige leeren setzt die Telegramme pro Minute nicht zurück, sie kommen vom Gateway.
Es folgt dem Home-Assistant-Design, hell und dunkel.

## Gateway-Optionen und Reparaturen

**Konfigurieren** an einem Gateway öffnet **Einstellungen** (Pause zwischen Telegrammen,
Discovery, Bus-Verbindung, ESP3-Repeater) und **Sender-IDs**: welche der 128 Sender-IDs zu
welchem Gerät und Profil gehört, wie viele frei sind und welche gesperrt sind. Die ID eines
entfernten Geräts bleibt gesperrt, bis sie aus allen Aktoren abgelernt ist; danach lässt sie
sich dort freigeben.

Reparaturen weisen darauf hin, wo etwas zu tun ist:

- ein Gateway bleibt getrennt oder ein Gerät meldet sich nicht mehr
- ein Gateway meldet eine andere Base-ID als eingerichtet (Gateway oder Funkmodul getauscht):
  die Aktoren kennen die alten Sender-IDs, Befehle kämen nicht an
- Bus-Aktoren bestätigen Befehle im Mittel erst nach mehr als 3 s: der FAM14 gibt
  Bestätigungen nur in Betriebsart 5 mit einer per PCT14 erstellten Geräteliste sofort weiter

## Blueprints

Taster melden je Taste kurzes, langes und doppeltes Drücken. Fertige Automationen:

- [Wippe schaltet und dimmt Licht](https://github.com/bertel2020/HA-Enocean-Eltako/blob/main/blueprints/automation/enocean_eltako/rocker_light.yaml) [![Importieren](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fbertel2020%2FHA-Enocean-Eltako%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fenocean_eltako%2Frocker_light.yaml)
- [Wippe steuert Rollladen](https://github.com/bertel2020/HA-Enocean-Eltako/blob/main/blueprints/automation/enocean_eltako/rocker_cover.yaml) [![Importieren](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fbertel2020%2FHA-Enocean-Eltako%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fenocean_eltako%2Frocker_cover.yaml)
- [Doppelklick ruft Szene](https://github.com/bertel2020/HA-Enocean-Eltako/blob/main/blueprints/automation/enocean_eltako/double_press_scene.yaml) [![Importieren](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fbertel2020%2FHA-Enocean-Eltako%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fenocean_eltako%2Fdouble_press_scene.yaml)
- [Rollläden zeitgesteuert kalibrieren](https://github.com/bertel2020/HA-Enocean-Eltako/blob/main/blueprints/automation/enocean_eltako/calibrate_covers.yaml) [![Importieren](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fbertel2020%2FHA-Enocean-Eltako%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fenocean_eltako%2Fcalibrate_covers.yaml)

## Aktionen

- `enocean_eltako.capture`: schneidet die Telegramme aller Gateways oder eines Gateways für
  eine Anzahl Sekunden (Vorgabe 60) nach `enocean_eltako/capture-<Zeit>.jsonl` im
  Konfigurationsverzeichnis mit, für Fehlerberichte.
- `enocean_eltako.calibrate_cover`: fährt Eltako-Rollläden an die nähere Endlage und zurück,
  danach stimmt die Position wieder genau (I6).

## App EnOcean Proxy

Die optionale App [EnOcean Proxy](https://github.com/bertel2020/HA-Enocean-Proxy) (Home
Assistant OS oder Supervised) hält die seriellen Ports der Gateways und bietet jedes Gateway
auf einem TCP-Port an. So können mehrere Programme ein Gateway gleichzeitig nutzen, z. B. die
alte Integration `eltako` während des Umstiegs. Die App meldet ihre Gateways an: Jedes erscheint
hier als entdeckt (**EnOcean Proxy**); Modell wählen, und das Gateway ist mit **Nachlieferung
über EnOcean Proxy** eingerichtet. Nach einem Neustart von Home Assistant liefert die App die
Telegramme nach, die inzwischen ankamen (nur Funktelegramme, höchstens 15 Minuten alt), mit ihrer
Empfangszeit, damit Rollladenpositionen, Zählerstände und „Zuletzt gehört“ stimmen. Ihre
Statusseite nimmt außerdem Mitschnitte auf (z. B. PCT14 mit FAM14) und zeigt die Funkbelegung
gegenüber dem 1-%-Limit. Ist die App älter als nötig (0.5.2), bittet ein Reparaturhinweis um
ein Update. Legt die App ein Gateway auf einen anderen Port, findet die Integration es über die
Basis-ID wieder und passt den Eintrag selbst an; ebenso bei einem MGW-ETH mit neuer IP-Adresse. Die App ist nur aus Home Assistant erreichbar,
solange ihre Ports nicht freigegeben sind.

## Bekannte Einschränkungen

- **Bus-Speicher:** Lesen und Schreiben des FAM14-Bus-Speichers (Import, Verknüpfungsansicht,
  Aktor-Konfiguration) ist noch nicht gebaut; dafür fehlen Mitschnitte zwischen PCT14 und FAM14.
- **Ein Programm pro Port:** Ein serielles Gateway kann nur von einer Integration genutzt
  werden. Vorher aus der alten Integration `eltako` entfernen oder über die App EnOcean Proxy
  teilen.
- **VLD-Anlernen:** D2-01- und D2-05-Aktoren lernen per UTE, dafür ist ein ESP3-Gateway nötig
  (USB300, MGW-ETH, generisch ESP3); ESP2-Gateways wie der FAM-USB können nicht antworten.
- **Generische Profile:** Geräte per EEP entschlüsseln jedes Standardprofil, aber Profile
  außerhalb des Katalogs sind nicht mit Hardware geprüft; einige offizielle Testcontainer
  weichen ab (siehe [docs/quality_scale.md](docs/quality_scale.md)).
- **Virtueller Helligkeitssensor und Wetterstation** senden die dokumentierten Formate von
  FAH60 und FWS61; noch nicht an einem Aktor geprüft. Ist eine gewählte Wetter-Entität nicht
  verfügbar, wird nichts gesendet, damit kein falscher Alarm ausgelöst wird.
- **Multisensoren D2-14-40/41** (FMS55SB, FMMS44SB) werden nach dem Profil entschlüsselt,
  sind aber noch nicht mit Hardware geprüft.
- **Rollladenpositionen** von Eltako-Aktoren werden aus Laufzeiten berechnet, der Aktor meldet
  nie, wo er angehalten hat.

## Fehlersuche

1. Panel **EnOcean** öffnen: Ist das Gateway verbunden, und kommen Telegramme an, wenn eine
   Taste gedrückt wird? Unbekannte Sender erscheinen dort mit **Anlegen**.
2. Unter **Einstellungen → Reparaturen** nachsehen: getrennte Gateways, stumme Geräte,
   geänderte Base-ID, langsame Bus-Bestätigungen.
3. Für einen Fehlerbericht die Diagnosedaten des Gateway-Eintrags herunterladen und Telegramme
   mit dem Export im Panel oder der Aktion `enocean_eltako.capture` mitschneiden.
   Debug-Protokoll:
   ```yaml
   logger:
     logs:
       custom_components.enocean_eltako: debug
   ```

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

### Entfernen

Unter **Einstellungen → Geräte & Dienste → EnOcean Eltako** jeden Gateway-Eintrag löschen
(seine Geräte gehen mit, Sender-IDs werden frei). Danach die Integration in HACS entfernen oder
`/config/custom_components/enocean_eltako` löschen und Home Assistant neu starten. Aktoren
behalten die gelernten Sender-IDs; am Aktor ablernen, wenn ein neuer Regler sie nutzen soll.

## Entwicklung

```bash
python -m pip install -r requirements_test.txt
ruff check custom_components tests scripts
mypy
python scripts/check_protocol_imports.py
python -m pytest
```

`python scripts/fetch_eep.py --generated` und danach
`python scripts/generate_eep.py` erzeugen die Standardprofile neu.
`python scripts/build_protocol_package.py` baut die Protokollschicht als eigenständiges Wheel
(`enocean-eltako-protocol`, ohne Home Assistant nutzbar) nach `dist/`; die CI baut es bei jedem
Push. Auf PyPI ist es noch nicht veröffentlicht.
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
