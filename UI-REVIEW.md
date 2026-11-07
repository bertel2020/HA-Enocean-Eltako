# UI-Review: HA EnOcean Eltako

Stand: 3. November 2026

## Status (7. November 2026)

Stand der Befunde nach dem Code-Review vom 7. November 2026 (`CODE-REVIEW.md`):

| Befund | Status |
| --- | --- |
| P3 Gerätetyp geht beim Leeren verloren | Erledigt: `bus.js` stellt den vorherigen Wert bei leerem Feld wieder her. |
| P2 Ungespeicherte Drawer-Eingaben | Erledigt: `_bvGuard()` fragt nach; seit dem Review auch bei Zurück, Links und Bus-Wechsel. |
| P2 Drawer nicht vollständig modal | Erledigt: Hintergrund wird inert, der Fokus kehrt zum Auslöser zurück. |
| Navigation 4: native `confirm()` | Größtenteils erledigt: der Bus nutzt Panel-Dialoge; offen bleibt `window.confirm` beim Dokumentationsimport (`monitor-panel.js`). |
| Navigation 1–3 (Begriffe, Übernahme, Aktionsmuster) | Offen. |
| Optische Empfehlungen 1–5 | Offen. |

## Umfang und Gesamteindruck

Geprüft wurden vor allem das eigene Home-Assistant-Panel, die Konfigurationsoberflächen, die deutschen Texte und die vorhandenen Showcase-Screenshots. Der Schwerpunkt liegt auf Bedienbarkeit, visueller Gestaltung, Navigation und Konsistenz. Es handelt sich um ein Code- und Screenshot-Review, nicht um einen Test an einer laufenden Home-Assistant-Instanz.

Das Panel hat bereits eine erkennbare visuelle Sprache: Karten, Chips, Tabellen, Statusfarben und Abstände sind weitgehend einheitlich. Die Hauptansichten Telegramme, Geräte und Anlage sind grundsätzlich verständlich. Die größten Verbesserungsmöglichkeiten liegen bei der Orientierung zwischen ähnlichen Bereichen, bei der Gewichtung von Informationen und bei einigen Interaktionen im Anlagen-Drawer.

## Konkrete Befunde

### P3: Gerätetyp kann beim Leeren oder Teiltippen verloren gehen

In `custom_components/enocean_eltako/frontend/monitor-panel.js` (ab Zeile 1220) leert `focusin` den bestehenden Wert des Typ-Feldes, damit die Datalist alle Optionen zeigt. In `bus.js` verarbeitet `_busInput` das `change`-Ereignis und zeichnet das Formular mit dem gelesenen Wert neu. Das Leeren geschieht per Skript; der Browser feuert `change` nur bei Nutzeränderungen. Fokus und Blur ohne Eingabe sind daher unkritisch, `focusout` stellt den Wert wieder her. Riskant ist der Fall, dass der Nutzer den Text selbst löscht oder halb tippt und das Feld verlässt: dann liest `_busInput` den leeren oder unvollständigen Wert und zeichnet das Formular damit neu.

**Vorschlag:** Bei leerem Feld den vorherigen Wert übernehmen, bevor neu gezeichnet wird.

### P2: Ungespeicherte Eingaben im Anlagen-Drawer gehen leicht verloren

`_bvClose` in `custom_components/enocean_eltako/frontend/bus.js` (Zeile 1215) entfernt Drawer und Entwurf unmittelbar. Escape, Schließen und der Klick auf den Hintergrund führen dorthin. Auch der Wechsel zu einem anderen Objekt kann den aktuellen Formularzustand ersetzen. Bei Formularen mit vielen Feldern ist versehentlicher Datenverlust wahrscheinlich.

**Vorschlag:** Änderungen am Formular erkennen. Beim Schließen oder Wechsel mit ungespeicherten Änderungen eine kurze Bestätigung mit „Weiter bearbeiten“ und „Änderungen verwerfen“ zeigen. Nach dem Speichern den Zustand als sauber markieren.

### P2: Der modale Drawer ist per Tastatur nicht vollständig modal

Der Drawer wird in `bus.js` (Zeile 893) mit `role="dialog"` und `aria-modal="true"` ausgegeben. `_bvOpen` setzt Fokus auf die Schließen-Schaltfläche, aber es gibt keine Fokusbegrenzung im Drawer. Beim Schließen kehrt der Fokus nicht zum auslösenden Element zurück. Dadurch können Tastaturnutzer hinter den sichtbaren Dialog navigieren und verlieren nach dem Schließen ihren Ausgangspunkt.

**Vorschlag:** Hintergrund während des Dialogs inert machen oder den Fokus im Drawer halten; beim Schließen den vorherigen Auslöser wieder fokussieren. Escape sollte zusätzlich `preventDefault()` nutzen, wenn es den Dialog schließt.

## Navigation und Konsistenz

