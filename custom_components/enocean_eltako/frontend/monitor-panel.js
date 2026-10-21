// "EnOcean" sidebar panel of the enocean_eltako integration: gateway overview and live
// telegram monitor. Plain web component, no build step; uses HA theme variables, so light
// and dark mode follow Home Assistant. Data: websocket enocean_eltako/telegrams/subscribe,
// enocean_eltako/gateways and enocean_eltako/discover.

const MAX_ROWS = 1000;
const PAGE_SIZES = [25, 50, 100, 200];
const STORAGE_KEY = "enocean_eltako_monitor"; // page size, sort order and filters, per browser
const HISTORY = 200;
// the keys of a capture line (service enocean_eltako.capture): exports can be used as test fixtures
const CAPTURE_KEYS = ["time", "gateway", "dir", "rorg", "data", "sender", "status", "destination", "dbm", "duplicate"];
const ANSWER_WINDOW = 3000; // ms in which a device answers a command
const WEAK_DBM = -85; // below this a sender is at the edge of the range (repeater or antenna)
const TREND_POINTS = 30; // telegrams in a sender's signal curve
const STATUS_INTERVAL = 5000; // ms between gateway status updates
const RORG = { F6: "RPS", D5: "1BS", A5: "4BS", D2: "VLD", D4: "UTE", D1: "MSC" };

// Material Design Icons (Apache 2.0), inlined so the panel needs no icon loading
const ICON = {
  rx: "M20,5.41L18.59,4L7,15.59V9H5V19H15V17H8.41L20,5.41Z",
  tx: "M5,17.59L15.59,7H9V5H19V15H17V8.41L6.41,19L5,17.59Z",
  search:
    "M9.5,3A6.5,6.5 0 0,1 16,9.5C16,11.11 15.41,12.59 14.44,13.73L14.71,14H15.5L20.5,19L19,20.5L14,15.5V14.71L13.73,14.44C12.59,15.41 11.11,16 9.5,16A6.5,6.5 0 0,1 3,9.5A6.5,6.5 0 0,1 9.5,3M9.5,5C7,5 5,7 5,9.5C5,12 7,14 9.5,14C12,14 14,12 14,9.5C14,7 12,5 9.5,5Z",
  pause: "M14,19H18V5H14M6,19H10V5H6V19Z",
  play: "M8,5.14V19.14L19,12.14L8,5.14Z",
  clear:
    "M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19M8,9H16V19H8V9M15.5,4L14.5,3H9.5L8.5,4H5V6H19V4H15.5Z",
  send: "M2,21L23,12L2,3V10L17,12L2,14V21Z",
  copy: "M19,21H8V7H19M19,5H8A2,2 0 0,0 6,7V21A2,2 0 0,0 8,23H19A2,2 0 0,0 21,21V7A2,2 0 0,0 19,5M16,1H4A2,2 0 0,0 2,3V17H4V3H16V1Z",
  download: "M5,20H19V18H5M19,9H15V3H9V9H5L12,16L19,9Z",
  close:
    "M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z",
  plus: "M19,13H13V19H11V13H5V11H11V5H13V11H19V13Z",
  chevron: "M7.41,8.58L12,13.17L16.59,8.58L18,10L12,16L6,10L7.41,8.58Z",
  first: "M18.41,16.59L13.82,12L18.41,7.41L17,6L11,12L17,18L18.41,16.59M6,6H8V18H6V6Z",
  prev: "M15.41,16.58L10.83,12L15.41,7.41L14,6L8,12L14,18L15.41,16.58Z",
  next: "M8.59,16.58L13.17,12L8.59,7.41L10,6L16,12L10,18L8.59,16.58Z",
  last: "M5.59,7.41L10.18,12L5.59,16.59L7,18L13,12L7,6L5.59,7.41M16,6H18V18H16V6Z",
  filter: "M14,12V19.88C14.04,20.18 13.94,20.5 13.71,20.71C13.32,21.1 12.69,21.1 12.3,20.71L10.29,18.7C10.06,18.47 9.96,18.16 10,17.87V12H9.97L4.21,4.62C3.87,4.19 3.95,3.56 4.38,3.22C4.57,3.08 4.78,3 5,3H19C19.22,3 19.43,3.08 19.62,3.22C20.05,3.56 20.13,4.19 19.79,4.62L14.03,12H14Z",
  tower:
    "M12,10A2,2 0 0,1 14,12C14,12.5 13.82,12.94 13.53,13.29L16.7,22H14.57L12,14.93L9.43,22H7.3L10.47,13.29C10.18,12.94 10,12.5 10,12A2,2 0 0,1 12,10M12,8A4,4 0 0,0 8,12C8,12.5 8.1,13 8.28,13.46L7.4,15.86C6.53,14.81 6,13.47 6,12A6,6 0 0,1 12,6A6,6 0 0,1 18,12C18,13.47 17.47,14.81 16.6,15.86L15.72,13.46C15.9,13 16,12.5 16,12A4,4 0 0,0 12,8M12,4A8,8 0 0,0 4,12C4,14.36 5,16.5 6.64,17.94L5.92,19.94C3.54,18.11 2,15.23 2,12A10,10 0 0,1 12,2A10,10 0 0,1 22,12C22,15.23 20.46,18.11 18.08,19.94L17.36,17.94C19,16.5 20,14.36 20,12A8,8 0 0,0 12,4Z",
};

// the integration's icon (docs/assets/enocean-eltako-icon.svg), inline: no image to load,
// own dark tile, so it suits every header colour and theme
const LOGO = `<svg class="logo" viewBox="16 16 480 480" aria-hidden="true">
  <rect x="16" y="16" width="480" height="480" rx="112" fill="#142E42"/>
  <g fill="none" stroke="#66D8D0" stroke-width="34" stroke-linecap="round" stroke-linejoin="round">
    <path d="M137 144V368"/><path d="M137 145H284"/><path d="M137 256H265"/><path d="M137 367H284"/>
  </g>
  <circle cx="314" cy="256" r="17" fill="#F7B36B"/>
  <g fill="none" stroke="#F5FBFC" stroke-linecap="round">
    <path d="M345 211C365 220 378 235 378 256S365 292 345 301" stroke-width="25"/>
    <path d="M365 157C403 181 424 215 424 256S403 331 365 355" stroke-width="22"/>
  </g>
</svg>`;

