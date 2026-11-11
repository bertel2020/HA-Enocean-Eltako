# Supported devices

[Deutsch](devices.de.md)

Generated from the device catalog by `scripts/gen_device_docs.py`; do not edit.
Every profile is named as EEP plus variant (`std` = EnOcean Alliance definition,
`eltako` = Eltako variant documented in `protocol/eep/eltako/`).

## Gateways

One config entry per gateway. Serial gateways connect over USB or, through
ser2net or the Device Proxy app, over TCP.

| Gateway | Connection |
| --- | --- |
| Eltako FGW14-USB | Eltako series 14 bus (RS485) over USB; forms a bus group with the FAM14 |
| Eltako FAM14 | Eltako series 14 bus (RS485); may stay disconnected until it is needed |
| Eltako FAM-USB | USB radio gateway (ESP2) |
| PioTek MGW-ETH | Network (TCP, ESP3), found automatically |
| Symcon EnOcean LAN Gateway | Network (TCP, ESP3) |
| Generic ESP3 (USB 300, TCM 310 …) | Any ESP3 gateway over USB or TCP |
| Generic ESP2 | Any ESP2 gateway over USB or TCP |

## Devices of the catalog

Receives: telegrams the device sends to Home Assistant. Sends: sender profiles
Home Assistant uses to control it, each with its own sender ID from the gateway's pool.
Hardware: ✓ when the repository holds a real capture of this model that the tests replay;
a model without it follows the manufacturer's documentation. Captures are welcome, see
[CONTRIBUTING](../CONTRIBUTING.md).

