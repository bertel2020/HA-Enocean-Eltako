# Changelog (Deutsch)

> English version: [CHANGELOG.md](CHANGELOG.md)

## Unreleased

### Geändert

- **Panel:**
  - „Unbekannte Sender vergessen nach“ steht nur noch im Panel („Automatisch vergessen…“ im ⋮-Menü der Geräteliste), nicht mehr in den Gateway-Einstellungen. Der Wert bleibt erhalten.

### Behoben

- **Panel:**
  - Die Einträge des ⋮-Menüs (u. a. „Automatisch vergessen…“, Export, Dokumentation) taten beim Anklicken nichts: das Menü schloss sich schon beim Drücken der Maustaste.
- **Rollläden:**
  - Der Zustandssensor zeigt „Offen“ bzw. „Geschlossen“, wenn die gemeldete Fahrzeit eine volle Fahrt war (Fahrten mit Laufzeit aus Home Assistant enden mit der Fahrzeit, nicht mit 0x70/0x50), statt „Gestoppt“.

## 1.11.0 - 2026-11-12

### Neu

- **Unbekannte Sender parken**: Im Panel lassen sich unbekannte Sender über das ⋮-Menü als **Taster**, **ungenutzt** oder **ignoriert** ablegen (nichts wird automatisch geparkt). Geparkte Sender fallen aus „Alle“ und der Aufmerksamkeit; „Zurückholen“ macht es rückgängig, bei den Chips auch „Alle zurückholen“. Bisher ausgeblendete Sender gelten als „ignoriert“ (Migration). „Geparkte Sender“ unter Konfigurieren entfällt. Bus-Sender tragen „Bus · Adresse N“ und lassen sich gemeinsam parken. Pool-IDs, die Home Assistant nicht vergeben hat (z. B. Symcon), werden aufgelistet und lassen sich für ein anderes System sperren.
- **Beschriftung für unbekannte Sender**: „Beschriftung ändern“ im ⋮-Menü. Sie ersetzt den Namen, ist durchsuchbar und wird beim Einrichten vorgeschlagen.
- **Vergessen im Panel**: „Automatisch vergessen…“ stellt die Tage ein (je Gateway), „Vergessen…“ unter „Neu“ vergisst nach Zeitraum (1, 7, 30 Tage oder alle), jeweils mit Rückfrage. Geparktes und Beschriftungen bleiben.
- **Impuls-Aktor (Garagentor)**: Neuer Typ „Impuls (Taste)“ beim Schaltaktor. Der Button „Auslösen“ sendet „Ein“ genau einmal (nie wiederholt), ein Diagnose-Relais zeigt die Rückmeldung. Den Aktor als Universaltaster ER einlernen (Drehschalter 10) und die EW-Zeit auf 1–2 s stellen. Noch nicht an Hardware getestet.
- **Letzte Taste (Diagnose)** bei Wippentastern und Kontakten über Tastertelegramme: Sensor mit der zuletzt gedrückten Taste, standardmäßig aus.
- **Tastenlage in den Auswahllisten**, z. B. „B0 · rechts oben (0x70)“.
- **Taster sperren** (Schaltaktor, Dimmer, Rollladen): Schalter je Gerät. Ist er an, tragen die Befehle von Home Assistant das Sperr-Bit und der Aktor ignoriert eingelernte Taster. Der Zustand ist angenommen. Noch nicht an Hardware getestet.
- **Helligkeitssensoren FAH65S, FIH65S und FHD65SB** (A5-06-01 und A5-06-02 im Eltako-Format, noch nicht an Hardware getestet). Als Modelle neu: FSTAP, FSMTB, FLGTF65, FLGTF55, FLGTF55E, FSM14.
- **Baureihe 62** (FL62, FR62, FD62, FJ62): Buttons „Lernmodus entsperren“ und „Ausmelden“ (Diagnose, standardmäßig aus). Noch nicht an Hardware getestet.
- **Thermostat am Schaltaktor-Kanal** (z. B. Konvektor am FSR14): Optional in den Geräteeinstellungen. Home Assistant regelt einen frei wählbaren Raumtemperatursensor um die Solltemperatur und schaltet das Relais, ohne eigene Sender-ID. Ohne Raumtemperatur (oder zu lange stumm) geht das Relais aus. Mit einem Zähler „Gehört zu Gerät“ zeigt „Heizt“ die echte Leistung, eine Blockade wird als Reparaturhinweis gemeldet. Einstellbar sind u. a. Hysterese, Sollwertgrenzen, Laufzeiten und ein Feuchtesensor. Subentry-Schema 7 mit Migration.
- **Zähler unter einem Gerät**: Ein Zähler (z. B. F3Z14D) kann „Gehört zu Gerät“ auf den Schaltaktor an derselben Last gesetzt werden und erscheint dort als „Verbunden über …“. Entitäten, IDs und Verlauf bleiben. Subentry-Schema 6 mit Migration.

### Geändert

- **Übernahme: Kontakte über Tastertelegramme** (FSM14, FTS14EM …) übernehmen jetzt „Aus bei: losgelassen“, wie die alte Integration. Ohne das blieb ein Kontakt nach dem ersten Öffnen für immer auf „offen“. Bereits übernommene Kontakte lassen sich unter „Aus bei“ umstellen.
- **Bus-Aktoren (Baureihe 14 am FAM14)** bestätigen bis zu 10 s später. Ein Befehl wartet deshalb 12 s statt 1 s auf die Bestätigung, und ein Fahrbefehl eines Rollladens wird nicht mehr wiederholt. Schneller geht es mit einer Geräteliste im PCT14 und FAM14-Betriebsart 5.
- **Zähler: Seriennummer** nur noch bei Zählern, die sie senden (FWZ12, FWZ14, FSDG14, DSZ14DRS, DSZ14WDRS), im Format „S-AABBCC“. Die Ziffernkodierung ist noch nicht mit einem Mitschnitt geprüft.
- **Dokumentation**: Die Benutzeranleitung und der Hilfetext erklären „Bestehende Entitäten jetzt umbenennen“ (was angepasst wird, was nicht, Backup vorher).

## 1.10.0 - 2026-11-11

### Geändert

- **Sensoren**: Versorgungsspannungen (Batterie oder Solarzelle) werden mit einer Nachkommastelle angezeigt; der gespeicherte Wert behält zwei.

### Behoben

- **Panel**:
  - Die aktive Ansicht lädt sich von selbst neu, wenn sich in Home Assistant Geräte-, Entitäts-, Bereichs- oder Label-Register ändern (mit kurzer Verzögerung, damit eine Serie von Änderungen nur einmal lädt).
  - Beim Zurückkehren zum Tab wird die aktive Ansicht neu geladen (Anlage, Geräte, Sender-ID-Pool, Übernahme); Änderungen in Home Assistant brauchen dafür kein Neuladen der Seite mehr.
  - Suchfelder: Der Cursor springt beim Tippen in den Suchfeldern der Anlage und des Busses nicht mehr an den Anfang, und sie haben ein Kreuz zum Leeren.
  - Die runden Symbol-Buttons (zum Beispiel das + eines unbekannten Senders) behalten ihre Größe und werden nicht mehr zu einem Oval gedrückt.
- **Übernahme, Zuordnung und CSV**: Der alte Fenstergriff-Sensor (`…_windowhandle`) bekommt in der Zuordnung alt → neu jetzt sein Gegenstück (den Sensor Griff); er stand bisher ohne neue ID da.
- **Katalog**: Der F3Z14D steht in der Modellliste des Stromzählers an erster Stelle.
- **Geräte-Dialog**: Der Schalter „Zurück“ heißt jetzt „Zurück (ohne Speichern)“ und erklärt sich in seiner Beschreibung.

### Neu

- **Unbekannte Sender**:
  - Sie bleiben über Neustarts erhalten; Geräteansicht des Panels und „Gerät hinzufügen“ listen sie wieder auf.
  - Neue Gateway-Einstellung „Unbekannte Sender vergessen nach“: nach so vielen Tagen ohne Telegramm fallen sie heraus (Standard 30 Tage, 0 behält sie).
  - Die Geräteansicht hat auf dem Reiter Unbekannt einen Button „Alle vergessen“.
- **Panel**:
  - Ein Aktualisieren-Button im Kopf jeder Ansicht lädt die Daten neu aus Home Assistant; der Tooltip nennt den Zeitpunkt der letzten Aktualisierung.
  - Geräteansicht: Die Zeile eines eingerichteten Aktors zeigt seine Sender-ID (die erste; der Tooltip listet alle).
  - Verbindungen: Die Liste nach Aktor lässt sich auch nach Geräte-ID und nach Sender-Nr. sortieren.
  - „Als Gerät hinzufügen“ zeigt einen Hinweis, dass es mit „Gerät hinzufügen“ beim Gateway weitergeht.
- **Geräte-Dialog**: Das Geräteformular und die Auswahl der Geräteart eines gehörten Senders haben einen Schalter „Zurück“, der ohne Speichern zum vorigen Schritt führt (Adressmenü, Liste der entdeckten Geräte oder Start).
- **Katalog**: Der F3Z14D (drei S0-Eingänge für Strom, Gas und Wasser) ist jetzt als Modell für Strom-, Gas- und Wasserzähler wählbar.
- **Übernahme, Gateway-Präfix**: Bei eingeschaltetem Gateway-Präfix bietet der Schritt „Mitnehmen“ die Option „Gateway-Präfix in Entitäts-IDs“. Home Assistant gibt einer Entität, die es schon gab (Gerät übernommen, gelöscht und erneut übernommen), ihre frühere ID zurück, das Präfix wurde dann nicht angewendet; die Option benennt die Entitäten der gerade übernommenen Geräte nach dem Präfix-Schema um.

## 1.9.0 - 2026-11-09

### Geändert

- **Entdeckte Geräte, Karte**: „Hinzufügen" auf der Karte im Bereich „Entdeckt" zeigt jetzt gleich die gehörten Sender (stärkstes Signal zuerst, mit Art und dBm), statt nur auf das Gateway zu verweisen. Ein gewählter Sender wird beim „Gerät hinzufügen" am Gateway direkt weitergeführt, ohne Menü und zweite Liste. Sender, die nicht dir gehören, lassen sich in der Karte ausblenden; sie bleibt offen, bis die Liste leer ist.
- **Entdeckte Geräte**: Die Liste zeigt das stärkste Signal zuerst, mit der Art im Klartext (zum Beispiel `FF-C2-4A-C5 · Sensoren (A5) · -69 dBm`) oder dem Profil aus einem Teach-in. Ab 7 Einträgen ist sie ein Dropdown statt einer langen Liste, und die Beschreibung ist kürzer. Beim Ausblenden eines Senders geht es zur Liste zurück, solange noch weitere übrig sind.

## 1.8.0 - 2026-11-08

### Geändert

- **Monitor-Panel am Handy**: Die Ansichten (Telegramme, Geräte, Anlage, Übernahme) sind jetzt eine untere Leiste mit Icons. Der Integration-Link im Header zeigt nur noch das Icon.
- **Monitor-Panel-Benennung**: In der Anlage heißt die bisherige Gruppe und der Tab Geräte jetzt **Dokumentation**, damit der Name nicht mehr mit der Ansicht Geräte übereinstimmt.
- **Monitor-Panel-Header**: Palette und Integration-Link sind jetzt runde 24-px-Icon-Buttons im gleichen Look wie im Fritzbox-Network-Panel.

### Neu

- **Bus-Sender-IDs**: Geräte an einem Gateway einer Bus-Gruppe (FGW14-USB, FAM14) bekommen ihre Sender-ID aus dem Bus-Pool (00-00-B0-xx) vorgeschlagen statt aus dem Funk-Pool. Der Pool gehört der ganzen Gruppe; ein Neuladen eines Mitglieds sperrt die IDs der Geräte eines anderen nicht mehr.

### Behoben

