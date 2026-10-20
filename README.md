<p align="center"><picture><source media="(prefers-color-scheme: dark)" srcset="custom_components/enocean_eltako/brand/dark_logo.png"><img src="custom_components/enocean_eltako/brand/logo.png" alt="EnOcean Eltako logo" width="350"></picture></p>

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
> show up live in the **EnOcean** sidebar panel and in the diagnostics, and can
> be recorded with the action `enocean_eltako.capture`.
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
- **Virtual sensors:** HA entities sent as EnOcean contact, motion, temperature or rocker
- **Teach-in, discovery, telegram monitor**, import from the FAM14 bus memory
  and a takeover assistant for the old `eltako` integration
- **No third-party EnOcean libraries:** no extra requirements; serial ports
  use Home Assistant's own port picker and serial library (usb integration),
  so ESPHome serial proxies work too

## Supported devices

Add a device under the gateway with **Add device** in one of five ways:

- **Listen for the device** (recommended): press a button on it or switch the actuator
  locally; the kind is suggested from its telegram.
- **Eltako device** or **EnOcean device of another manufacturer**: pick category and kind
  from the catalog.
- **Virtual sensor**: Home Assistant itself sends as a window contact (D5-00-01), motion
  sensor (A5-07-01), temperature sensor (A5-02-05) or rocker (F6-02-01) with its own sender
  ID. An HA window contact can lower the heating actuator, an HA temperature can be its room
  sensor. It sends on every change of the chosen entity and repeats every 15 min (adjustable);
  if the entity is unavailable, a contact can send the safe value "open". Teach it in with the
  button on the device page; the device page also shows the value sent last.
- **By EEP** (expert): any of the 318 standard profiles of the EnOcean Alliance becomes a
  device with one sensor per value; type a code such as `A5-04-02` to find it.

