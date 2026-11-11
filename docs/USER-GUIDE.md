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
- **FGW14-USB** (Eltako bus of the series 14): see [Eltako bus with the FGW14-USB](#eltako-bus-with-the-fgw14-usb).
  A FAM14 is the bus master and has no connection of its own to the computer; it needs a
  gateway entry only when it is reached through an interface of its own. Gateways on the same
  bus form a bus group with failover.
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

### Eltako bus with the FGW14-USB

The FAM14 is the master of the bus; the FGW14-USB sits on that bus like any other device and
connects it to Home Assistant over USB (or over ser2net). You add **one** gateway, the
FGW14-USB. Actuators on the bus (FSR14, FUD14, ...) are devices of that gateway.

- **Sender IDs** of devices on a bus gateway come from the bus pool
  **00-00-B0-00 ... 00-00-B0-7F**, not from base ID + 1...127. The pool belongs to the bus
  group. Enter the ID in the actuator with the PCT14 (or teach it in, see
  [teach_in.md](teach_in.md)).
- **Confirmations:** an actuator answers with a confirmation only when it has a device address
  and the upper rotary switch of the FAM14 is at position 2 while teaching in. Without it,
  commands are repeated and reported as unconfirmed.
- **Not built yet:** reading and writing the bus memory of the FAM14 (see Known limitations).

Commissioning, in this order:

1. Connect the FGW14-USB to the bus and to the computer. Add the gateway; the base ID it reports
   is shown, check that it matches what you expect.
2. Open the Telegrams view and **only listen**: telegrams of bus devices must appear. Do not add
   devices yet.
3. Add **one** uncritical actuator (a lamp). Take the suggested bus ID, enter it in the actuator
   and switch it from Home Assistant. Check that the state follows and that the telegram list
   shows the command once, not repeated.
4. If the command is repeated: check the FAM14 rotary switch and the device address (see above).
5. Add the other actuators one by one, and look at **Installation → Sender IDs**: every ID
   should show its device.
6. Download the diagnostics of the gateway (it contains the bus group and the bus pool) and
   keep it with your installation notes.

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
**Add device → Discovered devices** of that gateway (a card under **Settings → Devices
& services → Discovered** tells how many there are, and points here). Picking one suggests the kind and fills in the ID. Senders that are not yours
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

### Switching actuator and meter on the same load

An FSR14 has no measurement; an F3Z14D (or another meter) measures the circuit. Add them as two
devices and name the function, for example "Bath convector switch" and "Bath convector meter",
both in the same area. In the meter's device settings, **Belongs to device** can point to the
switch: the meter's page then says "Connected via Bath convector switch", and the switch lists
the meter as a connected device. Both stay devices of their own with their own entities, so
entity IDs, sender IDs and history do not change, and the energy dashboard keeps using the meter.
The link can be set or removed at any time.

### Thermostat for a switching actuator (convector)

A switching actuator cannot regulate. Under **Thermostat** in the device settings (collapsed
section), switch it on and pick a room temperature sensor (any temperature sensor in Home
Assistant, for example a SwitchBot); the channel then also gets a thermostat entity. Home
Assistant switches the relay through the send queue, with the senders of the channel.

- **Regulation:** on at setpoint minus hysteresis, off at setpoint plus hysteresis; in between
  nothing is sent, so a relay switched by hand or by a wall switch stays until the next
  threshold. The relay stays at least the shortest time on and off; after the longest run (0 =
  unlimited) it rests for the forced pause.
- **Safety:** without a room temperature (unavailable or silent for longer than "Sensor outdated
  after") the relay goes off and a repair issue says so. The convector's own thermostat stays the
  safety limit: set it above the highest setpoint of the thermostat.
- **Does it really heat?** With a meter that is set to **Belongs to device** this actuator
  (previous section) the thermostat reads its power: "heating" means at least "Heating from
  power". Relay on but no power for the time set under "Report blockade after" and the room below
  the setpoint raises a repair issue (the convector's own thermostat holds it back, or the device
  is out of order). Without such a meter "relay on" counts as heating and the blockade check is off.
- **Humidity:** an optional humidity sensor is shown as the thermostat's humidity; it regulates
  nothing.
- **Extra readings:** power, run time, pause remaining, hours on today and status as attributes of
  the thermostat, and run time, pause, time on today, "Heating" and "Blocked" as entities of their
  own (diagnostics). Both can be switched off. The time on today starts again at midnight and
  after a restart of Home Assistant.

The thermostat is a device option and needs no sender ID of its own; it uses the senders taught
into the actuator.

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
- **FUTH room controllers** (FUTH55ED, FUTH65D) send from four consecutive IDs, and **Room
  controller with several IDs** makes them one device: enter the lowest ID, the one ending in
  `00`. The controller at `+01` gives the climate entity (setpoint, temperature) and night
  setback, the pump at `+10` a binary sensor, the operating mode at `+11` (normal, night
  setback, setback, off) a sensor, and the hygrostat at `+12` humidity, which the climate entity
  shows too. All read only: the FUTH is operated on site. Each of its IDs shows in the Devices
  view, and the documentation lists them with their profiles.
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

The **EnOcean** sidebar panel (admins only) has the views **Telegrams**, **Devices**, **Installation** and, while there is something to take over or a report to read, **Takeover** (tabs; the arrow keys move
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
- **Report device** (unknown senders) copies the sender's last telegrams (up to 60) as capture
  lines and opens the device request on GitHub, where you paste them. Sender IDs, the gateway
  name and the times are replaced before anything is copied; the telegram data, status and
  signal strength stay, as the decoders need them. Nothing is sent from Home Assistant, and no
  data goes into the link. **Record and report** (play button) listens to the sender for 60
  seconds first, so the telegrams of what you do with the device are in the report: press its
  buttons or trigger it, then open the sender's details again and copy the recorded telegrams.

### Search, filters, pause

Search by device, ID (with or without dashes), value name or data (key `/`) and received or
sent are right above the list. **Unknown only** sits right next to them. **Filter** opens the others: a gateway, a telegram type (RPS, 1BS,
4BS, VLD …) or repetitions. Set filters show as chips above the list;
their cross removes one, **Reset filters** clears them all. The panel remembers the filters in the
browser. Pause (key `P`) keeps collecting (up to 1,000) and shows how many telegrams arrived;
export saves all telegrams matching the filter (every page) as JSON lines; **Clear display** sits in the **⋮** menu (on a phone export does too). The chip **Unknown senders only** shows how many unknown senders the buffer holds. The badge next to
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

The **Devices** switch shows one line per device instead of the telegram list: name with ID and
EEP, the type with the area below it, the latest values, and when it was last heard with the
signal strength and a note for weak reception (below -85 dBm), which a repeater or a better
gateway position helps. The arrow opens the details: type, labels, entities, telegrams in the
list and per minute, and a curve of the signal of the last telegrams. Your devices
without a telegram in the monitor's buffer are listed too (**not heard**, with **silent** for a
device whose usual interval has passed three times). For an unknown sender the list adds the
telegram type and what its telegrams tell: a teach-in profile or the profiles that could fit.
With several gateways, a device's details list **Heard by**: each gateway with its last signal
and telegram count, the strongest one tagged **best**; a device that no gateway hears directly
(3 or more telegrams, all repeated) is tagged **via repeater only**.
For a switching actuator or dimmer whose state is known, **Test senders** in the details sends that state
through each of its senders in turn (so nothing changes, at background priority) and tags each
sender **answered** or **no answer**. No answer does not prove that the sender is unknown to the
actuator, as an actuator may stay silent; a rocker that toggles is not tested. A dimmer gets its current brightness as a dim command through its central command; its rocker is not tested, as a press could change the brightness. Covers are not tested at all: every command moves them or interrupts a run. The test does not
count in the command statistics.

**Installation view:** the **Installation** tab gathers the documentation in one place, in four
tabs: **Devices**, **Sender IDs**, **Links** and **Log**. The tables are the same rows as in the
printout.

**Devices** has a switch between four views at the top. Every row names its **kind** as a tag
(Eltako bus, radio sensor, radio button, radio actuator, virtual, power supply); a click on it opens
the view of that kind, and a device with sender IDs from the pool carries **Sender 1, 2**, which
jumps to the Sender IDs tab.

- **All devices** has typed fields you edit in place: place (three fields: cabinet, row, slot),
  circuit, fuse, installation date, revision (the date code, as it decides the learn function),
  supply (mains, battery type) and a note. The **Columns** menu shows them in groups (place and
  fuse, bus, upkeep); the table of all kinds shows only the columns every kind has, the others (bus address,
  supply, revision, part of) appear once you choose a kind above. The kind chips and the filters **Missing: Place** and **Missing:
  Fuse** (with a count) narrow the rows, **Group by** orders them by area or place (the cabinet),
  and **Next without a place** puts the cursor in the first field that is still empty. The
  progress counts devices, power supplies and entries written down by hand, but not virtual
  devices: they have no place. Select rows to set one field for all of them, or **paste from a
  spreadsheet**: a header row, an Address column and columns named like the fields; empty cells
  change nothing, and **Copy the table** gives the same layout to edit and paste back.
- **Bus** shows the Eltako bus grouped by **power supply**: each supply is a header row with its
  type, watts and the bus addresses it feeds (all edited right there), with a load bar and a
  warning when it is overloaded; addresses no supply feeds sit in a group of their own. A strip of
  tiles names duplicate addresses, used and free addresses, the total power and the state of the
  supplies. Devices of the Eltako series 14 (FSR14, FUD14, FSB14 ...) count as Eltako bus even
  without an address: they sit in the group **No bus address yet** until you write it down. You edit bus address, feedback ID and power in the row (the power is what the device
  takes from the bus; without a value of your own the one from Eltako's planning guide counts,
  marked **table**).
- **Radio** lists the radio devices (buttons, sensors, actuators) and the entries written down by
  hand. The columns (menu **Columns**): place, sender ID (all of them for a device with several
  IDs), what it sends, **supply** (battery type, mains), part of, **signal** and **link**. The
  signal is a dot with the time of the last telegram: green within a day, yellow within a week,
  red after that, plus the strength and "via repeater only". The link shows what a button or
  sensor controls and what controls an actuator, each name a jump to the device. **Write down a
  device** adds an entry by hand (name, ID, kind, function): a button taught in directly or a
  device of another system. It carries the tag **only written down**, also shows in **All
  devices** and has place and supply like a device; Home Assistant creates nothing and teaches
  nothing in.
- **Virtual** shows what Home Assistant sends: pool number, sender ID, the entities a virtual
  device follows and the actuators it was taught into according to your notes. With a gateway of
  another base ID every one of these senders has to be taught in again.

**Sender IDs** is the table of the gateway senders: one row per sender (not per device; a device
can hold several), number 0 to 127, the gateway's own ID as number 0, free numbers folded, blocked
IDs first, with their release, and the sender ID pool above it. The device names jump to the device.
**Links** shows who is taught into which actuator, as a card per actuator, per sender or as a
matrix. Every link names the other end, the role (a left or right rocker, say) and where it comes
from: **assigned** (a sender Home Assistant holds for the actuator, with when its teach-in was
sent and what the last sender test said), **declared** (the wall switch set in the device's
options) or **entered** (written down by you: a button taught in directly, an actuator of another
system; only these can be removed here). Each link has a field for its learn position. An actuator
without a link is marked; filters and tiles show those without a link, not tested and without an
answer. **Test senders** runs the sender test from an actuator's card, **+ Link** and **+ Actuator**
write a link down (so does a **+** in the matrix), and a wall switch ID without a device gets
**Write down as device**. What an actuator has really learned is stored in the actuator and cannot
be read, so the tab says so; a link that was never tested says "not tested". **Log** lists what
happened: devices added or removed, senders assigned or removed, teach-ins, sender tests and
imports. Print, the CSV and JSON exports and the notes import sit in the **⋮** menu of the tab.

**Outputs:** the buttons of the Installation tab (and the ⋮ menu of the Devices view) give:

- **Print**: one self-contained page with sections you switch on or off above it (they are not
  printed): **Handover** (every device with address, EEP, senders and the typed fields),
  **Cabinet** (devices by place, with circuit, fuse, revision and power), **Links**, a
  **checklist for a new gateway**, **Sender IDs** (pool with blocked IDs, further devices, unknown
  senders heard since the restart) and the **Log**. With several gateways it opens with an
  overview. It ends with a note on what Home Assistant cannot know. If the browser blocks the print
  window, the page is saved as a file to open and print.
- **CSV** of the devices (one row per sender), **Links as CSV** and **Sender tables CSV** (the
  tables below, one under the other).
- Four more print sections, in the order of an installation list: **Gateway senders** (sender no. 0
  to 127 of the radio pool, which is the base ID plus the number; free numbers are folded; several
  senders of one device point to each other, and senders you wrote down by hand as taught in (the
  GFVS software, say; its IDs are free) follow below with the numbers of their device; bus address and feedback
  ID are fields you write down per device), **Buttons** (each wall switch with the actuators on its
  left and right rocker, taken from the actuators' wall switch option), **Radio senders** (devices
  that only send, and entries made by hand) and **Eltako bus** (every device with a bus address, by
  address 1 to 126, one per channel; free addresses are folded; an address given twice is
  reported). The power is what a device takes from the bus, not the switched load: what you wrote
  down, otherwise the value of Eltako's planning guide (edition 07/2014, the table of the maximum
  power need), marked with `*`. A type the guide does not list (newer devices such as the F3Z14D)
  has no value, and the sum says how many devices have none. The **Devices** table names a wrong bus address or
  watts value under the field instead of sending it. In the **Bus** view
  the fields of a device are changed right where they stand (bus address, feedback ID,
  **Part of**, power; saved as you type). The channels of one device count
  once if they share a **Part of** name; without it the sum counts each channel and says so. The
  supply defaults to the 12 W of the FAM14. In the **Bus** view you write down one or more
  power supplies (type, watts); with the bus addresses a supply feeds, the printout shows the load
  of each one and names addresses no supply feeds, without them only the total. Which addresses a
  supply feeds depends on how the rail is plugged together, so only you know it. Home Assistant cannot read the bus yet, so bus address, feedback ID and the
  entries by hand are written down by you.
- **JSON** (version 2: typed fields, links and the log; the import still reads version 1).

The checklist is for moving to a radio gateway with another base ID: its sender IDs are new and
the actuators know only the old ones, so each assigned sender has to be taught in again. It lists
them, each with its learn position if you wrote one down, and points to the learn function table
(`docs/teach_in.md`), as the right function depends on the actuator's type and revision. Buttons
taught in directly and wall switches are not affected.

**Signal and unknown senders across restarts:** how each gateway hears a device (telegram count,
last signal, whether any telegram came without a repeater) and the unknown senders a gateway heard
(the newest 100) are kept in the same store and written at most once a minute, so **Heard by**,
"via repeater only" and the list of heard senders do not start empty after a restart.

**Notes and further devices:** each device's details have a **Notes** field, each gateway's
details a note field of its own, and under **Devices → Radio** in the Installation tab the button
**Write down a device** for entries by hand (name, ID, kind, function: buttons taught in directly,
devices of other systems; bus address, feedback ID and watts when it sits on the Eltako bus; place
and supply are edited in the table). Saved as you type, kept in a store of its
own per gateway, part of Home Assistant's backup. A device's fields belong to its address, so they
come back if you add the device again; a gateway's details offer to forget those of deleted
devices.

**Import notes from JSON** (Installation tab) reads an export back, for example for a new
gateway: gateways are matched by base ID, devices by address, and only what is still empty is
filled in. Fields, further devices, entered links and learn positions come along, never the
devices themselves. If a gateway has another base ID, the panel offers to import the one gateway of
the file that found no match into the one set up here that got nothing.
**Telegrams** opens that device's telegrams, the **+** of an unknown sender asks whether to **Set up as
device** or **Only write down** (an entry tagged *only written down* under **Devices → Radio** with the ID
filled in, for the documentation; Home Assistant creates nothing), and the arrow icon opens the device's page in Home Assistant.
**Set up as device** leaves the sender for the next **Add device** of its gateway (ten minutes, once): that
dialog goes straight to the kind, with the likeliest one preselected. **Only write down** opens the form of **Write down as device** with the ID and a guessed kind filled in. An entry without a name shows
**Unnamed sender** until you **Give a name**; the ID, the type (for example PTM 215) and the kind stand under
the name, and the more menu (⋮) offers **Set up as device** and **Remove entry**. Place, circuit, fuse,
date of installation, supply and function are filled in like for any device.

**Teach in** (graduation cap icon, for devices with a sender ID of their own) teaches the device
into its actuator without opening the device page: put the actuator into learn mode (on Eltako
actuators usually the rotary switch to LRN), then **Send teach-in**. A device with several sender
IDs (for example central command and rocker) offers a choice. It sends the same as the device's
teach-in button; for a VLD actuator (UTE) send first, then put the actuator into learn mode
within 60 s.

The status tab **Weak signal** (with an amber dot) shows only the senders with a weak signal,
weakest first.

**Group devices** (next to the search) sorts the list under headings by **area** or **type**, or
not at all; the headings fold, name the count and how many in the group need a look. The choice is
remembered in the browser.

A click on a column header sorts by it (again: reverse); on a phone a selection does it. The
search box, the status tabs under the tools (**All devices / Set up / Unknown / Silent / Never heard / Weak signal**, each with its count, empty ones dimmed) and, under **Filter**, the gateway and the area narrow the list (**Filter** only shows with several gateways or areas),
and it is shown in pages of 25 to 200 rows. Telegram counts refer to the monitor's buffer (the
newest 1,000 telegrams), not to the time since the start. The device count appears above the list while a filter narrows it. Export saves the whole filtered list
as CSV; sending and clearing belong to the telegram list and are not offered here. Each row shows one state (active, silent, not heard, disabled, unknown); its **⋮** menu holds teach-in, opening the device in Home Assistant, the device's telegrams and **Remove**, which asks first.