- **Monitor-Panel auf dem Handy**: Die Übernahme-Liste hält IDs und Typen zusammen und zeigt ihre Marken in einer eigenen Zeile statt über dem Text. Die Sortier- und Gruppierungsauswahl der Geräte-Ansicht ist vollständig lesbar, Gerätenamen dürfen zwei Zeilen belegen, Häkchenfelder sind größer und ein Profilhinweis wie „A5-10-06“ bricht nicht mehr mitten im Code um.
- **Schaltbestätigungen**: Ein Status, der den anderen Relaiszustand meldet als der Befehl verlangt (die späte Antwort auf einen ersetzten Befehl), bestätigt den neuen Befehl nicht mehr.
- **Geräteansicht mit mehreren Gateways**: Eine auf zwei Gateways eingerichtete Sender-ID behält je Zeile Gerät und Gateway.
- **Anlage**: Das Verlassen des Bus-Drawers per Zurück, Link oder Bus-Wechsel fragt bei ungespeicherter Eingabe zuerst nach.
- **Dokumentationsimport**: Jedes nicht zugeordnete Gateway wird mit seiner eigenen Base-ID gemeldet.
- **Sender-IDs**: Ein fehlgeschlagenes Speichern eines Geräts stellt jede berührte ID genau wieder her; ein entferntes Gateway hält seine IDs für ein später mit gleicher Base-ID neu angelegtes Gateway gesperrt; der Lern-Schritt ignoriert unsere eigenen Pool-IDs.
- **Wiederhergestellte Schalter und Lichter**: Das Gerät behält den rohen Relaiszustand, und der Sendertest wartet auf ein echtes Status-Telegramm (ein invertierter Schalter konnte vom Test geschaltet werden).
- **Als Gerät anlegen** nutzt das angeklickte Gateway, nicht das Gateway, das den Sender zuletzt gehört hat.
- **Gateway**: Schließen während des Verbindungsaufbaus lässt Port oder Socket nicht mehr offen; ein Senden hinter einem Base-ID- oder Repeater-Befehl scheitert nicht mehr mit ihm; ein ersetzter, schon gesendeter Befehl wartet nicht mehr auf seine Antwort.
- **Telegramm-Verlauf** übersteht ein Neuladen des Gateways (jede Geräteänderung); das Notizobjekt eines entladenen Eintrags wird nach dem Flush verworfen.
- **Panel**: Die Aufnahme nutzt die Serveruhr, eine Takeover-Antwort für ein anderes Gateway wird verworfen, die Tabs der Anlage und die Popup-Menüs funktionieren mit den Pfeiltasten, ein Doppelklick auf Speichern im Bus legt nur einen Eintrag an, und das Autospeichern der Netzteile zieht den Cursor nicht mehr zurück.

## 1.7.0 - 2026-11-05

### Geändert

- **Ablauf der Übernahme**: ein Knopf je Schritt. Schon eingerichtete Geräte, denen noch Werte der alten Integration fehlen, sind jetzt Zeilen der Liste in Schritt 1 (mit der Marke, was fehlt) statt eines eigenen Abschnitts mit zweitem Knopf. Schritt 2 zeigt vorab, was mit jedem Gerät geschieht, und hat den einen Knopf **Übernehmen (n Geräte)**: Er legt die neuen Geräte an und ergänzt die gewählten eingerichteten. Danach zeigt eine Ergebnisseite, was getan wurde, und führt zum optionalen letzten Schritt, den sie erklärt. Der kleine Link „Weiter: Ablösen“ entfällt. Der Websocket-Befehl `takeover/carry` nimmt eine optionale Geräteliste.

### Behoben

- **Übernahme**: Die Ansicht nach einer Übernahme schlug fehl („nichts zu tun“), wenn eine alte Entität in einer Automation, einem Skript, einer Szene oder einem Dashboard verwendet wurde.
- **Gateway-Karte**: Der Status „Verbunden“ übernimmt nicht mehr das Aussehen der Gerätestatus-Pillen (grau, mit zwei Punkten).
- **Übernahme, schon eingerichtete Geräte**: Der Hinweis „Wähle oben, was mitkommen soll“ steht jetzt als Text; der ausgegraute Button trägt ihn nicht mehr als Beschriftung.

## 1.6.0 - 2026-11-04

### Neu

- **Eltako-Bus-Ansicht, Lesen (experimentell, nicht mit einem FAM14 geprüft)**: liest den Bus nur durch Mithören; Home Assistant sendet nichts an den FAM14 oder an Bus-Geräte. Der FAM14 funkt die Bestätigungstelegramme der Aktoren mit seiner Base-ID plus Geräteadresse (so beschreibt es Eltako); nach ausdrücklicher Zustimmung nimmt die Ansicht, was die Gateways des Busses schon gehört haben, und hört bis zu 120 s mit. Sie listet die antwortenden Adressen mit ihrem letzten Telegramm, gleicht sie mit der Dokumentation ab (neue Prüfungen: gehörte, aber nicht dokumentierte Adressen, dokumentierte Kanäle ohne Antwort, eine vorgeschlagene Base-ID), bietet an, eine Adresse zu dokumentieren oder einen gehörten Sender als Gerät anzulegen, und der Kanal-Drawer schlägt die Rückmelde-ID vor (Base-ID + Adresse). Auf dem Draht des Busses (FGW14-USB) wird angenommen, dass die ID die Adresse ist. Geräteliste, Typen oder Base-ID aus dem FAM14 lesen und eine PCT14-Sicherung importieren ist nicht gebaut: Eltako veröffentlicht dieses Protokoll nicht.
- **Eltako-Bus-Ansicht, Schränke**: jede Reihe eines Schranks ist eine maßstäbliche Hutschiene in TE, mit den Modulen an ihrem Platz (FAM14 als Master, eine LED je Kanal: in Home Assistant, nur dokumentiert, frei; ein Punkt bei einer Prüfung), Abständen (½ TE), Trennbrücken TB14, dem Abschlusswiderstand 120 Ω, den Bändern der Speiseabschnitte unter der Schiene und wie der Bus weitergeht (BBV14, Busankoppler FBA14, Busleitung mit Länge). **Anordnen** tauscht ein Gerät per Pfeiltasten mit seinem Nachbarn, am Ende der Reihe verschiebt es sich um ½ TE; was überlappt oder nicht passt, wird abgelehnt (kein Drag and Drop). Geräte ohne Bus (LS, FI, Klemmen) sind Blöcke mit Name und Breite, angelegt im Drawer am ersten freien Platz.
- **Eltako-Bus-Ansicht, Prüfungen der Schiene**: ein Netzteil mit mehr als 4 W Last ohne ½ TE Luft auf der linken Seite und mit mehr als 6 W direkt neben dem FAM14 ohne Distanzstück DS14 (die Regeln der FAM14-Anleitung und der Betriebsanleitung Baureihe 14), ein FUD14 ohne Abstand, Abschlusswiderstand fehlt, doppelt oder nicht am letzten Gerät, und eine Reihe ohne eingetragene Busverbindung zur nächsten.
- **Eltako-Bus-Ansicht, Druck**: **Drucken / PDF** gibt die Schienen jedes Schranks, die Geräte und Kanäle nach Einbauort (Adresse, Rückmelde-ID, Gerät in Home Assistant, Stromkreis und Sicherung), die offenen Prüfungen und Etikettenstreifen mit 18 mm je TE zum Ausschneiden.
- **Eltako-Bus-Ansicht nach Bus-Master**: Anlage → Geräte → Bus zeigt den Bus, wie er gebaut ist, nicht mehr eine Tabelle je Gateway. Der Kopf nennt den Bus-Master (FAM14, Base-ID von Hand eingetragen) und wie Home Assistant den Bus erreicht (ein FAM-USB als Funk-Gateway, das nicht am Bus sitzt, ein Bus-Gateway als drahtgebundener Zugang). Ein **Modul** ist das Gerät auf der Hutschiene mit seinen **Kanälen** (ein FSR14-4x mit vier Kanälen, jeder ein Gerät in Home Assistant, nur dokumentiert oder frei); die **Liste** ist eine Tabelle mit der Adresse vorn (der Bereich in der Modulzeile, je Kanalzeile eine Adresse), sortierbar nach Adresse, Gerät, Typ und Einbauort, mit Suche, Filterchips (doppelt, ohne Adresse, in Home Assistant, nur dokumentiert), Rolle und Schrank oder Reihe und einzeln wählbaren Spalten (Adresse und Gerät bleiben); Sortierung, Filter und Spalten merkt sich der Browser, freie Adressbereiche stehen bei Sortierung nach Adresse zwischen den Modulen, der **Adressplan** zeigt 1 bis 126 mit Doppelvergaben, die **Prüfungen** nennen doppelte Adressen und Rückmelde-IDs, Geräte ohne Adresse oder Einbauort, Lücken, Kanäle, die nicht in Home Assistant sind, Bus-Geräte aus Home Assistant ohne Modul und überlastete Netzteile. Ein Drawer für Modul, Kanal, Sender und Bus verlinkt das Gerät in Home Assistant, die eingelernten Sender, das Netzteil sowie Schrank und Reihe. Der Einbauort wird aus **Schränken mit Reihen** (12 TE, wenn nicht anders eingestellt) und einem Platz in halben TE gewählt, statt als Freitext.
- **Katalog der Baureihe 14**: Breite in TE, Bus-Adressen (eine je Kanal, F3Z14D drei), Leistung vom und an den Bus und Rolle jedes Typs; `docs/devices.de.md` listet ihn. Werte, die noch kein Datenblatt bestätigt, sind markiert.
- **Installationsspeicher** `enocean_eltako.installation` (Version 1) für den Bus aller Gateways, mit Websocket-Befehlen zum Lesen und Ändern (geprüft: Raster in halben TE, Reihenbreite, Überlappung, Adressen 1 bis 126). Notizspeicher Version 8 übernimmt einmal je Gateway, was die Notizen für den Bus hielten (Bus-Adresse, Rückmelde-ID, Leistung, Netzteile mit ihren Adressbereichen, Bus-Einträge von Hand; Kanäle mit gleichem „Gehört zu“ und Typ werden ein Modul, ein Ort „Schrank · Reihe · Platz“ Schrank, Reihe und Platz). Die Notizen behalten diese Felder als Kopie, die der Speicher zurückschreibt, damit die anderen Ansichten, der Druck und die CSV dieselben Werte lesen; eine Änderung dort wird übernommen. Der Doku-Export Version 3 enthält die Installation; der Import nimmt die Versionen 1, 2 und 3.
- **Solarsensor FAFT60**: Der neue Gerätetyp **Temperatur, Feuchte und Versorgungsspannung** (Profil `A5-04-02:eltako`) liest neben Temperatur und Feuchte die Spannung des Energiespeichers des Sensors, als Diagnose-Entität (**Spannung**). Der Sensor sendet sie im ersten Datenbyte, 0,025 V pro Schritt; ein FAFT60 im Betrieb liest 2,8 bis 3,5 V, tagsüber steigend und nachts fallend. Der FAFT60 wandert von **Temperatur und Feuchte** zum neuen Typ; ein vorhandenes FAFT60-Gerät wechselst du unter **Neu konfigurieren → Gerätetyp**. Die Skala (0,025 V) stammt von einem Gerät im Betrieb, nicht aus einem Datenblatt.
- **Letztes Telegramm jedes Senders**: Das neueste Telegramm jedes bekannten Geräts und jedes unbekannten Senders bleibt über Neustarts erhalten (Typ, Datenbytes, Statusbyte, Signal, Zeit; höchstens 300 Sender je Gateway, geschrieben zusammen mit den Signaldaten). Die aufgeklappte Zeile der Geräte-Ansicht zeigt es unter **Funk** als **Letztes Telegramm**, mit den Bytes in hex und dem, was sie sagen; ein Sensor, der selten sendet, hat so immer etwas zu zeigen. Notizspeicher Version 7.
- **Eltako-Bus-Ansicht**: Ein Netzteil, das über zwei Drittel seiner Nennleistung belastet ist (8 W von 12 W beim FSNT14-12V/12W, der vorsichtige Wert aus Eltakos Handbüchern), zeigt **weiteres Netzteil empfohlen** und einen hervorgehobenen Balken; über der Nennleistung bleibt es überlastet.
- **Eltako-Bus-Ansicht**: **Netzteil hinzufügen** bietet die 12-V-Netzteile von Eltako mit ihrer Nennleistung an (FSNT14-12V/12W, SNT12-230V/12V DC-1A, SNT15-12VDC/15W, WNT15-12VDC/24W) und ein eigenes Netzteil zum selbst Ausfüllen.
- **Geräteansicht (Tabelle)**: Der Gerätename öffnet das Gerät in der Ansicht Geräte.
- **Raumregler mit mehreren IDs** (FUTH55ED, FUTH65D): ein Gerät für die vier IDs, von denen ein FUTH sendet, eingetragen mit seiner niedrigsten ID (endet auf `00`). Regler (`+01`: Klima, Sollwert, Temperatur, Nachtabsenkung), Pumpe (`+10`), Betriebsart (`+11`) und Hygrostat (`+12`: Luftfeuchte, auch an der Klima-Entität). Nur lesend. Die Geräteansicht listet jede ID, die Dokumentation jede mit ihrem Profil. Die Offsets stammen aus der Tabelle der alten Integration; die Telegramme eines FUTH55ED bestätigen Regler und Hygrostat, Pumpe und Betriebsart werden aus den Wippen-Codes `0x70/0x50` und `0x70/0x50/0x30/0x10` gelesen.
- **Telegrammprotokoll**: Ein Befehl, den Home Assistant gesendet hat, wird jetzt wie ein empfangenes Telegramm gelesen: Sollwert und Nachtabsenkung eines Raumreglers (Temperatur 0 heißt: das Thermostat misst), Schalten Ein/Aus und Dimmwert, Rollladen auf/ab/Stopp mit Laufzeit, Wippentaste gedrückt oder losgelassen, die Statusanforderung. Gelesen wird nur, was die Encoder bauen; andere Profile zeigen weiter die Rohbytes.
- **Telegrammprotokoll**: Ein Telegramm, das das Modell eines bekannten Geräts nicht lesen kann, ein bis drei andere Modelle aber schon, nennt diese Gerätetypen (**Passt zu** ...). Ein Gerät mit falschem Gerätetyp, etwa ein Permundo PSC als Eltako-Schalter, zeigt Rohbytes; jetzt steht in der Zeile, welcher Typ sie entschlüsseln würde.
- **Übernahme**: Ein Schalter der alten Konfiguration, dessen ID mit einem D2-01-09-Status gehört wurde (die alte Integration kennt kein VLD), wird als **Permundo PSC** mit dem Standard-A5-38-08-Controller übernommen, nicht mehr als Eltako-Schalter, der Rohbytes zeigt.
- **Gerät umkonfigurieren**: Der **Gerätetyp** eines schaltenden Geräts lässt sich ändern (Eltako-Schalter, Permundo PSC, VLD-Schalter). Die Sender-ID des ersten Senders bleibt, vor der Bestätigung des Formulars des neuen Typs wird nichts gespeichert, und die ID wird nicht gesperrt oder ausgemeldet, weil sie nur das Profil wechselt.

