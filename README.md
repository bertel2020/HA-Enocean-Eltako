<p align="center"><img src="https://raw.githubusercontent.com/bertel2020/HA-Enocean-Eltako/main/custom_components/enocean_eltako/brand/logo.png" alt="EnOcean Eltako logo" width="350"></p>

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

> [!IMPORTANT]
> **Device Proxy app (recommended):** the [Device Proxy](https://github.com/bertel2020/HA-Device-Proxy) app for Home Assistant OS and Supervised keeps the gateway's serial port and shares it: Home Assistant, the old `eltako` integration or a second Home Assistant (a test system, for example) can use one gateway at the same time. After a restart it replays the telegrams Home Assistant missed, and it can stand in with a fallback gateway. The integration finds the app's gateways by itself. See the [User Guide](docs/USER-GUIDE.md#device-proxy-app).

EnOcean Eltako brings Eltako devices (series 14 bus and wireless) and other EnOcean devices into Home Assistant. It is written from scratch, needs no third-party EnOcean library and is configured entirely in the UI: one entry per gateway, one sub-entry per device, no YAML.

## Highlights

- **Gateways:** Eltako FGW14-USB (RS485 bus of the series 14; a FAM14 with an interface of its own joins the same bus group with failover), FAM-USB, PioTek MGW-ETH, Symcon EnOcean LAN Gateway and generic ESP2/ESP3 gateways; every USB gateway also over ser2net (TCP).
- **Devices:** switching actuators, dimmers, shutters, heating actuators and room controllers, window handles, contacts, rockers, meters, sensors, Permundo plugs and VLD actuators. Any of the standard EnOcean profiles can be added as a generic device. Full list: [docs/devices.md](docs/devices.md).
- **Covers** with controller and direction-rocker senders in parallel, position tracking, vent slots, slat tilt and a travel time assistant.
- **Virtual sensors:** Home Assistant entities sent as EnOcean contact, motion, temperature, brightness, weather or rocker, e.g. to feed the shading automatic of an actuator.
- **Teach-in, discovery and a live telegram monitor** in the **EnOcean** sidebar panel, plus capture and diagnostics for bug reports. Three colour schemes (light/dark) and three font sizes are selectable.
- **[Device Proxy app](https://github.com/bertel2020/HA-Device-Proxy):** shares one gateway between Home Assistant and other programs, replays the telegrams missed during a restart and is set up from its announcement.
- **Takeover** of the devices of the old `eltako` integration without teaching the actuators in again.
- **Installation documentation** in the panel: places, circuits, fuses, sender IDs and links, and the **Eltako bus** by its master (FAM14) with each DIN rail device and its channels, cabinets drawn as DIN rails to scale with label strips to print, the address plan 1–126, the load of the power supplies and checks (duplicate addresses, missing ones, devices not in Home Assistant); an experimental reading of the bus by listening compares the addresses that answer with the documentation.
- **Safety stays in the actuator:** wind, rain, frost and lock-out protection are never replaced.

## Screenshots

The screenshots show sample data from the **EnOcean** sidebar panel.

<p align="center">
  <img src="https://raw.githubusercontent.com/bertel2020/HA-Enocean-Eltako/main/screenshots/showcase-en/telegrams-desktop-light.png" alt="Live telegram monitor" width="100%">
</p>

| Devices | Sender IDs |
| --- | --- |
| ![Devices](https://raw.githubusercontent.com/bertel2020/HA-Enocean-Eltako/main/screenshots/showcase-en/devices-desktop-light.png) | ![Sender IDs](https://raw.githubusercontent.com/bertel2020/HA-Enocean-Eltako/main/screenshots/showcase-en/senders-desktop-light.png) |

| Takeover |
| --- |
| ![Takeover](https://raw.githubusercontent.com/bertel2020/HA-Enocean-Eltako/main/screenshots/showcase-en/takeover-desktop-light.png) |

| Installation: documentation | Installation: links |
| --- | --- |
| ![Installation devices](https://raw.githubusercontent.com/bertel2020/HA-Enocean-Eltako/main/screenshots/showcase-en/installation-devices-desktop-light.png) | ![Installation links](https://raw.githubusercontent.com/bertel2020/HA-Enocean-Eltako/main/screenshots/showcase-en/installation-links-desktop-light.png) |

| Device details | Installation documentation (print) |
| --- | --- |
| ![Device details](https://raw.githubusercontent.com/bertel2020/HA-Enocean-Eltako/main/screenshots/showcase-en/device-details-desktop-light.png) | ![Installation documentation](https://raw.githubusercontent.com/bertel2020/HA-Enocean-Eltako/main/screenshots/showcase-en/documentation-print.png) |

| Gateway details |
| --- |
| ![Gateway details](https://raw.githubusercontent.com/bertel2020/HA-Enocean-Eltako/main/screenshots/showcase-en/gateway-details-desktop-light.png) |

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

## Quick start

1. Add the integration once per gateway and pick the model and connection (USB port, or host and port).
2. Under the gateway choose **Add device**: listen for the device by pressing a button on it, or pick it from the catalog. Senders the gateway hears on its own are listed there under **Discovered devices**.
3. Open the panel in the sidebar (named **EnOcean**; the integration itself is **EnOcean Eltako**) to watch telegrams live and to check sender IDs.

Every step, all device types, the panel, the takeover, blueprints, known limitations and troubleshooting are in the **[User Guide](docs/USER-GUIDE.md)**.

## Documentation

- [User Guide](docs/USER-GUIDE.md)
- [Supported devices](docs/devices.md)
- [Learn functions of Eltako series 14 actuators](docs/teach_in.md)
- [Quality scale](docs/quality_scale.md)
- [Changelog](CHANGELOG.md) ([Deutsch](CHANGELOG.de.md))

## Thanks

This integration is written from scratch, but it would not exist without the work and experience of these projects and their authors:

- [grimmpp/home-assistant-eltako](https://github.com/grimmpp/home-assistant-eltako) (Philipp Grimm): the previous Eltako integration, which in turn thanks chrysn and Johannes Bosecker for the first version as well as Cedric Van Labeke and LHBL2003.
- [grimmpp/eltako14bus](https://github.com/grimmpp/eltako14bus): originally by Christian Amsüss and Energy Harvesting Solutions (2016–2020), maintained by Philipp Grimm.
- [grimmpp/esp2_gateway_adapter](https://github.com/grimmpp/esp2_gateway_adapter) (Philipp Grimm).
- [kipe/enocean](https://github.com/kipe/enocean) (Kimmo Huoman).
- [grimmpp/enocean-device-manager](https://github.com/grimmpp/enocean-device-manager).

No code was taken from these projects. License terms are in [LICENSE](LICENSE) and [NOTICE](NOTICE).

## License

[MIT](LICENSE). EnOcean is a registered trademark of EnOcean GmbH, Eltako of Eltako GmbH. This project is not affiliated with either company.
