# Code-Review: HA EnOcean Eltako

Stand: 7. November 2026

## Umfang und Gesamturteil

Geprüft wurden die Home-Assistant-Integration, die Python-WebSocket-Endpunkte und insbesondere das mehrteilige JavaScript-Panel. Dazu kamen die vorhandenen Showcase-Screenshots, statische Prüfungen und die Testsuite. Es war ein Code- und Screenshot-Review; eine laufende Home-Assistant-Instanz und echte EnOcean-Hardware wurden nicht geprüft. Der Anwendungscode wurde im Rahmen des Reviews nicht verändert.

**Gesamturteil:** Die Integration ist technisch solide und gut getestet. Protokollcode und Home-Assistant-Anbindung sind klar getrennt; die Panel-Gestaltung ist weitgehend einheitlich. Die wichtigsten Verbesserungen betreffen die Zuordnung von Geräten bei mehreren Gateways, den Schutz ungespeicherter Formulareingaben und die Wartbarkeit der großen Frontend-Module.

| Bereich | Bewertung |
| --- | --- |
| Codequalität | Gut: klare Schichten, verständliche Benennung, umfangreiche Tests. Die großen JS-Dateien machen Änderungen und Reviews aufwendig. |
| Sicherheit | Gut, soweit statisch prüfbar: Panel und WebSocket-Befehle verlangen Admin-Rechte; Eingaben werden serverseitig validiert und dynamische HTML-Werte überwiegend maskiert. Kein vollständiger Sicherheitstest. |
| Konsistenz | Technisch überwiegend gut. In der UI bezeichnet „Geräte“ sowohl eine Hauptansicht als auch einen Bereich unter „Anlage“. |
| Logik | Im Normalfall plausibel; relevante Randfälle bei mehreren Gateways und beim Verlassen eines ungespeicherten Drawers. |
| Usability und Look & Feel | Einheitliche Karten, Statusfarben und Abstände; Telegramme sind gut lesbar. Die Anlagenansicht ist dicht, kleinere Metadaten und reine Symbolaktionen kosten Aufmerksamkeit. |

## Priorisierte Befunde

### P2: Geräteansicht vermischt Sender und Gateway

`frontend/monitor-panel.js` baut die Liste eingerichteter Geräte in `_deviceItems()` mit einer Map auf, deren Schlüssel nur die Sender-ID ist (um Zeile 3025). Empfangene Telegramme werden dagegen nach Gateway und Sender gruppiert. Hören mehrere Gateways denselben Sender, kann die Gerätezeile Metadaten eines Geräts mit dem Gateway des Telegramms kombinieren. Detail- und Sender-Test-Abfragen verwenden anschließend diese Kombination (um Zeile 3733 bzw. 3748). Das kann zu falschen Angaben oder fehlgeschlagenen Aktionen führen. Beim Entfernen prüft der Server die Subentry-ID, sodass ein fremdes Gerät nicht einfach unter dem falschen Gateway entfernt wird.

**Empfehlung:** Die Beziehung zwischen Sender, konfiguriertem Gerät und dessen Eigentümer-Gateway explizit modellieren. Für gerätebezogene Aktionen immer das Gateway des konfigurierten Geräts verwenden. Einen Test mit zwei Gateways ergänzen, die denselben Sender hören.

### P2: Ein Navigationspfad umgeht den Schutz ungespeicherter Drawer-Eingaben

Der Anlagen-Drawer fragt beim regulären Schließen über `_bvGuard()` nach, bevor ungespeicherte Änderungen verworfen werden (`frontend/bus.js`, um Zeile 1235). In `_busClick()` werden Drawer und Entwurf bei Klicks auf `[data-in-goto]` oder `[data-in-snd]` jedoch direkt gelöscht (um Zeile 1308). Der Bus-Wechsel setzt den Drawer ebenfalls direkt zurück (um Zeile 1325). Diese Pfade sollten denselben Schutz verwenden.

**Empfehlung:** Alle Wege, die Drawer, Entwurf oder aktiven Bus wechseln, über eine gemeinsame asynchrone Guard-Funktion führen. Den Verlustfall durch einen gezielten Interaktionstest abdecken.

### P3: Falsche Base-ID in der Rückmeldung eines Dokumentationsimports