Even simpler: every sender the gateway hears that is not set up yet shows up as a
**discovered** card on the integration page. **Add** suggests the kind and fills in the ID;
**Ignore** hides senders that are not yours (a neighbour's, for example) for good. Discovery
can be switched off per gateway in its options.

Generated from the catalog; details in [docs/devices.md](docs/devices.md).

<!-- devices:start -->
| Category | Device | Manufacturer | Receives | Sends (sender profiles) | Entities |
| --- | --- | --- | --- | --- | --- |
| Lighting and switching | Switching actuator (FSR61, FSR14, FL62 …) | Eltako | `M5-38-08:eltako` | `central: A5-38-08:eltako`<br>`rocker: F6-02-01:std` | light, switch |
| Lighting and switching | Dimmer (FUD14, FUD61, FD62 …) | Eltako | `A5-38-08:eltako` | `central: A5-38-08:eltako`<br>`rocker: F6-02-01:std` | light |
| Shutters and blinds | Shutter / blind (FSB14, FSB61, FSB71 …) | Eltako | `G5-3F-7F:eltako` | `controller: H5-3F-7F:eltako`<br>`direction_rocker: F6-02-01:std` | cover |
| Heating and climate | Heating actuator, Home Assistant controls (FHK14, FAE14 …) | Eltako | `M5-10-06:eltako` | `controller: A5-10-06:eltako`<br>`cooling: F6-02-01:std` | climate, sensor |
| Heating and climate | Room controller (FUTH, FTR65HS …) | Eltako | `A5-10-06:eltako` | - | climate, sensor |
| Buttons and contacts | Window handle (FTKE, FFG7B …) | Eltako | `F6-10-00:std` | - | sensor, binary_sensor |
| Buttons and contacts | Door / window contact (FTK, FTKB …) | Eltako | `D5-00-01:std` | - | binary_sensor |
| Buttons and contacts | Rocker switch (F4T55E, FT55, FT4F …) | Eltako | `F6-02-01:std` | - | event |
| Buttons and contacts | Contact via rocker telegrams (FTS14EM, garage door …) | Eltako | `F6-02-01:std` | - | binary_sensor |
| Sensors | Temperature and humidity (FAFT60, FFT65B …) | Eltako | `A5-04-02:std` | - | sensor |
| Sensors | Motion and brightness sensor (FBH65 …) | Eltako | `A5-08-01:eltako` | - | sensor, binary_sensor |
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
| Virtual sensor (Home Assistant sends) | Virtual rocker | Home Assistant | - | `rocker: F6-02-01:std` | button |
<!-- devices:end -->

## EnOcean panel

The **EnOcean** sidebar panel (admins only) starts with a card per gateway: connected,
disconnected (and for how long) or on demand, telegrams per minute, last telegram, devices,
free sender IDs, send queue and unconfirmed commands. Click a card to show only that
gateway's telegrams; on a phone the cards scroll sideways.

Below, every received and sent telegram appears live, newest first: device name (or
"unknown sender" with an **Add** button that opens its discovered card), sender ID, gateway,
telegram type, the decoded values with name and unit as the entities show them ("Power
15 W") and the signal strength. Telegrams per minute count the received telegrams of the
last minute. Sent telegrams name the device and
sender profile; a teach-in of an unknown sender shows its EEP. Click a telegram for its raw
data, status, destination and signal in dBm, or to show only that sender.

Search by device, ID (with or without dashes) or data (key `/`), choose received or sent,
show unknown senders only or include repetitions; **Reset filters** clears them. Pause keeps
collecting and shows how many telegrams wait; export saves the visible ones as JSON lines.
The panel loads the last 200 telegrams of the running session and keeps up to 1,000. It
follows the Home Assistant theme, light and dark.

## Gateway options and repairs

**Configure** on a gateway opens **Settings** (pause between telegrams, discovery, bus
connection, ESP3 repeater) and **Sender IDs**: which of the 128 sender IDs belongs to which
device and profile, how many are free, and which are blocked. An ID of a removed device stays
blocked until it is taught out of every actuator; free it there once that is done.

Repairs point out what needs a hand:

- a gateway that stays disconnected, or a device that has gone silent
- a gateway that reports a different base ID than the one set up (gateway or radio module
  replaced): the actuators know the old sender IDs, so commands would not arrive
- bus actuators that confirm commands after more than 3 s on average: the FAM14 passes
  confirmations on right away only in operating mode 5 with a device list made by PCT14

## Blueprints

Rockers report short, long and double presses per button. Ready-made automations:

- [Rocker switches and dims a light](https://github.com/bertel2020/HA-Enocean-Eltako/blob/main/blueprints/automation/enocean_eltako/rocker_light.yaml) [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fbertel2020%2FHA-Enocean-Eltako%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fenocean_eltako%2Frocker_light.yaml)
- [Rocker controls a cover](https://github.com/bertel2020/HA-Enocean-Eltako/blob/main/blueprints/automation/enocean_eltako/rocker_cover.yaml) [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fbertel2020%2FHA-Enocean-Eltako%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fenocean_eltako%2Frocker_cover.yaml)
- [Double press activates a scene](https://github.com/bertel2020/HA-Enocean-Eltako/blob/main/blueprints/automation/enocean_eltako/double_press_scene.yaml) [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fbertel2020%2FHA-Enocean-Eltako%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fenocean_eltako%2Fdouble_press_scene.yaml)
- [Calibrate covers on a schedule](https://github.com/bertel2020/HA-Enocean-Eltako/blob/main/blueprints/automation/enocean_eltako/calibrate_covers.yaml) [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fbertel2020%2FHA-Enocean-Eltako%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fenocean_eltako%2Fcalibrate_covers.yaml)

## Actions

- `enocean_eltako.capture`: records the telegrams of all gateways, or of one, for a number of
  seconds (default 60) into `enocean_eltako/capture-<time>.jsonl` in the configuration
  directory, for bug reports.
- `enocean_eltako.calibrate_cover`: drives Eltako covers to the nearer end position and
  back, which makes their position exact again (I6).

## EnOcean Proxy app

The optional [EnOcean Proxy](https://github.com/bertel2020/HA-Enocean-Proxy) app (Home
Assistant OS or Supervised) keeps the gateways' serial ports and offers each gateway on a
TCP port, so several programs can use one gateway at the same time, e.g. the old `eltako`
integration while moving over. The app announces its gateways: they show up here as
discovered (**EnOcean Proxy**); pick the model and the gateway is set up with **Replay over
EnOcean Proxy** switched on. After a Home Assistant restart the app delivers the telegrams
that arrived meanwhile (radio telegrams only, up to 15 minutes old), so cover positions and
meter readings stay right. The app is reachable from Home Assistant only, unless you open
its ports.

## Known limitations

- **Bus memory:** reading or writing the FAM14 bus memory (import, link view, actuator
  configuration) is not built yet; it needs captures of the PCT14 ↔ FAM14 exchange.
- **One program per port:** a serial gateway can only be used by one integration at a time.
  Remove it from the old `eltako` integration before adding it here, or share it through the
  EnOcean Proxy app.
- **VLD teach-in:** D2-01 and D2-05 actuators learn by UTE, which needs an ESP3 gateway
  (USB300, MGW-ETH, generic ESP3); ESP2 gateways such as the FAM-USB cannot answer.
- **Generic profiles:** devices added by EEP decode every standard profile, but profiles
  outside the catalog are not checked against hardware; some official test containers
  disagree (see [docs/quality_scale.md](docs/quality_scale.md)).
- **Cover positions** of Eltako actuators are calculated from run times, the actuator
  never reports where it stopped.

## Troubleshooting

1. Open the **EnOcean** panel: is the gateway connected, and do telegrams arrive when you
   press a button? Unknown senders show up there with **Add**.
2. Check **Settings → Repairs** for disconnected gateways, silent devices, a changed base ID
   or slow bus confirmations.
3. For a bug report, download the diagnostics of the gateway entry, and record telegrams with
   the panel's export or the action `enocean_eltako.capture`. Debug logging:
   ```yaml
   logger:
     logs:
       custom_components.enocean_eltako: debug
   ```

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

### Removal

In **Settings → Devices & services → EnOcean Eltako**, delete every gateway entry (its
devices go with it, sender IDs are released). Then remove the integration in HACS, or delete
`/config/custom_components/enocean_eltako`, and restart Home Assistant. Actuators keep the
sender IDs they learned; teach them out on the actuator if a new controller should use them.

## Development

```bash
python -m pip install -r requirements_test.txt
ruff check custom_components tests scripts
mypy
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
