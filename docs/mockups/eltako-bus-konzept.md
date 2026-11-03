# Konzept: Ansicht „Eltako-Bus“ (Installationsdokumentation)

Stand: 2026-11-03 · Status: Phase 1 umgesetzt (siehe „Entscheidungen bei der Umsetzung“) · Mockup: [eltako-bus-ansicht.html](eltako-bus-ansicht.html)

Ziel: Die Ansicht *Installation → Geräte → Bus* bildet die Reiheneinbaugeräte der Eltako-Baureihe 14
am RS485-Bus so ab, wie sie wirklich verbaut sind: **Bus-Master FAM14 → Schrank → Reihe (Hutschiene) →
Geräte in Einbaureihenfolge → Kanäle**, mit Adressen, Netzteilen und allen Querverweisen zu
Home-Assistant-Entitäten, Sendern und Tastern. Das FAM-USB erscheint nur noch als das, was es ist:
ein Funk-Gateway, über das Home Assistant den Bus erreicht.

---

## 1. Bestandsaufnahme (Code, Stand `main` cda884f)

### 1.1 Wo was liegt

| Was | Wo gespeichert | Bemerkung |
|---|---|---|
| Gateway | Config-Entry (`entry.data`: `model`, `base_id`, `device.path`, `bus_group`, …) | Modelle in `protocol/models.py`: `fam_usb` (Funk, ESP2 9600), `fgw14_usb` und `fam14` mit `bus=True` (RS485, 57600). |
| Bus-Gruppe | `entry.data["bus_group"]` (8-stelliger Schlüssel) | Nur für drahtgebundene Bus-Gateways (FGW14-USB, FAM14 am USB). `protocol/bus_group.py`: Failover, FAM14 „on demand“. Ein FAM-USB ist nie Mitglied. |
| Gerät = **ein Kanal** | Config-Subentry je Gerät (`SUBENTRY_SCHEMA = 5`: `device_id`, `senders`, `model`, `model_name`, Optionen) | Ein FSR14-4x mit 4 genutzten Kanälen sind **4 Subentries** mit je eigener Funk-ID. Ein „physisches Gerät“ gibt es im Datenmodell nicht. |
| Typ des Geräts | `CONF_MODEL_NAME` (z. B. „FSR14-4x“), nur Anzeige | `catalog.py`: `models=("FSR14-2x", "FSR14-4x", "FSR14SSR", …)` je Katalogeintrag (switch, dimmer, cover, meter …). Keine Kanalzahl, keine TE-Breite. |
| Doku-Felder je Gerät | `Notes`-Store **je Gateway** (`notes.py`, `STORAGE_VERSION = 7`), Schlüssel `device_key` = Subentry-`unique_id` | `FIELDS`: `location` (Freitext „Schrank · Reihe · Platz“, `placeParts`), `group` („gehört zu“: verbindet die Kanäle eines Mehrkanalgeräts per Freitext), `bus_address` (1–126), `feedback_id`, `bus_power`, `circuit`, `fuse`, `installed`, `revision`, `power`, `note`. |
| Netzteile | `Notes.supplies` (Liste, max. 8 je Gateway) | `SUPPLY_FIELDS`: `name`, `watts`, `first`/`last` (**Adressbereich**), `location`, `circuit`, `fuse`, `note`. Migrationen v3/v4. |
| Von Hand dokumentierte Einträge | `Notes.manual` (max. 200) | `MANUAL_FIELDS` inkl. `bus_address`, `feedback_id`, `bus_power`, `kind` (taster/sensor/aktor). Beispiel F3Z14D „Stromzähler Haus“ (Adr. 12, 00008C0C) ist so ein Eintrag. |
| Verknüpfungen Sender → Aktor | `documentation.build_links`: `assigned` (HA-Sender aus dem Pool), `declared` (Wandtaster-Option), `entered` (`Notes.links`) | Pro Kanal (Subentry), nicht pro physischem Gerät. |
| Leistungstabelle | `bus_devices.py` (`POWER`, `ADDRESSES = 126`, `SUPPLY_WATTS = 12`, Quelle Planungshilfe 07/2014) | Nur Watt. F3Z14D fehlt (neuer als die Tabelle). Keine TE, keine Kanäle. |
| Doku-Export | `documentation.collect` (`VERSION = 2`), Import nimmt 1 und 2 | Struktur `gateways[]` → `devices`, `supplies`, `manual`, `links`, `pools`, … |
| FAM14-Busprotokoll | `protocol/bus/__init__.py` | Nur Docstring („discovery, bus lock, memory read/write“), noch nicht implementiert. Base-ID des FAM14 wird von Hand eingetragen. |

### 1.2 Frontend heute

- `installation.js` → `_instBus()` ruft `_instPerGateway(gw => _instBusOf(gw))` auf: **Gruppierung je
  Config-Entry**. Weil alle Bus-Kanäle als Subentries am FAM-USB hängen, landet „der Bus“ unter
  „FAM-USB Keller“. Das ist der Kern des beschriebenen Fehlers.
