# Changelog

> Deutsche Version: [CHANGELOG.de.md](CHANGELOG.de.md)

## Unreleased

## 1.12.0 - 2026-11-13

### New

- **Setup:**
  - The connection step of "Add gateway" points to the optional Device Proxy app (shared gateway, replay, fallback gateway, troubleshooting tools).
- **Panel:**
  - The details of a gateway that is not reached through the Device Proxy app carry the same tip with a link.

### Changed

- **Panel:**
  - "Forget unknown senders after" is now set only in the panel ("Forget automatically…" in the ⋮ menu of the device list), no longer in the gateway settings. The value is kept.

### Fixed

- **Panel:**
  - The entries of the ⋮ menu (including "Forget automatically…", export, documentation) did nothing when clicked: the menu closed as soon as the mouse button went down.
- **Covers:**
  - The state sensor shows "Open" or "Closed" when the reported driven time was a full run (runs with a run time from Home Assistant end with the driven time, not with 0x70/0x50), instead of "Stopped".

## 1.11.0 - 2026-11-12

### New

- **Park unknown senders**: in the panel, unknown senders can be filed from the ⋮ menu as **button**, **unused** or **ignored** (nothing is parked automatically). Parked senders drop out of "All" and the attention count; "Bring back" undoes it, and the chips also offer "Bring all back". Senders hidden before count as "ignored" (migration). "Parked senders" under Configure is gone. Bus senders are marked "Bus · address N" and can be parked together. Pool IDs that Home Assistant did not hand out (e.g. Symcon) are listed and can be kept for another system.
- **Labels for unknown senders**: "Edit label" in the ⋮ menu. It replaces the name, is searchable and is suggested when setting up.
- **Forget in the panel**: "Forget automatically…" sets the days (per gateway), "Forget…" under "New" forgets by period (1, 7, 30 days or all), each with a confirmation. Parked senders and labels stay.
- **Impulse actuator (garage door)**: new type "Impulse (button)" for the switching actuator. The "Trigger" button sends "on" exactly once (never repeated), a diagnostic relay shows the answer. Teach the actuator in as universal rocker ER (rotary switch 10) and set the EW time to 1-2 s. Not yet tested on hardware.
- **Last button (diagnostic)** for rocker switches and contacts via rocker telegrams: a sensor with the button pressed last, off by default.
- **Button position in the choice lists**, e.g. "B0 · right top (0x70)".
- **Lock pushbuttons** (switching actuator, dimmer, shutter): a switch per device. While on, commands from Home Assistant carry the lock bit and the actuator ignores taught-in pushbuttons. The state is assumed. Not yet tested on hardware.
- **Brightness sensors FAH65S, FIH65S and FHD65SB** (A5-06-01 and A5-06-02 in Eltako's layout, not yet tested on hardware). New models: FSTAP, FSMTB, FLGTF65, FLGTF55, FLGTF55E, FSM14.
- **Series 62** (FL62, FR62, FD62, FJ62): buttons "Unlock learn mode" and "Teach out" (diagnostic, off by default). Not yet tested on hardware.
- **Thermostat on a switching actuator channel** (e.g. a convector on an FSR14): optional in the device settings. Home Assistant regulates a room temperature sensor of your choice around the setpoint and switches the relay, with no sender ID of its own. Without a room temperature (or silent for too long) the relay goes off. With a meter set to "Belongs to device", "Heating" shows the real power and a blockade raises a repair issue. Settings include hysteresis, setpoint limits, run times and a humidity sensor. Subentry schema 7 with a migration.
- **Meter under a device**: a meter (e.g. the F3Z14D) can be set to "Belongs to device" the switching actuator on the same load and shows there as "Connected via …". Entities, IDs and history stay. Subentry schema 6 with a migration.

### Changed

- **Takeover: contacts via rocker telegrams** (FSM14, FTS14EM …) now take over "Off with: released", like the old integration. Without it a contact stayed "open" forever after its first opening. Contacts taken over earlier can be changed under "Off with".
- **Bus actuators (series 14 on the FAM14)** confirm up to 10 s later. A command now waits 12 s instead of 1 s for the confirmation, and a cover's run command is no longer repeated. Faster with a device list in the PCT14 and FAM14 operating mode 5.
- **Meter serial number** only on meters that send it (FWZ12, FWZ14, FSDG14, DSZ14DRS, DSZ14WDRS), in the format "S-AABBCC". The digit coding is not yet checked against a capture.
- **Documentation**: the user guide and help text explain "Rename existing entities now" (what it adapts and what not, backup first).

## 1.10.0 - 2026-11-11

### Changed

- **Sensors**: supply voltage sensors (battery or solar cell) show one decimal place; the stored value keeps two.

### Fixed

- **Panel**:
  - The active view reloads by itself when device, entity, area or label registries change in Home Assistant (after a short delay, so a series of changes reloads once).
  - Coming back to the tab reloads the active view (installation, devices, sender pool, takeover); changes made in Home Assistant meanwhile no longer need a page reload.
  - Search fields: the cursor no longer jumps to the start while typing in the installation and bus search fields, and they have a clear (x) button.
  - The round icon buttons (for example the + of an unknown sender) keep their size and stay round instead of being squeezed into an oval.
- **Takeover, mapping and CSV**: the old window handle sensor (`…_windowhandle`) now gets its new counterpart (the Handle sensor) in the old → new entity IDs; it was listed without one.
- **Catalog**: F3Z14D is the first model in the list of the electricity meter.
- **Device flow**: the "Back" switch is labelled "Back (without saving)" and explains itself in its description.

### New

- **Unknown senders**:
  - They are kept across restarts; the panel's devices view and "Add device" list them again.
  - New gateway setting "Forget unknown senders after": they drop out after that many days without a telegram (default 30 days, 0 keeps them).
  - The devices view has a "Forget all" button on the Unknown tab.
- **Panel**:
  - A reload button in the header of every view reloads the data from Home Assistant; its tooltip says when it was last reloaded.
  - Devices view: the row of a set-up actuator shows its sender ID (the first one; the tooltip lists all of them).
  - Connections: the by-actuator list can also be sorted by device ID and by sender number.
  - "Add as device" shows a notice that you continue with "Add device" on the gateway.
- **Device flow**: the device form and the kind list of a heard sender have a "Back" switch that returns to the previous step (address menu, discovered list or start) without saving.
- **Catalog**: F3Z14D (three S0 inputs for electricity, gas and water) is now selectable as a model for the electricity, gas and water meter.
- **Takeover, gateway prefix**: with the gateway prefix on, the carry-over step offers "Gateway prefix in entity IDs". Home Assistant gives an entity that existed before (a device taken over, deleted and taken over again) its former ID, so the prefix was not applied; the option renames the entities of the devices just taken over to the prefix scheme.

## 1.9.0 - 2026-11-09

### Changed

- **Discovered devices, card**: "Add" on the card in Home Assistant's "Discovered" area now shows the heard senders right there (strongest signal first, with type and dBm) instead of only pointing to the gateway. Pick one and "Add device" at the gateway continues straight with it, without the menu and the second list. Senders that are not yours can be hidden in the card; it stays open until the list is empty.
- **Discovered devices**: the list shows the strongest signal first, with the type in words (for example `FF-C2-4A-C5 · Sensors (A5) · -69 dBm`) or the profile from a teach-in. From 7 entries on it is a dropdown instead of a long list, and the description is shorter. Hiding a sender returns to the list while others are left.

## 1.8.0 - 2026-11-08

### Changed

- **Monitor panel on phones**: the view switch (Telegrams, Devices, Installation, Takeover) is now a bottom bar with icons. The Integration link in the header shows only its icon.
- **Monitor panel naming**: inside Installation the group and tab formerly called Devices is now **Documentation**, so it no longer shares its name with the Devices view.
- **Monitor panel header**: the palette and the Integration link are now round 24 px icon buttons in the same look as in the Fritzbox Network panel.

### New

- **Bus sender IDs**: devices on a gateway of a bus group (FGW14-USB, FAM14) get their sender ID suggested from the bus pool (00-00-B0-xx) instead of the radio pool. The pool is shared by the group; a reload of one member no longer blocks the IDs of devices on another.

### Fixed

- **Monitor panel on phones**: the Takeover list keeps IDs and types whole and shows its tags on their own line instead of over the text. The sort and group selects of the Devices view are fully readable, device names may use two lines, tick boxes are larger and a profile hint like "A5-10-06" no longer breaks inside its code.
- **Switching confirmations**: a status that reports the other relay state than the command asked for (the late answer to a command that was replaced) no longer confirms the new command.
- **Devices view with several gateways**: a sender ID set up on two gateways keeps the device and the gateway of each row.
- **Installation**: leaving the bus drawer by Back, a link or a bus change asks first when it holds unsaved input.
- **Documentation import**: each unmatched gateway is reported with its own base ID.
- **Sender IDs**: a failed device save restores every touched ID exactly as it was; a removed gateway keeps its IDs blocked for a gateway added again with the same base ID; the learn step ignores our own pool IDs.
- **Restored switches and lights**: the device keeps the raw relay state, and the sender test waits for a real status telegram (an inverted switch could be switched by the test).
- **Add as device** uses the gateway that was clicked, not the gateway that heard the sender last.
- **Gateway**: closing during a connection attempt no longer leaves the port or socket open; a send queued behind a base ID or repeater command no longer fails with it; a replaced command that was already sent stops waiting for its answer.
- **Telegram history** survives a gateway reload (every device change); the notes object of an unloaded entry is dropped after its flush.
- **Panel**: recording uses the server clock, a takeover answer for another gateway is dropped, the Installation tabs and the popup menus work with the arrow keys, a double click on Save in the bus view creates one item, and the power supply autosave no longer pulls the cursor back.

## 1.7.0 - 2026-11-05

### Changed

- **Takeover workflow**: one button per step. Devices already set up that still lack values of the old integration are now rows of the list in step 1 (tagged with what is missing) instead of a section of their own with a second button. Step 2 previews what happens to each device and has the single **Take over (n devices)** button, which sets up the new devices and completes the chosen set-up ones. A result page then shows what was done and leads to the optional last step, which it explains. The small "Next: retire" link is gone. The websocket command `takeover/carry` takes an optional list of devices.

### Fixed

- **Takeover**: the view after a takeover failed ("nothing to do") when an old entity was used in an automation, script, scene or dashboard.
- **Gateway card**: the "Connected" status no longer takes the look of the device state pills (grey, with two dots).
- **Takeover, devices already set up**: the hint "choose above what should come along" is now plain text; the disabled button no longer carries it as its label.

## 1.6.0 - 2026-11-04

### New

- **Eltako bus view, Read (experimental, not checked with a FAM14)**: reads the bus by listening only; Home Assistant sends nothing to the FAM14 or to a bus device. The FAM14 radios the confirmation telegrams of the actuators with its base ID plus the device address (as Eltako describes them); after an explicit opt-in, the view takes what the gateways of the bus heard before and listens for up to 120 s. It lists the addresses that answered with their last telegram, compares them with the documentation (new checks: addresses heard but not documented, documented channels that did not answer, a suggested base ID), offers to document an address or to set up a heard sender as a device, and the channel drawer suggests the feedback ID (base ID + address). On the wire of the bus (FGW14-USB) the ID is assumed to be the address. Reading the device list, types or the base ID from the FAM14 and importing a PCT14 backup are not built: Eltako does not publish that protocol.
- **Eltako bus view, cabinets**: every row of a cabinet is drawn as a DIN rail to scale in TE, with the modules at their slots (FAM14 as master, a LED per channel: in Home Assistant, only written down, free; a dot for a finding), spacers (½ TE), separator bridges TB14, the terminating resistor 120 Ω, the bands of the supply sections under the rail and how the bus goes on (BBV14, bus coupler FBA14, bus cable with its length). **Arrange** swaps a device with its neighbour by arrow buttons, at the end of a row it moves by half a TE; what overlaps or does not fit is refused (no drag and drop). Devices not on the bus (circuit breakers, RCDs, terminals) are blocks with name and width, written down in the drawer at the first free slot.
- **Eltako bus view, checks of the rail**: a power supply loaded above 4 W without half a TE of air on its left side, and above 6 W right next to the FAM14 without the spacer DS14 (the rules of the FAM14 manual and the operating manual of the series 14), a FUD14 without its spacer, the terminating resistor missing, twice or not at the last device, and a row whose link to the next one is not written down.
- **Eltako bus view, print**: **Print / PDF** gives the rails of every cabinet, the devices and channels by place (address, feedback ID, device in Home Assistant, circuit and fuse), the open checks and label strips at 18 mm per TE to cut out.
- **Eltako bus view by its master**: Installation → Devices → Bus shows the bus as it is built, no longer one table per gateway. The head names the bus master (FAM14, with its base ID written down by hand) and how Home Assistant reaches the bus (a FAM-USB as radio gateway that is not on the bus, a bus gateway as wired access). A **module** is the device on the DIN rail with its **channels** (an FSR14-4x with four channels, each a device in Home Assistant, written down only, or free); the **list** is one table with the address first (the range on the module row, one address per channel row), sortable by address, device, type and place, with search, filter chips (twice, without address, in Home Assistant, only written down), role and cabinet or row, and columns chosen one by one (address and device stay); sorting, filters and columns are kept per browser, free address ranges show between the modules when sorted by address, the **address plan** shows 1 to 126 with duplicates, the **checks** name duplicate addresses and feedback IDs, devices without address or place, gaps, channels not in Home Assistant, bus devices of Home Assistant without a module and overloaded power supplies. A drawer for module, channel, sender and bus links the device in Home Assistant, the senders taught in, the power supply and cabinet and row. The place is chosen from **cabinets with rows** (12 TE unless set otherwise) and a slot in half TE, instead of free text.
- **Catalog of the series 14**: width in TE, bus addresses (one per channel, F3Z14D three), power from and to the bus and role of each type; `docs/devices.md` lists it. Values not yet confirmed by a data sheet are marked.
- **Installation store** `enocean_eltako.installation` (version 1) for the bus of all gateways, with websocket commands to read and change it (checked: half-TE grid, row width, overlap, addresses 1 to 126). Notes store version 8 takes over what the notes held for the bus once per gateway (bus address, feedback ID, power, power supplies with their address ranges, bus entries by hand; channels with the same "part of" text and type become one module, a place "cabinet · row · slot" a cabinet, row and slot). The notes keep these fields as a copy that the store writes back, so the other views, the print and the CSV read the same values; an edit there is taken over. Documentation export version 3 carries the installation; the import takes versions 1, 2 and 3.
- **Solar sensor FAFT60**: the new device type **Temperature, humidity and supply voltage** (profile `A5-04-02:eltako`) reads the voltage of the sensor's energy storage besides temperature and humidity, as a diagnostic entity (**Voltage**). The sensor sends it in the first data byte, 0.025 V per step; a FAFT60 in use reads 2.8 to 3.5 V, rising by day and falling by night. FAFT60 moves from **Temperature and humidity** to the new type; an existing FAFT60 device changes over under **Reconfigure → device type**. The scale (0.025 V) is taken from a device in use, not from a data sheet.
- **Last telegram of each sender**: the newest telegram of every known device and every unknown sender is kept across restarts (type, data bytes, status byte, signal, time; at most 300 senders per gateway, written with the signal data). The opened row of the Devices view shows it under **Radio** as **Last telegram**, with the bytes in hex and what they say, so a sensor that rarely sends always has something to show. Notes store version 7.
- **Eltako bus view**: a power supply loaded above two thirds of its rated power (8 W of 12 W for the FSNT14-12V/12W, the cautious value of Eltako's manuals) shows **another supply recommended** and a highlighted bar; above the rated power it still shows overloaded.
- **Eltako bus view**: **Add power supply** offers the 12 V supplies of Eltako with their rated power (FSNT14-12V/12W, SNT12-230V/12V DC-1A, SNT15-12VDC/15W, WNT15-12VDC/24W) and a custom supply to fill in yourself.
- **Devices view (table)**: the device name opens the device in the Devices view.
- **Room controller with several IDs** (FUTH55ED, FUTH65D): one device for the four IDs a FUTH sends from, entered with its lowest ID (ending in `00`). Controller (`+01`: climate, setpoint, temperature, night setback), pump (`+10`), operating mode (`+11`) and hygrostat (`+12`: humidity, also on the climate entity). Read only. The Devices view lists every ID, the documentation each with its profile. The offsets are those of the old integration's table; the telegrams of a FUTH55ED confirm the controller and the hygrostat, pump and mode are read from the rocker codes `0x70/0x50` and `0x70/0x50/0x30/0x10`.
- **Telegram log**: a command Home Assistant sent is now read like a received telegram: setpoint and night setback of a room controller (a temperature of 0 means the thermostat measures), switch on/off and dim value, shutter up/down/stop with run time, rocker button pressed or released, the status request. Only what the encoders build is read; other profiles still show the raw bytes.
- **Telegram log**: a telegram that a known device's model cannot read, but one to three other models can, names those device types (**Fits** ...). A device saved under the wrong type, such as a Permundo PSC as an Eltako switch, shows raw bytes; now the row says which type would decode them.
- **Takeover**: a switch of the old configuration whose ID has been heard sending a D2-01-09 status (the old integration knows no VLD) is taken over as a **Permundo PSC** with the standard A5-38-08 controller, no longer as an Eltako switch that shows raw bytes.
- **Reconfigure a device**: the **device type** of a switching device can be changed (Eltako switch, Permundo PSC, VLD switch). The sender ID of the first sender carries over, nothing is saved before the form of the new type is confirmed, and the ID is not blocked or taught out because it only changes its profile.

### Changed

- **User guide**: the Devices section describes the status tabs, the grouping and the device count of the new filter bar.
- **Installation → Devices, bar**: the counters "without place / without fuse" are quiet pills hanging right under the tools, and the views, tools and counters sit closer together.
- **Devices view, filter bar**: search, filter, grouping and the Takeover reports now share one row of tools; the status filter is a quiet tab strip under it (pressed tab underlined, empty ones dimmed, weak signal with an amber dot). The line with the device count and the weak-signal hint is gone: the count shows only while a filter narrows the list, the weak-signal tab sorts the weakest first. Grouping reads "No groups / By area / By type".
- **Devices view, opened row**: the cards of the radio section no longer leave a lone card in a row: "heard by" has the full width and the telegram count sits with the other figures. On phones the tabs of the installation fade out at the menu instead of being cut off by it.
- **Installation, sender IDs**: a line under the pool map says what it counts (what Home Assistant has assigned) and that the table below also lists IDs that are only documented.
- **Telegrams view**: calmer rows: no dot before the sender name, the telegram type is plain text instead of a chip, and a sent telegram is laid out like a received one (device name with the "Sent" tag, sender ID below).
- **Installation on phones**: the tabs scroll in one line with the menu beside them instead of wrapping into three rows, and the search and the buttons over a list use the full width.
- **Installation, devices**: the list of all devices has one filter row (the views) instead of two; the kinds are offered inside a view. The clear button of a place shows only when the row is looked at, the checkbox no longer touches the colour bar, and the counters over the table have room of their own.
- **Devices view on phones**: the status chips scroll in one line, search, sorting and grouping share one row, and the weak-signal hint is left out (its chip says the same), so the list starts about 200 px higher.
- **Installation, sender IDs**: the tile "In use" counts the same rows its filter shows (including the gateway).
- **Devices view**: one row per device, read at a glance: name with ID and model on the left, type over area in one cell, state with its values, last heard with the signal on the right. The EEP chip, the entities column, the labels and the telegram trend are gone from the row (labels, entities and telegram counts are in the opened row). Devices are grouped by area (or by type, or not at all) under foldable headings that say how many in them need a look; a new status filter shows devices never heard.
- **Device row**: the columns of values, senders, settings and entities line up in every row, also with long values. The last telegram spans the full width and shows only time, type, signal and bytes; the values read from it stand once under Last values. Entity states are readable (a time as "... ago", numbers in the language's format, on / off translated). Entities are listed as control, readings, diagnostics; one without a name of its own is called like its device, not by its ID.
- **Permundo plug (PSC132, PSC234)**: the rocker can be chosen as a sender next to the central command. A plug taught in as a wall switch is thus switched from Home Assistant; one sender is enough. The buttons default to AI for on and A0 for off, as the plug expects them.
- **Installation, links**: every link row has fixed columns (sender with its ID | role | where it comes from | learn position | state with a short time, the full one as tooltip | actions at the right), rows alike in height, tags never break; the sender number tag no longer repeats in each row, the ID itself leads to the Sender IDs tab. On a phone the row stacks with the actions next to the name.
- **Cross links**: the kind tag of a bus device or power supply opens its channel or module in the bus tab, a row of a cabinet lists its devices in the devices table and a place group of the table links back to the row; a gateway's name opens its card; a used sender ID leads to the links it is in, an opened device to its links card, an entry by hand as sender to its row, a sender ID in the log to its row in the Sender IDs tab. A jump to another tab shows **Back**.
- **Installation, devices table**: one table for all gateways, grouped by place (cabinet · row) at first; the grouping (none, area, place, gateway) is kept per browser, the gateway is a tag of the row. The place is picked from the documented cabinets and rows, with the slot as a number, **+ Add cabinet …** or free text for a place that is no cabinet; ✕ removes it. For a device on the bus it is the place of its module: the devices tab and the bus tab show and edit the same place (notes store version 9 takes it over once). Views and kinds are one filter bar with matching counts. Columns are chosen one by one under their groups, with all / none per group (the earlier choice of groups is taken over); a column is shown as soon as one of the rows can use it, no kind needs to be chosen. Empty places and fields are one quiet dash, the counters above the table plain text. Every table of the installation ends in a narrow menu column, so the row menu (⋮) sits at the same place in each row and opens towards the left.
- **Devices view, opened row**: one card grid (cards from 220 px, alike in height per row; wide content such as the last telegram or "heard by" over two columns) and one row component with inner space and fixed columns for last values, sender IDs, settings and entities. The last telegram reads time · type · dBm, with its bytes and status byte as monospace tags that never break. **Last values** shows what the telegram says (from the live telegram, else from the last stored one) with its source, the raw bytes below; only hex when nothing can be read. Section headings are stronger and count their rows. In the list the name keeps one line (tooltip with the full name), last heard takes two lines, and the values column shows the entities' state before raw hex.
- **Eltako bus view, power supplies**: a FAM14 and the FSNT14 that came with it no longer count twice. A FAM14 up to production week 07/22 has its supply integrated (12 W); a later one is supplied by its enclosed FSNT14-12V/12W. An FSNT14 right beside the FAM14 is taken as that one (an assumption), so the section has 12 W, not 24 W; **Own supply** of the FAM14 in the drawer (12 integrated, 0 via FSNT14) decides instead. The FTS14KS delivers 8 W.
- **Catalog of the series 14** now holds 52 types instead of 33: every DIN rail device of Eltako's operating manual for the series 14 RS485 bus (edition 10/2026) and of the main catalogue (chapters 1 and 2), among them FSR14M-2x, F4HK14, F2L14, FDG14, FD2G14, FSDG14, FRGBW14, BGW14, FWG14MS, FSM14-UC, FPLG14, FPLT14, FTS14FA, FTS14GBZ, DSZ14DRS-3x80A, DSZ14WDRS-3x5A, FLUD14, and the accessories on the rail (FBA14, STE14, DS14, GBA14) as their own role. Power values follow the newer table (F3Z14D 0.10 W, F4SR14-LED 1.00 W, FGW14-USB 0.30 W, FTS14KS 0.40 W); widths follow the catalogue (F4SR14-LED and FUD14/800W 2 TE, FTS14TG 2.5 TE, FTS14EM 2 TE); FSU14 takes 8 addresses and FMSR14 5. What the sources do not give stays empty.
- **Eltako bus view, power supplies**: the load of each supply is computed by the server from the documented modules; with address ranges as before, and by place (the section of the rail between separator bridges TB14 and cabinet ends) once every power supply has a place. The previous view of the supplies by address range per gateway stays inside **Power supplies** and works as before.
- **Only write down** (the + of an unknown sender) opens the form of **Write down as device** with the ID filled in and the kind guessed from the telegram, instead of adding a half-empty row to the list. The form has labelled fields for name, ID, kind, type, place, function, circuit and fuse (for actuators), date of installation and supply, and keeps what was typed when the kind changes.
- **Documented senders** (Installation → Devices, "Only write down"): an entry without a name shows **Unnamed sender** with **Give a name** instead of the ID as its name; the ID stands under the name, the kind is a tag with a small menu, and **only written down** is its own tag. The Signal column says **not monitored**. The more menu (⋮) offers **Set up as device** (with the hand-over to Add device) and **Remove entry**. Both views (All and Radio) draw the entry alike, and the name can be changed by clicking it.
- **Documented senders** have the fields of a device: **circuit**, **fuse**, **date of installation** and **type** (for example PTM 215), besides place, function and supply. They are columns of the table, in the print and in the CSV, and the "without a fuse" tile no longer counts entries that could not be filled. Notes store version 6, with a migration of the entries.
- **Documentation import**: an entry by hand is the same entry when its address is the same, also when it was named since; before, name and address together decided.
- **Panel**: leaving the panel and coming back keeps the telegrams, devices and documentation of the last visit while it refreshes, instead of showing empty lists (kept in the page only; a reload starts empty).
- **Add as device** (the + of an unknown sender in the panel): the next **Add device** of that gateway goes straight to the kind of the sender, without the menu and the list of discovered senders; the likeliest kind is preselected (a press or release telegram: the rocker). The hand-over is used once and expires after ten minutes, after which the menu is back.
- **Telegram log**: for an unknown sender of a press or release telegram the hint lists the rocker profile (F6-02-01) first, ahead of rarer profiles such as the window handle.
- **Installation**: every device name that is a link (Sender IDs, Links, Log, Eltako bus) opens the device in the Devices view, like the name in the table. A device without a row there still opens in the table of the Installation.
- **Installation → Sender IDs**: one table instead of two lists. The list of the pool by device (with its search, chips and sort) is gone; the pool map, **Free all** with its confirmation and the confirmation of a single release stay above the table. Blocked IDs stand first in the table, and the tab shows how many wait.
- **Sender IDs view**: a device with a single ID no longer has a fold arrow; only devices with several IDs can be collapsed.
- **Devices view**: the ⋮ menu of a set-up device has *Remove*, which asks the same confirmation as removing a ticked selection.
- **Installation view**: the kind chips sit on the line of the view switch, and the two missing-data tiles are one compact line.
- **Takeover view**: the two counts above the device list (in configuration.yaml, already set up) are larger.
- **Telegram view**: the *Unknown senders only* chip shows how many unknown senders the buffer holds.
- **Telegram view**: clearing the list moved from its own icon, next to the send button, into the more menu (⋮), so it can no longer be hit by mistake.
- **Installation view**: print, the exports and the notes import sit in one more menu (⋮); the kind chips lose their label and hide a kind without devices; the empty place fields are quiet (no dashed frame) and the two missing-data tiles are more compact.
- **Panel header on a phone**: the palette and the integration link stay on the first line next to the logo (the link as an icon), the views scroll below.
- **Devices view**: every device shows one **state pill** (active, silent, not heard, disabled, unknown) instead of a mix of tags; the first that applies counts, so a disabled device is not judged by its silence. The text names the state, the color only backs it up.
- **Devices view**: the table keeps its widths: the action column has a fixed width, the *Last heard* header sits over its right-aligned values, every row is at least one height, and a device never heard no longer says so twice (the state pill does). On phones the kind tile is smaller.
- **Devices view**: a device with no telegram in the monitor's buffer (after a restart, or one that rarely sends) shows what its entities hold, up to two values, instead of an empty column; unavailable and unknown values are left out, diagnostics and settings never count.
- **Devices view**: the status chips (All devices, Set up, Unknown, Silent, Weak signal) show **how many devices** each would list, for the gateway chosen.
- **Devices view**: every device has a **tile** for its kind (light, cover, climate, button, sensor, meter, virtual), a question mark for an unknown sender; the tooltip names the kind. A device whose model is not fixed (one EEP, several devices, such as the FUD14, FUD61 and FD62) lists the candidates under its name instead of nothing.
- **Devices view**: the buttons of a row no longer move around. Teach in, open the device in Home Assistant and show its telegrams sit in a **⋮** menu; an unknown sender keeps its **+**, and the **checkbox** and the **expand arrow** stay where they are. A device that offers none of these (not heard yet, no page, no senders) has no menu.
- The **+** of an unknown sender (Devices view and telegram details) opens a menu: **Set up as device** as before, or **Only write down**, which adds an entry tagged *only written down* (Installation → Devices → Radio) with the ID filled in and puts the cursor in its name field. Nothing is created in Home Assistant and nothing is learned into an actuator; an ID already written down is not added twice.
- The catalog entry **Rocker switch** (EnOcean) and the device documentation now name the **EnOcean PTM 210/215** pushbutton modules (F6-02-01), found in many switches.
- **Installation view redesigned.** Four tabs (Devices, Sender IDs, Links, Log); the Overview, Senders and Bus tabs are gone, their tables live in the views of the **Devices** tab: **All devices**, **Bus**, **Radio** and **Virtual**, switched at the top. Every row names its **kind** (Eltako bus, radio sensor, radio button, radio actuator, virtual, power supply) as a tag that opens the view of that kind, and a device with sender IDs from the pool carries **Sender 1, 2**, which jumps to its rows in the Sender IDs tab (the device names there jump back).
  - **All devices**: the **place** is three fields that look like one (cabinet, row, slot, stored as "cabinet · row · slot"; older free text is split at the comma); kind chips, filters for a missing place or fuse (with counts), grouping by area or place, a **Next without a place** button and a **Columns** menu. Virtual devices have no place and do not count in the progress; power supplies and entries written down by hand do.
  - **Bus**: grouped by **power supply**. A supply is a header row with type, watts and the bus addresses it feeds, edited right there, with a load bar and an overload warning; addresses no supply feeds sit in a group of their own; tiles show duplicate addresses, used and free addresses, total power and the state of the supplies. Supplies also appear in **All devices** with place, circuit, fuse and note.
  - **Radio**: radio devices and entries written down by hand in one table (place, sender ID, what it sends, **supply**, part of, **signal**: a dot for when it was last heard with strength and "via repeater only", and the **link**: what it controls, what controls it). **Write down a device** (name, ID, kind, function) replaces the editor of the Other devices; such an entry carries *only written down* and also shows in **All devices**.
  - **Virtual**: pool number, sender ID, the entities a virtual device follows and the actuators it was taught into.
  - Devices of the Eltako series 14 (FSR14, FUD14, FSB14 ...) count as **Eltako bus** even without an address and wait in the group *No bus address yet* of the Bus view; a room controller is a radio sensor, not an actuator, so the Links tab does not ask who switches it.
  - **Sender IDs**: the table of the gateway senders with the sender ID pool, as before, one row per sender.
  - **Links**: a card per actuator, per sender or a **matrix**; every link names the other end, the role and its origin (assigned, declared, entered), the learn position and the state. An actuator without a link is marked; tiles and filters show what is open; **Test senders**, **+ Link**, **+ Actuator**, a **+** in the matrix and **Write down as device** for a wall switch ID without a device. The table of the former Buttons tab (left and right rocker) is this tab grouped by sender.
- **Colour in the Installation view**: every kind has its own hue (Eltako bus blue, radio sensor teal, radio button violet, radio actuator orange, virtual magenta, power supply slate), used for the kind tag, the dot of the kind chips, a stripe at the left of each row and the cards of the Links tab. The views are switched with a solid selected button, the tiles carry an accent (green when all is well, amber when something is open), group and supply rows are tinted, the origin of a link has its own colour (assigned orange, declared blue, entered green) in tags and filters, and the events of the log are coloured tags.
- The device table shows **only the columns a kind can use**: the table of all kinds has place, circuit, fuse, installation date and note; choose a kind above and the columns for it appear (bus address, feedback ID and bus power for the Eltako bus; supply for radio devices; part of and revision where they make sense). Empty fields carry short hints (Circ., Fuse, Addr.) instead of the full column name, and the column group *Bus and radio* is just *Bus*.
- The block to **paste from a spreadsheet** is now **Edit with a spreadsheet**: three numbered steps (copy the table, fill it in, paste it back) with a plain hint instead of a tab-separated example, and a line under the text field that says how many rows and fields were found before you apply them.
- Storage and documentation: the notes store is now **version 5**. A power supply of the bus has a place, circuit, fuse and note, and an entry written down by hand has a kind, place and supply (older entries are migrated, the new fields start empty). The documentation tells for every device when it was last heard, the best signal and whether it is heard only via a repeater, and for a virtual sensor the entities it follows.
- **Telegram log**: a telegram Home Assistant sent to a device is no longer shown as if the device sent it. The row carries a **Sent** tag, the name reads "to <device>" and the second line "from <sender ID>".
- **Installation**: checkboxes have their own look (clear box, accent fill with a tick) and the device table gives them room next to the row stripe. **Edit with a spreadsheet** is now a **Spreadsheet** button in the toolbar that opens a card with the three steps, instead of a collapsible block.
- **Sender IDs tab**: each gateway shows tiles (in use, blocked, free, all) that filter the table, a bar of the pool, the **next free ID** with a copy button and a short intro (the long text is a tooltip). The table is sortable (number, device, function, role, status), searchable, filterable by function and **paged (25 by default)**, with a colour stripe and a tag per status; the default view lists the IDs in use and blocked ones, free numbers one row each under *Free*.
- **Log tab**: events read as sentences (the device is a link to its row, sender test results are tags: confirmed, not confirmed, failed), grouped by day with the time relative to now, filterable by kind and period (today, 7 days, all), searchable, sortable, **paged (25 by default)** and downloadable as CSV.
- **Links tab**: one sentence of intro (the long text is a tooltip); the tiles (actuators, without link, no answer, not tested, answered) filter the list, the source is three toggle chips, search and sorting (name, status, number) are new, the learn position shows on request, and the actuators are **paged (25 by default)**.
- **All devices**: the **Missing** chips and the progress line are two tiles (without a place, without a fuse) with the count and "x of y recorded" that filter the table, next to **Next without a place**; an empty place is one **+ Add place** button that opens the three fields only when clicked; the table is **sortable** (column headers) and **paged (25 by default)**; placeholders are written out (Circuit, Address, Fuse) and the *Group by* select is styled.

### Fixed

- **Installation, Log**: the tab did not open as soon as an event was less than a day old (the display of "... s ago" failed, the tab stayed on the previous view).
- **Installation views**: the summary tiles (Funk, Virtuell, Eltako-Bus) no longer overlap their text. The icon-tile style of the device list applied to them too and squeezed them to 36 px. The supply rows of the bus view now show the whole placeholder of the address fields.
- **Telegram log**: the direction is the one marker of a row: a green arrow for received, a blue one for sent. The blue bar and tint on sent rows are gone; a bar now marks only a warning: a sent command without an answer within 3 s gets an amber bar and a tag.
- **Takeover**: after taking devices over, the view always lands on step 3 (retire the old integration). When the old integration has no entities left for them, step 3 says so instead of the view falling back to step 1.
- **Last heard** is kept across a restart: it comes from the saved signal data, no longer only from the *Last seen* sensor, which is disabled by default. A device that has not sent since Home Assistant started is no longer shown as never heard.

## 1.5.0 - 2026-11-02

### New

- **Appearance** of the panel (palette button in the header): three colour schemes (Ocean, Forest, Graphite), each light and dark; light, dark or like Home Assistant; font size small, normal or large (12.6, 14 or 16 px, every size in the panel follows). The choice is stored per Home Assistant user and cached in the browser.
- The tables of the Senders and Bus groups are **editable in place**: bus address and feedback ID (gateway senders, bus), place (buttons, radio senders), **Part of** (radio senders) and bus power (bus). A device with several senders shows the same value in every row and all rows follow a change.
- **Several power supplies** of the bus: each with type, watts and, optionally, the bus addresses it feeds. The printout shows the load of every supply with a range, the total, and addresses no supply feeds. The notes store is now version 3 (a single supply of version 2 is migrated).
- The **Eltako bus** table lists bus addresses 1 to 126 (one per channel) with free runs folded and an address given twice reported, and takes the power of a type from Eltako's planning guide (07/2014) where you wrote none down; the supply defaults to the 12 W of the FAM14. Types the guide does not list (newer devices) have no value.
- New device field **Part of**: radio IDs with the same value (a room controller such as the FUTH55 sends under several IDs) are one block in the **Radio senders** table of the printout, each ID saying what it sends.
- **Eltako bus** table in the printout: every device with a bus address, by address, with the power it takes from the bus (written down by hand, from its data sheet), the sum and the load of the bus power supply, which you write down in the gateway details. Devices of the bus that Home Assistant does not hold are entries by hand with bus address, feedback ID and watts.
- The printout has three more tables: **Gateway senders** (sender no. 0 to 127 of the radio pool, free numbers folded, several senders of one device pointing to each other, and senders you wrote down by hand below, with the numbers of their device), **Buttons** (each wall switch with the actuators on its left and right rocker) and **Radio senders** (devices that only send, and the entries by hand). New fields **Bus address** and **Feedback ID** per device, and **Sender tables CSV**.
- A **checklist for a new gateway** in the printout: every assigned sender to teach in again when a radio gateway with another base ID takes over.
- **Links as CSV**, and the JSON export is now version 2 (typed fields, links, the log); the import still reads version 1.
- **Links** in the Installation tab: who is taught into which actuator, by actuator or by sender, each link marked as assigned, declared (wall switch option) or entered by you, with the teach-in time, the last sender test and a learn position. The JSON export carries them and the import takes entered links and learn positions back.
- The new **Installation** tab of the panel: devices by area or place, a table with typed fields (place, circuit, fuse, installed, revision, power, note) edited in place, for a selection or pasted from a spreadsheet, and the event log.
- The installation keeps an **event log** per gateway: devices added or removed, senders assigned or removed, teach-ins, sender tests and imports.
- Importing notes into a **swapped gateway** (another base ID): the panel offers to map the one unmatched gateway of the file to the one set up here.

### Changed

- The panel tells why a gateway behind the proxy app shows no status: **proxy status not reachable** (request failed) or **does not list this gateway** (the app's status has no gateway on our port). The diagnostics carry the status URL (host masked) and the last error, and the first failure is logged on debug.
- **Devices** table: a progress line (devices with a place), columns in groups to show or hide (place and fuse, bus and radio, upkeep; remembered per browser), and a wrong bus address or watts value is named under the field and not sent.
- **Sender IDs** is no longer a tab of its own: it is the **Sender ID pool** above the table under Installation → Senders → Gateway senders, always shown and foldable (pool map, who uses which ID, release of blocked IDs, also from a blocked row of the table). `?view=senders` and a saved Sender IDs view open it there.
- The tabs of the Installation view are real tabs (underlined) in two levels; the switch between table and ID management is gone. The first group is now **Devices** (Overview, Table); the grouping by area or place is a segmented switch, each gateway is a card with its device count, and a gateway without devices offers a button to the integration.
- The **Installation** tab is now the place for documentation and administration, in groups: Site (by area, devices), Senders (gateway senders, buttons, radio senders), Bus (Eltako bus, power supplies), Links, Log. The sender and bus tables show the same rows as the printout; the power supplies and the entries by hand moved there from the gateway details, and the output buttons are one **Output** menu.
- The **Takeover** view shows the switch between takeover and reports at once, with an animated placeholder while it loads, so the reports are reachable without waiting for the takeover.
- **Heard by** and the heard but unknown senders **survive a restart**: how each gateway hears a device and the newest 100 unknown senders are kept (written at most once a minute).
- The printout is **one page with sections** you switch on or off above it (handover, cabinet, links, checklist, sender IDs, log); it replaces the separate cabinet sheet.
- A device's notes are now typed fields (store version 2, migrated from version 1 on first load); exports and the import carry all of them.

### Fixed

- Importing notes of a **two-channel actuator** put the second channel's note under the first channel's key; exports now carry the key of each device.

## 1.4.1 - 2026-11-01

### Fixed

- The **⋮ menu** of the Devices view, which holds the installation documentation (print, cabinet sheet, CSV, JSON, import), was only shown on narrow screens. It now also shows on desktop.

## 1.4.0 - 2026-11-01

### New

- **Test senders** also works for dimmers: the central command repeats the current brightness; the rocker is skipped, as a press could change it. Covers stay untested, as every command moves them.
- **Record and report** for unknown senders: listens to the sender for 60 seconds first, so the telegrams of what you do with the device are in the device report.
- The **profile check repair** also fires for values outside the ranges of a standard profile, and names devices that telegrams of the unexpected type are typical for.
- **Import notes from JSON** in the Devices view menu: reads the notes and further devices of an earlier documentation export back (matched by base ID and device address), filling in only what is empty. Devices are never imported.
- A gateway's details offer to **remove the notes of deleted devices**, which otherwise stay for when the device returns.
- **Cabinet sheet** in the Devices view menu: a dense landscape printout, one table per gateway, for the distribution board.
- Screenshots of the sidebar panel (sample data) in both READMEs.
- **Further devices** in a gateway's details: write down buttons taught in directly, devices of other systems and anything else Home Assistant cannot see (name, ID, function). They appear in the printout, CSV and JSON of the installation documentation.
- The printed **installation documentation** opens with an overview page, one line per gateway, when there are several gateways.
- **Installation documentation** also lists the unknown senders a gateway heard since the restart (not set up), and keeps the result of the last **Test senders** across restarts.
- **Notes** for the installation documentation: a field in each device's details and in each gateway's details (place, terminal, fuse, battery date). They are stored per gateway, belong to the device address and appear in the printout, CSV and JSON.
- **Installation documentation** in the Devices view (⋮ menu): print it (one gateway per page), or download it as CSV or versioned JSON. It lists devices with address, EEP, area and wall switch, the assigned senders with teach-in kind and sender test result, and the sender ID pool with blocked IDs, and says what Home Assistant cannot know.
- **Test senders** in the details of a switching actuator: sends its current state through each sender in turn (nothing changes) and shows which senders it answers.
- **Heard by** in a device's details: with several gateways, each gateway with its last signal and telegram count and the strongest one tagged; a device that only a repeater carries is tagged **via repeater only**.
- **Profile check repair**: a device whose last 5 telegrams in a row fit none of its profiles raises a repair (it was most likely set up with the wrong kind); a fitting telegram clears it.
- **Report device** for unknown senders in the telegram details: copies the sender's last telegrams (up to 60) with IDs, gateway and times replaced and opens the new device request form on GitHub. Nothing goes into the link.
- **Hardware column** in the supported devices list: a ✓ where the repository holds a real capture of that model (`tests/fixtures/captures/<model id>.jsonl`).
- **`scripts/capture_to_fixture.py`** turns a capture into an anonymous test fixture (IDs, gateway names and times replaced, telegram data kept), so a bug report can become a regression test.
- **Quality scale**: a self-assessment against the Home Assistant integration quality scale (Bronze to Platinum) in [docs/quality_scale.md](docs/quality_scale.md), also in German.

### Changed

- The printed **installation documentation** repeats table headers on every page and keeps headings with their table.
- **Signal curve** in the devices list is larger (96 × 32 px; the global 20 px icon size no longer squeezes it) and zooms to the data: the band is at least 16 dB wide, so a steady sender no longer shows a flat line. The weak-signal line appears only when it lies inside the band.

## 1.3.0 - 2026-10-26

### Changed

- **Telegram details** put the data first, with the previous telegram right below it and the changed bytes marked in both (plus a line like "Byte 3 changed: 44 → 49"). The metadata sits in two rows, the signal is left out (it is in the row), and the actions are icon buttons.
- **Devices** list: wider values column, narrower area and entity columns, and "Add device" is a round filled plus button (its name stays as the tooltip).
- **Signal curve** in the device view takes the colour of the last value, ends in a dot and shows the weak-signal line (-85 dBm).
- **Search** shows the `/` shortcut as a small key in the field instead of a tooltip over the whole label; the column headers lose their sort tooltip (the sort state stays in the arrow and for screen readers).
- **Telegram list** can hide an unknown sender from discovery with one click (button in the opened row). It is shown again under Configure → Hidden senders.
- **Could be** (profile candidates of an unknown sender) now sits below the value and lists two profiles plus "+n" (all of them in the tooltip), in the telegram list and the device view.
- **Sender IDs** show the number counted from the base ID (1 to 127) instead of the decimal ID, in the list and on the map.
- **Devices** show the status chips, the search and the filters in one row.
- **Sender IDs** show the status chips, the search and the sorting in one row.
- **Telegram list** puts a small dot before the sender: filled for known devices, hollow for unknown ones.
- **Signal bars** in the telegram list and the device view are coloured by strength: green, amber or red.
- **Telegram list** tints sent telegrams slightly and marks them with an accent bar, so they stand out from received ones.
- **Takeover search** also finds labels, in the review preview (device and entities) and in the reports.

## 1.2.0 - 2026-10-24

### Changed

- **Takeover, three steps instead of four:** Select, Review & take over, Retire the old integration. The old
  "Switch over" and "Clean up" steps are gone, and with them **Finish the takeover**.
- **Review shows what comes along:** for every option you tick, the preview lists per device the actual values (area,
  labels, names, icons, hidden/disabled, voice assistants), also per entity. Devices already set up are completed in
  the same step.
- **Retire the old integration:** you first choose how the old entity IDs are dealt with, either keep them (delete the
  old integration, give the new entities the old IDs back, remove `eltako:`) or use the new ones (switch the places
  that use old IDs, delete, remove). The steps follow from the choice.
- **Reports:** one report per takeover, always reachable under **Reports** in the Takeover view, openable and deletable.
  The old reports are migrated (one per gateway and day).

### Fixed

- **Restore old IDs** no longer renames a new ID that an automation, script, scene or dashboard already uses.
- **Virtual rockers** (old buttons) get a report entry and are completed by "Devices already set up".
- A device taken over after its old entities are gone still gets a report.

## 1.1.1 - 2026-10-24

### Changed

- **Discovery card:** the dialog names how many senders were heard by type (for example "15 sensors (A5), 9 rockers
  (F6)") and links to the gateway, instead of listing ten IDs.

## 1.1.0 - 2026-10-23

### Changed

- **Discovered devices:** a gateway that heard unknown senders shows one card under Settings → Devices & services →
  Discovered (with the number of senders) instead of a notification. The card lists them and points to **Add device →
  Discovered devices** of the gateway; it goes away when there is nothing left to discover.

## 1.0.2 - 2026-10-23

### Fixed

- **PioTek MGW-ETH behind the Device Proxy:** the gateway is no longer offered again as discovered on its own address
  once an MGW-ETH is set up through the app (it serves one connection only, the app holds it).

## 1.0.1 - 2026-10-23

### Fixed

- **Device Proxy, base ID:** when the gateway behind the app does not answer the base ID read while it is set up, the
  integration takes the base ID from the app's status instead of asking for it.

## 1.0.0 - 2026-10-23

### New

- **Sender IDs view:** a search (device name, profile, ID with or without dashes, decimal), chips for All / Assigned /
  Blocked and a sort (blocked first, name, sender ID). **Free all** frees every blocked ID the list shows, after a
  confirmation.
- **Device Proxy discovery:** an app that names the model of a gateway in its announcement (`model`, for example
  `fam_usb`) spares the model question; without it the model is still guessed from the name.

### Changed

- **Panel filters:** the device status is a row of chips instead of a dropdown in the filter menu, and "Unknown senders
  only" is a toggle beside RX / TX in the telegram view. **Filter** only shows in the devices view when there are several
  gateways or areas to choose from.

### Fixed

- **Device Proxy replay, binary sensors:** contacts, window handles, motion and rain sensors take the replay of telegrams
  the Device Proxy kept during a restart in one go: the state is written once when the replay is through, so a door
  opened and closed in the meantime no longer flips the sensor (and fires triggers) several times, and a state that ends
  where it began fires none.
- **Device Proxy replay, rockers:** replayed rocker presses fire no rocker events. Gestures are timed live, so a replayed
  press became a short press (or two a double press) at the restart and ran automations with a press from minutes ago.

## 0.1.13 - 2026-10-23

### New

- **Weather station:** a "Sunniest side" sensor (south, east, west, or no sun below 2 klx on every side) and a "Rain
  recently" sensor that stays on for some minutes after the rain stops, so covers and awnings do not move back onto a wet
  surface. The minutes are a device setting (15 by default, 0 = no hold).
- **Blueprint "Shade covers by the sun":** moves covers to a shading position when the sun on one side stays strong
  enough, and back when it has been weak for a while; optionally only when it is warm; leaves covers alone whose
  "Automation mode" is Off and covers you moved by hand.
- **Blueprint "Covers and lights at dusk and dawn":** closes covers and switches lights on when it has been dark for a
  while, opens and switches off in the morning; a cover's "Automation mode" decides (Evening and Both in the evening,
  Morning and Both in the morning, Off never), with earliest times so a storm cloud at noon closes nothing.
- **Blueprint "Weather warning with a window open":** a notice (any action you choose) when it starts to rain or blows
  while a window is open, and when a window is opened in bad weather. It moves nothing.

### Changed

- **Weather station:** dawn and the three sun sensors show whole lux (dawn no longer "999,0 lx"), the wind one decimal.
  Rain is a plain on/off sensor shown as "Rain" / "No rain" with the rain icons, no longer a "moisture" (leak) sensor
  that assistants might treat as a leak alarm. The wind's unit (m/s, km/h, Beaufort) is the entity's display unit
  setting in Home Assistant.
- **Device page:** a device without a named type lists its EEP once, as the model, not again as the model ID.
- **Panel, Devices view:** the boxes have a column of their own, so name and ID line up, and "Select all" sits in the
  table head above them (on phones it stays in the line above the list). The bar of the ticked devices takes the place
  of the count line, the row icons are subdued until the pointer is over the row, and "not heard" is muted.

## 0.1.12 - 2026-10-23

### New

- **Panel, Devices view:** select several devices (a box per row, "Select all" for the filtered ones) and, with a bar,
  set an **area**, add or remove **labels** (new labels can be created in place), **disable** or **enable** them, or
  **remove** them from Home Assistant in one go. Area, labels and disabling are Home Assistant's own, so they show on
  the device page too. Removing asks first, reloads the gateway once and leaves the devices' sender IDs blocked until
  the teach-out is confirmed under Sender IDs.
- **Panel:** a device's labels show under its name, a disabled device is tagged, and the search finds labels.

## 0.1.11 - 2026-10-23

### New

- **Cover automation mode:** every cover has a select "Automation mode" (Off, Morning, Evening, Both; Both until chosen
  otherwise) for your own automations, like the old Eltako integration's. It moves nothing by itself and is kept across
  restarts.
- **Cover state and driven time:** FSB covers have a "State" sensor (opening, closing, open, closed, stopped) and a
  "Driven time" sensor (with the direction) from the actuator's confirmation telegrams.
- **Panel:** an Integration link in the header bar and in the gateway details, straight to that gateway's entry.

### Changed

- **Cover routing:** a cover moves through one sender, the controller or the direction rocker. "Both" is gone: it sent two
  telegrams per run, and the direction rocker stops a run on the same direction again. Existing covers with "Both" keep
  the controller (the direction rocker where they have no controller).
- **Takeover:** a rocker (F6-02-01, F6-02-02) of the old binary_sensor platform becomes a rocker contact with its device
  class and inverted flag, not a button. The takeover stays on the selection when nothing is left to switch over and
  says so in step 3.

### Fixed

- **Rocker and wall switch buttons:** the collapsed sections show the button in use (or the default) preselected instead
  of no choice at all.
- **Device page:** the EEP is listed once, as model ID, not also in the model.

## 0.1.10 - 2026-10-23

### Changed

- **Links to the device in the panel:** an opened telegram has a "Device in panel" button, and the device name of a sender ID
  group is a link: both open the device's row in the Devices view. "Open device" is now "Open in Home Assistant".
- **Panel look:** logo and view tabs line up with the content (at most 1200 px, centred) instead of the window's
  edges, like in the Device Proxy app.
- **Sender IDs:** the top of the view is clearer: tiles for free, assigned and blocked IDs and the next
  free ID (with a copy button), one bar for the share used, a note when blocked IDs wait for their teach-out
  (with a button to the first one), a pool map whose rows name their ID range, and a line under the map that
  tells ID, number, state and device of the chosen square. The legend shows the numbers.

## 0.1.9 - 2026-10-23

### New

- **Device model:** a device of a kind that several Eltako models share (switching actuators,
  dimmers, shutter actuators, heating actuators, meters ...) has an optional "Model" field: pick
  FSR14-4x, FUD61NPN-230V ... or type another one. It is shown in the telegram monitor and on the
  device page and changes no behaviour. New device data version (schema 4, migration included).

### Changed

- **Telegram monitor:** the radio does not tell which model sent a telegram, so the monitor no
  longer shows the first example of the kind (FSR61 for an FSR14). Without a chosen model it lists
  the possible models; the device page shows the EEP only.
- **Weather station:** the example FWG14 is named FWG14MS.
- **Devices view:** a set-up device's row opens in place and shows everything known of it: identity
  (model, EEP, area, gateway, ID), radio (last heard, signal with minimum and maximum, repeater hops,
  telegram count, expected interval), latest values, sender IDs with their teach-in kind, command
  statistics (sent, confirmed, answer time), settings and entities with their states. Several rows
  can be open; they stay up to date, and the list keeps its order while one is open. A click on the
  row no longer jumps to the telegrams: the filter button of the row does that.
- **Devices view:** the model of a device is set in its opened row: a dropdown with the models of its
  kind, "Not specified", or "Other model…" to type one. It is saved at once (the gateway's entry
  reloads, as after any change of a device).
- **Devices view:** the opened row shows its values as small tiles and tables on white, like the statistics of the
  Device Proxy app; the share of confirmed commands is a coloured chip.
- **Panel look:** the panel looks like the Device Proxy app: its page colour, larger rounded cards
  with a soft shadow, and pill-shaped view tabs. The accent colour is always the blue of the app; it
  no longer follows the primary colour of a Home Assistant theme (light and dark still follow it).
- **Devices view:** the list always opens sorted by name; a column sort you click applies until the
  panel is closed and is no longer kept.
- **Telegram monitor:** an open telegram pauses the list: new telegrams wait (the live badge shows
  "Paused" with their number) while you read the details and appear when you close the last open
  one. A pause you set yourself stays until you resume.

## 0.1.8 - 2026-10-22

### Changed

- **Device Proxy:** the gateway card and the gateway's connection sensor show whether the app's
  fallback gateway stands in and whether it is ready.

### Fixed

- **Panel:** the EnOcean panel no longer stays blank when one of its files fails to load once
  (during a Home Assistant start or a proxy hiccup): the parts load with retries, and if they
  still fail the panel shows a message with a Reload button.

## 0.1.7 - 2026-10-22

### Changed

- **Panel, Takeover:** what to carry over from the old integration is chosen on its own
  (area, labels, voice assistants, own names, icons, hidden / disabled), with the number of
  devices each concerns; nothing is chosen at first and the choice is remembered per browser.
  Own names, icons and hidden / disabled are new.
- **Panel, Takeover:** devices already set up are no longer a list in Take over but a hint
  leading to Check, which became the overview of every device set up: what it still lacks from
  the old integration, the places using its old IDs, a view by place with links to the editors,
  filters Still in use and Done, and Check again.
- **Panel, Takeover:** Take over asks first: a confirmation shows the devices, entities and
  places to switch over afterwards, the chosen options and each old entity ID next to the one
  its new entity will probably get; only Take over now sets the devices up.
- **Panel, Takeover:** four steps, Select, Carry over (the options as cards with their values,
  and the preview of old and new IDs), Switch over (by place, by device with what each device
  was in the old integration, and the report as a table) and Clean up (a checklist found from
  the current state); Finish the takeover hides the tab.
- **Takeover:** the mapping of old to new entity IDs is kept in the integration's own storage,
  so the report stays readable after the old integration is deleted; Takeover report in the
  Devices view opens it.
- **Takeover:** Restore old IDs gives the new entities the old entity IDs back once the old
  integration is deleted, so references go on working unchanged.
- **Panel, Sender IDs:** the map of the pool uses the full width and labels every row with the
  last byte of its first ID.

### Removed

- **EnOcean Proxy app:** no longer supported, the Device Proxy app is the proxy app. Gone are
  its discovery format with a single gateway and the repair issue for its old versions; texts
  name the Device Proxy only.

### New

- **Device Proxy, fallback gateway:** when the Device Proxy app runs a gateway on its fallback
  (a second gateway with the same base ID), the gateway card shows "Connected through the
  fallback …" in yellow instead of a green "Connected", also in the bar of gateways; the proxy
  line in the details says whether the fallback stands in, is ready or not ready. The gateway's
  Connection sensor gets the attributes `via_fallback`, `fallback` and `fallback_ready` (for
  automations, also without MQTT). Older app versions without a fallback show as before.
- **Panel, Takeover:** Carry over… fills in later what devices already set up still lack;
  values set on the new device stay (websocket `enocean_eltako/takeover/carry`).
- **Gateway settings:** optional gateway prefix in entity IDs: new entities get IDs like
  `light.eno_gw1_kitchen`, with a gateway number of their own per gateway; existing entities
  are renamed on request (automations and dashboards are not adapted). Off by default. The
  gateway shows its prefix in the diagnostic sensor Entity ID prefix.

### Fixed

- **Takeover:** two old buttons on one sender ID (left and right) no longer stop the takeover
  halfway; the second is marked as listed twice. What was added before an error stays, with its
  sender IDs saved and the gateway set up again.
- **Heating actuator:** when the room temperature sensor becomes unavailable, Home Assistant
  stops sending instead of repeating the last temperature, so the actuator falls back to its
  fault mode rather than heating to a frozen value.
- **Covers with a controller:** a full run is sent in whole seconds rounded up, so the driven
  time the actuator reports reaches the full run and renews the position anchor (a travel time
  of 15.3 s sent 17 s instead of 18 s).
- **Covers with controller and direction rocker:** Stop after the actuator has stopped and
  reported its driven time no longer presses the direction rocker again, which started the
  cover moving.
- **Covers:** the higher inaccuracy after an anchor run without an answer shows in the cover's
  state at once and survives a restart.
- **Covers:** the travel time fields of the add dialog point to the travel time assistant
  (Reconfigure → Measure travel times), so default times are not left unmeasured by accident.
- **ESP3 gateways:** a stray sync byte with an implausible packet length no longer holds back
  every telegram behind it (possible after a reconnect in the middle of a packet).
- **ESP3 gateways:** the answer to a radio telegram is no longer taken for the answer to the
  base ID or repeater command: after a reconnect the base ID was sometimes not read and the
  gateway wrongly counted as silent, and a refused repeater setting counted as accepted.
- **Actions:** Import custom devices, Capture telegrams and Add energy devices write files or
  the Energy settings and are now for administrators only.
- **Takeover, restore entity IDs:** an old entity whose new counterpart is of another kind
  (for example sensor and binary sensor) keeps the new ID instead of failing the restore for
  all others.
- **Covers, Calibrate button:** the run stops when the gateway is reloaded or removed, and a
  failure (gateway offline) is logged as a warning instead of an unhandled error.
- **Development:** a release is only created once the checks have passed for that push to
  main, and by hand only from main.
- **Panel:** leaving it right after opening no longer leaves a status poll running every 5 s
  until the browser tab is closed.
- **Device Proxy discovery:** gateway information that cannot be read (no host or port, an
  unknown protocol) ends the discovery with a message instead of an error.
- **Measuring travel times, hidden senders:** when the gateway is reloaded, unloaded or offline
  while the form is open, the flow ends with a hint instead of an error.
- **Heating actuator:** the repair issue that it has not been controlled goes when the device is
  removed or the gateway unloaded.
- **Actuators without a sender ID:** switching them shows that a sender ID is missing instead of
  an unknown error.
- **Device Proxy:** a replay of received telegrams that never ends (above 1 MB or 30 s) is
  skipped, so it no longer holds back the live telegrams for the rest of the connection.
- **Diagnostics:** the network address of a LAN gateway is redacted.

## 0.1.6 - 2026-10-22

### New

- **Panel, teach in:** a device with a sender ID of its own can be taught into its actuator
  from the Devices view (graduation cap), with the steps and a choice of sender ID; it sends what
  the device's teach-in button sends (websocket `enocean_eltako/teach_in`).
- **Panel, weak signal:** a hint above the Devices list counts the senders with a weak signal and
  shows only them on a click; status filter **Weak signal**.
- **Panel, send again:** the details of a sent telegram can send it once more.
- **Development:** a preview page of the panel with sample data (`scripts/panel-preview`) and a
  CI check that renders every view in a simulated browser.

### Fixed

- **Panel in English:** milliseconds stand before AM/PM; the gateway card counts in lower case
  and in the singular for one.

## 0.1.5 - 2026-10-22

### New

- **Sender IDs:** the decimal value of an ID is an attribute (`decimal`) of the EnOcean ID and
  Sender ID diagnostics sensors and an own column in the panel's Sender IDs view. The view
  also shows a pool map (one square per ID, click to jump to its row), the next free ID, and
  device groups can be collapsed.
- **Swap a gateway:** reconfiguring a gateway now also asks for the model, so a defective
  gateway or a FAM-USB can be replaced by another model (for example a network gateway)
  without losing devices or sender IDs. The new gateway has to report the same base ID,
  otherwise the change is refused. Bus gateways (FGW14-USB, FAM14) swap among themselves.

### Changed

- **Panel, Devices:** one line per device with EEP, area and entity count, also for set-up
  devices not heard yet; sortable by column, filterable by status (set up, unknown, silent),
  area, gateway and text, with pages of 25 to 200 rows. The CSV export saves the whole filtered
  list.
- **Device page:** the model of a device lists the EEP it speaks, for example "FSR61
  (M5-38-08)", so the integration page shows it in the device row. Existing devices update on
  the next start; nothing is migrated.
- **Sender IDs:** a radio gateway hands out base ID + 1 ... 127; the base ID itself is no
  longer used (127 IDs per gateway). A device that already sends from the base ID keeps
  working and is reported in the log: give it another sender ID.
- **Panel:** senders hidden from a gateway's discovery are tagged "hidden" and not offered as a
  new device; "x s ago" and last heard use the server's clock; times and numbers follow your
  profile (time format, browser or server time zone, number format); the view is remembered,
  and links like `/enocean-eltako?view=devices&sender=<ID>` open a filtered view; "Open
  device" leads to the device page; success messages disappear after 4 s; sending a rocker
  telegram can press and release; screen readers hear a lost connection and every message.
- **Panel look:** one **Filter** button opens the rarer filters, and the set ones show as chips
  with a cross above the list; the bar of the list stays on top while scrolling and shows the
  gateways' state once their cards are out of view; empty views explain what to do (send a
  telegram, reset the filters, open the integration); a compact pool map with a legend; one
  button style (filled, outlined, text); own-styled lists and checkboxes; quieter column heads.
  On phones the view tabs fit the width and the Takeover steps stand one below the other.

### Fixed

- **Panel:** command and answer are paired by the device, not its name (two devices may share
  a name); the Takeover view goes once nothing is left, without a reload; CSV exports guard
  against spreadsheet formulas.

## 0.1.4 - 2026-10-22

### Changed

- **Discovered devices:** senders a gateway hears but no device listens to are listed under
  **Add device → Discovered devices** of that gateway instead of as cards on the integration
  page and in the "Add hub" list. One notification per gateway announces new ones.
- **Teach-in hints:** the device form names the learn function and the rotary switch
  positions for switching actuators, dimmers and cover actuators (Eltako series 14).
- **Panel:** "Add device" on an unknown sender opens the integration page and highlights its
  gateway.
- **Panel:** the gateway cards stand only above Telegrams and Devices, a single gateway has no
  filter button; the views are tabs (arrow keys); the export button says it saves every
  telegram matching the filter; a theme or primary colour of your own becomes the accent
  colour; the takeover shows three steps (the never usable "Old IDs" step is gone), and
  "Old integration off" opens the old integration's page; durations know days; on phones
  export and clear sit in a ⋮ menu; Devices offers no send and clear, its export is a CSV of
  the sender list.

### New

- **Old integration on the same gateway:** a repair issue names a gateway that the old
  `eltako` integration also uses (same USB port, or same host and port).
- **Sharing device definitions:** the actions `enocean_eltako.export_custom_devices` and
  `enocean_eltako.import_custom_devices` hand definitions over as YAML text; imported ones are
  stored as files in `enocean_eltako/custom_devices/`, your own file is never changed.
- **Energy dashboard:** the action `enocean_eltako.add_energy_devices` adds the electricity
  meters of your devices (with their power sensor) to the Energy dashboard.
- **Hide sender:** senders that are not yours can be hidden (remembered per gateway) and shown
  again under **Configure → Hidden senders**. The list keeps the newest 100 senders.
- **Panel:** Devices lists your devices with no telegram in the monitor, with when they were
  last heard and whether they are silent; the Live badge shows Connecting and No connection;
  the send form gives an example of the right length per telegram type and checks the data
  before sending.

### Fixed

- **Panel:** clearing the display twice no longer brings back the telegrams of the first clear
  after a reconnect; `/` and `P` no longer act in Sender IDs and Takeover; closing the send
  form hides its hint; Devices searches data and values like Telegrams; older browsers without
  `light-dark()` (iOS before 17.5) get the panel's colours; no status requests while the
  browser tab is hidden.

## 0.1.3 - 2026-10-22

### New

- **Device Proxy app:** its EnOcean gateways are discovered like those of the EnOcean Proxy app,
  titled "(Device Proxy)", with replay and the status in the panel. The update issue for old
  EnOcean Proxy versions does not apply to it (it names the version of the contract instead).
- **Moving from the EnOcean Proxy to the Device Proxy:** a gateway set up through one proxy app
  and announced by another is found by its base ID; its entry only gets the new address and
  status port, devices and entities stay

### Fixed

- **Panel on phones:** the view tabs in the header stay on one line and scroll sideways
  instead of wrapping into a second line

## 0.1.2 - 2026-10-21

### Changed

- **Panel:** new look like the Device Proxy app: white header with the views as tabs, rounded
  cards and buttons, its own light and dark colours that follow Home Assistant's theme
- **Documentation:** the teach-in guide lists which virtual sensor each actuator accepts

## 0.1.1 - 2026-10-21

### Changed

- **Panel:**
  - Devices: values in one column, buttons for a sender's telegrams and for adding an unknown
    sender, sorting by name, last heard, weakest signal or most telegrams, more about unknown
    senders (telegram type, teach-in or possible profiles)
  - Sender IDs: grouped by device, blocked IDs first with their note, readable profile names
  - Takeover: after taking devices over the view moves on to checking the old IDs that are still
    in use, the mapping is shorter per device
  - the heading names the view, layouts for phones

## 0.1.0 - 2026-10-21

### New

- **Gateways:** Eltako FGW14-USB, FAM14 and FAM-USB, PioTek MGW-ETH (found through zeroconf), Symcon
  EnOcean LAN Gateway and generic ESP2/ESP3 gateways. Serial ports use
  Home Assistant's port picker, TCP (ser2net, LAN gateways) is supported too. Several gateways
  work side by side, and the FAM14 bus can be used through bus groups with failover.
- **Configuration only through the UI:** one config entry per gateway, one subentry per device.
  Devices are added by learning the ID from a telegram, by category and kind, or by EEP.
  Reconfigure is available for gateways and devices.
- **Devices:** switching and dimming actuators (also channel 2 of two-channel actuators),
  covers with position, vent slots and slat tilt, heating actuators and room controllers
  (with cooling mode), meters (electricity, gas, water, energy dashboard ready), window
  handles, contacts, wall switches, weather and air quality sensors, Permundo PSC plugs and
  all standard EEP profiles as generic devices. [docs/devices.md](docs/devices.md) lists them.
- **Several senders per actuator** (central command, rocker, controller, direction rocker),
  with a sender ID pool: IDs are taken from base ID + 0...127 and stay blocked until the
  teach-out is confirmed.
- **Covers:** position tracking that anchors on end positions, a travel time assistant and
  calibration (also on a schedule through a blueprint).
- **Rocker gestures** (single, double, long press) with device triggers, plus blueprints for
  lights, covers, scenes and calibration.
- **Virtual devices:** Home Assistant sends as a contact (also with priority for lock-out
  protection), temperature, motion and brightness sensor, weather station, scene button or
  rocker with selectable buttons.
- **Telegram monitor panel:** live telegram list with details, filters, sorting, exports,
  signal quality per sender, gateway cards, sender ID table, sending a telegram and adding
  unknown senders as devices.
- **Takeover from the old `eltako` integration** in the panel: preview, selection, area and
  label carry-over and a mapping of old to new entity IDs with their usage.
- **Gateway care:** last-seen monitoring, state reconciliation at startup, repairs for an
  unstable or silent connection, diagnostic sensors and diagnostics download.
- **EnOcean Proxy** gateways are set up through Supervisor discovery.
- Translations in German and English, brand images, German and English READMEs and a user
  guide.

### Notes

- The protocol layer (ESP2/ESP3, EEPs, FAM14 bus) is implemented in this repository without
  EnOcean or Eltako libraries.
- The official EnOcean Alliance files are not part of the repository (see [NOTICE](NOTICE)).
