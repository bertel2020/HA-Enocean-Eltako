# Supported devices

Generated from the device catalog by `scripts/gen_device_docs.py`; do not edit.
Every profile is named as EEP plus variant (`std` = EnOcean Alliance definition,
`eltako` = Eltako variant documented in `protocol/eep/eltako/`).

| Category | Device | Manufacturer | Receives | Sends (sender profiles) | Entities |
| --- | --- | --- | --- | --- | --- |
| Lighting and switching | Switching actuator (FSR61, FSR14, FL62 …) | Eltako | `M5-38-08:eltako` | `rocker: F6-02-01:std`<br>`central: A5-38-08:eltako` | light, switch |
| Lighting and switching | Dimmer (FUD14, FUD61, FD62 …) | Eltako | `A5-38-08:eltako` | `rocker: F6-02-01:std`<br>`central: A5-38-08:eltako` | light |
| Shutters and blinds | Shutter / blind (FSB14, FSB61, FSB71 …) | Eltako | `G5-3F-7F:eltako` | `controller: H5-3F-7F:eltako`<br>`direction_rocker: F6-02-01:std` | cover |
| Heating and climate | Heating actuator, Home Assistant controls (FHK14, FAE14 …) | Eltako | `M5-10-06:eltako` | `controller: A5-10-06:eltako`<br>`cooling: F6-02-01:std` | climate, sensor |
| Heating and climate | Room controller (FUTH, FTR65HS …) | Eltako | `A5-10-06:eltako` | - | climate, sensor |
| Buttons and contacts | Window handle (FTKE, FFG7B …) | Eltako | `F6-10-00:std` | - | sensor, binary_sensor |
| Buttons and contacts | Door / window contact (FTK, FTKB …) | Eltako | `D5-00-01:std` | - | binary_sensor |
| Buttons and contacts | Rocker switch (F4T55E, FT55, FT4F …) | Eltako | `F6-02-01:std` | - | event |
| Buttons and contacts | Contact via rocker telegrams (FTS14EM, garage door …) | Eltako | `F6-02-01:std` | - | binary_sensor |
| Buttons and contacts | Digital input (FSM60B) | Eltako | `A5-30-01:std` | - | binary_sensor |
| Buttons and contacts | Four digital inputs and temperature (FHMB) | Eltako | `A5-30-03:std` | - | binary_sensor, sensor |
| Sensors | Temperature and humidity (FAFT60, FFT65B …) | Eltako | `A5-04-02:std` | - | sensor |
| Sensors | Motion and brightness sensor (FBH65 …) | Eltako | `A5-08-01:eltako` | - | sensor, binary_sensor |
| Sensors | VOC sensor (FLT58) | Eltako | `A5-09-05:std` | - | sensor |
| Sensors | TVOC sensor (FLGTF) | Eltako | `A5-09-0C:std` | - | sensor |
| Sensors | Multisensor (VLD D2-14-40) (FMS55SB) | Eltako | `D2-14-40:std` | - | sensor |
| Sensors | Multisensor with contact (VLD D2-14-41) (FMMS44SB) | Eltako | `D2-14-41:std` | - | sensor, binary_sensor |
| Sensors | CO2 sensor (FCO2TF65) | Eltako | `A5-09-04:std` | - | sensor |
| Sensors | Weather station (FWS61, FWG14) | Eltako | `A5-13-01:eltako` | - | sensor, binary_sensor |
| Meters | Energy meter (FWZ12, FSDG14, DSZ14 …) | Eltako | `A5-12-01:eltako` | - | sensor |
| Meters | Gas meter (F3Z14D …) | Eltako | `A5-12-02:eltako` | - | sensor |
| Meters | Water meter (F3Z14D …) | Eltako | `A5-12-03:eltako` | - | sensor |
| Lighting and switching | Permundo PSC132 / PSC234 plug | Permundo | `D2-01-09:std`<br>`A5-12-01:std`<br>`M5-38-08:eltako` | `controller: A5-38-08:std` | switch, light, sensor |
| Lighting and switching | Switch or dimmer actuator (VLD D2-01) | EnOcean | `D2-01-00:std` | `vld: D2-01-00:std` | light, switch |
| Shutters and blinds | Shutter actuator (VLD D2-05) | EnOcean | `D2-05-00:std` | `vld: D2-05-00:std` | cover |
| Buttons and contacts | Rocker switch (NodOn, PEHA, Jung …) | EnOcean | `F6-02-01:std` | - | event |
| Buttons and contacts | Window handle (Hoppe SecuSignal …) | EnOcean | `F6-10-00:std` | - | sensor, binary_sensor |
| Buttons and contacts | Door / window contact (NodOn …) | EnOcean | `D5-00-01:std` | - | binary_sensor |
| Virtual sensor (Home Assistant sends) | Virtual window contact | Home Assistant | - | `contact: D5-00-01:std` | button, sensor |
| Virtual sensor (Home Assistant sends) | Virtual temperature sensor | Home Assistant | - | `temperature: A5-02-05:std` | button, sensor |
| Virtual sensor (Home Assistant sends) | Virtual motion sensor | Home Assistant | - | `motion: A5-07-01:std` | button, sensor |
| Virtual sensor (Home Assistant sends) | Virtual brightness sensor (FAH60) | Home Assistant | - | `brightness: A5-06-01:eltako` | button, sensor |
| Virtual sensor (Home Assistant sends) | Virtual weather station (FWS61) | Home Assistant | - | `weather: A5-13-01:eltako` | button, sensor |
| Virtual sensor (Home Assistant sends) | Virtual scene button (scenes 1–4) | Home Assistant | - | `rocker: F6-02-01:std` | button |
| Virtual sensor (Home Assistant sends) | Virtual rocker | Home Assistant | - | `rocker: F6-02-01:std` | button |