`websocket.py` speichert beim Einlesen der Gateways eine Variable `base_id` (um Zeile 745). Bei der späteren Antwort für ein nicht zugeordnetes Gateway wird diese Variable erneut verwendet (um Zeile 768), statt dessen eigene Base-ID zu lesen. Sind mehrere Gateways im Import nicht zugeordnet, zeigt die Rückmeldung für sie die Base-ID des zuletzt durchlaufenen Gateways. Die eigentliche Zuordnung beim Import ist davon getrennt.

**Empfehlung:** In der Ergebnis-Schleife `gateway.get("base_id")` verwenden und einen Import mit zwei nicht zugeordneten Gateways testen.

### Skalierungsrisiko: Lineare Gerätesuche für jedes Telegramm

`describe()` in `websocket.py` (um Zeile 231) durchsucht für jedes Telegramm die Geräte aller geladenen Gateways. Bei vielen Geräten und hoher Telegrammrate erhöht das die Arbeit pro Nachricht; die Historie durchläuft denselben Pfad. Ein messbarer Engpass wurde ohne Lasttest nicht nachgewiesen.

**Empfehlung:** Sender-ID zu Gerät und Gateway indizieren und die Wirkung bei realistischen Geräte- und Telegrammzahlen messen.

## Panel und Bedienung

- Die Telegrammansicht setzt eine klare Hierarchie aus Gateway-Status, Suche, Filtern und Tabelle. Karten, Chips und Statusfarben wirken zusammenhängend.
- In „Anlage“ folgen mehrere Navigations-, Filter- und Aktionszeilen direkt aufeinander. Häufige Aufgaben sollten deutlicher hervortreten; seltene Optionen können hinter „Filter“ oder „Mehr“ liegen.
- „Geräte“ als Hauptansicht und „Geräte“ innerhalb von „Anlage“ sollten sprachlich unterschieden werden, etwa erkannte Geräte gegenüber Anlagendokumentation.
- Kleine Nebeninformationen und nur durch Symbole bezeichnete Hauptaktionen sollten auf Lesbarkeit und Verständlichkeit in Desktop- und Mobilansicht geprüft werden.
- Ein älteres `UI-REVIEW.md` enthält teils inzwischen behobene Punkte: Der Drawer besitzt mittlerweile eine Änderungsabfrage und eine Tastatur-Fokusbegrenzung. Die oben genannten Umgehungspfade bleiben relevant.

## Wartbarkeit und Testsignal

Die Frontend-Module sind groß: `monitor-panel.js` umfasst rund 3800, `installation.js` rund 2300 und `bus.js` rund 1600 Zeilen. Die Aufteilung in Dateien ist sinnvoll, innerhalb dieser Dateien sind Zustandsänderungen und asynchrone UI-Abläufe aber schwer zu überblicken. Weitere, fachlich abgegrenzte Module und gezielte Tests für Mehr-Gateway- und Formular-Randfälle würden Änderungen erleichtern.

Die vollständige Testsuite meldete **1949 bestanden, 1 übersprungen, 114 xfailed und 501 xpassed**. Die vielen XPASS stammen aus nicht strikten Xfail-Markierungen für bislang unbestätigte offizielle EEP-Profile (`tests/protocol/test_eep_official.py`). Sie sind kein Testfehler, schwächen aber die Aussagekraft einer grünen Gesamtsuite; bestätigte Profile sollten nach Prüfung aus der Xfail-Liste entfernt werden.

## Verifikation und Grenzen

- `node scripts/check_panel.mjs`: bestanden.
- `node scripts/check_panel_render.mjs`: bestanden für Deutsch, Englisch und die geprüften Ansichten.
- `ruff check custom_components/enocean_eltako`: bestanden.
- Gezielte Backend-Tests für Monitor, Anlage und Dokumentation: 60 bestanden.
- Vollständige Python-Testsuite: 1949 bestanden, 1 übersprungen, 114 xfailed, 501 xpassed; keine unerwarteten Fehlschläge.

Die genannten Randfälle sind anhand des Codes nachvollzogen, aber noch nicht durch eigene Regressionstests oder eine laufende HA-Instanz bestätigt. Das visuelle Urteil beruht auf den vorhandenen Showcase-Screenshots; sie müssen nicht jeden aktuellen Zustand des Panels zeigen.
