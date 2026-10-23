# Changelog

All notable changes to this project are documented here, in English and German
(Deutsche Fassung weiter unten: [Deutsch](#deutsch)). The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## English

### [Unreleased]

#### Added

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

#### Changed

- **Weather station:** dawn and the three sun sensors show whole lux (dawn no longer "999,0 lx"), the wind one decimal.
  Rain is a plain on/off sensor shown as "Rain" / "No rain" with the rain icons, no longer a "moisture" (leak) sensor
  that assistants might treat as a leak alarm. The wind's unit (m/s, km/h, Beaufort) is the entity's display unit
  setting in Home Assistant.
- **Device page:** a device without a named type lists its EEP once, as the model, not again as the model ID.
- **Panel, Devices view:** the boxes have a column of their own, so name and ID line up, and "Select all" sits in the
  table head above them (on phones it stays in the line above the list). The bar of the ticked devices takes the place
  of the count line, the row icons are subdued until the pointer is over the row, and "not heard" is muted.

### [0.1.12] - 2026-10-23

#### Added

- **Panel, Devices view:** select several devices (a box per row, "Select all" for the filtered ones) and, with a bar,
  set an **area**, add or remove **labels** (new labels can be created in place), **disable** or **enable** them, or
  **remove** them from Home Assistant in one go. Area, labels and disabling are Home Assistant's own, so they show on
  the device page too. Removing asks first, reloads the gateway once and leaves the devices' sender IDs blocked until
  the teach-out is confirmed under Sender IDs.
- **Panel:** a device's labels show under its name, a disabled device is tagged, and the search finds labels.

### [0.1.11] - 2026-10-23

#### Added

- **Cover automation mode:** every cover has a select "Automation mode" (Off, Morning, Evening, Both; Both until chosen
  otherwise) for your own automations, like the old Eltako integration's. It moves nothing by itself and is kept across
  restarts.
- **Cover state and driven time:** FSB covers have a "State" sensor (opening, closing, open, closed, stopped) and a
  "Driven time" sensor (with the direction) from the actuator's confirmation telegrams.
- **Panel:** an Integration link in the header bar and in the gateway details, straight to that gateway's entry.

#### Changed

- **Cover routing:** a cover moves through one sender, the controller or the direction rocker. "Both" is gone: it sent two
  telegrams per run, and the direction rocker stops a run on the same direction again. Existing covers with "Both" keep
  the controller (the direction rocker where they have no controller).
- **Takeover:** a rocker (F6-02-01, F6-02-02) of the old binary_sensor platform becomes a rocker contact with its device
  class and inverted flag, not a button. The takeover stays on the selection when nothing is left to switch over and
  says so in step 3.

#### Fixed

- **Rocker and wall switch buttons:** the collapsed sections show the button in use (or the default) preselected instead
  of no choice at all.
- **Device page:** the EEP is listed once, as model ID, not also in the model.

### [0.1.10] - 2026-10-23

#### Changed

- **Links to the device in the panel:** an opened telegram has a "Device in panel" button, and the device name of a sender ID
  group is a link: both open the device's row in the Devices view. "Open device" is now "Open in Home Assistant".
- **Panel look:** logo and view tabs line up with the content (at most 1200 px, centred) instead of the window's
  edges, like in the Device Proxy app.
- **Sender IDs:** the top of the view is clearer: tiles for free, assigned and blocked IDs and the next
  free ID (with a copy button), one bar for the share used, a note when blocked IDs wait for their teach-out
  (with a button to the first one), a pool map whose rows name their ID range, and a line under the map that
  tells ID, number, state and device of the chosen square. The legend shows the numbers.

### [0.1.9] - 2026-10-23

#### Added

- **Device model:** a device of a kind that several Eltako models share (switching actuators,
  dimmers, shutter actuators, heating actuators, meters ...) has an optional "Model" field: pick
  FSR14-4x, FUD61NPN-230V ... or type another one. It is shown in the telegram monitor and on the
  device page and changes no behaviour. New device data version (schema 4, migration included).

#### Changed

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

### [0.1.8] - 2026-10-22

#### Changed

- **Device Proxy:** the gateway card and the gateway's connection sensor show whether the app's
  fallback gateway stands in and whether it is ready.

#### Fixed

- **Panel:** the EnOcean panel no longer stays blank when one of its files fails to load once
  (during a Home Assistant start or a proxy hiccup): the parts load with retries, and if they
  still fail the panel shows a message with a Reload button.

### [0.1.7] - 2026-10-22

#### Changed

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

#### Removed

- **EnOcean Proxy app:** no longer supported, the Device Proxy app is the proxy app. Gone are
  its discovery format with a single gateway and the repair issue for its old versions; texts
  name the Device Proxy only.

#### Added

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

#### Fixed

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

### [0.1.6] - 2026-10-22

#### Added

- **Panel, teach in:** a device with a sender ID of its own can be taught into its actuator
  from the Devices view (graduation cap), with the steps and a choice of sender ID; it sends what
  the device's teach-in button sends (websocket `enocean_eltako/teach_in`).
- **Panel, weak signal:** a hint above the Devices list counts the senders with a weak signal and
  shows only them on a click; status filter **Weak signal**.
- **Panel, send again:** the details of a sent telegram can send it once more.
- **Development:** a preview page of the panel with sample data (`scripts/panel-preview`) and a
  CI check that renders every view in a simulated browser.

#### Fixed

- **Panel in English:** milliseconds stand before AM/PM; the gateway card counts in lower case
  and in the singular for one.

### [0.1.5] - 2026-10-22

#### Added

- **Sender IDs:** the decimal value of an ID is an attribute (`decimal`) of the EnOcean ID and
  Sender ID diagnostics sensors and an own column in the panel's Sender IDs view. The view
  also shows a pool map (one square per ID, click to jump to its row), the next free ID, and
  device groups can be collapsed.
- **Swap a gateway:** reconfiguring a gateway now also asks for the model, so a defective
  gateway or a FAM-USB can be replaced by another model (for example a network gateway)
  without losing devices or sender IDs. The new gateway has to report the same base ID,
  otherwise the change is refused. Bus gateways (FGW14-USB, FAM14) swap among themselves.

#### Changed

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

#### Fixed

- **Panel:** command and answer are paired by the device, not its name (two devices may share
  a name); the Takeover view goes once nothing is left, without a reload; CSV exports guard
  against spreadsheet formulas.

### [0.1.4] - 2026-10-22

#### Changed

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

#### Added

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

#### Fixed

- **Panel:** clearing the display twice no longer brings back the telegrams of the first clear
  after a reconnect; `/` and `P` no longer act in Sender IDs and Takeover; closing the send
  form hides its hint; Devices searches data and values like Telegrams; older browsers without
  `light-dark()` (iOS before 17.5) get the panel's colours; no status requests while the
  browser tab is hidden.

### [0.1.3] - 2026-10-22

#### Added

- **Device Proxy app:** its EnOcean gateways are discovered like those of the EnOcean Proxy app,
  titled "(Device Proxy)", with replay and the status in the panel. The update issue for old
  EnOcean Proxy versions does not apply to it (it names the version of the contract instead).
- **Moving from the EnOcean Proxy to the Device Proxy:** a gateway set up through one proxy app
  and announced by another is found by its base ID; its entry only gets the new address and
  status port, devices and entities stay

#### Fixed

- **Panel on phones:** the view tabs in the header stay on one line and scroll sideways
  instead of wrapping into a second line

### [0.1.2] - 2026-10-21

#### Changed

- **Panel:** new look like the Device Proxy app: white header with the views as tabs, rounded
  cards and buttons, its own light and dark colours that follow Home Assistant's theme
- **Documentation:** the teach-in guide lists which virtual sensor each actuator accepts

### [0.1.1] - 2026-10-21

#### Changed

- **Panel:**
  - Devices: values in one column, buttons for a sender's telegrams and for adding an unknown
    sender, sorting by name, last heard, weakest signal or most telegrams, more about unknown
    senders (telegram type, teach-in or possible profiles)
  - Sender IDs: grouped by device, blocked IDs first with their note, readable profile names
  - Takeover: after taking devices over the view moves on to checking the old IDs that are still
    in use, the mapping is shorter per device
  - the heading names the view, layouts for phones

### [0.1.0] - 2026-10-21

First version of the integration.

#### Added

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

#### Notes

- The protocol layer (ESP2/ESP3, EEPs, FAM14 bus) is implemented in this repository without
  EnOcean or Eltako libraries.
- The official EnOcean Alliance files are not part of the repository (see [NOTICE](NOTICE)).

## Deutsch

Das Format folgt [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).

### [Unreleased]

#### Hinzugefügt

- **Wetterstation:** ein Sensor „Sonnigste Seite“ (Süd, Ost, West oder keine Sonne unter 2 klx auf allen Seiten) und ein
  Sensor „Regen kürzlich“, der nach dem Regen noch einige Minuten an bleibt, damit Rollläden und Markisen nicht auf eine
  nasse Fläche zurückfahren. Die Minuten sind eine Geräteeinstellung (Vorgabe 15, 0 = kein Nachlauf).
- **Blueprint „Rollläden nach der Sonne beschatten“:** fährt Rollläden in eine Beschattungsposition, wenn die Sonne auf einer
  Seite stark genug bleibt, und zurück, wenn sie eine Weile schwach war; auf Wunsch nur bei Wärme; lässt Rollläden in Ruhe,
  deren „Automatikmodus“ Aus ist, und solche, die du von Hand bewegt hast.
- **Blueprint „Rollläden und Licht bei Dämmerung“:** schließt Rollläden und schaltet Licht ein, wenn es eine Weile dunkel
  ist, öffnet und schaltet morgens aus; der „Automatikmodus“ eines Rollladens entscheidet (Abends und Beides am Abend,
  Morgens und Beides am Morgen, Aus nie), mit frühesten Zeiten, damit eine Gewitterwolke am Mittag nichts schließt.
- **Blueprint „Wetterwarnung bei offenem Fenster“:** eine Meldung (eine Aktion deiner Wahl), wenn es zu regnen beginnt oder
  weht, während ein Fenster offen ist, und wenn ein Fenster bei schlechtem Wetter geöffnet wird. Es bewegt nichts.

#### Geändert

- **Wetterstation:** Dämmerung und die drei Sonnensensoren zeigen ganze Lux (die Dämmerung nicht mehr „999,0 lx“), der
  Wind eine Nachkommastelle. Regen ist ein einfacher Ein/Aus-Sensor mit den Anzeigen „Regen“ / „Kein Regen“ und den
  Regen-Symbolen, kein „Feuchtigkeits“-Sensor (Leck) mehr, den Assistenten als Leckalarm behandeln könnten. Die Einheit
  des Winds (m/s, km/h, Beaufort) ist die Anzeigeeinheit der Entität in Home Assistant.
- **Geräteseite:** ein Gerät ohne benannten Typ nennt sein EEP einmal, als Modell, nicht noch einmal als Modell-ID.
- **Panel, Ansicht Geräte:** die Kästchen haben eine eigene Spalte, so fluchten Name und ID, und „Alle auswählen“ steht
  im Tabellenkopf darüber (auf dem Handy bleibt es in der Zeile über der Liste). Die Leiste der gewählten Geräte
  ersetzt die Zeile mit der Anzahl, die Symbole der Zeilen sind gedämpft, bis der Zeiger über der Zeile steht, und
  „nicht gehört“ ist abgeschwächt.

### [0.1.12] - 2026-10-23

#### Hinzugefügt

- **Panel, Ansicht Geräte:** mehrere Geräte auswählen (ein Kästchen je Zeile, „Alle auswählen“ für die gefilterten) und
  mit einer Leiste einen **Bereich** setzen, **Labels** hinzufügen oder entfernen (neue Labels lassen sich gleich
  anlegen), sie **deaktivieren** oder **aktivieren** oder in einem Zug aus Home Assistant **entfernen**. Bereich, Labels
  und Deaktivieren sind die von Home Assistant, sie erscheinen also auch auf der Geräteseite. Das Entfernen fragt vorher
  nach, lädt das Gateway nur einmal neu und lässt die Sender-IDs der Geräte gesperrt, bis das Abmelden unter Sender-IDs
  bestätigt ist.
- **Panel:** die Labels eines Geräts stehen unter seinem Namen, ein deaktiviertes Gerät trägt eine Markierung, und die
  Suche findet Labels.

### [0.1.11] - 2026-10-23

#### Hinzugefügt

- **Automatikmodus der Cover:** Jedes Cover hat eine Auswahl „Automatikmodus" (Aus, Morgens, Abends, Beides; bis zur Wahl
  Beides) für deine eigenen Automationen, wie in der alten Eltako-Integration. Sie fährt nichts selbst und bleibt über
  Neustarts erhalten.
- **Zustand und Fahrzeit der Cover:** FSB-Cover haben einen Sensor „Zustand" (fährt auf, fährt zu, offen, geschlossen,
  gestoppt) und einen Sensor „Fahrzeit" (mit der Richtung) aus den Bestätigungstelegrammen des Aktors.
