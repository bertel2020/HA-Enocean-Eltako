# EnOcean Eltako – User Guide

[Deutsch](USER-GUIDE.de.md)

## Contents

- [What the integration does](#what-the-integration-does)
- [Installation](#installation)
- [Setting up a gateway](#setting-up-a-gateway)
- [Adding devices](#adding-devices)
- [Device notes](#device-notes)
- [The EnOcean panel](#the-enocean-panel)
- [Sender IDs](#sender-ids)
- [Gateway settings and repairs](#gateway-settings-and-repairs)
- [Taking over the old eltako integration](#taking-over-the-old-eltako-integration)
- [Blueprints and actions](#blueprints-and-actions)
- [Device Proxy app](#device-proxy-app)
- [Known limitations](#known-limitations)
- [Troubleshooting](#troubleshooting)

## What the integration does

EnOcean Eltako connects Eltako (series 14 bus and wireless) and other EnOcean devices to Home
Assistant. Everything is set up in the UI, there is no YAML for devices.

- **One entry per gateway, one sub-entry per device.** Deleting a gateway removes its devices.
- **Several senders per actuator are normal.** An actuator channel can be driven by a
  controller sender, a direction rocker sender and others in parallel; each has its own
  sender ID from the gateway's pool.
- **Safety functions stay in the actuator.** Wind, rain, frost and lock-out protection keep
  working inside the actuator; Home Assistant adds to them and never replaces them.
- **No third-party EnOcean libraries.** Serial ports use Home Assistant's own port picker and
  serial library (the `usb` integration), so serial ESPHome proxies work too. Network
  gateways use plain TCP.
- **Telegrams, EEPs and the FAM14 bus protocol are implemented here.** Standard profiles are
  generated from the official EnOcean Alliance definitions; Eltako variants are kept strictly
  separate and written `EEP:variant`, for example `A5-08-01:eltako` or `F6-02-01:std`.

The list of gateways and devices: [devices.md](devices.md).

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

### Running next to the old `eltako` integration

The old `eltako` integration keeps running in parallel; this one uses its own domain
`enocean_eltako`. A serial gateway can only be opened by one program at a time: remove it
from the old integration before adding it here, or share it through the
[Device Proxy app](#device-proxy-app). When the old integration is set up on the same USB
port or host and port as a gateway here, a repair issue names the gateway and says so; it goes
away once the old entry is off.

## Setting up a gateway

Add the integration once per gateway: pick the gateway model, then its connection and base ID.
Supported gateways and how they connect are listed in [devices.md](devices.md).

- **USB gateways** are picked with Home Assistant's port selector. The port is stored with
  the entry, so Home Assistant attributes it to the integration.
- **Network gateways** (ser2net, PioTek MGW-ETH, Symcon LAN, Device Proxy app) are added by
  host and port. A MGW-ETH and the Device Proxy's gateways are found automatically and show up as
  discovered; a MGW-ETH that gets a new IP address is updated by itself.
- **FGW14-USB and FAM14 on the same bus** form a bus group with failover. The FAM14 can stay
  disconnected until it is needed.
- **Swapping a gateway:** the gateway's menu → **Reconfigure** asks for the model and the
  connection. A defective gateway or a FAM-USB can be replaced by another model, for example
  a network gateway; devices, sender IDs and the actuators' teach-in stay as they are. This
  only works when the new gateway reports the same base ID; with another one the change is
  refused (the actuators know only the old sender IDs). Bus gateways (FGW14-USB, FAM14) swap
  among themselves.
- **Two gateways with one base ID** (for example two radios of one installation): adding the
  second asks for confirmation and stores it as `<base ID>#2`. Sender IDs are never assigned
  twice across them. A discovered gateway with a known base ID counts as moved only if the
  known one is not connected; otherwise it is offered as another gateway.

## Adding devices

Add a device under the gateway with **Add device** in one of six ways:

- **Listen for the device** (recommended): press a button on it or switch the actuator
  locally; the kind is suggested from its telegram.
- **Eltako device** or **EnOcean device of another manufacturer**: pick category and kind
  from the catalog.
- **Virtual sensor**: Home Assistant itself sends, see below.
- **By EEP** (expert): any standard profile of the EnOcean Alliance becomes a device with one
  sensor per value; type a code such as `A5-04-02` to find it.
- **Own definition**: sensors you describe yourself, see below.

Even simpler: every sender the gateway hears that is not set up yet is listed under
**Add device → Discovered devices** of that gateway (a notification tells when new ones
arrive). Picking one suggests the kind and fills in the ID. Senders that are not yours
(a neighbour's, for example) can be hidden there with **Hide this sender**; **Configure →
Hidden senders** on the gateway lists them again. The list keeps the newest 100 senders and
starts empty after a restart; hidden senders are remembered.
Discovery can be switched off per gateway in its settings.

Eltako series 14 actuators learn a sender ID through a learn function on the actuator; which
function belongs to which teach-in button is in [teach_in.md](teach_in.md).

### Switching actuators that do not report

For older or 230 V-only actuators: enter the ID of a pushbutton taught into the actuator under
**Wall switch** and pick its on and off buttons (the same button for both toggles). Its presses
then set the state in Home Assistant, marked as assumed until the actuator reports itself.

### Virtual sensors

Home Assistant itself sends as a window contact (D5-00-01), motion sensor (A5-07-01),
temperature sensor (A5-02-05), brightness sensor (FAH60 format), weather station (FWS61
format: temperature, wind, rain, brightness from any entities), rocker (F6-02-01) or scene
button (scenes 1–4, for example FSB14 learn function 180/200), each with its own sender ID.

- An HA lux sensor can drive the shading automatic of an FSB14, a weather service its wind and
  rain alarm. An HA window contact can lower the heating actuator, an HA temperature can be its
  room sensor.
- It sends on every change of the chosen entity and repeats every 15 min (adjustable). If the
  entity is unavailable, a contact can send the safe value "open"; weather values send nothing,
  so no false alarm goes out.
- With **Send with priority** a contact overtakes every queued command, for the lock-out
  protection of an FSB14.
- Teach it in with the button on the device page; the page also shows the value sent last.

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

**Sharing definitions:** the action `enocean_eltako.export_custom_devices` returns your
definitions (all, or the `ids` you name) as YAML text. Someone else pastes it into
`enocean_eltako.import_custom_devices` (Developer tools → Actions), which checks it and stores
each valid definition as its own file in `/config/enocean_eltako/custom_devices/`; the
definitions are listed under **Add device → Own definition** at once. Your own
`custom_devices.yaml` is never changed, and a definition with the same ID as one in it is
skipped; imported ones are only replaced with `overwrite: true`.

## Device notes

- **Covers** (FSB14/61/71) take a controller sender and a direction-rocker sender in
  parallel. The position is calculated from run times and anchored at the end positions, on
  commands to 0/100 % and after a full run; the actuator never reports where it stopped.
  Vent slots and slat tilt are supported. The travel time assistant in the device settings
  measures all times with a click.
- **Rocker senders** press the buttons you choose (left or right rocker, top and bottom
  swapped), matching how the ID was taught into the actuator.
- **Two-channel actuators** with one ID (for example FSR71NP-2x): each channel is a device of
  its own; channel 2 reports 0x30/0x10.
- **Heating actuators** controlled by Home Assistant get the setpoint; a room temperature
  entity can be added.
- **Rockers** report short, long and double presses per button, which blueprints and device
  triggers use.
- **Weather stations** (FWS61, FWG14MS) report dawn, temperature, wind, sun from three sides and
  rain. Besides these there are "Sunniest side" (south, east, west, or no sun below 2 klx) and
  "Rain recently", which stays on for some minutes after the rain stops (15 by default, set in
  the device's settings), so covers and awnings do not move back out onto a wet surface. The wind
  unit (m/s, km/h, Beaufort) is the entity's display unit in Home Assistant. The "Shade covers by
  the sun" blueprint uses the sun sensors; protection against wind, rain and frost stays in the
  actuator.
- **Permundo PSC132/PSC234** plugs report energy and power; see
  [Known limitations](#known-limitations).

## The EnOcean panel

The **EnOcean** sidebar panel (admins only) has the views **Telegrams**, **Devices**, **Sender
IDs** and, until the takeover is finished, **Takeover** (tabs; the arrow keys move
between them). Above Telegrams and Devices it shows a compact summary per gateway:
connection status, telegrams per minute, last telegram, devices and free sender IDs.
With several gateways, **Telegrams** on a gateway filters by it. **Details** expands the connection, send queue
and unconfirmed commands. For a gateway through the Device Proxy it also shows the app and its version,
connected programs, air time against the 1 % limit and any capture send lock. Once the summary
is scrolled away, the bar of the list (it stays on top) shows each gateway's state and telegrams
per minute; a click on it scrolls back to the cards.

### Telegram list

Every received and sent telegram appears live in a table, newest first, 50 per page: time,
direction, device name (or "unknown sender") with sender ID, telegram type, the decoded values
with name and unit as the entities show them ("Power 15 W"), the signal strength and, with
several gateways, the gateway.

- Click a column header to sort by time, direction, sender, type, signal or gateway (on a
  phone: the sort list). Pages hold 25, 50, 100 or 200 rows; the browser remembers page size
  and sort order. On a later page new telegrams do not push the rows away: the page stays,
  and a button jumps to the new ones.
- Sent telegrams name the device and sender profile; a teach-in of an unknown sender shows its
  EEP.
- Click a telegram for its raw data, status, destination and signal in dBm, or to show only
  that sender. **Open device** leads to the device's page in Home Assistant. Unknown senders also offer **Add device** there to open the integration page, where they wait under **Add device → Discovered devices**; a sender you hid from discovery is tagged **hidden** instead and left out of "unknown senders only".
- The details also show the EEP (with its variant) and, for Eltako devices, the device type;
  what changed against the previous telegram of the sender (changed bytes and values); a
  command and the device's answer with the latency; the repeater hops and how many copies of
  the telegram the gateway heard. For an unknown sender whose telegram fits only a few profiles
  the row says "Could be …".
- **Copy as capture line** puts the telegram on the clipboard in the format of the capture
  action; the export uses the same format, so both can be used as test fixtures.

### Search, filters, pause

Search by device, ID (with or without dashes), value name or data (key `/`) and received or
sent are right above the list. **Filter** opens the others: a gateway, a telegram type (RPS, 1BS,
4BS, VLD …), unknown senders only or with repetitions. Set filters show as chips above the list;
their cross removes one, **Reset filters** clears them all. The panel remembers the filters in the
browser. Pause (key `P`) keeps collecting (up to 1,000) and shows how many telegrams arrived;
export saves all telegrams matching the filter (every page) as JSON lines; on a phone, export
and **Clear display** sit in the **⋮** menu. The badge next to
the title says **Live**, **Paused**, **Connecting…** or **No connection** (then telegrams are
missing until Home Assistant is reachable again). While text in the list is selected, for example
to copy an ID, new telegrams wait until the selection ends.

The panel loads the last 200 telegrams of the running session and keeps up to 1,000; after a
lost connection or a long time in a background tab it adds only what it missed. Clearing the
display does not reset telegrams per minute, which come from the gateway. The panel follows
the Home Assistant theme, light and dark; with a theme or primary colour of your own, that
colour becomes the panel's accent. In a hidden browser tab it pauses its status requests.
Times and numbers follow your profile (time format, browser or server time zone, number
format); "x s ago" counts on the server's clock, so a browser clock that is off does not
matter. Success messages disappear after 4 s, errors stay until closed; screen readers hear a
lost connection and every message.

The panel opens with the view you used last. A link like
`/enocean-eltako?view=devices&sender=05-10-A2-B3` (optionally `&gateway=<entry ID>`) opens a
view with that filter, for example from a dashboard.

### Devices view

The **Devices** switch shows one line per device instead of the telegram list: name and ID,
the EEP, the area, the number of entities, the latest values, when it was last heard, telegrams
in the list and per minute, and a curve of the signal of its last telegrams with a note for weak
reception (below -85 dBm), which a repeater or a better gateway position helps. Your devices
without a telegram in the monitor's buffer are listed too (**not heard**, with **silent** for a
device whose usual interval has passed three times). For an unknown sender the list adds the
telegram type and what its telegrams tell: a teach-in profile or the profiles that could fit.
**Telegrams** opens that device's telegrams, **Add device** sets up an unknown sender, and the
arrow icon opens the device's page in Home Assistant.

**Teach in** (graduation cap icon, for devices with a sender ID of their own) teaches the device
into its actuator without opening the device page: put the actuator into learn mode (on Eltako
actuators usually the rotary switch to LRN), then **Send teach-in**. A device with several sender
IDs (for example central command and rocker) offers a choice. It sends the same as the device's
teach-in button; for a VLD actuator (UTE) send first, then put the actuator into learn mode
within 60 s.

Above the list a hint counts the senders with a weak signal; a click shows only them, weakest
first (also the status **Weak signal** under **Filter**).

A click on a column header sorts by it (again: reverse); on a phone a selection does it. The
search box and, under **Filter**, the gateway, the status (**All devices / Set up / Unknown / Silent / Weak signal**) and the area narrow the list,
and it is shown in pages of 25 to 200 rows. Telegram counts refer to the monitor's buffer (the
newest 1,000 telegrams), not to the time since the start. Export saves the whole filtered list
as CSV; sending and clearing belong to the telegram list and are not offered here.

**Selecting several devices:** every set-up device has a box at the start of its row, **Select all**
above the list ticks all filtered ones. As soon as something is ticked, a bar offers what to do with
all of them at once: set an **area**, add or remove **labels** (a tick adds the label to all, no
tick removes it, a dash leaves it; new labels are created in the form), **disable** or **enable**
the devices, and **remove** them. Area, labels and disabling are Home Assistant's own, so they show
on the device page and work in automations. **Remove** asks first and deletes the devices with their
entities; their sender IDs stay blocked until you confirm under **Sender IDs** that the actuators
have forgotten them. A device's labels show under its name, and the search finds them.

### Send a telegram

The **Send a telegram** button sends a raw telegram (type, data, status as hex) through the
send queue, only from a sender ID that one of your devices already uses, to try out an
actuator. The data field shows an example of the right length for the type (RPS and 1BS one
byte, 4BS four, VLD one to fourteen); length and hex are checked before anything is sent, and
Escape closes the form. For a rocker telegram (RPS) **Press and release** (on by default) sends
the release (data 00, status 20) right after, as a wall switch does. Actuators react to it as
to any telegram; the telegram appears in the list as sent. In the details of a sent telegram,
**Send again** sends it once more (a rocker press with its release) without typing it again.

## Sender IDs

The **Sender IDs** switch of the panel shows who uses which sender ID: per gateway (and per bus
group) the free IDs of the pool, and each device with its IDs, their profile and status, blocked
IDs first. Radio gateways hand out base ID + 1…127. The pool map shows every ID as a small
square (free, assigned, blocked, used elsewhere; the legend below names the colours); the tooltip
names ID and device, a click jumps to its row.

After a device is deleted its ID stays **blocked** until it is taught out of every actuator.
**Free** releases it once the actuator has forgotten it, after a confirmation.

## Gateway settings and repairs

**Configure** on a gateway opens **Settings**: pause between telegrams, discovery, bus
connection, the ESP3 repeater and the gateway prefix in entity IDs.

Without the prefix Home Assistant builds entity IDs from device and entity name
(`light.kitchen`, `sensor.kitchen_signal_strength`). **Gateway prefix in entity IDs** puts
`eno_gw` and the **Gateway number** in front (`light.eno_gw1_kitchen`), which tells
apart the entities of several gateways; every gateway with a prefix needs a number of its own.
The gateway device shows its prefix in the diagnostic sensor **Entity ID prefix**.
The setting applies to entities added from then on. **Rename existing entities now** renames
the gateway's entities right away, in both directions; automations, scripts and dashboards are
not adapted, so check them afterwards.

Repairs point out what needs a hand:

- a gateway that stays disconnected, or a device that has gone silent
- a connection that drops again and again (3 times in 10 minutes), usually a port another
  integration opens as well; loaded integrations on the same port are named
- a gateway that reports a different base ID than the one set up (gateway or radio module
  replaced): the actuators know the old sender IDs, so commands would not arrive
- bus actuators that confirm commands after more than 3 s on average: the FAM14 passes
  confirmations on right away only in operating mode 5 with a device list made by PCT14

## Taking over the old eltako integration

The **Takeover** view of the panel reads the devices of the old `eltako` integration from
`configuration.yaml` (the gateway with the same base ID) and sets up the chosen ones with their
IDs, names and sender IDs, so the actuators need no new teach-in. Four steps across the top
show where you are; the view opens on the first one with something left to do.

1. **Select** lists the devices not set up yet, grouped by area, each with its old platform
   and EEP and the number of places using it. Counters above show how many are in
   `configuration.yaml`, how many are set up already (a click leads to them under Switch over)
   and how many cannot be taken over (folded away at the end, with the reason).
2. **Carry over** shows what comes along from the old integration as cards: **Area**,
   **Labels**, **Voice assistants**, **Own names** (names given in Home Assistant), **Icons** and
   **Hidden / disabled**, each with its values and for how many of the chosen devices it is
   set. Nothing is chosen at first; the panel remembers your choice in this browser; values
   already set on the new device are never overwritten. Below, the preview: each old entity ID
   next to the one its new entity will probably get (Home Assistant gives the ID only when the
   entity is added; for the main entity and the ID sensor it is predicted, a taken ID gets
   "_2"). Nothing is written before **Take over n devices now**.
3. **Switch over** shows where the old entity IDs are still used, in three views:
   **By place** (default) lists each automation, script, scene and dashboard with its old and
   new IDs and **Open the editor**, so you switch it over in one go; **By device** lists every
   device set up here that the old integration had, taken over or set up by hand, with what it
   still lacks and, opened, what it was in the old integration (platform, EEP, names, area,
   labels, sender IDs, when it was taken over and what came along); **Report** is the mapping
   as a table, with copy and CSV. **Check again** after editing; **Carry over…** fills in later
   what a device still lacks. Places written in YAML, templates and other tools such as
   Node-RED are not found: search them yourself with the CSV.
4. **Clean up** is a checklist, each item found from the current state: devices taken over,
   mapping saved, old IDs switched over, old integration deleted, `eltako:` removed from
   `configuration.yaml`. Once the old integration is deleted, **Restore old IDs** gives the new
   entities the old entity IDs back instead (optional): automations and dashboards then work
   unchanged and the history goes on under the old ID; what was recorded under the new ID in
   the meantime stays there, and Home Assistant logs once per entity that it could not move it.
   **Finish the takeover** hides the tab.

The integration keeps the mapping in its own storage, so the report stays readable after the
old integration is deleted and after the takeover is finished: **Takeover report** in the
Devices view opens it. A device of the old configuration not set up yet brings the tab back.

- A rocker sender's `left`/`right` becomes the rocker buttons it presses, `invert_signal` of
  switches and window handles becomes **Invert**, cover times are carried over. Covers get whole
  seconds as with the old integration; **Run times in 100 ms** is for actuators that know that
  form.
- Buttons of the old integration and switches reporting as rockers are not taken over (use a
  virtual rocker). Heating actuators get only the setpoint, as with the old integration, and
  keep their thermostat.

Turn the old integration off once its devices run here: both must not open the same port.

## Blueprints and actions

### Blueprints

Rockers report short, long and double presses per button. Ready-made automations:

- [Rocker switches and dims a light](https://github.com/bertel2020/HA-Enocean-Eltako/blob/main/blueprints/automation/enocean_eltako/rocker_light.yaml) [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fbertel2020%2FHA-Enocean-Eltako%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fenocean_eltako%2Frocker_light.yaml)
- [Rocker controls a cover](https://github.com/bertel2020/HA-Enocean-Eltako/blob/main/blueprints/automation/enocean_eltako/rocker_cover.yaml) [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fbertel2020%2FHA-Enocean-Eltako%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fenocean_eltako%2Frocker_cover.yaml)
- [Double press activates a scene](https://github.com/bertel2020/HA-Enocean-Eltako/blob/main/blueprints/automation/enocean_eltako/double_press_scene.yaml) [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fbertel2020%2FHA-Enocean-Eltako%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fenocean_eltako%2Fdouble_press_scene.yaml)
- [Calibrate covers on a schedule](https://github.com/bertel2020/HA-Enocean-Eltako/blob/main/blueprints/automation/enocean_eltako/calibrate_covers.yaml) [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fbertel2020%2FHA-Enocean-Eltako%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fenocean_eltako%2Fcalibrate_covers.yaml)
- [Shade covers by the sun](https://github.com/bertel2020/HA-Enocean-Eltako/blob/main/blueprints/automation/enocean_eltako/sun_shading.yaml) [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fbertel2020%2FHA-Enocean-Eltako%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fenocean_eltako%2Fsun_shading.yaml)

### Actions

- `enocean_eltako.capture`: records the telegrams of all gateways, or of one, for a number of
  seconds (default 60) into `enocean_eltako/capture-<time>.jsonl` in the configuration
  directory, for bug reports.
- `enocean_eltako.calibrate_cover`: drives Eltako covers to the nearer end position and
  back, which makes their position exact again (I6). A cover with an unknown position
  drives to the open end instead, never to the closed one. `only_if_inaccurate: true` skips
  covers whose position is already known well.
- `enocean_eltako.add_energy_devices`: adds the electricity meters of your devices to the
  **Energy** dashboard as individual devices, with the device's power sensor when it has
  exactly one. Meters with a day and a night tariff use their total sensor when you enabled
  it, otherwise both tariff counters. Meters that are already there stay untouched; gas and
  water meters are not added. Open Settings → Dashboards → Energy once before the first call.

## Device Proxy app

The optional [Device Proxy](https://github.com/bertel2020/HA-Device-Proxy) app (Home Assistant OS or Supervised) keeps the gateways'
serial ports and offers each EnOcean gateway on a TCP port, so several programs can use one
gateway at the same time, for example the old `eltako` integration while moving over, eo_man
or PCT14.

- The app announces its gateways: each one shows up here as discovered (**Device Proxy**);
  pick the model and the gateway is set up with **Replay over the Device Proxy** switched on.
- After a Home Assistant restart the app delivers the telegrams that arrived meanwhile (radio
  telegrams only, up to 15 minutes old by default) with their reception time, so cover
  positions, meter readings and "last seen" stay right. If wanted, the app keeps them over its
  own restart too.
- Its web interface shows every frame live, tests the gateway, sends a single frame, records
  captures (for example PCT14 with a FAM14) and shows the air time against the 1 % limit.
- A gateway the app moves to another port is found again by its base ID and updated by itself.
- A gateway the app announces under another address (the app installed again, from another
  repository) is found by its base ID too: only the address changes, devices and entities stay.
- The gateways are reachable from Home Assistant and the other apps only, unless you allow
  more addresses in the app.
- The app can give a gateway a fallback: a second gateway with the same base ID that stands in
  when the first one fails. The integration stays connected and notices nothing; its gateway
  card shows "Connected through the fallback …" in yellow meanwhile, and the details say
  whether the fallback is ready. The gateway's Connection sensor carries the same as attributes
  (`via_fallback`, `fallback`, `fallback_ready`), for automations.

## Known limitations

- **Not tested on real hardware yet.** Do not use it in production.
- **Bus memory:** reading or writing the FAM14 bus memory (import, link view, actuator
  configuration) is not built yet; it needs captures of the PCT14 ↔ FAM14 exchange.
- **Network gateways serve one connection:** the PioTek MGW-ETH accepts further connections
  but does not answer them; a stuck connection stays until the gateway is restarted. HA then
  raises the repair "… does not answer". Use the Device Proxy app to share one gateway.
- **PSC energy and power:** the Permundo PSC reports them as D2-01 (Wh, W) and A5-12-01. The
  full D2-01 telegram needs an ESP3 gateway (MGW-ETH, Symcon, USB300); ESP2 gateways (FAM-USB)
  cut it, so energy then comes from the A5-12-01 counter, which is sent every 10 minutes.
- **One program per port:** a serial gateway can only be used by one integration at a time.
  Remove it from the old `eltako` integration before adding it here, or share it through the
  Device Proxy app.
- **VLD teach-in:** D2-01 and D2-05 actuators learn by UTE, which needs an ESP3 gateway
  (USB300, MGW-ETH, generic ESP3); ESP2 gateways such as the FAM-USB cannot answer.
- **Generic profiles:** devices added by EEP decode every standard profile, but profiles
  outside the catalog are not checked against hardware; some official test containers
  disagree.
- **Virtual brightness sensor and weather station** send Eltako's FAH60 and FWS61
  formats as documented; not checked against an actuator yet.
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
   use the Device Proxy app). Growing: the diagnostics list "ignored_packets" (packet types
   that are no radio telegram) and "bytes_unparsed".
5. For a bug report, download the diagnostics of the gateway entry, and record telegrams with
   the panel's export or the action `enocean_eltako.capture`. Debug logging:
   ```yaml
   logger:
     logs:
       custom_components.enocean_eltako: debug
   ```