const TEXT = {
  en: {
    title: "EnOcean",
    gateways: "Gateways",
    sender: "Sender", content: "Content", unavailable: "Not available",
    direction: "Direction", allTypes: "All types", sortHint: "Sort by this column", sortLabel: "Sort",
    sortOptions: { "time:desc": "Newest first", "time:asc": "Oldest first", "sender:asc": "Sender A–Z", "type:asc": "Type", "dbm:desc": "Strongest signal", "gateway:asc": "Gateway" },
    rowsPerPage: "Rows per page", range: (a, b, n) => `${a}–${b} of ${n}`,
    firstPage: "First page", prevPage: "Previous page", nextPage: "Next page", lastPage: "Last page",
    newAbove: (n) => (n === 1 ? "1 new above" : `${n} new above`),
    telegrams: "Telegrams",
    live: "Live",
    paused: (n) => (n ? `Paused · ${n} new` : "Paused"),
    pause: "Pause",
    resume: "Resume",
    clear: "Clear display",
    export: "Export visible telegrams (JSON lines, like the capture service)",
    send: "Send a telegram", sendTitle: "Send a telegram",
    sendHint: "A real telegram: actuators react to it. It is sent from the sender ID of one of your devices, so use it to try out that device.",
    sendGateway: "Gateway", sendSender: "Sender ID", sendType: "Telegram type", sendData: "Data (hex)", sendStatus: "Status (hex)",
    sendAction: "Send", sendCancel: "Cancel", noSenders: "No device of this gateway has a sender ID of its own.",
    sendResult: { sent: "Telegram sent", confirmed: "Telegram sent and confirmed", unconfirmed: "Sent, no answer", failed: "Sending failed: gateway not connected",
      replaced: "Replaced by a newer command", cancelled: "Cancelled", invalid_format: "ID or data is not valid hex", invalid_length: "Wrong data length for this type",
      invalid_sender: "This is not the sender ID of a device", not_found: "Gateway not loaded", unknown: "Sending failed" },
    copy: "Copy as capture line", copied: "Capture line copied", copyFailed: "Copying failed",
    search: "Search device, ID or data",
    searchKey: "Press / to search",
    dirAll: "All",
    rx: "Received",
    tx: "Sent",
    unknownOnly: "Unknown senders only",
    repeats: "Show repetitions",
    details: "Details",
    allGateways: "All gateways",
    count: (shown, total) => (shown === total ? `${total} telegrams` : `${shown} of ${total} telegrams`),
    unknownDevice: "Unknown sender",
    add: "Add device",
    addHint: "Add this sender as a device",
    duplicate: "repetition",
    teachIn: "Teach-in",
    filterSender: "Show only this sender",
    filterDevice: "Show only this device (commands and answers)",
    answerAfter: (ms) => `Answered after ${ms} ms`,
    answerTo: (ms) => `Answer to a command ${ms} ms earlier`,
    noAnswer: "No answer within 3 s",
    pair: "Command and answer",
    repeated: "Repetitions", repeater: "Repeater hops",
    heardTimes: (n) => (n === 1 ? "heard once more" : `heard ${n} more times`),
    viewTakeover: "Takeover",
    tkSteps: ["Take over", "Check", "Old integration off", "Old IDs (optional)"],
    tkStepState: {
      todo: (n) => (n === 1 ? "1 device to take over" : `${n} devices to take over`), done: (a, b) => `${a} of ${b} devices`, check: "Look at the mapping",
      oldOn: "still active", oldOff: "switched off", later: "possible once step 3 is done",
    },
    tkReady: "Can be taken over", tkNot: "Cannot be taken over", tkExists: "Already set up",
    tkAutomations: "Automations", tkScenes: "Scenes", tkScripts: "Scripts", tkDashboards: "Dashboards",
    tkCarry: "Carry area, labels and voice assistant exposure over from the old integration",
    tkNoArea: "No area", tkSearch: "Search name or ID", tkNoMatch: "Nothing matches the search",
    tkSelected: (n, total) => `${n} of ${total} selected`,
    tkGroupCount: (n, total) => (n === total ? (total === 1 ? "1 device" : `${total} devices`) : `${n} of ${total} selected`),
    tkFilterAll: "All", tkFilterUsed: "In use", tkFilterUnused: "Not used",
    tkRun: (n) => (n === 1 ? "Take over 1 device" : `Take over ${n} devices`), tkSelectAll: "Select all", tkSelectNone: "Select none",
    tkNothing: "Nothing selected", tkNotReady: "Cannot be taken over",
    tkReasons: {
      takeover_unsupported: "not supported", takeover_no_sender: "no sender", takeover_bad_sender: "sender not usable",
      takeover_duplicate: "ID listed twice", takeover_exists: "already set up",
    },
    tkErrors: {
      no_config: "No `eltako:` section found in configuration.yaml, so there is nothing to preview. The mapping of already taken devices is below.",
      no_gateway: "The old configuration has no gateway with this base ID.",
      gateway_not_loaded: "The gateway is not loaded.", unknown: "The takeover failed",
    },
    tkDone: (n, carried) => `${n === 1 ? "1 device" : `${n} devices`} taken over${carried ? `, area and labels carried over for ${carried}` : ""}`,
    tkSkipped: "Sender IDs not taken over", tkBusy: "Taking over…",
    tkOldActive: "The old integration is still active, so its entity IDs are taken. Switch the references over, turn the old integration off and remove its entities.",
    tkOldGone: "The old integration is switched off.",
    tkColDevice: "Device", tkColOld: "Old ID", tkColNew: "New ID", tkColUsed: "Used in",
    tkNoNew: "no counterpart", tkNotTaken: "not taken over", tkUnused: "not used",
    tkUsage: { automation: (n) => (n === 1 ? "1 automation" : `${n} automations`), script: (n) => (n === 1 ? "1 script" : `${n} scripts`),
      scene: (n) => (n === 1 ? "1 scene" : `${n} scenes`), dashboard: (n) => (n === 1 ? "1 dashboard" : `${n} dashboards`) },
    tkWhere: "Where the old ID is used", tkCopy: "Copy mapping", tkCsv: "As CSV", tkCopied: "Mapping copied",
    tkEmpty: "No old entities found.",
    tkMore: (n) => (n === 1 ? "1 more entity without counterpart or use" : `${n} more entities without counterpart or use`), tkLess: "Show less",
    tkStillUsed: (n) => (n === 1 ? "1 old ID is still in use: switch it over under Check" : `${n} old IDs are still in use: switch them over under Check`),
    viewTelegrams: "Telegrams", viewDevices: "Devices", viewSenders: "Sender IDs",
    pools: "Sender ID pool", poolBus: (t) => `${t} (bus)`, poolFree: "Free", poolOf: (n) => `of ${n}`,
    poolSummary: (a, b) => `${a} assigned · ${b} blocked`,
    stateAssigned: "assigned", stateBlocked: "blocked", deletedDevice: "deleted device",
    freeAction: "Free", noSenderIds: "No sender IDs in use yet.",
    blockedHint: "Free an ID only once the actuator no longer knows it (teach-out). Otherwise a new device with this ID would control the old actuator too.",
    idCount: (n) => (n === 1 ? "1 ID" : `${n} IDs`),
    profiles: { central: "Central command", controller: "Controller", rocker: "Rocker", cooling: "Cooling switch", direction_rocker: "Direction rocker",
      vld: "VLD commands", contact: "Window contact", temperature: "Temperature", motion: "Motion", brightness: "Brightness", weather: "Weather" },
    freeConfirmTitle: (id) => `Free ${id}?`,
    freeConfirmText: "The actuator has forgotten this ID in its teach-out. After that a new device can get it.",
    freeConfirm: "Yes, free it", freed: "Sender ID freed",
    freeErrors: { not_blocked: "Only a blocked sender ID can be freed", not_found: "Pool not found", invalid_id: "Invalid sender ID", unknown: "Freeing failed" },
    deviceCount: (n) => (n === 1 ? "1 sender" : `${n} senders`),
    telegramsCount: (n) => (n === 1 ? "1 telegram" : `${n} telegrams`),
    weak: "weak signal", weakHint: "Reception is poor: a repeater or a better gateway position helps",
    trend: (n, lo, hi) => `Signal of the last ${n} telegrams: ${lo} to ${hi} dBm`,
    noDevices: "No senders heard yet", showTelegrams: "Show this sender's telegrams",
    devSort: "Sort senders", devSorts: { name: "Name A–Z", recent: "Last heard", weak: "Weakest signal", busy: "Most telegrams" },
    maybe: "Could be", maybeHint: "These profiles decode the telegram; a single telegram cannot tell for sure",
    change: "Change", previous: "Previous telegram", noChange: "same as the previous telegram",
    raw: "Data",
    status: "Status",
    destination: "Destination",
    signal: "Signal",
    gateway: "Gateway",
    time: "Time",
    type: "Type",
    profile: "Sender profile",
    eep: "EEP", model: "Device type",
    on: "on",
    off: "off",
    fields: {
      temperature: "Temperature", humidity: "Humidity", power: "Power", energy: "Energy",
      illuminance: "Illuminance", motion: "Motion", position: "Position", setpoint: "Setpoint",
      voltage: "Voltage", co2: "CO2", window: "Window", handle: "Handle", contact: "Contact",
      button: "Button", pressed: "Pressed", dim: "Brightness", mode: "Mode",
    },
    emptyTitle: "No telegrams yet",
    emptyText: "Press a button or switch an actuator; telegrams show up here right away.",
    noMatchTitle: "No telegram matches the filter",
    noMatchText: "Change or reset the filters.",
    resetFilters: "Reset filters",
    connected: "Connected",
    disconnected: "Disconnected",
    onDemand: "On demand",
    notLoaded: "Not loaded",
    perMinute: "telegrams/min",
    lastHeard: "last",
    never: "nothing heard yet",
    queue: "Queue",
    unconfirmed: "Unconfirmed",
    devices: "Devices",
    freeSenders: "Free sender IDs",
    ago: (s) => (s < 60 ? `${s} s ago` : s < 3600 ? `${Math.round(s / 60)} min ago` : `${Math.round(s / 3600)} h ago`),
    since: (s) => (s < 3600 ? `for ${Math.round(s / 60)} min` : `for ${Math.round(s / 3600)} h`),
    cardHint: "Show only this gateway's telegrams",
    viaProxy: (app, version) => (version ? `via ${app || "proxy app"} ${version}` : `via ${app || "proxy app"}`),
    proxyUnreachable: "proxy status not reachable",
    airtime: "Air time",
    airtimeHint: "Share of the allowed 1 % radio time used in the last hour (estimated by the proxy)",
    programs: (n) => (n === 1 ? "1 program connected" : `${n} programs connected`),
    alone: (peer) => `only ${peer} may send (capture)`,
    noGateways: "No gateway set up yet.",
    addResult: {
      already_configured: "This sender is already set up or ignored (see ignored integrations).",
      no_matching_kind: "No device kind fits this telegram. Add it on the gateway with Add device → By EEP.",
      gateway_not_loaded: "The gateway that heard it is not loaded.",
      not_found: "No telegram from this sender in the monitor any more.",
      failed: "Could not add the device.",
    },
  },
  de: {
    title: "EnOcean",
    gateways: "Gateways",
    sender: "Sender", content: "Inhalt", unavailable: "Nicht verfügbar",
    direction: "Richtung", allTypes: "Alle Typen", sortHint: "Nach dieser Spalte sortieren", sortLabel: "Sortieren",
    sortOptions: { "time:desc": "Neueste zuerst", "time:asc": "Älteste zuerst", "sender:asc": "Sender A–Z", "type:asc": "Typ", "dbm:desc": "Stärkstes Signal", "gateway:asc": "Gateway" },
    rowsPerPage: "Zeilen pro Seite", range: (a, b, n) => `${a}–${b} von ${n}`,
    firstPage: "Erste Seite", prevPage: "Vorherige Seite", nextPage: "Nächste Seite", lastPage: "Letzte Seite",
    newAbove: (n) => (n === 1 ? "1 neues oben" : `${n} neue oben`),
    telegrams: "Telegramme",
    live: "Live",
    paused: (n) => (n ? `Pausiert · ${n} neu` : "Pausiert"),
    pause: "Anhalten",
    resume: "Fortsetzen",
    clear: "Anzeige leeren",
    export: "Sichtbare Telegramme exportieren (JSON-Zeilen, wie der Capture-Dienst)",
    send: "Telegramm senden", sendTitle: "Telegramm senden",
    sendHint: "Ein echtes Telegramm: Aktoren reagieren darauf. Es wird von der Sender-ID eines deiner Geräte gesendet, taugt also zum Ausprobieren dieses Geräts.",
    sendGateway: "Gateway", sendSender: "Sender-ID", sendType: "Telegrammtyp", sendData: "Daten (Hex)", sendStatus: "Status (Hex)",
    sendAction: "Senden", sendCancel: "Abbrechen", noSenders: "Kein Gerät dieses Gateways hat eine eigene Sender-ID.",
    sendResult: { sent: "Telegramm gesendet", confirmed: "Telegramm gesendet und bestätigt", unconfirmed: "Gesendet, keine Antwort", failed: "Senden fehlgeschlagen: Gateway nicht verbunden",
      replaced: "Durch einen neueren Befehl ersetzt", cancelled: "Abgebrochen", invalid_format: "ID oder Daten sind kein gültiges Hex", invalid_length: "Falsche Datenlänge für diesen Typ",
      invalid_sender: "Das ist nicht die Sender-ID eines Geräts", not_found: "Gateway nicht geladen", unknown: "Senden fehlgeschlagen" },
    copy: "Als Capture-Zeile kopieren", copied: "Capture-Zeile kopiert", copyFailed: "Kopieren fehlgeschlagen",
    search: "Gerät, ID oder Daten suchen",
    searchKey: "Taste / zum Suchen",
    dirAll: "Alle",
    rx: "Empfangen",
    tx: "Gesendet",
    unknownOnly: "Nur unbekannte Sender",
    repeats: "Wiederholungen zeigen",
    details: "Details",
    allGateways: "Alle Gateways",
    count: (shown, total) => (shown === total ? `${total} Telegramme` : `${shown} von ${total} Telegrammen`),
    unknownDevice: "Unbekannter Sender",
    add: "Gerät hinzufügen",
    addHint: "Diesen Sender als Gerät anlegen",
    duplicate: "Wiederholung",
    teachIn: "Lerntelegramm",
    filterSender: "Nur diesen Sender zeigen",
    filterDevice: "Nur dieses Gerät zeigen (Befehle und Antworten)",
    answerAfter: (ms) => `Antwort nach ${ms} ms`,
    answerTo: (ms) => `Antwort auf einen Befehl vor ${ms} ms`,
    noAnswer: "Keine Antwort innerhalb von 3 s",
    pair: "Befehl und Antwort",
    repeated: "Wiederholungen", repeater: "Repeater-Stufen",
    heardTimes: (n) => (n === 1 ? "noch einmal empfangen" : `noch ${n}-mal empfangen`),
    viewTakeover: "Übernahme",
    tkSteps: ["Übernehmen", "Prüfen", "Alte Integration aus", "Alte IDs (optional)"],
    tkStepState: {
      todo: (n) => (n === 1 ? "1 Gerät zu übernehmen" : `${n} Geräte zu übernehmen`), done: (a, b) => `${a} von ${b} Geräten`, check: "Zuordnung ansehen",
      oldOn: "noch aktiv", oldOff: "abgeschaltet", later: "möglich nach Schritt 3",
    },
    tkReady: "Übernehmbar", tkNot: "Nicht übernehmbar", tkExists: "Schon eingerichtet",
    tkAutomations: "Automationen", tkScenes: "Szenen", tkScripts: "Skripte", tkDashboards: "Dashboards",
    tkCarry: "Bereich, Labels und Sprachsteuerungs-Freigabe aus der alten Integration übernehmen",
    tkNoArea: "Ohne Bereich", tkSearch: "Name oder ID suchen", tkNoMatch: "Nichts passt zur Suche",
    tkSelected: (n, total) => `${n} von ${total} gewählt`,
    tkGroupCount: (n, total) => (n === total ? (total === 1 ? "1 Gerät" : `${total} Geräte`) : `${n} von ${total} gewählt`),
    tkFilterAll: "Alle", tkFilterUsed: "Verwendet", tkFilterUnused: "Nicht verwendet",
    tkRun: (n) => (n === 1 ? "1 Gerät übernehmen" : `${n} Geräte übernehmen`), tkSelectAll: "Alle auswählen", tkSelectNone: "Alle abwählen",
    tkNothing: "Nichts ausgewählt", tkNotReady: "Nicht übernehmbar",
    tkReasons: {
      takeover_unsupported: "nicht unterstützt", takeover_no_sender: "kein Sender", takeover_bad_sender: "Sender nicht nutzbar",
      takeover_duplicate: "ID doppelt", takeover_exists: "schon eingerichtet",
    },
    tkErrors: {
      no_config: "Kein `eltako:`-Abschnitt in der configuration.yaml gefunden, es gibt also nichts in der Vorschau. Unten steht die Zuordnung der schon übernommenen Geräte.",
      no_gateway: "Die alte Konfiguration hat kein Gateway mit dieser Base-ID.",
      gateway_not_loaded: "Das Gateway ist nicht geladen.", unknown: "Die Übernahme ist fehlgeschlagen",
    },
    tkDone: (n, carried) => `${n === 1 ? "1 Gerät" : `${n} Geräte`} übernommen${carried ? `, Bereich und Labels für ${carried} übertragen` : ""}`,
    tkSkipped: "Sender-IDs nicht übernommen", tkBusy: "Übernehme…",
    tkOldActive: "Die alte Integration ist noch aktiv, ihre Entity-IDs sind belegt. Stelle die Verweise um, schalte die alte Integration ab und entferne ihre Entitäten.",
    tkOldGone: "Die alte Integration ist abgeschaltet.",
    tkColDevice: "Gerät", tkColOld: "Alte ID", tkColNew: "Neue ID", tkColUsed: "Verwendet in",
    tkNoNew: "kein Gegenstück", tkNotTaken: "nicht übernommen", tkUnused: "nicht verwendet",
    tkUsage: { automation: (n) => (n === 1 ? "1 Automation" : `${n} Automationen`), script: (n) => (n === 1 ? "1 Skript" : `${n} Skripte`),
      scene: (n) => (n === 1 ? "1 Szene" : `${n} Szenen`), dashboard: (n) => (n === 1 ? "1 Dashboard" : `${n} Dashboards`) },
    tkWhere: "Wo die alte ID steht", tkCopy: "Zuordnung kopieren", tkCsv: "Als CSV", tkCopied: "Zuordnung kopiert",
    tkEmpty: "Keine alten Entitäten gefunden.",
    tkMore: (n) => (n === 1 ? "1 weitere Entität ohne Gegenstück und Verwendung" : `${n} weitere Entitäten ohne Gegenstück und Verwendung`), tkLess: "Weniger zeigen",
    tkStillUsed: (n) => (n === 1 ? "1 alte ID wird noch verwendet: unter „Prüfen“ umstellen" : `${n} alte IDs werden noch verwendet: unter „Prüfen“ umstellen`),
    viewTelegrams: "Telegramme", viewDevices: "Geräte", viewSenders: "Sender-IDs",
    pools: "Sender-ID-Pool", poolBus: (t) => `${t} (Bus)`, poolFree: "Frei", poolOf: (n) => `von ${n}`,
    poolSummary: (a, b) => `${a} zugewiesen · ${b} gesperrt`,
    stateAssigned: "zugewiesen", stateBlocked: "gesperrt", deletedDevice: "gelöschtes Gerät",
    freeAction: "Freigeben", noSenderIds: "Noch keine Sender-IDs vergeben.",
    blockedHint: "Erst freigeben, wenn der Aktor die ID nicht mehr kennt (Teach-out). Sonst steuert ein neues Gerät mit dieser ID den alten Aktor mit.",
    idCount: (n) => (n === 1 ? "1 ID" : `${n} IDs`),
    profiles: { central: "Zentralbefehl", controller: "Controller", rocker: "Taster", cooling: "Kühlschalter", direction_rocker: "Richtungstaster",
      vld: "VLD-Befehle", contact: "Fensterkontakt", temperature: "Temperatur", motion: "Bewegung", brightness: "Helligkeit", weather: "Wetter" },
    freeConfirmTitle: (id) => `${id} freigeben?`,
    freeConfirmText: "Der Aktor hat diese ID im Teach-out verlernt. Danach kann ein neues Gerät sie bekommen.",
    freeConfirm: "Ja, freigeben", freed: "Sender-ID freigegeben",
    freeErrors: { not_blocked: "Nur eine gesperrte Sender-ID lässt sich freigeben", not_found: "Pool nicht gefunden", invalid_id: "Ungültige Sender-ID", unknown: "Freigeben fehlgeschlagen" },
    deviceCount: (n) => (n === 1 ? "1 Sender" : `${n} Sender`),
    telegramsCount: (n) => (n === 1 ? "1 Telegramm" : `${n} Telegramme`),
    weak: "schwaches Signal", weakHint: "Der Empfang ist schlecht: ein Repeater oder ein besserer Gateway-Standort hilft",
    trend: (n, lo, hi) => `Signal der letzten ${n} Telegramme: ${lo} bis ${hi} dBm`,
    noDevices: "Noch keine Sender gehört", showTelegrams: "Telegramme dieses Senders zeigen",
    devSort: "Sender sortieren", devSorts: { name: "Name A–Z", recent: "Zuletzt gehört", weak: "Schwächstes Signal", busy: "Meiste Telegramme" },
    maybe: "Könnte sein", maybeHint: "Diese Profile dekodieren das Telegramm; ein einzelnes Telegramm sagt es nicht sicher",
    change: "Änderung", previous: "Vorheriges Telegramm", noChange: "wie das vorherige Telegramm",
    raw: "Daten",
    status: "Status",
    destination: "Ziel",
    signal: "Signal",
    gateway: "Gateway",
    time: "Zeit",
    type: "Typ",
    profile: "Sender-Profil",
    eep: "EEP", model: "Gerätetyp",
    on: "an",
    off: "aus",
    fields: {
      temperature: "Temperatur", humidity: "Feuchte", power: "Leistung", energy: "Energie",
      illuminance: "Helligkeit", motion: "Bewegung", position: "Position", setpoint: "Sollwert",
      voltage: "Spannung", co2: "CO2", window: "Fenster", handle: "Griff", contact: "Kontakt",
      button: "Taste", pressed: "Gedrückt", dim: "Helligkeit", mode: "Modus",
    },
    emptyTitle: "Noch keine Telegramme",
    emptyText: "Eine Taste drücken oder einen Aktor schalten; Telegramme erscheinen hier sofort.",
    noMatchTitle: "Kein Telegramm passt zum Filter",
    noMatchText: "Filter ändern oder zurücksetzen.",
    resetFilters: "Filter zurücksetzen",
    connected: "Verbunden",
    disconnected: "Getrennt",
    onDemand: "Bei Bedarf",
    notLoaded: "Nicht geladen",
    perMinute: "Telegramme/min",
    lastHeard: "zuletzt",
    never: "noch nichts gehört",
    queue: "Warteschlange",
    unconfirmed: "Unbestätigt",
    devices: "Geräte",
    freeSenders: "Freie Sender-IDs",
    ago: (s) => (s < 60 ? `vor ${s} s` : s < 3600 ? `vor ${Math.round(s / 60)} min` : `vor ${Math.round(s / 3600)} h`),
    since: (s) => (s < 3600 ? `seit ${Math.round(s / 60)} min` : `seit ${Math.round(s / 3600)} h`),
    cardHint: "Nur die Telegramme dieses Gateways zeigen",
    viaProxy: (app, version) => (version ? `über ${app || "Proxy-App"} ${version}` : `über ${app || "Proxy-App"}`),
    proxyUnreachable: "Proxy-Status nicht erreichbar",
    airtime: "Funkbelegung",
    airtimeHint: "Anteil der erlaubten 1 % Sendezeit in der letzten Stunde (vom Proxy geschätzt)",
    programs: (n) => (n === 1 ? "1 Programm verbunden" : `${n} Programme verbunden`),
    alone: (peer) => `nur ${peer} darf senden (Mitschnitt)`,
    noGateways: "Noch kein Gateway eingerichtet.",
    addResult: {
      already_configured: "Dieser Sender ist schon eingerichtet oder ignoriert (siehe ignorierte Integrationen).",
      no_matching_kind: "Zu diesem Telegramm passt keine Geräteart. Am Gateway über Gerät hinzufügen → Per EEP anlegen.",
      gateway_not_loaded: "Das Gateway, das ihn gehört hat, ist nicht geladen.",
      not_found: "Kein Telegramm dieses Senders mehr im Monitor.",
      failed: "Das Gerät ließ sich nicht anlegen.",
    },
  },
};