- **Panel:** ein Integrations-Link in der Kopfleiste und in den Gateway-Details, direkt zum Eintrag dieses Gateways.

#### Geändert

- **Routing der Cover:** Ein Cover fährt über einen Sender, den Controller oder den Richtungstaster. „Beide" entfällt:
  Es sendete zwei Telegramme je Fahrt, und der Richtungstaster stoppt eine Fahrt bei erneutem Druck in dieselbe Richtung.
  Bestehende Cover mit „Beide" behalten den Controller (den Richtungstaster, wo sie keinen Controller haben).
- **Übernahme:** Ein Taster (F6-02-01, F6-02-02) der alten Plattform binary_sensor wird ein Taster-Kontakt mit seiner
  Geräteklasse und dem Invertieren, kein Knopf. Die Übernahme bleibt bei der Auswahl, wenn nichts mehr umzustellen ist,
  und sagt das in Schritt 3.

#### Behoben

- **Tasten von Taster und Wandtaster:** Die eingeklappten Bereiche zeigen die genutzte Taste (oder den Standard)
  vorausgewählt, statt gar keine Auswahl.
- **Geräteseite:** Die EEP steht einmal, als Modell-ID, nicht zusätzlich im Modell.

### [0.1.10] - 2026-10-23

#### Geändert

