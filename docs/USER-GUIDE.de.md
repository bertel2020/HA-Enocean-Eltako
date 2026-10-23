# EnOcean Eltako – Benutzerhandbuch

[English](USER-GUIDE.md)

## Inhalt

- [Was die Integration tut](#was-die-integration-tut)
- [Installation](#installation)
- [Gateway einrichten](#gateway-einrichten)
- [Geräte hinzufügen](#geräte-hinzufügen)
- [Hinweise zu Geräten](#hinweise-zu-geräten)
- [Das Panel EnOcean](#das-panel-enocean)
- [Sender-IDs](#sender-ids)
- [Gateway-Einstellungen und Reparaturen](#gateway-einstellungen-und-reparaturen)
- [Übernahme der alten Integration eltako](#übernahme-der-alten-integration-eltako)
- [Blueprints und Aktionen](#blueprints-und-aktionen)
- [App Device Proxy](#app-device-proxy)
- [Bekannte Einschränkungen](#bekannte-einschränkungen)
- [Fehlersuche](#fehlersuche)

## Was die Integration tut

EnOcean Eltako bindet Eltako-Geräte (Baureihe 14 am Bus und Funk) und andere EnOcean-Geräte in
Home Assistant ein. Alles wird über die Oberfläche eingerichtet, es gibt kein YAML für Geräte.

- **Ein Eintrag pro Gateway, ein Untereintrag pro Gerät.** Löscht du ein Gateway, gehen seine
  Geräte mit.
- **Mehrere Sender je Aktor sind der Normalfall.** Ein Aktorkanal kann von einem
  Controller-Sender, einem Richtungstaster-Sender und weiteren parallel gesteuert werden; jeder
  hat eine eigene Sender-ID aus dem Pool des Gateways.
- **Sicherheitsfunktionen bleiben im Aktor.** Wind-, Regen-, Frost- und Aussperrschutz laufen
  weiter im Aktor; Home Assistant ergänzt sie und ersetzt sie nie.
- **Keine fremden EnOcean-Bibliotheken.** Serielle Ports laufen über die Port-Auswahl und die
  Seriell-Bibliothek von Home Assistant (Integration `usb`), damit gehen auch serielle
  ESPHome-Proxys. Netzwerk-Gateways nutzen einfaches TCP.
- **Telegramme, EEPs und das FAM14-Busprotokoll sind hier selbst umgesetzt.** Standardprofile
  werden aus den offiziellen Definitionen der EnOcean Alliance erzeugt; Eltako-Varianten sind
  streng getrennt und als `EEP:Variante` geschrieben, etwa `A5-08-01:eltako` oder
  `F6-02-01:std`.

Die Liste der Gateways und Geräte: [devices.de.md](devices.de.md).

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

### Parallel zur alten Integration `eltako`

Die alte Integration `eltako` läuft parallel weiter; diese hier hat die eigene Domain
`enocean_eltako`. Einen seriellen Port kann nur ein Programm gleichzeitig öffnen: das Gateway
vorher aus der alten Integration entfernen oder über die [App Device Proxy](#app-device-proxy)
teilen. Ist die alte Integration auf demselben USB-Port oder
Host und Port wie ein Gateway hier eingerichtet, nennt ein Reparaturhinweis das Gateway; er
verschwindet, sobald der alte Eintrag aus ist.

## Gateway einrichten

Die Integration pro Gateway einmal hinzufügen: Gateway-Modell wählen, dann Anbindung und
Base-ID. Welche Gateways unterstützt sind und wie sie angebunden werden, steht in
[devices.de.md](devices.de.md).

- **USB-Gateways** werden mit der Port-Auswahl von Home Assistant gewählt. Der Port wird am
  Eintrag gespeichert, damit Home Assistant ihn der Integration zuordnet.
- **Netzwerk-Gateways** (ser2net, PioTek MGW-ETH, Symcon LAN, App Device Proxy) werden mit
  Host und Port angelegt. Ein MGW-ETH und die Gateways des Device Proxy werden automatisch
  gefunden und erscheinen als entdeckt; ein MGW-ETH mit neuer IP-Adresse wird selbst angepasst.
- **FGW14-USB und FAM14 am selben Bus** bilden eine Bus-Gruppe mit Failover. Der FAM14 kann
  getrennt bleiben, bis er gebraucht wird.
- **Gateway tauschen:** Menü des Gateways → **Neu konfigurieren** fragt Modell und
  Verbindung ab. Ein defektes Gateway oder ein FAM-USB lässt sich durch ein anderes Modell
  ersetzen, z. B. ein Netzwerk-Gateway; Geräte, Sender-IDs und das Einlernen der Aktoren
  bleiben. Das gelingt nur, wenn das neue Gateway dieselbe Base-ID meldet; bei einer anderen
  wird der Wechsel abgelehnt (die Aktoren kennen nur die alten Sender-IDs). Bus-Gateways
  (FGW14-USB, FAM14) tauschen nur untereinander.
- **Zwei Gateways mit derselben Base-ID** (z. B. zwei Funkgateways einer Anlage): Das zweite
  wird nach einer Rückfrage als `<Basis-ID>#2` angelegt. Sender-IDs werden über beide hinweg nie
  doppelt vergeben. Ein gefundenes Gateway mit bekannter Base-ID gilt nur dann als umgezogen,
  wenn das bekannte nicht verbunden ist; sonst wird es als weiteres Gateway angeboten.

## Geräte hinzufügen

Ein Gerät kommt unter dem Gateway mit **Gerät hinzufügen** dazu, auf einem von sechs Wegen:

- **Gerät anlernen** (empfohlen): eine Taste am Gerät drücken oder den Aktor vor Ort
  schalten; die Geräteart wird aus dem Telegramm vorgeschlagen.
- **Eltako-Gerät** oder **EnOcean-Gerät anderer Hersteller**: Kategorie und Geräteart aus
  dem Katalog wählen.
- **Virtueller Sensor**: Home Assistant sendet selbst, siehe unten.
- **Per EEP** (Experte): Jedes Standardprofil der EnOcean Alliance wird zu einem Gerät mit
  einem Sensor je Wert; ein Code wie `A5-04-02` findet es direkt.
- **Eigene Definition**: Sensoren, die du selbst beschreibst, siehe unten.

Noch einfacher: Jeder Sender, den das Gateway hört und der noch nicht eingerichtet ist,
steht beim Gateway unter **Gerät hinzufügen → Entdeckte Geräte** (eine Benachrichtigung
meldet neue). Die Auswahl schlägt die Geräteart vor und trägt die ID ein. Fremde Sender (z. B.
vom Nachbarn) lassen sich dort mit **Diesen Sender ausblenden** verstecken; **Konfigurieren →
Ausgeblendete Sender** am Gateway zeigt sie wieder an. Die Liste behält die neuesten 100
Sender und beginnt nach einem Neustart leer; ausgeblendete Sender werden gemerkt. In den
Einstellungen des Gateways lässt sich die Discovery abschalten.

Eltako-Aktoren der Baureihe 14 lernen eine Sender-ID über eine Einlernfunktion am Aktor; welche
Funktion zu welchem Einlern-Button gehört, steht in [teach_in.de.md](teach_in.de.md).

### Schaltaktoren ohne Rückmeldung

Für ältere oder reine 230-V-Aktoren: unter **Wandtaster** die ID eines im Aktor eingelernten
Tasters eintragen und die Tasten für Ein und Aus wählen (dieselbe Taste für beides schaltet
um). Seine Tastendrücke setzen dann den Zustand in Home Assistant, als angenommen markiert, bis
der Aktor sich selbst meldet.

### Virtuelle Sensoren

Home Assistant sendet selbst als Fensterkontakt (D5-00-01), Bewegungsmelder (A5-07-01),
Temperaturfühler (A5-02-05), Helligkeitssensor (FAH60-Format), Wetterstation (FWS61-Format:
Temperatur, Wind, Regen, Helligkeit aus beliebigen Entitäten), Taster (F6-02-01) oder
Szenentaster (Szenen 1–4, z. B. FSB14 Einlernfunktion 180/200), jeweils mit eigener Sender-ID.

- Ein HA-Luxsensor steuert so die Beschattungsautomatik eines FSB14, ein Wetterdienst dessen
  Wind- und Regenalarm. Ein HA-Fensterkontakt senkt den Heizungsaktor ab, eine HA-Temperatur
  dient als Raumfühler.
- Gesendet wird bei jeder Änderung der gewählten Entität und alle 15 min (einstellbar). Ist die
  Entität nicht verfügbar, kann ein Kontakt den sicheren Wert „offen“ senden; Wetterwerte senden
  nichts, damit kein falscher Alarm ausgelöst wird.
- Mit **Mit Priorität senden** überholt ein Kontakt alle wartenden Befehle, für den
  Aussperrschutz eines FSB14.
- Eingelernt wird über den Button auf der Geräteseite, dort steht auch der zuletzt gesendete
  Wert.

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

**Definitionen weitergeben:** Die Aktion `enocean_eltako.export_custom_devices` gibt deine
Definitionen (alle oder die `ids`, die du nennst) als YAML-Text zurück. Jemand anderes fügt ihn
in `enocean_eltako.import_custom_devices` ein (Entwicklerwerkzeuge → Aktionen); sie prüft ihn und
legt jede gültige Definition als eigene Datei in `/config/enocean_eltako/custom_devices/` ab.
Die Definitionen stehen sofort unter **Gerät hinzufügen → Eigene Definition**. Deine eigene
`custom_devices.yaml` wird nie geändert; eine Definition mit der ID einer dort vorhandenen wird
übersprungen, importierte werden nur mit `overwrite: true` ersetzt.

## Hinweise zu Geräten

- **Rollläden** (FSB14/61/71) nehmen einen Controller-Sender und einen Richtungstaster-Sender
  parallel. Die Position wird aus Laufzeiten berechnet und an den Endlagen, bei Befehlen auf
  0/100 % und nach einer vollen Fahrt verankert; der Aktor meldet nie, wo er angehalten hat.
  Lüftungsschlitze und Lamellenstellung werden unterstützt. Der Laufzeit-Assistent in den
  Geräteeinstellungen misst alle Zeiten per Klick.
- **Taster-Sender** drücken die gewählten Tasten (linke oder rechte Wippe, oben und unten
  vertauscht), passend dazu, wie die ID im Aktor eingelernt ist.
- **Zweikanal-Aktoren** mit einer ID (z. B. FSR71NP-2x): jeder Kanal ist ein eigenes Gerät;
  Kanal 2 meldet 0x30/0x10.
- **Heizungsaktoren**, die Home Assistant regelt, bekommen den Sollwert; eine
  Raumtemperatur-Entität lässt sich ergänzen.
- **Taster** melden je Taste kurzes, langes und doppeltes Drücken, die Blueprints und
  Gerätetrigger nutzen.
- **Wetterstationen** (FWS61, FWG14MS) melden Dämmerung, Temperatur, Wind, Sonne von drei Seiten und
  Regen. Dazu kommen „Sonnigste Seite“ (Süd, Ost, West oder keine Sonne unter 2 klx) und „Regen
  kürzlich“, das nach dem Regen noch einige Minuten an bleibt (Vorgabe 15, in den Einstellungen des
  Geräts), damit Rollläden und Markisen nicht auf eine nasse Fläche zurückfahren. Die Einheit des
  Winds (m/s, km/h, Beaufort) ist die Anzeigeeinheit der Entität in Home Assistant. Das Blueprint
  „Rollläden nach der Sonne beschatten“ nutzt die Sonnensensoren; der Schutz vor Wind, Regen und
  Frost bleibt im Aktor.
- **Permundo PSC132/PSC234** melden Energie und Leistung; siehe
  [Bekannte Einschränkungen](#bekannte-einschränkungen).

## Das Panel EnOcean

Das Seitenleisten-Panel **EnOcean** (nur für Administratoren) hat die Ansichten **Telegramme**,
**Geräte**, **Sender-IDs** und, bis die Übernahme abgeschlossen ist, **Übernahme** (Tabs; die
Pfeiltasten wechseln zwischen ihnen). Über Telegramme und Geräte steht eine kompakte
Zusammenfassung je Gateway: Verbindung, Telegramme pro Minute, letztes Telegramm, Geräte
und freie Sender-IDs. Bei mehreren Gateways filtert **Telegramme** auf das jeweilige Gateway. **Details** zeigt
Anschluss, Sendewarteschlange und unbestätigte Befehle. Bei einem Gateway über den Device Proxy
stehen dort auch Proxy-Version, verbundene Programme, Funkbelegung gegenüber dem 1-%-Limit
und eine Sendesperre während eines Mitschnitts. Ist die Zusammenfassung weggescrollt, zeigt die
Leiste der Liste (sie bleibt oben stehen) Zustand und Telegramme pro Minute je Gateway; ein Klick
darauf führt zurück zu den Karten.

### Telegrammliste

Jedes empfangene und gesendete Telegramm erscheint live in einer Tabelle, das neueste oben,
50 je Seite: Zeit, Richtung, Gerätename (oder „Unbekannter Sender“) mit Sender-ID,
Telegrammtyp, die entschlüsselten Werte mit Namen und Einheit wie bei den Entitäten („Leistung
15 W“), die Signalstärke und bei mehreren Gateways das Gateway.

- Ein Klick auf einen Spaltenkopf sortiert nach Zeit, Richtung, Sender, Typ, Signal oder
  Gateway (auf dem Handy: die Sortierliste). Seiten fassen 25, 50, 100 oder 200 Zeilen;
  Seitengröße und Sortierung merkt sich der Browser. Auf einer späteren Seite verschieben neue
  Telegramme die Zeilen nicht: Die Seite bleibt, ein Knopf springt zu den neuen.
- Gesendete Telegramme nennen Gerät und Sender-Profil; beim Lerntelegramm eines unbekannten
  Senders steht die EEP dabei.
- Ein Klick auf ein Telegramm zeigt Rohdaten, Status, Ziel und Signal in dBm oder filtert auf
  diesen Sender. **Gerät öffnen** führt zur Geräteseite in Home Assistant. Bei unbekannten
  Sendern öffnet dort **Gerät hinzufügen** die Integrationsseite, wo sie unter **Gerät
  hinzufügen → Entdeckte Geräte** warten; ein Sender, den du in der Discovery ausgeblendet hast,
  ist stattdessen als **ausgeblendet** markiert und fehlt bei „Nur unbekannte Sender“.
- Die Details zeigen außerdem die EEP (mit Variante) und bei Eltako-Geräten den Gerätetyp; was
  sich gegenüber dem vorigen Telegramm des Senders geändert hat (geänderte Bytes und Werte); einen
  Befehl und die Antwort des Geräts mit der Laufzeit; die Repeater-Stufen und wie viele Kopien
  des Telegramms das Gateway gehört hat. Bei einem unbekannten Sender, dessen Telegramm nur auf
  wenige Profile passt, steht in der Zeile „Könnte sein …“.
- **Als Capture-Zeile kopieren** legt das Telegramm im Format der Capture-Aktion in die
  Zwischenablage; der Export nutzt dasselbe Format, beide taugen als Testdaten.

### Suchen, Filter, Anhalten

Suchen nach Gerät, ID (mit oder ohne Bindestriche), Wertname oder Daten (Taste `/`) und nur
Empfangenes oder Gesendetes stehen direkt über der Liste. **Filter** öffnet die übrigen: ein
Gateway, ein Telegrammtyp (RPS, 1BS, 4BS, VLD …), nur unbekannte Sender oder mit Wiederholungen.
Gesetzte Filter stehen als Chips über der Liste, ihr Kreuz hebt sie einzeln auf, **Filter
zurücksetzen** alle. Das Panel
merkt sich die Filter im Browser. Anhalten (Taste `P`) sammelt weiter (bis zu 1.000) und zeigt,
wie viele Telegramme eingetroffen sind; Exportieren speichert alle Telegramme, die zum Filter
passen (alle Seiten), als JSON-Zeilen; auf dem Handy stehen Exportieren und **Anzeige leeren** im
Menü **⋮**. Das Kennzeichen neben dem Titel zeigt **Live**,
**Pausiert**, **Verbinde…** oder **Keine Verbindung** (dann fehlen Telegramme, bis Home Assistant
wieder erreichbar ist).
Solange in der Liste Text markiert ist, etwa um eine ID zu kopieren, warten neue Telegramme,
bis die Markierung endet.

Das Panel lädt die letzten 200 Telegramme der laufenden Sitzung und hält bis zu 1.000; nach
einem Verbindungsabbruch oder langer Zeit im Hintergrund-Tab ergänzt es nur, was fehlt. Anzeige
leeren setzt die Telegramme pro Minute nicht zurück, sie kommen vom Gateway. Das Panel folgt dem
Home-Assistant-Design, hell und dunkel; mit einem eigenen Design oder einer eigenen Hauptfarbe
wird diese Farbe zur Akzentfarbe des Panels. In einem verborgenen Browser-Tab pausiert es seine
Statusabfragen. Zeiten und Zahlen folgen deinem Profil (Zeitformat, Zeitzone von Browser oder
Server, Zahlenformat); „vor x s“ rechnet mit der Serveruhr, eine falsch gehende Browser-Uhr
stört also nicht. Erfolgsmeldungen verschwinden nach 4 s, Fehler bleiben bis zum Schließen;
Screenreader hören einen Verbindungsverlust und jede Meldung.

Das Panel öffnet mit der zuletzt genutzten Ansicht. Ein Link wie
`/enocean-eltako?view=devices&sender=05-10-A2-B3` (optional `&gateway=<Entry-ID>`) öffnet eine
Ansicht mit diesem Filter, etwa von einem Dashboard aus.

### Ansicht Geräte

Der Schalter **Geräte** zeigt statt der Telegrammliste eine Zeile je Gerät: Name und ID, das
EEP, den Bereich, die Zahl der Entitäten, die letzten Werte, wann es zuletzt gehört wurde,
Telegramme in der Liste und pro Minute sowie eine Kurve der Signalstärke seiner letzten
Telegramme, mit einem Hinweis bei schwachem Empfang (unter -85 dBm), dem ein Repeater oder ein
besserer Gateway-Standort hilft. Auch deine Geräte ohne Telegramm im Puffer des Monitors stehen
in der Liste (**nicht gehört**, und **still** bei einem Gerät, dessen üblicher Abstand dreimal
verstrichen ist). Bei einem unbekannten Sender kommen der Telegrammtyp dazu und was seine
Telegramme verraten: ein Lerntelegramm-Profil oder die Profile, die passen könnten.
**Telegramme** öffnet die Telegramme dieses Geräts, **Gerät hinzufügen** richtet einen
unbekannten Sender ein, und das Pfeil-Symbol öffnet die Geräteseite in Home Assistant.

**Einlernen** (Doktorhut-Symbol, bei Geräten mit eigener Sender-ID) lernt das Gerät in seinen
Aktor ein, ohne dafür die Geräteseite zu öffnen: Aktor in den Lernmodus bringen (bei Eltako
meist Drehschalter auf LRN), dann **Einlernen senden**. Hat das Gerät mehrere Sender-IDs (etwa
Zentralbefehl und Taster), wählt man eine aus. Gesendet wird dasselbe wie mit der
Einlern-Schaltfläche des Geräts; bei einem VLD-Aktor (UTE) erst senden und den Aktor dann
innerhalb von 60 s in den Lernmodus bringen.

Über der Liste zählt ein Hinweis die Sender mit schwachem Signal; ein Klick zeigt nur sie, das
schwächste zuerst (auch als Status **Schwaches Signal** unter **Filter**).

Ein Klick auf eine Spaltenüberschrift sortiert danach (nochmal: umgekehrt); auf dem Handy
übernimmt das eine Auswahl. Die Suche und unter **Filter** das Gateway, der Status (**Alle Geräte /
Eingerichtet / Unbekannt / Still / Schwaches Signal**) und der Bereich grenzen die Liste ein, und sie wird seitenweise mit 25 bis 200 Zeilen
gezeigt. Die Telegrammzahlen beziehen sich auf den Puffer des Monitors (die neuesten 1.000
Telegramme), nicht auf die Zeit seit dem Start. Exportieren speichert die ganze gefilterte
Liste als CSV; Senden und Leeren gehören zur Telegrammliste und fehlen hier.

**Mehrere Geräte auswählen:** Jedes eingerichtete Gerät hat vorn ein Kästchen, **Alle auswählen**
über der Liste wählt alle gefilterten. Sobald etwas gewählt ist, zeigt eine Leiste, was sich mit
allen auf einmal tun lässt: einen **Bereich** setzen, **Labels** hinzufügen oder entfernen (ein
Haken fügt das Label allen hinzu, ohne Haken wird es entfernt, ein Strich lässt es; neue Labels
legst du im Formular an), die Geräte **deaktivieren** oder wieder **aktivieren** und sie
**entfernen**. Bereich, Labels und Deaktivieren sind die von Home Assistant, sie gelten also auch
auf der Geräteseite und in Automationen. **Entfernen** fragt vorher nach und löscht die Geräte
mit ihren Entitäten; ihre Sender-IDs bleiben gesperrt, bis du unter **Sender-IDs** bestätigst, dass
die Aktoren sie vergessen haben. Die Labels eines Geräts stehen unter seinem Namen, und die Suche
findet sie.

### Telegramm senden

Die Schaltfläche **Telegramm senden** schickt ein rohes Telegramm (Typ, Daten und Status als
Hex) über die Sendewarteschlange, nur von einer Sender-ID, die eines deiner Geräte schon
nutzt, etwa um einen Aktor auszuprobieren. Das Datenfeld zeigt ein Beispiel in der richtigen
Länge für den Typ (RPS und 1BS ein Byte, 4BS vier, VLD eins bis vierzehn); Länge und Hex werden
vor dem Senden geprüft, Escape schließt das Formular. Bei einem Taster-Telegramm (RPS) sendet
**Drücken und loslassen** (standardmäßig an) gleich danach das Loslassen (Daten 00, Status 20),
wie ein Wandtaster. Aktoren reagieren darauf wie auf jedes Telegramm; es erscheint in der Liste
als gesendet. In den Details eines gesendeten Telegramms schickt **Nochmal senden** es erneut
(einen Tastendruck mit Loslassen), ohne es neu einzutippen.

## Sender-IDs

Der Schalter **Sender-IDs** im Panel zeigt, wer welche Sender-ID nutzt: je Gateway (und je
Bus-Gruppe) die freien IDs des Pools und jedes Gerät mit seinen IDs, deren Profil und Status,
gesperrte IDs zuerst. Funkgateways vergeben Base-ID + 1…127. Die Pool-Karte zeigt jede ID als
kleines Feld (frei, zugewiesen, gesperrt, anderweitig belegt; die Legende darunter nennt die
Farben); der Tooltip nennt ID und Gerät, ein Klick springt zur Zeile.

Nach dem Löschen eines Geräts bleibt seine ID **gesperrt**, bis sie aus allen Aktoren abgelernt
ist. **Freigeben** gibt sie nach einer Rückfrage frei, sobald der Aktor sie verlernt hat
(Teach-out).

## Gateway-Einstellungen und Reparaturen

**Konfigurieren** an einem Gateway öffnet **Einstellungen**: Pause zwischen Telegrammen,
Discovery, Bus-Verbindung, ESP3-Repeater und Gateway-Präfix in Entitäts-IDs.

Ohne Präfix bildet Home Assistant Entitäts-IDs aus Geräte- und Entitätsname (`light.kuche`,
`sensor.kuche_signalstarke`). **Gateway-Präfix in Entitäts-IDs** stellt `eno_gw` und die
**Gateway-Nummer** davor (`light.eno_gw1_kuche`); so lassen sich die Entitäten mehrerer
Gateways unterscheiden. Jedes Gateway mit Präfix braucht eine eigene Nummer; das Gateway-Gerät
zeigt seinen Präfix im Diagnose-Sensor **Entitäts-ID-Präfix**. Die Einstellung
gilt für Entitäten, die ab dann dazukommen. **Bestehende Entitäten jetzt umbenennen** benennt
die Entitäten des Gateways sofort um, in beide Richtungen; Automationen, Skripte und Dashboards
werden nicht angepasst, danach also prüfen.

Reparaturen weisen darauf hin, wo etwas zu tun ist:

- ein Gateway bleibt getrennt oder ein Gerät meldet sich nicht mehr
- eine Verbindung bricht immer wieder ab (3-mal in 10 Minuten), meist weil eine andere
  Integration denselben Port öffnet; geladene Integrationen am selben Port werden genannt
- ein Gateway meldet eine andere Base-ID als eingerichtet (Gateway oder Funkmodul getauscht):
  die Aktoren kennen die alten Sender-IDs, Befehle kämen nicht an
- Bus-Aktoren bestätigen Befehle im Mittel erst nach mehr als 3 s: der FAM14 gibt
  Bestätigungen nur in Betriebsart 5 mit einer per PCT14 erstellten Geräteliste sofort weiter

## Übernahme der alten Integration eltako

Die Ansicht **Übernahme** des Panels liest die Geräte der alten Integration `eltako` aus der
`configuration.yaml` (das Gateway mit derselben Base-ID) und richtet die gewählten mit ihren
IDs, Namen und Sender-IDs ein; die Aktoren brauchen kein neues Einlernen. Vier Schritte oben
zeigen, wo du stehst; die Ansicht öffnet beim ersten Schritt, in dem noch etwas offen ist.

1. **Auswählen** listet die noch nicht eingerichteten Geräte nach Bereich, jedes mit alter
   Plattform und EEP und der Zahl seiner Fundstellen. Zähler darüber zeigen, wie viele in der
   `configuration.yaml` stehen, wie viele schon eingerichtet sind (ein Klick führt zu ihnen
   unter Umstellen) und wie viele nicht übernehmbar sind (am Ende eingeklappt, mit Grund).
2. **Mitnehmen** zeigt als Kacheln, was aus der alten Integration mitkommt: **Bereich**,
   **Labels**, **Sprachsteuerung**, **Eigene Namen** (in Home Assistant vergebene Namen),
   **Symbole** und **Ausgeblendet / deaktiviert**, jeweils mit den Werten und bei wie vielen der
   gewählten Geräte es gesetzt ist. Anfangs ist nichts gewählt; das Panel merkt sich deine Wahl
   in diesem Browser; am neuen Gerät schon gesetzte Werte werden nie überschrieben. Darunter die
   Vorschau: jede alte Entity-ID neben der, die die neue Entität voraussichtlich bekommt (Home
   Assistant vergibt die ID erst beim Anlegen; für die Hauptentität und den ID-Sensor wird sie
   vorhergesagt, eine belegte ID bekommt „_2“). Vor **n Geräte jetzt übernehmen** wird nichts
   geschrieben.
3. **Umstellen** zeigt, wo die alten Entity-IDs noch verwendet werden, in drei Ansichten:
   **Nach Fundstelle** (Standard) listet jede Automation, jedes Skript, jede Szene und jedes
   Dashboard mit alten und neuen IDs und **Im Editor öffnen**, so stellst du sie in einem Zug
   um; **Nach Gerät** listet jedes hier eingerichtete Gerät, das die alte Integration kannte,
   ob übernommen oder von Hand angelegt, mit dem, was ihm noch fehlt, und aufgeklappt, wie es
   in der alten Integration aussah (Plattform, EEP, Namen, Bereich, Labels, Sender-IDs, wann es
   übernommen wurde und was mitkam); **Bericht** ist die Zuordnung als Tabelle, mit Kopieren
   und CSV. **Neu prüfen** nach dem Bearbeiten; **Nachträglich übernehmen…** ergänzt, was einem
   Gerät noch fehlt. Stellen in YAML, Templates und andere Werkzeuge wie Node-RED findet sie
   nicht: die mit der CSV selbst durchsuchen.
4. **Aufräumen** ist eine Checkliste, jeder Punkt aus dem aktuellen Stand erkannt: Geräte
   übernommen, Zuordnung gespeichert, alte IDs umgestellt, alte Integration gelöscht, `eltako:`
   aus der `configuration.yaml` entfernt. Sobald die alte Integration gelöscht ist, gibt
   **Alte IDs wiederherstellen** den neuen Entitäten stattdessen die alten Entity-IDs zurück
   (optional): Automationen und Dashboards laufen dann unverändert, die Historie geht unter der
   alten ID weiter; was in der Zwischenzeit unter der neuen ID aufgezeichnet wurde, bleibt dort,
   und Home Assistant protokolliert je Entität einmal, dass es das nicht verschieben konnte.
   **Übernahme abschließen** blendet den Tab aus.

Die Integration speichert die Zuordnung selbst, der Bericht bleibt deshalb nach dem Löschen der
alten Integration und nach dem Abschluss abrufbar: **Übernahme-Bericht** in der Ansicht Geräte
öffnet ihn. Ein noch nicht eingerichtetes Gerät der alten Konfiguration bringt den Tab zurück.

- `left`/`right` eines Taster-Senders wird zu den Tasten, die er drückt, `invert_signal` von
  Schaltern und Fenstergriffen zu **Umkehren**, Fahrzeiten von Rollläden werden übernommen.
  Rollläden bekommen wie bei der alten Integration ganze Sekunden; **Fahrzeiten in 100 ms** ist
  für Aktoren, die diese Form kennen.
- Buttons der alten Integration und Schalter, die sich als Taster melden, werden nicht
  übernommen (dafür einen virtuellen Taster anlegen). Heizungsaktoren bekommen wie bei der alten
  Integration nur den Sollwert und behalten ihren Thermostat.

Die alte Integration abschalten, sobald ihre Geräte hier laufen: beide dürfen nicht denselben
Port öffnen.

## Blueprints und Aktionen

### Blueprints

Taster melden je Taste kurzes, langes und doppeltes Drücken. Fertige Automationen:

- [Wippe schaltet und dimmt Licht](https://github.com/bertel2020/HA-Enocean-Eltako/blob/main/blueprints/automation/enocean_eltako/rocker_light.yaml) [![Importieren](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fbertel2020%2FHA-Enocean-Eltako%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fenocean_eltako%2Frocker_light.yaml)
- [Wippe steuert Rollladen](https://github.com/bertel2020/HA-Enocean-Eltako/blob/main/blueprints/automation/enocean_eltako/rocker_cover.yaml) [![Importieren](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fbertel2020%2FHA-Enocean-Eltako%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fenocean_eltako%2Frocker_cover.yaml)
- [Doppelklick ruft Szene](https://github.com/bertel2020/HA-Enocean-Eltako/blob/main/blueprints/automation/enocean_eltako/double_press_scene.yaml) [![Importieren](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fbertel2020%2FHA-Enocean-Eltako%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fenocean_eltako%2Fdouble_press_scene.yaml)
- [Rollläden zeitgesteuert kalibrieren](https://github.com/bertel2020/HA-Enocean-Eltako/blob/main/blueprints/automation/enocean_eltako/calibrate_covers.yaml) [![Importieren](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fbertel2020%2FHA-Enocean-Eltako%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fenocean_eltako%2Fcalibrate_covers.yaml)
- [Rollläden nach der Sonne beschatten](https://github.com/bertel2020/HA-Enocean-Eltako/blob/main/blueprints/automation/enocean_eltako/sun_shading.yaml) [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fbertel2020%2FHA-Enocean-Eltako%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fenocean_eltako%2Fsun_shading.yaml)

### Aktionen

- `enocean_eltako.capture`: schneidet die Telegramme aller Gateways oder eines Gateways für
  eine Anzahl Sekunden (Vorgabe 60) nach `enocean_eltako/capture-<Zeit>.jsonl` im
  Konfigurationsverzeichnis mit, für Fehlerberichte.
- `enocean_eltako.calibrate_cover`: fährt Eltako-Rollläden an die nähere Endlage und zurück,
  danach stimmt die Position wieder genau (I6). Bei unbekannter Position fährt ein Rollladen
  stattdessen in die offene Endlage, nie in die geschlossene. `only_if_inaccurate: true`
  überspringt Rollläden, deren Position schon genau bekannt ist.
- `enocean_eltako.add_energy_devices`: fügt die Stromzähler deiner Geräte als Einzelgeräte zum
  **Energie**-Dashboard hinzu, mit dem Leistungssensor des Geräts, wenn es genau einen hat.
  Zähler mit Tag- und Nachttarif nehmen ihren Gesamt-Sensor, wenn du ihn aktiviert hast,
  sonst beide Tarifzähler. Bereits vorhandene Zähler bleiben unverändert; Gas- und
  Wasserzähler werden nicht hinzugefügt. Öffne vor dem ersten Aufruf einmal Einstellungen →
  Dashboards → Energie.

## App Device Proxy

Die optionale App [Device Proxy](https://github.com/bertel2020/HA-Device-Proxy) (Home Assistant OS oder Supervised) hält die seriellen
Ports der Gateways und bietet jedes EnOcean-Gateway auf einem TCP-Port an. So können mehrere
Programme ein Gateway gleichzeitig nutzen, z. B. die alte Integration `eltako` während des
Umstiegs, eo_man oder PCT14.

- Die App meldet ihre Gateways an: Jedes erscheint hier als entdeckt (**Device Proxy**);
  Modell wählen, und das Gateway ist mit **Nachlieferung über den Device Proxy** eingerichtet.
- Nach einem Neustart von Home Assistant liefert die App die Telegramme nach, die inzwischen
  ankamen (nur Funktelegramme, standardmäßig höchstens 15 Minuten alt), mit ihrer
  Empfangszeit, damit Rollladenpositionen, Zählerstände und „Zuletzt gehört“ stimmen. Auf
  Wunsch hebt die App sie auch über ihren eigenen Neustart auf.
- Ihre Oberfläche zeigt jedes Telegramm live, testet das Gateway, sendet einzelne Telegramme,
  nimmt Mitschnitte auf (z. B. PCT14 mit FAM14) und zeigt die Funkbelegung gegenüber dem
  1-%-Limit.
- Legt die App ein Gateway auf einen anderen Port, findet die Integration es über die Base-ID
  wieder und passt den Eintrag selbst an.
- Meldet die App ein Gateway unter einer anderen Adresse an (App neu installiert, aus einem
  anderen Repository), findet die Integration es ebenfalls über die Base-ID: Nur die Adresse
  ändert sich, Geräte und Entitäten bleiben.
- Die Gateways sind nur aus Home Assistant und den anderen Apps erreichbar, solange in der App
  keine weiteren Adressen erlaubt sind.
- Die App kann einem Gateway einen Ersatz geben: ein zweites Gateway mit derselben Base-ID, das
  einspringt, wenn das erste ausfällt. Die Integration bleibt verbunden und merkt nichts; ihre
  Gateway-Karte zeigt solange gelb „Verbunden über Ersatz …“, und die Details sagen, ob der
  Ersatz bereit ist. Der Sensor Verbindung des Gateways trägt dasselbe als Attribute
  (`via_fallback`, `fallback`, `fallback_ready`), für Automationen.

## Bekannte Einschränkungen

- **Noch nicht mit echter Hardware getestet.** Nicht produktiv einsetzen.
- **Bus-Speicher:** Lesen und Schreiben des FAM14-Bus-Speichers (Import, Verknüpfungsansicht,
  Aktor-Konfiguration) ist noch nicht gebaut; dafür fehlen Mitschnitte zwischen PCT14 und FAM14.
- **Netzwerk-Gateways bedienen eine Verbindung:** Das PioTek MGW-ETH nimmt weitere
  Verbindungen an, antwortet ihnen aber nicht; eine hängende Verbindung bleibt, bis das Gateway
  neu gestartet wird. HA zeigt dann die Reparatur „… antwortet nicht“. Zum Teilen eines Gateways
  die App Device Proxy nutzen.
- **PSC-Energie und -Leistung:** Das Permundo PSC meldet sie als D2-01 (Wh, W) und als
  A5-12-01. Das volle D2-01-Telegramm braucht ein ESP3-Gateway (MGW-ETH, Symcon, USB300);
  ESP2-Gateways (FAM-USB) kürzen es, dann kommt die Energie aus dem A5-12-01-Zähler, der nur
  alle 10 Minuten gesendet wird.
- **Ein Programm pro Port:** Ein serielles Gateway kann nur von einer Integration genutzt
  werden. Vorher aus der alten Integration `eltako` entfernen oder über die App Device Proxy
  teilen.
- **VLD-Anlernen:** D2-01- und D2-05-Aktoren lernen per UTE, dafür ist ein ESP3-Gateway nötig
  (USB300, MGW-ETH, generisch ESP3); ESP2-Gateways wie der FAM-USB können nicht antworten.
- **Generische Profile:** Geräte per EEP entschlüsseln jedes Standardprofil, aber Profile
  außerhalb des Katalogs sind nicht mit Hardware geprüft; einige offizielle Testcontainer
  weichen ab.
- **Virtueller Helligkeitssensor und Wetterstation** senden die dokumentierten Formate von
  FAH60 und FWS61; noch nicht an einem Aktor geprüft.
- **Multisensoren D2-14-40/41** (FMS55SB, FMMS44SB) werden nach dem Profil entschlüsselt,
  sind aber noch nicht mit Hardware geprüft.
- **Rollladenpositionen** von Eltako-Aktoren werden aus Laufzeiten berechnet, der Aktor meldet
  nie, wo er angehalten hat.

## Fehlersuche

1. Panel **EnOcean** öffnen: Ist das Gateway verbunden, und kommen Telegramme an, wenn eine
   Taste gedrückt wird? Unbekannte Sender erscheinen dort; ihre Details bieten
   **Gerät hinzufügen**.
2. Unter **Einstellungen → Reparaturen** nachsehen: getrennte oder instabile Gateways, stumme
   Geräte, geänderte Base-ID, langsame Bus-Bestätigungen.
3. „Connection … lost: device disconnected or in use by another process“ immer wieder im
   Protokoll: Ein anderes Programm nutzt denselben seriellen Port, etwa eine zweite
   EnOcean-Integration oder eine App. Einen Port darf nur eines öffnen; zum Teilen eines
   Gateways die App Device Proxy nutzen und alles mit ihr verbinden.
4. Ein Netzwerk-Gateway ist verbunden, aber „Telegramme empfangen“ bleibt bei 0: den
   Diagnose-Sensor **Empfangene Bytes** des Gateways aktivieren. Er wächst mit jedem Byte,
   das ankommt, ob lesbar oder nicht. Wächst er nicht, wird auf dieser Verbindung nichts
   gesendet (viele Netzwerk-Gateways bedienen nur einen Client; andere Nutzer wie die alte
   Integration `eltako`, eine App oder eine Brücke beenden, oder die App Device Proxy
   verwenden). Wächst er, zeigen die Diagnosedaten „ignored_packets“ (Pakettypen, die kein
   Funktelegramm sind) und „bytes_unparsed“.
5. Für einen Fehlerbericht die Diagnosedaten des Gateway-Eintrags herunterladen und Telegramme
   mit dem Export im Panel oder der Aktion `enocean_eltako.capture` mitschneiden.
   Debug-Protokoll:
   ```yaml
   logger:
     logs:
       custom_components.enocean_eltako: debug
   ```