1. **Zwei Bedeutungen von „Geräte“.** Die Hauptansicht zeigt erkannte beziehungsweise aktive Geräte; innerhalb von „Anlage“ gibt es erneut eine Geräteansicht für die Dokumentation. Die Begriffe machen den Unterschied nicht klar. Eine Benennung wie „Erkannte Geräte“ und „Anlagendokumentation“ würde die Aufgaben deutlicher trennen.
2. **„Übernahme“ steht auf derselben Ebene wie Alltagsansichten.** Telegramme, Geräte und Anlage sind wiederkehrende Aufgaben; die Übernahme ist ein einmaliger Prozess. Sie könnte nach Abschluss aus der Hauptnavigation verschwinden oder unter Einrichtung/Mehr liegen. Ein verbleibender Bericht kann über einen klaren Link erreichbar bleiben.
3. **Ähnliche Aktionen öffnen unterschiedliche Oberflächen.** Gerätedetails erscheinen teils in der Zeile, Bearbeitung teils als Inline-Formular und teils im seitlichen Drawer. Eine feste Regel würde helfen: Zeile öffnet Lesedetails, „Bearbeiten“ öffnet den Bearbeitungs-Drawer.
4. **Bestätigungen sind uneinheitlich.** Der Anlagen-Bus verwendet native `confirm()`-Dialoge (`bus.js`, Zeilen 1294 und 1315; dazu `window.confirm` in `monitor-panel.js`, Zeile 2537), andere Bereiche verwenden Bestätigungen im Panel. Einheitliche Panel-Dialoge mit konkretem Objektnamen würden besser zur Gestaltung passen.

## Optische Empfehlungen

### 1. Anlagenansicht beruhigen

In der Geräteansicht der Anlage konkurrieren Untertabs, Filterchips, Suchfeld, Gruppierung, Fortschritt und Tabellenkopf. Die häufigsten Filter sollten in eine kompakte Zeile; seltenere Filter können hinter „Filter“ liegen. Der Bereich „Dokumentation vervollständigen“ mit Ort und Sicherung sollte als eigene Aufgabe unter der Suche stehen. Das verbessert die Hierarchie ohne Neugestaltung.

### 2. Kleine Metadaten besser lesbar machen

Mehrere Nebeninformationen in Karten, Tabellen und Formularen liegen bei 11–12 px. Für normale Desktop-Ansichten wären 13–14 px als Untergrenze angenehmer. Hierarchie lässt sich über Gewicht und Ton statt über immer kleinere Schrift erzeugen. Die vorhandene Schriftgrößen-Einstellung ist hilfreich, ersetzt aber keine gut lesbare Grundeinstellung.

### 3. Hauptaktionen mit Text zeigen

In der Telegrammleiste stehen Pause, Senden, Export und Löschen vor allem als Symbole. „Telegramm senden“ ist eine zentrale Aktion und sollte mindestens auf breiteren Ansichten als beschrifteter Button erscheinen. Export und Löschen können im Mehr-Menü bleiben. Die Symbolschaltflächen sollten ihre Tooltips und zugänglichen Namen behalten.

### 4. Akzentfarbe gezielter einsetzen

Blau markiert Navigation, Filter, Links, Typen und Aktionen. Für aktive Navigation und primäre Aktionen ist das sinnvoll. Typkategorien können ihre eigenen Farben behalten, aber sekundäre Links und Filter sollten zurückhaltender sein, damit Warnungen und aktive Zustände schneller auffallen.

### 5. Gerätedetails nach Nutzerfragen ordnen

Die erste Ebene sollte Name, Zustand, letzte Aktivität und wichtigste Werte zeigen. Verknüpfungen und Einstellungen folgen danach. Rohtelegramme und technische Kennungen können in einem eingeklappten Abschnitt stehen. So lässt sich die häufige Frage „Funktioniert dieses Gerät?“ schneller beantworten.

## Empfohlene Reihenfolge

1. Drawer-Änderungen schützen und Tastaturfokus korrekt führen.
2. Typ-Feld gegen Wertverlust beim Leeren absichern (P3).
3. Begriffe für erkannte Geräte und Anlagendokumentation schärfen.
4. Anlagenansicht visuell vereinfachen und kleine Schrift anheben.
5. Aktionsmuster und Bestätigungsdialoge vereinheitlichen.

## Verifikation und Grenzen

`node scripts/check_panel.mjs` lief erfolgreich. `node scripts/check_panel_render.mjs` lief erfolgreich für Deutsch und Englisch sowie die vorhandenen Ansichten. Diese Prüfungen bestätigen die grundsätzliche Renderbarkeit, decken Fokusführung, versehentlichen Verlust von Eingaben und die tatsächliche Darstellung in Home Assistant aber nicht vollständig ab. Die Showcase-Screenshots dienten als visuelle Referenz; sie müssen nicht exakt dem aktuellen uncommitteten Stand entsprechen.