- `kindOf()` erkennt Bus-Geräte heuristisch: Bus-Adresse gesetzt **oder** `BUS_MODEL = /^F[A-Z0-9]{1,4}14/`
  auf den Typnamen.
- `_instBusOf()` zeigt eine flache Tabelle (Gerät / Bus-Adresse / Rückmelde-ID / Leistung / Gehört zu),
  gruppiert nach **Netzteil per Adressbereich**, dazu Kacheln (Duplikate, Belegt, Frei, Leistung,
  Netzteile), „Noch keine Bus-Adresse“, Netzteil-Presets (FSNT14-12V/12W, SNT12, SNT15, WNT15) und
  Reserve-Hinweis ab 2/3 (`RESERVE_LIMIT`).
- `shared.js` → `docBus()` rechnet Zeilen/Leistung/Duplikate auch für CSV und Druck; `group` sorgt dafür,
  dass der Tabellenwert eines Mehrkanalgeräts nur einmal zählt.

### 1.3 Was fehlt

1. **Bus als eigenes Objekt** (Master, Adressraum, Zugang über welche Gateways) – heute implizit „das Gateway“.
2. **Physisches Gerät (Modul)** mit Kanälen: heute nur der Freitext `group`; Kanalnummer, erste Adresse,
   freie/ungenutzte Kanäle und nicht in HA eingerichtete Kanäle sind nicht abbildbar.
3. **Schrank / Reihe / Platz strukturiert**: heute ein Freitext mit „·“ als Trenner, ohne Reihenbreite,
   ohne TE-Position, ohne Reihenfolge der Reihen und Schränke.
4. **TE-Breite und Kanalzahl je Typ** im Katalog.
5. **Physische Speisung**: Netzteile werden über Adressbereiche zugeordnet; real speist ein Netzteil die
   Geräte seines Abschnitts zwischen Trennbrücken (siehe 2.3).
6. Bus-Topologie (Reihenwechsel per BBV14/FBA14, Schrankwechsel per Busleitung, Abschlusswiderstand).
7. Master selbst (FAM14) als dokumentiertes Gerät, auch wenn er kein HA-Gateway ist.

---

## 2. Fachliches Modell Eltako-Baureihe 14 (RS485)

Quellen: Eltako-Planungshilfe „RS485-Bus-Reiheneinbaugeräte Baureihe 14“ (07/2014, auch Quelle von
`bus_devices.py`), Bedienungsanleitungen FAM14 und FSNT14-12V/12W, Händler-Datenblätter. Annahmen sind
mit **(A)** markiert.

### 2.1 Bus und Master
- Geräte sitzen auf Hutschiene TH35; **Bus und 12 V DC laufen über Steckbrücken** von Gerät zu Gerät.
  Die Reihenfolge auf der Schiene ist frei wählbar.
- **FAM14** = Funk-Antennenmodul und **Bus-Master**, **2 TE (36 mm)**, mit **integriertem Schaltnetzteil
  12 V DC, bis 12 W** für alle Geräte; Eigenbedarf 0,8 W (Tabelle). Ohne FAM14 übernimmt **FTS14KS**
  die Masterrolle mit Netzteil (A: als zweiter Master-Typ vorsehen).
- **Bis zu 126 Kanäle** pro FAM14; **eine Geräteadresse je Kanal**, Mehrkanalgeräte bekommen beim
  Adressieren automatisch **fortlaufende** Adressen (FSR14-4x: 4, FSR14-2x: 2, FSB14: 2).
- Adressvergabe am FAM14 (Drehschalter BA auf 1, Aktor auf LRN) oder per PCT14. Ohne Adresse können
  z. B. FSU14 und FMSR14 nicht eingelernt werden, PCT14 kann das Gerät nicht auslesen.
- Reihenwechsel: flexibler **Busverbinder BBV14** (letztes Gerät rechts → erstes Gerät links der nächsten
  Schiene) oder **Busankoppler FBA14**. Anderer Verteiler: Busleitung (geschirmte Fernmeldeleitung,
  besser CAT7), Bus bis ca. 100 m.
- **Abschlusswiderstand 120 Ω** am letzten Gerät des letzten Strangs (liegt dem FAM14 bei), nur einmal.
  (A: die zweite Busseite ist im FAM14 abgeschlossen; die Planungshilfe spricht an anderer Stelle von
  „beiden Seiten“ – im Konzept prüfen wir nur „genau ein gesteckter Abschluss am Ende“.)

### 2.2 Gateways und IDs
- **FAM-USB**: reines USB-Funk-Gateway, **nicht am Bus**. HA erreicht Bus-Aktoren per Funk über den FAM14.
- **FGW14-USB** (1 TE) bzw. FAM14 am USB: **drahtgebundene** Bus-Gateways, sitzen selbst auf der Schiene
  (FGW14 bekommt eine Adresse, Drehschalter Pos. 10). In der Integration: `bus=True`, Bus-Gruppe.
