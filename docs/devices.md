# Supported devices

Generated from the device catalog by `scripts/gen_device_docs.py`; do not edit.
Every profile is named as EEP plus variant (`std` = EnOcean Alliance definition,
`eltako` = Eltako variant documented in `protocol/eep/eltako/`).

| Device | Manufacturer | Receives | Sends (sender profiles) | Entities |
| --- | --- | --- | --- | --- |
| Switching actuator (FSR61, FSR14, FL62 …) | Eltako | `M5-38-08:eltako` | `central: A5-38-08:eltako`<br>`rocker: F6-02-01:std` | light, switch |
| Dimmer (FUD14, FUD61, FD62 …) | Eltako | `A5-38-08:eltako` | `central: A5-38-08:eltako`<br>`rocker: F6-02-01:std` | light |
| Shutter / blind (FSB14, FSB61, FSB71 …) | Eltako | `G5-3F-7F:eltako` | `controller: H5-3F-7F:eltako`<br>`direction_rocker: F6-02-01:std` | cover |
| Permundo PSC132 / PSC234 plug | Permundo | `D2-01-09:std`<br>`A5-12-01:std`<br>`M5-38-08:eltako` | `controller: A5-38-08:std` | switch, light, sensor |
| Window handle (FTKE, FFG7B, Hoppe …) | Eltako | `F6-10-00:std` | - | sensor, binary_sensor |
| Door / window contact (FTK, FTKB …) | Eltako | `D5-00-01:std` | - | binary_sensor |
| Rocker switch (F4T55E, FT55, NodOn …) | Eltako | `F6-02-01:std` | - | event |
| Contact via rocker telegrams (FTS14EM, garage door …) | Eltako | `F6-02-01:std` | - | binary_sensor |
| Energy meter (FWZ12, FSDG14, DSZ14 …) | Eltako | `A5-12-01:eltako` | - | sensor |
| Temperature and humidity (FAFT60, FFT65B …) | Eltako | `A5-04-02:std` | - | sensor |
| Motion and brightness sensor (FBH65 …) | Eltako | `A5-08-01:eltako` | - | sensor, binary_sensor |
| CO2 sensor (FCO2TF65) | Eltako | `A5-09-04:std` | - | sensor |
| Heating actuator, Home Assistant controls (FHK14, FAE14 …) | Eltako | `M5-10-06:eltako` | `controller: A5-10-06:eltako` | climate, sensor |
| Room controller (FUTH, FTR65HS …) | Eltako | `A5-10-06:eltako` | - | climate, sensor |
| Weather station (FWS61, FWG14) | Eltako | `A5-13-01:eltako` | - | sensor, binary_sensor |