### Geändert

- **Benutzerhandbuch**: Der Abschnitt Geräte beschreibt die Status-Tabs, die Gruppierung und die Gerätezahl der neuen Filterleiste.
- **Anlage → Geräte, Leiste**: die Zähler „ohne Ort / ohne Sicherung“ sind ruhige Pillen direkt unter den Werkzeugen, Ansichten, Werkzeuge und Zähler rücken enger zusammen.
- **Geräte-Ansicht, Filterleiste**: Suche, Filter, Gruppierung und die Übernahme-Berichte stehen jetzt in einer Zeile; der Status-Filter ist darunter eine ruhige Tab-Leiste (aktiver Tab unterstrichen, leere gedimmt, schwaches Signal mit orangefarbenem Punkt). Die Zeile mit Gerätezahl und Hinweis auf schwache Signale entfällt: Die Zahl erscheint nur, solange ein Filter die Liste einengt, der Tab „Schwaches Signal“ sortiert die schwächsten zuerst. Die Gruppierung heißt „Keine Gruppen / Nach Bereich / Nach Art“.
- **Geräte-Ansicht, geöffnete Zeile**: die Karten des Funk-Abschnitts lassen keine einzelne Karte mehr allein in einer Reihe: „Gehört von“ hat die volle Breite, die Telegrammzahl steht bei den anderen Werten. Auf dem Handy laufen die Tabs der Anlage am Menü weich aus, statt davon abgeschnitten zu werden.
- **Anlage, Sender-IDs**: eine Zeile unter der Pool-Karte sagt, was sie zählt (was Home Assistant vergeben hat) und dass die Tabelle darunter auch nur dokumentierte IDs führt.
- **Telegramm-Ansicht**: ruhigere Zeilen: kein Punkt vor dem Sendernamen, der Telegrammtyp ist schlichter Text statt Chip, und ein gesendetes Telegramm ist wie ein empfangenes aufgebaut (Gerätename mit der Markierung „Gesendet“, darunter die Sender-ID).
- **Anlage auf dem Handy**: die Tabs laufen in einer Zeile zum Wischen, das Menü steht daneben (statt drei Reihen), und Suche und Knöpfe über einer Liste nutzen die ganze Breite.
- **Anlage, Geräte**: die Liste aller Geräte hat eine Filterreihe (die Ansichten) statt zwei; die Arten gibt es innerhalb einer Ansicht. Der Löschknopf eines Ortes erscheint erst, wenn man die Zeile ansieht, das Auswahlkästchen klebt nicht mehr an der Farbleiste, und die Zähler über der Tabelle haben eigenen Platz.
- **Geräte-Ansicht auf dem Handy**: die Status-Chips laufen in einer Zeile zum Wischen, Sortierung und Gruppierung teilen sich eine Zeile, der Hinweis auf schwaches Signal entfällt (sein Chip sagt dasselbe); die Liste beginnt etwa 200 px weiter oben.
- **Anlage, Sender-IDs**: die Kachel „In Gebrauch“ zählt jetzt dieselben Zeilen, die ihr Filter zeigt (mit dem Gateway).
- **Geräte-Ansicht**: eine Zeile je Gerät, auf einen Blick lesbar: links Name mit ID und Modell, Typ über Bereich in einer Zelle, Zustand mit Werten, rechts zuletzt gehört mit Signal. EEP-Chip, Entitäten-Spalte, Labels und Telegramm-Verlauf sind aus der Zeile verschwunden (Labels, Entitäten und Telegrammzahl stehen in der geöffneten Zeile). Geräte sind nach Bereich gruppiert (oder nach Art, oder gar nicht) unter einklappbaren Überschriften, die zeigen, wie viele davon Aufmerksamkeit brauchen; ein neuer Statusfilter zeigt nie gehörte Geräte.
- **Gerätezeile**: Die Spalten von Werten, Sendern, Einstellungen und Entitäten stehen in allen Zeilen untereinander, auch bei langen Werten. „Letztes Telegramm“ geht über die ganze Breite und zeigt nur Zeit, Typ, Signal und Bytes; die gelesenen Werte stehen einmal unter „Letzte Werte“. Zustände der Entitäten sind lesbar (Zeit als „vor …“, Zahlen mit Komma, ein/aus übersetzt). Die Entitäten stehen in der Reihenfolge Steuerung, Messwerte, Diagnose; ohne eigenen Namen heißt eine Entität wie ihr Gerät, nicht wie ihre ID.
- **Permundo-Stecker (PSC132, PSC234)**: Der Taster (Wippe) ist als Sender wählbar, neben dem Zentralbefehl. Ein Stecker, der als Taster eingelernt ist, wird damit aus Home Assistant geschaltet; mindestens ein Sender genügt. Die Tasten stehen vorbelegt auf AI für Ein und A0 für Aus, wie der Stecker sie erwartet.
- **Anlage, Verbindungen**: jede Verbindungszeile hat feste Spalten (Sender mit ID | Rolle | Herkunft | Lernposition | Status mit kurzer Zeitangabe, die volle als Tooltip | Aktionen rechts), gleich hohe Zeilen, Tags brechen nie um; die Sendernummer steht nicht mehr in jeder Zeile, die ID selbst führt zum Tab Sender-IDs. Auf dem Handy stapelt sich die Zeile, die Aktionen stehen neben dem Namen.
- **Querverweise**: das Art-Tag eines Bus-Geräts oder Netzteils öffnet seinen Kanal bzw. sein Modul im Bus-Tab, eine Schrankreihe zeigt ihre Geräte in der Gerätetabelle, eine Ortsgruppe der Tabelle führt zurück zur Reihe; der Gateway-Name öffnet seine Karte; eine benutzte Sender-ID führt zu ihren Verbindungen, ein aufgeklapptes Gerät zu seiner Verbindungskarte, ein von Hand eingetragener Sender zu seiner Zeile, eine Sender-ID im Protokoll zu ihrer Zeile im Tab Sender-IDs. Nach einem Sprung in einen anderen Tab erscheint **Zurück**.
- **Anlage, Gerätetabelle**: eine Tabelle für alle Gateways, zuerst nach Ort (Schrank · Reihe) gruppiert; die Gruppierung (keine, Bereich, Ort, Gateway) merkt sich der Browser, das Gateway ist ein Tag der Zeile. Der Ort wird aus den dokumentierten Schränken und Reihen gewählt, der Platz als Zahl, mit **+ Schrank anlegen …** oder Freitext für einen Ort, der kein Schrank ist; ✕ entfernt ihn. Bei einem Bus-Gerät ist es der Ort seines Moduls: Geräte-Tab und Bus-Tab zeigen und bearbeiten denselben Ort (Notizspeicher Version 9 übernimmt ihn einmal). Ansichten und Arten sind eine Filterleiste mit stimmigen Zahlen. Spalten werden einzeln unter ihren Gruppen gewählt, mit alle/keine je Gruppe (die bisherige Gruppenwahl wird übernommen); eine Spalte erscheint, sobald eine der Zeilen sie nutzen kann, ohne dass eine Art gewählt sein muss. Leere Orte und Felder sind ein ruhiger Strich, die Zähler über der Tabelle schlichter Text. Jede Tabelle der Anlage endet in einer schmalen Menüspalte: das Zeilenmenü (⋮) steht in jeder Zeile an derselben Stelle und öffnet nach links.
- **Geräte-Ansicht, aufgeklappte Zeile**: ein Kartenraster (Karten ab 220 px, je Zeile gleich hoch; breite Inhalte wie letztes Telegramm oder „Gehört von“ über zwei Spalten) und eine Zeilenkomponente mit Innenabstand und festen Spalten für letzte Werte, Sender-IDs, Einstellungen und Entitäten. Das letzte Telegramm zeigt Zeit · Typ · dBm, die Bytes und das Statusbyte als Monospace-Tags, die nicht umbrechen. **Letzte Werte** zeigt, was das Telegramm sagt (aus dem Live-Telegramm, sonst aus dem zuletzt gespeicherten) mit Herkunft, die Rohbytes darunter; nur Hex, wenn sich nichts lesen lässt. Abschnittsüberschriften sind deutlicher und zählen ihre Zeilen. In der Liste bleibt der Name einzeilig (voller Name als Tooltip), „Zuletzt gehört“ steht in zwei Zeilen, und die Werte-Spalte zeigt den Zustand der Entitäten vor rohem Hex.
- **Eltako-Bus-Ansicht, Netzteile**: ein FAM14 und sein beiliegendes FSNT14 zählen nicht mehr doppelt. Ein FAM14 bis Fertigungswoche 07/22 hat das Netzteil integriert (12 W), ein späterer wird über sein beiliegendes FSNT14-12V/12W versorgt. Ein FSNT14 direkt neben dem FAM14 gilt als dieses (Annahme), der Abschnitt hat dann 12 W statt 24 W; **Eigenes Netzteil** des FAM14 im Drawer (12 integriert, 0 über FSNT14) entscheidet stattdessen. Das FTS14KS liefert 8 W.
- **Katalog der Baureihe 14** hat jetzt 52 statt 33 Typen: jedes Reiheneinbaugerät aus Eltakos Betriebsanleitung für den RS485-Bus der Baureihe 14 (Stand 10/2026) und dem Gesamtkatalog (Kapitel 1 und 2), darunter FSR14M-2x, F4HK14, F2L14, FDG14, FD2G14, FSDG14, FRGBW14, BGW14, FWG14MS, FSM14-UC, FPLG14, FPLT14, FTS14FA, FTS14GBZ, DSZ14DRS-3x80A, DSZ14WDRS-3x5A, FLUD14, und das Zubehör auf der Schiene (FBA14, STE14, DS14, GBA14) mit eigener Rolle. Die Leistungswerte folgen der neueren Tabelle (F3Z14D 0,10 W, F4SR14-LED 1,00 W, FGW14-USB 0,30 W, FTS14KS 0,40 W); die Breiten dem Katalog (F4SR14-LED und FUD14/800W 2 TE, FTS14TG 2,5 TE, FTS14EM 2 TE); FSU14 belegt 8 Adressen und FMSR14 5. Was die Quellen nicht angeben, bleibt leer.
- **Eltako-Bus-Ansicht, Netzteile**: die Last jedes Netzteils rechnet der Server aus den dokumentierten Modulen; über Adressbereiche wie bisher und nach Einbaulage (der Abschnitt der Hutschiene zwischen Trennbrücken TB14 und Schrankende), sobald jedes Netzteil einen Einbauort hat. Die bisherige Ansicht der Netzteile nach Adressbereich je Gateway bleibt unter **Netzteile** erhalten und funktioniert wie bisher.
- **Nur dokumentieren** (das + eines unbekannten Senders) öffnet das Formular von **Gerät dokumentieren** mit eingetragener ID und der aus dem Telegramm geratenen Art, statt eine halbleere Zeile in die Liste zu setzen. Das Formular hat beschriftete Felder für Name, ID, Art, Typ, Ort, Funktion, Stromkreis und Sicherung (bei Aktoren), Einbaudatum und Versorgung und behält das Getippte, wenn sich die Art ändert.
- **Dokumentierte Sender** (Anlage → Geräte, „Nur dokumentieren“): Ein Eintrag ohne Namen zeigt **Unbenannter Sender** mit **Namen geben**, nicht mehr die ID als Namen; die ID steht unter dem Namen, die Art ist ein Tag mit kleinem Menü, und **nur dokumentiert** ist ein eigenes Tag. Die Spalte Signal sagt **nicht überwacht**. Das Menü ⋮ bietet **Als Gerät anlegen** (mit der Übergabe an Gerät hinzufügen) und **Eintrag entfernen**. Beide Ansichten (Alle und Funk) zeichnen den Eintrag gleich, der Name lässt sich durch Anklicken ändern.
- **Dokumentierte Sender** haben die Felder eines Geräts: **Stromkreis**, **Sicherung**, **Einbaudatum** und **Typ** (zum Beispiel PTM 215), neben Ort, Funktion und Versorgung. Sie sind Spalten der Tabelle, stehen im Ausdruck und in der CSV, und die Kachel „ohne Sicherung“ zählt keine Einträge mehr mit, die sich nicht ausfüllen ließen. Notizspeicher Version 6, mit Migration der Einträge.
- **Dokumentationsimport**: Ein Eintrag von Hand ist derselbe Eintrag, wenn seine Adresse gleich ist, auch wenn er seitdem benannt wurde; vorher entschieden Name und Adresse zusammen.
- **Panel**: Beim Verlassen und Zurückkehren bleiben Telegramme, Geräte und Dokumentation vom letzten Besuch stehen, während sie sich auffrischen, statt leerer Listen (nur in der Seite gehalten; ein Neuladen beginnt leer).
- **Als Gerät anlegen** (das + eines unbekannten Senders im Panel): Das nächste **Gerät hinzufügen** dieses Gateways geht direkt zur Art des Senders, ohne Menü und ohne die Liste der entdeckten Sender; die wahrscheinlichste Art ist vorgewählt (bei einem Druck- oder Loslass-Telegramm der Taster). Die Übergabe gilt einmal und verfällt nach zehn Minuten, danach ist das Menü wieder da.
- **Telegrammprotokoll**: Bei einem unbekannten Sender eines Druck- oder Loslass-Telegramms nennt der Hinweis zuerst das Taster-Profil (F6-02-01), vor selteneren wie dem Fenstergriff.
- **Anlage**: Jeder Gerätename, der ein Link ist (Sender-IDs, Verbindungen, Protokoll, Eltako-Bus), öffnet das Gerät in der Geräte-Ansicht, wie der Name in der Tabelle. Ein Gerät ohne Zeile dort öffnet weiter in der Tabelle der Anlage.
- **Anlage → Sender-IDs**: eine Tabelle statt zwei Listen. Die Liste des Pools nach Gerät (mit Suche, Chips und Sortierung) entfällt; die Pool-Karte, **Alle freigeben** mit Rückfrage und die Rückfrage einer einzelnen Freigabe bleiben über der Tabelle. Gesperrte IDs stehen in der Tabelle zuerst, der Reiter zeigt, wie viele warten.
- **Ansicht Sender-IDs**: Ein Gerät mit nur einer ID hat keinen Einklapp-Pfeil mehr; nur Geräte mit mehreren IDs lassen sich einklappen.
- **Ansicht Geräte**: Das ⋮-Menü eines eingerichteten Geräts hat *Entfernen*; es fragt wie beim Entfernen einer markierten Auswahl nach.
- **Ansicht Anlage**: Die Art-Chips stehen in der Zeile der Ansichtswahl, und die beiden Kacheln für fehlende Angaben sind eine kompakte Zeile.
- **Ansicht Übernahme**: Die beiden Zähler über der Geräteliste (in configuration.yaml, bereits eingerichtet) sind größer.
- **Ansicht Telegramme**: Der Chip *Nur unbekannte Sender* zeigt, wie viele unbekannte Sender der Puffer enthält.
- **Ansicht Telegramme**: Das Leeren der Liste liegt nicht mehr als eigenes Symbol neben dem Senden-Knopf, sondern im Menü (⋮) und lässt sich so nicht mehr versehentlich treffen.
- **Ansicht Anlage**: Drucken, die Ausgaben und der Notizen-Import liegen in einem Menü (⋮); die Art-Chips verlieren ihr Label und blenden eine Art ohne Geräte aus; die leeren Ortsfelder sind ruhig (ohne gestrichelten Rahmen) und die beiden Kacheln für fehlende Angaben sind kompakter.
- **Kopfzeile des Panels auf dem Handy**: Farbwahl und Integrations-Link bleiben neben dem Logo in der ersten Zeile (der Link als Symbol), die Ansichten scrollen darunter.
- **Geräteansicht**: Die Tabelle behält ihre Breiten: die Aktionsspalte hat eine feste Breite, die Überschrift *Zuletzt gehört* steht über den rechtsbündigen Werten, jede Zeile ist mindestens eine Höhe hoch, und ein nie gehörtes Gerät sagt das nicht mehr doppelt (die Statuspille tut es). Auf dem Handy ist die Kachel der Art kleiner.
- **Geräteansicht**: Ein Gerät ohne Telegramm im Puffer des Monitors (nach einem Neustart oder weil es selten sendet) zeigt, was seine Entitäten halten, bis zu zwei Werte, statt einer leeren Spalte; nicht verfügbare und unbekannte Werte entfallen, Diagnose und Einstellungen zählen nie.
- **Geräteansicht**: Die Statuschips (Alle Geräte, Eingerichtet, Unbekannt, Still, Schwaches Signal) zeigen, **wie viele Geräte** sie jeweils anzeigen würden, für das gewählte Gateway.
- **Geräteansicht**: Jedes Gerät hat eine **Kachel** für seine Art (Licht, Rollladen, Klima, Taster, Sensor, Zähler, virtuell), ein Fragezeichen für einen unbekannten Sender; der Tooltip nennt die Art. Ein Gerät, dessen Modell nicht feststeht (ein EEP, mehrere Geräte, etwa FUD14, FUD61 und FD62), nennt die Kandidaten unter dem Namen statt nichts.
- **Geräteansicht**: Die Knöpfe einer Zeile springen nicht mehr. Einlernen, Gerät in Home Assistant öffnen und Telegramme zeigen liegen in einem **⋮**-Menü; ein unbekannter Sender behält sein **+**, **Checkbox** und **Aufklapp-Pfeil** bleiben an ihrem Platz. Ein Gerät, das nichts davon anbietet (noch nicht gehört, keine Seite, keine Sender), hat kein Menü.
- **Geräteansicht**: Jedes Gerät zeigt eine **Statuspille** (aktiv, still, nicht gehört, deaktiviert, unbekannt) statt einer Mischung aus Tags; es zählt der erste Zustand, der zutrifft, ein deaktiviertes Gerät wird also nicht nach seiner Stille beurteilt. Der Text nennt den Zustand, die Farbe unterstützt ihn nur.
- Das **+** eines unbekannten Senders (Geräteansicht und Telegramm-Details) öffnet ein Menü: **Als Gerät anlegen** wie bisher oder **Nur dokumentieren**; das legt einen Eintrag mit dem Kennzeichen *nur dokumentiert* (Anlage → Geräte → Funk) mit ausgefüllter ID an und setzt den Cursor ins Feld Name. In Home Assistant entsteht nichts, und in keinen Aktor wird etwas eingelernt; eine schon notierte ID wird nicht doppelt angelegt.
- Der Katalogeintrag **Wippentaster** (EnOcean) und die Geräte-Dokumentation nennen jetzt die **EnOcean-Tastermodule PTM 210/215** (F6-02-01), die in vielen Tastern stecken.
- **Anlage-Ansicht neu gestaltet.** Vier Reiter (Geräte, Sender-IDs, Verbindungen, Protokoll); die Reiter Übersicht, Sender und Bus entfallen, ihre Tabellen stehen in den Ansichten des Reiters **Geräte**: **Alle Geräte**, **Bus**, **Funk** und **Virtuell**, oben umgeschaltet. Jede Zeile nennt ihre **Art** (Eltako-Bus, Funk Sensor, Funk Taster, Funk Aktor, Virtuell, Netzteil) als Kennzeichen, das die Ansicht dieser Art öffnet, und ein Gerät mit Sender-IDs aus dem Pool trägt **Sender 1, 2**, das zu seinen Zeilen im Reiter Sender-IDs springt (die Gerätenamen dort springen zurück).
  - **Alle Geräte**: der **Ort** sind drei Felder, die wie eines aussehen (Schrank, Reihe, Platz, gespeichert als „Schrank · Reihe · Platz“; älterer Freitext wird am Komma geteilt); Art-Chips, Filter für fehlenden Ort oder fehlende Sicherung (mit Zähler), Gruppieren nach Bereich oder Ort, ein Knopf **Nächstes ohne Ort** und ein Menü **Spalten**. Virtuelle Geräte haben keinen Ort und zählen beim Fortschritt nicht mit; Netzteile und von Hand notierte Einträge zählen mit.
  - **Bus**: gruppiert nach **Netzteil**. Ein Netzteil ist eine Kopfzeile mit Typ, Watt und den Bus-Adressen, die es versorgt, direkt bearbeitbar, mit Auslastungsbalken und Überlastwarnung; Adressen, die kein Netzteil versorgt, stehen in einer eigenen Gruppe; Kacheln zeigen doppelte Adressen, belegte und freie Adressen, die Gesamtleistung und den Zustand der Netzteile. Netzteile erscheinen auch in **Alle Geräte** mit Ort, Stromkreis, Sicherung und Notiz.
  - **Funk**: Funk-Geräte und von Hand notierte Einträge in einer Tabelle (Ort, Sender-ID, Sendet, **Versorgung**, Gehört zu, **Signal**: ein Punkt für das letzte Hören mit Stärke und „nur über Repeater“, und die **Verbindung**: was es steuert, was es steuert). **Gerät dokumentieren** (Name, ID, Art, Funktion) ersetzt den Editor der Weiteren Geräte; ein solcher Eintrag trägt *nur dokumentiert* und steht auch in **Alle Geräte**.
  - **Virtuell**: Pool-Nummer, Sender-ID, die Entitäten, denen ein virtuelles Gerät folgt, und die Aktoren, in die es eingelernt ist.
  - Geräte der Eltako-Baureihe 14 (FSR14, FUD14, FSB14 …) zählen als **Eltako-Bus**, auch ohne Adresse, und warten in der Gruppe *Noch keine Bus-Adresse* der Bus-Ansicht; ein Raumregler ist ein Funk-Sensor und kein Aktor, deshalb fragt der Reiter Verbindungen nicht, wer ihn schaltet.
  - **Sender-IDs**: die Tabelle der Gateway-Sender mit dem Sender-ID-Pool, wie bisher, eine Zeile je Sender.
  - **Verbindungen**: eine Karte je Aktor, je Sender oder eine **Matrix**; jede Verbindung nennt das andere Ende, die Rolle und die Herkunft (vergeben, angegeben, eingetragen), die Lernposition und den Stand. Ein Aktor ohne Verbindung ist markiert; Kacheln und Filter zeigen, was offen ist; **Sender testen**, **+ Verbindung**, **+ Aktor**, ein **+** in der Matrix und **Als Gerät notieren** für eine Wandschalter-ID ohne Gerät. Die Tabelle des früheren Reiters Taster (linke und rechte Wippe) ist dieser Reiter nach Sender gruppiert.
