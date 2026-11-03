# Unterstützte Geräte

[English](devices.md)

Aus dem Gerätekatalog von `scripts/gen_device_docs.py` erzeugt; nicht von Hand ändern.
Jedes Profil heißt EEP plus Variante (`std` = Definition der EnOcean Alliance,
`eltako` = Eltako-Variante, dokumentiert in `protocol/eep/eltako/`).

## Gateways

Ein Eintrag pro Gateway. Serielle Gateways verbinden per USB oder, über ser2net
oder die App Device Proxy, per TCP.

| Gateway | Anbindung |
| --- | --- |
| Eltako FGW14-USB | Eltako-Bus der Baureihe 14 (RS485) per USB; bildet mit dem FAM14 eine Bus-Gruppe |
| Eltako FAM14 | Eltako-Bus der Baureihe 14 (RS485); kann getrennt bleiben, bis er gebraucht wird |
| Eltako FAM-USB | USB-Funkgateway (ESP2) |
| PioTek MGW-ETH | Netzwerk (TCP, ESP3), wird automatisch gefunden |
| Symcon EnOcean LAN Gateway | Netzwerk (TCP, ESP3) |
| Generisch ESP3 (USB 300, TCM 310 …) | Beliebiges ESP3-Gateway per USB oder TCP |
| Generisch ESP2 | Beliebiges ESP2-Gateway per USB oder TCP |

## Geräte des Katalogs

Empfängt: Telegramme, die das Gerät an Home Assistant sendet. Sendet: Sender-Profile,
mit denen Home Assistant es steuert, je mit eigener Sender-ID aus dem Pool des Gateways.
Hardware: ✓, wenn das Repository einen echten Mitschnitt dieses Modells enthält, den die Tests
abspielen; ein Modell ohne ✓ folgt der Dokumentation des Herstellers. Mitschnitte sind willkommen,
siehe [CONTRIBUTING](../CONTRIBUTING.md).