- **Links zum Gerät im Panel:** Ein aufgeklapptes Telegramm hat den Knopf „Gerät im Panel", und der Gerätename einer
  Sender-ID-Gruppe ist ein Link: beide öffnen die Zeile des Geräts in der Geräteansicht. „Gerät öffnen" heißt jetzt
  „In Home Assistant öffnen".
- **Aussehen des Panels:** Logo und Reiter richten sich am Inhalt aus (höchstens 1200 px, zentriert) statt an den
  Fensterrändern, wie in der Device-Proxy-App.
- **Sender-IDs:** Der Kopf der Ansicht ist klarer: Kacheln für freie, zugewiesene und gesperrte IDs und die nächste
  freie ID (mit Kopieren-Knopf), ein Balken für den belegten Anteil, ein Hinweis, wenn gesperrte IDs auf ihr
  Teach-out warten (mit Knopf zur ersten), eine Pool-Karte, deren Zeilen ihren ID-Bereich nennen, und eine Zeile
  unter der Karte mit ID, Nummer, Status und Gerät des gewählten Felds. Die Legende zeigt die Zahlen.

### [0.1.9] - 2026-10-23

#### Hinzugefügt

- **Gerätemodell:** Ein Gerät einer Art, die mehrere Eltako-Modelle teilen (Schaltaktoren,
  Dimmer, Rollladenaktoren, Heizungsaktoren, Zähler ...), hat ein optionales Feld „Modell": FSR14-4x,
  FUD61NPN-230V ... wählen oder ein anderes eintippen. Es erscheint im Telegramm-Monitor und auf
  der Geräteseite und ändert kein Verhalten. Neue Version der Gerätedaten (Schema 4, Migration
  inklusive).