- **Farbe in der Anlage-Ansicht**: jede Art hat ihren Farbton (Eltako-Bus blau, Funk Sensor türkis, Funk Taster violett, Funk Aktor orange, Virtuell magenta, Netzteil schiefergrau) für das Kennzeichen, den Punkt der Art-Chips, einen Streifen am Zeilenanfang und die Karten der Verbindungen. Die Ansichten werden mit einem vollfarbigen gewählten Knopf umgeschaltet, die Kacheln tragen einen Akzent (grün, wenn alles in Ordnung ist, bernstein, wenn etwas offen ist), Gruppen- und Netzteilzeilen sind getönt, die Herkunft einer Verbindung hat eine eigene Farbe (vergeben orange, angegeben blau, eingetragen grün) in Kennzeichen und Filtern, und die Ereignisse des Protokolls sind farbige Kennzeichen.
- Die Gerätetabelle zeigt **nur die Spalten, die eine Art nutzen kann**: die Tabelle aller Arten hat Ort, Stromkreis, Sicherung, Einbaudatum und Notiz; wählst du oben eine Art, erscheinen die Spalten dafür (Bus-Adresse, Rückmelde-ID und Leistung am Bus für den Eltako-Bus; Versorgung für Funk-Geräte; Gehört zu und Revision, wo sie Sinn haben). Leere Felder tragen kurze Hinweise (Kreis, Sich., Adr.) statt des vollen Spaltennamens, und die Spaltengruppe *Bus und Funk* heißt nur noch *Bus*.
- Der Block zum **Einfügen aus einer Tabellenkalkulation** heißt jetzt **Mit einer Tabellenkalkulation bearbeiten**: drei nummerierte Schritte (Tabelle kopieren, ausfüllen, wieder einfügen) mit einem klaren Hinweis statt eines Beispiels mit Tabulatoren, und eine Zeile unter dem Textfeld, die vor dem Übernehmen sagt, wie viele Zeilen und Felder erkannt wurden.
- Speicher und Dokumentation: der Notizspeicher hat jetzt **Version 5**. Ein Netzteil des Busses hat Ort, Stromkreis, Sicherung und Notiz, ein von Hand notierter Eintrag eine Art, einen Ort und eine Versorgung (ältere Einträge werden migriert, die neuen Felder sind leer). Die Dokumentation nennt zu jedem Gerät, wann es zuletzt gehört wurde, das beste Signal und ob es nur über einen Repeater ankommt, und zu einem virtuellen Sensor die Entitäten, denen er folgt.
- **Telegrammprotokoll**: ein Telegramm, das Home Assistant an ein Gerät gesendet hat, wird nicht mehr so gezeigt, als käme es vom Gerät. Die Zeile trägt das Tag **Gesendet**, der Name lautet "an <Gerät>", die zweite Zeile "von <Sender-ID>".
- **Anlage**: Checkboxen haben ein eigenes Aussehen (klares Kästchen, Akzentfüllung mit Haken) und in der Gerätetabelle Abstand zum Zeilenstreifen. **Mit einer Tabellenkalkulation bearbeiten** ist jetzt ein Button **Tabellenkalkulation** in der Werkzeugleiste, der eine Karte mit den drei Schritten öffnet, statt eines aufklappbaren Blocks.
- **Tab Sender-IDs**: jedes Gateway zeigt Kacheln (in Gebrauch, gesperrt, frei, alle), die die Tabelle filtern, eine Leiste des Pools, die **nächste freie ID** mit Kopier-Knopf und einen kurzen Einleitungssatz (der lange Text steht im Tooltip). Die Tabelle ist sortierbar (Nummer, Gerät, Funktion, Rolle, Status), durchsuchbar, nach Funktion filterbar und **seitenweise (standardmäßig 25)**, mit Farbstreifen und einem Tag je Status; die Standardansicht zeigt belegte und gesperrte IDs, freie Nummern stehen unter *Frei* einzeln.
- **Tab Protokoll**: Ereignisse lesen sich als Sätze (das Gerät ist ein Link zu seiner Zeile, Ergebnisse des Sendertests sind Tags: bestätigt, nicht bestätigt, fehlgeschlagen), nach Tag gruppiert und mit relativer Zeit, filterbar nach Art und Zeitraum (heute, 7 Tage, alle), durchsuchbar, sortierbar, **seitenweise (standardmäßig 25)** und als CSV ladbar.
- **Tab Verbindungen**: ein Einleitungssatz (der lange Text steht im Tooltip); die Kacheln (Aktoren, ohne Verbindung, keine Antwort, nicht getestet, Antwort) filtern die Liste, die Quelle sind drei Schalter-Chips, Suche und Sortierung (Name, Status, Anzahl) sind neu, die Lernposition erscheint auf Wunsch, und die Aktoren werden **seitenweise (standardmäßig 25)** gezeigt.
- **Alle Geräte**: die Chips **Fehlt** und die Fortschrittszeile sind zwei Kacheln (ohne Ort, ohne Sicherung) mit Anzahl und "x von y erfasst", die die Tabelle filtern, daneben **Nächstes ohne Ort**; ein leerer Ort ist ein Knopf **+ Ort eintragen**, der die drei Felder erst beim Klick öffnet; die Tabelle ist **sortierbar** (Spaltenköpfe) und **seitenweise (standardmäßig 25)**; Platzhalter sind ausgeschrieben (Stromkreis, Adresse, Sicherung) und das Auswahlfeld *Gruppieren nach* ist gestaltet.

