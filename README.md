<h1 align="center">EnOcean Eltako for Home Assistant</h1>

<p align="center">
  Eltako and EnOcean devices in Home Assistant, configured entirely through the UI.
</p>

<p align="center">
  <a href="https://github.com/hacs/integration"><img src="https://img.shields.io/badge/HACS-Custom-41BDF5.svg" alt="HACS Custom"></a>
  <a href="https://www.home-assistant.io/"><img src="https://img.shields.io/badge/Home%20Assistant-Custom%20Integration-18BCF2.svg?logo=home-assistant&logoColor=white" alt="Home Assistant"></a>
  <a href="https://github.com/bertel2020/HA-Enocean-Eltako/releases"><img src="https://img.shields.io/github/v/release/bertel2020/HA-Enocean-Eltako?sort=semver&include_prereleases" alt="Release"></a>
  <a href="https://github.com/bertel2020/HA-Enocean-Eltako/actions/workflows/validate.yml"><img src="https://github.com/bertel2020/HA-Enocean-Eltako/actions/workflows/validate.yml/badge.svg" alt="Validate"></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/bertel2020/HA-Enocean-Eltako" alt="License"></a>
</p>

<p align="center">
  <a href="https://buymeacoffee.com/bertel2020"><img src="https://img.shields.io/badge/Buy%20Me%20a%20Coffee-support-FFDD00?logo=buy-me-a-coffee&logoColor=black" alt="Buy Me a Coffee"></a>
  <a href="https://ko-fi.com/bertel2020"><img src="https://img.shields.io/badge/Ko--fi-support-FF5E5B?logo=ko-fi&logoColor=white" alt="Ko-fi"></a>
  <a href="https://paypal.me/RobertoMartins"><img src="https://img.shields.io/badge/PayPal-donate-00457C?logo=paypal&logoColor=white" alt="PayPal"></a>
</p>

<p align="center"><em><a href="README.de.md">Deutsche Version</a></em></p>

> **Status: early development.** Gateways can be added (FAM-USB, FGW14-USB,
> FAM14, MGW-ETH with discovery, Symcon LAN, generic ESP2/ESP3; USB or ser2net)
> and stay connected. FGW14-USB and FAM14 on the same bus form a bus group with
> failover; the FAM14 can stay disconnected until it is needed. Devices are
> added per gateway, by ID or by listening for a telegram: switching actuators,
> dimmers, shutters (controller and direction rocker in parallel), window
> handles, contacts, rockers, meters, sensors, Permundo PSC132/PSC234, room
> controllers and heating actuators controlled by Home Assistant. Telegrams
> show up in the diagnostics and can be recorded with the action
> `enocean_eltako.capture`.
> Not tested on real hardware yet; do not use it in production. The existing
> `eltako` integration keeps running in parallel; this one uses its own domain
> `enocean_eltako`.

A new integration for Eltako (series 14 bus and wireless) and other EnOcean
devices, written from scratch. Goals:

- **UI only:** one entry per gateway, one sub-entry per device, no YAML
- **Gateways:** FGW14-USB and FAM14 on the RS485 bus (as a bus group with
  failover), FAM-USB, PioTek MGW-ETH, Symcon EnOcean LAN Gateway; every USB
  gateway also via ser2net (TCP)
- **All EEPs incl. VLD**, standard profiles generated from the official
  EnOcean Alliance definitions; Eltako variants kept strictly separate
- **Covers** (FSB14/61/71) with controller and direction-rocker senders in
  parallel, position tracking and calibration at the end positions
- **Teach-in, discovery, telegram monitor**, import from the FAM14 bus memory
  and a takeover assistant for the old `eltako` integration
- **No third-party EnOcean libraries:** no extra requirements; serial ports
  use Home Assistant's own port picker and serial library (usb integration),
  so ESPHome serial proxies work too

## Supported devices

Generated from the catalog; details in [docs/devices.md](docs/devices.md).

<!-- devices:start -->
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
<!-- devices:end -->

## Installation

### Via HACS (recommended)

[![Open the HACS repository in My Home Assistant](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=bertel2020&repository=HA-Enocean-Eltako&category=integration)
[![Add EnOcean Eltako to My Home Assistant](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=enocean_eltako)

1. Use the first button to open the EnOcean Eltako repository in HACS.
2. Download **EnOcean Eltako** and restart Home Assistant.
3. Use the second button to add the integration. Alternatively open **Settings
   → Devices & services → Add integration → EnOcean Eltako**.

If the first button does not work, add `https://github.com/bertel2020/HA-Enocean-Eltako`
in HACS under **Integrations → Custom repositories** as category **Integration**.

### Manual

Copy the `custom_components/enocean_eltako` directory to
`/config/custom_components/enocean_eltako` and restart Home Assistant.

## Development

```bash
python -m pip install -r requirements_test.txt
ruff check custom_components tests scripts
python scripts/check_protocol_imports.py
python -m pytest
```

`python scripts/fetch_eep.py --generated` followed by
`python scripts/generate_eep.py` regenerates the standard profiles.
`python scripts/fetch_eep.py` downloads the official EEP definitions into
`.eep_cache/`. These files belong to the EnOcean Alliance and are never
committed (see [NOTICE](NOTICE)).

## Thanks

This integration is written from scratch, but it would not exist without the
work and experience of these projects and their authors:

- [grimmpp/home-assistant-eltako](https://github.com/grimmpp/home-assistant-eltako)
  (Philipp Grimm): the previous Eltako integration, which in turn thanks chrysn
  and Johannes Bosecker for the first version as well as Cedric Van Labeke and
  LHBL2003.
- [grimmpp/eltako14bus](https://github.com/grimmpp/eltako14bus): originally by
  Christian Amsüss and Energy Harvesting Solutions (2016–2020), maintained by
  Philipp Grimm.
- [grimmpp/esp2_gateway_adapter](https://github.com/grimmpp/esp2_gateway_adapter)
  (Philipp Grimm).
- [kipe/enocean](https://github.com/kipe/enocean) (Kimmo Huoman).
- [grimmpp/enocean-device-manager](https://github.com/grimmpp/enocean-device-manager)
  (eo_man).

No code was taken from these projects. License terms are in
[LICENSE](LICENSE) and [NOTICE](NOTICE).

## License

[MIT](LICENSE). EnOcean is a registered trademark of EnOcean GmbH, Eltako of
Eltako GmbH. This project is not affiliated with either company.