| Category | Device | Manufacturer | Receives | Sends (sender profiles) | Entities | Hardware |
| --- | --- | --- | --- | --- | --- | --- |
| Lighting and switching | Switching actuator (FSR61, FSR14, FL62 …) | Eltako | `M5-38-08:eltako` | `rocker: F6-02-01:std`<br>`central: A5-38-08:eltako` | light, switch | - |
| Lighting and switching | Dimmer (FUD14, FUD61, FD62 …) | Eltako | `A5-38-08:eltako` | `rocker: F6-02-01:std`<br>`central: A5-38-08:eltako` | light | - |
| Shutters and blinds | Shutter / blind (FSB14, FSB61, FSB71 …) | Eltako | `G5-3F-7F:eltako` | `controller: H5-3F-7F:eltako`<br>`direction_rocker: F6-02-01:std` | cover | - |
| Heating and climate | Heating actuator, Home Assistant controls (FHK14, FAE14 …) | Eltako | `M5-10-06:eltako` | `controller: A5-10-06:eltako`<br>`cooling: F6-02-01:std` | climate, sensor | - |
| Heating and climate | Room controller (FUTH, FTR65HS …) | Eltako | `A5-10-06:eltako` | - | climate, sensor | - |
| Heating and climate | Room controller with several IDs (FUTH55ED, FUTH65D) | Eltako | `A5-10-06:eltako` | - | climate, sensor, binary_sensor | - |
| Buttons and contacts | Window handle (FTKE, FFG7B …) | Eltako | `F6-10-00:std` | - | sensor, binary_sensor | - |
| Buttons and contacts | Door / window contact (FTK, FTKB …) | Eltako | `D5-00-01:std` | - | binary_sensor | - |
| Buttons and contacts | Rocker switch (F4T55E, FT55, FT4F …) | Eltako | `F6-02-01:std` | - | event | - |
| Buttons and contacts | Contact via rocker telegrams (FTS14EM, garage door …) | Eltako | `F6-02-01:std` | - | binary_sensor | - |
| Buttons and contacts | Digital input (FSM60B) | Eltako | `A5-30-01:std` | - | binary_sensor | - |
| Buttons and contacts | Four digital inputs and temperature (FHMB) | Eltako | `A5-30-03:std` | - | binary_sensor, sensor | - |
| Sensors | Temperature and humidity (FFT65B …) | Eltako | `A5-04-02:std` | - | sensor | - |
| Sensors | Temperature, humidity and supply voltage (FAFT60 solar sensor) | Eltako | `A5-04-02:eltako` | - | sensor | - |
| Sensors | Motion and brightness sensor (FBH65 …) | Eltako | `A5-08-01:eltako` | - | sensor, binary_sensor | - |
| Sensors | VOC sensor (FLT58) | Eltako | `A5-09-05:std` | - | sensor | - |
| Sensors | TVOC sensor (FLGTF) | Eltako | `A5-09-0C:std` | - | sensor | - |
| Sensors | Multisensor (VLD D2-14-40) (FMS55SB) | Eltako | `D2-14-40:std` | - | sensor | - |
| Sensors | Multisensor with contact (VLD D2-14-41) (FMMS44SB) | Eltako | `D2-14-41:std` | - | sensor, binary_sensor | - |
| Sensors | CO2 sensor (FCO2TF65) | Eltako | `A5-09-04:std` | - | sensor | - |
| Sensors | Weather station (FWS61, FWG14MS) | Eltako | `A5-13-01:eltako` | - | sensor, binary_sensor | - |
| Meters | Energy meter (F3Z14D, FWZ12, FSDG14, DSZ14 …) | Eltako | `A5-12-01:eltako` | - | sensor | - |
| Meters | Gas meter (F3Z14D …) | Eltako | `A5-12-02:eltako` | - | sensor | - |
| Meters | Water meter (F3Z14D …) | Eltako | `A5-12-03:eltako` | - | sensor | - |
| Lighting and switching | Permundo PSC132 / PSC234 plug | Permundo | `D2-01-09:std`<br>`A5-12-01:std`<br>`M5-38-08:eltako` | `controller: A5-38-08:std`<br>`rocker: F6-02-01:std` | switch, light, sensor | - |
| Lighting and switching | Switch or dimmer actuator (VLD D2-01) | EnOcean | `D2-01-00:std` | `vld: D2-01-00:std` | light, switch | - |
| Shutters and blinds | Shutter actuator (VLD D2-05) | EnOcean | `D2-05-00:std` | `vld: D2-05-00:std` | cover | - |
| Buttons and contacts | Rocker switch (PTM 210/215, NodOn, PEHA, Jung …) | EnOcean | `F6-02-01:std` | - | event | - |
| Buttons and contacts | Window handle (Hoppe SecuSignal …) | EnOcean | `F6-10-00:std` | - | sensor, binary_sensor | - |
| Buttons and contacts | Door / window contact (NodOn …) | EnOcean | `D5-00-01:std` | - | binary_sensor | - |
| Virtual sensor (Home Assistant sends) | Virtual window contact | Home Assistant | - | `contact: D5-00-01:std` | button, sensor | - |
| Virtual sensor (Home Assistant sends) | Virtual temperature sensor | Home Assistant | - | `temperature: A5-02-05:std` | button, sensor | - |
| Virtual sensor (Home Assistant sends) | Virtual motion sensor | Home Assistant | - | `motion: A5-07-01:std` | button, sensor | - |
| Virtual sensor (Home Assistant sends) | Virtual brightness sensor (FAH60) | Home Assistant | - | `brightness: A5-06-01:eltako` | button, sensor | - |
| Virtual sensor (Home Assistant sends) | Virtual weather station (FWS61) | Home Assistant | - | `weather: A5-13-01:eltako` | button, sensor | - |
| Virtual sensor (Home Assistant sends) | Virtual scene button (scenes 1–4) | Home Assistant | - | `rocker: F6-02-01:std` | button | - |
| Virtual sensor (Home Assistant sends) | Virtual rocker | Home Assistant | - | `rocker: F6-02-01:std` | button | - |

## Eltako series 14 on the bus (installation documentation)

What the Bus view of the installation documentation knows of a type: its width in TE
(18 mm each), the bus addresses it takes (one per channel), what it takes from the bus
and what it delivers (watts; source: Eltako operating manual series 14 RS485 bus 10/2026, main catalogue chapter 1). A dash: not given by Eltako's documents. Values marked * are
assumed until a data sheet confirms them.