### Behoben

- **Installation, Protokoll**: Der Tab öffnete sich nicht, sobald ein Ereignis jünger als ein Tag war (die Anzeige „vor … s“ schlug fehl, der Tab blieb auf der vorigen Ansicht).
- **Installationsansichten**: Die Kacheln mit den Zahlen (Funk, Virtuell, Eltako-Bus) überlappen ihren Text nicht mehr. Die Symbolkachel der Geräteliste galt auch für sie und presste sie auf 36 px. In den Netzteil-Zeilen der Bus-Ansicht passt jetzt der ganze Platzhalter in die Adressfelder.
- **Telegrammprotokoll**: Die Richtung ist das eine Kennzeichen einer Zeile: grüner Pfeil für empfangen, blauer für gesendet. Der blaue Balken und die Tönung bei gesendeten Zeilen entfallen; ein Balken markiert nur noch eine Warnung: ein gesendeter Befehl ohne Antwort innerhalb von 3 s bekommt einen gelben Balken und ein Tag.
- **Übernahme**: Nach der Übernahme landet die Ansicht immer bei Schritt 3 (Alte Integration ablösen). Hat die alte Integration für die Geräte keine Entitäten mehr, sagt Schritt 3 das, statt dass die Ansicht auf Schritt 1 zurückfällt.
- **Zuletzt gehört** bleibt über einen Neustart erhalten: der Wert kommt aus den gespeicherten Signaldaten und nicht mehr nur aus dem standardmäßig deaktivierten Sensor *Zuletzt gesehen*. Ein Gerät, das seit dem Start von Home Assistant nicht gesendet hat, gilt nicht mehr als nie gehört.

## 1.5.0 - 2026-11-02

### Neu

- **Darstellung** des Panels (Paletten-Schaltfläche in der Kopfzeile): drei Farbschemata (Ozean, Wald, Graphit), je hell und dunkel; hell, dunkel oder wie Home Assistant; Schriftgröße klein, normal oder groß (12,6, 14 oder 16 px, alle Größen im Panel ziehen mit). Die Wahl wird pro Home-Assistant-Benutzer gespeichert und im Browser zwischengespeichert.
- Die Tabellen der Gruppen Sender und Bus sind **direkt bearbeitbar**: Bus-Adresse und Rückmelde-ID (Gateway-Sender, Bus), Ort (Taster, Funk-Sender), **Gehört zu** (Funk-Sender) und Leistung am Bus (Bus). Ein Gerät mit mehreren Sendern zeigt in jeder Zeile denselben Wert, und alle Zeilen folgen einer Änderung.
- **Mehrere Netzteile** am Bus: jedes mit Typ, Watt und, wenn du willst, den Bus-Adressen, die es versorgt. Der Ausdruck zeigt die Auslastung jedes Netzteils mit Bereich, die Gesamtsumme und Adressen, die kein Netzteil versorgt. Der Notizen-Speicher hat jetzt Version 3 (ein einzelnes Netzteil der Version 2 wird übernommen).
- Die Tabelle **Eltako-Bus** führt die Bus-Adressen 1 bis 126 (eine je Kanal) mit zusammengefassten freien Bereichen und meldet doppelt vergebene Adressen. Die Leistung eines Typs kommt, wo du keine eingetragen hast, aus der Eltako-Planungshilfe (07/2014); als Netzteil gelten die 12 W des FAM14. Typen, die die Planungshilfe nicht kennt (neuere Geräte), haben keinen Wert.
- Neues Gerätefeld **Gehört zu**: Funk-IDs mit gleichem Wert (ein Raumregler wie der FUTH55 sendet unter mehreren IDs) stehen in der Tabelle **Funk-Sender** des Ausdrucks als ein Block, jede ID mit dem, was sie sendet.
- Tabelle **Eltako-Bus** im Ausdruck: jedes Gerät mit Bus-Adresse, nach Adresse, mit der Leistung, die es vom Bus nimmt (von Hand aus dem Datenblatt eingetragen), der Summe und der Auslastung des Bus-Netzteils, das du in den Details des Gateways einträgst. Geräte am Bus, die Home Assistant nicht kennt, sind Einträge von Hand mit Bus-Adresse, Rückmelde-ID und Watt.
- Der Ausdruck hat drei weitere Tabellen: **Gateway-Sender** (Sender-Nr. 0 bis 127 des Funk-Pools, freie Nummern zusammengefasst, mehrere Sender eines Geräts verweisen aufeinander, darunter die von Hand eingetragenen Sender mit den Nummern ihres Geräts), **Taster** (jeder Wandtaster mit den Aktoren auf linker und rechter Wippe) und **Funk-Sender** (Geräte, die nur senden, und die Einträge von Hand). Neue Felder **Bus-Adresse** und **Rückmelde-ID** je Gerät und **Sender-Tabellen-CSV**.
- Eine **Checkliste für ein neues Gateway** im Ausdruck: jeder vergebene Sender, der neu einzulernen ist, wenn ein Funkgateway mit anderer Base-ID übernimmt.
- **Verbindungen als CSV**, und der JSON-Export ist jetzt Version 2 (typisierte Felder, Verbindungen, Protokoll); der Import liest weiter Version 1.
- **Verbindungen** im Reiter Installation: wer in welchen Aktor eingelernt ist, nach Aktor oder nach Sender, jede als vergeben, angegeben (Wandschalter-Option) oder von dir eingetragen markiert, mit Einlernzeitpunkt, letztem Sendertest und Lernposition. Der JSON-Export enthält sie, der Import übernimmt eingetragene Verbindungen und Lernpositionen.
- Der neue Reiter **Installation** im Panel: Geräte nach Bereich oder Ort, eine Tabelle mit typisierten Feldern (Ort, Stromkreis, Sicherung, Eingebaut, Revision, Versorgung, Notiz), direkt bearbeitbar, für eine Auswahl oder aus einer Tabellenkalkulation eingefügt, und das Ereignisprotokoll.
- Die Installation führt ein **Ereignisprotokoll** pro Gateway: Geräte hinzugefügt oder entfernt, Sender vergeben oder entfernt, Einlernen, Sendertests und Importe.
- Beim Import von Notizen in ein **getauschtes Gateway** (andere Base-ID) bietet das Panel an, das eine Gateway der Datei ohne Treffer dem hier eingerichteten zuzuordnen.

### Geändert

- Das Panel nennt den Grund, wenn ein Gateway hinter der Proxy-App keinen Status zeigt: **Proxy-Status nicht erreichbar** (Abfrage fehlgeschlagen) oder **listet dieses Gateway nicht** (der Status der App hat kein Gateway auf unserem Port). Die Diagnose enthält die Status-URL (Host maskiert) und den letzten Fehler, der erste Fehlschlag steht im Debug-Log.
- Die Reiter der Ansicht Anlage sind echte Reiter (unterstrichen) in zwei Ebenen, der Umschalter zwischen Tabelle und ID-Verwaltung entfällt. Die erste Gruppe heißt jetzt **Geräte** (Übersicht, Tabelle); die Gruppierung nach Bereich oder Ort ist ein Segment-Schalter, jedes Gateway ist eine Karte mit Gerätezahl, und ein Gateway ohne Geräte bietet einen Button zur Integration.
- Tabelle **Geräte**: eine Fortschrittszeile (Geräte mit Ort), Spalten in Gruppen zum Ein- und Ausblenden (Ort und Sicherung, Bus und Funk, Wartung; pro Browser gemerkt), und eine falsche Bus-Adresse oder Wattzahl wird unter dem Feld genannt und nicht gesendet.
- **Sender-IDs** ist kein eigener Reiter mehr, sondern der **Sender-ID-Pool** über der Tabelle unter Anlage → Sender → Gateway-Sender, immer sichtbar und einklappbar (Pool-Karte, wer welche ID nutzt, Freigabe gesperrter IDs, auch aus einer gesperrten Zeile der Tabelle). `?view=senders` und eine gespeicherte Ansicht Sender-IDs öffnen sie dort.
- Der Reiter **Installation** heißt jetzt **Anlage** und ist der Ort für Dokumentation und Verwaltung, in Gruppen: Anlage (nach Bereich, Geräte), Sender (Gateway-Sender, Taster, Funk-Sender), Bus (Eltako-Bus, Netzteile), Verbindungen, Protokoll. Die Tabellen der Gruppen Sender und Bus zeigen dieselben Zeilen wie der Ausdruck; Netzteile und Einträge von Hand sind aus den Gateway-Details dorthin umgezogen, und die Ausgabe-Knöpfe sind ein Menü **Ausgabe**.
- Die Ansicht **Übernahme** zeigt den Wechsel zwischen Übernahme und Berichten sofort und beim Laden einen animierten Platzhalter; die Berichte sind erreichbar, ohne auf die Übernahme zu warten.
- **Gehört von** und die gehörten unbekannten Sender **überstehen einen Neustart**: wie jedes Gateway ein Gerät hört und die neuesten 100 unbekannten Sender bleiben erhalten (höchstens einmal pro Minute geschrieben).
- Der Ausdruck ist **eine Seite mit Abschnitten**, die du oben ein- oder ausschaltest (Übergabe, Schaltschrank, Verbindungen, Checkliste, Sender-IDs, Protokoll); sie ersetzt das eigene Schaltschrank-Blatt.
- Die Notizen eines Geräts sind jetzt typisierte Felder (Speicherversion 2, beim ersten Laden aus Version 1 überführt); Exporte und der Import enthalten alle.

