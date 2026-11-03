# Changelog

All notable changes to this project are documented here, in English and German: every release
has an English and a German part. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
([deutsch](https://keepachangelog.com/de/1.1.0/)).

### [Unreleased]

**English**

#### Added

- **Room controller with several IDs** (FUTH55ED, FUTH65D): one device for the four IDs a FUTH sends from, entered with its lowest ID (ending in `00`). Controller (`+01`: climate, setpoint, temperature, night setback), pump (`+10`), operating mode (`+11`) and hygrostat (`+12`: humidity, also on the climate entity). Read only. The Devices view lists every ID, the documentation each with its profile. The offsets are those of the old integration's table; the telegrams of a FUTH55ED confirm the controller and the hygrostat, pump and mode are read from the rocker codes `0x70/0x50` and `0x70/0x50/0x30/0x10`.
- **Telegram log**: a command Home Assistant sent is now read like a received telegram: setpoint and night setback of a room controller (a temperature of 0 means the thermostat measures), switch on/off and dim value, shutter up/down/stop with run time, rocker button pressed or released, the status request. Only what the encoders build is read; other profiles still show the raw bytes.
- **Telegram log**: a telegram that a known device's model cannot read, but one to three other models can, names those device types (**Fits** ...). A device saved under the wrong type, such as a Permundo PSC as an Eltako switch, shows raw bytes; now the row says which type would decode them.
- **Takeover**: a switch of the old configuration whose ID has been heard sending a D2-01-09 status (the old integration knows no VLD) is taken over as a **Permundo PSC** with the standard A5-38-08 controller, no longer as an Eltako switch that shows raw bytes.
- **Reconfigure a device**: the **device type** of a switching device can be changed (Eltako switch, Permundo PSC, VLD switch). The sender ID of the first sender carries over, nothing is saved before the form of the new type is confirmed, and the ID is not blocked or taught out because it only changes its profile.

#### Changed

- **Devices view**: every device shows one **state pill** (active, silent, not heard, disabled, unknown) instead of a mix of tags; the first that applies counts, so a disabled device is not judged by its silence. The text names the state, the color only backs it up.
- **Devices view**: the status chips (All devices, Set up, Unknown, Silent, Weak signal) show **how many devices** each would list, for the gateway chosen.
- **Devices view**: every device has a **tile** for its kind (light, cover, climate, button, sensor, meter, virtual), a question mark for an unknown sender; the tooltip names the kind. A device whose model is not fixed (one EEP, several devices, such as the FUD14, FUD61 and FD62) lists the candidates under its name instead of nothing.
- **Devices view**: the buttons of a row no longer move around. Teach in, open the device in Home Assistant and show its telegrams sit in a **⋮** menu; an unknown sender keeps its **+**, and the **checkbox** and the **expand arrow** stay where they are. A device that offers none of these (not heard yet, no page, no senders) has no menu.
- The **+** of an unknown sender (Devices view and telegram details) opens a menu: **Set up as device** as before, or **Only write down**, which adds an entry tagged *only written down* (Installation → Devices → Radio) with the ID filled in and puts the cursor in its name field. Nothing is created in Home Assistant and nothing is learned into an actuator; an ID already written down is not added twice.
- The catalog entry **Rocker switch** (EnOcean) and the device documentation now name the **EnOcean PTM 210/215** pushbutton modules (F6-02-01), found in many switches.
- **Installation view redesigned.** Four tabs (Devices, Sender IDs, Links, Log); the Overview, Senders and Bus tabs are gone, their tables live in the views of the **Devices** tab: **All devices**, **Bus**, **Radio** and **Virtual**, switched at the top. Every row names its **kind** (Eltako bus, radio sensor, radio button, radio actuator, virtual, power supply) as a tag that opens the view of that kind, and a device with sender IDs from the pool carries **Sender 1, 2**, which jumps to its rows in the Sender IDs tab (the device names there jump back).
  - **All devices**: the **place** is three fields that look like one (cabinet, row, slot, stored as "cabinet · row · slot"; older free text is split at the comma); kind chips, filters for a missing place or fuse (with counts), grouping by area or place, a **Next without a place** button and a **Columns** menu. Virtual devices have no place and do not count in the progress; power supplies and entries written down by hand do.
  - **Bus**: grouped by **power supply**. A supply is a header row with type, watts and the bus addresses it feeds, edited right there, with a load bar and an overload warning; addresses no supply feeds sit in a group of their own; tiles show duplicate addresses, used and free addresses, total power and the state of the supplies. Supplies also appear in **All devices** with place, circuit, fuse and note.
  - **Radio**: radio devices and entries written down by hand in one table (place, sender ID, what it sends, **supply**, part of, **signal**: a dot for when it was last heard with strength and "via repeater only", and the **link**: what it controls, what controls it). **Write down a device** (name, ID, kind, function) replaces the editor of the Other devices; such an entry carries *only written down* and also shows in **All devices**.
  - **Virtual**: pool number, sender ID, the entities a virtual device follows and the actuators it was taught into.
  - Devices of the Eltako series 14 (FSR14, FUD14, FSB14 ...) count as **Eltako bus** even without an address and wait in the group *No bus address yet* of the Bus view; a room controller is a radio sensor, not an actuator, so the Links tab does not ask who switches it.
  - **Sender IDs**: the table of the gateway senders with the sender ID pool, as before, one row per sender.
  - **Links**: a card per actuator, per sender or a **matrix**; every link names the other end, the role and its origin (assigned, declared, entered), the learn position and the state. An actuator without a link is marked; tiles and filters show what is open; **Test senders**, **+ Link**, **+ Actuator**, a **+** in the matrix and **Write down as device** for a wall switch ID without a device. The table of the former Buttons tab (left and right rocker) is this tab grouped by sender.
- **Colour in the Installation view**: every kind has its own hue (Eltako bus blue, radio sensor teal, radio button violet, radio actuator orange, virtual magenta, power supply slate), used for the kind tag, the dot of the kind chips, a stripe at the left of each row and the cards of the Links tab. The views are switched with a solid selected button, the tiles carry an accent (green when all is well, amber when something is open), group and supply rows are tinted, the origin of a link has its own colour (assigned orange, declared blue, entered green) in tags and filters, and the events of the log are coloured tags.
- The device table shows **only the columns a kind can use**: the table of all kinds has place, circuit, fuse, installation date and note; choose a kind above and the columns for it appear (bus address, feedback ID and bus power for the Eltako bus; supply for radio devices; part of and revision where they make sense). Empty fields carry short hints (Circ., Fuse, Addr.) instead of the full column name, and the column group *Bus and radio* is just *Bus*.
- The block to **paste from a spreadsheet** is now **Edit with a spreadsheet**: three numbered steps (copy the table, fill it in, paste it back) with a plain hint instead of a tab-separated example, and a line under the text field that says how many rows and fields were found before you apply them.
- Storage and documentation: the notes store is now **version 5**. A power supply of the bus has a place, circuit, fuse and note, and an entry written down by hand has a kind, place and supply (older entries are migrated, the new fields start empty). The documentation tells for every device when it was last heard, the best signal and whether it is heard only via a repeater, and for a virtual sensor the entities it follows.
- **Telegram log**: a telegram Home Assistant sent to a device is no longer shown as if the device sent it. The row carries a **Sent** tag, the name reads "to <device>" and the second line "from <sender ID>".
- **Installation**: checkboxes have their own look (clear box, accent fill with a tick) and the device table gives them room next to the row stripe. **Edit with a spreadsheet** is now a **Spreadsheet** button in the toolbar that opens a card with the three steps, instead of a collapsible block.
- **Sender IDs tab**: each gateway shows tiles (in use, blocked, free, all) that filter the table, a bar of the pool, the **next free ID** with a copy button and a short intro (the long text is a tooltip). The table is sortable (number, device, function, role, status), searchable, filterable by function and **paged (25 by default)**, with a colour stripe and a tag per status; the default view lists the IDs in use and blocked ones, free numbers one row each under *Free*.
- **Log tab**: events read as sentences (the device is a link to its row, sender test results are tags: confirmed, not confirmed, failed), grouped by day with the time relative to now, filterable by kind and period (today, 7 days, all), searchable, sortable, **paged (25 by default)** and downloadable as CSV.
- **Links tab**: one sentence of intro (the long text is a tooltip); the tiles (actuators, without link, no answer, not tested, answered) filter the list, the source is three toggle chips, search and sorting (name, status, number) are new, the learn position shows on request, and the actuators are **paged (25 by default)**.
- **All devices**: the **Missing** chips and the progress line are two tiles (without a place, without a fuse) with the count and "x of y recorded" that filter the table, next to **Next without a place**; an empty place is one **+ Add place** button that opens the three fields only when clicked; the table is **sortable** (column headers) and **paged (25 by default)**; placeholders are written out (Circuit, Address, Fuse) and the *Group by* select is styled.

#### Fixed

- **Telegram log**: the direction is the one marker of a row: a green arrow for received, a blue one for sent. The blue bar and tint on sent rows are gone; a bar now marks only a warning: a sent command without an answer within 3 s gets an amber bar and a tag.
- **Takeover**: after taking devices over, the view always lands on step 3 (retire the old integration). When the old integration has no entities left for them, step 3 says so instead of the view falling back to step 1.
- **Last heard** is kept across a restart: it comes from the saved signal data, no longer only from the *Last seen* sensor, which is disabled by default. A device that has not sent since Home Assistant started is no longer shown as never heard.

**Deutsch**

#### Hinzugefügt

- **Raumregler mit mehreren IDs** (FUTH55ED, FUTH65D): ein Gerät für die vier IDs, von denen ein FUTH sendet, eingetragen mit seiner niedrigsten ID (endet auf `00`). Regler (`+01`: Klima, Sollwert, Temperatur, Nachtabsenkung), Pumpe (`+10`), Betriebsart (`+11`) und Hygrostat (`+12`: Luftfeuchte, auch an der Klima-Entität). Nur lesend. Die Geräteansicht listet jede ID, die Dokumentation jede mit ihrem Profil. Die Offsets stammen aus der Tabelle der alten Integration; die Telegramme eines FUTH55ED bestätigen Regler und Hygrostat, Pumpe und Betriebsart werden aus den Wippen-Codes `0x70/0x50` und `0x70/0x50/0x30/0x10` gelesen.
- **Telegrammprotokoll**: Ein Befehl, den Home Assistant gesendet hat, wird jetzt wie ein empfangenes Telegramm gelesen: Sollwert und Nachtabsenkung eines Raumreglers (Temperatur 0 heißt: das Thermostat misst), Schalten Ein/Aus und Dimmwert, Rollladen auf/ab/Stopp mit Laufzeit, Wippentaste gedrückt oder losgelassen, die Statusanforderung. Gelesen wird nur, was die Encoder bauen; andere Profile zeigen weiter die Rohbytes.
- **Telegrammprotokoll**: Ein Telegramm, das das Modell eines bekannten Geräts nicht lesen kann, ein bis drei andere Modelle aber schon, nennt diese Gerätetypen (**Passt zu** ...). Ein Gerät mit falschem Gerätetyp, etwa ein Permundo PSC als Eltako-Schalter, zeigt Rohbytes; jetzt steht in der Zeile, welcher Typ sie entschlüsseln würde.
- **Übernahme**: Ein Schalter der alten Konfiguration, dessen ID mit einem D2-01-09-Status gehört wurde (die alte Integration kennt kein VLD), wird als **Permundo PSC** mit dem Standard-A5-38-08-Controller übernommen, nicht mehr als Eltako-Schalter, der Rohbytes zeigt.
- **Gerät umkonfigurieren**: Der **Gerätetyp** eines schaltenden Geräts lässt sich ändern (Eltako-Schalter, Permundo PSC, VLD-Schalter). Die Sender-ID des ersten Senders bleibt, vor der Bestätigung des Formulars des neuen Typs wird nichts gespeichert, und die ID wird nicht gesperrt oder ausgemeldet, weil sie nur das Profil wechselt.

#### Geändert

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

#### Behoben

- **Telegrammprotokoll**: Die Richtung ist das eine Kennzeichen einer Zeile: grüner Pfeil für empfangen, blauer für gesendet. Der blaue Balken und die Tönung bei gesendeten Zeilen entfallen; ein Balken markiert nur noch eine Warnung: ein gesendeter Befehl ohne Antwort innerhalb von 3 s bekommt einen gelben Balken und ein Tag.
- **Übernahme**: Nach der Übernahme landet die Ansicht immer bei Schritt 3 (Alte Integration ablösen). Hat die alte Integration für die Geräte keine Entitäten mehr, sagt Schritt 3 das, statt dass die Ansicht auf Schritt 1 zurückfällt.
- **Zuletzt gehört** bleibt über einen Neustart erhalten: der Wert kommt aus den gespeicherten Signaldaten und nicht mehr nur aus dem standardmäßig deaktivierten Sensor *Zuletzt gesehen*. Ein Gerät, das seit dem Start von Home Assistant nicht gesendet hat, gilt nicht mehr als nie gehört.

### [1.5.0] - 2026-11-02

**English**

#### Added

- **Appearance** of the panel (palette button in the header): three colour schemes (Ocean, Forest, Graphite), each light and dark; light, dark or like Home Assistant; font size small, normal or large (12.6, 14 or 16 px, every size in the panel follows). The choice is stored per Home Assistant user and cached in the browser.

- The tables of the Senders and Bus groups are **editable in place**: bus address and feedback ID (gateway senders, bus), place (buttons, radio senders), **Part of** (radio senders) and bus power (bus). A device with several senders shows the same value in every row and all rows follow a change.
- **Several power supplies** of the bus: each with type, watts and, optionally, the bus addresses it feeds. The printout shows the load of every supply with a range, the total, and addresses no supply feeds. The notes store is now version 3 (a single supply of version 2 is migrated).
- The **Eltako bus** table lists bus addresses 1 to 126 (one per channel) with free runs folded and an address given twice reported, and takes the power of a type from Eltako's planning guide (07/2014) where you wrote none down; the supply defaults to the 12 W of the FAM14. Types the guide does not list (newer devices) have no value.
- New device field **Part of**: radio IDs with the same value (a room controller such as the FUTH55 sends under several IDs) are one block in the **Radio senders** table of the printout, each ID saying what it sends.
- **Eltako bus** table in the printout: every device with a bus address, by address, with the power it takes from the bus (written down by hand, from its data sheet), the sum and the load of the bus power supply, which you write down in the gateway details. Devices of the bus that Home Assistant does not hold are entries by hand with bus address, feedback ID and watts.
- The printout has three more tables: **Gateway senders** (sender no. 0 to 127 of the radio pool, free numbers folded, several senders of one device pointing to each other, and senders you wrote down by hand below, with the numbers of their device), **Buttons** (each wall switch with the actuators on its left and right rocker) and **Radio senders** (devices that only send, and the entries by hand). New fields **Bus address** and **Feedback ID** per device, and **Sender tables CSV**.
- A **checklist for a new gateway** in the printout: every assigned sender to teach in again when a radio gateway with another base ID takes over.
- **Links as CSV**, and the JSON export is now version 2 (typed fields, links, the log); the import still reads version 1.
- **Links** in the Installation tab: who is taught into which actuator, by actuator or by sender, each link marked as assigned, declared (wall switch option) or entered by you, with the teach-in time, the last sender test and a learn position. The JSON export carries them and the import takes entered links and learn positions back.
- The new **Installation** tab of the panel: devices by area or place, a table with typed fields (place, circuit, fuse, installed, revision, power, note) edited in place, for a selection or pasted from a spreadsheet, and the event log.
- The installation keeps an **event log** per gateway: devices added or removed, senders assigned or removed, teach-ins, sender tests and imports.
- Importing notes into a **swapped gateway** (another base ID): the panel offers to map the one unmatched gateway of the file to the one set up here.

#### Changed

- The panel tells why a gateway behind the proxy app shows no status: **proxy status not reachable** (request failed) or **does not list this gateway** (the app's status has no gateway on our port). The diagnostics carry the status URL (host masked) and the last error, and the first failure is logged on debug.
- **Devices** table: a progress line (devices with a place), columns in groups to show or hide (place and fuse, bus and radio, upkeep; remembered per browser), and a wrong bus address or watts value is named under the field and not sent.
- **Sender IDs** is no longer a tab of its own: it is the **Sender ID pool** above the table under Installation → Senders → Gateway senders, always shown and foldable (pool map, who uses which ID, release of blocked IDs, also from a blocked row of the table). `?view=senders` and a saved Sender IDs view open it there.
- The tabs of the Installation view are real tabs (underlined) in two levels; the switch between table and ID management is gone. The first group is now **Devices** (Overview, Table); the grouping by area or place is a segmented switch, each gateway is a card with its device count, and a gateway without devices offers a button to the integration.
- The **Installation** tab is now the place for documentation and administration, in groups: Site (by area, devices), Senders (gateway senders, buttons, radio senders), Bus (Eltako bus, power supplies), Links, Log. The sender and bus tables show the same rows as the printout; the power supplies and the entries by hand moved there from the gateway details, and the output buttons are one **Output** menu.
- The **Takeover** view shows the switch between takeover and reports at once, with an animated placeholder while it loads, so the reports are reachable without waiting for the takeover.
- **Heard by** and the heard but unknown senders **survive a restart**: how each gateway hears a device and the newest 100 unknown senders are kept (written at most once a minute).
- The printout is **one page with sections** you switch on or off above it (handover, cabinet, links, checklist, sender IDs, log); it replaces the separate cabinet sheet.
- A device's notes are now typed fields (store version 2, migrated from version 1 on first load); exports and the import carry all of them.

#### Fixed

- Importing notes of a **two-channel actuator** put the second channel's note under the first channel's key; exports now carry the key of each device.

**Deutsch**

#### Hinzugefügt

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

#### Geändert

- Das Panel nennt den Grund, wenn ein Gateway hinter der Proxy-App keinen Status zeigt: **Proxy-Status nicht erreichbar** (Abfrage fehlgeschlagen) oder **listet dieses Gateway nicht** (der Status der App hat kein Gateway auf unserem Port). Die Diagnose enthält die Status-URL (Host maskiert) und den letzten Fehler, der erste Fehlschlag steht im Debug-Log.
- Die Reiter der Ansicht Anlage sind echte Reiter (unterstrichen) in zwei Ebenen, der Umschalter zwischen Tabelle und ID-Verwaltung entfällt. Die erste Gruppe heißt jetzt **Geräte** (Übersicht, Tabelle); die Gruppierung nach Bereich oder Ort ist ein Segment-Schalter, jedes Gateway ist eine Karte mit Gerätezahl, und ein Gateway ohne Geräte bietet einen Button zur Integration.
- Tabelle **Geräte**: eine Fortschrittszeile (Geräte mit Ort), Spalten in Gruppen zum Ein- und Ausblenden (Ort und Sicherung, Bus und Funk, Wartung; pro Browser gemerkt), und eine falsche Bus-Adresse oder Wattzahl wird unter dem Feld genannt und nicht gesendet.
- **Sender-IDs** ist kein eigener Reiter mehr, sondern der **Sender-ID-Pool** über der Tabelle unter Anlage → Sender → Gateway-Sender, immer sichtbar und einklappbar (Pool-Karte, wer welche ID nutzt, Freigabe gesperrter IDs, auch aus einer gesperrten Zeile der Tabelle). `?view=senders` und eine gespeicherte Ansicht Sender-IDs öffnen sie dort.
- Der Reiter **Installation** heißt jetzt **Anlage** und ist der Ort für Dokumentation und Verwaltung, in Gruppen: Anlage (nach Bereich, Geräte), Sender (Gateway-Sender, Taster, Funk-Sender), Bus (Eltako-Bus, Netzteile), Verbindungen, Protokoll. Die Tabellen der Gruppen Sender und Bus zeigen dieselben Zeilen wie der Ausdruck; Netzteile und Einträge von Hand sind aus den Gateway-Details dorthin umgezogen, und die Ausgabe-Knöpfe sind ein Menü **Ausgabe**.
- Die Ansicht **Übernahme** zeigt den Wechsel zwischen Übernahme und Berichten sofort und beim Laden einen animierten Platzhalter; die Berichte sind erreichbar, ohne auf die Übernahme zu warten.
- **Gehört von** und die gehörten unbekannten Sender **überstehen einen Neustart**: wie jedes Gateway ein Gerät hört und die neuesten 100 unbekannten Sender bleiben erhalten (höchstens einmal pro Minute geschrieben).
- Der Ausdruck ist **eine Seite mit Abschnitten**, die du oben ein- oder ausschaltest (Übergabe, Schaltschrank, Verbindungen, Checkliste, Sender-IDs, Protokoll); sie ersetzt das eigene Schaltschrank-Blatt.
- Die Notizen eines Geräts sind jetzt typisierte Felder (Speicherversion 2, beim ersten Laden aus Version 1 überführt); Exporte und der Import enthalten alle.

#### Behoben

- Der Import von Notizen eines **Zweikanal-Aktors** legte die Notiz des zweiten Kanals unter dem Schlüssel des ersten ab; Exporte tragen jetzt den Schlüssel jedes Geräts.

### [1.4.1] - 2026-11-01

**English**

#### Fixed

- The **⋮ menu** of the Devices view, which holds the installation documentation (print, cabinet sheet, CSV, JSON, import), was only shown on narrow screens. It now also shows on desktop.

**Deutsch**

#### Behoben

- Das **⋮-Menü** der Geräteansicht mit der Installationsdokumentation (Drucken, Schaltschrank-Blatt, CSV, JSON, Import) wurde nur auf schmalen Bildschirmen angezeigt. Es erscheint jetzt auch am Desktop.

### [1.4.0] - 2026-11-01

**English**

#### Added

- **Test senders** also works for dimmers: the central command repeats the current brightness; the rocker is skipped, as a press could change it. Covers stay untested, as every command moves them.
- **Record and report** for unknown senders: listens to the sender for 60 seconds first, so the telegrams of what you do with the device are in the device report.
- The **profile check repair** also fires for values outside the ranges of a standard profile, and names devices that telegrams of the unexpected type are typical for.
- **Import notes from JSON** in the Devices view menu: reads the notes and further devices of an earlier documentation export back (matched by base ID and device address), filling in only what is empty. Devices are never imported.
- A gateway's details offer to **remove the notes of deleted devices**, which otherwise stay for when the device returns.
- **Cabinet sheet** in the Devices view menu: a dense landscape printout, one table per gateway, for the distribution board.
- Screenshots of the sidebar panel (sample data) in both READMEs.
- **Further devices** in a gateway's details: write down buttons taught in directly, devices of other systems and anything else Home Assistant cannot see (name, ID, function). They appear in the printout, CSV and JSON of the installation documentation.
- The printed **installation documentation** opens with an overview page, one line per gateway, when there are several gateways.
- **Installation documentation** also lists the unknown senders a gateway heard since the restart (not set up), and keeps the result of the last **Test senders** across restarts.
- **Notes** for the installation documentation: a field in each device's details and in each gateway's details (place, terminal, fuse, battery date). They are stored per gateway, belong to the device address and appear in the printout, CSV and JSON.
- **Installation documentation** in the Devices view (⋮ menu): print it (one gateway per page), or download it as CSV or versioned JSON. It lists devices with address, EEP, area and wall switch, the assigned senders with teach-in kind and sender test result, and the sender ID pool with blocked IDs, and says what Home Assistant cannot know.
- **Test senders** in the details of a switching actuator: sends its current state through each sender in turn (nothing changes) and shows which senders it answers.
- **Heard by** in a device's details: with several gateways, each gateway with its last signal and telegram count and the strongest one tagged; a device that only a repeater carries is tagged **via repeater only**.
- **Profile check repair**: a device whose last 5 telegrams in a row fit none of its profiles raises a repair (it was most likely set up with the wrong kind); a fitting telegram clears it.
- **Report device** for unknown senders in the telegram details: copies the sender's last telegrams (up to 60) with IDs, gateway and times replaced and opens the new device request form on GitHub. Nothing goes into the link.
- **Hardware column** in the supported devices list: a ✓ where the repository holds a real capture of that model (`tests/fixtures/captures/<model id>.jsonl`).
- **`scripts/capture_to_fixture.py`** turns a capture into an anonymous test fixture (IDs, gateway names and times replaced, telegram data kept), so a bug report can become a regression test.
- **Quality scale**: a self-assessment against the Home Assistant integration quality scale (Bronze to Platinum) in [docs/quality_scale.md](docs/quality_scale.md), also in German.

#### Changed

- The printed **installation documentation** repeats table headers on every page and keeps headings with their table.
- **Signal curve** in the devices list is larger (96 × 32 px; the global 20 px icon size no longer squeezes it) and zooms to the data: the band is at least 16 dB wide, so a steady sender no longer shows a flat line. The weak-signal line appears only when it lies inside the band.

**Deutsch**

#### Hinzugefügt

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

#### Geändert

- Die gedruckte **Installationsdokumentation** wiederholt Tabellenköpfe auf jeder Seite und hält Überschriften bei ihrer Tabelle.
- **Signalkurve** in der Geräteliste ist größer (96 × 32 px; die globale Icon-Größe von 20 px staucht sie nicht mehr) und passt sich den Daten an: der Bereich ist mindestens 16 dB breit, ein gleichmäßiger Sender zeigt also keine flache Linie mehr. Die Linie für schwaches Signal erscheint nur, wenn sie im Bereich liegt.

### [1.3.0] - 2026-10-26

**English**

#### Changed

- **Telegram details** put the data first, with the previous telegram right below it and the changed bytes marked in both (plus a line like "Byte 3 changed: 44 → 49"). The metadata sits in two rows, the signal is left out (it is in the row), and the actions are icon buttons.
- **Devices** list: wider values column, narrower area and entity columns, and "Add device" is a round filled plus button (its name stays as the tooltip).
- **Signal curve** in the device view takes the colour of the last value, ends in a dot and shows the weak-signal line (-85 dBm).
- **Search** shows the `/` shortcut as a small key in the field instead of a tooltip over the whole label; the column headers lose their sort tooltip (the sort state stays in the arrow and for screen readers).
- **Telegram list** can hide an unknown sender from discovery with one click (button in the opened row). It is shown again under Configure → Hidden senders.
- **Could be** (profile candidates of an unknown sender) now sits below the value and lists two profiles plus "+n" (all of them in the tooltip), in the telegram list and the device view.
- **Sender IDs** show the number counted from the base ID (1 to 127) instead of the decimal ID, in the list and on the map.
- **Devices** show the status chips, the search and the filters in one row.
- **Sender IDs** show the status chips, the search and the sorting in one row.
- **Telegram list** puts a small dot before the sender: filled for known devices, hollow for unknown ones.
- **Signal bars** in the telegram list and the device view are coloured by strength: green, amber or red.
- **Telegram list** tints sent telegrams slightly and marks them with an accent bar, so they stand out from received ones.
- **Takeover search** also finds labels, in the review preview (device and entities) and in the reports.

**Deutsch**

#### Geändert

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

### [1.2.0] - 2026-10-24

**English**

#### Changed

- **Takeover, three steps instead of four:** Select, Review & take over, Retire the old integration. The old
  "Switch over" and "Clean up" steps are gone, and with them **Finish the takeover**.
- **Review shows what comes along:** for every option you tick, the preview lists per device the actual values (area,
  labels, names, icons, hidden/disabled, voice assistants), also per entity. Devices already set up are completed in
  the same step.
- **Retire the old integration:** you first choose how the old entity IDs are dealt with, either keep them (delete the
  old integration, give the new entities the old IDs back, remove `eltako:`) or use the new ones (switch the places
  that use old IDs, delete, remove). The steps follow from the choice.
- **Reports:** one report per takeover, always reachable under **Reports** in the Takeover view, openable and deletable.
  The old reports are migrated (one per gateway and day).

#### Fixed

- **Restore old IDs** no longer renames a new ID that an automation, script, scene or dashboard already uses.
- **Virtual rockers** (old buttons) get a report entry and are completed by "Devices already set up".
- A device taken over after its old entities are gone still gets a report.

**Deutsch**

#### Geändert

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

#### Behoben

- **Alte IDs wiederherstellen** benennt keine neue ID mehr um, die eine Automation, ein Skript, eine Szene oder ein
  Dashboard schon nutzt.
- **Virtuelle Taster** (alte Buttons) bekommen einen Berichtseintrag und werden von „Schon eingerichtete Geräte“
  ergänzt.
- Ein Gerät, das übernommen wird, nachdem die alten Entitäten weg sind, bekommt trotzdem einen Bericht.

### [1.1.1] - 2026-10-24

**English**

#### Changed

- **Discovery card:** the dialog names how many senders were heard by type (for example "15 sensors (A5), 9 rockers
  (F6)") and links to the gateway, instead of listing ten IDs.

**Deutsch**

#### Geändert

- **Entdeckt-Karte:** Der Dialog nennt, wie viele Sender nach Typ gehört wurden (zum Beispiel „15 Sensoren (A5), 9 Taster
  (F6)“), und verlinkt aufs Gateway, statt zehn IDs aufzulisten.

### [1.1.0] - 2026-10-23

**English**

#### Changed

- **Discovered devices:** a gateway that heard unknown senders shows one card under Settings → Devices & services →
  Discovered (with the number of senders) instead of a notification. The card lists them and points to **Add device →
  Discovered devices** of the gateway; it goes away when there is nothing left to discover.

**Deutsch**

#### Geändert

- **Entdeckte Geräte:** Ein Gateway, das unbekannte Sender gehört hat, zeigt eine Karte unter Einstellungen → Geräte &
  Dienste → Entdeckt (mit der Anzahl der Sender) statt einer Benachrichtigung. Die Karte listet sie auf und weist auf
  **Gerät hinzufügen → Entdeckte Geräte** am Gateway hin; sie verschwindet, wenn nichts mehr zu entdecken ist.

### [1.0.2] - 2026-10-23

**English**

#### Fixed

- **PioTek MGW-ETH behind the Device Proxy:** the gateway is no longer offered again as discovered on its own address
  once an MGW-ETH is set up through the app (it serves one connection only, the app holds it).

**Deutsch**

#### Behoben

- **PioTek MGW-ETH hinter dem Device Proxy:** Das Gateway wird nicht mehr unter seiner eigenen Adresse als entdeckt
  angeboten, sobald ein MGW-ETH über die App eingerichtet ist (es bedient nur eine Verbindung, die hält die App).

### [1.0.1] - 2026-10-23

**English**

#### Fixed

- **Device Proxy, base ID:** when the gateway behind the app does not answer the base ID read while it is set up, the
  integration takes the base ID from the app's status instead of asking for it.

**Deutsch**

#### Behoben

- **Device Proxy, Base-ID:** Antwortet das Gateway hinter der App beim Einrichten nicht auf das Lesen der Base-ID, nimmt die
  Integration sie aus dem Status der App, statt danach zu fragen.

### [1.0.0] - 2026-10-23

**English**

#### Added

- **Sender IDs view:** a search (device name, profile, ID with or without dashes, decimal), chips for All / Assigned /
  Blocked and a sort (blocked first, name, sender ID). **Free all** frees every blocked ID the list shows, after a
  confirmation.
- **Device Proxy discovery:** an app that names the model of a gateway in its announcement (`model`, for example
  `fam_usb`) spares the model question; without it the model is still guessed from the name.

#### Changed

- **Panel filters:** the device status is a row of chips instead of a dropdown in the filter menu, and "Unknown senders
  only" is a toggle beside RX / TX in the telegram view. **Filter** only shows in the devices view when there are several
  gateways or areas to choose from.

#### Fixed

- **Device Proxy replay, binary sensors:** contacts, window handles, motion and rain sensors take the replay of telegrams
  the Device Proxy kept during a restart in one go: the state is written once when the replay is through, so a door
  opened and closed in the meantime no longer flips the sensor (and fires triggers) several times, and a state that ends
  where it began fires none.
- **Device Proxy replay, rockers:** replayed rocker presses fire no rocker events. Gestures are timed live, so a replayed
  press became a short press (or two a double press) at the restart and ran automations with a press from minutes ago.

**Deutsch**

#### Hinzugefügt

- **Ansicht Sender-IDs:** eine Suche (Gerätename, Profil, ID mit oder ohne Bindestriche, dezimal), Chips für Alle /
  Zugewiesen / Gesperrt und eine Sortierung (Gesperrte zuerst, Name, Sender-ID). **Alle freigeben** gibt jede gesperrte
  ID frei, die die Liste zeigt, nach einer Rückfrage.
- **Entdeckung über den Device Proxy:** Nennt die App das Modell eines Gateways in ihrer Meldung (`model`, zum Beispiel
  `fam_usb`), entfällt die Frage nach dem Modell; ohne bleibt es beim Erraten am Namen.

#### Geändert

- **Filter im Panel:** Der Gerätestatus ist eine Chip-Reihe statt eines Dropdowns im Filtermenü, und „Nur unbekannte
  Sender“ ist ein Schalter neben RX / TX in der Telegrammansicht. **Filter** erscheint in der Geräteansicht nur, wenn
  mehrere Gateways oder Bereiche zur Auswahl stehen.

#### Behoben

- **Nachlieferung über den Device Proxy, Binärsensoren:** Kontakte, Fenstergriffe, Bewegungs- und Regensensoren nehmen die
  nachgelieferten Telegramme aus der Zeit des Neustarts in einem Zug auf: der Zustand wird einmal geschrieben, wenn die
  Nachlieferung durch ist. Eine zwischendurch geöffnete und geschlossene Tür lässt den Sensor nicht mehr mehrfach
  umschalten (und Trigger feuern), und ein Zustand, der am Ende dort steht, wo er begann, löst nichts aus.
- **Nachlieferung über den Device Proxy, Taster:** nachgelieferte Tasterdrücke lösen keine Taster-Ereignisse aus. Gesten
  werden live gemessen, ein nachgelieferter Druck wurde beim Neustart zum kurzen Druck (zwei zum Doppelklick) und
  startete Automationen mit einem Druck von vor Minuten.

### [0.1.13] - 2026-10-23

**English**

#### Added

- **Weather station:** a "Sunniest side" sensor (south, east, west, or no sun below 2 klx on every side) and a "Rain
  recently" sensor that stays on for some minutes after the rain stops, so covers and awnings do not move back onto a wet
  surface. The minutes are a device setting (15 by default, 0 = no hold).
- **Blueprint "Shade covers by the sun":** moves covers to a shading position when the sun on one side stays strong
  enough, and back when it has been weak for a while; optionally only when it is warm; leaves covers alone whose
  "Automation mode" is Off and covers you moved by hand.
- **Blueprint "Covers and lights at dusk and dawn":** closes covers and switches lights on when it has been dark for a
  while, opens and switches off in the morning; a cover's "Automation mode" decides (Evening and Both in the evening,
  Morning and Both in the morning, Off never), with earliest times so a storm cloud at noon closes nothing.
- **Blueprint "Weather warning with a window open":** a notice (any action you choose) when it starts to rain or blows
  while a window is open, and when a window is opened in bad weather. It moves nothing.

#### Changed

- **Weather station:** dawn and the three sun sensors show whole lux (dawn no longer "999,0 lx"), the wind one decimal.
  Rain is a plain on/off sensor shown as "Rain" / "No rain" with the rain icons, no longer a "moisture" (leak) sensor
  that assistants might treat as a leak alarm. The wind's unit (m/s, km/h, Beaufort) is the entity's display unit
  setting in Home Assistant.
- **Device page:** a device without a named type lists its EEP once, as the model, not again as the model ID.
- **Panel, Devices view:** the boxes have a column of their own, so name and ID line up, and "Select all" sits in the
  table head above them (on phones it stays in the line above the list). The bar of the ticked devices takes the place
  of the count line, the row icons are subdued until the pointer is over the row, and "not heard" is muted.

**Deutsch**

#### Hinzugefügt

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

#### Geändert

- **Wetterstation:** Dämmerung und die drei Sonnensensoren zeigen ganze Lux (die Dämmerung nicht mehr „999,0 lx“), der
  Wind eine Nachkommastelle. Regen ist ein einfacher Ein/Aus-Sensor mit den Anzeigen „Regen“ / „Kein Regen“ und den
  Regen-Symbolen, kein „Feuchtigkeits“-Sensor (Leck) mehr, den Assistenten als Leckalarm behandeln könnten. Die Einheit
  des Winds (m/s, km/h, Beaufort) ist die Anzeigeeinheit der Entität in Home Assistant.
- **Geräteseite:** ein Gerät ohne benannten Typ nennt sein EEP einmal, als Modell, nicht noch einmal als Modell-ID.
- **Panel, Ansicht Geräte:** die Kästchen haben eine eigene Spalte, so fluchten Name und ID, und „Alle auswählen“ steht
  im Tabellenkopf darüber (auf dem Handy bleibt es in der Zeile über der Liste). Die Leiste der gewählten Geräte
  ersetzt die Zeile mit der Anzahl, die Symbole der Zeilen sind gedämpft, bis der Zeiger über der Zeile steht, und
  „nicht gehört“ ist abgeschwächt.

### [0.1.12] - 2026-10-23

**English**

#### Added

- **Panel, Devices view:** select several devices (a box per row, "Select all" for the filtered ones) and, with a bar,
  set an **area**, add or remove **labels** (new labels can be created in place), **disable** or **enable** them, or
  **remove** them from Home Assistant in one go. Area, labels and disabling are Home Assistant's own, so they show on
  the device page too. Removing asks first, reloads the gateway once and leaves the devices' sender IDs blocked until
  the teach-out is confirmed under Sender IDs.
- **Panel:** a device's labels show under its name, a disabled device is tagged, and the search finds labels.

**Deutsch**

#### Hinzugefügt

- **Panel, Ansicht Geräte:** mehrere Geräte auswählen (ein Kästchen je Zeile, „Alle auswählen“ für die gefilterten) und
  mit einer Leiste einen **Bereich** setzen, **Labels** hinzufügen oder entfernen (neue Labels lassen sich gleich
  anlegen), sie **deaktivieren** oder **aktivieren** oder in einem Zug aus Home Assistant **entfernen**. Bereich, Labels
  und Deaktivieren sind die von Home Assistant, sie erscheinen also auch auf der Geräteseite. Das Entfernen fragt vorher
  nach, lädt das Gateway nur einmal neu und lässt die Sender-IDs der Geräte gesperrt, bis das Abmelden unter Sender-IDs
  bestätigt ist.
- **Panel:** die Labels eines Geräts stehen unter seinem Namen, ein deaktiviertes Gerät trägt eine Markierung, und die
  Suche findet Labels.

### [0.1.11] - 2026-10-23

**English**

#### Added

- **Cover automation mode:** every cover has a select "Automation mode" (Off, Morning, Evening, Both; Both until chosen
  otherwise) for your own automations, like the old Eltako integration's. It moves nothing by itself and is kept across
  restarts.
- **Cover state and driven time:** FSB covers have a "State" sensor (opening, closing, open, closed, stopped) and a
  "Driven time" sensor (with the direction) from the actuator's confirmation telegrams.
- **Panel:** an Integration link in the header bar and in the gateway details, straight to that gateway's entry.

#### Changed

- **Cover routing:** a cover moves through one sender, the controller or the direction rocker. "Both" is gone: it sent two
  telegrams per run, and the direction rocker stops a run on the same direction again. Existing covers with "Both" keep
  the controller (the direction rocker where they have no controller).
- **Takeover:** a rocker (F6-02-01, F6-02-02) of the old binary_sensor platform becomes a rocker contact with its device
  class and inverted flag, not a button. The takeover stays on the selection when nothing is left to switch over and
  says so in step 3.

#### Fixed

- **Rocker and wall switch buttons:** the collapsed sections show the button in use (or the default) preselected instead
  of no choice at all.
- **Device page:** the EEP is listed once, as model ID, not also in the model.

**Deutsch**

#### Hinzugefügt

- **Automatikmodus der Cover:** Jedes Cover hat eine Auswahl „Automatikmodus" (Aus, Morgens, Abends, Beides; bis zur Wahl
  Beides) für deine eigenen Automationen, wie in der alten Eltako-Integration. Sie fährt nichts selbst und bleibt über
  Neustarts erhalten.
- **Zustand und Fahrzeit der Cover:** FSB-Cover haben einen Sensor „Zustand" (fährt auf, fährt zu, offen, geschlossen,
  gestoppt) und einen Sensor „Fahrzeit" (mit der Richtung) aus den Bestätigungstelegrammen des Aktors.
- **Panel:** ein Integrations-Link in der Kopfleiste und in den Gateway-Details, direkt zum Eintrag dieses Gateways.

#### Geändert

- **Routing der Cover:** Ein Cover fährt über einen Sender, den Controller oder den Richtungstaster. „Beide" entfällt:
  Es sendete zwei Telegramme je Fahrt, und der Richtungstaster stoppt eine Fahrt bei erneutem Druck in dieselbe Richtung.
  Bestehende Cover mit „Beide" behalten den Controller (den Richtungstaster, wo sie keinen Controller haben).
- **Übernahme:** Ein Taster (F6-02-01, F6-02-02) der alten Plattform binary_sensor wird ein Taster-Kontakt mit seiner
  Geräteklasse und dem Invertieren, kein Knopf. Die Übernahme bleibt bei der Auswahl, wenn nichts mehr umzustellen ist,
  und sagt das in Schritt 3.

#### Behoben

- **Tasten von Taster und Wandtaster:** Die eingeklappten Bereiche zeigen die genutzte Taste (oder den Standard)
  vorausgewählt, statt gar keine Auswahl.
- **Geräteseite:** Die EEP steht einmal, als Modell-ID, nicht zusätzlich im Modell.

### [0.1.10] - 2026-10-23

**English**

#### Changed

- **Links to the device in the panel:** an opened telegram has a "Device in panel" button, and the device name of a sender ID
  group is a link: both open the device's row in the Devices view. "Open device" is now "Open in Home Assistant".
- **Panel look:** logo and view tabs line up with the content (at most 1200 px, centred) instead of the window's
  edges, like in the Device Proxy app.
- **Sender IDs:** the top of the view is clearer: tiles for free, assigned and blocked IDs and the next
  free ID (with a copy button), one bar for the share used, a note when blocked IDs wait for their teach-out
  (with a button to the first one), a pool map whose rows name their ID range, and a line under the map that
  tells ID, number, state and device of the chosen square. The legend shows the numbers.

**Deutsch**

#### Geändert

- **Links zum Gerät im Panel:** Ein aufgeklapptes Telegramm hat den Knopf „Gerät im Panel", und der Gerätename einer
  Sender-ID-Gruppe ist ein Link: beide öffnen die Zeile des Geräts in der Geräteansicht. „Gerät öffnen" heißt jetzt
  „In Home Assistant öffnen".
- **Aussehen des Panels:** Logo und Reiter richten sich am Inhalt aus (höchstens 1200 px, zentriert) statt an den
  Fensterrändern, wie in der Device-Proxy-App.
- **Sender-IDs:** Der Kopf der Ansicht ist klarer: Kacheln für freie, zugewiesene und gesperrte IDs und die nächste
  freie ID (mit Kopieren-Knopf), ein Balken für den belegten Anteil, ein Hinweis, wenn gesperrte IDs auf ihr
  Teach-out warten (mit Knopf zur ersten), eine Pool-Karte, deren Zeilen ihren ID-Bereich nennen, und eine Zeile
  unter der Karte mit ID, Nummer, Status und Gerät des gewählten Felds. Die Legende zeigt die Zahlen.

### [0.1.9] - 2026-10-23

**English**

#### Added

- **Device model:** a device of a kind that several Eltako models share (switching actuators,
  dimmers, shutter actuators, heating actuators, meters ...) has an optional "Model" field: pick
  FSR14-4x, FUD61NPN-230V ... or type another one. It is shown in the telegram monitor and on the
  device page and changes no behaviour. New device data version (schema 4, migration included).

#### Changed

- **Telegram monitor:** the radio does not tell which model sent a telegram, so the monitor no
  longer shows the first example of the kind (FSR61 for an FSR14). Without a chosen model it lists
  the possible models; the device page shows the EEP only.
- **Weather station:** the example FWG14 is named FWG14MS.
- **Devices view:** a set-up device's row opens in place and shows everything known of it: identity
  (model, EEP, area, gateway, ID), radio (last heard, signal with minimum and maximum, repeater hops,
  telegram count, expected interval), latest values, sender IDs with their teach-in kind, command
  statistics (sent, confirmed, answer time), settings and entities with their states. Several rows
  can be open; they stay up to date, and the list keeps its order while one is open. A click on the
  row no longer jumps to the telegrams: the filter button of the row does that.
- **Devices view:** the model of a device is set in its opened row: a dropdown with the models of its
  kind, "Not specified", or "Other model…" to type one. It is saved at once (the gateway's entry
  reloads, as after any change of a device).
- **Devices view:** the opened row shows its values as small tiles and tables on white, like the statistics of the
  Device Proxy app; the share of confirmed commands is a coloured chip.
- **Panel look:** the panel looks like the Device Proxy app: its page colour, larger rounded cards
  with a soft shadow, and pill-shaped view tabs. The accent colour is always the blue of the app; it
  no longer follows the primary colour of a Home Assistant theme (light and dark still follow it).
- **Devices view:** the list always opens sorted by name; a column sort you click applies until the
  panel is closed and is no longer kept.
- **Telegram monitor:** an open telegram pauses the list: new telegrams wait (the live badge shows
  "Paused" with their number) while you read the details and appear when you close the last open
  one. A pause you set yourself stays until you resume.

**Deutsch**

#### Hinzugefügt

- **Gerätemodell:** Ein Gerät einer Art, die mehrere Eltako-Modelle teilen (Schaltaktoren,
  Dimmer, Rollladenaktoren, Heizungsaktoren, Zähler ...), hat ein optionales Feld „Modell": FSR14-4x,
  FUD61NPN-230V ... wählen oder ein anderes eintippen. Es erscheint im Telegramm-Monitor und auf
  der Geräteseite und ändert kein Verhalten. Neue Version der Gerätedaten (Schema 4, Migration
  inklusive).

#### Geändert

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

### [0.1.8] - 2026-10-22

**English**

#### Changed

- **Device Proxy:** the gateway card and the gateway's connection sensor show whether the app's
  fallback gateway stands in and whether it is ready.

#### Fixed

- **Panel:** the EnOcean panel no longer stays blank when one of its files fails to load once
  (during a Home Assistant start or a proxy hiccup): the parts load with retries, and if they
  still fail the panel shows a message with a Reload button.

**Deutsch**

#### Geändert

- **Device Proxy:** die Gateway-Karte und der Verbindungssensor des Gateways zeigen, ob das
  Ausweich-Gateway der App einspringt und ob es bereit ist.

#### Behoben

- **Panel:** das EnOcean-Panel bleibt nicht mehr leer, wenn eine seiner Dateien einmal nicht
  lädt (beim Start von Home Assistant oder bei einem Proxy-Aussetzer): die Teile laden mit
  Wiederholungen, und scheitern sie dennoch, zeigt das Panel eine Meldung mit Neu-laden-Knopf.

### [0.1.7] - 2026-10-22

**English**

#### Changed

- **Panel, Takeover:** what to carry over from the old integration is chosen on its own
  (area, labels, voice assistants, own names, icons, hidden / disabled), with the number of
  devices each concerns; nothing is chosen at first and the choice is remembered per browser.
  Own names, icons and hidden / disabled are new.
- **Panel, Takeover:** devices already set up are no longer a list in Take over but a hint
  leading to Check, which became the overview of every device set up: what it still lacks from
  the old integration, the places using its old IDs, a view by place with links to the editors,
  filters Still in use and Done, and Check again.
- **Panel, Takeover:** Take over asks first: a confirmation shows the devices, entities and
  places to switch over afterwards, the chosen options and each old entity ID next to the one
  its new entity will probably get; only Take over now sets the devices up.
- **Panel, Takeover:** four steps, Select, Carry over (the options as cards with their values,
  and the preview of old and new IDs), Switch over (by place, by device with what each device
  was in the old integration, and the report as a table) and Clean up (a checklist found from
  the current state); Finish the takeover hides the tab.
- **Takeover:** the mapping of old to new entity IDs is kept in the integration's own storage,
  so the report stays readable after the old integration is deleted; Takeover report in the
  Devices view opens it.
- **Takeover:** Restore old IDs gives the new entities the old entity IDs back once the old
  integration is deleted, so references go on working unchanged.
- **Panel, Sender IDs:** the map of the pool uses the full width and labels every row with the
  last byte of its first ID.

#### Removed

- **EnOcean Proxy app:** no longer supported, the Device Proxy app is the proxy app. Gone are
  its discovery format with a single gateway and the repair issue for its old versions; texts
  name the Device Proxy only.

#### Added

- **Device Proxy, fallback gateway:** when the Device Proxy app runs a gateway on its fallback
  (a second gateway with the same base ID), the gateway card shows "Connected through the
  fallback …" in yellow instead of a green "Connected", also in the bar of gateways; the proxy
  line in the details says whether the fallback stands in, is ready or not ready. The gateway's
  Connection sensor gets the attributes `via_fallback`, `fallback` and `fallback_ready` (for
  automations, also without MQTT). Older app versions without a fallback show as before.
- **Panel, Takeover:** Carry over… fills in later what devices already set up still lack;
  values set on the new device stay (websocket `enocean_eltako/takeover/carry`).
- **Gateway settings:** optional gateway prefix in entity IDs: new entities get IDs like
  `light.eno_gw1_kitchen`, with a gateway number of their own per gateway; existing entities
  are renamed on request (automations and dashboards are not adapted). Off by default. The
  gateway shows its prefix in the diagnostic sensor Entity ID prefix.

#### Fixed

- **Takeover:** two old buttons on one sender ID (left and right) no longer stop the takeover
  halfway; the second is marked as listed twice. What was added before an error stays, with its
  sender IDs saved and the gateway set up again.
- **Heating actuator:** when the room temperature sensor becomes unavailable, Home Assistant
  stops sending instead of repeating the last temperature, so the actuator falls back to its
  fault mode rather than heating to a frozen value.
- **Covers with a controller:** a full run is sent in whole seconds rounded up, so the driven
  time the actuator reports reaches the full run and renews the position anchor (a travel time
  of 15.3 s sent 17 s instead of 18 s).
- **Covers with controller and direction rocker:** Stop after the actuator has stopped and
  reported its driven time no longer presses the direction rocker again, which started the
  cover moving.
- **Covers:** the higher inaccuracy after an anchor run without an answer shows in the cover's
  state at once and survives a restart.
- **Covers:** the travel time fields of the add dialog point to the travel time assistant
  (Reconfigure → Measure travel times), so default times are not left unmeasured by accident.
- **ESP3 gateways:** a stray sync byte with an implausible packet length no longer holds back
  every telegram behind it (possible after a reconnect in the middle of a packet).
- **ESP3 gateways:** the answer to a radio telegram is no longer taken for the answer to the
  base ID or repeater command: after a reconnect the base ID was sometimes not read and the
  gateway wrongly counted as silent, and a refused repeater setting counted as accepted.
- **Actions:** Import custom devices, Capture telegrams and Add energy devices write files or
  the Energy settings and are now for administrators only.
- **Takeover, restore entity IDs:** an old entity whose new counterpart is of another kind
  (for example sensor and binary sensor) keeps the new ID instead of failing the restore for
  all others.
- **Covers, Calibrate button:** the run stops when the gateway is reloaded or removed, and a
  failure (gateway offline) is logged as a warning instead of an unhandled error.
- **Development:** a release is only created once the checks have passed for that push to
  main, and by hand only from main.
- **Panel:** leaving it right after opening no longer leaves a status poll running every 5 s
  until the browser tab is closed.
- **Device Proxy discovery:** gateway information that cannot be read (no host or port, an
  unknown protocol) ends the discovery with a message instead of an error.
- **Measuring travel times, hidden senders:** when the gateway is reloaded, unloaded or offline
  while the form is open, the flow ends with a hint instead of an error.
- **Heating actuator:** the repair issue that it has not been controlled goes when the device is
  removed or the gateway unloaded.
- **Actuators without a sender ID:** switching them shows that a sender ID is missing instead of
  an unknown error.
- **Device Proxy:** a replay of received telegrams that never ends (above 1 MB or 30 s) is
  skipped, so it no longer holds back the live telegrams for the rest of the connection.
- **Diagnostics:** the network address of a LAN gateway is redacted.

**Deutsch**

#### Geändert

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

#### Entfernt

- **App EnOcean Proxy:** nicht mehr unterstützt, die Proxy-App ist der Device Proxy. Entfallen
  sind ihr Discovery-Format mit nur einem Gateway und der Reparaturhinweis für ihre alten
  Versionen; die Texte nennen nur noch den Device Proxy.

#### Hinzugefügt

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

#### Behoben

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

### [0.1.6] - 2026-10-22

**English**

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

**Deutsch**

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

**English**

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

**Deutsch**

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

**English**

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

**Deutsch**

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

**English**

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

**Deutsch**

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

**English**

#### Changed

- **Panel:** new look like the Device Proxy app: white header with the views as tabs, rounded
  cards and buttons, its own light and dark colours that follow Home Assistant's theme
- **Documentation:** the teach-in guide lists which virtual sensor each actuator accepts

**Deutsch**

#### Geändert

- **Panel:** neues Aussehen wie die Device-Proxy-App: weiße Kopfzeile mit den Ansichten als
  Reiter, runde Karten und Knöpfe, eigene helle und dunkle Farben, die dem Theme von Home
  Assistant folgen
- **Dokumentation:** die Anlernanleitung nennt, welchen virtuellen Sensor jeder Aktor annimmt

### [0.1.1] - 2026-10-21

**English**

#### Changed

- **Panel:**
  - Devices: values in one column, buttons for a sender's telegrams and for adding an unknown
    sender, sorting by name, last heard, weakest signal or most telegrams, more about unknown
    senders (telegram type, teach-in or possible profiles)
  - Sender IDs: grouped by device, blocked IDs first with their note, readable profile names
  - Takeover: after taking devices over the view moves on to checking the old IDs that are still
    in use, the mapping is shorter per device
  - the heading names the view, layouts for phones

**Deutsch**

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

**English**

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

**Deutsch**

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