- Rückmelde-ID: die ID, mit der ein Kanal seinen Status sendet. (A) Am Bus ist sie aus der Adresse
  abgeleitet, über Funk sendet der FAM14 sie mit seiner Base-ID + Adresse; die Integration speichert sie
  heute als Freitext (`feedback_id`) und soll das beibehalten, bis das FAM14-Lesen (Phase 3) die Werte liefert.

### 2.3 Stromversorgung
- FAM14 liefert 12 W. Laut aktueller FSNT14-Anleitung ab **> 8 W** Gesamtlast weiteres **FSNT14-12V/12W**
  (1 TE, 12 W), je 12 W Mehrbedarf eins; ältere Dokumente nennen 10 W bzw. 12 W. Das Panel nutzt heute
  2/3 (= 8 W) als Hinweis, 100 % als Fehler – beibehalten.
- **Jedes FSNT14 versorgt eine eigene Gruppe**, abgetrennt mit **Trennbrücke TB14** (liegt bei).
  Empfehlung: FSNT14 neben das letzte Gerät setzen. Parallel zum FAM14 (normale Brücke) nur als Redundanz.
- **Ab ca. 50 % Last** (≈ 6 W) zwischen nebeneinander sitzenden Netzteilen/Dimmern **½ TE Luft**
  (Distanzstück **DS14** bzw. lange Brücken); beim **FUD14** immer möglichst lange Brücken (½ TE).
- Konsequenz: Die Zuordnung „Netzteil ↔ Verbraucher“ ist **physisch** (Abschnitt zwischen TB14 in
  Einbaureihenfolge), nicht über Adressbereiche. Adressbereiche bleiben als Altdaten und Fallback.
  (A) Die Busleitung zwischen Schränken führt keine 12 V; jeder Schrank braucht ein eigenes Netzteil.

### 2.4 Typdaten (für den Katalog, nur technische Fakten)

| Typ | TE | Adressen/Kanäle | Busleistung (W, Planungshilfe) | Art |
|---|---|---|---|---|
| FAM14 | 2 | Master (keine) | 0,80 (liefert 12 W) | Master |
| FSR14-4x | 1 | 4 | 0,70 | Schalten |
| FSR14-2x | 1 | 2 | 0,14 | Schalten |
| FSR14SSR | 1 | (A) 2 | 0,40 | Schalten |
| F4SR14-LED | 1 | 4 | – (nicht in Tabelle) | Schalten |
| FSB14 | 1 | 2 | 0,42 | Rollladen |
| FUD14, FUD14/800W | 1 | 1 | 0,20 | Dimmen |
| FTN14 | 1 | 1 | 0,14 | Treppenlicht |
| FSU14 | 1 | 1 (A) | 0,14 | Schaltuhr |
| FWZ14-65A | 1 | 1 | 0,10 | Zähler |
| F3Z14D | 1 (A) | 3 (je Zählereingang, vom Nutzer bestätigt) | – (Anleitung: 0,10) | Zähler |
| FTS14EM | 1 | (A) je nach Drehschalter | 0,13 | Eingänge |
| FTS14TG | 1 | 1 | 0,42 (+ Bustaster, extern) | Eingänge |
| FGW14(-USB) | 1 | 1 | 0,50 | Gateway |
| FSNT14-12V/12W | 1 | – | – (liefert 12 W) | Netzteil |
| DSZ14DRS | 4 (A) | 1 | – | Zähler (am Ende einer Buslinie) |

Mit (A) markierte Werte vor Übernahme in `bus_devices.py` am Datenblatt prüfen.

---

## 3. Informationsarchitektur

### 3.1 Einstieg und Gruppierung
- Tab *Installation → Geräte → Bus* zeigt **einen Bus** (Auswahl-Chips, falls mehrere), **nicht** ein
  Gateway. Kopf mit zwei Karten:
  - **Bus-Master**: FAM14 (oder FTS14KS), Einbauort, Base-ID, „bis 126 Adressen“, Netzteil integriert.
  - **Zugang aus Home Assistant**: jedes Gateway, über das HA den Bus erreicht, mit Art der Verbindung:
    „Funk (FAM-USB, nicht am Bus)“ bzw. „drahtgebunden (FGW14-USB / FAM14-USB, Bus-Gruppe)“.
- **Mehrere Busse**: je FAM14/FTS14KS ein Bus mit eigenem Adressraum 1–126. Ein Gateway kann mehrere
  Busse erreichen (Funk), ein drahtgebundenes Gateway gehört genau zu einem Bus.
- **Mehrere Gateways**: Die Kanäle bleiben Subentries ihres Gateways (HA-Logik unverändert); die
  Bus-Ansicht führt sie über die Kanal-Zuordnung zusammen. Ein Kanal zeigt „gehört in HA zu Gateway X“.
- Ein **FGW14-USB** erscheint doppelt, aber konsistent: als Kachel auf der Schiene (Modul, Adresse,
  1 TE) **und** als Zugang „drahtgebunden“ im Kopf; beide verlinken aufeinander.

