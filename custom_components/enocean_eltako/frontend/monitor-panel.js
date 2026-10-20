// "EnOcean" sidebar panel of the enocean_eltako integration: gateway overview and live
// telegram monitor. Plain web component, no build step; uses HA theme variables, so light
// and dark mode follow Home Assistant. Data: websocket enocean_eltako/telegrams/subscribe,
// enocean_eltako/gateways and enocean_eltako/discover.

const MAX_ROWS = 1000;
const HISTORY = 200;
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
  download: "M5,20H19V18H5M19,9H15V3H9V9H5L12,16L19,9Z",
  close:
    "M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z",
  plus: "M19,13H13V19H11V13H5V11H11V5H13V11H19V13Z",
  chevron: "M7.41,8.58L12,13.17L16.59,8.58L18,10L12,16L6,10L7.41,8.58Z",
  filter: "M14,12V19.88C14.04,20.18 13.94,20.5 13.71,20.71C13.32,21.1 12.69,21.1 12.3,20.71L10.29,18.7C10.06,18.47 9.96,18.16 10,17.87V12H9.97L4.21,4.62C3.87,4.19 3.95,3.56 4.38,3.22C4.57,3.08 4.78,3 5,3H19C19.22,3 19.43,3.08 19.62,3.22C20.05,3.56 20.13,4.19 19.79,4.62L14.03,12H14Z",
  tower:
    "M12,10A2,2 0 0,1 14,12C14,12.5 13.82,12.94 13.53,13.29L16.7,22H14.57L12,14.93L9.43,22H7.3L10.47,13.29C10.18,12.94 10,12.5 10,12A2,2 0 0,1 12,10M12,8A4,4 0 0,0 8,12C8,12.5 8.1,13 8.28,13.46L7.4,15.86C6.53,14.81 6,13.47 6,12A6,6 0 0,1 12,6A6,6 0 0,1 18,12C18,13.47 17.47,14.81 16.6,15.86L15.72,13.46C15.9,13 16,12.5 16,12A4,4 0 0,0 12,8M12,4A8,8 0 0,0 4,12C4,14.36 5,16.5 6.64,17.94L5.92,19.94C3.54,18.11 2,15.23 2,12A10,10 0 0,1 12,2A10,10 0 0,1 22,12C22,15.23 20.46,18.11 18.08,19.94L17.36,17.94C19,16.5 20,14.36 20,12A8,8 0 0,0 12,4Z",
};