| Type | Role | TE | Addresses | Takes (W) | Delivers (W) |
| --- | --- | ---: | ---: | ---: | ---: |
| BGW14 | gateway | 1 | – | 0.3 | – |
| DS14 | accessory (not on the bus) | 0.5 | 0 | – | – |
| DSZ14DRS-3x80A | meter | 4 | – | – | – |
| DSZ14WDRS-3x5A | meter | 4 | – | – | – |
| F2L14 | actuator | 1 | – | 0.14 | – |
| F3Z14D | meter | 1 | 3 | 0.1 | – |
| F4HK14 | actuator | 1 | 4 | 0.7 | – |
| F4SR14-LED | actuator | 2 | 4 | 1 | – |
| FAE14LPR | actuator | 1 | 2 | 0.42 | – |
| FAE14SSR | actuator | 1 | 2 | 0.4 | – |
| FAM14 | bus master | 2 | 0 | 0.8 | 12 |
| FBA14 | accessory (not on the bus) | 1 | 0 | – | – |
| FD2G14 | gateway | – | – | 0.5 | – |
| FDG14 | gateway | 2 | 16 | 0.4 | – |
| FFR14 | actuator | – | – | 0.63 | – |
| FGSM14 | gateway | – | – | 0.2 | – |
| FGW14 | gateway | 1 | 1 | 0.5 | – |
| FGW14-USB | gateway | 1 | 1 | 0.3 | – |
| FHK14 | actuator | 1 | – | 0.42 | – |
| FLUD14 | other | 1 | – | – | – |
| FMS14 | actuator | 1 | – | 0.63 | – |
| FMSR14 | inputs | 1 | 5 | 0.1 | – |
| FMZ14 | actuator | 1 | 1 | 0.4 | – |
| FPLG14 | gateway | – | – | 0.4 | – |
| FPLT14 | gateway | – | – | 0.4 | – |
| FRGBW14 | actuator | – | – | 0.1 | – |
| FRP14 | other | 1 | – | 0.5 | – |
| FSB14 | actuator | 1 | 2 | 0.42 | – |
| FSDG14 | meter | 1 | 2 | 0.4 | – |
| FSG14/1-10V | actuator | 1 | 1 | 0.2 | – |
| FSM14-UC | inputs | 1 | – | 0.1 | – |
| FSNT14-12V/12W | power supply | 1 | 0 | – | 12 |
| FSR14-2x | actuator | 1 | 2 | 0.14 | – |
| FSR14-4x | actuator | 1 | 4 | 0.7 | – |
| FSR14M-2x | actuator | – | 2* | 0.14 | – |
| FSR14SSR | actuator | 1 | 2 | 0.4 | – |
| FSU14 | actuator | 1 | 8 | 0.14 | – |
| FTD14 | other | 1 | – | 0.53 | – |
| FTN14 | actuator | 1 | 1 | 0.14 | – |
| FTS14EM | inputs | 2 | 0 | 0.13 | – |
| FTS14FA | inputs | 1 | – | 0.5 | – |
| FTS14GBZ | inputs | – | – | 0.1 | – |
| FTS14KS | bus master | 2 | 0 | 0.4 | 8 |
| FTS14TG | inputs | 2.5 | 1 | 0.42 | – |
| FUD14 | actuator | 1 | 1 | 0.2 | – |
| FUD14/800W | actuator | 2 | 1 | 0.2 | – |
| FWG14MS | gateway | 1 | – | 0.3 | – |
| FWZ14 | meter | 1 | 1* | 0.1 | – |
| FWZ14-65A | meter | 1 | 1* | 0.1 | – |
| FZK14 | actuator | – | – | 0.14 | – |
| GBA14 | accessory (not on the bus) | 1 | 0 | – | – |
| STE14 | accessory (not on the bus) | 1 | 0 | – | – |

## Beyond the catalog

- **By EEP** (expert): all 318 standard profiles of the EnOcean Alliance can be added
  as a device with one sensor per value. Profiles outside the catalog are not checked
  against hardware.
- **Own definition**: sensors you describe in `/config/enocean_eltako/custom_devices.yaml`.
- **Discovered senders**: every unknown sender a gateway hears is listed under **Add
  device → Discovered devices** with a suggested kind.

How to add each kind: [User Guide](USER-GUIDE.md). Learn function to set on an Eltako
series 14 actuator for each teach-in button: [teach_in.md](teach_in.md).
