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
  parallel, position tracking and calibration at the end positions, vent slots and slat
  tilt; the travel time assistant (device settings) measures all times with a click
- **Rocker senders** press the buttons you choose (left or right rocker, top and
  bottom swapped), matching how the ID was taught into the actuator
- **Two-channel actuators** with one ID (e.g. FSR71NP-2x): each channel is a device of its
  own; channel 2 reports 0x30/0x10
- **Virtual sensors:** HA entities sent as EnOcean contact, motion, temperature or rocker
- **Teach-in, discovery, telegram monitor**, import from the FAM14 bus memory
  and a takeover assistant for the old `eltako` integration
- **No third-party EnOcean libraries:** no extra requirements; serial ports
  use Home Assistant's own port picker and serial library (usb integration),
  so ESPHome serial proxies work too

## Supported devices

Add a device under the gateway with **Add device** in one of six ways:

- **Listen for the device** (recommended): press a button on it or switch the actuator
  locally; the kind is suggested from its telegram.
- **Eltako device** or **EnOcean device of another manufacturer**: pick category and kind
  from the catalog.
- **Virtual sensor**: Home Assistant itself sends as a window contact (D5-00-01), motion
  sensor (A5-07-01), temperature sensor (A5-02-05), brightness sensor (FAH60 format),
  weather station (FWS61 format: temperature, wind, rain, brightness from any entities),
  rocker (F6-02-01) or scene button (scenes 1–4, e.g. FSB14 learn function 180/200) with its
  own sender ID. An HA lux sensor can drive the shading automatic of an FSB14, a weather
  service its wind and rain alarm. An HA window contact can lower the heating actuator, an HA temperature can be its room
  sensor. It sends on every change of the chosen entity and repeats every 15 min (adjustable);
  if the entity is unavailable, a contact can send the safe value "open". With **Send with
  priority** a contact overtakes every queued command, for the lock-out protection of an FSB14.
  Teach it in with the button on the device page; the device page also shows the value sent
  last.
- **By EEP** (expert): any of the 318 standard profiles of the EnOcean Alliance becomes a
  device with one sensor per value; type a code such as `A5-04-02` to find it.
- **Own definition**: devices you describe yourself in
  `/config/enocean_eltako/custom_devices.yaml` (see below).