### 3.2 Ansichten (im Mockup umschaltbar)
1. **Übersicht**: Kennzahlen (Geräte, Kanäle/davon in HA, Adressen belegt von 126 inkl. Duplikate,
   Netzteile mit Status, Schränke·Reihen, Prüfungen), **Bus-Verlauf** (Reihe → BBV14 → Reihe → Busleitung →
   Schrank → Abschluss), Schrankkarten mit Mini-Schienen, die wichtigsten Prüfungen.
2. **Schrank**: Schrank wählen, jede Reihe als **Hutschiene, maßstäblich in TE** (Raster ½ TE). Kacheln je
   Modul mit Adressbereich, Typ, Kanal-LEDs (in HA / nur dokumentiert / frei), Warnpunkt; FAM14 als
   „MASTER“; Netzteile, Abstände (DS14 ½ TE), Trennbrücken (TB14), Abschlusswiderstand, Fremdgeräte
   (LS-Schalter, schraffiert, „nicht am Bus“) zur realistischen Belegung. Unter der Schiene **Bänder der
   Speiseabschnitte** (A/B/C … mit Last). Ablage „Ohne Einbauort“. Modus **Anordnen** (◀ ▶).
3. **Liste**: eine Zeile je Modul, darunter seine Kanäle; umschaltbar **nach Einbauort** (Bus-Reihenfolge)
   oder **nach Adresse** (mit „frei: x–y“-Zeilen und Block „ohne Bus-Adresse“), Suche, CSV.
4. **Adressen**: Adressplan 1–126 als Raster (belegt/frei/doppelt, Farbe nach Art), Klick → Kanal.
5. **Netzteile**: je Speiseabschnitt Netzteil(e), Einbauort, Lastbalken mit 8-W-Marke, Verbraucherliste
   mit Herkunft des Werts (Tabelle / eingetragen / kein Wert), Altbereich („bisher Adressen 1–8“).
6. **Prüfungen**: Fehler, Hinweise, Info, Bestanden – jede Meldung mit Sprung-Chips zu den Betroffenen.
7. **Detail-Drawer** (rechts, mobil vollflächig), Typen: **Modul**, **Kanal**, **Sender/Taster**,
   **Speiseabschnitt**, **Gateway**. Brotkrumen *Hausbus › Schrank › Reihe › Platz › Gerät › Kanal*,
   Zurück-Taste mit Verlauf, Esc schließt.

### 3.3 Verknüpfungen (alle anklickbar)

```
Bus ── Master (FAM14) ── Zugang: Gateway(s)
 └─ Schrank ── Reihe ── Platz ── Modul (Typ, TE, Netzteil-Abschnitt)
                                   └─ Kanal n ── Bus-Adresse ── Rückmelde-ID
                                        ├─ HA-Gerät/Entität (Subentry, Gateway)
                                        └─ Sender/Taster ── weitere Kanäle desselben Senders
Speiseabschnitt ── Netzteil(e) ── Verbraucher (Module)
```

- Modul → Schrank/Reihe/Platz (öffnet die Schrankansicht und hebt die Kachel hervor), → Netzteil-Abschnitt,
  → Kanäle, → Prüfungen zum Modul.
- Kanal → Modul, Einbauort, Entität (öffnet HA-More-Info), Funk-ID mit Gateway, Abschnitt,
  Sender/Taster; „Weg“ HA → Gateway → FAM14 → Adresse → Kanal.
- Sender → alle Kanäle, in die er eingelernt ist (z. B. Zentral-AUS), HA-Sender zusätzlich → Tab
  *Sender-IDs* (bestehend, `data-in-snd`).
- Adressplan-Zelle → Kanal; Duplikat → beide Kanäle.

### 3.4 Prüfungen

| Prüfung | Stufe |
|---|---|
| Bus-Adresse doppelt (auch über Mehrkanal-Bereiche) | Fehler |
| Speiseabschnitt überlastet (> 12 W je Netzteil) / ohne Netzteil | Fehler |
| Reihe zu voll / Module überlappen | Fehler (Eingabe wird abgelehnt) |
| Abschnitt über 2/3 (8 W) | Hinweis |
| Modul ohne Bus-Adresse | Hinweis |
| Modul ohne Einbauort | Hinweis |
| FUD14 ohne ½ TE Abstand; Netzteil/Dimmer nebeneinander > 6 W ohne DS14 | Hinweis |
| Abschlusswiderstand fehlt / mehrfach | Hinweis |
| Rückmelde-ID doppelt | Fehler |
| Kein Master dokumentiert / zwei Master an einem Bus | Fehler |
| Gerät ohne Leistungswert | Info |
| Adresslücken | Info |
| Kanäle nur dokumentiert (nicht in HA) | Info (Aktion „Als Gerät hinzufügen“) |
| Bisheriger Adressbereich eines Netzteils widerspricht der Einbaulage | Info (bestätigen/verwerfen) |
| Typ mit `BUS_MODEL`-Muster ohne Modulzuordnung | Hinweis (Aktion „zuordnen“) |