| Kategorie | Gerät | Hersteller | Empfängt | Sendet (Sender-Profile) | Entitäten | Hardware |
| --- | --- | --- | --- | --- | --- | --- |
| Licht und Schalten | Schaltaktor (FSR61, FSR14, FL62 …) | Eltako | `M5-38-08:eltako` | `rocker: F6-02-01:std`<br>`central: A5-38-08:eltako` | light, switch | - |
| Licht und Schalten | Dimmaktor (FUD14, FUD61, FD62 …) | Eltako | `A5-38-08:eltako` | `rocker: F6-02-01:std`<br>`central: A5-38-08:eltako` | light | - |
| Rollläden und Jalousien | Rollladen / Jalousie (FSB14, FSB61, FSB71 …) | Eltako | `G5-3F-7F:eltako` | `controller: H5-3F-7F:eltako`<br>`direction_rocker: F6-02-01:std` | cover | - |
| Heizung und Klima | Heizungsaktor, Home Assistant regelt (FHK14, FAE14 …) | Eltako | `M5-10-06:eltako` | `controller: A5-10-06:eltako`<br>`cooling: F6-02-01:std` | climate, sensor | - |
| Heizung und Klima | Raumregler (FUTH, FTR65HS …) | Eltako | `A5-10-06:eltako` | - | climate, sensor | - |
| Heizung und Klima | Raumregler mit mehreren IDs (FUTH55ED, FUTH65D) | Eltako | `A5-10-06:eltako` | - | climate, sensor, binary_sensor | - |
| Taster und Kontakte | Fenstergriff (FTKE, FFG7B …) | Eltako | `F6-10-00:std` | - | sensor, binary_sensor | - |
| Taster und Kontakte | Tür-/Fensterkontakt (FTK, FTKB …) | Eltako | `D5-00-01:std` | - | binary_sensor | - |
| Taster und Kontakte | Wippentaster (F4T55E, FT55, FT4F …) | Eltako | `F6-02-01:std` | - | event | - |
| Taster und Kontakte | Kontakt über Tastertelegramme (FTS14EM, Garagentor …) | Eltako | `F6-02-01:std` | - | binary_sensor | - |
| Taster und Kontakte | Digitaleingang (FSM60B) | Eltako | `A5-30-01:std` | - | binary_sensor | - |
| Taster und Kontakte | Vier Digitaleingänge und Temperatur (FHMB) | Eltako | `A5-30-03:std` | - | binary_sensor, sensor | - |
| Sensoren | Temperatur und Feuchte (FFT65B …) | Eltako | `A5-04-02:std` | - | sensor | - |
| Sensoren | Temperatur, Feuchte und Versorgungsspannung (FAFT60 Solarsensor) | Eltako | `A5-04-02:eltako` | - | sensor | - |
| Sensoren | Bewegungs- und Helligkeitssensor (FBH65 …) | Eltako | `A5-08-01:eltako` | - | sensor, binary_sensor | - |
| Sensoren | VOC-Sensor (FLT58) | Eltako | `A5-09-05:std` | - | sensor | - |
| Sensoren | TVOC-Sensor (FLGTF) | Eltako | `A5-09-0C:std` | - | sensor | - |
| Sensoren | Multisensor (VLD D2-14-40) (FMS55SB) | Eltako | `D2-14-40:std` | - | sensor | - |
| Sensoren | Multisensor mit Kontakt (VLD D2-14-41) (FMMS44SB) | Eltako | `D2-14-41:std` | - | sensor, binary_sensor | - |
| Sensoren | CO2-Sensor (FCO2TF65) | Eltako | `A5-09-04:std` | - | sensor | - |
| Sensoren | Wetterstation (FWS61, FWG14MS) | Eltako | `A5-13-01:eltako` | - | sensor, binary_sensor | - |
| Zähler | Energiezähler (FWZ12, FSDG14, DSZ14 …) | Eltako | `A5-12-01:eltako` | - | sensor | - |
| Zähler | Gaszähler (F3Z14D …) | Eltako | `A5-12-02:eltako` | - | sensor | - |
| Zähler | Wasserzähler (F3Z14D …) | Eltako | `A5-12-03:eltako` | - | sensor | - |
| Licht und Schalten | Permundo PSC132 / PSC234 Zwischenstecker | Permundo | `D2-01-09:std`<br>`A5-12-01:std`<br>`M5-38-08:eltako` | `controller: A5-38-08:std` | switch, light, sensor | - |
| Licht und Schalten | Schalt- oder Dimmaktor (VLD D2-01) | EnOcean | `D2-01-00:std` | `vld: D2-01-00:std` | light, switch | - |
| Rollläden und Jalousien | Rollladenaktor (VLD D2-05) | EnOcean | `D2-05-00:std` | `vld: D2-05-00:std` | cover | - |
| Taster und Kontakte | Wippentaster (PTM 210/215, NodOn, PEHA, Jung …) | EnOcean | `F6-02-01:std` | - | event | - |
| Taster und Kontakte | Fenstergriff (Hoppe SecuSignal …) | EnOcean | `F6-10-00:std` | - | sensor, binary_sensor | - |
| Taster und Kontakte | Tür-/Fensterkontakt (NodOn …) | EnOcean | `D5-00-01:std` | - | binary_sensor | - |
| Virtueller Sensor (Home Assistant sendet) | Virtueller Fensterkontakt | Home Assistant | - | `contact: D5-00-01:std` | button, sensor | - |
| Virtueller Sensor (Home Assistant sendet) | Virtueller Temperaturfühler | Home Assistant | - | `temperature: A5-02-05:std` | button, sensor | - |
| Virtueller Sensor (Home Assistant sendet) | Virtueller Bewegungsmelder | Home Assistant | - | `motion: A5-07-01:std` | button, sensor | - |
| Virtueller Sensor (Home Assistant sendet) | Virtueller Helligkeitssensor (FAH60) | Home Assistant | - | `brightness: A5-06-01:eltako` | button, sensor | - |
| Virtueller Sensor (Home Assistant sendet) | Virtuelle Wetterstation (FWS61) | Home Assistant | - | `weather: A5-13-01:eltako` | button, sensor | - |
| Virtueller Sensor (Home Assistant sendet) | Virtueller Szenentaster (Szenen 1–4) | Home Assistant | - | `rocker: F6-02-01:std` | button | - |
| Virtueller Sensor (Home Assistant sendet) | Virtueller Taster | Home Assistant | - | `rocker: F6-02-01:std` | button | - |