#### Geändert

- **Telegramm-Monitor:** Das Funktelegramm verrät das Modell nicht, deshalb zeigt der Monitor nicht
  mehr das erste Beispiel der Art (FSR61 bei einem FSR14). Ohne gewähltes Modell steht dort die
  Liste der möglichen Modelle, die Geräteseite zeigt nur das EEP.
- **Wetterstation:** Das Beispiel FWG14 heißt FWG14MS.
- **Geräteansicht:** Die Zeile eines eingerichteten Geräts klappt an Ort und Stelle auf und zeigt alles,
  was wir kennen: Identität (Modell, EEP, Bereich, Gateway, ID), Funk (zuletzt gehört, Signal mit
  Minimum und Maximum, Repeater-Stufen, Telegrammzahl, erwartetes Intervall), letzte Werte,
  Sender-IDs mit Art des Einlernens, Befehlsstatistik (gesendet, bestätigt, Antwortzeit),
  Einstellungen und Entitäten mit ihren Zuständen. Mehrere Zeilen können offen sein, sie bleiben
  aktuell, und die Liste behält ihre Reihenfolge, solange eine offen ist. Ein Klick auf die Zeile
  springt nicht mehr zu den Telegrammen: Das macht der Filter-Knopf der Zeile.
- **Geräteansicht:** Das Modell eines Geräts wird in seiner aufgeklappten Zeile gesetzt: Dropdown mit den
  Modellen seiner Art, „Nicht angegeben" oder „Anderes Modell …" zum Eintippen. Es wird sofort
  gespeichert (der Eintrag des Gateways lädt neu, wie nach jeder Änderung an einem Gerät).
- **Geräteansicht:** Die aufgeklappte Zeile zeigt ihre Werte als kleine Kacheln und Tabellen auf Weiß, wie die
  Statistiken der Device-Proxy-App; der Anteil bestätigter Befehle ist ein farbiger Chip.
- **Aussehen des Panels:** Das Panel sieht aus wie die Device-Proxy-App: deren Seitenfarbe, größere
  abgerundete Karten mit weichem Schatten und Reiter als Pillen. Die Akzentfarbe ist immer das Blau
  der App und folgt nicht mehr der Primärfarbe eines Home-Assistant-Themes (hell und dunkel folgen
  ihm weiterhin).
- **Geräteansicht:** Die Liste öffnet immer nach Namen sortiert; eine angeklickte Spaltensortierung
  gilt, bis das Panel geschlossen wird, und wird nicht mehr gemerkt.