const TEXT = {
  en: {
    title: "EnOcean",
    gateways: "Gateways",
    telegrams: "Telegrams",
    live: "Live",
    paused: (n) => (n ? `Paused · ${n} new` : "Paused"),
    pause: "Pause",
    resume: "Resume",
    clear: "Clear list",
    export: "Export visible telegrams (JSON lines)",
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
    add: "Add",
    addHint: "Add this sender as a device",
    duplicate: "repetition",
    teachIn: "Teach-in",
    filterSender: "Show only this sender",
    raw: "Data",
    status: "Status",
    destination: "Destination",
    signal: "Signal",
    gateway: "Gateway",
    time: "Time",
    type: "Type",
    profile: "Sender profile",
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
    perMinute: "per min",
    lastHeard: "last",
    never: "nothing heard yet",
    queue: "Queue",
    unconfirmed: "Unconfirmed",
    devices: "Devices",
    freeSenders: "Free IDs",
    ago: (s) => (s < 60 ? `${s} s ago` : s < 3600 ? `${Math.round(s / 60)} min ago` : `${Math.round(s / 3600)} h ago`),
    since: (s) => (s < 3600 ? `for ${Math.round(s / 60)} min` : `for ${Math.round(s / 3600)} h`),
    cardHint: "Show only this gateway's telegrams",
    viaProxy: (version) => (version ? `via EnOcean Proxy ${version}` : "via EnOcean Proxy"),
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
    telegrams: "Telegramme",
    live: "Live",
    paused: (n) => (n ? `Pausiert · ${n} neu` : "Pausiert"),
    pause: "Anhalten",
    resume: "Fortsetzen",
    clear: "Liste leeren",
    export: "Sichtbare Telegramme exportieren (JSON-Zeilen)",
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
    add: "Anlegen",
    addHint: "Diesen Sender als Gerät anlegen",
    duplicate: "Wiederholung",
    teachIn: "Lerntelegramm",
    filterSender: "Nur diesen Sender zeigen",
    raw: "Daten",
    status: "Status",
    destination: "Ziel",
    signal: "Signal",
    gateway: "Gateway",
    time: "Zeit",
    type: "Typ",
    profile: "Sender-Profil",
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
    perMinute: "pro Min.",
    lastHeard: "zuletzt",
    never: "noch nichts gehört",
    queue: "Warteschlange",
    unconfirmed: "Unbestätigt",
    devices: "Geräte",
    freeSenders: "Freie IDs",
    ago: (s) => (s < 60 ? `vor ${s} s` : s < 3600 ? `vor ${Math.round(s / 60)} min` : `vor ${Math.round(s / 3600)} h`),
    since: (s) => (s < 3600 ? `seit ${Math.round(s / 60)} min` : `seit ${Math.round(s / 3600)} h`),
    cardHint: "Nur die Telegramme dieses Gateways zeigen",
    viaProxy: (version) => (version ? `über EnOcean Proxy ${version}` : "über EnOcean Proxy"),
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
  :host {
    display: block; min-height: 100%; background: var(--primary-background-color);
    color: var(--primary-text-color); font-family: var(--ha-font-family-body, Roboto, sans-serif);
    --accent: var(--primary-color);
    --muted: var(--secondary-text-color);
    --line: var(--divider-color);
    --surface: var(--card-background-color, #fff);
    --soft: var(--secondary-background-color, rgba(127,127,127,.12));
    --ok: var(--success-color, #43a047);
    --bad: var(--error-color, #db4437);
    --warn: var(--warning-color, #ffa600);
    --radius: var(--ha-card-border-radius, 12px);
  }
  * { box-sizing: border-box; }
  svg { width: 20px; height: 20px; fill: currentColor; flex: none; }
  button { font: inherit; color: inherit; background: none; border: 0; cursor: pointer; }
  button:focus-visible, input:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

  .header { position: sticky; top: 0; z-index: 2; display: flex; align-items: center; gap: 4px;
    height: var(--header-height, 56px); padding: 0 12px;
    background: var(--app-header-background-color, var(--primary-color));
    color: var(--app-header-text-color, var(--text-primary-color, #fff)); }
  .header h1 { margin: 0 0 0 4px; font-size: 20px; font-weight: 400; }
  main { max-width: 1280px; margin: 0 auto; padding: 16px; display: grid;
    grid-template-columns: minmax(0, 1fr); gap: 20px; }
  main > section { min-width: 0; }
  h2 { margin: 0 0 10px 4px; font-size: 14px; font-weight: 500; letter-spacing: .02em;
    text-transform: uppercase; color: var(--muted); }

  /* gateway cards */
  .cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 12px; }
  .card { text-align: left; background: var(--surface); border-radius: var(--radius); padding: 14px 16px;
    border: 1px solid var(--line); box-shadow: var(--ha-card-box-shadow, none);
    display: grid; gap: 10px; align-content: start; transition: border-color .15s, box-shadow .15s; }
  .card:hover { border-color: color-mix(in srgb, var(--accent) 50%, var(--line)); }
  .card.selected { border-color: var(--accent); box-shadow: 0 0 0 1px var(--accent) inset; }
  .card .top { display: flex; align-items: center; gap: 8px; min-width: 0; }
  .card .name { font-size: 16px; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .pill { margin-left: auto; flex: none; display: inline-flex; align-items: center; gap: 6px; font-size: 12px;
    padding: 2px 8px; border-radius: 999px; background: var(--soft); color: var(--muted); white-space: nowrap; }
  .pill i { width: 8px; height: 8px; border-radius: 50%; background: currentColor; }
  .pill.ok { color: var(--ok); background: color-mix(in srgb, var(--ok) 14%, transparent); }
  .pill.bad { color: var(--bad); background: color-mix(in srgb, var(--bad) 14%, transparent); }
  .pill.idle { color: var(--warn); background: color-mix(in srgb, var(--warn) 16%, transparent); }
  .card .sub { font-size: 12px; color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin-top: -6px; }
  .rate { display: flex; align-items: baseline; gap: 6px; }
  .rate b { font-size: 26px; font-weight: 400; line-height: 1; }
  .rate span { font-size: 13px; color: var(--muted); }
  .rate .last { margin-left: auto; }
  .stats { display: grid; grid-template-columns: 1fr 1fr; gap: 4px 14px; font-size: 12px; color: var(--muted); }
  .stats > span { display: flex; justify-content: space-between; gap: 8px; }
  .stats b { color: var(--primary-text-color); font-weight: 500; }
  .stats b.warn { color: var(--bad); }
  .hint { color: var(--muted); font-size: 14px; padding: 4px; }
  .proxy { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 10px; font-size: 12px;
    color: var(--muted); padding-top: 8px; border-top: 1px solid var(--line); }
  .proxy .muted { color: var(--muted); }
  .tag.warn { background: color-mix(in srgb, var(--warn) 22%, transparent); color: var(--primary-text-color); }
  .airtime { display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 8px;
    font-size: 12px; color: var(--muted); }
  .airtime b { color: var(--primary-text-color); font-weight: 500; }
  .meter { height: 6px; border-radius: 3px; background: var(--soft); overflow: hidden; }
  .meter i { display: block; height: 100%; background: var(--accent); }
  .meter i.warn { background: var(--warn); }
  .meter i.bad { background: var(--bad); }

  /* telegram section */
  .panel { background: var(--surface); border-radius: var(--radius); border: 1px solid var(--line);
    box-shadow: var(--ha-card-box-shadow, none); overflow: hidden; }
  .bar { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; padding: 12px 12px 12px 16px;
    border-bottom: 1px solid var(--line); }
  .bar h2 { margin: 0; }
  .live { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; padding: 3px 10px;
    border-radius: 999px; color: var(--ok); background: color-mix(in srgb, var(--ok) 14%, transparent); }
  .live i { width: 8px; height: 8px; border-radius: 50%; background: currentColor; animation: pulse 1.6s infinite; }
  .live.paused { color: var(--warn); background: color-mix(in srgb, var(--warn) 16%, transparent); }
  .live.paused i { animation: none; }
  @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: .25; } }
  .spacer { flex: 1; }
  .icon-btn { width: 40px; height: 40px; border-radius: 50%; display: inline-grid; place-items: center; color: var(--muted); }
  .icon-btn:hover { background: var(--soft); color: var(--primary-text-color); }
  .icon-btn[hidden] { display: none; }
  .icon-btn.on { color: var(--accent); }

  .filters { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; padding: 12px 16px; border-bottom: 1px solid var(--line); }
  .search { flex: 1 1 260px; min-width: 0; display: flex; align-items: center; gap: 8px; height: 40px; padding: 0 6px 0 12px;
    border-radius: 999px; background: var(--soft); color: var(--muted); }
  .search input { flex: 1; min-width: 0; height: 100%; border: 0; background: none; outline: none; font: inherit;
    font-size: 14px; color: var(--primary-text-color); }
  .search input::placeholder { color: var(--muted); }
  .search .icon-btn { width: 30px; height: 30px; }
  .search .icon-btn svg { width: 18px; height: 18px; }
  .segmented { display: inline-flex; padding: 3px; border-radius: 999px; background: var(--soft); }
  .segmented button { height: 34px; padding: 0 14px; border-radius: 999px; font-size: 13px; color: var(--muted); white-space: nowrap; }
  .segmented button[aria-pressed="true"] { background: var(--surface); color: var(--primary-text-color);
    box-shadow: 0 1px 3px rgba(0,0,0,.15); }
  .chip { height: 34px; padding: 0 12px; border-radius: 999px; border: 1px solid var(--line); font-size: 13px;
    display: inline-flex; align-items: center; gap: 6px; color: var(--muted); white-space: nowrap; }
  .chip svg { width: 16px; height: 16px; }
  .chip[aria-pressed="true"] { border-color: transparent; color: var(--accent);
    background: color-mix(in srgb, var(--accent) 14%, transparent); }
  .chip.removable { border-color: transparent; color: var(--accent); background: color-mix(in srgb, var(--accent) 14%, transparent); }
  .meta { display: flex; justify-content: space-between; gap: 8px; padding: 8px 16px; font-size: 12px; color: var(--muted); }
  .notice { margin: 8px 16px 0; padding: 10px 12px; border-radius: 8px; font-size: 13px;
    background: color-mix(in srgb, var(--warn) 14%, transparent); display: flex; gap: 8px; align-items: center; }
  .notice[hidden] { display: none; }
  .notice span { flex: 1; }

  /* telegram rows */
  .list { display: block; }
  .row { display: grid; grid-template-columns: 92px 28px minmax(160px, 300px) minmax(0, 1fr) 56px; align-items: center;
    gap: 12px; padding: 7px 12px 7px 16px; border-top: 1px solid var(--line); cursor: pointer; }
  .row:first-child { border-top: 0; }
  .row:hover { background: color-mix(in srgb, var(--soft) 60%, transparent); }
  .row.fresh { animation: fresh 1.2s ease-out; }
  @keyframes fresh { from { background: color-mix(in srgb, var(--accent) 16%, transparent); } }
  .row.dup { opacity: .6; }
  .time { font-family: var(--code-font-family, ui-monospace, monospace); font-size: 13px; }
  .time small { color: var(--muted); }
  .dir { width: 28px; height: 28px; border-radius: 50%; display: grid; place-items: center; color: var(--muted); background: var(--soft); }
  .dir svg { width: 16px; height: 16px; }
  .dir.tx { color: var(--accent); background: color-mix(in srgb, var(--accent) 14%, transparent); }
  .who { min-width: 0; }
  .who .line1 { display: flex; align-items: center; gap: 8px; min-width: 0; }
  .who .name { font-size: 14px; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .who .name.unknown { font-weight: 400; font-style: italic; color: var(--muted); }
  .who .line2 { font-size: 12px; color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin-top: 2px; }
  .mono { font-family: var(--code-font-family, ui-monospace, monospace); }
  .tag { flex: none; font-size: 11px; padding: 1px 8px; border-radius: 999px; background: var(--soft); color: var(--muted); }
  .tag.teach { background: color-mix(in srgb, var(--warn) 22%, transparent); color: var(--primary-text-color); }
  .add { flex: none; display: inline-flex; align-items: center; gap: 2px; height: 26px; padding: 0 10px 0 6px; border-radius: 999px;
    font-size: 12px; font-weight: 500; color: var(--text-primary-color, #fff); background: var(--accent); }
  .add svg { width: 16px; height: 16px; }
  .values { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; min-width: 0; }
  .value { font-size: 13px; padding: 2px 10px; border-radius: 999px; background: var(--soft); white-space: nowrap; }
  .value span { color: var(--muted); }
  .value b { font-weight: 500; }
  .raw { font-size: 12px; color: var(--muted); }
  .end { display: flex; align-items: center; justify-content: flex-end; gap: 6px; color: var(--muted); }
  .end .chev { transition: transform .15s; }
  .expand { width: 32px; height: 32px; border-radius: 50%; display: inline-grid; place-items: center; color: var(--muted); }
  .expand:hover { background: var(--soft); }
  .expand[aria-expanded="true"] .chev { transform: rotate(180deg); }
  .bars { width: 18px; height: 14px; }
  .bars rect { fill: var(--line); }
  .bars rect.on { fill: var(--muted); }
  .details { grid-column: 1 / -1; display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 10px 16px; margin: 4px 0 4px 132px; padding: 12px; border-radius: 8px; background: var(--soft); cursor: default; }
  .details div { min-width: 0; }
  .details dt { font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: .03em; }
  .details dd { margin: 2px 0 0; font-size: 13px; overflow-wrap: anywhere; }
  .details .actions { grid-column: 1 / -1; display: flex; flex-wrap: wrap; gap: 8px; }

  .empty { display: grid; justify-items: center; gap: 6px; padding: 48px 16px; text-align: center; color: var(--muted); }
  .empty svg { width: 48px; height: 48px; opacity: .5; }
  .empty b { color: var(--primary-text-color); font-weight: 500; font-size: 16px; }
  .empty .chip { margin-top: 8px; }

  @media (max-width: 760px) {
    main { padding: 12px 8px; gap: 16px; }
    .row { grid-template-columns: 28px minmax(0, 1fr) auto; gap: 4px 10px; padding: 9px 12px; }
    .row .time { grid-column: 3; grid-row: 1; font-size: 12px; text-align: right; }
    .row .dir { grid-column: 1; grid-row: 1 / span 2; align-self: start; }
    .row .who { grid-column: 2; grid-row: 1; }
    .row .values { grid-column: 2 / -1; grid-row: 2; justify-content: flex-start; }
    .row .end { display: none; }
    .details { margin-left: 0; }
    .filters .segmented { order: 3; }
    .filters .chip { padding: 0 10px; font-size: 12px; flex: 1 1 auto; justify-content: center; }
    .who .line1 { flex-wrap: wrap; row-gap: 4px; }
    .who .name { flex: 1 1 100%; }
    .cards { grid-auto-flow: column; grid-template-columns: none; grid-auto-columns: 86%;
      overflow-x: auto; scroll-snap-type: x mandatory; padding-bottom: 4px; }
    .card { scroll-snap-align: start; }
  }
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

function rowKey(r) {
  return `${r.time}|${r.dir}|${r.sender}|${r.data}|${r.gateway}`;
}

class EnOceanEltakoPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._rows = [];
    this._pending = [];
    this._paused = false;
    this._filter = { gateway: "", text: "", dir: "", repeats: false, unknown: false };
    this._gateways = [];
    this._expanded = new Set();
    this._fresh = new Set();
    this._unsub = null;
    this._frame = null;
    this._timer = null;
    this._onKey = (e) => this._keydown(e);
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
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
    if (this._hass && !this._unsub) this._subscribe();
  }

  disconnectedCallback() {
    window.removeEventListener("keydown", this._onKey);
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
      <div class="header"><ha-menu-button></ha-menu-button><h1>${esc(t.title)}</h1></div>
      <main>
        <section>
          <h2>${esc(t.gateways)}</h2>
          <div class="cards" id="cards"></div>
        </section>
        <section class="panel" aria-label="${esc(t.telegrams)}">
          <div class="bar">
            <h2>${esc(t.telegrams)}</h2>
            <span class="live" id="live"><i></i><span></span></span>
            <span class="spacer"></span>
            <button class="icon-btn" id="pause"></button>
            <button class="icon-btn" id="export" title="${esc(t.export)}" aria-label="${esc(t.export)}">${svg(ICON.download)}</button>
            <button class="icon-btn" id="clear" title="${esc(t.clear)}" aria-label="${esc(t.clear)}">${svg(ICON.clear)}</button>
          </div>
          <div class="filters">
            <label class="search" title="${esc(t.searchKey)}">
              ${svg(ICON.search)}
              <input id="text" type="search" placeholder="${esc(t.search)}" aria-label="${esc(t.search)}" autocomplete="off">
              <button class="icon-btn" id="clearText" aria-label="✕" hidden>${svg(ICON.close)}</button>
            </label>
            <div class="segmented" role="group" id="dir">
              <button data-dir="" aria-pressed="true">${esc(t.dirAll)}</button>
              <button data-dir="rx" aria-pressed="false">${esc(t.rx)}</button>
              <button data-dir="tx" aria-pressed="false">${esc(t.tx)}</button>
            </div>
            <button class="chip" id="unknown" aria-pressed="false">${esc(t.unknownOnly)}</button>
            <button class="chip" id="repeats" aria-pressed="false">${esc(t.repeats)}</button>
            <span id="gatewayChip"></span>
          </div>
          <div class="notice" id="notice" hidden><span></span><button class="icon-btn" id="closeNotice" aria-label="✕">${svg(ICON.close)}</button></div>
          <div class="meta"><span id="count"></span></div>
          <div class="list" id="list"></div>
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
    $("unknown").addEventListener("click", () => this._set("unknown", !this._filter.unknown));
    $("repeats").addEventListener("click", () => this._set("repeats", !this._filter.repeats));
    $("gatewayChip").addEventListener("click", () => this._set("gateway", ""));
    $("pause").addEventListener("click", () => this._togglePause());
    $("clear").addEventListener("click", () => {
      this._rows = [];
      this._pending = [];
      this._expanded.clear();
      this._render();
    });
    $("export").addEventListener("click", () => this._export());
    $("closeNotice").addEventListener("click", () => this._notice(""));
    $("cards").addEventListener("click", (e) => {
      const card = e.target.closest(".card");
      if (card) this._set("gateway", this._filter.gateway === card.dataset.entry ? "" : card.dataset.entry);
    });
    $("list").addEventListener("click", (e) => this._listClick(e));
    this._renderBar();
    this._renderCards();
    this._render();
  }

  _keydown(e) {
    const input = this.shadowRoot.getElementById("text");
    if (e.key === "/" && input && this.shadowRoot.activeElement !== input && !e.composedPath()[0]?.matches?.("input, textarea")) {
      e.preventDefault();
      input.focus();
    } else if (e.key === "Escape" && this.shadowRoot.activeElement === input) {
      this._setText("");
      input.blur();
    }
  }

  // ---- data --------------------------------------------------------------------------------

  async _subscribe() {
    this._unsub = this._hass.connection.subscribeMessage((row) => this._add(row), {
      type: "enocean_eltako/telegrams/subscribe",
      history: HISTORY,
    });
    await this._refreshStatus();
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
    this._renderCards();
  }

  _add(row) {
    if (this._paused) {
      this._pending.push(row);
      this._renderBar();
      return;
    }
    this._rows.unshift(row);
    if (this._rows.length > MAX_ROWS) this._rows.length = MAX_ROWS;
    if (this._initialised) this._fresh.add(rowKey(row));
    this._schedule();
  }

  _schedule() {
    if (this._frame) return;
    this._frame = requestAnimationFrame(() => {
      this._frame = null;
      this._render();
      this._initialised = true;
    });
  }

  _set(key, value) {
    this._filter[key] = value;
    if (key === "gateway") this._renderCards();
    this._renderFilters();
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
    if (!this._paused) {
      this._rows = [...this._pending.reverse(), ...this._rows].slice(0, MAX_ROWS);
      this._pending = [];
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
    const only = e.target.closest("[data-only]");
    if (only) {
      this._setText(only.dataset.only);
      return;
    }
    if (e.target.closest(".reset")) {
      this._resetFilters();
      return;
    }
    if (e.target.closest(".details")) return;
    const row = e.target.closest(".row");
    if (row) this._toggleRow(row.dataset.key);
  }

  _resetFilters() {
    this._filter = { gateway: "", text: "", dir: "", repeats: false, unknown: false };
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

  _notice(text) {
    const notice = this.shadowRoot.getElementById("notice");
    notice.hidden = !text;
    notice.querySelector("span").textContent = text;
  }

  _visible() {
    const f = this._filter;
    const text = f.text.toLowerCase();
    const compact = text.replace(/[-:\s]/g, "");
    return this._rows.filter(
      (r) =>
        (!f.gateway || r.gateway === f.gateway) &&
        (!f.dir || r.dir === f.dir) &&
        (f.repeats || !r.duplicate) &&
        !(f.unknown && (r.device || r.dir === "tx")) &&
        (!text ||
          [r.device, r.data, r.teach_in, r.profile, r.gateway_name].some((v) => v && String(v).toLowerCase().includes(text)) ||
          (compact && String(r.sender).replace(/-/g, "").toLowerCase().includes(compact)))
    );
  }

  _export() {
    const lines = this._visible().slice().reverse().map((r) => JSON.stringify(r)).join("\n");
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
    live.querySelector("span").textContent = this._paused ? t.paused(this._pending.length) : t.live;
    const pause = this.shadowRoot.getElementById("pause");
    const label = this._paused ? t.resume : t.pause;
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
    const gw = this._gateways.find((g) => g.entry_id === f.gateway);
    $("gatewayChip").innerHTML = gw
      ? `<button class="chip removable" title="${esc(this._t.allGateways)}">${svg(ICON.filter)}${esc(gw.title)}${svg(ICON.close)}</button>`
      : "";
  }

  _renderCards() {
    const t = this._t;
    const cards = this.shadowRoot.getElementById("cards");
    if (!cards) return;
    if (!this._gateways.length) {
      cards.innerHTML = `<div class="hint">${esc(t.noGateways)}</div>`;
      return;
    }
    const now = Date.now() / 1000;
    cards.innerHTML = this._gateways
      .map((gw) => {
        let pill = ["", t.notLoaded];
        if (gw.loaded) {
          if (gw.connected) pill = ["ok", t.connected];
          else if (gw.on_demand) pill = ["idle", t.onDemand];
          else pill = ["bad", gw.disconnected_since ? `${t.disconnected} ${t.since(Math.round(now - gw.disconnected_since))}` : t.disconnected];
        }
        const last = gw.last_telegram != null ? `${t.lastHeard} ${t.ago(Math.max(0, Math.round(now - gw.last_telegram)))}` : t.never;
        const perMinute = this._perMinute(gw.entry_id);
        const rate = perMinute < 10 ? perMinute.toFixed(1).replace(/\.0$/, "") : String(Math.round(perMinute));
        const stat = (label, value, warn) => `<span>${esc(label)} <b class="${warn ? "warn" : ""}">${esc(value)}</b></span>`;
        const body = gw.loaded
          ? `<div class="rate"><b>${esc(rate)}</b><span>${esc(t.perMinute)}</span><span class="last">${esc(last)}</span></div>
             <div class="stats">${stat(t.devices, gw.devices ?? "–")}${stat(t.freeSenders, gw.free_senders ?? "–", gw.free_senders === 0)}${stat(t.queue, gw.queue ?? "–", gw.queue > 5)}${stat(t.unconfirmed, gw.unconfirmed ?? "–", gw.unconfirmed > 0)}</div>`
          : "";
        const selected = this._filter.gateway === gw.entry_id;
        const proxy = gw.via_proxy ? this._proxyLine(gw) : "";
        const sub = [gw.model !== gw.title ? gw.model : "", gw.base_id, gw.connection].filter(Boolean).join(" · ");
        return `<button class="card${selected ? " selected" : ""}" data-entry="${esc(gw.entry_id)}" title="${esc(t.cardHint)}" aria-pressed="${selected}">
          <div class="top"><span class="name">${esc(gw.title)}</span><span class="pill ${pill[0]}"><i></i>${esc(pill[1])}</span></div>
          <div class="sub" title="${esc(sub)}">${esc(sub)}</div>
          ${body}${proxy}
        </button>`;
      })
      .join("");
  }

  _proxyLine(gw) {
    const t = this._t;
    const p = gw.proxy;
    if (!p) {
      return `<div class="proxy"><span class="tag">${esc(t.viaProxy(""))}</span><span class="muted">${esc(t.proxyUnreachable)}</span></div>`;
    }
    const share = Number(p.duty_of_limit ?? 0);
    const level = share >= 80 ? "bad" : share >= 50 ? "warn" : "";
    return `<div class="proxy">
        <span class="tag">${esc(t.viaProxy(p.version))}</span>
        <span>${esc(t.programs(p.programs ?? 0))}</span>
        ${p.exclusive_peer ? `<span class="tag warn">${esc(t.alone(p.exclusive_peer))}</span>` : ""}
      </div>
      <div class="airtime" title="${esc(t.airtimeHint)}">
        <span>${esc(t.airtime)}</span>
        <span class="meter" role="meter" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${share}" aria-label="${esc(t.airtimeHint)}"><i class="${level}" style="width:${Math.min(100, share)}%"></i></span>
        <b>${esc(share.toLocaleString(this._hass.language, { maximumFractionDigits: 1 }))} %</b>
      </div>`;
  }

  _perMinute(gateway) {
    // received telegrams of the last minute, from the list itself (repetitions included)
    const since = Date.now() - 60000;
    let count = 0;
    for (const r of [...this._pending.slice().reverse(), ...this._rows]) {
      if (r.gateway !== gateway || r.dir !== "rx") continue;
      if (Date.parse(r.time) < since) break;
      count += 1;
    }
    return count;
  }

  _value(value) {
    if (value === true) return this._t.on;
    if (value === false) return this._t.off;
    if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toLocaleString(this._hass.language, { maximumFractionDigits: 2 });
    return String(value);
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
      (unknown ? `<button class="add" data-id="${esc(r.sender)}" title="${esc(t.addHint)}">${svg(ICON.plus)}${esc(t.add)}</button>` : "") +
      (r.teach_in ? `<span class="tag teach">${esc(t.teachIn)} ${esc(r.teach_in)}</span>` : "");
    const type = RORG[r.rorg] || r.rorg;
    const line2 = [
      `<span class="mono">${esc(r.sender)}</span>`,
      r.profile ? esc(r.profile) : "",
      this._gateways.length > 1 ? esc(r.gateway_name) : "",
      esc(type),
    ].filter(Boolean).join(" · ");
    const fields = r.fields || (r.values ? Object.entries(r.values).map(([label, value]) => ({ label, value })) : null);
    const values = fields && fields.length
      ? fields
          .map((f) =>
            f.label === "on" || f.label === "state"
              ? `<span class="value"><b>${esc(this._value(f.value))}</b></span>`
              : `<span class="value"><span>${esc(t.fields[f.label] || f.label.replace(/_/g, " "))}</span> <b>${esc(this._value(f.value))}</b>${f.unit ? ` ${esc(f.unit)}` : ""}</span>`
          )
          .join("")
      : `<span class="raw mono">${esc(r.data)}</span>`;
    const details = expanded
      ? `<dl class="details">
          <div><dt>${esc(t.time)}</dt><dd class="mono">${esc(time.toLocaleString(this._hass.language))}.${ms}</dd></div>
          <div><dt>${esc(t.gateway)}</dt><dd>${esc(r.gateway_name)}</dd></div>
          <div><dt>${esc(t.type)}</dt><dd>${esc(type)} (${esc(r.rorg)})</dd></div>
          <div><dt>${esc(t.raw)}</dt><dd class="mono">${esc(r.data)}</dd></div>
          <div><dt>${esc(t.status)}</dt><dd class="mono">${esc(r.status)}</dd></div>
          <div><dt>${esc(t.destination)}</dt><dd class="mono">${esc(r.destination)}</dd></div>
          <div><dt>${esc(t.signal)}</dt><dd>${r.dbm != null ? `${esc(r.dbm)} dBm` : "–"}</dd></div>
          ${r.profile ? `<div><dt>${esc(t.profile)}</dt><dd>${esc(r.profile)}</dd></div>` : ""}
          <div class="actions"><button class="chip" data-only="${esc(r.sender)}">${svg(ICON.filter)}${esc(t.filterSender)}</button></div>
        </dl>`
      : "";
    const classes = ["row", r.duplicate ? "dup" : "", this._fresh.has(key) ? "fresh" : ""].filter(Boolean).join(" ");
    return `<div class="${classes}" data-key="${esc(key)}">
      <span class="time">${esc(clock)}<small>.${ms}</small></span>
      <span class="dir ${r.dir}" title="${esc(r.dir === "rx" ? t.rx : t.tx)}">${svg(r.dir === "rx" ? ICON.rx : ICON.tx)}</span>
      <div class="who" title="${esc([r.device, r.sender, r.gateway_name].filter(Boolean).join(" · "))}"><div class="line1">${name}${tags}</div><div class="line2">${line2}</div></div>
      <div class="values">${extra}${values}</div>
      <div class="end">${bars(r.dbm)}<button class="expand" aria-expanded="${expanded}" aria-label="${esc(t.details)}" title="${esc(t.details)}">${svg(ICON.chevron, "chev")}</button></div>
      ${details}
    </div>`;
  }

  _render() {
    const t = this._t;
    const list = this.shadowRoot.getElementById("list");
    if (!list) return;
    const rows = this._visible();
    this.shadowRoot.getElementById("count").textContent = t.count(rows.length, this._rows.length);
    if (!rows.length) {
      const filtered = this._rows.length > 0;
      list.innerHTML = `<div class="empty">${svg(ICON.tower)}<b>${esc(filtered ? t.noMatchTitle : t.emptyTitle)}</b><span>${esc(filtered ? t.noMatchText : t.emptyText)}</span>${
        filtered ? `<button class="chip reset">${esc(t.resetFilters)}</button>` : ""
      }</div>`;
    } else {
      list.innerHTML = rows.map((r) => this._row(r)).join("");
    }
    this._fresh.clear();
  }
}

customElements.define("enocean-eltako-monitor", EnOceanEltakoPanel);