### 3.5 Bearbeiten
- Im Modul-Drawer: Schrank·Reihe (Auswahl), Platz in TE (½-Schritte), Breite (vorbelegt aus Katalog),
  erste Adresse (Kanäle fortlaufend), ½ TE Abstand links, Trennbrücke rechts, Abschluss. Prüfung beim
  Speichern (Reihe zu voll, Überlappung, Adresse 1…127−Kanäle). Duplikate werden gespeichert und gemeldet,
  nicht blockiert (die Doku soll den Ist-Zustand festhalten können).
- In der Schrankansicht: *Anordnen* (◀ ▶ tauscht mit dem Nachbarn bzw. schiebt um ½ TE).
  Später optional Drag & Drop.
- Schränke/Reihen anlegen, umbenennen, Breite in TE, Reihenfolge, Verbindung zur nächsten Reihe
  (BBV14/FBA14/Busleitung + Länge).
- Kanal einem HA-Gerät zuordnen (Auswahl der Subentries mit passendem Typ, nicht zugeordnet zuerst)
  oder als „nur dokumentiert“ benennen; „frei“ markieren.
- Speichern wie heute: verzögert (`SAVE_DELAY`) über WebSocket, State nur bei echten Änderungen.

### 3.6 Druck / Dokumentation
- „Drucken / PDF“: Kopf (Bus, Master, Zugang), je Schrank die Schienengrafik (Kacheln mit Typ +
  Adressen, Abschnittsbänder), danach die Liste nach Einbauort (Modul + Kanäle, Adresse, Rückmelde-ID,
  Entität, Sicherung) und die offenen Prüfungen. Bisheriger Abschnitt „Eltako-Bus“ in `docTables`/CSV
  wird auf Kanalzeilen mit Ort/Modul erweitert.
- Die Schienengrafik ist ein Schrank-Beschriftungsplan: optional „Etikettenstreifen“ je Reihe (Typ,
  Adressen, Kanalnamen kurz) zum Ausdrucken und Einkleben.

---

## 4. Datenmodell-Vorschlag

### 4.1 Grundsatz
- Config-Entry- und Subentry-Daten bleiben **unverändert** (kein neuer `SUBENTRY_SCHEMA`): die Bus-Doku
  ist Dokumentation, keine Betriebskonfiguration.
- Neu: ein **installationsweiter Store** `enocean_eltako.installation` (HA `Store`, Version 1), weil ein
  Bus nicht zu genau einem Gateway gehört. Die Notes je Gateway bleiben für alles andere.
- Bezug zu HA-Kanälen über den bestehenden `device_key` (Subentry-`unique_id`), der Löschen/Neuanlegen
  übersteht. Manuelle Kanäle stehen direkt im Modul.

```jsonc
{
  "buses": [{
    "id": "b1", "name": "Hausbus",
    "master": "m1",                    // Modul-ID des FAM14 / FTS14KS
    "base_id": "FF-9A-1C-80",          // von Hand, später aus dem FAM14 gelesen
    "access": [{ "entry_id": "…", "via": "radio" }],   // "wired" = Bus-Gruppen-Mitglied (abgeleitet)
    "bus_group": null,                 // Schlüssel der Bus-Gruppe, wenn drahtgebunden
    "terminator_note": ""
  }],
  "cabinets": [{
    "id": "c1", "name": "Keller-Verteiler", "area_id": "keller", "order": 0, "note": "",
    "rows": [{ "id": "r1", "name": "Reihe 1", "te": 12, "order": 0,
               "next": { "kind": "bbv14|fba14|cable|none", "to": "r2", "length_m": null } }]
  }],
  "modules": [{
    "id": "m2", "bus": "b1", "type": "FSR14-4X",          // Katalogschlüssel (normalisiert wie bus_power)
    "name": "Licht EG 1",
    "row": "r1", "slot": 3.0, "te": null,                 // null = aus Katalog
    "spacer_before": false, "separator_after": false, "terminator": false,
    "first_address": 1,                                    // null = noch keine
    "supply_watts": null,                                  // nur Netzteile / Master; null = Katalog
    "legacy_range": null,                                  // "1-8" aus Notes v7 (Netzteile)
    "power": "",                                           // eingetragene Busleistung, überschreibt Tabelle
    "circuit": "", "fuse": "", "installed": "", "revision": "", "note": "",
    "channels": [
      { "n": 1, "device_key": "05-10-A2-B3", "feedback_id": "00000081" },
      { "n": 4, "device_key": null, "name": "Licht Kellertreppe", "function": "Licht", "feedback_id": "00000084" },
      { "n": 3, "unused": true }
    ]
  }]
}
```

Regeln: Kanal-Adresse = `first_address + n − 1`; ein Kanal ohne Eintrag ist „unbekannt“; Speiseabschnitte
werden **berechnet** (Bus-Reihenfolge = Schrank-, Reihen-Reihenfolge, `slot`; Schnitt an
`separator_after` und am Schrankwechsel), nicht gespeichert. Lookups (device_key → Kanal, Adresse →
Kanal) über Dicts (CLAUDE.md).