**Selecting several devices:** every set-up device has a box at the start of its row, **Select all**
above the list ticks all filtered ones. As soon as something is ticked, a bar offers what to do with
all of them at once: set an **area**, add or remove **labels** (a tick adds the label to all, no
tick removes it, a dash leaves it; new labels are created in the form), **disable** or **enable**
the devices, and **remove** them. Area, labels and disabling are Home Assistant's own, so they show
on the device page and work in automations. **Remove** asks first and deletes the devices with their
entities; their sender IDs stay blocked until you confirm under **Installation → Sender IDs → Sender ID pool** that the actuators
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

The **Sender ID pool** (Installation → Sender IDs, above the table, can be folded) shows how full the
pool is: per gateway (and per bus group) the pool map with every ID as a small square (free,
assigned, blocked, used elsewhere; the legend below names the colours). The tooltip names ID and
device, a click jumps to its row in the table below. Radio gateways hand out base ID + 1…127.

After a device is deleted its ID stays **blocked** until it is taught out of every actuator. Blocked
IDs stand first in the table, and the tab shows how many wait. **Free** releases one once the
actuator has forgotten it, after a confirmation. **Free all** above the map frees every blocked ID of
the pool, again after a confirmation.
Do this only when every actuator has forgotten them: a new device that gets such an ID would
switch the old actuator too.

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
- a device whose last 5 telegrams in a row fit none of its profiles (a rocker telegram from a
  meter, for example) or, for a standard profile, have values outside its ranges: it was most
  likely set up with the wrong kind. The first case names devices such telegrams are typical for. Teach-in telegrams do not
  count, and one fitting telegram clears the repair

