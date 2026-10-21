# Einlernfunktionen der Eltako-Aktoren Baureihe 14

[English](teach_in.md)

Welche Einlernfunktion am Aktor für welchen Einlern-Button einer Geräteseite einzustellen
ist. Entnommen aus den Bedienungsanleitungen FSR14-4x (30014001-6), FUD14 (30014005-3),
FSB14 (30014004-7) und FHK14 (30014014-1). Andere Stände und die Aktoren der Baureihen
61/62 nummerieren ihre Funktionen anders: im Zweifel die Anleitung des eigenen Geräts
prüfen.

## Ablauf

1. Nur FSR14-4x: mit dem unteren Drehschalter den Kanal wählen (1 bis 4 oder 1..4).
2. Den oberen Drehschalter auf die Einlernfunktion aus der Tabelle stellen.
3. Den mittleren Drehschalter auf **LRN** stellen; die LED blinkt ruhig.
4. Den Einlern-Button auf der Geräteseite in Home Assistant drücken. Die LED erlischt.
5. Für weitere Sender den mittleren Drehschalter kurz von LRN wegdrehen und bei 2.
   beginnen. Danach die Drehschalter wieder auf ihre Betriebsstellungen (AUTO, Zeiten)
   stellen.

Damit der Aktor mit einem Bestätigungstelegramm antwortet, braucht er eine Geräteadresse,
und der obere Drehschalter des FAM14 muss beim Einlernen auf Position 2 stehen.

## Tabelle

„Beliebig“ heißt, die Anleitung verlangt für diesen Sender keine Einlernstellung.

| Einlern-Button | FSR14-4x | FUD14 | FSB14 | FHK14 |
|---|---|---|---|---|
| Einlernen Taster (Schalter, Dimmer) | 0 Richtungstaster; 5 Universaltaster ES; 10 Universaltaster ER | LC2 Richtungstaster; EC2 Universaltaster | – | – |
| Einlernen Zentralbefehl | beliebig (Controller) | PCT | – | – |
| Einlernen Richtungstaster (Rollladen) | – | – | 10 Motor 1; 30 Motor 2 | – |
| Einlernen Controller (Rollladen) | – | – | 180 Motor 1; 200 Motor 2 | – |
| Einlernen Controller (Heizung) | – | – | – | Rechtsanschlag (4.5) |
| Virtueller Taster als Zentraltaster | 45 ein, 90 aus; 15 ein, 20 aus mit Priorität | LC1 Zentral ein; EC1 Zentral aus | 60 ohne Priorität; 90 mit Priorität (Tasten schaltet sie um) | – |
| Einlernen Fensterkontakt | beliebig (der mittlere Drehschalter AUTO 1–4 bestimmt die Logik) | LC2 Schließer; LC3 Öffner | 20 Motor 1; 40 Motor 2, richtet zugleich den Aussperrschutz ein | Rechtsanschlag (4.5) |
| Einlernen Bewegung | beliebig | – | – | – |
| Einlernen Temperatur | – | – | – | der Hysterese-Drehschalter bestimmt beim Einlernen die Solltemperatur (2.5 = 21 °C, 0.5 = 17 °C, 4.5 = 25 °C) |
| Helligkeitssensor einlernen | beliebig; danach legt der obere Drehschalter die Schaltschwelle fest | – | 150 (Motor 1 und 2) | – |
| Wetterstation einlernen | – | – | beliebig; entweder ein FAH60 oder ein FWS61 | – |
| Szenen-Buttons | 30 | LC4 | 180 Motor 1; 200 Motor 2 | – |

Ein Strich heißt, die Anleitung nennt für diesen Sender keine Einlernfunktion; über das
PC-Tool PCT14 kann der Aktor ihn trotzdem annehmen.

## Welchen virtuellen Sensor welcher Aktor annimmt

Aus der Tabelle oben abgelesen (Anleitung des Aktors, nicht an Hardware geprüft). **Ja** heißt,
die Anleitung nennt eine Einlernfunktion, **nein**, dass sie keine nennt (über PCT14 kann er
trotzdem möglich sein).

| Virtuelles Gerät | FSR14-4x | FUD14 | FSB14 | FHK14 |
|---|---|---|---|---|
| Fensterkontakt | ja | ja | ja (Aussperrschutz) | ja |
| Bewegungsmelder | ja | nein | nein | nein |
| Temperaturfühler | nein | nein | nein | ja (legt auch die Solltemperatur fest) |
| Helligkeitssensor (FAH60-Format) | ja | nein | ja | nein |
| Wetterstation (FWS61-Format) | nein | nein | ja | nein |
| Taster als Zentraltaster | ja | ja | ja | nein |
| Szenentaster | ja | ja | ja | nein |

Noch nicht erfasst: FAE14SSR und die Aktoren der Serien 61/62 (FSR61, FSB61, FUD61, FD62,
FJ62). Ihre Anleitungen nennen andere Einlernstellungen; eine Spalte ergänzen, sobald sie
geprüft sind.

## Aussperrschutz

Ist ein Fensterkontakt in einen FSB14 eingelernt, sperrt der Aktor Zentral-Ab und
Szene-Ab, solange der Kontakt „offen“ meldet. Beim virtuellen Kontakt in den Optionen
**Mit Priorität senden** einschalten: Sein Telegramm überholt dann alle Befehle in der
Sendewarteschlange, sodass „offen“ den Aktor vor einem gleichzeitig gesendeten
Zentral-Ab-Befehl erreicht.