### 4.2 Katalog
`bus_devices.py` wird zu einer Typtabelle (nur Zahlen, Quelle je Wert):
`BUS_TYPES = {"FSR14-4X": BusType(te=1, addresses=4, power=0.70, role="actuator"), "FAM14": BusType(te=2, addresses=0, power=0.80, supply=12.0, role="master"), "FSNT14-12V/12W": BusType(te=1, supply=12.0, role="supply"), …}`.
`bus_power()` bleibt als Wrapper. `docs/devices.md` kann eine Spalte „TE / Kanäle“ für Baureihe 14 bekommen
(generiert, CI-Prüfung bleibt).

### 4.3 Migration (getestet, CLAUDE.md)
- **Notes v7 → v8** (je Gateway): Felder `bus_address`, `feedback_id`, `bus_power`, `group` der Geräte,
  `supplies` und Bus-Felder von `manual` werden **in den Installations-Store übernommen** und in den Notes
  als `migrated_to_installation: true` markiert (Werte bleiben ein Release lang lesbar für Rückfall/Export).
- Einmaliger Aufbau des Installations-Stores beim ersten Laden:
  1. Je Gateway mit Bus-Geräten ein Bus „Bus (über <Gateway>)“, `access` = dieses Gateway (radio, bzw.
     wired bei `bus=True`). Gateways derselben `bus_group` → ein gemeinsamer Bus.
  2. Module bilden: Geräte mit gleichem `group` **und** gleichem Typ und zusammenhängenden Adressen → ein
     Modul, Kanäle nach Adresse; sonst ein Modul je Gerät. Kanalnummer = Adresse − erste Adresse + 1
     (bei Lücken Kanal „unbekannt“).
  3. `location` „Schrank · Reihe · Platz“ → Schrank/Reihe anlegen (Name), `slot` aus Platz, wenn Zahl;
     sonst bleibt das Modul „ohne Einbauort“ und der Text wandert in `note`.
  4. Netzteile → Module `FSNT14-12V/12W` (oder Name) ohne Einbauort, `legacy_range` = first–last; Prüfung
     „Bereich bestätigen“ bis sie platziert sind. Solange ein Abschnitt keine Lage hat, wird die alte
     Bereichslogik verwendet (kein Rückschritt für bestehende Nutzer).
  5. `manual` mit `bus_address` → Modul mit einem dokumentierten Kanal.
  6. Kein FAM14 dokumentiert → Platzhalter-Master „FAM14 (nicht dokumentiert)“ ohne Einbauort.
- **Doku-Export `VERSION = 3`**: neuer Block `installation` (buses/cabinets/modules); Import nimmt 1, 2, 3;
  1/2 laufen durch dieselbe Migration.
- Tests: Migration v7→v8 mit Fixtures (1 Gateway, 2 Netzteile mit Bereichen, FSR14-4x mit `group`,
  manueller F3Z14D, Freitext-Ort), Round-Trip Export/Import v3, Import v2 → v3.

### 4.4 Backend-Schnittstellen
- WebSocket: `enocean_eltako/installation` (lesen, in `documentation` eingebettet),
  `installation/set_module`, `set_cabinet`, `set_bus`, `remove_*` – jeweils Validierung im Backend
  (Adressen 1–126, ½-TE-Raster, Überlappung, max. Mengen wie `MAX_*`).
- Protokollschicht unberührt; Prüfungen als reine Funktion (testbar ohne HA) z. B. in
  `installation_checks.py`, Frontend rechnet dieselben Regeln für die Live-Anzeige.

---

## 5. Phasenplan

**Phase 1 – richtig gruppieren, Gerät mit Kanälen (jetzt)**
- Installations-Store + Migration v7→v8, Export v3.
- Bus-Ansicht: Kopf Master/Zugang (FAM-USB = Funk-Gateway), Liste Modul → Kanäle, Adressplan,
  Prüfungen (Duplikate, ohne Adresse, Lücken, nicht in HA), Modul-/Kanal-/Sender-Drawer mit Links.
- Einbauort strukturiert (Schrank/Reihe/Platz als Auswahl + Zahl statt Freitext).
- Netzteile weiter über Adressbereich **oder** Lage (wenn vorhanden).

**Phase 2 – Schrank und Speisung**
- Schrankansicht mit Hutschienen-Grafik in TE, Anordnen, Fremdgeräte, Reihenverbindungen.
- Speiseabschnitte nach Einbaulage (TB14), DS14/FUD14-/Abschluss-Prüfungen, Netzteil-Ansicht.
- Druck: Schienengrafik + Kanalliste, Etikettenstreifen.

**Phase 3 – aus dem Bus lesen**
- `protocol/bus/`: FAM14 über USB (Bus-Gruppe, on demand) – Geräte scannen, Typ, Adressen, Base-ID
  lesen; Abgleich „gelesen ↔ dokumentiert“ als Prüfung; Rückmelde-IDs ableiten.