## Taking over the old eltako integration

The **Takeover** view of the panel reads the devices of the old `eltako` integration from
`configuration.yaml` (the gateway with the same base ID) and sets up the chosen ones with their
IDs, names and sender IDs, so the actuators need no new teach-in. Three steps across the top
show where you are; the view opens on the first one with something left to do. **Reports**
next to the steps keeps what each takeover did (see below).

1. **Select** lists the devices grouped by area, each with its old platform and EEP and the
   number of places using it. New devices carry the tag *new*. Devices already set up that still
   lack values of the old integration are in the same list, tagged *already set up* with what
   is missing (for example *Labels missing*). Counters above show how many are in
   `configuration.yaml`, how many are already complete and how many cannot be taken over
   (folded away at the end, with the reason).
2. **Review & take over** shows what comes along from the old integration as cards: **Area**,
   **Labels**, **Voice assistants**, **Own names** (names given in Home Assistant), **Icons** and
   **Hidden / disabled**, each with its values and for how many of the chosen devices it is
   set. Nothing is chosen at first; the panel remembers your choice in this browser; values
   already set on the new device are never overwritten. Below, the preview has one row per
   device; for every option you tick, the values that device brings show up right in the row
   (for example *Area: Hall*, *Labels: Light, Matter hub*). Opened, a device lists its area,
   labels and name, and per entity the old entity ID next to the one its new entity will
   probably get (Home Assistant gives the ID only when the entity is added; for the main entity
   and the ID sensor it is predicted, a taken ID gets "_2") with the name, icon, labels,
   visibility and voice settings that go to it. Of the other entities only some have a
   counterpart, so their values are marked "if a counterpart exists". Devices already set up show the
   values that would be added in the preview. Nothing is written before **Take over (n
   devices)**; this one button sets up the new devices and completes the chosen ones already
   set up, with the same options. A result page then shows what was done and leads on to the
   last step, which is optional: until then the old integration keeps running unchanged.