- **Telegramm-Monitor:** Ein aufgeklapptes Telegramm hält die Liste an: neue Telegramme warten (die
  Live-Anzeige zeigt „Pausiert" mit ihrer Anzahl), solange du die Details liest, und erscheinen,
  wenn du das letzte geöffnete zuklappst. Eine selbst gesetzte Pause bleibt, bis du sie aufhebst.

### [0.1.8] - 2026-10-22

#### Geändert

- **Device Proxy:** die Gateway-Karte und der Verbindungssensor des Gateways zeigen, ob das
  Ausweich-Gateway der App einspringt und ob es bereit ist.

#### Behoben

- **Panel:** das EnOcean-Panel bleibt nicht mehr leer, wenn eine seiner Dateien einmal nicht
  lädt (beim Start von Home Assistant oder bei einem Proxy-Aussetzer): die Teile laden mit
  Wiederholungen, und scheitern sie dennoch, zeigt das Panel eine Meldung mit Neu-laden-Knopf.

### [0.1.7] - 2026-10-22

#### Geändert

- **Panel, Übernahme:** was aus der alten Integration mitkommt, wird einzeln gewählt (Bereich,
  Labels, Sprachsteuerung, eigene Namen, Symbole, ausgeblendet / deaktiviert), mit der Zahl der
  betroffenen Geräte; anfangs ist nichts gewählt, die Wahl merkt sich der Browser. Eigene Namen,
  Symbole und ausgeblendet / deaktiviert sind neu.
- **Panel, Übernahme:** schon eingerichtete Geräte sind in Übernehmen keine Liste mehr, sondern
  ein Hinweis, der zu Prüfen führt; Prüfen ist die Übersicht aller eingerichteten Geräte: was
  ihnen aus der alten Integration noch fehlt, die Fundstellen ihrer alten IDs, eine Ansicht nach
  Fundstelle mit Links in die Editoren, Filter Noch verwendet und Erledigt, und Neu prüfen.
- **Panel, Übernahme:** Übernehmen fragt zuerst nach: eine Bestätigung zeigt Geräte, Entitäten
  und die danach umzustellenden Fundstellen, die gewählten Optionen und jede alte Entity-ID neben
  der, die die neue Entität voraussichtlich bekommt; erst Jetzt übernehmen legt die Geräte an.
- **Panel, Übernahme:** vier Schritte, Auswählen, Mitnehmen (die Optionen als Kacheln mit ihren
  Werten, dazu die Vorschau alter und neuer IDs), Umstellen (nach Fundstelle, nach Gerät mit dem,
  was jedes Gerät in der alten Integration war, und der Bericht als Tabelle) und Aufräumen (eine
  Checkliste aus dem aktuellen Stand); Übernahme abschließen blendet den Tab aus.
- **Übernahme:** die Zuordnung alter zu neuen Entity-IDs speichert die Integration selbst, der
  Bericht bleibt deshalb nach dem Löschen der alten Integration abrufbar; Übernahme-Bericht in
  der Ansicht Geräte öffnet ihn.
- **Übernahme:** Alte IDs wiederherstellen gibt den neuen Entitäten die alten Entity-IDs zurück,
  sobald die alte Integration gelöscht ist; Verweise laufen dann unverändert weiter.
- **Panel, Sender-IDs:** die Karte des Pools nutzt die volle Breite und beschriftet jede Reihe
  mit dem letzten Byte ihrer ersten ID.

#### Entfernt

- **App EnOcean Proxy:** nicht mehr unterstützt, die Proxy-App ist der Device Proxy. Entfallen
  sind ihr Discovery-Format mit nur einem Gateway und der Reparaturhinweis für ihre alten
  Versionen; die Texte nennen nur noch den Device Proxy.

#### Hinzugefügt

- **Device Proxy, Ersatz-Gateway:** Läuft ein Gateway in der App Device Proxy über seinen
  Ersatz (ein zweites Gateway mit derselben Base-ID), zeigt die Gateway-Karte gelb „Verbunden
  über Ersatz …“ statt grün „Verbunden“, auch in der Leiste der Gateways; die Proxy-Zeile in den
  Details sagt, ob der Ersatz einspringt, bereit oder nicht einsatzbereit ist. Der Sensor
  Verbindung des Gateways bekommt die Attribute `via_fallback`, `fallback` und `fallback_ready`
  (für Automationen, auch ohne MQTT). Ältere Versionen der App ohne Ersatz zeigen sich wie
  bisher.
- **Panel, Übernahme:** Nachträglich übernehmen… ergänzt, was schon eingerichteten Geräten
  noch fehlt; am neuen Gerät gesetzte Werte bleiben (Websocket `enocean_eltako/takeover/carry`).
- **Gateway-Einstellungen:** optionaler Gateway-Präfix in Entitäts-IDs: neue Entitäten bekommen
  IDs wie `light.eno_gw1_kuche`, mit einer eigenen Gateway-Nummer je Gateway; bestehende
  Entitäten werden auf Wunsch umbenannt (Automationen und Dashboards werden nicht angepasst).
  Standardmäßig aus. Das Gateway zeigt seinen Präfix im Diagnose-Sensor Entitäts-ID-Präfix.

#### Behoben

- **Übernahme:** zwei alte Taster auf derselben Sender-ID (links und rechts) brechen die
  Übernahme nicht mehr mittendrin ab; der zweite gilt als doppelt. Was vor einem Fehler angelegt
  wurde, bleibt, mit gespeicherten Sender-IDs und neu eingerichtetem Gateway.
- **Heizungsaktor:** ist der Raumtemperaturfühler nicht verfügbar, sendet Home Assistant nichts
  mehr, statt die letzte Temperatur zu wiederholen; der Aktor geht so in seinen Störbetrieb,
  statt auf einen eingefrorenen Wert zu heizen.
- **Rollläden mit Controller:** eine Vollfahrt wird in ganzen, aufgerundeten Sekunden gesendet,
  damit die gemeldete Fahrzeit die Vollfahrt erreicht und den Positionsanker erneuert (bei 15,3 s
  Fahrzeit wurden 17 statt 18 s gesendet).
- **Rollläden mit Controller und Richtungstaster:** Stopp, nachdem der Aktor angehalten und seine
  Fahrzeit gemeldet hat, drückt den Richtungstaster nicht mehr erneut, was den Rollladen wieder
  losfahren ließ.
- **Rollläden:** die höhere Ungenauigkeit nach einer Ankerfahrt ohne Antwort steht sofort im
  Zustand des Rollladens und übersteht einen Neustart.
- **Rollläden:** die Laufzeitfelder im Dialog zum Anlegen verweisen auf den Laufzeit-Assistenten
  (Neu konfigurieren → Laufzeiten messen), damit Standardzeiten nicht versehentlich ungemessen
  bleiben.
- **ESP3-Gateways:** ein verirrtes Sync-Byte mit unplausibler Paketlänge hält nicht mehr alle
  folgenden Telegramme zurück (möglich nach einem Reconnect mitten in einem Paket).
- **ESP3-Gateways:** die Antwort auf ein Funktelegramm gilt nicht mehr als Antwort auf den
  Base-ID- oder Repeater-Befehl: nach einem Reconnect wurde die Base-ID manchmal nicht gelesen
  und das Gateway fälschlich als stumm gewertet, und eine abgelehnte Repeater-Einstellung galt als
  übernommen.
- **Aktionen:** Eigene Geräte importieren, Telegramme aufzeichnen und Energie-Geräte hinzufügen
  schreiben Dateien oder die Energie-Einstellungen und sind jetzt nur noch für Administratoren.
- **Übernahme, Entitäts-IDs wiederherstellen:** eine alte Entität, deren neue Entsprechung
  eine andere Art ist (etwa Sensor und Binärsensor), behält die neue ID, statt das
  Wiederherstellen für alle anderen scheitern zu lassen.
- **Rollläden, Schaltfläche Kalibrieren:** die Fahrt endet, wenn das Gateway neu geladen oder
  entfernt wird, und ein Fehler (Gateway offline) steht als Warnung im Log statt als unbehandelter
  Fehler.
- **Entwicklung:** ein Release entsteht erst, wenn die Prüfungen für den Push auf main
  bestanden sind, und von Hand nur von main aus.
- **Panel:** wird es direkt nach dem Öffnen verlassen, läuft nicht mehr bis zum Schließen des
  Browser-Tabs alle 5 s eine Statusabfrage weiter.
- **Device-Proxy-Erkennung:** nicht lesbare Gateway-Angaben (ohne Host oder Port, unbekanntes
  Protokoll) beenden die Erkennung mit einem Hinweis statt mit einem Fehler.
- **Fahrzeiten messen, ausgeblendete Sender:** wird das Gateway neu geladen, entladen oder ist
  es offline, während das Formular offen ist, endet der Ablauf mit einem Hinweis statt mit einem
  Fehler.
- **Heizungsaktor:** der Reparaturhinweis, dass er nicht mehr geregelt wird, verschwindet, wenn das
  Gerät entfernt oder das Gateway entladen wird.
- **Aktoren ohne Sender-ID:** beim Schalten erscheint, dass die Sender-ID fehlt, statt eines
  unbekannten Fehlers.
- **Device Proxy:** eine Wiedergabe empfangener Telegramme, die nicht endet (über 1 MB oder
  30 s), wird übersprungen und hält die Live-Telegramme nicht mehr für den Rest der Verbindung
  zurück.
- **Diagnose:** die Netzwerkadresse eines LAN-Gateways wird geschwärzt.

### [0.1.6] - 2026-10-22

#### Hinzugefügt

- **Panel, Einlernen:** ein Gerät mit eigener Sender-ID lässt sich in der Ansicht Geräte
  (Doktorhut) in seinen Aktor einlernen, mit Anleitung und Wahl der Sender-ID; gesendet wird
  dasselbe wie mit der Einlern-Schaltfläche des Geräts (Websocket `enocean_eltako/teach_in`).
- **Panel, schwaches Signal:** ein Hinweis über der Geräteliste zählt die Sender mit schwachem
  Signal und zeigt per Klick nur sie; Status-Filter **Schwaches Signal**.
- **Panel, nochmal senden:** die Details eines gesendeten Telegramms senden es erneut.
- **Entwicklung:** eine Vorschauseite des Panels mit Beispieldaten (`scripts/panel-preview`) und
  eine CI-Prüfung, die jede Ansicht in einem simulierten Browser zeichnet.

#### Behoben

- **Panel auf Englisch:** Millisekunden stehen vor AM/PM; die Zahlen der Gateway-Karte klein
  geschrieben und bei eins im Singular.

### [0.1.5] - 2026-10-22

#### Hinzugefügt

- **Sender-IDs:** Der Dezimalwert einer ID ist ein Attribut (`decimal`) der Diagnose-Sensoren
  EnOcean-ID und Sender-ID und eine eigene Spalte in der Ansicht Sender-IDs des Panels. Die
  Ansicht zeigt außerdem eine Pool-Karte (ein Feld pro ID, Klick springt zur Zeile) und die
  nächste freie ID; Gerätegruppen lassen sich einklappen.
- **Gateway tauschen:** Beim Neukonfigurieren eines Gateways wird jetzt auch das Modell
  abgefragt. So lässt sich ein defektes Gateway oder ein FAM-USB durch ein anderes Modell
  (z. B. ein Netzwerk-Gateway) ersetzen, ohne Geräte und Sender-IDs zu verlieren. Das neue
  Gateway muss dieselbe Base-ID melden, sonst wird der Wechsel abgelehnt. Bus-Gateways
  (FGW14-USB, FAM14) tauschen nur untereinander.

#### Geändert

- **Panel, Geräte:** Eine Zeile je Gerät mit EEP, Bereich und Entitätenzahl, auch für
  eingerichtete, noch nicht gehörte Geräte; nach Spalten sortierbar, filterbar nach Status
  (eingerichtet, unbekannt, still), Bereich, Gateway und Text, mit Seiten zu 25 bis 200 Zeilen.
  Der CSV-Export speichert die ganze gefilterte Liste.
- **Geräteseite:** Das Modell eines Geräts nennt das EEP, mit dem es funkt, zum Beispiel
  „FSR61 (M5-38-08)“, sodass die Integrationsseite es in der Geräte-Zeile zeigt. Bestehende
  Geräte ziehen beim nächsten Start nach; es wird nichts migriert.
- **Sender-IDs:** Ein Funk-Gateway vergibt Base-ID + 1 ... 127; die Base-ID selbst wird nicht
  mehr verwendet (127 IDs pro Gateway). Ein Gerät, das schon von der Base-ID sendet, läuft
  weiter und wird im Log gemeldet: ihm eine andere Sender-ID geben.
- **Panel:** In der Discovery eines Gateways ausgeblendete Sender sind als „ausgeblendet“
  markiert und werden nicht als neues Gerät angeboten; „vor x s“ und der letzte Empfang rechnen
  mit der Serveruhr; Zeiten und Zahlen folgen deinem Profil (Zeitformat, Zeitzone von Browser
  oder Server, Zahlenformat); die Ansicht wird gemerkt, und Links wie
  `/enocean-eltako?view=devices&sender=<ID>` öffnen eine gefilterte Ansicht; „Gerät öffnen“
  führt zur Geräteseite; Erfolgsmeldungen verschwinden nach 4 s; ein Taster-Telegramm lässt
  sich drücken und loslassen; Screenreader hören einen Verbindungsverlust und jede Meldung.
- **Panel-Optik:** ein Knopf **Filter** öffnet die selteneren Filter, gesetzte Filter stehen als
  Chips mit Kreuz über der Liste; die Leiste der Liste bleibt beim Scrollen oben und zeigt den
  Zustand der Gateways, sobald deren Karten aus dem Bild sind; leere Ansichten sagen, was zu tun
  ist (Telegramm senden, Filter zurücksetzen, Integration öffnen); eine kompakte Pool-Karte mit
  Legende; ein Knopfstil (gefüllt, umrandet, Text); eigene Auswahllisten und Checkboxen;
  ruhigere Spaltenköpfe. Auf dem Handy passen die Reiter in die Breite, und die Schritte der
  Übernahme stehen untereinander.

#### Behoben

- **Panel:** Befehl und Antwort werden über das Gerät gepaart, nicht über seinen Namen (zwei
  Geräte können gleich heißen); die Ansicht Übernahme verschwindet ohne Neuladen, sobald nichts
  mehr übrig ist; CSV-Exporte sind gegen Tabellenformeln abgesichert.

### [0.1.4] - 2026-10-22

#### Geändert

- **Entdeckte Geräte:** Sender, die ein Gateway hört und auf die kein Gerät hört, stehen beim
  Gateway unter **Gerät hinzufügen → Entdeckte Geräte** statt als Karten auf der Integrationsseite
  und in der Liste bei „Hub hinzufügen“. Eine Benachrichtigung pro Gateway meldet neue.
- **Anlernhinweise:** das Geräteformular nennt für Schaltaktoren, Dimmer und Rollladenaktoren
  (Eltako Baureihe 14) die Lernfunktion und die Drehschalterstellungen.
- **Panel:** „Gerät hinzufügen“ bei einem unbekannten Sender öffnet die Integrationsseite und
  hebt sein Gateway hervor.
- **Panel:** die Gateway-Karten stehen nur über Telegramme und Geräte, ein einzelnes Gateway hat
  keinen Filterknopf; die Ansichten sind Tabs (Pfeiltasten); der Export-Knopf sagt, dass er alle
  Telegramme zum Filter speichert; ein eigenes Design oder eine eigene Hauptfarbe wird zur
  Akzentfarbe; die Übernahme zeigt drei Schritte (der nie nutzbare Schritt „Alte IDs“ ist weg),
  und „Alte Integration aus“ öffnet die Seite der alten Integration; Zeitangaben kennen Tage;
  auf dem Handy stehen Exportieren und Leeren in einem ⋮-Menü; Geräte bietet kein Senden und
  Leeren, sein Export ist eine CSV der Senderliste.

#### Neu

- **Alte Integration am selben Gateway:** ein Reparaturhinweis nennt ein Gateway, das auch die
  alte Integration `eltako` nutzt (derselbe USB-Port oder derselbe Host mit Port).
- **Gerätedefinitionen weitergeben:** die Aktionen `enocean_eltako.export_custom_devices` und
  `enocean_eltako.import_custom_devices` übergeben Definitionen als YAML-Text; importierte liegen
  als Dateien in `enocean_eltako/custom_devices/`, deine eigene Datei bleibt unverändert.
- **Energie-Dashboard:** die Aktion `enocean_eltako.add_energy_devices` fügt die Stromzähler
  deiner Geräte (mit ihrem Leistungssensor) zum Energie-Dashboard hinzu.
- **Sender ausblenden:** fremde Sender lassen sich ausblenden (pro Gateway gemerkt) und unter
  **Konfigurieren → Ausgeblendete Sender** wieder anzeigen. Die Liste behält die neuesten 100
  Sender.
- **Panel:** Geräte listet deine Geräte ohne Telegramm im Monitor, mit dem letzten Empfang und
  ob sie still sind; das Live-Kennzeichen zeigt Verbinde… und Keine Verbindung; das
  Sendeformular zeigt ein Beispiel in der richtigen Länge je Telegrammtyp und prüft die Daten vor
  dem Senden.

#### Behoben

- **Panel:** zweimal Anzeige leeren holt nach einem Reconnect die Telegramme des ersten Leerens
  nicht mehr zurück; `/` und `P` wirken nicht mehr in Sender-IDs und Übernahme; Schließen des
  Sendeformulars blendet seinen Hinweis aus; Geräte durchsucht Daten und Werte wie Telegramme;
  ältere Browser ohne `light-dark()` (iOS vor 17.5) bekommen die Farben des Panels; keine
  Statusabfragen, solange der Browser-Tab verborgen ist.

### [0.1.3] - 2026-10-22

#### Neu

- **App Device Proxy:** ihre EnOcean-Gateways werden wie die der App EnOcean Proxy gefunden,
  mit dem Titel „(Device Proxy)“, Nachlieferung und Status im Panel. Der Hinweis auf eine zu
  alte EnOcean-Proxy-Version gilt für sie nicht (sie nennt stattdessen die Version der
  Schnittstelle).
- **Umstieg vom EnOcean Proxy zum Device Proxy:** Ein Gateway, das über die eine Proxy-App
  eingerichtet wurde und von der anderen gemeldet wird, wird über seine Base-ID erkannt; der
  Eintrag bekommt nur die neue Adresse und den Status-Port, Geräte und Entitäten bleiben

#### Behoben

- **Panel auf dem Handy:** Die Ansichts-Reiter in der Kopfzeile bleiben in einer Zeile und
  lassen sich seitlich wischen, statt in eine zweite Zeile umzubrechen

### [0.1.2] - 2026-10-21

#### Geändert

- **Panel:** neues Aussehen wie die Device-Proxy-App: weiße Kopfzeile mit den Ansichten als
  Reiter, runde Karten und Knöpfe, eigene helle und dunkle Farben, die dem Theme von Home
  Assistant folgen
- **Dokumentation:** die Anlernanleitung nennt, welchen virtuellen Sensor jeder Aktor annimmt

### [0.1.1] - 2026-10-21

#### Geändert

- **Panel:**
  - Geräte: Werte in einer Spalte, Knöpfe für die Telegramme eines Senders und zum Hinzufügen
    eines unbekannten Senders, Sortierung nach Name, letztem Empfang, schwächstem Signal oder
    meisten Telegrammen, mehr Angaben zu unbekannten Sendern (Telegrammtyp, Lerntelegramm oder
    mögliche Profile)
  - Sender-IDs: nach Gerät gruppiert, gesperrte IDs zuerst mit ihrem Hinweis, lesbare
    Profilnamen
  - Übernahme: nach dem Übernehmen geht es gleich zur Prüfung der alten IDs, die noch verwendet
    werden, die Zuordnung ist je Gerät kürzer
  - die Überschrift nennt die Ansicht, Darstellung für das Handy

### [0.1.0] - 2026-10-21

Erste Version der Integration.

#### Hinzugefügt

- **Gateways:** Eltako FGW14-USB, FAM14 und FAM-USB, PioTek MGW-ETH (per Zeroconf gefunden), Symcon
  EnOcean LAN Gateway und generische ESP2/ESP3-Gateways. Serielle
  Anschlüsse laufen über die Portauswahl von Home Assistant, TCP (ser2net, LAN-Gateways) wird
  ebenfalls unterstützt. Mehrere Gateways arbeiten nebeneinander, und der FAM14-Bus lässt sich
  über Busgruppen mit Ausfallsicherung nutzen.
- **Einrichtung nur über die Oberfläche:** ein Config-Eintrag pro Gateway, ein Subentry pro
  Gerät. Geräte werden über das Einlernen der ID aus einem Telegramm, nach Kategorie und Art
  oder über das EEP hinzugefügt. Gateways und Geräte lassen sich neu konfigurieren.
- **Geräte:** Schalt- und Dimmaktoren (auch Kanal 2 von Zweikanalaktoren), Rollläden mit
  Position, Lüftungsschlitzen und Lamellenneigung, Heizungsaktoren und Raumregler (mit
  Kühlbetrieb), Zähler (Strom, Gas, Wasser, bereit für das Energie-Dashboard), Fenstergriffe,
  Kontakte, Wandtaster, Wetter- und Luftqualitätssensoren, Permundo-PSC-Zwischenstecker und
  alle Standard-EEP-Profile als generische Geräte. Die Liste steht in
  [docs/devices.de.md](docs/devices.de.md).
- **Mehrere Sender pro Aktor** (Zentralbefehl, Wippe, Controller, Richtungswippe) mit einem
  Sender-ID-Pool: IDs kommen aus Base-ID + 0...127 und bleiben gesperrt, bis das Auslernen
  bestätigt ist.
- **Rollläden:** Positionsverfolgung mit Ankern an den Endlagen, Laufzeit-Assistent und
  Kalibrierung (auch zeitgesteuert über einen Blueprint).
- **Wippengesten** (einfach, doppelt, lang) mit Gerätetriggern sowie Blueprints für Lichter,
  Rollläden, Szenen und Kalibrierung.
- **Virtuelle Geräte:** Home Assistant sendet als Kontakt (auch mit Priorität für den
  Aussperrschutz), Temperatur-, Bewegungs- und Helligkeitssensor, Wetterstation,
  Szenentaster oder Wippe mit wählbaren Tasten.
- **Telegramm-Monitor im Panel:** Live-Liste mit Details, Filtern, Sortierung, Export,
  Signalqualität pro Sender, Gateway-Karten, Sender-ID-Tabelle, Telegramm senden und
  unbekannte Sender als Gerät hinzufügen.
- **Übernahme aus der alten `eltako`-Integration** im Panel: Vorschau, Auswahl, Übernahme von
  Bereich und Labels sowie eine Zuordnung alter zu neuen Entitäts-IDs mit ihrer Verwendung.
- **Gateway-Pflege:** Überwachung der letzten Meldung, Zustandsabgleich beim Start, Reparaturen
  bei instabiler oder stummer Verbindung, Diagnosesensoren und Diagnose-Download.
- **EnOcean-Proxy-Gateways** werden über die Supervisor-Erkennung eingerichtet.
- Übersetzungen auf Deutsch und Englisch, Markenbilder, deutsche und englische READMEs sowie
  ein Benutzerhandbuch.

#### Hinweise

- Die Protokollschicht (ESP2/ESP3, EEPs, FAM14-Bus) ist in diesem Repository ohne EnOcean-
  oder Eltako-Bibliotheken umgesetzt.
- Die offiziellen Dateien der EnOcean Alliance gehören nicht zum Repository (siehe
  [NOTICE](NOTICE)).