- FGW14-USB als drahtgebundener Zugang sichtbar; „Als Gerät hinzufügen“ direkt aus einem gelesenen Kanal.
- Optional Import einer PCT14-Sicherung (Format klären).

---

## 6. Offene Fragen an den Nutzer

1. **Reihenbreite**: Haben deine Verteiler 12 TE je Reihe (oder 18/24)? Soll die Breite je Reihe frei sein
   (Vorschlag: ja, Vorgabe 12)?
2. **Fremdgeräte** (LS, FI, Klemmen) in der Schienengrafik mitführen – ja als einfache Platzhalter-Blöcke,
   oder nur Bus-Geräte?
3. **Netzteile**: Sind deine zwei FSNT14 wirklich über Trennbrücken getrennt (eigene Gruppen) oder parallel
   zum FAM14 (Redundanz)? Die bisherigen Bereiche 1–8 / 9–126 passen physisch nicht zum Speisekonzept.
4. **F3Z14D**: belegt es eine Adresse oder eine je Zählereingang? Breite 1 TE?
5. **Rückmelde-ID**: Woher stammen deine Werte (00000081 …) – aus PCT14, aus dem Monitor? Soll die
   Integration sie später aus Adresse + Base-ID vorschlagen?
6. **Mehrere Busse**: Gibt es (geplant) einen zweiten FAM14/FTS14KS? Sonst Bus-Auswahl ausblenden, bis es
   mehr als einen gibt.
7. **Kanal ↔ HA-Gerät**: Ist „ein Subentry = ein Kanal“ für dich richtig, oder soll ein FSR14-4x später
   auch in HA ein Gerät mit 4 Entitäten werden (wäre eine Subentry-Schemaänderung, nicht Teil dieses
   Konzepts)?
8. Soll der **FAM14 als HA-Gateway** (USB, Bus-Gruppe) eingerichtet werden können/sein, oder bleibt bei dir
   der Zugang ausschließlich per Funk über das FAM-USB?
9. Drag & Drop in der Schrankansicht wichtig, oder reichen ◀ ▶ und das Formular?

---

## 7. Annahmen (Sammlung)
- Busleitung zwischen Schränken führt keine 12 V → jeder Schrank eigener Speiseabschnitt.
- Kanal-/Adressanzahl FSR14SSR, FSU14, F3Z14D, FTS14EM; TE von F3Z14D, DSZ14DRS.
- Abschluss: „genau ein gesteckter Widerstand am Ende“ (FAM14-Seite intern).
- Rückmelde-ID = Base-ID FAM14 + Adresse über Funk (nur als Vorschlag, nie überschreiben).
- Beispieldaten im Mockup (Base-ID FAM14, zweiter Schrank, FTS14TG mit 11,2 W inkl. Bustaster) sind
  erfunden, um alle Zustände zu zeigen.

## Quellen
- Eltako, *RS485-Bus-Reiheneinbaugeräte Baureihe 14 – Planungshilfe und Betriebsanleitung* (07/2014),
  Kap. 1 und 3 (Aufbau, Adressvergabe, BBV14/FBA14, Abschluss, Leistungstabelle).
- Eltako, Bedienungsanleitung FAM14 (30014000): https://www.eltako.com/fileadmin/downloads/de/_bedienung/FAM14_30014000-7_dt.pdf
- Eltako, Bedienungsanleitung FSNT14-12V/12W (30014062): https://www.eltako.com/fileadmin/downloads/de/_bedienung/FSNT14-12V12W_30014062-2_dt.pdf
- Händlerdaten FSNT14 (TB14, DS14, 8-W-Grenze): https://industry-electronics.com/eltako/30014062-fsnt14-12v-12w-switching-power-supply-30-014-062-printview-872741.htm
- Händlerdaten FWZ14-65A (1 TE): https://industry-electronics.com/eltako/30014050-fwz14-65a-radio-ac-meter-transmitter-module-printview-170659.htm

## Entscheidungen des Nutzers zu den offenen Fragen

| Frage | Entscheidung |
|---|---|
| Reihenbreite | 12 TE pro Reihe als Standard, pro Reihe einstellbar |
| FSNT14 am FAM14 | Getrennt mit TB14; Leistung je Abschnitt nach Einbauposition |
| Geräte ohne Bus (LS, FI, Zähler) | Ja, als einfache Platzhalter (Name + TE-Breite) auf der Schiene |
| Zweiter Bus / FAM14 als Gateway | Ein Bus, FAM14 vorerst nur dokumentiert; Modell bleibt mehrbusfähig |
| F3Z14D | Eine Bus-Adresse pro Zählereingang (3 Adressen); TE-Breite bleibt Annahme (A) |
| Rückmelde-ID | Aus FAM14-Konfiguration / PCT14, von Hand eingetragen; Auslesen am Bus in Phase 3 |
| Gerätemodell | Subentry = Kanal; Gerät nur im neuen Installationsspeicher / in der Doku-Ansicht |
| Drag and Drop | Nein; Bearbeiten per Formular, Drag and Drop später |