const STYLE = `
  /* look of the Device Proxy app: own tokens (light-dark), the colour scheme follows Home Assistant's theme */
  :host {
    display: block; min-height: 100%; background: var(--bg); color: var(--text);
    font-family: Roboto, "Noto Sans", system-ui, -apple-system, sans-serif; font-size: 14px;
    --bg: light-dark(#f3f4f6, #111418); --surface: light-dark(#ffffff, #1b1f24); --soft: light-dark(#f5f7f9, #22272e);
    --line: light-dark(#e1e5ea, #2d333b); --line-2: light-dark(#eef0f3, #262c33); --input-line: light-dark(#c3cbd5, #3a424c);
    --text: light-dark(#1b1f24, #e6e9ed); --muted: light-dark(#5b6270, #9aa4b1);
    --accent: light-dark(#0a6aa8, #5bb2ea); --accent-hover: light-dark(#07507f, #8ccaf2); --accent-soft: light-dark(#eaf3fa, #16324a);
    --on-accent: light-dark(#ffffff, #0b1a26); --focus: #7db8e0;
    --ok: light-dark(#1e6b34, #7fd49a); --warn: light-dark(#8a4b00, #f2c27a); --bad: light-dark(#a1261b, #f2a29a);
    --radius: 16px;
  }
  * { box-sizing: border-box; }
  svg { width: 20px; height: 20px; fill: currentColor; flex: none; }
  button { font: inherit; color: inherit; background: none; border: 0; cursor: pointer; }
  button:focus-visible, input:focus-visible { outline: 3px solid var(--focus); outline-offset: 2px; }

  .header { display: flex; flex-wrap: wrap; align-items: flex-end; justify-content: space-between;
    gap: 0 24px; padding: 0 24px; background: var(--surface); border-bottom: 1px solid var(--line); }
  .brand { display: flex; align-items: center; gap: 12px; padding: 10px 0; min-height: 60px; }
  .brand ha-menu-button { margin-left: -12px; color: var(--text); }
  .brand b { display: block; font-size: 18px; font-weight: 500; line-height: 1.2; }
  .brand small { display: block; font-size: 12px; color: var(--muted); }
  .header .logo { width: 36px; height: 36px; flex: none; }
  .segmented#view { display: flex; flex-wrap: wrap; border: 0; border-radius: 0; overflow: visible; }
  #view button + button { border-left: 0; }
  #view button { display: inline-flex; background: none; align-items: center; min-height: 48px; padding: 0 16px; border-radius: 0; font-size: 14px; font-weight: 500;
    color: var(--muted); border-bottom: 3px solid transparent; }
  #view button:hover { color: var(--text); }
  #view button[aria-pressed="true"] { color: var(--accent); background: none; border-bottom-color: var(--accent); }
  #view button[hidden] { display: none; }
  main { max-width: 1200px; margin: 0 auto; padding: 24px 24px 48px; display: grid;
    grid-template-columns: minmax(0, 1fr); gap: 16px; }
  main > section { min-width: 0; }
  h2 { margin: 0; font-size: 16px; font-weight: 500; }
  .mono { font-family: var(--code-font-family, ui-monospace, monospace); }

  /* gateway summary: status first, technical information under Details */
  .cards { display: flex; flex-direction: column; gap: 12px; }
  .card { display: flex; flex-wrap: wrap; align-items: center; gap: 16px; padding: 20px;
    background: var(--surface); border-radius: var(--radius); border: 1px solid var(--line);
    box-shadow: none; transition: border-color .15s, box-shadow .15s; }
  .card.selected { border: 2px solid var(--accent); padding: 19px; background: var(--accent-soft); }
  .card .name { font-size: 16px; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .card .sub { font-size: 12px; color: var(--muted); overflow-wrap: anywhere; }
  .gateway-icon { display: grid; place-items: center; width: 40px; height: 40px; border-radius: 12px;
    color: var(--accent); background: var(--accent-soft); }
  .gateway-title { flex: 1 1 170px; min-width: 0; }
  .gateway-status { display: flex; flex-wrap: wrap; gap: 4px 10px; align-items: center; margin-top: 3px; }
  .pill { display: inline-flex; align-items: center; gap: 6px; font-size: 12px; white-space: nowrap; }
  .pill i { width: 8px; height: 8px; border-radius: 50%; background: currentColor; }
  .pill.ok i { background: var(--ok); }
  .pill.bad i { background: var(--bad); }
  .pill.idle i { background: var(--warn); }
  .rate, .gateway-count { display: flex; flex-direction: column; align-items: flex-start; gap: 3px;
    padding-left: 18px; border-left: 1px solid var(--line); }
  .rate b { font-size: 16px; font-weight: 500; line-height: 1; }
  .rate span { font-size: 13px; color: var(--muted); }
  .rate .last { font-size: 12px; }
  .gateway-count { font-size: 12px; color: var(--muted); }
  .gateway-count b { font-size: 14px; font-weight: 500; color: var(--text); }
  .gateway-actions { display: flex; flex-wrap: wrap; gap: 8px; }
  .gateway-details { flex-basis: 100%; border-top: 1px solid var(--line); padding-top: 12px; display: grid; gap: 12px; }
  .connection { font-size: 12px; color: var(--muted); overflow-wrap: anywhere; }
  .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 4px 14px;
    font-size: 12px; color: var(--muted); }
  .stats > span { display: flex; justify-content: space-between; gap: 8px; }
  .stats b { color: var(--text); font-weight: 500; }
  .stats b.warn { color: var(--bad); }
  .hint { color: var(--muted); font-size: 14px; padding: 4px; }
  .proxy { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 10px; font-size: 12px;
    color: var(--muted); padding-top: 8px; border-top: 1px solid var(--line); }
  .proxy .muted { color: var(--muted); }
  .airtime { display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 8px;
    font-size: 12px; color: var(--muted); }
  .airtime b { color: var(--text); font-weight: 500; }
  .meter { height: 6px; border-radius: 3px; background: var(--soft); overflow: hidden; }
  .meter i { display: block; height: 100%; background: var(--accent); }
  .meter i.warn { background: var(--warn); }
  .meter i.bad { background: var(--bad); }

  /* telegram section */
  .panel { background: var(--surface); border-radius: var(--radius); border: 1px solid var(--line);
    box-shadow: none; overflow: clip; }
  .bar { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; padding: 12px 12px 12px 16px;
    border-bottom: 1px solid var(--line); }
  .live { display: inline-flex; align-items: center; gap: 6px; font-size: 12px; font-weight: 500; min-height: 24px; padding: 0 10px;
    border-radius: 12px; background: color-mix(in srgb, var(--ok) 16%, transparent); color: var(--ok); }
  .live i { width: 8px; height: 8px; border-radius: 50%; background: currentColor; }
  .live.paused { color: var(--warn); background: color-mix(in srgb, var(--warn) 16%, transparent); }
  .spacer { flex: 1; }
  .icon-btn { width: 40px; height: 40px; border-radius: 50%; display: inline-grid; place-items: center; color: var(--muted); }
  .icon-btn:hover { background: var(--accent-soft); color: var(--accent-hover); }
  .icon-btn[hidden] { display: none; }
  .icon-btn.on { color: var(--accent); }

  .filters { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; padding: 12px 16px; border-bottom: 1px solid var(--line); }
  .search { flex: 1 1 260px; min-width: 0; display: flex; align-items: center; gap: 8px; height: 42px; padding: 0 6px 0 12px;
    border-radius: 10px; border: 1px solid var(--input-line); background: var(--surface); color: var(--muted); }
  .search input { flex: 1; min-width: 0; height: 100%; border: 0; background: none; outline: none; font: inherit;
    font-size: 14px; color: var(--text); }
  .search input::placeholder { color: var(--muted); }
  .search .icon-btn { width: 30px; height: 30px; }
  .search .icon-btn svg { width: 18px; height: 18px; }
  .segmented { display: inline-flex; border: 1px solid var(--input-line); border-radius: 10px; overflow: hidden; }
  .segmented button { min-height: 38px; padding: 0 14px; font-size: 13px; font-weight: 500; color: var(--text); background: var(--surface); white-space: nowrap; }
  .segmented button + button { border-left: 1px solid var(--input-line); }
  .segmented button[aria-pressed="true"] { color: var(--on-accent); background: var(--accent); }
  .chip { min-height: 36px; padding: 0 16px; border-radius: 20px; border: 1px solid var(--input-line); font-size: 13px; font-weight: 500;
    display: inline-flex; align-items: center; justify-content: center; gap: 6px; color: var(--accent); background: var(--surface); white-space: nowrap; }
  .chip:hover:not(:disabled) { background: var(--accent-soft); color: var(--accent-hover); }
  .chip svg { width: 16px; height: 16px; }
  .chip[aria-pressed="true"] { border-color: var(--accent); color: var(--accent-hover); background: var(--accent-soft); }
  .chip.add { color: var(--accent); }
  .chip.primary { background: var(--accent); color: var(--on-accent); border-color: var(--accent); }
  .chip.primary:hover:not(:disabled) { background: var(--accent-hover); color: var(--on-accent); }
  .chip:disabled { opacity: .5; cursor: default; }
  .meta { display: flex; justify-content: space-between; gap: 8px; padding: 8px 16px; font-size: 12px; color: var(--muted); }
  .notice { margin: 8px 16px 0; padding: 12px 14px; border-radius: 12px; font-size: 13px;
    background: color-mix(in srgb, var(--warn) 14%, transparent); display: flex; gap: 8px; align-items: center; }
  .notice[hidden] { display: none; }
  .notice span { flex: 1; }

  /* telegram table: sortable columns, one page at a time */
  .select { height: 38px; border-radius: 10px; border: 1px solid var(--input-line); background: var(--surface);
    color: var(--text); font: inherit; font-size: 13px; padding: 0 8px; max-width: 220px; }
  .select[hidden] { display: none; }
  .telegrams { width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 13px; }
  .telegrams col.c-time { width: 112px; }
  .telegrams col.c-dir { width: 48px; }
  .telegrams col.c-who { width: 30%; }
  .telegrams col.c-type { width: 76px; }
  .telegrams col.c-signal { width: 92px; }
  .telegrams col.c-gw { width: 140px; }
  .telegrams col.c-end { width: 48px; }
  .telegrams th { position: sticky; top: 0; z-index: 1; padding: 0; text-align: left;
    background: var(--soft); border-bottom: 1px solid var(--line); }
  .telegrams th > button, .telegrams th > span { display: flex; align-items: center; gap: 2px; width: 100%; height: 38px;
    padding: 0 8px; font-size: 12px; font-weight: 500; color: var(--muted); text-align: left; white-space: nowrap; }
  .telegrams th:first-child > * { padding-left: 16px; }
  .telegrams th > button:hover, .telegrams th[aria-sort] > button { color: var(--text); }
  .telegrams th .sort { width: 16px; height: 16px; opacity: 0; transition: transform .15s, opacity .15s; }
  .telegrams th > button:hover .sort { opacity: .45; }
  .telegrams th[aria-sort] .sort { opacity: 1; }
  .telegrams th[aria-sort="ascending"] .sort { transform: rotate(180deg); }
  .telegrams td { padding: 10px 8px; border-top: 1px solid var(--line); vertical-align: middle; min-width: 0; }
  .telegrams td:first-child { padding-left: 16px; }
  .telegrams tbody tr:first-child td { border-top: 0; }
  tr.row { cursor: pointer; }
  tr.row:hover > td { background: color-mix(in srgb, var(--soft) 60%, transparent); }
  tr.row.open > td, tr.detail-row > td { background: color-mix(in srgb, var(--accent) 6%, transparent); }
  tr.row.fresh > td { animation: fresh 1.2s ease-out; }
  @keyframes fresh { from { background: color-mix(in srgb, var(--accent) 16%, transparent); } }
  tr.row.dup { opacity: .6; }
  tr.detail-row > td { border-top: 0; padding: 0 12px 12px 16px; cursor: default; }
  tr.empty-row > td { padding: 0; }
  .time { font-family: var(--code-font-family, ui-monospace, monospace); white-space: nowrap; }
  .time small { color: var(--muted); }
  .dir { width: 28px; height: 28px; border-radius: 50%; display: grid; place-items: center; color: var(--muted); background: var(--soft); }
  .dir svg { width: 16px; height: 16px; }
  .dir.tx { color: var(--accent); background: var(--accent-soft); }
  .who .line1 { display: flex; align-items: center; gap: 8px; min-width: 0; }
  .who .name { font-size: 14px; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .who .name.unknown { font-weight: 400; color: var(--muted); }
  .who .line2 { font-size: 12px; color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin-top: 2px; }
  .tag { flex: none; font-size: 12px; font-weight: 500; padding: 2px 10px; border-radius: 12px; background: light-dark(#eef1f4, #2a3038); color: light-dark(#3a414c, #c5ccd5); white-space: nowrap; }
  .tag.teach, .tag.warn { background: color-mix(in srgb, var(--warn) 22%, transparent); color: var(--text); }
  .values { display: flex; flex-wrap: wrap; align-items: center; gap: 4px 12px; min-width: 0; }
  .value { white-space: nowrap; }
  .value span { color: var(--muted); }
  .value b { font-weight: 500; }
  .raw { font-size: 12px; color: var(--muted); overflow-wrap: anywhere; }
  .gw { color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .signal { display: flex; align-items: center; gap: 6px; color: var(--muted); font-size: 12px; white-space: nowrap; }
  .end { text-align: right; }
  .end .chev { transition: transform .15s; }
  .expand { width: 32px; height: 32px; border-radius: 50%; display: inline-grid; place-items: center; color: var(--muted); }
  .expand:hover { background: var(--soft); }
  .expand[aria-expanded="true"] .chev { transform: rotate(180deg); }
  .bars { width: 18px; height: 14px; }
  .bars rect { fill: var(--line); }
  .bars rect.on { fill: var(--muted); }
  .details { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 14px 20px;
    margin: 0; padding: 14px 16px; border-radius: 12px; background: var(--surface); border: 1px solid var(--line); }
  .details div { min-width: 0; }
  .details dt { font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: .03em; }
  .details dd { margin: 2px 0 0; font-size: 13px; overflow-wrap: anywhere; }
  .details .wide { grid-column: 1 / -1; }
  .chg { background: color-mix(in srgb, var(--warn) 35%, transparent); border-radius: 3px; padding: 0 2px; }
  .details .actions { grid-column: 1 / -1; display: flex; flex-wrap: wrap; gap: 8px; }
  .m-only { display: none; }
  .sendform { padding: 12px 16px; border-bottom: 1px solid var(--line); background: color-mix(in srgb, var(--warn) 8%, transparent); }
  .sendform[hidden] { display: none; }
  .sendform h3 { margin: 0 0 4px; font-size: 14px; font-weight: 500; }
  .sendform p { margin: 0 0 10px; font-size: 12px; color: var(--muted); }
  .sendform .fields { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 10px 12px; }
  .sendform label { display: grid; gap: 4px; font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: .03em; min-width: 0; }
  .sendform .text { height: 38px; border-radius: 10px; border: 1px solid var(--input-line); background: var(--surface); color: var(--text);
    padding: 0 10px; font: 13px ui-monospace, monospace; text-transform: none; min-width: 0; }
  .sendform .buttons { display: flex; justify-content: flex-end; gap: 8px; margin-top: 12px; }
  .panel[data-view="devices"] .tg-only, .panel[data-view="senders"] .tg-only, .panel[data-view="senders"] .list-only,
  .panel[data-view="takeover"] .tg-only, .panel[data-view="takeover"] .list-only { display: none !important; }
  .panel:not([data-view="devices"]) .devices, .panel:not([data-view="senders"]) .senders,
  .panel:not([data-view="takeover"]) .takeover { display: none; }
  .takeover { padding-bottom: 8px; }
  .takeover .steps { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px; padding: 14px 16px 12px; border-bottom: 1px solid var(--line); }
  .takeover .step { display: flex; gap: 8px; align-items: flex-start; text-align: left; font: inherit; font-size: 12px; color: var(--muted); background: none; border: 0; padding: 0; }
  .takeover button.step { cursor: pointer; }
  .takeover button.step:disabled { cursor: default; opacity: .6; }
  .takeover .step b { display: block; font-weight: 500; font-size: 13px; color: var(--text); }
  .takeover .step.opt b { color: var(--muted); }
  .takeover .num { flex: none; width: 22px; height: 22px; border-radius: 50%; border: 1px solid var(--line); display: flex; align-items: center; justify-content: center; font-size: 12px; }
  .takeover .step.cur .num { border-color: var(--accent); color: var(--accent); background: color-mix(in srgb, var(--accent) 10%, var(--surface)); }
  .takeover .step.done .num { border-color: var(--ok); color: var(--ok); background: color-mix(in srgb, var(--ok) 15%, var(--surface)); }
  .takeover .toolbar { padding: 10px 16px; display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
  .takeover .pill { height: 28px; padding: 0 12px; border-radius: 999px; border: 1px solid var(--line); font-size: 12px; color: var(--muted); white-space: nowrap; }
  .takeover .pill[aria-pressed="true"] { border-color: transparent; color: var(--accent); background: color-mix(in srgb, var(--accent) 10%, var(--surface)); }
  .takeover .search { flex: 1; min-width: 140px; height: 34px; border-radius: 8px; border: 1px solid var(--line); background: var(--surface);
    color: var(--text); font: inherit; font-size: 13px; padding: 0 10px; }
  .takeover .banner { margin: 0 16px 10px; padding: 8px 12px; border-radius: 8px; font-size: 12px; background: color-mix(in srgb, var(--warn) 18%, transparent); }
  .takeover .banner.ok { background: color-mix(in srgb, var(--ok) 15%, transparent); }
  .takeover .group { display: flex; gap: 10px; align-items: center; padding: 7px 16px; border-top: 1px solid var(--line); background: var(--soft); font-size: 12px; }
  .takeover .group .sub { margin-left: auto; }
  .takeover .fold { font: inherit; font-weight: 500; color: var(--text); background: none; border: 0; padding: 0; cursor: pointer; }
  .takeover .pickrow { display: flex; gap: 10px; align-items: center; padding: 6px 16px 6px 40px; border-top: 1px solid var(--line); font-size: 13px; cursor: pointer; }
  .takeover .pick-name { flex: 1; }
  .takeover .sub { color: var(--muted); font-size: 12px; }
  .takeover .skiprow { display: flex; justify-content: space-between; gap: 12px; padding: 6px 16px; font-size: 13px; color: var(--muted); border-top: 1px solid var(--line); }
  .takeover .actionbar { position: sticky; bottom: 0; display: grid; grid-template-columns: minmax(0, 1fr) auto auto;
    grid-template-areas: "count all run" "carry carry carry"; align-items: center; gap: 6px 12px; padding: 10px 16px;
    border-top: 1px solid var(--line); background: var(--soft); }
  .takeover .bar-count { grid-area: count; font-size: 13px; font-weight: 500; }
  .takeover .bar-all { grid-area: all; }
  .takeover .bar-run { grid-area: run; }
  .takeover .carry { grid-area: carry; display: flex; gap: 6px; align-items: center; font-size: 12px; color: var(--muted); }
  .takeover table { width: 100%; border-collapse: collapse; font-size: 12px; table-layout: fixed; }
  .takeover th { text-align: left; font-weight: 400; font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: .03em; padding: 8px 12px; }
  .takeover td { padding: 6px 12px; vertical-align: top; overflow-wrap: anywhere; }
  .takeover tbody.block { border-top: 1px solid var(--line); }
  .takeover tbody.block tr:first-child td { padding-top: 10px; }
  .takeover tbody.block tr:last-child td { padding-bottom: 10px; }
  .takeover tr.more .fold { font-size: 12px; font-weight: 400; color: var(--muted); }
  .takeover tr.map { cursor: pointer; }
  .takeover tr.map:hover { background: color-mix(in srgb, var(--soft) 60%, transparent); }
  .takeover .old { color: var(--muted); }
  .takeover .chip-s { display: inline-block; font-size: 11px; padding: 1px 7px; border-radius: 999px; margin: 0 4px 2px 0; background: var(--soft); }
  .takeover .chip-s.used { background: color-mix(in srgb, var(--warn) 25%, transparent); }
  .takeover .chip-s.ok { background: color-mix(in srgb, var(--ok) 20%, transparent); }
  .takeover .where td { background: var(--soft); font-size: 12px; }
  @media (max-width: 760px) {
    .takeover .steps { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    /* phones: the main button gets the whole width */
    .takeover .actionbar { grid-template-columns: minmax(0, 1fr) auto; grid-template-areas: "count all" "carry carry" "run run"; }
    .takeover .bar-run { justify-content: center; }
  }
  .senders .pool { display: grid; grid-template-columns: minmax(120px, 1fr) minmax(0, 2fr); gap: 12px 16px; align-items: center; padding: 14px 16px; }
  .senders .meta-label { font-size: 13px; color: var(--muted); }
  .senders .pool .big { font-size: 24px; font-weight: 500; }
  .senders .pool .big small { font-size: 13px; font-weight: 400; color: var(--muted); }
  .senders .pool .range { font-size: 12px; color: var(--muted); margin-top: 6px; }
  .senders .meter { display: block; height: 6px; border-radius: 3px; background: var(--soft); overflow: hidden; }
  .senders .meter i { display: block; height: 100%; background: var(--accent); }
  .senders .sid-group { padding: 4px 0 8px; border-top: 1px solid var(--line); }
  .senders .sid-group.blocked { background: color-mix(in srgb, var(--warn) 10%, transparent); }
  .senders .sid-head { display: flex; align-items: baseline; gap: 8px; padding: 8px 16px 2px; min-width: 0; }
  .senders .sid-name { font-size: 14px; font-weight: 500; overflow-wrap: anywhere; }
  .senders .sid-head .sub { font-size: 12px; color: var(--muted); white-space: nowrap; }
  .senders .sid-row { display: grid; grid-template-columns: 120px minmax(0, 1fr) 96px auto; gap: 2px 12px; align-items: center;
    min-height: 34px; padding: 2px 16px 2px 28px; font-size: 13px; }
  .senders .sid-profile { color: var(--muted); overflow-wrap: anywhere; }
  .senders .act { text-align: right; }
  .senders .act .chip { height: 30px; }
  .senders .deleted { color: var(--muted); font-weight: 400; }
  .senders .tag.ok { background: color-mix(in srgb, var(--ok) 20%, transparent); }
  .senders .sid-hint { margin: 4px 16px 0 28px; font-size: 12px; color: var(--muted); }
  .senders .confirm { margin: 10px 16px 0 28px; padding: 12px 14px; border-radius: 8px; border: 1px solid var(--line); background: var(--surface); }
  .senders .confirm b { display: block; font-weight: 500; margin-bottom: 4px; }
  .senders .confirm p { margin: 0 0 12px; font-size: 13px; color: var(--muted); }
  .senders .confirm .buttons { display: flex; justify-content: flex-end; gap: 8px; }
  .senders .pick { padding: 12px 16px 0; }
  @media (max-width: 760px) {
    /* phones: ID and status on top, profile and button below */
    .senders .sid-row { grid-template-columns: minmax(0, 1fr) auto; grid-template-areas: "id state" "profile act"; padding: 6px 16px; }
    .senders .sid-id { grid-area: id; }
    .senders .sid-state { grid-area: state; }
    .senders .sid-profile { grid-area: profile; }
    .senders .act { grid-area: act; }
    .senders .sid-hint, .senders .confirm { margin-left: 16px; }
  }
  /* one grid for all senders (subgrid): names, values and numbers line up in columns */
  .panel:not([data-view="devices"]) .dev-only { display: none !important; }
  .devices { display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(0, 2fr) auto auto; column-gap: 16px; }
  .devices > .empty { grid-column: 1 / -1; }
  .devices .dev { grid-column: 1 / -1; display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(0, 2fr) auto auto;
    grid-template-columns: subgrid; gap: 4px 16px; align-items: center; padding: 12px 16px; border-top: 1px solid var(--line); cursor: pointer; }
  .devices .dev .acts { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 6px; }
  .devices .dev .acts .chip { height: 30px; padding: 0 10px; }
  .devices .dev:hover { background: color-mix(in srgb, var(--soft) 60%, transparent); }
  .devices .dev .ident { min-width: 0; }
  .spark { display: block; }
  .spark polyline { fill: none; stroke: var(--muted); stroke-width: 1.5; stroke-linejoin: round; stroke-linecap: round; }
  .devices .dev .sub { color: var(--muted); font-size: 12px; overflow-wrap: anywhere; }
  .devices .dev .stats { display: flex; flex-direction: column; align-items: flex-end; gap: 2px; font-size: 12px; color: var(--muted); white-space: nowrap; }
  @media (max-width: 760px) {
    .devices { grid-template-columns: minmax(0, 1fr) auto; }
    .devices .dev { grid-template-columns: minmax(0, 1fr) auto; grid-template-columns: subgrid; }
    .devices .dev .values { grid-column: 1; grid-row: 2; }
    /* phones: the buttons shrink to their icons, next to the values */
    .devices .dev .acts { grid-column: 2; grid-row: 2; flex-wrap: nowrap; }
    .devices .dev .acts .chip { width: 34px; padding: 0; justify-content: center; }
    .devices .dev .acts .lbl { display: none; }
  }

  .pager { display: flex; flex-wrap: wrap; align-items: center; justify-content: flex-end; gap: 6px 12px;
    padding: 8px 8px 8px 16px; border-top: 1px solid var(--line); font-size: 13px; color: var(--muted); }
  .pager label { display: inline-flex; align-items: center; gap: 8px; white-space: nowrap; }
  .pager .range { min-width: 110px; text-align: right; white-space: nowrap; }
  .pager .nav { display: inline-flex; }
  .pager .icon-btn { width: 36px; height: 36px; }
  .pager .icon-btn:disabled { opacity: .35; cursor: default; background: none; color: var(--muted); }
  .pager[hidden] { display: none; }
  .pager .newer { margin-right: auto; }
  .pager .newer[hidden] { display: none; }
  .meta .chip { height: 26px; font-size: 12px; }
  .meta .chip[hidden] { display: none; }

  .empty { display: grid; justify-items: center; gap: 6px; padding: 48px 16px; text-align: center; color: var(--muted); }
  .empty svg { width: 48px; height: 48px; opacity: .5; }
  .empty b { color: var(--text); font-weight: 500; font-size: 16px; }
  .empty .chip { margin-top: 8px; }

  @media (max-width: 760px) {
    main { padding: 16px 16px 32px; }
    .header { padding: 0 16px; }
    .card { gap: 12px; }
    .gateway-title { flex-basis: calc(100% - 60px); }
    .rate { border: 0; padding: 0; flex: 1; }
    .gateway-count { flex: 1; }
    .gateway-actions { flex-basis: 100%; }
    .telegrams colgroup, .telegrams thead { display: none; }
    .telegrams, .telegrams tbody { display: block; }
    tr.row { display: grid; grid-template-columns: 28px minmax(0, 1fr) auto auto; gap: 4px 10px; padding: 12px;
      grid-template-areas: "dir who who time" "dir values signal end"; border-top: 1px solid var(--line); }
    .telegrams tbody tr:first-child { border-top: 0; }
    tr.row > td { display: block; padding: 0; border: 0; background: none !important; }
    tr.row:hover, tr.row.open { background: color-mix(in srgb, var(--soft) 60%, transparent); }
    tr.row.fresh { animation: fresh 1.2s ease-out; }
    tr.row > td.time { grid-area: time; font-size: 12px; text-align: right; }
    tr.row > td.dirc { grid-area: dir; align-self: start; }
    tr.row > td.who { grid-area: who; }
    tr.row > td.content { grid-area: values; }
    tr.row > td.sig { grid-area: signal; align-self: center; }
    tr.row > td.sig .dbm { display: none; }
    tr.row > td.end { grid-area: end; }
    tr.row > td.type, tr.row > td.gwc { display: none; }
    tr.detail-row, tr.detail-row > td { display: block; }
    tr.detail-row > td { padding: 0 12px 12px; }
    tr.empty-row, tr.empty-row > td { display: block; }
    .m-only { display: inline; }
    select.m-only { display: block; }
    .time small { display: none; }
    .pager { justify-content: space-between; gap: 4px; padding: 8px; }
    .pager .range { min-width: 0; margin-left: auto; }
    .pager .icon-btn { width: 34px; height: 34px; }
    .pager label span { display: none; }
    .filters .search { flex-basis: 100%; }
    /* the view switch gets a line of its own and scrolls instead of cutting off a view */
    .segmented#view { flex-basis: 100%; flex-wrap: nowrap; overflow-x: auto; scrollbar-width: none; }
    #view::-webkit-scrollbar { display: none; }
    #view button { flex: 1 0 auto; justify-content: center; padding: 0 10px; }
    .filters .chip { padding: 0 10px; font-size: 12px; flex: 1 1 auto; justify-content: center; }
    .who .line1 { flex-wrap: wrap; row-gap: 4px; }
    .who .name { flex: 1 1 100%; }
  }
  @media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation: none !important; transition: none !important; } }
`;