3. **Retire the old integration** starts with one choice, because the old entity IDs can be
   dealt with in two ways that exclude each other (you can change it later):
   - **Keep the old IDs:** delete the old integration, then **Restore old IDs** gives the new
     entities the old entity IDs back, then remove `eltako:` from `configuration.yaml`.
     Automations, scripts and dashboards work unchanged and the history goes on under the old
     ID; what was recorded under the new ID in the meantime stays there, and Home Assistant
     logs once per entity that it could not move it. An ID that an automation, script, scene or
     dashboard already uses as a *new* ID stays as it is.
   - **Use the new IDs:** the places that still use old IDs are listed by automation, script,
     scene and dashboard with their old and new IDs and **Open the editor**, so you switch each
     one in one go; **Check again** after editing. Then delete the old integration and remove
     `eltako:`. Places written in YAML, templates and other tools such as Node-RED are not
     found: search them yourself with the CSV of the report.

   Automations with a **device trigger, condition or action** (picked by device in the editor)
   do not survive the deletion either way: they hold the old entity's registry ID, which goes
   with the old integration, not its entity ID. Switch those to the new device, or to a state
   trigger on the entity ID, before you delete the old integration.

Every takeover leaves a **report** in the integration's own storage: when it happened, which
settings came along and, per device, what it was in the old integration (platform, EEP, names,
area, labels, sender IDs, the settings of its entities) and its old → new entity IDs. Devices
set up by hand that the old integration had get one report of their own. The reports stay
readable after the old integration is deleted. **Reports** next to the steps (or **Takeover
reports** in the Devices view) lists them; a report opens with copy and CSV, and **Delete**
removes it after a confirmation: the mapping of its devices is gone then, and their old IDs
can no longer be given back. The tab stays as long as there is a report; the steps come back
when a device of the old configuration is not set up yet.

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
- [Covers and lights at dusk and dawn](https://github.com/bertel2020/HA-Enocean-Eltako/blob/main/blueprints/automation/enocean_eltako/dusk_dawn.yaml) [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fbertel2020%2FHA-Enocean-Eltako%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fenocean_eltako%2Fdusk_dawn.yaml)
- [Weather warning with a window open](https://github.com/bertel2020/HA-Enocean-Eltako/blob/main/blueprints/automation/enocean_eltako/weather_warning.yaml) [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fbertel2020%2FHA-Enocean-Eltako%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fenocean_eltako%2Fweather_warning.yaml)

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
  An app that names the model in its announcement (`model`, for example `fam_usb`) spares the
  question; otherwise the model is guessed from the gateway's name. The base ID is read from the
  gateway; if it does not answer, the app's status supplies it.
- After a Home Assistant restart the app delivers the telegrams that arrived meanwhile (radio
  telegrams only, up to 15 minutes old by default) with their reception time, so cover
  positions, meter readings and "last seen" stay right. If wanted, the app keeps them over its
  own restart too.
- What the replay does with them: contacts and other binary sensors take it in one go and
  write their state once when it is through, so a door opened and closed meanwhile does not
  flip the sensor several times or fire triggers for each change; a state that ends where it
  began fires none. The history shows the change at the restart, not at the real time (Home
  Assistant cannot backdate it); "last seen" has the real time. Rocker presses are events, not
  states: replayed ones fire no rocker events, so no automation runs with a press from before
  the restart. Without the replay a contact keeps its last state until it reports again.
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
