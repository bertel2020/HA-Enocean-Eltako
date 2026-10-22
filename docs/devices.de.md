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

| Kategorie | Gerät | Hersteller | Empfängt | Sendet (Sender-Profile) | Entitäten |
| --- | --- | --- | --- | --- | --- |
| Licht und Schalten | Schaltaktor (FSR61, FSR14, FL62 …) | Eltako | `M5-38-08:eltako` | `rocker: F6-02-01:std`<br>`central: A5-38-08:eltako` | light, switch |
| Licht und Schalten | Dimmaktor (FUD14, FUD61, FD62 …) | Eltako | `A5-38-08:eltako` | `rocker: F6-02-01:std`<br>`central: A5-38-08:eltako` | light |
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