function esc(value) {
  return String(value ?? "").replace(
    /[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]
  );
}

function svg(path, cls = "") {
  return `<svg class="${cls}" viewBox="0 0 24 24" aria-hidden="true"><path d="${path}"></path></svg>`;
}

function bars(dbm) {
  if (dbm == null) return "";
  const level = dbm >= -70 ? 4 : dbm >= -80 ? 3 : dbm >= -90 ? 2 : 1;
  const rects = [0, 1, 2, 3]
    .map((i) => `<rect x="${i * 5}" y="${10 - i * 3}" width="3" height="${4 + i * 3}" rx="1" class="${i < level ? "on" : ""}"></rect>`)
    .join("");
  return `<svg class="bars" viewBox="0 0 18 14" role="img" aria-label="${dbm} dBm"><title>${dbm} dBm</title>${rects}</svg>`;
}

// buttons that keep the keyboard focus when their row or card is drawn again
const FOCUSABLE = [".expand", "[data-copy]", "[data-only]", ".add", "[data-free]", '[data-gateway-action="filter"]', '[data-gateway-action="details"]'];

// column sort: each compares ascending; equal rows stay newest first
const collator = new Intl.Collator(undefined, { numeric: true, sensitivity: "base" });
const SORTERS = {
  time: (a, b) => (a.time < b.time ? -1 : a.time > b.time ? 1 : 0),
  dir: (a, b) => collator.compare(a.dir, b.dir),
  sender: (a, b) => collator.compare(a.device || `\uffff${a.sender}`, b.device || `\uffff${b.sender}`), // unknown last
  type: (a, b) => collator.compare(RORG[a.rorg] || a.rorg, RORG[b.rorg] || b.rorg),
  dbm: (a, b) => (a.dbm ?? -999) - (b.dbm ?? -999),
  gateway: (a, b) => collator.compare(a.gateway_name || "", b.gateway_name || ""),
};
const DESC_FIRST = new Set(["time", "dbm"]); // first click: newest, strongest
// order of the Devices view; senders without a signal (bus) sort last by signal
const byName = (a, b) => collator.compare(a.last.device || `\uffff${a.last.sender}`, b.last.device || `\uffff${b.last.sender}`);
const DEV_SORTERS = {
  name: byName,
  recent: (a, b) => SORTERS.time(b.last, a.last) || byName(a, b),
  weak: (a, b) => (a.last.dbm == null) - (b.last.dbm == null) || (a.last.dbm ?? 0) - (b.last.dbm ?? 0) || byName(a, b),
  busy: (a, b) => b.count - a.count || byName(a, b),
};

// where an old entity ID of the takeover mapping is still used
const USAGE_KINDS = ["automation", "script", "scene", "dashboard"];
const isUsed = (row) => USAGE_KINDS.some((k) => row.usage[k].length);

const NO_FILTER = { gateway: "", text: "", dir: "", type: "", repeats: false, unknown: false };

function loadView() {
  const fallback = { pageSize: 50, sort: { key: "time", desc: true }, devSort: "name", filter: { ...NO_FILTER } };
  try {
    const view = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
    const saved = view.filter || {};
    const text = (v) => (typeof v === "string" ? v : "");
    return {
      pageSize: PAGE_SIZES.includes(view.pageSize) ? view.pageSize : 50,
      sort: SORTERS[view.sort?.key] ? { key: view.sort.key, desc: !!view.sort.desc } : fallback.sort,
      devSort: DEV_SORTERS[view.devSort] ? view.devSort : "name",
      filter: {
        gateway: text(saved.gateway),
        text: text(saved.text),
        dir: ["rx", "tx"].includes(saved.dir) ? saved.dir : "",
        type: text(saved.type),
        repeats: saved.repeats === true,
        unknown: saved.unknown === true,
      },
    };
  } catch (err) {
    return fallback;
  }
}

function rowKey(r) {
  return `${r.time}|${r.dir}|${r.sender}|${r.data}|${r.gateway}`;
}

class EnOceanEltakoPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._rows = [];
    this._pending = [];
    this._missed = 0; // telegrams while paused, also those beyond the held-back ones
    this._paused = false;
    this._view = "telegrams"; // or "devices" (one line per sender) or "senders" (sender ID pools)
    this._tk = { entry: "", tab: "", preview: null, previewError: "", mapping: null, selected: new Set(), carry: true, open: new Set(), busy: false, filter: "ready", mfilter: "all", q: "", folded: new Set(), more: new Set() };
    this._pools = [];
    this._pool = ""; // shown pool
    this._freeing = null; // blocked sender ID waiting for its confirmation
    const view = loadView();
    this._filter = view.filter;
    this._sort = view.sort;
    this._devSort = view.devSort;
    this._pageSize = view.pageSize;
    this._offset = 0; // first row of the page within the sorted, filtered rows
    this._pageFirst = null; // that row: new rows sorting before it keep the page in place
    this._newAbove = 0;
    this._multi = false; // more than one gateway: gateway column and filter
    this._gateways = [];
    this._expanded = new Set();
    this._keys = new Set(); // rows shown or pending, so a repeated history is not added twice
    this._cleared = new Set(); // rows removed with "clear display"
    this._gatewayDetails = new Set();
    this._fresh = new Set();
    this._unsub = null;
    this._frame = null;
    this._timer = null;
    this._drawn = new WeakMap(); // last HTML per container: unchanged status costs nothing
    this._stale = { list: false, cards: false, devices: false }; // redraw held back while text is selected
    this._onKey = (e) => this._keydown(e);
    this._onSelection = () => {
      if (this._stale.list) this._render(true);
      if (this._stale.cards) this._renderCards(true);
      if (this._stale.devices) this._render(true);
    };
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    this.style.colorScheme = hass.themes?.darkMode ? "dark" : "light";
    if (first) {
      this._t = TEXT[(hass.language || "en").startsWith("de") ? "de" : "en"];
      this._build();
    }
    if (this._menu) this._menu.hass = hass;
    if (this.isConnected && !this._unsub) this._subscribe();
  }

  set narrow(narrow) {
    this._narrow = narrow;
    if (this._menu) this._menu.narrow = narrow;
  }

  connectedCallback() {
    window.addEventListener("keydown", this._onKey);
    document.addEventListener("selectionchange", this._onSelection);
    if (this._hass && !this._unsub) this._subscribe();
  }

  disconnectedCallback() {
    window.removeEventListener("keydown", this._onKey);
    document.removeEventListener("selectionchange", this._onSelection);
    clearInterval(this._timer);
    this._timer = null;
    if (this._unsub) {
      this._unsub.then((unsub) => unsub()).catch(() => {});
      this._unsub = null;
    }
  }

  // ---- structure ---------------------------------------------------------------------------

  _build() {
    const t = this._t;
    this.shadowRoot.innerHTML = `
      <style>${STYLE}</style>
      <header class="header">
        <div class="brand"><ha-menu-button></ha-menu-button>${LOGO}<div><b>${esc(t.title)}</b></div></div>
        <nav class="segmented" role="group" id="view" aria-label="${esc(t.title)}">
          <button data-view="telegrams" aria-pressed="true">${esc(t.viewTelegrams)}</button>
          <button data-view="devices" aria-pressed="false">${esc(t.viewDevices)}</button>
          <button data-view="senders" aria-pressed="false">${esc(t.viewSenders)}</button>
          <button data-view="takeover" aria-pressed="false" hidden>${esc(t.viewTakeover)}</button>
        </nav>
      </header>
      <main>
        <section aria-label="${esc(t.gateways)}">
          <div class="cards" id="cards"></div>
        </section>
        <section class="panel" id="panel" data-view="telegrams" aria-label="${esc(t.telegrams)}">
          <div class="bar">
            <h2 id="viewTitle">${esc(t.telegrams)}</h2>
            <span class="live list-only" id="live"><i></i><span></span></span>
            <span class="spacer"></span>
            <button class="icon-btn list-only" id="pause"></button>
            <button class="icon-btn list-only" id="send" title="${esc(t.send)}" aria-label="${esc(t.send)}" aria-expanded="false">${svg(ICON.send)}</button>
            <button class="icon-btn list-only" id="export" title="${esc(t.export)}" aria-label="${esc(t.export)}">${svg(ICON.download)}</button>
            <button class="icon-btn list-only" id="clear" title="${esc(t.clear)}" aria-label="${esc(t.clear)}">${svg(ICON.clear)}</button>
          </div>
          <div class="filters list-only">
            <label class="search" title="${esc(t.searchKey)}">
              ${svg(ICON.search)}
              <input id="text" type="search" placeholder="${esc(t.search)}" aria-label="${esc(t.search)}" autocomplete="off">
              <button class="icon-btn" id="clearText" aria-label="✕" hidden>${svg(ICON.close)}</button>
            </label>
            <div class="segmented tg-only" role="group" id="dir">
              <button data-dir="" aria-pressed="true">${esc(t.dirAll)}</button>
              <button data-dir="rx" aria-pressed="false">${esc(t.rx)}</button>
              <button data-dir="tx" aria-pressed="false">${esc(t.tx)}</button>
            </div>
            <select class="select" id="gatewayFilter" aria-label="${esc(t.gateway)}" hidden></select>
            <select class="select tg-only" id="typeFilter" aria-label="${esc(t.type)}"></select>
            <button class="chip" id="unknown" aria-pressed="false">${esc(t.unknownOnly)}</button>
            <button class="chip tg-only" id="repeats" aria-pressed="false">${esc(t.repeats)}</button>
            <select class="select m-only tg-only" id="sortSelect" aria-label="${esc(t.sortLabel)}"></select>
            <select class="select dev-only" id="devSort" aria-label="${esc(t.devSort)}" title="${esc(t.devSort)}">${Object.entries(t.devSorts)
              .map(([key, label]) => `<option value="${key}">${esc(label)}</option>`)
              .join("")}</select>
          </div>
          <form class="sendform list-only" id="sendForm" hidden>
            <h3>${esc(t.sendTitle)}</h3>
            <p>${esc(t.sendHint)}</p>
            <div class="fields">
              <label id="sendGatewayRow"><span>${esc(t.sendGateway)}</span><select class="select" id="sendGateway"></select></label>
              <label><span>${esc(t.sendSender)}</span><select class="select" id="sendSender"></select></label>
              <label><span>${esc(t.sendType)}</span><select class="select" id="sendType">${[["F6", "RPS"], ["D5", "1BS"], ["A5", "4BS"], ["D2", "VLD"]].map(([v, l]) => `<option value="${v}">${l} (${v})</option>`).join("")}</select></label>
              <label><span>${esc(t.sendData)}</span><input class="text" id="sendData" autocomplete="off" spellcheck="false" placeholder="70" required></label>
              <label><span>${esc(t.sendStatus)}</span><input class="text" id="sendStatus" autocomplete="off" spellcheck="false" value="30" required></label>
            </div>
            <div class="buttons"><button class="chip" type="button" id="sendCancel">${esc(t.sendCancel)}</button><button class="chip primary" type="submit" id="sendGo">${svg(ICON.send)}${esc(t.sendAction)}</button></div>
          </form>
          <div class="notice" id="notice" hidden><span></span><button class="icon-btn" id="closeNotice" aria-label="✕">${svg(ICON.close)}</button></div>
          <div class="meta list-only"><span id="count"></span><button class="chip reset" id="resetTop" hidden>${esc(t.resetFilters)}</button></div>
          <div class="devices" id="devices"></div>
          <div class="senders" id="senders"></div>
          <div class="takeover" id="takeover"></div>
          <table class="telegrams tg-only" id="table"><colgroup id="cols"></colgroup><thead id="thead"></thead><tbody id="list"></tbody></table>
          <div class="pager tg-only" id="pager">
            <button class="chip newer" id="newer" hidden></button>
            <label><span>${esc(t.rowsPerPage)}</span><select class="select" id="pageSize" aria-label="${esc(t.rowsPerPage)}">${PAGE_SIZES.map((n) => `<option value="${n}">${n}</option>`).join("")}</select></label>
            <span class="range" id="range" aria-live="polite"></span>
            <span class="nav">
              <button class="icon-btn" id="pgFirst" title="${esc(t.firstPage)}" aria-label="${esc(t.firstPage)}">${svg(ICON.first)}</button>
              <button class="icon-btn" id="pgPrev" title="${esc(t.prevPage)}" aria-label="${esc(t.prevPage)}">${svg(ICON.prev)}</button>
              <button class="icon-btn" id="pgNext" title="${esc(t.nextPage)}" aria-label="${esc(t.nextPage)}">${svg(ICON.next)}</button>
              <button class="icon-btn" id="pgLast" title="${esc(t.lastPage)}" aria-label="${esc(t.lastPage)}">${svg(ICON.last)}</button>
            </span>
          </div>
        </section>
      </main>`;
    const $ = (id) => this.shadowRoot.getElementById(id);
    this._menu = this.shadowRoot.querySelector("ha-menu-button");
    this._menu.hass = this._hass;
    this._menu.narrow = this._narrow;

    $("text").addEventListener("input", (e) => {
      $("clearText").hidden = !e.target.value;
      this._set("text", e.target.value.trim());
    });
    $("clearText").addEventListener("click", (e) => {
      e.preventDefault();
      this._setText("");
    });
    $("dir").addEventListener("click", (e) => {
      const button = e.target.closest("button");
      if (button) this._set("dir", button.dataset.dir);
    });
    $("view").addEventListener("click", (e) => {
      const button = e.target.closest("button");
      if (button) this._setView(button.dataset.view);
    });
    $("senders").addEventListener("click", (e) => this._sendersClick(e));
    $("takeover").addEventListener("click", (e) => this._takeoverClick(e));
    $("takeover").addEventListener("change", (e) => this._takeoverChange(e));
    $("takeover").addEventListener("input", (e) => this._takeoverInput(e));
    $("senders").addEventListener("change", (e) => {
      if (e.target.id !== "poolSelect") return;
      this._pool = e.target.value;
      this._freeing = null;
      this._renderSenderIds();
    });
    $("devices").addEventListener("click", (e) => {
      const add = e.target.closest(".add");
      if (add) {
        this._addDevice(add.dataset.id);
        return;
      }
      const dev = e.target.closest(".dev");
      if (!dev || this._selecting($("devices"))) return;
      this._setText(dev.dataset.only);
      this._setView("telegrams");
    });
    $("unknown").addEventListener("click", () => this._set("unknown", !this._filter.unknown));
    $("repeats").addEventListener("click", () => this._set("repeats", !this._filter.repeats));
    $("gatewayFilter").addEventListener("change", (e) => this._set("gateway", e.target.value));
    $("typeFilter").addEventListener("change", (e) => this._set("type", e.target.value));
    $("resetTop").addEventListener("click", () => this._resetFilters());
    $("thead").addEventListener("click", (e) => {
      const button = e.target.closest("[data-sort]");
      if (!button) return;
      const key = button.dataset.sort;
      this._setSort(key, this._sort.key === key ? !this._sort.desc : DESC_FIRST.has(key));
    });
    $("devSort").addEventListener("change", (e) => {
      this._devSort = e.target.value;
      this._saveView();
      this._render();
    });
    $("sortSelect").addEventListener("change", (e) => {
      const [key, dir] = e.target.value.split(":");
      this._setSort(key, dir === "desc");
    });
    $("pageSize").addEventListener("change", (e) => {
      this._pageSize = Number(e.target.value);
      this._offset = Math.floor(this._offset / this._pageSize) * this._pageSize;
      this._saveView();
      this._render();
    });
    $("pager").addEventListener("click", (e) => {
      const button = e.target.closest("button");
      if (!button || button.disabled) return;
      const size = this._pageSize;
      const total = this._total || 0;
      const moves = {
        pgFirst: 0,
        newer: 0,
        pgPrev: Math.max(0, this._offset - size),
        pgNext: this._offset + size,
        pgLast: Math.max(0, Math.floor((total - 1) / size) * size),
      };
      if (!(button.id in moves)) return;
      this._offset = moves[button.id];
      this._render();
    });
    $("pause").addEventListener("click", () => this._togglePause());
    $("clear").addEventListener("click", () => {
      this._offset = 0;
      this._cleared = this._keys;
      this._keys = new Set();
      this._rows = [];
      this._pending = [];
      this._missed = 0;
      this._expanded.clear();
      this._renderBar();
      this._render();
    });
    $("export").addEventListener("click", () => this._export());
    $("send").addEventListener("click", () => this._toggleSend());
    $("sendCancel").addEventListener("click", () => this._toggleSend(false));
    $("sendGateway").addEventListener("change", () => this._renderSenders());
    $("sendType").addEventListener("change", (e) => {
      // a rocker telegram carries its button state in the status byte
      $("sendStatus").value = e.target.value === "F6" ? "30" : "00";
    });
    $("sendForm").addEventListener("submit", (e) => {
      e.preventDefault();
      this._send();
    });
    $("closeNotice").addEventListener("click", () => this._notice(""));
    $("cards").addEventListener("click", (e) => {
      const button = e.target.closest("[data-gateway-action]");
      if (!button) return;
      const entry = button.closest(".card").dataset.entry;
      if (button.dataset.gatewayAction === "details") {
        if (this._gatewayDetails.has(entry)) this._gatewayDetails.delete(entry);
        else this._gatewayDetails.add(entry);
        this._renderCards();
      } else this._set("gateway", this._filter.gateway === entry ? "" : entry);
    });
    $("list").addEventListener("click", (e) => this._listClick(e));
    $("pageSize").value = String(this._pageSize);
    $("devSort").value = this._devSort;
    $("text").value = this._filter.text;
    $("clearText").hidden = !this._filter.text;
    this._renderHead();
    this._renderFilters();
    this._renderBar();
    this._renderCards();
    this._render();
  }

  _keydown(e) {
    const input = this.shadowRoot.getElementById("text");
    const target = e.composedPath()[0];
    const typing = target?.isContentEditable || target?.matches?.("input, textarea, select");
    if (e.key === "/" && input && !typing && !e.defaultPrevented && !e.ctrlKey && !e.metaKey && !e.altKey) {
      e.preventDefault();
      input.focus();
    } else if ((e.key === "p" || e.key === "P") && !typing && !e.defaultPrevented && !e.ctrlKey && !e.metaKey && !e.altKey) {
      e.preventDefault();
      this._togglePause();
    } else if (e.key === "Escape" && this.shadowRoot.activeElement === input) {
      this._setText("");
      input.blur();
    }
  }

  // ---- data --------------------------------------------------------------------------------

  async _subscribe() {
    const unsub = this._hass.connection.subscribeMessage((row) => this._add(row), {
      type: "enocean_eltako/telegrams/subscribe",
      history: HISTORY,
    });
    this._unsub = unsub;
    // failed (e.g. connection lost while subscribing): the next hass update tries again
    unsub.catch(() => {
      if (this._unsub === unsub) this._unsub = null;
    });
    await this._refreshStatus();
    this._checkTakeover();
    clearInterval(this._timer);
    this._timer = setInterval(() => this._refreshStatus(), STATUS_INTERVAL);
  }

  async _refreshStatus() {
    let gateways;
    try {
      gateways = await this._hass.callWS({ type: "enocean_eltako/gateways" });
    } catch (err) {
      return;
    }
    this._gateways = gateways;
    // a remembered gateway filter for a gateway that is gone would hide everything
    if (this._filter.gateway && !gateways.some((g) => g.entry_id === this._filter.gateway)) {
      this._set("gateway", "");
    }
    this._renderCards(true);
    if (this._view === "devices") this._render(true); // "heard x ago" moves on
    if (this._view === "senders" && !this._freeing) this._loadPools();
    const multi = gateways.length > 1;
    if (multi !== this._multi) {
      this._multi = multi;
      this._renderHead();
      this._render();
    }
    this._renderFilters();
  }

  _add(row) {
    // every (re)subscription sends the buffered telegrams again: after a websocket reconnect
    // and when Home Assistant reattaches the panel; keep only those not seen yet
    const key = rowKey(row);
    if (row.history) {
      delete row.history;
      if (this._keys.has(key) || this._cleared.has(key)) return;
    }
    this._keys.add(key);
    if (this._paused) {
      // held back up to the list size; older ones would drop out on resume anyway
      this._pending.push(row);
      this._missed += 1;
      for (const r of this._pending.splice(0, this._pending.length - MAX_ROWS)) this._keys.delete(rowKey(r));
      this._renderBar();
      return;
    }
    this._keepPlace(row);
    this._rows.unshift(row);
    this._trim();
    if (this._initialised) this._fresh.add(key);
    this._schedule();
  }

  _trim() {
    for (const r of this._rows.splice(MAX_ROWS)) {
      const key = rowKey(r);
      this._keys.delete(key);
      this._expanded.delete(key);
      // the oldest drop out; sorted oldest first they stood before the page
      if (this._offset && this._pageFirst && this._matches(r) && this._compare(r, this._pageFirst) < 0) this._offset -= 1;
    }
  }

  _keepPlace(row) {
    // on a later page, a new row sorting before it moves the page along: the rows being
    // read stay where they are, and a button offers the new ones
    if (!this._offset || !this._pageFirst || !this._matches(row)) return;
    if (this._compare(row, this._pageFirst) < 0) {
      this._offset += 1;
      this._newAbove += 1;
    }
  }

  _compare(a, b) {
    const order = SORTERS[this._sort.key](a, b);
    return (this._sort.desc ? -order : order) || SORTERS.time(b, a);
  }

  _setSort(key, desc) {
    this._sort = { key, desc };
    this._offset = 0;
    this._saveView();
    this._renderHead();
    this._render();
  }

  _saveView() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ pageSize: this._pageSize, sort: this._sort, devSort: this._devSort, filter: this._filter }));
    } catch (err) {
      // private window or blocked storage: the view just is not remembered
    }
  }

  _schedule() {
    if (this._frame) return;
    this._frame = requestAnimationFrame(() => {
      this._frame = null;
      this._render(true);
      this._initialised = true;
    });
  }

  _set(key, value) {
    this._filter[key] = value;
    this._offset = 0;
    this._saveView();
    if (key === "gateway") this._renderCards();
    this._renderFilters();
    this._render();
  }

  _setView(view) {
    this._view = view;
    this._offset = 0;
    const $ = (id) => this.shadowRoot.getElementById(id);
    $("panel").dataset.view = view;
    // the heading names the view; the section's label follows it
    const title = { telegrams: this._t.telegrams, devices: this._t.viewDevices, senders: this._t.viewSenders, takeover: this._t.viewTakeover }[view];
    $("viewTitle").textContent = title;
    $("panel").setAttribute("aria-label", title);
    if (view === "senders") this._loadPools();
    if (view === "takeover") this._loadTakeover();
    for (const button of $("view").querySelectorAll("button")) {
      button.setAttribute("aria-pressed", String(button.dataset.view === view));
    }
    this._render();
  }

  _setText(value) {
    const input = this.shadowRoot.getElementById("text");
    input.value = value;
    this.shadowRoot.getElementById("clearText").hidden = !value;
    this._set("text", value);
  }

  _togglePause() {
    this._paused = !this._paused;
    this._missed = 0;
    if (!this._paused) {
      for (const row of this._pending) this._keepPlace(row);
      this._rows = [...this._pending.reverse(), ...this._rows];
      this._pending = [];
      this._trim();
    }
    this._renderBar();
    this._render();
  }

  _toggleRow(key) {
    if (this._expanded.has(key)) this._expanded.delete(key);
    else this._expanded.add(key);
    this._render();
  }

  _listClick(e) {
    const add = e.target.closest(".add");
    if (add) {
      e.stopPropagation();
      this._addDevice(add.dataset.id);
      return;
    }
    const copy = e.target.closest("[data-copy]");
    if (copy) {
      this._copy(copy.dataset.copy);
      return;
    }
    const only = e.target.closest("[data-only]");
    if (only) {
      this._setText(only.dataset.only);
      return;
    }
    if (e.target.closest(".reset")) {
      this._resetFilters();
      return;
    }
    if (e.target.closest(".details") || this._selecting(this.shadowRoot.getElementById("list"))) return;
    const row = e.target.closest(".row");
    if (row) this._toggleRow(row.dataset.key);
  }

  _resetFilters() {
    this._filter = { ...NO_FILTER };
    this._offset = 0;
    this._saveView();
    this.shadowRoot.getElementById("text").value = "";
    this.shadowRoot.getElementById("clearText").hidden = true;
    this._renderCards();
    this._renderFilters();
    this._render();
  }

  async _addDevice(sender) {
    this._notice("");
    let result;
    try {
      result = await this._hass.callWS({ type: "enocean_eltako/discover", sender });
    } catch (err) {
      this._notice(this._t.addResult[err.code] || this._t.addResult.failed);
      return;
    }
    if (result.flow_id || result.reason === "already_in_progress") {
      // the discovered card waits on the integration page
      history.pushState(null, "", "/config/integrations/integration/enocean_eltako");
      window.dispatchEvent(new CustomEvent("location-changed", { detail: { replace: false } }));
      return;
    }
    this._notice(this._t.addResult[result.reason] || this._t.addResult.failed);
  }

  _toggleSend(open = this.shadowRoot.getElementById("sendForm").hidden) {
    const $ = (id) => this.shadowRoot.getElementById(id);
    $("sendForm").hidden = !open;
    $("send").setAttribute("aria-expanded", String(open));
    $("send").classList.toggle("on", open);
    if (open) {
      const loaded = this._gateways.filter((g) => g.loaded);
      this._options($("sendGateway"), loaded.map((g) => [g.entry_id, g.title]), this._filter.gateway || loaded[0]?.entry_id || "");
      $("sendGatewayRow").hidden = loaded.length < 2;
      this._renderSenders();
    }
  }

  _renderSenders() {
    const t = this._t;
    const $ = (id) => this.shadowRoot.getElementById(id);
    const gateway = this._gateways.find((g) => g.entry_id === $("sendGateway").value);
    const senders = gateway?.senders || [];
    const keep = senders.some((s) => s.id === $("sendSender").value) ? $("sendSender").value : senders[0]?.id || "";
    this._options($("sendSender"), senders.map((s) => [s.id, `${s.device} · ${s.id}`]), keep);
    $("sendGo").disabled = !senders.length;
    if (!senders.length) this._notice(t.noSenders);
    else if (this.shadowRoot.getElementById("notice").textContent === t.noSenders) this._notice("");
  }

  async _send() {
    const t = this._t;
    const $ = (id) => this.shadowRoot.getElementById(id);
    if (!$("sendSender").value) return;
    $("sendGo").disabled = true;
    try {
      const result = await this._hass.callWS({
        type: "enocean_eltako/send",
        entry_id: $("sendGateway").value,
        sender: $("sendSender").value,
        rorg: $("sendType").value,
        data: $("sendData").value.trim(),
        status: $("sendStatus").value.trim(),
      });
      this._notice(t.sendResult[result.result] || t.sendResult.unknown);
    } catch (err) {
      this._notice(t.sendResult[err.code] || t.sendResult.unknown);
    }
    $("sendGo").disabled = false;
  }

  _notice(text) {
    const notice = this.shadowRoot.getElementById("notice");
    notice.hidden = !text;
    notice.querySelector("span").textContent = text;
  }

  _matches(r) {
    const f = this._filter;
    const text = f.text.toLowerCase();
    const compact = text.replace(/[-:\s]/g, "");
    return (
      (!f.gateway || r.gateway === f.gateway) &&
      (!f.dir || r.dir === f.dir) &&
      (!f.type || r.rorg === f.type) &&
      (f.repeats || !r.duplicate) &&
      !(f.unknown && (r.device || r.dir === "tx")) &&
      (!text ||
        [r.device, r.data, r.teach_in, r.profile, r.eep, r.model, r.gateway_name, ...(r.candidates || [])].some((v) => v && String(v).toLowerCase().includes(text)) ||
        (r.fields || []).some((field) => String(field.label).toLowerCase().includes(text)) ||
        (compact && String(r.sender).replace(/-/g, "").toLowerCase().includes(compact)))
    );
  }

  _visible() {
    return this._rows.filter((r) => this._matches(r));
  }

  _captureLine(r) {
    // gateway as the entry ID, like the capture service writes it
    return JSON.stringify(Object.fromEntries(CAPTURE_KEYS.map((k) => [k, r[k]])));
  }

  async _copy(key) {
    const row = this._rows.find((r) => rowKey(r) === key);
    if (!row) return;
    try {
      await navigator.clipboard.writeText(this._captureLine(row));
      this._notice(this._t.copied);
    } catch (err) {
      this._notice(this._t.copyFailed);
    }
  }

  _export() {
    const lines = this._visible().slice().reverse().map((r) => this._captureLine(r)).join("\n");
    const blob = new Blob([lines + "\n"], { type: "application/x-ndjson" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `enocean-telegrams-${new Date().toISOString().replace(/[:.]/g, "-")}.jsonl`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(link.href), 1000);
  }

  // ---- rendering ---------------------------------------------------------------------------

  _renderBar() {
    const t = this._t;
    const live = this.shadowRoot.getElementById("live");
    if (!live) return;
    live.classList.toggle("paused", this._paused);
    live.querySelector("span").textContent = this._paused ? t.paused(this._missed) : t.live;
    const pause = this.shadowRoot.getElementById("pause");
    const label = `${this._paused ? t.resume : t.pause} (P)`;
    pause.innerHTML = svg(this._paused ? ICON.play : ICON.pause);
    pause.title = label;
    pause.setAttribute("aria-label", label);
    pause.classList.toggle("on", this._paused);
  }

  _renderFilters() {
    const f = this._filter;
    const $ = (id) => this.shadowRoot.getElementById(id);
    for (const button of $("dir").querySelectorAll("button")) {
      button.setAttribute("aria-pressed", String(button.dataset.dir === f.dir));
    }
    $("unknown").setAttribute("aria-pressed", String(f.unknown));
    $("repeats").setAttribute("aria-pressed", String(f.repeats));
    const gateways = $("gatewayFilter");
    this._options(gateways, [["", this._t.allGateways], ...this._gateways.map((g) => [g.entry_id, g.title])], f.gateway);
    gateways.hidden = !this._multi && !f.gateway;
    $("resetTop").hidden = !(f.gateway || f.text || f.dir || f.type || f.repeats || f.unknown);
  }

  _options(select, options, value) {
    // rebuilt only when the choices change, so an open list stays open
    const key = JSON.stringify(options);
    if (select.dataset.options !== key) {
      select.innerHTML = options.map(([v, label]) => `<option value="${esc(v)}">${esc(label)}</option>`).join("");
      select.dataset.options = key;
    }
    select.value = value;
  }

  _renderHead() {
    // static header: rebuilt only for a new sort or when the gateway column comes or goes
    const t = this._t;
    const columns = [
      ["time", t.time, "time"],
      ["dir", "", "dir", t.direction],
      ["who", t.sender, "sender"],
      ["type", t.type, "type"],
      ["content", t.content],
      ["signal", t.signal, "dbm"],
      ...(this._multi ? [["gw", t.gateway, "gateway"]] : []),
      ["end", ""],
    ];
    const $ = (id) => this.shadowRoot.getElementById(id);
    const focused = this.shadowRoot.activeElement?.dataset?.sort;
    $("cols").innerHTML = columns.map(([id]) => `<col class="c-${id}">`).join("");
    $("thead").innerHTML = `<tr>${columns
      .map(([id, label, sort, aria]) => {
        if (!sort) return `<th scope="col"><span>${esc(label)}</span></th>`;
        const active = this._sort.key === sort;
        const state = active ? ` aria-sort="${this._sort.desc ? "descending" : "ascending"}"` : "";
        return `<th scope="col"${state}><button data-sort="${sort}" title="${esc(t.sortHint)}" aria-label="${esc(aria || label)}">${esc(label)}${svg(ICON.chevron, "sort")}</button></th>`;
      })
      .join("")}</tr>`;
    if (focused) $("thead").querySelector(`[data-sort="${focused}"]`)?.focus({ preventScroll: true });
    const options = Object.entries(t.sortOptions).filter(([v]) => this._multi || !v.startsWith("gateway"));
    const current = `${this._sort.key}:${this._sort.desc ? "desc" : "asc"}`;
    if (!options.some(([v]) => v === current)) options.push([current, `${t.sortLabel}: ${current}`]);
    this._options($("sortSelect"), options, current);
  }

  _renderPager(total, shown) {
    const t = this._t;
    const $ = (id) => this.shadowRoot.getElementById(id);
    const last = this._offset + shown >= total;
    $("range").textContent = total ? t.range(this._offset + 1, this._offset + shown, total) : t.range(0, 0, 0);
    $("pgFirst").disabled = $("pgPrev").disabled = this._offset === 0;
    $("pgNext").disabled = $("pgLast").disabled = last;
    const newer = $("newer");
    newer.hidden = !(this._offset && this._newAbove);
    newer.textContent = t.newAbove(this._newAbove);
    $("pager").hidden = total <= PAGE_SIZES[0] && this._offset === 0; // a short list needs no pages
  }

  _renderCards(background = false) {
    const t = this._t;
    const cards = this.shadowRoot.getElementById("cards");
    if (!cards || this._hold("cards", cards, background)) return;
    if (!this._gateways.length) {
      this._replace(cards, `<div class="hint">${esc(t.noGateways)}</div>`);
      return;
    }
    const now = Date.now() / 1000;
    this._replace(cards, this._gateways
      .map((gw) => {
        let pill = ["", t.notLoaded];
        if (gw.loaded) {
          if (gw.connected) pill = ["ok", t.connected];
          else if (gw.on_demand) pill = ["idle", t.onDemand];
          else pill = ["bad", gw.disconnected_since ? `${t.disconnected} ${t.since(Math.round(now - gw.disconnected_since))}` : t.disconnected];
        }
        const last = gw.last_telegram != null ? `${t.lastHeard} ${t.ago(Math.max(0, Math.round(now - gw.last_telegram)))}` : t.never;
        const rate = gw.per_minute ?? "–";
        const stat = (label, value, warn) => `<span>${esc(label)} <b class="${warn ? "warn" : ""}">${esc(value)}</b></span>`;
        const selected = this._filter.gateway === gw.entry_id;
        const expanded = this._gatewayDetails.has(gw.entry_id);
        const sub = [gw.model !== gw.title ? gw.model : "", gw.base_id].filter(Boolean).join(" · ");
        return `<article class="card${selected ? " selected" : ""}" data-entry="${esc(gw.entry_id)}">
          <div class="gateway-icon">${svg(ICON.tower)}</div>
          <div class="gateway-title"><span class="name">${esc(gw.title)}</span><div class="gateway-status"><span class="pill ${pill[0]}"><i></i>${esc(pill[1])}</span><span class="sub">${esc(sub)}</span></div></div>
          ${gw.loaded ? `<div class="rate"><div><b>${esc(rate)}</b> <span>${esc(t.perMinute)}</span></div><span class="last">${esc(last)}</span></div><div class="gateway-count"><b>${esc(gw.devices ?? "–")} ${esc(t.devices)}</b><span>${esc(gw.free_senders ?? "–")} ${esc(t.freeSenders)}</span></div>` : ""}
          <div class="gateway-actions"><button class="chip" data-gateway-action="filter" title="${esc(t.cardHint)}" aria-pressed="${selected}">${svg(ICON.filter)}${esc(t.telegrams)}</button><button class="chip" data-gateway-action="details" aria-expanded="${expanded}">${esc(t.details)}${svg(ICON.chevron)}</button></div>
          ${expanded ? `<div class="gateway-details"><div class="connection mono">${esc(gw.connection)}</div><div class="stats">${stat(t.queue, gw.queue ?? "–", gw.queue > 5)}${stat(t.unconfirmed, gw.unconfirmed ?? "–", gw.unconfirmed > 0)}${stat(t.freeSenders, gw.free_senders ?? "–", gw.free_senders === 0)}</div>${gw.via_proxy ? this._proxyLine(gw) : ""}</div>` : ""}
        </article>`;
      })
      .join(""));
  }

  _proxyLine(gw) {
    const t = this._t;
    const p = gw.proxy;
    if (!p) {
      return `<div class="proxy"><span class="tag">${esc(t.viaProxy("", ""))}</span><span class="muted">${esc(t.proxyUnreachable)}</span></div>`;
    }
    const share = Number(p.duty_of_limit ?? 0);
    const level = share >= 80 ? "bad" : share >= 50 ? "warn" : "";
    return `<div class="proxy">
        <span class="tag">${esc(t.viaProxy(p.app, p.version))}</span>
        <span>${esc(t.programs(p.programs ?? 0))}</span>
        ${p.exclusive_peer ? `<span class="tag warn">${esc(t.alone(p.exclusive_peer))}</span>` : ""}
      </div>
      <div class="airtime" title="${esc(t.airtimeHint)}">
        <span>${esc(t.airtime)}</span>
        <span class="meter" role="meter" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${share}" aria-label="${esc(t.airtimeHint)}"><i class="${level}" style="width:${Math.min(100, share)}%"></i></span>
        <b>${esc(share.toLocaleString(this._hass.language, { maximumFractionDigits: 1 }))} %</b>
      </div>`;
  }

  _value(value) {
    if (value === true) return this._t.on;
    if (value === false) return this._t.off;
    if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toLocaleString(this._hass.language, { maximumFractionDigits: 2 });
    return String(value);
  }

  _previous(r) {
    // the telegram before this one from the same sender: same direction and type, no repetition
    const start = this._rows.indexOf(r);
    if (start < 0 || r.duplicate) return null;
    for (let i = start + 1; i < this._rows.length; i++) {
      const o = this._rows[i];
      if (o.sender === r.sender && o.dir === r.dir && o.rorg === r.rorg && !o.duplicate && o.gateway === r.gateway) return o;
    }
    return null;
  }

  _diff(r) {
    // the data bytes that differ from the previous telegram, and the values that changed
    const prev = this._previous(r);
    if (!prev) return null;
    const bytes = r.data.match(/../g) || [];
    const before = prev.data.match(/../g) || [];
    const same = bytes.length === before.length;
    const raw = bytes.map((b, i) => (same && b === before[i] ? b : `<span class="chg">${esc(b)}</span>`)).join(" ");
    const now = new Map((r.fields || []).map((f) => [f.label, f]));
    const changes = (prev.fields || [])
      .map((old) => [old, now.get(old.label)])
      .filter(([old, cur]) => cur && cur.value !== old.value)
      .map(([old, cur]) => `${this._label(cur.label)}: ${this._value(old.value)} → ${this._value(cur.value)}${cur.unit ? ` ${cur.unit}` : ""}`);
    const unchanged = same && r.data === prev.data;
    return { raw, prev: prev.data, text: changes.length ? changes.join(" · ") : unchanged ? this._t.noChange : "" };
  }

  _repeats(r) {
    // copies of this telegram the gateway heard (repeaters, a second path), within one second
    const at = Date.parse(r.time);
    return this._rows.filter(
      (o) => o.duplicate && o.sender === r.sender && o.data === r.data && o.gateway === r.gateway && Math.abs(Date.parse(o.time) - at) <= 1000
    ).length;
  }

  _profile(profile) {
    return this._t.profiles[profile] || profile;
  }

  _label(label) {
    return this._t.fields[label] || label.replace(/_/g, " ");
  }

  _pairText(r) {
    // a command we sent and the answer of the same device, matched by time (3 s window)
    if (!r.device || r.duplicate) return "";
    const at = Date.parse(r.time);
    let best = null;
    for (const o of this._rows) {
      if (o.device !== r.device || o.dir === r.dir || o.duplicate) continue;
      const delta = r.dir === "tx" ? Date.parse(o.time) - at : at - Date.parse(o.time);
      if (delta >= 0 && delta <= ANSWER_WINDOW && (best === null || delta < best)) best = delta;
    }
    if (best !== null) return r.dir === "tx" ? this._t.answerAfter(best) : this._t.answerTo(best);
    // the newest telegrams may still be waiting for their answer: only call it missing when old
    return r.dir === "tx" && Date.now() - at > ANSWER_WINDOW ? this._t.noAnswer : "";
  }

  _row(r) {
    const t = this._t;
    const key = rowKey(r);
    const expanded = this._expanded.has(key);
    const time = new Date(r.time);
    const clock = time.toLocaleTimeString(this._hass.language, { hour12: false });
    const ms = String(time.getMilliseconds()).padStart(3, "0");
    const unknown = !r.device && r.dir === "rx";
    const name = r.device
      ? `<span class="name">${esc(r.device)}</span>`
      : `<span class="name unknown">${esc(unknown ? t.unknownDevice : r.sender)}</span>`;
    const tags = r.duplicate ? `<span class="tag">${esc(t.duplicate)}</span>` : "";
    const extra =
      (r.teach_in ? `<span class="tag teach">${esc(t.teachIn)} ${esc(r.teach_in)}</span>` : "") +
      (r.candidates ? `<span class="tag" title="${esc(t.maybeHint)}">${esc(t.maybe)} ${esc(r.candidates.join(", "))}</span>` : "");
    const type = RORG[r.rorg] || r.rorg;
    // on phones type and gateway have no column of their own
    const line2 = [`<span class="mono">${esc(r.sender)}</span>`, r.profile ? esc(this._profile(r.profile)) : "", r.eep ? esc(r.eep) : "", r.eep?.endsWith(":eltako") && r.model ? esc(r.model) : ""].filter(Boolean).join(" · ") +
      `<span class="m-only"> · ${esc(type)}${this._multi ? ` · ${esc(r.gateway_name)}` : ""}</span>`;
    const fields = r.fields || (r.values ? Object.entries(r.values).map(([label, value]) => ({ label, value })) : null);
    const values = fields && fields.length
      ? fields
          .map((f) =>
            f.label === "on" || f.label === "state"
              ? `<span class="value"><b>${esc(this._value(f.value))}</b></span>`
              : `<span class="value"><span>${esc(this._label(f.label))}</span> <b>${esc(this._value(f.value))}</b>${f.unit ? ` ${esc(f.unit)}` : ""}</span>`
          )
          .join("")
      : `<span class="raw mono">${esc(r.data)}</span>`;
    const pair = expanded ? this._pairText(r) : "";
    const diff = expanded ? this._diff(r) : null;
    const copies = expanded && !r.duplicate ? this._repeats(r) : 0;
    const hops = parseInt(r.status, 16) & 0x0f; // low nibble of the status byte: repeater count
    const details = expanded
      ? `<tr class="detail-row" data-key="${esc(key)}"><td colspan="${this._multi ? 8 : 7}"><dl class="details">
          <div><dt>${esc(t.time)}</dt><dd class="mono">${esc(time.toLocaleString(this._hass.language))}.${ms}</dd></div>
          <div><dt>${esc(t.gateway)}</dt><dd>${esc(r.gateway_name)}</dd></div>
          <div><dt>${esc(t.type)}</dt><dd>${esc(type)} (${esc(r.rorg)})</dd></div>
          <div><dt>${esc(t.raw)}</dt><dd class="mono">${diff ? diff.raw : esc(r.data)}</dd></div>
          ${diff ? `<div><dt>${esc(t.previous)}</dt><dd class="mono">${esc(diff.prev)}</dd></div>` : ""}
          ${diff?.text ? `<div class="wide"><dt>${esc(t.change)}</dt><dd>${esc(diff.text)}</dd></div>` : ""}
          <div><dt>${esc(t.status)}</dt><dd class="mono">${esc(r.status)}</dd></div>
          <div><dt>${esc(t.destination)}</dt><dd class="mono">${esc(r.destination)}</dd></div>
          <div><dt>${esc(t.signal)}</dt><dd>${r.dbm != null ? `${esc(r.dbm)} dBm` : esc(t.unavailable)}</dd></div>
          ${hops ? `<div><dt>${esc(t.repeater)}</dt><dd>${hops}</dd></div>` : ""}
          ${copies ? `<div><dt>${esc(t.repeated)}</dt><dd>${esc(t.heardTimes(copies))}</dd></div>` : ""}
          ${r.candidates ? `<div class="wide"><dt>${esc(t.maybe)}</dt><dd class="mono">${esc(r.candidates.join(", "))}</dd></div>` : ""}
          ${r.eep ? `<div><dt>${esc(t.eep)}</dt><dd class="mono">${esc(r.eep)}</dd></div>` : ""}
          ${r.model ? `<div><dt>${esc(t.model)}</dt><dd>${esc(r.model)}</dd></div>` : ""}
          ${pair ? `<div><dt>${esc(t.pair)}</dt><dd>${esc(pair)}</dd></div>` : ""}
          ${r.profile ? `<div><dt>${esc(t.profile)}</dt><dd>${esc(this._profile(r.profile))}</dd></div>` : ""}
          <div class="actions"><button class="chip" data-copy="${esc(key)}">${svg(ICON.copy)}${esc(t.copy)}</button><button class="chip" data-only="${esc(r.device || r.sender)}">${svg(ICON.filter)}${esc(r.device ? t.filterDevice : t.filterSender)}</button>${unknown ? `<button class="chip add" data-id="${esc(r.sender)}" title="${esc(t.addHint)}">${svg(ICON.plus)}${esc(t.add)}</button>` : ""}</div>
        </dl></td></tr>`
      : "";
    const classes = ["row", r.duplicate ? "dup" : "", expanded ? "open" : "", this._fresh.has(key) ? "fresh" : ""].filter(Boolean).join(" ");
    return `<tr class="${classes}" data-key="${esc(key)}">
      <td class="time">${esc(clock)}<small>.${ms}</small></td>
      <td class="dirc"><span class="dir ${r.dir}" title="${esc(r.dir === "rx" ? t.rx : t.tx)}">${svg(r.dir === "rx" ? ICON.rx : ICON.tx)}</span></td>
      <td class="who" title="${esc([r.device, r.sender, r.gateway_name].filter(Boolean).join(" · "))}"><div class="line1">${name}${tags}</div><div class="line2">${line2}</div></td>
      <td class="type"><span class="tag mono" title="${esc(r.rorg)}">${esc(type)}</span></td>
      <td class="content"><div class="values">${extra}${values}</div></td>
      <td class="sig"><span class="signal">${bars(r.dbm)}<span class="dbm">${r.dbm != null ? `${esc(r.dbm)} dBm` : ""}</span></span></td>
      ${this._multi ? `<td class="gwc"><div class="gw">${esc(r.gateway_name)}</div></td>` : ""}
      <td class="end"><button class="expand" aria-expanded="${expanded}" aria-label="${esc(t.details)}" title="${esc(t.details)}">${svg(ICON.chevron, "chev")}</button></td>
    </tr>${details}`;
  }

  _render(background = false) {
    const t = this._t;
    const list = this.shadowRoot.getElementById("list");
    if (!list) return;
    this._renderTypes();
    if (this._view === "devices") {
      this._renderDevices(background);
      return;
    }
    if (this._view === "senders" || this._view === "takeover") return;
    const rows = this._visible().sort((a, b) => this._compare(a, b));
    const total = rows.length;
    this._total = total;
    if (this._offset >= total) this._offset = total ? Math.floor((total - 1) / this._pageSize) * this._pageSize : 0;
    if (this._offset === 0) this._newAbove = 0;
    const page = rows.slice(this._offset, this._offset + this._pageSize);
    this._pageFirst = page[0] || null;
    this.shadowRoot.getElementById("count").textContent = t.count(total, this._rows.length);
    this._renderPager(total, page.length);
    if (this._hold("list", list, background)) return;
    if (!page.length) {
      const filtered = this._rows.length > 0;
      this._replace(list, `<tr class="empty-row"><td colspan="8"><div class="empty">${svg(ICON.tower)}<b>${esc(filtered ? t.noMatchTitle : t.emptyTitle)}</b><span>${esc(filtered ? t.noMatchText : t.emptyText)}</span>${
        filtered ? `<button class="chip reset">${esc(t.resetFilters)}</button>` : ""
      }</div></td></tr>`);
    } else {
      this._replace(list, page.map((r) => this._row(r)).join(""));
    }
    this._fresh.clear();
  }

  async _checkTakeover() {
    // the Takeover view exists only while there is something to take over or to look up
    try {
      const { available } = await this._hass.callWS({ type: "enocean_eltako/takeover/status" });
      const button = this.shadowRoot.querySelector('#view button[data-view="takeover"]');
      if (button) button.hidden = !available;
      if (!available && this._view === "takeover") this._setView("telegrams");
    } catch (err) {
      // not an admin or the integration is still starting: no view
    }
  }

  _tkGateways() {
    return this._gateways.filter((g) => g.loaded);
  }

  async _loadTakeover() {
    const tk = this._tk;
    const gateways = this._tkGateways();
    if (!gateways.some((g) => g.entry_id === tk.entry)) tk.entry = gateways[0]?.entry_id || "";
    if (!tk.entry) {
      this._renderTakeover();
      return;
    }
    tk.previewError = "";
    const [preview, mapping] = await Promise.allSettled([
      this._hass.callWS({ type: "enocean_eltako/takeover/preview", entry_id: tk.entry }),
      this._hass.callWS({ type: "enocean_eltako/takeover/mapping", entry_id: tk.entry }),
    ]);
    tk.preview = preview.status === "fulfilled" ? preview.value : null;
    tk.previewError = preview.status === "rejected" ? preview.reason?.code || "unknown" : "";
    tk.mapping = mapping.status === "fulfilled" ? mapping.value : null;
    const ready = (tk.preview?.devices || []).filter((d) => d.ready);
    tk.selected = new Set(ready.map((d) => d.id));
    tk.filter = "ready";
    if (!tk.tab || !tk.mapping?.rows.length) tk.tab = ready.length || !tk.mapping?.rows.length ? "preview" : "mapping";
    this._renderTakeover();
  }

  _tkDevices() {
    // an ID listed twice in the old configuration: the first entry is the device
    const seen = new Map();
    for (const d of this._tk.preview?.devices || []) if (!seen.has(d.id)) seen.set(d.id, d);
    return [...seen.values()];
  }

  _renderTakeover() {
    const t = this._t;
    const tk = this._tk;
    const container = this.shadowRoot.getElementById("takeover");
    const gateways = this._tkGateways();
    if (!gateways.length) {
      this._replace(container, `<div class="empty">${svg(ICON.tower)}<b>${esc(t.noGateways)}</b></div>`);
      return;
    }
    const devices = this._tkDevices();
    const ready = devices.filter((d) => d.ready);
    const rows = tk.mapping?.rows || [];
    const taken = new Set(rows.filter((r) => r.taken).map((r) => r.id));
    const oldActive = !!(tk.mapping?.old_active ?? tk.preview?.old_active);
    const st = t.tkStepState;
    const mapping = tk.tab === "mapping";
    const steps = [
      { text: ready.length ? st.todo(ready.length) : taken.size ? st.done(taken.size, devices.length || taken.size) : "–", done: !ready.length && taken.size > 0, cur: !mapping, tab: "preview" },
      { text: st.check, cur: mapping, tab: "mapping", off: !rows.length },
      { text: oldActive ? st.oldOn : st.oldOff, done: !oldActive && taken.size > 0 },
      { text: st.later, opt: true },
    ];
    const stepsHtml = steps
      .map((s, i) => {
        const cls = `step${s.done ? " done" : ""}${s.cur ? " cur" : ""}${s.opt ? " opt" : ""}`;
        const inner = `<span class="num">${s.done ? "✓" : i + 1}</span><span><b>${esc(t.tkSteps[i])}</b>${esc(s.text)}</span>`;
        return s.tab
          ? `<button class="${cls}" data-tk-tab="${s.tab}"${s.cur ? ' aria-current="step"' : ""}${s.off ? " disabled" : ""}>${inner}</button>`
          : `<div class="${cls}">${inner}</div>`;
      })
      .join("");
    const select = gateways.length > 1
      ? `<select class="select" id="tkGateway" aria-label="${esc(t.gateway)}">${gateways
          .map((g) => `<option value="${esc(g.entry_id)}"${g.entry_id === tk.entry ? " selected" : ""}>${esc(g.title)}</option>`)
          .join("")}</select>`
      : "";
    const body = mapping ? this._renderMapping(rows, oldActive, select) : this._renderPreview(devices, ready, select);
    this._replace(container, `<div class="steps">${stepsHtml}</div>${body}`);
    container.querySelectorAll("[data-partial]").forEach((box) => { box.indeterminate = true; });
  }

  _tkMatches(...fields) {
    const q = this._tk.q.trim().toLowerCase();
    return !q || fields.some((f) => String(f || "").toLowerCase().includes(q));
  }

  _tkToolbar(select, pills, attr, active, extra = "") {
    const t = this._t;
    const pillHtml = pills
      .map(([key, label, n]) => `<button class="pill" ${attr}="${key}" aria-pressed="${key === active}">${esc(label)} ${n}</button>`)
      .join("");
    return `<div class="toolbar">${select}${pillHtml}<input class="search" id="tkSearch" type="search" placeholder="${esc(t.tkSearch)}" value="${esc(this._tk.q)}" aria-label="${esc(t.tkSearch)}">${extra}</div>`;
  }

  _tkGroups(list) {
    // devices by area, areas alphabetical, devices without an area last
    const groups = new Map();
    for (const d of list) {
      const key = d.area || "";
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(d);
    }
    return [...groups.entries()]
      .sort(([a], [b]) => (a === "") - (b === "") || a.localeCompare(b))
      .map(([area, items]) => ({ area, items: items.sort((x, y) => x.name.localeCompare(y.name)) }));
  }

  _renderPreview(devices, ready, select) {
    const t = this._t;
    const tk = this._tk;
    if (tk.previewError) return `<p class="banner">${esc(t.tkErrors[tk.previewError] || t.tkErrors.unknown)}</p>`;
    const lists = {
      ready,
      exists: devices.filter((d) => d.reason === "takeover_exists"),
      not: devices.filter((d) => !d.ready && d.reason !== "takeover_exists"),
    };
    const labels = { ready: t.tkReady, exists: t.tkExists, not: t.tkNot };
    const pills = Object.keys(lists).filter((k) => k === "ready" || lists[k].length).map((k) => [k, labels[k], lists[k].length]);
    const active = pills.some(([k]) => k === tk.filter) ? tk.filter : "ready";
    const visible = lists[active].filter((d) => this._tkMatches(d.name, d.id, d.area, ...(d.labels || [])));
    const toolbar = this._tkToolbar(select, pills, "data-tk-filter", active);
    let list;
    if (!visible.length) {
      list = `<div class="hint">${esc(t.tkNoMatch)}</div>`;
    } else if (active === "ready") {
      const q = tk.q.trim();
      list = this._tkGroups(visible)
        .map((g) => {
          const picked = g.items.filter((d) => tk.selected.has(d.id)).length;
          const folded = !q && tk.folded.has(g.area);
          const rowsHtml = folded
            ? ""
            : g.items
                .map((d) => `<label class="pickrow"><input type="checkbox" data-tk-pick="${esc(d.id)}"${tk.selected.has(d.id) ? " checked" : ""}>
                  <span class="pick-name">${esc(d.name)} <span class="sub mono">${esc(d.id)}</span></span>
                  ${(d.labels || []).map((l) => `<span class="chip-s">${esc(l)}</span>`).join("")}</label>`)
                .join("");
          return `<div class="group"><input type="checkbox" data-tk-group="${esc(g.area)}" aria-label="${esc(g.area || t.tkNoArea)}"${picked === g.items.length ? " checked" : ""}${picked && picked < g.items.length ? " data-partial" : ""}>
            <button class="fold" data-tk-fold="${esc(g.area)}" aria-expanded="${!folded}"><span aria-hidden="true">${folded ? "▸" : "▾"}</span> ${esc(g.area || t.tkNoArea)}</button>
            <span class="sub">${esc(t.tkGroupCount(picked, g.items.length))}</span></div>${rowsHtml}`;
        })
        .join("");
    } else {
      list = visible
        .map((d) => `<div class="skiprow"><span>${esc(d.name)} <span class="mono">${esc(d.id)}</span></span><span>${esc(t.tkReasons[d.reason] || d.reason || "")}</span></div>`)
        .join("");
    }
    const picked = ready.filter((d) => tk.selected.has(d.id)).length;
    const bar = ready.length
      ? `<div class="actionbar"><b class="bar-count">${esc(t.tkSelected(picked, ready.length))}</b>
          <button class="chip bar-all" data-tk-all="${picked === ready.length ? "none" : "all"}">${esc(picked === ready.length ? t.tkSelectNone : t.tkSelectAll)}</button>
          <button class="chip primary bar-run" data-tk-run ${picked && !tk.busy ? "" : "disabled"}>${esc(tk.busy ? t.tkBusy : picked ? t.tkRun(picked) : t.tkNothing)}</button>
          <label class="carry"><input type="checkbox" id="tkCarry"${tk.carry ? " checked" : ""}>${esc(t.tkCarry)}</label></div>`
      : "";
    return `${toolbar}${list}${bar}`;
  }

  _renderMapping(rows, oldActive, select) {
    const t = this._t;
    const tk = this._tk;
    if (!rows.length) return `<div class="hint">${esc(t.tkEmpty)}</div>`;
    const used = rows.filter(isUsed).length;
    const pills = [["all", t.tkFilterAll, rows.length], ["used", t.tkFilterUsed, used], ["unused", t.tkFilterUnused, rows.length - used]];
    const active = tk.mfilter;
    const visible = rows.filter((r) => (active === "all" || (active === "used") === isUsed(r)) && this._tkMatches(r.device, r.id, r.old, r.new, r.area));
    const extra = `<button class="chip" data-tk-copy>${svg(ICON.copy)}${esc(t.tkCopy)}</button><button class="chip" data-tk-csv>${svg(ICON.download)}${esc(t.tkCsv)}</button>`;
    const usageChips = (r) => {
      const chips = USAGE_KINDS
        .filter((k) => r.usage[k].length)
        .map((k) => `<span class="chip-s used">${esc(t.tkUsage[k](r.usage[k].length))}</span>`)
        .join("");
      return chips || `<span class="chip-s ok">${esc(t.tkUnused)}</span>`;
    };
    const line = (r, first) => {
      const open = tk.open.has(r.old);
      const where = open && isUsed(r)
        ? `<tr class="where"><td colspan="3"><b>${esc(t.tkWhere)}:</b> ${USAGE_KINDS.filter((k) => r.usage[k].length).map((k) => `${esc(t.tkUsage[k](r.usage[k].length))}: ${esc(r.usage[k].join(", "))}`).join(" · ")}</td></tr>`
        : "";
      const target = r.new ? esc(r.new) : `<span class="old">${esc(r.taken ? t.tkNoNew : t.tkNotTaken)}</span>`;
      return `<tr class="map" data-tk-open="${esc(r.old)}">
        <td>${first ? `${esc(r.device)}<div class="sub">${esc([r.area, r.taken ? "" : t.tkNotTaken].filter(Boolean).join(" · "))}</div>` : ""}</td>
        <td class="mono"><span class="old">${esc(r.old)}</span><br>→ ${target}</td>
        <td>${usageChips(r)}</td></tr>${where}`;
    };
    // one block per device; side entities with no counterpart and no use fold away while
    // the whole, unsearched list is shown
    const blocks = new Map();
    for (const r of visible) {
      if (!blocks.has(r.id)) blocks.set(r.id, []);
      blocks.get(r.id).push(r);
    }
    const folding = active === "all" && !tk.q.trim();
    const body = [...blocks.entries()]
      .map(([id, items]) => {
        const minor = folding ? items.filter((r) => !r.primary && !r.new && !isUsed(r)) : [];
        const open = tk.more.has(id);
        const shown = open ? items : items.filter((r) => !minor.includes(r));
        const toggle = minor.length
          ? `<tr class="more"><td></td><td colspan="2"><button class="fold" data-tk-more="${esc(id)}" aria-expanded="${open}"><span aria-hidden="true">${open ? "▾" : "▸"}</span> ${esc(open ? t.tkLess : t.tkMore(minor.length))}</button></td></tr>`
          : "";
        return `<tbody class="block">${shown.map((r, i) => line(r, i === 0)).join("")}${toggle}</tbody>`;
      })
      .join("");
    return `${this._tkToolbar(select, pills, "data-tk-mfilter", active, extra)}
      <p class="banner ${oldActive ? "" : "ok"}">${esc(oldActive ? t.tkOldActive : t.tkOldGone)}</p>
      ${visible.length ? `<table><colgroup><col style="width:26%"><col style="width:40%"><col style="width:34%"></colgroup>
        <thead><tr><th>${esc(t.tkColDevice)}</th><th>${esc(t.tkColOld)} → ${esc(t.tkColNew)}</th><th>${esc(t.tkColUsed)}</th></tr></thead>${body}</table>` : `<div class="hint">${esc(t.tkNoMatch)}</div>`}`;
  }

  _takeoverInput(e) {
    if (e.target.id !== "tkSearch" || e.isComposing) return;
    const pos = e.target.selectionStart;
    this._tk.q = e.target.value;
    this._renderTakeover();
    const input = this.shadowRoot.getElementById("tkSearch");
    input.focus();
    input.setSelectionRange(pos, pos);
  }

  _takeoverChange(e) {
    const tk = this._tk;
    if (e.target.id === "tkGateway") {
      tk.entry = e.target.value;
      tk.tab = "";
      this._loadTakeover();
    } else if (e.target.id === "tkCarry") {
      tk.carry = e.target.checked;
    } else if (e.target.dataset.tkPick) {
      if (e.target.checked) tk.selected.add(e.target.dataset.tkPick);
      else tk.selected.delete(e.target.dataset.tkPick);
      this._renderTakeover();
    } else if (e.target.dataset.tkGroup !== undefined) {
      const area = e.target.dataset.tkGroup;
      for (const d of this._tkDevices()) {
        if (!d.ready || (d.area || "") !== area || !this._tkMatches(d.name, d.id, d.area, ...(d.labels || []))) continue;
        if (e.target.checked) tk.selected.add(d.id);
        else tk.selected.delete(d.id);
      }
      this._renderTakeover();
    }
  }

  _takeoverClick(e) {
    const tk = this._tk;
    const tab = e.target.closest("[data-tk-tab]");
    const fold = e.target.closest("[data-tk-fold]");
    const filter = e.target.closest("[data-tk-filter], [data-tk-mfilter]");
    const more = e.target.closest("[data-tk-more]");
    if (more) {
      const id = more.dataset.tkMore;
      if (tk.more.has(id)) tk.more.delete(id);
      else tk.more.add(id);
      this._renderTakeover();
    } else if (tab) {
      if (tk.tab !== tab.dataset.tkTab) tk.q = "";
      tk.tab = tab.dataset.tkTab;
      this._renderTakeover();
    } else if (filter) {
      if (filter.dataset.tkFilter) tk.filter = filter.dataset.tkFilter;
      else tk.mfilter = filter.dataset.tkMfilter;
      this._renderTakeover();
    } else if (fold) {
      const area = fold.dataset.tkFold;
      if (tk.folded.has(area)) tk.folded.delete(area);
      else tk.folded.add(area);
      this._renderTakeover();
    } else if (e.target.closest("[data-tk-all]")) {
      const all = e.target.closest("[data-tk-all]").dataset.tkAll === "all";
      tk.selected = new Set(all ? this._tkDevices().filter((d) => d.ready).map((d) => d.id) : []);
      this._renderTakeover();
    } else if (e.target.closest("[data-tk-run]")) {
      this._takeOver();
    } else if (e.target.closest("[data-tk-copy]")) {
      this._copyMapping();
    } else if (e.target.closest("[data-tk-csv]")) {
      this._downloadMapping();
    } else {
      const row = e.target.closest("[data-tk-open]");
      if (row && !this._selecting(this.shadowRoot.getElementById("takeover"))) {
        const id = row.dataset.tkOpen;
        if (tk.open.has(id)) tk.open.delete(id);
        else tk.open.add(id);
        this._renderTakeover();
      }
    }
  }

  async _takeOver() {
    const t = this._t;
    const tk = this._tk;
    if (tk.busy || !tk.selected.size) return;
    tk.busy = true;
    this._renderTakeover();
    let result = null;
    try {
      result = await this._hass.callWS({
        type: "enocean_eltako/takeover/run",
        entry_id: tk.entry,
        devices: [...tk.selected],
        carry_over: tk.carry,
      });
    } catch (err) {
      this._notice(t.tkErrors[err.code] || t.tkErrors.unknown);
    }
    tk.busy = false;
    // something taken over: on to step 2, the old IDs that still need switching over
    tk.tab = result?.count ? "mapping" : "";
    tk.mfilter = "all";
    tk.q = "";
    await this._refreshStatus();
    await this._loadTakeover();
    if (!result) return;
    const stillUsed = result.count ? (tk.mapping?.rows || []).filter(isUsed).length : 0;
    this._notice(
      t.tkDone(result.count, result.carried) +
        (stillUsed ? `. ${t.tkStillUsed(stillUsed)}` : "") +
        (result.skipped.length ? `. ${t.tkSkipped}: ${result.skipped.join("; ")}` : "")
    );
  }

  _mappingTable() {
    const t = this._t;
    const head = [t.tkColDevice, "ID", t.tkColOld, t.tkColNew, t.tkAutomations, t.tkScripts, t.tkScenes, t.tkDashboards];
    const lines = (this._tk.mapping?.rows || []).map((r) => [
      r.device, r.id, r.old, r.new || "", r.usage.automation.join("; "), r.usage.script.join("; "), r.usage.scene.join("; "), r.usage.dashboard.join("; "),
    ]);
    return [head, ...lines];
  }

  async _copyMapping() {
    try {
      await navigator.clipboard.writeText(this._mappingTable().map((l) => l.join("\t")).join("\n"));
      this._notice(this._t.tkCopied);
    } catch (err) {
      this._notice(this._t.copyFailed);
    }
  }

  _downloadMapping() {
    const csv = this._mappingTable().map((l) => l.map((v) => `"${String(v).replace(/"/g, '""')}"`).join(",")).join("\n");
    const link = document.createElement("a");
    link.href = URL.createObjectURL(new Blob([csv + "\n"], { type: "text/csv" }));
    link.download = "enocean-entity-mapping.csv";
    link.click();
    setTimeout(() => URL.revokeObjectURL(link.href), 1000);
  }

  async _loadPools() {
    try {
      this._pools = await this._hass.callWS({ type: "enocean_eltako/sender_pools" });
    } catch (err) {
      return;
    }
    if (!this._pools.some((p) => p.id === this._pool)) this._pool = this._pools[0]?.id || "";
    this._renderSenderIds();
  }

  _poolLabel(pool) {
    return pool.kind === "bus" ? this._t.poolBus(pool.title) : pool.title;
  }

  _renderSenderIds() {
    const t = this._t;
    const container = this.shadowRoot.getElementById("senders");
    const pool = this._pools.find((p) => p.id === this._pool);
    if (!pool) {
      this._replace(container, `<div class="empty">${svg(ICON.tower)}<b>${esc(t.noGateways)}</b></div>`);
      return;
    }
    const blocked = pool.rows.filter((r) => r.state === "blocked");
    const used = pool.size - pool.free;
    const select = this._pools.length > 1
      ? `<div class="pick"><select class="select" id="poolSelect" aria-label="${esc(t.pools)}">${this._pools
          .map((p) => `<option value="${esc(p.id)}"${p.id === pool.id ? " selected" : ""}>${esc(this._poolLabel(p))}</option>`)
          .join("")}</select></div>`
      : "";
    // one block per device with its IDs; blocked IDs (deleted devices) first, they need doing
    const groups = new Map();
    for (const r of pool.rows) {
      const key = r.ref || r.device || r.id;
      if (!groups.has(key)) groups.set(key, { device: r.device, ref: r.ref, rows: [] });
      groups.get(key).rows.push(r);
    }
    const isBlocked = (r) => r.state === "blocked";
    const list = [...groups.values()]
      .map((g) => ({ ...g, blocked: g.rows.some(isBlocked), rows: g.rows.sort((a, b) => isBlocked(b) - isBlocked(a) || collator.compare(a.id, b.id)) }))
      .sort((a, b) => b.blocked - a.blocked || (a.device == null) - (b.device == null) || collator.compare(a.device || "", b.device || ""));
    const html = list
      .map((g) => {
        const name = g.device
          ? `<span class="sid-name">${esc(g.device)}</span>`
          : `<span class="sid-name deleted" title="${esc(g.ref || "")}">${esc(t.deletedDevice)}</span>`;
        const rows = g.rows
          .map((r) => `<div class="sid-row${isBlocked(r) ? " blocked" : ""}" data-key="${esc(r.id)}">
            <span class="sid-id mono">${esc(r.id)}</span><span class="sid-profile">${esc(r.profile ? this._profile(r.profile) : "–")}</span>
            <span class="sid-state"><span class="tag ${isBlocked(r) ? "warn" : "ok"}">${esc(isBlocked(r) ? t.stateBlocked : t.stateAssigned)}</span></span>
            <span class="act">${isBlocked(r) ? `<button class="chip" data-free="${esc(r.id)}" data-device="${esc(r.device || r.ref || "")}">${esc(t.freeAction)}</button>` : ""}</span>
          </div>`)
          .join("");
        const confirm = this._freeing && g.rows.some((r) => isBlocked(r) && r.id === this._freeing.id)
          ? `<div class="confirm"><b>${esc(t.freeConfirmTitle(this._freeing.id))}</b><p>${esc(t.freeConfirmText)}</p>
              <div class="buttons"><button class="chip" data-free-cancel>${esc(t.sendCancel)}</button><button class="chip primary" data-free-confirm>${esc(t.freeConfirm)}</button></div></div>`
          : "";
        return `<div class="sid-group${g.blocked ? " blocked" : ""}">
          <div class="sid-head">${name}<span class="sub">${esc(t.idCount(g.rows.length))}</span></div>
          ${rows}${g.blocked ? `<p class="sid-hint">${esc(t.blockedHint)}</p>` : ""}${confirm}</div>`;
      })
      .join("");
    this._replace(container, `${select}
      <div class="pool">
        <div><div class="meta-label">${esc(t.poolFree)}</div><div class="big">${esc(pool.free)} <small>${esc(t.poolOf(pool.size))}</small></div></div>
        <div><span class="meter" role="meter" aria-valuemin="0" aria-valuemax="${esc(pool.size)}" aria-valuenow="${esc(used)}" aria-label="${esc(t.pools)}"><i style="width:${Math.round((used / pool.size) * 100)}%"></i></span>
          <div class="range"><span class="mono">${esc(pool.start)} – ${esc(pool.end)}</span> · ${esc(t.poolSummary(pool.rows.length - blocked.length, blocked.length))}</div></div>
      </div>
      ${pool.rows.length ? `<div class="sid-list">${html}</div>` : `<div class="hint">${esc(t.noSenderIds)}</div>`}`);
  }

  _sendersClick(e) {
    const free = e.target.closest("[data-free]");
    if (free) {
      this._freeing = { id: free.dataset.free, device: free.dataset.device };
      this._renderSenderIds();
    } else if (e.target.closest("[data-free-cancel]")) {
      this._freeing = null;
      this._renderSenderIds();
    } else if (e.target.closest("[data-free-confirm]")) {
      this._freeSender();
    }
  }

  async _freeSender() {
    const t = this._t;
    const { id } = this._freeing;
    try {
      await this._hass.callWS({ type: "enocean_eltako/sender_pools/free", pool: this._pool, sender: id });
      this._notice(t.freed);
    } catch (err) {
      this._notice(t.freeErrors[err.code] || t.freeErrors.unknown);
    }
    this._freeing = null;
    await this._loadPools();
  }

  _deviceList() {
    // the latest telegram of each sender, with its values, count and rate
    const f = this._filter;
    const text = f.text.toLowerCase();
    const compact = text.replace(/[-:\s]/g, "");
    const since = Date.now() - 60000;
    const senders = new Map();
    for (const r of this._rows) {
      if (r.dir !== "rx" || r.duplicate || (f.gateway && r.gateway !== f.gateway) || (f.unknown && r.device)) continue;
      const key = `${r.gateway}|${r.sender}`;
      let d = senders.get(key);
      if (!d) {
        d = { last: r, fields: null, teach: null, candidates: null, count: 0, perMinute: 0, dbm: [] };
        senders.set(key, d);
      }
      d.count += 1;
      if (!d.fields && (r.fields || r.values)) d.fields = r.fields || Object.entries(r.values).map(([label, value]) => ({ label, value }));
      // an unknown sender: what its telegrams tell about it, newest first
      d.teach ||= r.teach_in || null;
      d.candidates ||= r.candidates || null;
      if (Date.parse(r.time) >= since) d.perMinute += 1;
      if (r.dbm != null && d.dbm.length < TREND_POINTS) d.dbm.unshift(r.dbm); // oldest first
    }
    return [...senders.values()]
      .filter(({ last: r }) => {
        if (!text) return true;
        return (
          [r.device, r.teach_in, r.profile, r.eep, r.model, r.gateway_name].some((v) => v && String(v).toLowerCase().includes(text)) ||
          (compact && String(r.sender).replace(/-/g, "").toLowerCase().includes(compact))
        );
      })
      .sort(DEV_SORTERS[this._devSort]);
  }

  _renderDevices(background) {
    const t = this._t;
    const container = this.shadowRoot.getElementById("devices");
    const devices = this._deviceList();
    this.shadowRoot.getElementById("count").textContent = t.deviceCount(devices.length);
    if (this._hold("devices", container, background)) return;
    const now = Date.now();
    this._replace(container, devices.length
      ? devices.map((d) => this._deviceRow(d, now)).join("")
      : `<div class="empty">${svg(ICON.tower)}<b>${esc(t.noDevices)}</b></div>`);
  }

  _sparkline(dbm) {
    // the signal of the last telegrams as a small curve; the band is fixed (-100 to -30 dBm),
    // so curves of different senders compare
    if (dbm.length < 2) return "";
    const [w, h] = [72, 18];
    const y = (v) => (h - 2 - ((Math.min(-30, Math.max(-100, v)) + 100) / 70) * (h - 4)).toFixed(1);
    const points = dbm.map((v, i) => `${((i / (dbm.length - 1)) * w).toFixed(1)},${y(v)}`).join(" ");
    const title = this._t.trend(dbm.length, Math.min(...dbm), Math.max(...dbm));
    return `<svg class="spark" viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" role="img" aria-label="${esc(title)}"><title>${esc(title)}</title><polyline points="${points}"/></svg>`;
  }

  _deviceRow({ last: r, fields, teach, candidates, count, perMinute, dbm }, now) {
    const t = this._t;
    const unknown = !r.device;
    const name = unknown ? `<span class="name unknown">${esc(t.unknownDevice)}</span>` : `<span class="name">${esc(r.device)}</span>`;
    // without a profile the telegram type says what kind of sender it is
    const sub = [`<span class="mono">${esc(r.sender)}</span>`, esc(r.eep || RORG[r.rorg] || r.rorg), r.eep?.endsWith(":eltako") && r.model ? esc(r.model) : "", this._multi ? esc(r.gateway_name) : ""]
      .filter(Boolean)
      .join(" · ");
    const values = fields && fields.length
      ? fields
          .map((f) =>
            f.label === "on" || f.label === "state"
              ? `<span class="value"><b>${esc(this._value(f.value))}</b></span>`
              : `<span class="value"><span>${esc(this._label(f.label))}</span> <b>${esc(this._value(f.value))}</b>${f.unit ? ` ${esc(f.unit)}` : ""}</span>`
          )
          .join("")
      : `<span class="raw mono">${esc(r.data)}</span>`;
    const hints = unknown
      ? (teach ? `<span class="tag teach">${esc(t.teachIn)} ${esc(teach)}</span>` : "") +
        (candidates ? `<span class="tag" title="${esc(t.maybeHint)}">${esc(t.maybe)} ${esc(candidates.join(", "))}</span>` : "")
      : "";
    const weak = r.dbm != null && r.dbm < WEAK_DBM;
    const heard = t.ago(Math.max(0, Math.round((now - Date.parse(r.time)) / 1000)));
    return `<div class="dev" data-key="${esc(`${r.gateway}|${r.sender}`)}" data-only="${esc(r.device || r.sender)}">
      <div class="ident"><div class="line1">${name}</div><div class="sub">${sub}</div></div>
      <div class="values">${hints}${values}</div>
      <div class="stats"><span>${esc(heard)}</span><span>${esc(t.telegramsCount(count))} · ${esc(perMinute)}/min</span>
        <span class="signal">${this._sparkline(dbm)}${bars(r.dbm)}<span class="dbm">${r.dbm != null ? `${esc(r.dbm)} dBm` : ""}</span>${weak ? `<span class="tag warn" title="${esc(t.weakHint)}">${esc(t.weak)}</span>` : ""}</span></div>
      <div class="acts"><button class="chip" data-only="${esc(r.device || r.sender)}" title="${esc(t.showTelegrams)}" aria-label="${esc(t.showTelegrams)}">${svg(ICON.filter)}<span class="lbl">${esc(t.telegrams)}</span></button>${
        unknown ? `<button class="chip add" data-id="${esc(r.sender)}" title="${esc(t.addHint)}" aria-label="${esc(t.addHint)}">${svg(ICON.plus)}<span class="lbl">${esc(t.add)}</span></button>` : ""
      }</div>
    </div>`;
  }

  _renderTypes() {
    // the telegram types heard so far, plus the chosen one
    const types = new Set(this._rows.map((r) => r.rorg));
    if (this._filter.type) types.add(this._filter.type);
    const options = [...types].sort().map((rorg) => [rorg, RORG[rorg] ? `${RORG[rorg]} (${rorg})` : rorg]);
    this._options(this.shadowRoot.getElementById("typeFilter"), [["", this._t.allTypes], ...options], this._filter.type);
  }

  _selecting(container) {
    // shadowRoot.getSelection: Chromium; elsewhere the document selection reaches into it
    const sel = this.shadowRoot.getSelection ? this.shadowRoot.getSelection() : document.getSelection();
    if (!sel || sel.isCollapsed) return false;
    return sel.anchorNode === this || container.contains(sel.anchorNode);
  }

  _hold(name, container, background) {
    // a new telegram or status update does not wipe text the user is selecting (to copy an ID)
    this._stale[name] = background && this._selecting(container);
    return this._stale[name];
  }

  _replace(container, html) {
    // redraw, keeping the keyboard focus on the same button of the same row or card
    if (this._drawn.get(container) === html) return;
    this._drawn.set(container, html);
    const active = this.shadowRoot.activeElement;
    let focus = null;
    if (active && container.contains(active)) {
      const holder = active.closest("[data-key], [data-entry]");
      const selector = FOCUSABLE.find((s) => active.matches(s));
      if (holder && selector) {
        const attr = holder.hasAttribute("data-key") ? "data-key" : "data-entry";
        focus = { attr, value: holder.getAttribute(attr), selector };
      }
    }
    container.innerHTML = html;
    if (focus) {
      // a row and its details share the key: take the one that has the button
      [...container.querySelectorAll(`[${focus.attr}]`)]
        .filter((h) => h.getAttribute(focus.attr) === focus.value)
        .map((h) => h.querySelector(focus.selector))
        .find(Boolean)
        ?.focus({ preventScroll: true });
    }
  }
}

customElements.define("enocean-eltako-monitor", EnOceanEltakoPanel);