### Behoben

- Der Import von Notizen eines **Zweikanal-Aktors** legte die Notiz des zweiten Kanals unter dem Schlüssel des ersten ab; Exporte tragen jetzt den Schlüssel jedes Geräts.

## 1.4.1 - 2026-11-01

### Behoben

- Das **⋮-Menü** der Geräteansicht mit der Installationsdokumentation (Drucken, Schaltschrank-Blatt, CSV, JSON, Import) wurde nur auf schmalen Bildschirmen angezeigt. Es erscheint jetzt auch am Desktop.

## 1.4.0 - 2026-11-01

### Neu

- **Sender testen** gilt jetzt auch für Dimmer: der Zentralbefehl wiederholt die aktuelle Helligkeit, der Wipptaster wird übersprungen, weil ein Druck sie ändern könnte. Rollläden bleiben ungetestet, denn jeder Befehl bewegt sie.
- **Aufnehmen und melden** bei unbekannten Sendern: hört den Sender zuerst 60 Sekunden ab, damit die Telegramme dessen, was du mit dem Gerät machst, im Gerätebericht stehen.
- Die **Reparatur „Profil passt nicht“** greift auch bei Werten außerhalb der Bereiche eines Standardprofils und nennt Geräte, für die Telegramme des unerwarteten Typs typisch sind.
- **Notizen aus JSON importieren** im Menü der Geräteansicht: liest die Notizen und weiteren Geräte eines früheren Dokumentations-Exports wieder ein (zugeordnet über Base-ID und Geräteadresse) und füllt nur Leeres. Geräte werden nie importiert.
- Die Details eines Gateways bieten an, die **Notizen gelöschter Geräte zu entfernen**; sonst bleiben sie, falls das Gerät zurückkehrt.
- **Schaltschrank-Blatt** im Menü der Geräteansicht: ein dichter Ausdruck im Querformat, eine Tabelle pro Gateway, für den Verteiler.
- Screenshots des Seitenleisten-Panels (Beispieldaten) in beiden READMEs.
- **Weitere Geräte** in den Details eines Gateways: direkt eingelernte Taster, Geräte anderer Systeme und alles andere, was Home Assistant nicht sieht, lassen sich eintragen (Name, ID, Funktion). Sie stehen in Ausdruck, CSV und JSON der Installationsdokumentation.
- Die gedruckte **Installationsdokumentation** beginnt bei mehreren Gateways mit einer Übersichtsseite, eine Zeile pro Gateway.
- Die **Installationsdokumentation** nennt auch die unbekannten Sender, die ein Gateway seit dem Neustart gehört hat (nicht eingerichtet), und behält das Ergebnis des letzten **Sender testen** über Neustarts hinweg.
- **Notizen** für die Installationsdokumentation: ein Feld in den Details jedes Geräts und jedes Gateways (Ort, Klemme, Sicherung, Batteriedatum). Sie werden pro Gateway gespeichert, gehören zur Geräteadresse und stehen in Ausdruck, CSV und JSON.
- **Installationsdokumentation** in der Geräteansicht (⋮-Menü): drucken (ein Gateway pro Seite) oder als CSV bzw. versioniertes JSON laden. Sie nennt Geräte mit Adresse, EEP, Bereich und Wandschalter, die vergebenen Sender mit Art des Einlernens und Ergebnis des Sendertests sowie den Sender-ID-Pool mit blockierten IDs und sagt, was Home Assistant nicht wissen kann.
- **Sender testen** in den Details eines Schaltaktors: sendet seinen aktuellen Zustand nacheinander über jeden Sender (es ändert sich nichts) und zeigt, welche Sender er beantwortet.
- **Gehört von** in den Details eines Geräts: bei mehreren Gateways jedes Gateway mit letztem Signal und Telegrammzahl, das stärkste markiert; ein Gerät, das nur über einen Repeater ankommt, trägt den Hinweis **nur über Repeater**.
- **Reparatur „Profil passt nicht“**: ein Gerät, dessen letzte 5 Telegramme hintereinander zu keinem seiner Profile passen, löst eine Reparatur aus (es wurde sehr wahrscheinlich mit der falschen Art angelegt); ein passendes Telegramm hebt sie auf.
- **Gerät melden** bei unbekannten Sendern in den Telegramm-Details: kopiert die letzten Telegramme des Senders (bis zu 60) mit ersetzten IDs, Gateway und Zeiten und öffnet das neue Formular für Geräteanfragen auf GitHub. Im Link stehen keine Daten.
- **Spalte „Hardware“** in der Liste der unterstützten Geräte: ein ✓, wo das Repository einen echten Mitschnitt dieses Modells enthält (`tests/fixtures/captures/<Modell-ID>.jsonl`).
- **`scripts/capture_to_fixture.py`** macht aus einem Mitschnitt eine anonyme Testdatei (IDs, Gateway-Namen und Zeiten ersetzt, Telegrammdaten bleiben), damit aus einem Fehlerbericht ein Regressionstest werden kann.
- **Quality Scale**: eine Selbsteinschätzung nach der Integration Quality Scale von Home Assistant (Bronze bis Platin) in [docs/quality_scale.de.md](docs/quality_scale.de.md), auch auf Englisch.

### Geändert

- Die gedruckte **Installationsdokumentation** wiederholt Tabellenköpfe auf jeder Seite und hält Überschriften bei ihrer Tabelle.
- **Signalkurve** in der Geräteliste ist größer (96 × 32 px; die globale Icon-Größe von 20 px staucht sie nicht mehr) und passt sich den Daten an: der Bereich ist mindestens 16 dB breit, ein gleichmäßiger Sender zeigt also keine flache Linie mehr. Die Linie für schwaches Signal erscheint nur, wenn sie im Bereich liegt.

## 1.3.0 - 2026-10-26

### Geändert

- **Telegramm-Details** zeigen zuerst die Daten, darunter das vorherige Telegramm, die geänderten Bytes sind in beiden markiert (dazu eine Zeile wie „Byte 3 geändert: 44 → 49“). Die Metadaten stehen in zwei Zeilen, das Signal entfällt (es steht in der Zeile), und die Aktionen sind Icon-Buttons.
- **Geräteliste**: breitere Spalte für die Werte, schmalere für Bereich und Entitäten, und „Gerät hinzufügen“ ist ein runder, gefüllter Plus-Button (der Name bleibt als Tooltip).
- **Signalkurve** in der Geräteansicht übernimmt die Farbe des letzten Werts, endet in einem Punkt und zeigt die Linie für schwaches Signal (-85 dBm).
- **Suche** zeigt das Kürzel `/` als kleine Taste im Feld statt als Tooltip über dem ganzen Label; die Spaltenköpfe verlieren den Sortier-Tooltip (der Sortierzustand bleibt im Pfeil und für Screenreader erhalten).
- **Telegrammliste** kann einen unbekannten Sender mit einem Klick aus der Discovery ausblenden (Button in der aufgeklappten Zeile). Wieder anzeigen unter Konfigurieren → Ausgeblendete Sender.
- **Könnte sein** (Profil-Vorschläge für unbekannte Sender) steht jetzt unter dem Wert und zeigt zwei Profile plus „+n“ (alle im Tooltip), in der Telegrammliste und der Geräteansicht.
- **Sender-IDs** zeigen statt der Dezimal-ID die Nummer ab der Basis-ID (1 bis 127), in der Liste und auf der Karte.
- **Geräte** zeigen Status-Chips, Suche und Filter in einer Zeile.
- **Sender-IDs** zeigen Status-Chips, Suche und Sortierung in einer Zeile.
- **Telegrammliste** setzt einen kleinen Punkt vor den Sender: gefüllt für bekannte Geräte, hohl für unbekannte.
- **Signalbalken** in der Telegrammliste und der Geräteansicht sind nach Stärke eingefärbt: grün, gelb oder rot.
- **Telegrammliste** hinterlegt gesendete Telegramme leicht farbig und markiert sie mit einem Akzentbalken, damit sie sich von empfangenen abheben.
- **Suche in der Übernahme** findet jetzt auch Labels, in der Vorschau der Prüfung (Gerät und Entitäten) und in den Berichten.

## 1.2.0 - 2026-10-24

### Geändert

- **Übernahme in drei Schritten statt vier:** Auswählen, Prüfen & übernehmen, Alte Integration ablösen. Die bisherigen
  Schritte „Umstellen“ und „Aufräumen“ entfallen, ebenso **Übernahme abschließen**.
- **Prüfen zeigt, was mitkommt:** zu jeder angehakten Option listet die Vorschau je Gerät die tatsächlichen Werte
  (Bereich, Labels, Namen, Symbole, ausgeblendet/deaktiviert, Sprachsteuerung), auch je Entität. Schon eingerichtete
  Geräte werden im selben Schritt ergänzt.
- **Alte Integration ablösen:** zuerst wählst du, wie die alten Entity-IDs behandelt werden: behalten (alte Integration
  löschen, den neuen Entitäten die alten IDs zurückgeben, `eltako:` entfernen) oder die neuen verwenden (Fundstellen mit
  alten IDs umstellen, löschen, entfernen). Die Schritte ergeben sich aus der Wahl.
- **Berichte:** ein Bericht je Übernahme, jederzeit unter **Berichte** in der Ansicht Übernahme erreichbar, zu öffnen und
  zu löschen. Die bisherigen Berichte werden migriert (einer je Gateway und Tag).

### Behoben

- **Alte IDs wiederherstellen** benennt keine neue ID mehr um, die eine Automation, ein Skript, eine Szene oder ein
  Dashboard schon nutzt.
- **Virtuelle Taster** (alte Buttons) bekommen einen Berichtseintrag und werden von „Schon eingerichtete Geräte“
  ergänzt.
- Ein Gerät, das übernommen wird, nachdem die alten Entitäten weg sind, bekommt trotzdem einen Bericht.

## 1.1.1 - 2026-10-24

### Geändert

- **Entdeckt-Karte:** Der Dialog nennt, wie viele Sender nach Typ gehört wurden (zum Beispiel „15 Sensoren (A5), 9 Taster
  (F6)“), und verlinkt aufs Gateway, statt zehn IDs aufzulisten.

## 1.1.0 - 2026-10-23

### Geändert

- **Entdeckte Geräte:** Ein Gateway, das unbekannte Sender gehört hat, zeigt eine Karte unter Einstellungen → Geräte &
  Dienste → Entdeckt (mit der Anzahl der Sender) statt einer Benachrichtigung. Die Karte listet sie auf und weist auf
  **Gerät hinzufügen → Entdeckte Geräte** am Gateway hin; sie verschwindet, wenn nichts mehr zu entdecken ist.

## 1.0.2 - 2026-10-23

### Behoben

- **PioTek MGW-ETH hinter dem Device Proxy:** Das Gateway wird nicht mehr unter seiner eigenen Adresse als entdeckt
  angeboten, sobald ein MGW-ETH über die App eingerichtet ist (es bedient nur eine Verbindung, die hält die App).

## 1.0.1 - 2026-10-23

### Behoben

- **Device Proxy, Base-ID:** Antwortet das Gateway hinter der App beim Einrichten nicht auf das Lesen der Base-ID, nimmt die
  Integration sie aus dem Status der App, statt danach zu fragen.

## 1.0.0 - 2026-10-23

### Neu

- **Ansicht Sender-IDs:** eine Suche (Gerätename, Profil, ID mit oder ohne Bindestriche, dezimal), Chips für Alle /
  Zugewiesen / Gesperrt und eine Sortierung (Gesperrte zuerst, Name, Sender-ID). **Alle freigeben** gibt jede gesperrte
  ID frei, die die Liste zeigt, nach einer Rückfrage.
- **Entdeckung über den Device Proxy:** Nennt die App das Modell eines Gateways in ihrer Meldung (`model`, zum Beispiel
  `fam_usb`), entfällt die Frage nach dem Modell; ohne bleibt es beim Erraten am Namen.