Das Mockup zeigt den F3Z14D jetzt dreikanalig (Adressen 12–14, Kanäle L1–L3); alle folgenden Adressen sind um 2 verschoben, die absichtliche Doppelvergabe liegt nun bei Adresse 18.

## Entscheidungen bei der Umsetzung (Phase 1)

Grundsatzfragen, die das Konzept offen ließ, entschieden nach CLAUDE.md:

| Frage | Entscheidung |
|---|---|
| Notizen nach der Übernahme | Der Installationsspeicher ist führend. Die Notizen behalten `bus_address`, `feedback_id`, `bus_power`, die Netzteile und die Bus-Einträge von Hand als **Kopie, die der Speicher bei jeder Änderung zurückschreibt** (nur echte Änderungen). So zeigen Tabelle, Sender-IDs, Druck und CSV dieselben Werte; eine Änderung in diesen älteren Feldern wird in den Speicher übernommen. Kein Doppelpflegen, kein Rückschritt für die bestehenden Ansichten. |
| Adresse eines Mehrkanal-Moduls aus einem alten Feld | Verschiebt das ganze Modul (Adressen bleiben fortlaufend: erste Adresse = Adresse − Kanal + 1). Leeren der Adresse eines Kanals in einem Mehrkanal-Modul wird dort ignoriert (nur im Drawer). |
| Leistung eines Mehrkanal-Moduls in den Notizen | Steht am ersten verknüpften Kanal, die anderen sind leer: das Modul zählt einmal. |
| Freitext-Ort, der nicht „Schrank · Reihe · Platz“ ist | Bleibt als `legacy_location` am Modul („bisher: …“), nicht in der Notiz; Schrank und Reihe werden nur für einen vollständigen, passenden Ort angelegt. |
| Welche HA-Geräte die Übernahme aufnimmt | Mit Bus-Feld **oder** einem Typ der Baureihe 14 (Muster `F…14`). Später hinzugekommene Geräte werden nicht automatisch aufgenommen (sonst kämen entfernte Kanäle beim Neustart zurück), sondern als Prüfung „ohne Modul“ mit Aktion „hinzufügen“ gemeldet. Ein Import alter Exporte nimmt nur Geräte mit Bus-Feld. |
| Netzteile aus den Notizen | Modul mit Rolle Netzteil; `type` entspricht dem Namen des alten Netzteils, `legacy_range` dem Bereich, `supply_id` hält die Verbindung. Neu in der Bus-Ansicht angelegte Netzteile stehen nur im Speicher. |
| Bus-Einträge von Hand | Bleiben in den Notizen und sind per `manual_id` mit ihrem Kanal verbunden. Wird das Modul in der Bus-Ansicht entfernt, geht auch der Eintrag; verliert der Eintrag in einer alten Ansicht seine Bus-Adresse, verliert er nur seinen Kanal. |
| Netzteil-Last | Nach Lage, sobald jedes Netzteil (und der Master) einen Einbauort hat: Abschnitte in Bus-Reihenfolge, Schnitt nach `separator_after` (TB14) und am Schrankwechsel; der FAM14 zählt dort als Netzteil (12 W) und Verbraucher (0,8 W). Sonst über Adressbereiche wie bisher: der FAM14 zählt nur, wenn kein Netzteil eingetragen ist. Die Bänder unter der Schiene bleiben Phase 2. |
| Prüfungen im Frontend | Der Server rechnet sie (`installation_checks.py`, reine Funktion) und liefert sie mit den Daten; das Frontend rechnet sie nicht nach. Nach jeder Änderung liest das Panel die Dokumentation neu. Eine Meldung je Art (z. B. „3 Geräte ohne Einbauort“) mit Sprung-Chips. |
| Websocket-Befehle | `enocean_eltako/installation`, `installation/set` und `installation/remove` mit `kind` = module, cabinet oder bus (statt je eines Befehls). Antwort: Speicher, Prüfungen, Katalog. |
| Gateway gelöscht | Es verschwindet aus dem Zugang der Busse; die Kanäle bleiben dokumentiert (Prüfung „nicht mehr in Home Assistant“). Der Speicher wird nicht gelöscht. |
| Fremdgeräte | Rolle `foreign` ist im Datenmodell vorhanden (Name, TE, ohne Adresse und Leistung); Darstellung auf der Schiene ist Phase 2. |
| Katalogannahmen | Als `assumed` je Feld markiert: Adressen von FSR14SSR und FSU14, TE von F3Z14D und DSZ14DRS. Typen ohne bekannte TE oder Adressen zeigen „–“ (Breite 1 TE, Kanäle wie eingetragen). |

Nicht gebaut (Phase 2): Schrankgrafik mit Hutschiene, Anordnen, Bänder der Speiseabschnitte, Prüfungen zu DS14/FUD14/Abschluss, Druck mit Schienengrafik.