Even simpler: every sender the gateway hears that is not set up yet shows up as a
**discovered** card on the integration page. **Add** suggests the kind and fills in the ID;
**Ignore** hides senders that are not yours (a neighbour's, for example) for good. Discovery
can be switched off per gateway in its options.

**Switching actuators that do not report** (e.g. older or 230 V-only ones): enter the ID of a
pushbutton taught into the actuator under **Wall switch** and pick its on and off buttons
(the same button for both toggles). Its presses then set the state in Home Assistant, marked
as assumed until the actuator reports itself.

### Own device definitions

For a sensor the catalog does not know, describe it in
`/config/enocean_eltako/custom_devices.yaml`: a standard EEP plus which of its fields become
sensors and binary sensors, with names, device classes and units. Afterwards reload the
gateway entry; **Add device → Own definition** lists the definitions.

```yaml
devices:
  - id: acme_climate
    name: Acme room sensor
    manufacturer: Acme
    eep: A5-04-01
    interval: 600          # optional: seconds between telegrams (silence detection)
    sensors:
      - field: TMP         # field shortcut of the profile
        device_class: temperature
      - field: HUM
        name: Humidity     # optional, default: the EEP's name
        device_class: humidity
        unit: "%"          # optional, default: the EEP's unit
    binary_sensors:
      - field: TSN
        on: 1              # optional, default: any value but 0
```

Mistakes show up as a repair issue naming each one; the other definitions still load. If a
definition is removed, its devices keep working as generic EEP devices. Devices added by EEP
or by definition have a diagnostic sensor **Raw data** (disabled by default) with the bytes of
the last telegram, to check the fields.

Generated from the catalog; details in [docs/devices.md](docs/devices.md). Which learn function
to set on an Eltako series 14 actuator for each teach-in button: [docs/teach_in.md](docs/teach_in.md).

<!-- devices:start -->
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
<!-- devices:end -->

## EnOcean panel

The **EnOcean** sidebar panel (admins only) starts with a compact summary per gateway:
connection status, telegrams per minute, last telegram, devices and free sender IDs.
Use **Telegrams** to filter by gateway. **Details** expands the connection, send queue
and unconfirmed commands. For an EnOcean Proxy gateway it also shows the proxy version,
connected programs, air time against the 1 % limit and any capture send lock.

Below, every received and sent telegram appears live in a table, newest first, 50 per page:
time, direction, device name (or "unknown sender") with sender ID, telegram type, the decoded values with name and unit as the entities show them ("Power
15 W"), the signal strength and, with several gateways, the gateway. Click a column header
to sort by time, direction, sender, type, signal or gateway (on a phone: the sort list).
Pages hold 25, 50, 100 or 200 rows; the browser remembers the page size and sort order. On a
later page new telegrams do not push the rows away: the page stays, and a button jumps to
the new ones. Telegrams per minute count the received telegrams of the
last minute. Sent telegrams name the device and
sender profile; a teach-in of an unknown sender shows its EEP. Click a telegram for its raw
data, status, destination and signal in dBm, or to show only that sender. Unknown senders
also offer **Add device** in these details to open their discovered card.

Search by device, ID (with or without dashes), value name or data (key `/`), choose received
or sent, a gateway or a telegram type (RPS, 1BS, 4BS, VLD …), show unknown senders only or
include repetitions; **Reset filters** clears them. Pause keeps
collecting (up to 1,000) and shows how many telegrams arrived; export saves the visible ones
as JSON lines. While text in the list is selected, for example to copy an ID, new telegrams
wait until the selection ends. The panel loads the last 200 telegrams of the running session
and keeps up to 1,000; after a lost connection or a long time in a background tab it adds
only what it missed. Clearing the display does not reset telegrams per minute, which come
from the gateway. It follows the Home Assistant theme, light and dark.

More in the details of a telegram: the EEP (with its variant) and, for Eltako devices, the
device type; what changed against the previous telegram of the sender (changed bytes and
values); a command and the device's answer with the latency; the repeater hops and how many
copies of the telegram the gateway heard. For an unknown sender whose telegram fits only a few
profiles the row says "Could be …". **Copy as capture line** puts the telegram on the
clipboard in the format of the capture action; the export uses the same format, so both can
be used as test fixtures. The panel remembers the filters in the browser, and the key `P`
pauses and resumes.

The **Devices** switch shows one line per sender instead of the telegram list: the latest
values, when it was last heard, telegrams in the list and per minute, and a curve of the
signal of its last telegrams with a note for weak reception (below -85 dBm), which a
repeater or a better gateway position helps. A click opens that sender's telegrams.

The **Send a telegram** button sends a raw telegram (type, data, status as hex) through the
send queue, only from a sender ID that one of your devices already uses, to try out an actuator.
Actuators react to it as to any telegram; the telegram appears in the list as sent.

The **Sender IDs** switch shows who uses which sender ID: per gateway (and per bus group) the
free IDs of the pool, and a table with ID, device, profile and status. After a device is
deleted its ID stays **blocked**; **Free** releases it once the actuator has forgotten it
(teach-out), after a confirmation. The same list is still available in the gateway options.

## Gateway options and repairs

**Configure** on a gateway opens **Settings** (pause between telegrams, discovery, bus
connection, ESP3 repeater) and **Sender IDs**: which of the 128 sender IDs belongs to which
device and profile, how many are free, and which are blocked. An ID of a removed device stays
blocked until it is taught out of every actuator; free it there once that is done.

**Take over from eltako** reads the devices of the old `eltako` integration from
`configuration.yaml` (the gateway with the same base ID) and sets up the chosen ones with
their IDs, names and sender IDs, so the actuators need no new teach-in. A rocker sender's
`left`/`right` becomes the rocker buttons it presses, `invert_signal` of switches and window
handles becomes **Invert**, cover times are carried over. Buttons of the old integration and
switches reporting as rockers are not taken over (use a virtual rocker). Heating actuators, as
with the old integration, get only the setpoint and keep their thermostat; a room temperature
entity can be added. Covers get whole seconds as with the old integration; **Run times in 100 ms** is for actuators that
know that form. Turn the old integration off once its devices run here: both must not open
the same port.

Two gateways may share one base ID (e.g. two radios of one installation): adding the second
asks for confirmation, and it is stored as `<base ID>#2`. Sender IDs are never assigned twice
across them. A discovered gateway with a known base ID counts as moved only if the known one
is not connected; otherwise it is offered as another gateway.

Repairs point out what needs a hand:

- a gateway that stays disconnected, or a device that has gone silent
- a connection that drops again and again (3 times in 10 minutes), usually a port another
  integration opens as well; loaded integrations on the same port are named
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
  back, which makes their position exact again (I6). A cover with an unknown position
  drives to the open end instead, never to the closed one. `only_if_inaccurate: true` skips
  covers whose position is already known well.

## EnOcean Proxy app

The optional [EnOcean Proxy](https://github.com/bertel2020/HA-Enocean-Proxy) app (Home
Assistant OS or Supervised) keeps the gateways' serial ports and offers each gateway on a
TCP port, so several programs can use one gateway at the same time, e.g. the old `eltako`
integration while moving over. The app announces its gateways: each one shows up here as
discovered (**EnOcean Proxy**); pick the model and the gateway is set up with **Replay over
EnOcean Proxy** switched on. After a Home Assistant restart the app delivers the telegrams
that arrived meanwhile (radio telegrams only, up to 15 minutes old) with their reception
time, so cover positions, meter readings and "last seen" stay right. Its status page also
records captures (e.g. PCT14 with a FAM14) and shows the air time against the 1 % limit.
If the app is older than this integration needs (0.5.2), a repair issue asks to update it.
A gateway the app moves to another port is found again by its base ID and updated by
itself; the same goes for an MGW-ETH that gets a new IP address. The app is reachable from Home Assistant only, unless you open
its ports.

## Known limitations

- **Bus memory:** reading or writing the FAM14 bus memory (import, link view, actuator
  configuration) is not built yet; it needs captures of the PCT14 ↔ FAM14 exchange.
- **Network gateways serve one connection:** the PioTek MGW-ETH accepts further connections
  but does not answer them; a stuck connection stays until the gateway is restarted. HA then
  raises the repair "… does not answer". Use the EnOcean Proxy app to share one gateway.
- **PSC energy and power:** the Permundo PSC reports them as D2-01 (Wh, W) and A5-12-01. The
  full D2-01 telegram needs an ESP3 gateway (MGW-ETH, Symcon, USB300); ESP2 gateways (FAM-USB)
  cut it, so energy then comes from the A5-12-01 counter, which is sent every 10 minutes.
- **One program per port:** a serial gateway can only be used by one integration at a time.
  Remove it from the old `eltako` integration before adding it here, or share it through the
  EnOcean Proxy app.
- **VLD teach-in:** D2-01 and D2-05 actuators learn by UTE, which needs an ESP3 gateway
  (USB300, MGW-ETH, generic ESP3); ESP2 gateways such as the FAM-USB cannot answer.
- **Generic profiles:** devices added by EEP decode every standard profile, but profiles
  outside the catalog are not checked against hardware; some official test containers
  disagree.
- **Virtual brightness sensor and weather station** send Eltako's FAH60 and FWS61
  formats as documented; not checked against an actuator yet. While a chosen weather
  entity is unavailable nothing is sent, so no false alarm goes out.
- **Multisensors D2-14-40/41** (FMS55SB, FMMS44SB) are decoded from the profile but not
  checked against hardware yet.
- **Cover positions** of Eltako actuators are calculated from run times, the actuator
  never reports where it stopped.

## Troubleshooting

1. Open the **EnOcean** panel: is the gateway connected, and do telegrams arrive when you
   press a button? Unknown senders show up there; their details offer **Add device**.
2. Check **Settings → Repairs** for disconnected or unstable gateways, silent devices, a
   changed base ID or slow bus confirmations.
3. "Connection … lost: device disconnected or in use by another process" in the log, again
   and again: another program uses the same serial port, for example a second EnOcean
   integration or an app. Only one may open a port; to share a gateway, use the EnOcean
   Proxy app and connect everything to it.
4. A network gateway is connected but "Telegrams received" stays at 0: enable the diagnostic
   sensor **Bytes received** of the gateway. It grows with every byte that arrives, parsed
   or not. Not growing: nothing is sent on this connection (many network gateways serve only
   one client; stop other users such as the old `eltako` integration, an app or a bridge, or
   use the EnOcean Proxy app). Growing: the diagnostics list "ignored_packets" (packet types
   that are no radio telegram) and "bytes_unparsed".
5. For a bug report, download the diagnostics of the gateway entry, and record telegrams with
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