## Eltako-Baureihe 14 am Bus (Installationsdokumentation)

Was die Bus-Ansicht der Installationsdokumentation über einen Typ weiß: Breite in TE
(je 18 mm), belegte Bus-Adressen (eine je Kanal), Leistung, die er vom Bus nimmt, und was er
liefert (Watt; Quelle: Eltako Planungshilfe RS485-Bus Baureihe 14, 07/2014). Ein Strich: nicht bekannt. Mit * markierte Werte sind
Annahmen, bis ein Datenblatt sie bestätigt.

| Typ | Rolle | TE | Adressen | Nimmt (W) | Liefert (W) |
| --- | --- | ---: | ---: | ---: | ---: |
| DSZ14DRS | Zähler | 4* | 1 | – | – |
| F3Z14D | Zähler | 1* | 3 | – | – |
| F4SR14-LED | Aktor | 1 | 4 | – | – |
| FAE14LPR | Aktor | – | – | 0,42 | – |
| FAE14SSR | Aktor | – | – | 0,4 | – |
| FAM14 | Bus-Master | 2 | 0 | 0,8 | 12 |
| FFR14 | Aktor | – | – | 0,63 | – |
| FGSM14 | Sonstiges | – | – | 0,2 | – |
| FGW14 | Gateway | 1 | 1 | 0,5 | – |
| FGW14-USB | Gateway | 1 | 1 | 0,5 | – |
| FHK14 | Aktor | – | – | 0,42 | – |
| FMS14 | Aktor | – | – | 0,63 | – |
| FMSR14 | Eingänge | – | – | 0,1 | – |
| FMZ14 | Aktor | – | – | 0,4 | – |
| FRP14 | Sonstiges | – | – | 0,5 | – |
| FSB14 | Aktor | 1 | 2 | 0,42 | – |
| FSG14/1-10V | Aktor | – | – | 0,2 | – |
| FSNT14-12V/12W | Netzteil | 1 | 0 | – | 12 |
| FSR14-2x | Aktor | 1 | 2 | 0,14 | – |
| FSR14-4x | Aktor | 1 | 4 | 0,7 | – |
| FSR14SSR | Aktor | 1 | 2* | 0,4 | – |
| FSU14 | Aktor | 1 | 1* | 0,14 | – |
| FTD14 | Sonstiges | – | – | 0,53 | – |
| FTN14 | Aktor | 1 | 1 | 0,14 | – |
| FTS14EM | Eingänge | 1 | – | 0,13 | – |
| FTS14FA | Eingänge | – | – | 0,5 | – |
| FTS14KS | Bus-Master | – | – | 0,36 | – |
| FTS14TG | Eingänge | 1 | 1 | 0,42 | – |
| FUD14 | Aktor | 1 | 1 | 0,2 | – |
| FUD14/800W | Aktor | 1 | 1 | 0,2 | – |
| FWZ14 | Zähler | 1 | 1 | 0,1 | – |
| FWZ14-65A | Zähler | 1 | 1 | 0,1 | – |
| FZK14 | Aktor | – | – | 0,14 | – |

## Über den Katalog hinaus

- **Per EEP** (Experte): alle 318 Standardprofile der EnOcean Alliance lassen sich als
  Gerät mit einem Sensor je Wert anlegen. Profile außerhalb des Katalogs sind nicht mit
  Hardware geprüft.
- **Eigene Definition**: Sensoren, die du in `/config/enocean_eltako/custom_devices.yaml`
  beschreibst.
- **Entdeckte Sender**: jeder unbekannte Sender, den ein Gateway hört, steht unter **Gerät hinzufügen →
  Entdeckte Geräte** und bekommt einen Vorschlag für die Geräteart.

Wie jede Art angelegt wird: [Benutzerhandbuch](USER-GUIDE.de.md). Welche Einlernfunktion am
Eltako-Aktor der Baureihe 14 zu welchem Einlern-Button gehört: [teach_in.de.md](teach_in.de.md).
