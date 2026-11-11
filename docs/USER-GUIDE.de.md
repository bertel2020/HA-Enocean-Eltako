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
- **FGW14-USB** (Eltako-Bus der Baureihe 14): siehe [Eltako-Bus mit dem FGW14-USB](#eltako-bus-mit-dem-fgw14-usb).
  Der FAM14 ist der Bus-Master und hat keine eigene Verbindung zum Rechner; er braucht nur
  dann einen Gateway-Eintrag, wenn er über eine eigene Schnittstelle erreichbar ist. Gateways
  am selben Bus bilden eine Bus-Gruppe mit Failover.
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

### Eltako-Bus mit dem FGW14-USB

Der FAM14 ist der Master des Busses; der FGW14-USB hängt wie jedes andere Gerät an diesem Bus
und verbindet ihn per USB (oder ser2net) mit Home Assistant. Du legst **ein** Gateway an, den
FGW14-USB. Aktoren am Bus (FSR14, FUD14, ...) sind Geräte dieses Gateways.

- **Sender-IDs** von Geräten an einem Bus-Gateway kommen aus dem Bus-Pool
  **00-00-B0-00 ... 00-00-B0-7F**, nicht aus Base-ID + 1...127. Der Pool gehört der Bus-Gruppe.
  Die ID trägst du mit dem PCT14 in den Aktor ein (oder lernst sie ein, siehe
  [teach_in.de.md](teach_in.de.md)).
- **Bestätigungen:** Ein Aktor antwortet nur dann mit einer Bestätigung, wenn er eine
  Geräteadresse hat und der obere Drehschalter des FAM14 beim Einlernen auf Position 2 steht.
  Sonst werden Befehle wiederholt und als unbestätigt gemeldet.
- **Noch nicht gebaut:** Lesen und Schreiben des Bus-Speichers des FAM14 (siehe Bekannte
  Einschränkungen).

Inbetriebnahme, in dieser Reihenfolge:

1. FGW14-USB an Bus und Rechner anschließen. Gateway anlegen; die gemeldete Base-ID wird
   angezeigt, prüfe, ob sie zu deiner Anlage passt.
2. In der Telegrammansicht **nur zuhören**: Telegramme von Bus-Geräten müssen erscheinen.
   Noch keine Geräte anlegen.
3. **Einen** unkritischen Aktor (eine Lampe) anlegen. Die vorgeschlagene Bus-ID nehmen, im
   Aktor eintragen und aus Home Assistant schalten. Prüfen, ob der Zustand folgt und die
   Telegrammliste den Befehl einmal zeigt, nicht wiederholt.
4. Wird der Befehl wiederholt: Drehschalter am FAM14 und Geräteadresse prüfen (siehe oben).
5. Die übrigen Aktoren einzeln anlegen und unter **Anlage → Sender-IDs** prüfen, dass jede ID
   ihr Gerät zeigt.
6. Die Diagnose des Gateways herunterladen (sie enthält Bus-Gruppe und Bus-Pool) und zu den
   Anlagenunterlagen legen.

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
steht beim Gateway unter **Gerät hinzufügen → Entdeckte Geräte** (eine Karte unter **Einstellungen →
Geräte & Dienste → Entdeckt** nennt die Anzahl und weist hierher). Die Auswahl schlägt die Geräteart vor und trägt die ID ein. Fremde Sender (z. B.
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

### Schaltaktor und Zähler an derselben Last

Ein FSR14 misst nichts; ein F3Z14D (oder ein anderer Zähler) misst den Stromkreis. Beide werden
als zwei Geräte angelegt und nach ihrer Funktion benannt, zum Beispiel „Bad Konvektor Schalter“
und „Bad Konvektor Zähler“, im selben Bereich. In den Geräteeinstellungen des Schalters können
**Leistungsmesser** und **Energiezähler** auf die Sensoren des Zählers zeigen; der Schalter
zeigt dann `measured_power` und `measured_energy` als Attribute. Das ist nur eine Anzeige: Die
Messwerte bleiben beim Zähler, den das Energie-Dashboard weiter nutzt. Die Auswahl lässt sich
jederzeit setzen oder entfernen, ohne Sender-IDs oder Verlauf anzufassen.

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
- **FUTH-Raumregler** (FUTH55ED, FUTH65D) senden von vier aufeinanderfolgenden IDs, und
  **Raumregler mit mehreren IDs** macht daraus ein Gerät: Trage die niedrigste ID ein, die auf
  `00` endet. Der Regler bei `+01` liefert die Klima-Entität (Sollwert, Temperatur) und die
  Nachtabsenkung, die Pumpe bei `+10` einen Binärsensor, die Betriebsart bei `+11` (Normal,
  Nachtabsenkung, Absenkung, Aus) einen Sensor und der Hygrostat bei `+12` die Luftfeuchte, die
  auch die Klima-Entität zeigt. Alles nur lesend: Der FUTH wird vor Ort bedient. Jede seiner IDs
  erscheint in der Geräteansicht, und die Dokumentation führt sie mit ihren Profilen auf.
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
**Geräte**, **Anlage** und, solange etwas zu übernehmen ist oder ein Bericht zu lesen, **Übernahme** (Tabs; die
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
- **Gerät melden** (unbekannte Sender) kopiert die letzten Telegramme des Senders (bis zu 60) als
  Capture-Zeilen und öffnet die Geräteanfrage auf GitHub, in die du sie einfügst. Sender-IDs,
  Gateway-Name und Zeiten werden ersetzt, bevor etwas kopiert wird; Telegrammdaten, Status und
  Signalstärke bleiben, weil die Decoder sie brauchen. Home Assistant sendet nichts, und im Link
  stehen keine Daten. **Aufnehmen und melden** (Play-Knopf) hört den Sender zuerst 60 Sekunden
  ab, damit die Telegramme dessen, was du mit dem Gerät machst, im Bericht stehen: Tasten
  drücken oder das Gerät auslösen, dann die Details des Senders wieder öffnen und die
  aufgenommenen Telegramme kopieren.

### Suchen, Filter, Anhalten

Suchen nach Gerät, ID (mit oder ohne Bindestriche), Wertname oder Daten (Taste `/`) und nur
Empfangenes oder Gesendetes stehen direkt über der Liste. **Nur unbekannte** liegt gleich daneben. **Filter** öffnet die übrigen: ein
Gateway, ein Telegrammtyp (RPS, 1BS, 4BS, VLD …) oder Wiederholungen.
Gesetzte Filter stehen als Chips über der Liste, ihr Kreuz hebt sie einzeln auf, **Filter
zurücksetzen** alle. Das Panel
merkt sich die Filter im Browser. Anhalten (Taste `P`) sammelt weiter (bis zu 1.000) und zeigt,
wie viele Telegramme eingetroffen sind; Exportieren speichert alle Telegramme, die zum Filter
passen (alle Seiten), als JSON-Zeilen; **Anzeige leeren** steht im Menü **⋮** (auf dem Handy auch Exportieren). Der Chip **Nur unbekannte Sender** zeigt, wie viele unbekannte Sender der Puffer enthält. Das Kennzeichen neben dem Titel zeigt **Live**,
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

Der Schalter **Geräte** zeigt statt der Telegrammliste eine Zeile je Gerät: Name mit ID und EEP,
die Art mit dem Bereich darunter, die letzten Werte und wann es zuletzt gehört wurde, mit
Signalstärke und einem Hinweis bei schwachem Empfang (unter -85 dBm), dem ein Repeater oder ein
besserer Gateway-Standort hilft. Der Pfeil öffnet die Details: Art, Labels, Entitäten,
Telegramme in der Liste und pro Minute sowie eine Kurve der Signalstärke der letzten Telegramme. Auch deine Geräte ohne Telegramm im Puffer des Monitors stehen
in der Liste (**nicht gehört**, und **still** bei einem Gerät, dessen üblicher Abstand dreimal
verstrichen ist). Bei einem unbekannten Sender kommen der Telegrammtyp dazu und was seine
Telegramme verraten: ein Lerntelegramm-Profil oder die Profile, die passen könnten.
Bei mehreren Gateways zeigen die Details eines Geräts **Gehört von**: jedes Gateway mit letztem
Signal und Telegrammzahl, das stärkste mit dem Hinweis **am besten**; ein Gerät, das kein Gateway
direkt hört (ab 3 Telegrammen, alle wiederholt), trägt den Hinweis **nur über Repeater**.
Bei einem Schaltaktor oder Dimmer mit bekanntem Zustand sendet **Sender testen** in den Details diesen
Zustand nacheinander über jeden seiner Sender (es ändert sich also nichts, mit Hintergrund-
Priorität) und markiert jeden Sender mit **Antwort** oder **keine Antwort**. Keine Antwort
beweist nicht, dass der Aktor den Sender nicht kennt, denn ein Aktor kann stumm bleiben; ein
umschaltender Wipptaster wird nicht getestet. Ein Dimmer bekommt seine aktuelle Helligkeit als Dimmbefehl über den Zentralbefehl; sein Wipptaster wird nicht getestet, denn ein Druck könnte die Helligkeit ändern. Rollläden werden gar nicht getestet: jeder Befehl bewegt sie oder unterbricht eine Fahrt. Der Test zählt nicht in der Befehlsstatistik.

**Ansicht Anlage:** Der Reiter **Anlage** bündelt Dokumentation und Verwaltung an einer Stelle,
in vier Reitern: **Geräte**, **Sender-IDs**, **Verbindungen** und **Protokoll**. Die Tabellen
sind dieselben Zeilen wie im Ausdruck.

**Geräte** hat oben einen Umschalter zwischen vier Ansichten. Jede Zeile nennt ihre **Art** als
Kennzeichen (Eltako-Bus, Funk Sensor, Funk Taster, Funk Aktor, Virtuell, Netzteil); ein Klick darauf
öffnet die Ansicht dieser Art, und ein Gerät mit Sender-IDs aus dem Pool trägt **Sender 1, 2**, das
in den Reiter Sender-IDs springt.

- **Alle Geräte** hat typisierte Felder, die du direkt bearbeitest: Ort (drei Felder: Schrank,
  Reihe, Platz), Stromkreis, Sicherung, Einbaudatum, Revision (der Datumscode, denn er bestimmt die
  Lernfunktion), Versorgung (Netz, Batterietyp) und eine Notiz. Die Spalten zeigst du über das
  Menü **Spalten** in Gruppen (Ort und Sicherung, Bus, Wartung); die Tabelle aller Arten zeigt nur Spalten, die jede Art hat, die übrigen (Bus-Adresse, Versorgung, Revision, Gehört zu) erscheinen, sobald du oben eine Art wählst. Die Art-Chips und die
  Filter **Fehlt: Ort** und **Fehlt: Sicherung** (mit Zähler) grenzen die Zeilen ein, **Gruppieren**
  ordnet sie nach Bereich oder Ort (der Schrank), und **Nächstes ohne Ort** setzt den Cursor ins
  erste Feld, das noch leer ist. Der Fortschritt zählt Geräte, Netzteile und von Hand notierte
  Einträge, aber keine virtuellen Geräte: für sie gibt es keinen Ort. Mit markierten Zeilen setzt
  du ein Feld für alle auf einmal, oder du **fügst aus einer Tabellenkalkulation ein**: eine
  Kopfzeile, eine Spalte Adresse und Spalten, die wie die Felder heißen; leere Zellen ändern
  nichts, und **Tabelle kopieren** liefert dasselbe Layout zum Bearbeiten und Zurückfügen.
- **Bus** zeigt den Eltako-Bus gruppiert nach **Netzteil**: Jedes Netzteil ist eine Kopfzeile mit
  Typ, Watt und den Bus-Adressen, die es versorgt (alles direkt dort bearbeitbar), mit
  Auslastungsbalken und einer Warnung bei Überlast; Adressen, die kein Netzteil versorgt, stehen in
  einer eigenen Gruppe. Eine Kachelleiste nennt doppelte Adressen, belegte und freie Adressen, die
  Gesamtleistung und den Zustand der Netzteile. Geräte der Eltako-Baureihe 14 (FSR14, FUD14,
  FSB14 …) zählen als Eltako-Bus, auch ohne Adresse: sie stehen in der Gruppe **Noch keine
  Bus-Adresse**, bis du die Adresse einträgst. Bus-Adresse, Rückmelde-ID und Leistung bearbeitest
  du in der Zeile (die Leistung ist die Aufnahme am Bus; ohne eigenen Wert gilt der der
  Eltako-Planungshilfe, mit **Tabelle** markiert).
- **Funk** listet die Funk-Geräte (Taster, Sensoren, Aktoren) und die von Hand notierten Einträge.
  Die Spalten (Menü **Spalten**): Ort, Sender-ID (bei mehreren IDs eines Geräts alle), Sendet,
  **Versorgung** (Batterietyp, Netz), Gehört zu, **Signal** und **Verbindung**. Das Signal ist ein
  Punkt mit der Zeit des letzten Telegramms: grün innerhalb eines Tages, gelb innerhalb einer
  Woche, danach rot; dazu die Stärke und „nur über Repeater“. Die Verbindung zeigt, was ein
  Taster oder Sensor steuert und was einen Aktor steuert, jeder Name ein Sprung zum Gerät.
  **Gerät dokumentieren** legt einen Eintrag von Hand an (Name, ID, Art, Funktion): ein direkt
  eingelernter Taster oder ein Gerät eines anderen Systems. Er trägt das Kennzeichen **nur
  dokumentiert**, steht auch in **Alle Geräte** und hat Ort und Versorgung wie ein Gerät; Home
  Assistant legt nichts an und lernt nichts ein.
- **Virtuell** zeigt, was Home Assistant sendet: Pool-Nummer, Sender-ID, die Entitäten, denen ein
  virtuelles Gerät folgt, und die Aktoren, in die es laut Notiz eingelernt ist. Bei einem Gateway
  mit anderer Base-ID muss jeder dieser Sender neu eingelernt werden.

**Sender-IDs** ist die Tabelle der Gateway-Sender: eine Zeile je Sender (nicht je Gerät; ein Gerät
kann mehrere halten), Nummer 0 bis 127, die Gateway-ID selbst als Nummer 0, freie Nummern
zusammengefasst, blockierte IDs zuerst, mit der Freigabe, dazu der Sender-ID-Pool darüber. Die Gerätenamen
springen zum Gerät. **Verbindungen** zeigt, wer in welchen Aktor eingelernt ist, als Karte je
Aktor, je Sender oder als Matrix. Jede Verbindung nennt das andere Ende, die Rolle (etwa linke
oder rechte Wippe) und woher sie kommt: **vergeben** (ein Sender, den Home Assistant für den
Aktor hält, mit dem Zeitpunkt seines Einlernens und dem Ergebnis des letzten Sendertests),
**angegeben** (der Wandschalter aus den Optionen des Geräts) oder **eingetragen** (von dir
notiert: ein direkt eingelernter Taster, ein Aktor eines anderen Systems; nur diese lassen sich
hier entfernen). Jede Verbindung hat ein Feld für ihre Lernposition. Ein Aktor ohne Verbindung
ist markiert; Filter und Kacheln zeigen die ohne Verbindung, die nicht getesteten und die ohne
Antwort. **Sender testen** startet den Sendertest von der Karte eines Aktors, **+ Verbindung**
und **+ Aktor** notieren eine Verbindung (ebenso ein **+** in der Matrix), und eine
Wandschalter-ID ohne Gerät bekommt **Als Gerät notieren**. Was ein Aktor wirklich gelernt hat,
steckt im Aktor und lässt sich nicht lesen, das sagt der Reiter auch; eine nie getestete
Verbindung heißt „nicht getestet“. **Protokoll** listet, was passiert ist: Geräte hinzugefügt
oder entfernt, Sender vergeben oder entfernt, Einlernen, Sendertests und Importe. Drucken, die Ausgaben als CSV und JSON und der Notizen-Import stehen im Menü **⋮** des Reiters.

**Ausgaben:** Die Knöpfe des Reiters Anlage (und das ⋮-Menü der Geräteansicht) liefern:

- **Drucken**: eine in sich geschlossene Seite mit Abschnitten, die du oben ein- oder ausschaltest
  (sie werden nicht mitgedruckt): **Übergabe** (jedes Gerät mit Adresse, EEP, Sendern und den
  typisierten Feldern), **Schaltschrank** (Geräte nach Ort, mit Stromkreis, Sicherung, Revision und
  Versorgung), **Verbindungen**, eine **Checkliste für ein neues Gateway**, **Sender-IDs** (Pool mit
  blockierten IDs, weitere Geräte, seit dem Neustart gehörte unbekannte Sender) und das
  **Protokoll**. Bei mehreren Gateways beginnt sie mit einer Übersicht. Am Ende steht ein Hinweis,
  was Home Assistant nicht wissen kann. Blockiert der Browser das Druckfenster, wird die Seite als
  Datei gespeichert, die du öffnest und druckst.
- **CSV** der Geräte (eine Zeile pro Sender), **Verbindungen als CSV** und **Sender-Tabellen-CSV**
  (die folgenden Tabellen untereinander).
- Vier weitere Druckabschnitte, in der Reihenfolge einer Installationsliste: **Gateway-Sender**
  (Sender-Nr. 0 bis 127 des Funk-Pools, also Basis-ID plus Nummer; freie Nummern sind zusammengefasst;
  mehrere Sender eines Geräts verweisen aufeinander, von Hand als eingelernt eingetragene Sender
  (etwa die GFVS-Software, deren IDs frei sind) stehen darunter mit den Nummern ihres Geräts;
  Bus-Adresse und Rückmelde-ID schreibst du je Gerät auf), **Taster** (jeder Wandtaster mit den
  Aktoren auf linker und rechter Wippe, aus der Wandschalter-Option der Aktoren), **Funk-Sender**
  (Geräte, die nur senden, und Einträge von Hand) und **Eltako-Bus** (jedes Gerät mit Bus-Adresse,
  Adresse 1 bis 126, eine je Kanal; freie Adressen sind zusammengefasst; eine doppelt vergebene
  Adresse wird gemeldet). Die Leistung ist die Aufnahme am Bus, nicht die geschaltete Last: was du
  eingetragen hast, sonst der Wert der Eltako-Planungshilfe (Ausgabe 07/2014, Tabelle des maximalen
  Leistungsbedarfs), mit `*` markiert. Ein Typ, den die Planungshilfe nicht kennt (neuere Geräte
  wie der F3Z14D), hat keinen Wert, und die Summe sagt, wie vielen er fehlt. Die Tabelle **Geräte** nennt
  eine falsche Bus-Adresse oder Wattzahl unter dem Feld, statt sie zu senden. In der Ansicht
  **Bus** änderst du die Felder eines Geräts direkt dort, wo sie stehen (Bus-Adresse,
  Rückmelde-ID, **Gehört zu**, Leistung; gespeichert beim Tippen). Die Kanäle eines
  Geräts zählen einmal, wenn sie denselben Namen unter **Gehört zu** haben; ohne ihn zählt die
  Summe jeden Kanal und weist darauf hin. Als Netzteil gelten die 12 W des FAM14. In der Ansicht **Bus**
  trägst du ein oder mehrere Netzteile ein (Typ, Watt); mit den Bus-Adressen, die ein
  Netzteil versorgt, zeigt der Ausdruck die Auslastung je Netzteil und nennt Adressen, die kein
  Netzteil versorgt, ohne sie nur die Gesamtsumme. Welche Adressen ein Netzteil versorgt, hängt
  davon ab, wie die Hutschiene gesteckt ist, das weißt nur du. Home Assistant kann den Bus
  noch nicht lesen, deshalb schreibst du Bus-Adresse, Rückmelde-ID und die Einträge von Hand
  selbst auf.
- **JSON** (Version 2: typisierte Felder, Verbindungen und das Protokoll; der Import liest weiter
  Version 1).

Die Checkliste ist für den Wechsel auf ein Funkgateway mit anderer Base-ID: seine Sender-IDs sind
neu und die Aktoren kennen nur die alten, also muss jeder vergebene Sender neu eingelernt werden.
Sie listet sie auf, jeden mit seiner Lernposition, falls du eine notiert hast, und verweist auf die
Tabelle der Lernfunktionen (`docs/teach_in.de.md`), denn die richtige Funktion hängt von Typ und
Revision des Aktors ab. Direkt eingelernte Taster und Wandschalter sind nicht betroffen.

**Signal und unbekannte Sender über Neustarts hinweg:** wie jedes Gateway ein Gerät hört
(Telegrammzahl, letztes Signal, ob je ein Telegramm ohne Repeater kam) und die unbekannten Sender,
die ein Gateway gehört hat (die neuesten 100), liegen im selben Speicher und werden höchstens
einmal pro Minute geschrieben. **Gehört von**, „nur über Repeater“ und die Liste der gehörten
Sender beginnen nach einem Neustart also nicht leer.

**Notizen und weitere Geräte:** In den Details jedes Geräts gibt es ein Feld **Notizen**, in den
Details jedes Gateways ein eigenes Notizfeld, und unter **Geräte → Funk** im Reiter
Anlage den Knopf **Gerät dokumentieren** für Einträge von Hand (Name, ID, Art, Funktion: direkt
eingelernte Taster, Geräte anderer Systeme; bei Geräten am Eltako-Bus auch Bus-Adresse,
Rückmelde-ID und Watt; Ort und Versorgung bearbeitest du in der Tabelle). Gespeichert beim Tippen, in einem
eigenen Speicher pro Gateway, Teil des Home-Assistant-Backups. Die Felder eines Geräts gehören zu
seiner Adresse und sind wieder da, wenn du das Gerät neu anlegst; die Gateway-Details bieten an,
die der gelöschten Geräte zu vergessen.

**Notizen aus JSON importieren** (Reiter Anlage) liest einen Export wieder ein, etwa für ein
neues Gateway: Gateways werden über die Base-ID zugeordnet, Geräte über die Adresse, und nur was
noch leer ist, wird gefüllt. Felder, weitere Geräte, eingetragene Verbindungen und Lernpositionen
kommen mit, die Geräte selbst nie. Hat ein Gateway eine andere Base-ID, bietet das Panel an, das
eine Gateway der Datei ohne Treffer in das eine hier eingerichtete Gateway ohne Treffer zu
importieren.
**Telegramme** öffnet die Telegramme dieses Geräts, das **+** eines unbekannten Senders fragt, ob du ihn
**Als Gerät anlegen** oder **Nur dokumentieren** willst (ein Eintrag mit dem Kennzeichen *nur
dokumentiert* unter **Geräte → Funk** mit ausgefüllter ID, für die Dokumentation; Home Assistant
legt nichts an), und das Pfeil-Symbol öffnet die Geräteseite in Home Assistant.
**Als Gerät anlegen** hält den Sender für das nächste **Gerät hinzufügen** seines Gateways bereit (zehn
Minuten, einmal): Der Dialog geht dann direkt zur Art, die wahrscheinlichste ist vorgewählt. **Nur dokumentieren** öffnet das Formular von **Gerät dokumentieren** mit eingetragener ID und geratener Art. Ein
Eintrag ohne Namen zeigt **Unbenannter Sender**, bis du **Namen geben** wählst; unter dem Namen
stehen die ID, der Typ (zum Beispiel PTM 215) und die Art, und das Menü (⋮) bietet **Als Gerät anlegen**
und **Eintrag entfernen**. Ort, Stromkreis, Sicherung, Einbaudatum, Versorgung und Funktion trägst du
ein wie bei jedem Gerät.

**Einlernen** (Doktorhut-Symbol, bei Geräten mit eigener Sender-ID) lernt das Gerät in seinen
Aktor ein, ohne dafür die Geräteseite zu öffnen: Aktor in den Lernmodus bringen (bei Eltako
meist Drehschalter auf LRN), dann **Einlernen senden**. Hat das Gerät mehrere Sender-IDs (etwa
Zentralbefehl und Taster), wählt man eine aus. Gesendet wird dasselbe wie mit der
Einlern-Schaltfläche des Geräts; bei einem VLD-Aktor (UTE) erst senden und den Aktor dann
innerhalb von 60 s in den Lernmodus bringen.

Der Status-Tab **Schwaches Signal** (mit orangefarbenem Punkt) zeigt nur die Sender mit schwachem
Signal, das schwächste zuerst.

**Geräte gruppieren** (neben der Suche) ordnet die Liste unter Überschriften nach **Bereich** oder
**Art** oder gar nicht; die Überschriften lassen sich einklappen und nennen die Anzahl und wie viele
der Gruppe Aufmerksamkeit brauchen. Die Wahl merkt sich der Browser.

Ein Klick auf eine Spaltenüberschrift sortiert danach (nochmal: umgekehrt); auf dem Handy
übernimmt das eine Auswahl. Die Suche, die Status-Tabs unter den Werkzeugen (**Alle Geräte /
Eingerichtet / Unbekannt / Still / Nie gehört / Schwaches Signal**, jeweils mit Zähler, leere gedimmt) und unter **Filter** das Gateway und der Bereich grenzen die Liste ein (**Filter** erscheint nur bei mehreren Gateways oder Bereichen), und sie wird seitenweise mit 25 bis 200 Zeilen
gezeigt. Die Telegrammzahlen beziehen sich auf den Puffer des Monitors (die neuesten 1.000
Telegramme), nicht auf die Zeit seit dem Start. Die Gerätezahl steht über der Liste, solange ein Filter sie einengt. Exportieren speichert die ganze gefilterte
Liste als CSV; Senden und Leeren gehören zur Telegrammliste und fehlen hier. Jede Zeile zeigt einen Zustand (aktiv, still, nicht gehört, deaktiviert, unbekannt); ihr Menü **⋮** enthält Einlernen, das Gerät in Home Assistant öffnen, die Telegramme des Geräts und **Entfernen**, das vorher nachfragt.

**Mehrere Geräte auswählen:** Jedes eingerichtete Gerät hat vorn ein Kästchen, **Alle auswählen**
über der Liste wählt alle gefilterten. Sobald etwas gewählt ist, zeigt eine Leiste, was sich mit
allen auf einmal tun lässt: einen **Bereich** setzen, **Labels** hinzufügen oder entfernen (ein
Haken fügt das Label allen hinzu, ohne Haken wird es entfernt, ein Strich lässt es; neue Labels
legst du im Formular an), die Geräte **deaktivieren** oder wieder **aktivieren** und sie
**entfernen**. Bereich, Labels und Deaktivieren sind die von Home Assistant, sie gelten also auch
auf der Geräteseite und in Automationen. **Entfernen** fragt vorher nach und löscht die Geräte
mit ihren Entitäten; ihre Sender-IDs bleiben gesperrt, bis du unter **Anlage → Sender-IDs → Sender-ID-Pool** bestätigst, dass
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

Der **Sender-ID-Pool** (Anlage → Sender-IDs, über der Tabelle, einklappbar) zeigt, wie voll der Pool
ist: je Gateway (und je Bus-Gruppe) die Pool-Karte mit jeder ID als kleinem Feld (frei, zugewiesen,
gesperrt, anderweitig belegt; die Legende darunter nennt die Farben). Der Tooltip nennt ID und
Gerät, ein Klick springt zur Zeile in der Tabelle darunter. Funkgateways vergeben Base-ID + 1…127.

Nach dem Löschen eines Geräts bleibt seine ID **gesperrt**, bis sie aus allen Aktoren abgelernt
ist. Gesperrte IDs stehen in der Tabelle zuerst, der Reiter zeigt, wie viele warten. **Freigeben**
gibt eine nach einer Rückfrage frei, sobald der Aktor sie verlernt hat (Teach-out). **Alle
freigeben** über der Karte gibt jede gesperrte ID des Pools frei, ebenfalls nach einer Rückfrage.
Nur tun, wenn jeder Aktor sie verlernt
hat: Ein neues Gerät mit einer solchen ID würde den alten Aktor sonst mitsteuern.

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
- ein Gerät, dessen letzte 5 Telegramme hintereinander zu keinem seiner Profile passen (etwa
  ein Tastertelegramm von einem Zähler) oder bei einem Standardprofil Werte außerhalb seiner
  Bereiche haben: es wurde sehr wahrscheinlich mit der falschen Art angelegt. Im ersten Fall
  nennt die Reparatur Geräte, für die solche Telegramme typisch sind. Einlerntelegramme zählen nicht, ein passendes Telegramm hebt die Reparatur auf

## Übernahme der alten Integration eltako

Die Ansicht **Übernahme** des Panels liest die Geräte der alten Integration `eltako` aus der
`configuration.yaml` (das Gateway mit derselben Base-ID) und richtet die gewählten mit ihren
IDs, Namen und Sender-IDs ein; die Aktoren brauchen kein neues Einlernen. Drei Schritte oben
zeigen, wo du stehst; die Ansicht öffnet beim ersten Schritt, in dem noch etwas offen ist.
**Berichte** neben den Schritten hält fest, was jede Übernahme getan hat (siehe unten).

1. **Auswählen** listet die Geräte nach Bereich, jedes mit alter Plattform und EEP und der Zahl
   seiner Fundstellen. Neue Geräte tragen die Marke *neu*. Schon eingerichtete Geräte, denen
   noch Werte der alten Integration fehlen, stehen in derselben Liste mit der Marke *schon da*
   und dem, was fehlt (zum Beispiel *Labels fehlt*). Zähler darüber zeigen, wie viele in der
   `configuration.yaml` stehen, wie viele schon vollständig sind und wie viele nicht
   übernehmbar sind (am Ende eingeklappt, mit Grund).
2. **Prüfen & übernehmen** zeigt als Kacheln, was aus der alten Integration mitkommt:
   **Bereich**, **Labels**, **Sprachsteuerung**, **Eigene Namen** (in Home Assistant vergebene
   Namen), **Symbole** und **Ausgeblendet / deaktiviert**, jeweils mit den Werten und bei wie
   vielen der gewählten Geräte es gesetzt ist. Anfangs ist nichts gewählt; das Panel merkt sich
   deine Wahl in diesem Browser; am neuen Gerät schon gesetzte Werte werden nie überschrieben.
   Darunter die Vorschau mit einer Zeile je Gerät; zu jeder angehakten Option stehen die Werte,
   die das Gerät mitbringt, gleich in der Zeile (zum Beispiel *Bereich: Flur*, *Labels: Licht,
   Matter-Hub*). Aufgeklappt zeigt ein Gerät Bereich, Labels und Namen und je Entität die alte
   Entity-ID neben der, die die neue Entität voraussichtlich bekommt (Home Assistant vergibt
   die ID erst beim Anlegen; für die Hauptentität und den ID-Sensor wird sie vorhergesagt, eine
   belegte ID bekommt „_2“), mit Name, Symbol, Labels, Sichtbarkeit und Sprachsteuerung, die an
   sie gehen. Von den übrigen Entitäten haben nur einige ein Gegenstück; ihre Werte sind mit
   „falls es ein Gegenstück gibt“ markiert. Schon eingerichtete Geräte stehen mit den Werten
   in der Vorschau, die ergänzt würden. Vor **Übernehmen (n Geräte)** wird nichts geschrieben;
   dieser eine Knopf legt die neuen Geräte an und ergänzt die gewählten schon eingerichteten
   mit denselben Optionen. Danach zeigt eine Ergebnisseite, was getan wurde, und führt zum
   letzten Schritt, der optional ist: Bis dahin läuft die alte Integration unverändert weiter.
3. **Alte Integration ablösen** beginnt mit einer Wahl, weil sich die alten Entity-IDs auf zwei
   Wegen behandeln lassen, die sich ausschließen (du kannst sie später ändern):
   - **Alte IDs behalten:** alte Integration löschen, dann gibt **Alte IDs wiederherstellen**
     den neuen Entitäten die alten Entity-IDs zurück, dann `eltako:` aus der
     `configuration.yaml` entfernen. Automationen, Skripte und Dashboards laufen unverändert,
     die Historie geht unter der alten ID weiter; was in der Zwischenzeit unter der neuen ID
     aufgezeichnet wurde, bleibt dort, und Home Assistant protokolliert je Entität einmal, dass
     es das nicht verschieben konnte. Eine ID, die eine Automation, ein Skript, eine Szene oder
     ein Dashboard schon als *neue* ID nutzt, bleibt wie sie ist.
   - **Neue IDs verwenden:** die Fundstellen mit alten IDs stehen nach Automation, Skript, Szene
     und Dashboard mit alten und neuen IDs und **Im Editor öffnen**, so stellst du jede in einem
     Zug um; **Neu prüfen** nach dem Bearbeiten. Danach alte Integration löschen und `eltako:`
     entfernen. Stellen in YAML, Templates und andere Werkzeuge wie Node-RED findet sie nicht:
     die mit der CSV des Berichts selbst durchsuchen.

   Automationen mit einem **Geräte-Trigger, einer Geräte-Bedingung oder -Aktion** (im Editor
   über das Gerät gewählt) überstehen das Löschen in beiden Fällen nicht: sie halten die
   Registry-ID der alten Entität, nicht ihre Entity-ID, und die geht mit der alten Integration.
   Stelle sie auf das neue Gerät um, oder auf einen Zustands-Trigger mit der Entity-ID, bevor du
   die alte Integration löschst.

Jede Übernahme hinterlässt einen **Bericht** im eigenen Speicher der Integration: wann sie
stattfand, welche Einstellungen mitkamen und je Gerät, was es in der alten Integration war
(Plattform, EEP, Namen, Bereich, Labels, Sender-IDs, Einstellungen seiner Entitäten) und seine
alte → neue Entity-ID. Von Hand eingerichtete Geräte, die die alte Integration kannte, bekommen
einen eigenen Bericht. Die Berichte bleiben nach dem Löschen der alten Integration abrufbar.
**Berichte** neben den Schritten (oder **Übernahme-Berichte** in der Ansicht Geräte) listet
sie; ein Bericht öffnet sich mit Kopieren und CSV, und **Löschen** entfernt ihn nach einer
Rückfrage: die Zuordnung seiner Geräte ist dann weg, und ihre alten IDs lassen sich nicht mehr
zurückgeben. Der Tab bleibt, solange es einen Bericht gibt; die Schritte kommen zurück, wenn
ein Gerät der alten Konfiguration noch nicht eingerichtet ist.

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
- [Rollläden und Licht bei Dämmerung](https://github.com/bertel2020/HA-Enocean-Eltako/blob/main/blueprints/automation/enocean_eltako/dusk_dawn.yaml) [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fbertel2020%2FHA-Enocean-Eltako%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fenocean_eltako%2Fdusk_dawn.yaml)
- [Wetterwarnung bei offenem Fenster](https://github.com/bertel2020/HA-Enocean-Eltako/blob/main/blueprints/automation/enocean_eltako/weather_warning.yaml) [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fbertel2020%2FHA-Enocean-Eltako%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fenocean_eltako%2Fweather_warning.yaml)

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
  Nennt die App das Modell in ihrer Meldung (`model`, zum Beispiel `fam_usb`), entfällt die
  Frage; sonst wird es am Namen des Gateways erraten. Die Base-ID wird vom Gateway gelesen;
  antwortet es nicht, liefert sie der Status der App.
- Nach einem Neustart von Home Assistant liefert die App die Telegramme nach, die inzwischen
  ankamen (nur Funktelegramme, standardmäßig höchstens 15 Minuten alt), mit ihrer
  Empfangszeit, damit Rollladenpositionen, Zählerstände und „Zuletzt gehört“ stimmen. Auf
  Wunsch hebt die App sie auch über ihren eigenen Neustart auf.
- Was die Nachlieferung damit macht: Kontakte und andere Binärsensoren nehmen sie in einem Zug
  auf und schreiben ihren Zustand einmal, wenn sie durch ist. Eine zwischendurch geöffnete und
  geschlossene Tür lässt den Sensor also nicht mehrfach umschalten und löst nicht für jeden
  Wechsel Trigger aus; ein Zustand, der am Ende dort steht, wo er begann, löst nichts aus. Der
  Verlauf zeigt die Änderung zum Zeitpunkt des Neustarts, nicht zur echten Zeit (Home Assistant
  kann sie nicht zurückdatieren); „Zuletzt gehört“ hat die echte Zeit. Tasterdrücke sind
  Ereignisse, keine Zustände: nachgelieferte lösen keine Taster-Ereignisse aus, es läuft also
  keine Automation mit einem Druck von vor dem Neustart. Ohne Nachlieferung behält ein Kontakt
  seinen letzten Zustand, bis er sich wieder meldet.
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