### Geändert

- **Filter im Panel:** Der Gerätestatus ist eine Chip-Reihe statt eines Dropdowns im Filtermenü, und „Nur unbekannte
  Sender“ ist ein Schalter neben RX / TX in der Telegrammansicht. **Filter** erscheint in der Geräteansicht nur, wenn
  mehrere Gateways oder Bereiche zur Auswahl stehen.

### Behoben

- **Nachlieferung über den Device Proxy, Binärsensoren:** Kontakte, Fenstergriffe, Bewegungs- und Regensensoren nehmen die
  nachgelieferten Telegramme aus der Zeit des Neustarts in einem Zug auf: der Zustand wird einmal geschrieben, wenn die
  Nachlieferung durch ist. Eine zwischendurch geöffnete und geschlossene Tür lässt den Sensor nicht mehr mehrfach
  umschalten (und Trigger feuern), und ein Zustand, der am Ende dort steht, wo er begann, löst nichts aus.
- **Nachlieferung über den Device Proxy, Taster:** nachgelieferte Tasterdrücke lösen keine Taster-Ereignisse aus. Gesten
  werden live gemessen, ein nachgelieferter Druck wurde beim Neustart zum kurzen Druck (zwei zum Doppelklick) und
  startete Automationen mit einem Druck von vor Minuten.

## 0.1.13 - 2026-10-23

### Neu

- **Wetterstation:** ein Sensor „Sonnigste Seite“ (Süd, Ost, West oder keine Sonne unter 2 klx auf allen Seiten) und ein
  Sensor „Regen kürzlich“, der nach dem Regen noch einige Minuten an bleibt, damit Rollläden und Markisen nicht auf eine
  nasse Fläche zurückfahren. Die Minuten sind eine Geräteeinstellung (Vorgabe 15, 0 = kein Nachlauf).
- **Blueprint „Rollläden nach der Sonne beschatten“:** fährt Rollläden in eine Beschattungsposition, wenn die Sonne auf einer
  Seite stark genug bleibt, und zurück, wenn sie eine Weile schwach war; auf Wunsch nur bei Wärme; lässt Rollläden in Ruhe,
  deren „Automatikmodus“ Aus ist, und solche, die du von Hand bewegt hast.
- **Blueprint „Rollläden und Licht bei Dämmerung“:** schließt Rollläden und schaltet Licht ein, wenn es eine Weile dunkel
  ist, öffnet und schaltet morgens aus; der „Automatikmodus“ eines Rollladens entscheidet (Abends und Beides am Abend,
  Morgens und Beides am Morgen, Aus nie), mit frühesten Zeiten, damit eine Gewitterwolke am Mittag nichts schließt.
- **Blueprint „Wetterwarnung bei offenem Fenster“:** eine Meldung (eine Aktion deiner Wahl), wenn es zu regnen beginnt oder
  weht, während ein Fenster offen ist, und wenn ein Fenster bei schlechtem Wetter geöffnet wird. Es bewegt nichts.

### Geändert

- **Wetterstation:** Dämmerung und die drei Sonnensensoren zeigen ganze Lux (die Dämmerung nicht mehr „999,0 lx“), der
  Wind eine Nachkommastelle. Regen ist ein einfacher Ein/Aus-Sensor mit den Anzeigen „Regen“ / „Kein Regen“ und den
  Regen-Symbolen, kein „Feuchtigkeits“-Sensor (Leck) mehr, den Assistenten als Leckalarm behandeln könnten. Die Einheit
  des Winds (m/s, km/h, Beaufort) ist die Anzeigeeinheit der Entität in Home Assistant.
- **Geräteseite:** ein Gerät ohne benannten Typ nennt sein EEP einmal, als Modell, nicht noch einmal als Modell-ID.
- **Panel, Ansicht Geräte:** die Kästchen haben eine eigene Spalte, so fluchten Name und ID, und „Alle auswählen“ steht
  im Tabellenkopf darüber (auf dem Handy bleibt es in der Zeile über der Liste). Die Leiste der gewählten Geräte
  ersetzt die Zeile mit der Anzahl, die Symbole der Zeilen sind gedämpft, bis der Zeiger über der Zeile steht, und
  „nicht gehört“ ist abgeschwächt.

## 0.1.12 - 2026-10-23

### Neu

- **Panel, Ansicht Geräte:** mehrere Geräte auswählen (ein Kästchen je Zeile, „Alle auswählen“ für die gefilterten) und
  mit einer Leiste einen **Bereich** setzen, **Labels** hinzufügen oder entfernen (neue Labels lassen sich gleich
  anlegen), sie **deaktivieren** oder **aktivieren** oder in einem Zug aus Home Assistant **entfernen**. Bereich, Labels
  und Deaktivieren sind die von Home Assistant, sie erscheinen also auch auf der Geräteseite. Das Entfernen fragt vorher
  nach, lädt das Gateway nur einmal neu und lässt die Sender-IDs der Geräte gesperrt, bis das Abmelden unter Sender-IDs
  bestätigt ist.
- **Panel:** die Labels eines Geräts stehen unter seinem Namen, ein deaktiviertes Gerät trägt eine Markierung, und die
  Suche findet Labels.

## 0.1.11 - 2026-10-23

### Neu

- **Automatikmodus der Cover:** Jedes Cover hat eine Auswahl „Automatikmodus" (Aus, Morgens, Abends, Beides; bis zur Wahl
  Beides) für deine eigenen Automationen, wie in der alten Eltako-Integration. Sie fährt nichts selbst und bleibt über
  Neustarts erhalten.
- **Zustand und Fahrzeit der Cover:** FSB-Cover haben einen Sensor „Zustand" (fährt auf, fährt zu, offen, geschlossen,
  gestoppt) und einen Sensor „Fahrzeit" (mit der Richtung) aus den Bestätigungstelegrammen des Aktors.
- **Panel:** ein Integrations-Link in der Kopfleiste und in den Gateway-Details, direkt zum Eintrag dieses Gateways.

### Geändert

- **Routing der Cover:** Ein Cover fährt über einen Sender, den Controller oder den Richtungstaster. „Beide" entfällt:
  Es sendete zwei Telegramme je Fahrt, und der Richtungstaster stoppt eine Fahrt bei erneutem Druck in dieselbe Richtung.
  Bestehende Cover mit „Beide" behalten den Controller (den Richtungstaster, wo sie keinen Controller haben).
- **Übernahme:** Ein Taster (F6-02-01, F6-02-02) der alten Plattform binary_sensor wird ein Taster-Kontakt mit seiner
  Geräteklasse und dem Invertieren, kein Knopf. Die Übernahme bleibt bei der Auswahl, wenn nichts mehr umzustellen ist,
  und sagt das in Schritt 3.

### Behoben

- **Tasten von Taster und Wandtaster:** Die eingeklappten Bereiche zeigen die genutzte Taste (oder den Standard)
  vorausgewählt, statt gar keine Auswahl.
- **Geräteseite:** Die EEP steht einmal, als Modell-ID, nicht zusätzlich im Modell.

## 0.1.10 - 2026-10-23

### Geändert

- **Links zum Gerät im Panel:** Ein aufgeklapptes Telegramm hat den Knopf „Gerät im Panel", und der Gerätename einer
  Sender-ID-Gruppe ist ein Link: beide öffnen die Zeile des Geräts in der Geräteansicht. „Gerät öffnen" heißt jetzt
  „In Home Assistant öffnen".
- **Aussehen des Panels:** Logo und Reiter richten sich am Inhalt aus (höchstens 1200 px, zentriert) statt an den
  Fensterrändern, wie in der Device-Proxy-App.
- **Sender-IDs:** Der Kopf der Ansicht ist klarer: Kacheln für freie, zugewiesene und gesperrte IDs und die nächste
  freie ID (mit Kopieren-Knopf), ein Balken für den belegten Anteil, ein Hinweis, wenn gesperrte IDs auf ihr
  Teach-out warten (mit Knopf zur ersten), eine Pool-Karte, deren Zeilen ihren ID-Bereich nennen, und eine Zeile
  unter der Karte mit ID, Nummer, Status und Gerät des gewählten Felds. Die Legende zeigt die Zahlen.

## 0.1.9 - 2026-10-23

### Neu

- **Gerätemodell:** Ein Gerät einer Art, die mehrere Eltako-Modelle teilen (Schaltaktoren,
  Dimmer, Rollladenaktoren, Heizungsaktoren, Zähler ...), hat ein optionales Feld „Modell": FSR14-4x,
  FUD61NPN-230V ... wählen oder ein anderes eintippen. Es erscheint im Telegramm-Monitor und auf
  der Geräteseite und ändert kein Verhalten. Neue Version der Gerätedaten (Schema 4, Migration
  inklusive).

### Geändert

- **Telegramm-Monitor:** Das Funktelegramm verrät das Modell nicht, deshalb zeigt der Monitor nicht
  mehr das erste Beispiel der Art (FSR61 bei einem FSR14). Ohne gewähltes Modell steht dort die
  Liste der möglichen Modelle, die Geräteseite zeigt nur das EEP.
- **Wetterstation:** Das Beispiel FWG14 heißt FWG14MS.
- **Geräteansicht:** Die Zeile eines eingerichteten Geräts klappt an Ort und Stelle auf und zeigt alles,
  was wir kennen: Identität (Modell, EEP, Bereich, Gateway, ID), Funk (zuletzt gehört, Signal mit
  Minimum und Maximum, Repeater-Stufen, Telegrammzahl, erwartetes Intervall), letzte Werte,
  Sender-IDs mit Art des Einlernens, Befehlsstatistik (gesendet, bestätigt, Antwortzeit),
  Einstellungen und Entitäten mit ihren Zuständen. Mehrere Zeilen können offen sein, sie bleiben
  aktuell, und die Liste behält ihre Reihenfolge, solange eine offen ist. Ein Klick auf die Zeile
  springt nicht mehr zu den Telegrammen: Das macht der Filter-Knopf der Zeile.
- **Geräteansicht:** Das Modell eines Geräts wird in seiner aufgeklappten Zeile gesetzt: Dropdown mit den
  Modellen seiner Art, „Nicht angegeben" oder „Anderes Modell …" zum Eintippen. Es wird sofort
  gespeichert (der Eintrag des Gateways lädt neu, wie nach jeder Änderung an einem Gerät).
- **Geräteansicht:** Die aufgeklappte Zeile zeigt ihre Werte als kleine Kacheln und Tabellen auf Weiß, wie die
  Statistiken der Device-Proxy-App; der Anteil bestätigter Befehle ist ein farbiger Chip.
- **Aussehen des Panels:** Das Panel sieht aus wie die Device-Proxy-App: deren Seitenfarbe, größere
  abgerundete Karten mit weichem Schatten und Reiter als Pillen. Die Akzentfarbe ist immer das Blau
  der App und folgt nicht mehr der Primärfarbe eines Home-Assistant-Themes (hell und dunkel folgen
  ihm weiterhin).
- **Geräteansicht:** Die Liste öffnet immer nach Namen sortiert; eine angeklickte Spaltensortierung
  gilt, bis das Panel geschlossen wird, und wird nicht mehr gemerkt.
- **Telegramm-Monitor:** Ein aufgeklapptes Telegramm hält die Liste an: neue Telegramme warten (die
  Live-Anzeige zeigt „Pausiert" mit ihrer Anzahl), solange du die Details liest, und erscheinen,
  wenn du das letzte geöffnete zuklappst. Eine selbst gesetzte Pause bleibt, bis du sie aufhebst.

## 0.1.8 - 2026-10-22

### Geändert

- **Device Proxy:** die Gateway-Karte und der Verbindungssensor des Gateways zeigen, ob das
  Ausweich-Gateway der App einspringt und ob es bereit ist.

### Behoben

- **Panel:** das EnOcean-Panel bleibt nicht mehr leer, wenn eine seiner Dateien einmal nicht
  lädt (beim Start von Home Assistant oder bei einem Proxy-Aussetzer): die Teile laden mit
  Wiederholungen, und scheitern sie dennoch, zeigt das Panel eine Meldung mit Neu-laden-Knopf.

## 0.1.7 - 2026-10-22

### Geändert

- **Panel, Übernahme:** was aus der alten Integration mitkommt, wird einzeln gewählt (Bereich,
  Labels, Sprachsteuerung, eigene Namen, Symbole, ausgeblendet / deaktiviert), mit der Zahl der
  betroffenen Geräte; anfangs ist nichts gewählt, die Wahl merkt sich der Browser. Eigene Namen,
  Symbole und ausgeblendet / deaktiviert sind neu.
- **Panel, Übernahme:** schon eingerichtete Geräte sind in Übernehmen keine Liste mehr, sondern
  ein Hinweis, der zu Prüfen führt; Prüfen ist die Übersicht aller eingerichteten Geräte: was
  ihnen aus der alten Integration noch fehlt, die Fundstellen ihrer alten IDs, eine Ansicht nach
  Fundstelle mit Links in die Editoren, Filter Noch verwendet und Erledigt, und Neu prüfen.
- **Panel, Übernahme:** Übernehmen fragt zuerst nach: eine Bestätigung zeigt Geräte, Entitäten
  und die danach umzustellenden Fundstellen, die gewählten Optionen und jede alte Entity-ID neben
  der, die die neue Entität voraussichtlich bekommt; erst Jetzt übernehmen legt die Geräte an.
- **Panel, Übernahme:** vier Schritte, Auswählen, Mitnehmen (die Optionen als Kacheln mit ihren
  Werten, dazu die Vorschau alter und neuer IDs), Umstellen (nach Fundstelle, nach Gerät mit dem,
  was jedes Gerät in der alten Integration war, und der Bericht als Tabelle) und Aufräumen (eine
  Checkliste aus dem aktuellen Stand); Übernahme abschließen blendet den Tab aus.
- **Übernahme:** die Zuordnung alter zu neuen Entity-IDs speichert die Integration selbst, der
  Bericht bleibt deshalb nach dem Löschen der alten Integration abrufbar; Übernahme-Bericht in
  der Ansicht Geräte öffnet ihn.
- **Übernahme:** Alte IDs wiederherstellen gibt den neuen Entitäten die alten Entity-IDs zurück,
  sobald die alte Integration gelöscht ist; Verweise laufen dann unverändert weiter.
- **Panel, Sender-IDs:** die Karte des Pools nutzt die volle Breite und beschriftet jede Reihe
  mit dem letzten Byte ihrer ersten ID.

### Entfernt

- **App EnOcean Proxy:** nicht mehr unterstützt, die Proxy-App ist der Device Proxy. Entfallen
  sind ihr Discovery-Format mit nur einem Gateway und der Reparaturhinweis für ihre alten
  Versionen; die Texte nennen nur noch den Device Proxy.

### Neu

- **Device Proxy, Ersatz-Gateway:** Läuft ein Gateway in der App Device Proxy über seinen
  Ersatz (ein zweites Gateway mit derselben Base-ID), zeigt die Gateway-Karte gelb „Verbunden
  über Ersatz …“ statt grün „Verbunden“, auch in der Leiste der Gateways; die Proxy-Zeile in den
  Details sagt, ob der Ersatz einspringt, bereit oder nicht einsatzbereit ist. Der Sensor
  Verbindung des Gateways bekommt die Attribute `via_fallback`, `fallback` und `fallback_ready`
  (für Automationen, auch ohne MQTT). Ältere Versionen der App ohne Ersatz zeigen sich wie
  bisher.
- **Panel, Übernahme:** Nachträglich übernehmen… ergänzt, was schon eingerichteten Geräten
  noch fehlt; am neuen Gerät gesetzte Werte bleiben (Websocket `enocean_eltako/takeover/carry`).
- **Gateway-Einstellungen:** optionaler Gateway-Präfix in Entitäts-IDs: neue Entitäten bekommen
  IDs wie `light.eno_gw1_kuche`, mit einer eigenen Gateway-Nummer je Gateway; bestehende
  Entitäten werden auf Wunsch umbenannt (Automationen und Dashboards werden nicht angepasst).
  Standardmäßig aus. Das Gateway zeigt seinen Präfix im Diagnose-Sensor Entitäts-ID-Präfix.

### Behoben

- **Übernahme:** zwei alte Taster auf derselben Sender-ID (links und rechts) brechen die
  Übernahme nicht mehr mittendrin ab; der zweite gilt als doppelt. Was vor einem Fehler angelegt
  wurde, bleibt, mit gespeicherten Sender-IDs und neu eingerichtetem Gateway.
- **Heizungsaktor:** ist der Raumtemperaturfühler nicht verfügbar, sendet Home Assistant nichts
  mehr, statt die letzte Temperatur zu wiederholen; der Aktor geht so in seinen Störbetrieb,
  statt auf einen eingefrorenen Wert zu heizen.
- **Rollläden mit Controller:** eine Vollfahrt wird in ganzen, aufgerundeten Sekunden gesendet,
  damit die gemeldete Fahrzeit die Vollfahrt erreicht und den Positionsanker erneuert (bei 15,3 s
  Fahrzeit wurden 17 statt 18 s gesendet).
- **Rollläden mit Controller und Richtungstaster:** Stopp, nachdem der Aktor angehalten und seine
  Fahrzeit gemeldet hat, drückt den Richtungstaster nicht mehr erneut, was den Rollladen wieder
  losfahren ließ.
- **Rollläden:** die höhere Ungenauigkeit nach einer Ankerfahrt ohne Antwort steht sofort im
  Zustand des Rollladens und übersteht einen Neustart.
- **Rollläden:** die Laufzeitfelder im Dialog zum Anlegen verweisen auf den Laufzeit-Assistenten
  (Neu konfigurieren → Laufzeiten messen), damit Standardzeiten nicht versehentlich ungemessen
  bleiben.
- **ESP3-Gateways:** ein verirrtes Sync-Byte mit unplausibler Paketlänge hält nicht mehr alle
  folgenden Telegramme zurück (möglich nach einem Reconnect mitten in einem Paket).
- **ESP3-Gateways:** die Antwort auf ein Funktelegramm gilt nicht mehr als Antwort auf den
  Base-ID- oder Repeater-Befehl: nach einem Reconnect wurde die Base-ID manchmal nicht gelesen
  und das Gateway fälschlich als stumm gewertet, und eine abgelehnte Repeater-Einstellung galt als
  übernommen.
- **Aktionen:** Eigene Geräte importieren, Telegramme aufzeichnen und Energie-Geräte hinzufügen
  schreiben Dateien oder die Energie-Einstellungen und sind jetzt nur noch für Administratoren.
- **Übernahme, Entitäts-IDs wiederherstellen:** eine alte Entität, deren neue Entsprechung
  eine andere Art ist (etwa Sensor und Binärsensor), behält die neue ID, statt das
  Wiederherstellen für alle anderen scheitern zu lassen.
- **Rollläden, Schaltfläche Kalibrieren:** die Fahrt endet, wenn das Gateway neu geladen oder
  entfernt wird, und ein Fehler (Gateway offline) steht als Warnung im Log statt als unbehandelter
  Fehler.
- **Entwicklung:** ein Release entsteht erst, wenn die Prüfungen für den Push auf main
  bestanden sind, und von Hand nur von main aus.
- **Panel:** wird es direkt nach dem Öffnen verlassen, läuft nicht mehr bis zum Schließen des
  Browser-Tabs alle 5 s eine Statusabfrage weiter.
- **Device-Proxy-Erkennung:** nicht lesbare Gateway-Angaben (ohne Host oder Port, unbekanntes
  Protokoll) beenden die Erkennung mit einem Hinweis statt mit einem Fehler.
- **Fahrzeiten messen, ausgeblendete Sender:** wird das Gateway neu geladen, entladen oder ist
  es offline, während das Formular offen ist, endet der Ablauf mit einem Hinweis statt mit einem
  Fehler.
- **Heizungsaktor:** der Reparaturhinweis, dass er nicht mehr geregelt wird, verschwindet, wenn das
  Gerät entfernt oder das Gateway entladen wird.
- **Aktoren ohne Sender-ID:** beim Schalten erscheint, dass die Sender-ID fehlt, statt eines
  unbekannten Fehlers.
- **Device Proxy:** eine Wiedergabe empfangener Telegramme, die nicht endet (über 1 MB oder
  30 s), wird übersprungen und hält die Live-Telegramme nicht mehr für den Rest der Verbindung
  zurück.
- **Diagnose:** die Netzwerkadresse eines LAN-Gateways wird geschwärzt.

## 0.1.6 - 2026-10-22

### Neu

- **Panel, Einlernen:** ein Gerät mit eigener Sender-ID lässt sich in der Ansicht Geräte
  (Doktorhut) in seinen Aktor einlernen, mit Anleitung und Wahl der Sender-ID; gesendet wird
  dasselbe wie mit der Einlern-Schaltfläche des Geräts (Websocket `enocean_eltako/teach_in`).
- **Panel, schwaches Signal:** ein Hinweis über der Geräteliste zählt die Sender mit schwachem
  Signal und zeigt per Klick nur sie; Status-Filter **Schwaches Signal**.
- **Panel, nochmal senden:** die Details eines gesendeten Telegramms senden es erneut.
- **Entwicklung:** eine Vorschauseite des Panels mit Beispieldaten (`scripts/panel-preview`) und
  eine CI-Prüfung, die jede Ansicht in einem simulierten Browser zeichnet.

### Behoben

- **Panel auf Englisch:** Millisekunden stehen vor AM/PM; die Zahlen der Gateway-Karte klein
  geschrieben und bei eins im Singular.

## 0.1.5 - 2026-10-22

### Neu

- **Sender-IDs:** Der Dezimalwert einer ID ist ein Attribut (`decimal`) der Diagnose-Sensoren
  EnOcean-ID und Sender-ID und eine eigene Spalte in der Ansicht Sender-IDs des Panels. Die
  Ansicht zeigt außerdem eine Pool-Karte (ein Feld pro ID, Klick springt zur Zeile) und die
  nächste freie ID; Gerätegruppen lassen sich einklappen.
- **Gateway tauschen:** Beim Neukonfigurieren eines Gateways wird jetzt auch das Modell
  abgefragt. So lässt sich ein defektes Gateway oder ein FAM-USB durch ein anderes Modell
  (z. B. ein Netzwerk-Gateway) ersetzen, ohne Geräte und Sender-IDs zu verlieren. Das neue
  Gateway muss dieselbe Base-ID melden, sonst wird der Wechsel abgelehnt. Bus-Gateways
  (FGW14-USB, FAM14) tauschen nur untereinander.

### Geändert

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

### Behoben

- **Panel:** Befehl und Antwort werden über das Gerät gepaart, nicht über seinen Namen (zwei
  Geräte können gleich heißen); die Ansicht Übernahme verschwindet ohne Neuladen, sobald nichts
  mehr übrig ist; CSV-Exporte sind gegen Tabellenformeln abgesichert.

## 0.1.4 - 2026-10-22

### Geändert

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

### Neu

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

### Behoben

- **Panel:** zweimal Anzeige leeren holt nach einem Reconnect die Telegramme des ersten Leerens
  nicht mehr zurück; `/` und `P` wirken nicht mehr in Sender-IDs und Übernahme; Schließen des
  Sendeformulars blendet seinen Hinweis aus; Geräte durchsucht Daten und Werte wie Telegramme;
  ältere Browser ohne `light-dark()` (iOS vor 17.5) bekommen die Farben des Panels; keine
  Statusabfragen, solange der Browser-Tab verborgen ist.

## 0.1.3 - 2026-10-22

### Neu

- **App Device Proxy:** ihre EnOcean-Gateways werden wie die der App EnOcean Proxy gefunden,
  mit dem Titel „(Device Proxy)“, Nachlieferung und Status im Panel. Der Hinweis auf eine zu
  alte EnOcean-Proxy-Version gilt für sie nicht (sie nennt stattdessen die Version der
  Schnittstelle).
- **Umstieg vom EnOcean Proxy zum Device Proxy:** Ein Gateway, das über die eine Proxy-App
  eingerichtet wurde und von der anderen gemeldet wird, wird über seine Base-ID erkannt; der
  Eintrag bekommt nur die neue Adresse und den Status-Port, Geräte und Entitäten bleiben

### Behoben

- **Panel auf dem Handy:** Die Ansichts-Reiter in der Kopfzeile bleiben in einer Zeile und
  lassen sich seitlich wischen, statt in eine zweite Zeile umzubrechen

## 0.1.2 - 2026-10-21

### Geändert

- **Panel:** neues Aussehen wie die Device-Proxy-App: weiße Kopfzeile mit den Ansichten als
  Reiter, runde Karten und Knöpfe, eigene helle und dunkle Farben, die dem Theme von Home
  Assistant folgen
- **Dokumentation:** die Anlernanleitung nennt, welchen virtuellen Sensor jeder Aktor annimmt

## 0.1.1 - 2026-10-21

### Geändert

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

## 0.1.0 - 2026-10-21

### Neu

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

### Hinweise

- Die Protokollschicht (ESP2/ESP3, EEPs, FAM14-Bus) ist in diesem Repository ohne EnOcean-
  oder Eltako-Bibliotheken umgesetzt.
- Die offiziellen Dateien der EnOcean Alliance gehören nicht zum Repository (siehe
  [NOTICE](NOTICE)).
