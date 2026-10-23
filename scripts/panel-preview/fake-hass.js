// A stand-in for Home Assistant: the hass object the panel gets, with sample gateways,
// telegrams, sender pools and takeover data. Used by the preview page (index.html) and by the
// CI render check (scripts/check_panel_render.mjs).
//
// Options (query string of the preview page): lang=en|de, dark, primary (own primary colour),
// two (a second gateway), hide (an unknown sender hidden from discovery), skew=<s> (server clock
// ahead of the browser), empty (no gateways and no telegrams).

// the takeover view: two devices to take over, one already set up and still in use
const none = { automation: [], script: [], scene: [], dashboard: [] };
const takeoverDevices = [
  { id: "05-10-A2-B3", name: "Licht Diele", old: "light A5-38-08", ready: true, area: "Flur", labels: [], carry: ["area", "voice"], used: 2,
    entities: [{ old: "light.eltako_0510a2b3", new: "light.licht_diele" }, { old: "sensor.eltako_0510a2b3_id", new: "sensor.licht_diele_enocean_id" }],
    places: ["automation:Flur Bewegung", "dashboard:Übersicht"] },
  { id: "05-10-A2-B4", name: "Rollladen Süd", old: "cover G5-3F-7F", ready: true, area: "Wohnzimmer", labels: ["Beschattung"], carry: ["area", "labels", "names"], used: 0,
    entities: [{ old: "cover.eltako_0510a2b4", new: "cover.rollladen_sud" }, { old: "sensor.eltako_0510a2b4_power", new: null }], places: [] },
  { id: "01-90-8C-14", name: "Zwischenstecker", old: "switch M5-38-08", ready: false, reason: "takeover_exists", area: "Küche", labels: [], carry: ["area"], used: 1 },
];
const takeoverRows = [
  { device: "Zwischenstecker", id: "01-90-8C-14", area: "Küche", taken: true, primary: true, old: "switch.eltako_01908c14", new: "switch.zwischenstecker", restored: false,
    usage: { ...none, automation: [{ name: "Kaffee aus", path: "/config/automation/edit/1" }], dashboard: [{ name: "Küche", path: "/lovelace" }] } },
  { device: "Zwischenstecker", id: "01-90-8C-14", area: "Küche", taken: true, primary: false, old: "sensor.eltako_01908c14_id", new: "sensor.zwischenstecker_enocean_id", restored: false, usage: none },
];
// what the integration keeps per device set up: the report
const takeoverStored = {
  "01-90-8C-14": { name: "Zwischenstecker", taken_at: "2026-10-12T09:30:00+00:00", carried: ["area", "labels"],
    old: { config: "switch M5-38-08", name: "Zwischenstecker", senders: ["FF-B7-44-B2"], device_name: "Kaffeemaschine", area: "Küche", labels: ["Morgens"] } },
};

export function fakeHass(params = new URLSearchParams()) {
  const now = Date.now() / 1000;
  const empty = params.has("empty");
  const gateway = {
    entry_id: "gw1", title: "FAM-USB Keller", model: "Eltako FAM-USB", base_id: "FF-B7-44-80", loaded: true, connected: true,
    on_demand: false, connection: "tcp 127.0.0.1:9100", per_minute: 4, last_telegram: now - 3, queue: 0, unconfirmed: 0,
    devices: 3, free_senders: 120, senders: [{ id: "FF-B7-44-81", device: "Licht Diele", profile: "central" }], hidden: params.has("hide") ? ["01-99-88-77"] : [],
    server_time: now + Number(params.get("skew") || 0), disconnected_since: null, proxy: null, via_proxy: false,
    radio_devices: [
      { id: "05-10-A2-B3", device: "Licht Diele", last_seen: now - 30, silent: false, ha_device: "dev123", area: "Flur", entities: 3, eep: "M5-38-08:eltako", model: "FSR14-4x", models: [],
        key: "sub1", teach: [{ profile: "central", id: "FF-B7-44-81", ute: false }, { profile: "rocker", id: "FF-B7-44-83", ute: false }] },
      { id: "05-10-A2-B4", device: "Dimmer Flur", last_seen: now - 90, silent: false, ha_device: "dev124", area: "Flur", entities: 1, eep: "A5-38-08:eltako", model: "", models: ["FUD14", "FUD61", "FD62"], key: "sub2", teach: [] },
      { id: "05-11-11-11", device: "Temperatur Bad", last_seen: now - 200000, silent: true, ha_device: "dev456", area: "Bad", entities: 2, eep: "A5-02-05" },
      { id: "05-22-22-22", device: "Fensterkontakt Küche", last_seen: null, silent: false, area: "Küche", entities: 1, eep: "D5-00-01" },
    ],
  };
  const gateways = empty ? [] : [gateway];
  if (params.has("two") && !empty) {
    gateways.push({ ...gateway, entry_id: "gw2", title: "MGW Garage", base_id: "FF-AA-00-80", radio_devices: [], connected: false, disconnected_since: now - 4000 });
  }
  const at = (s) => new Date(Date.now() - s * 1000).toISOString();
  const history = empty ? [] : [
    { time: at(50), dir: "tx", sender: "FF-B7-44-81", rorg: "F6", data: "70", status: "30", destination: "FF-FF-FF-FF", dbm: null, gateway: "gw1", gateway_name: "FAM-USB Keller", device: "Licht Diele", device_key: "sub1", profile: "central" },
    { time: at(49.8), dir: "rx", sender: "05-10-A2-B3", rorg: "F6", data: "70", status: "30", destination: "FF-FF-FF-FF", dbm: -62, gateway: "gw1", gateway_name: "FAM-USB Keller", device: "Licht Diele", ha_device: "dev123", device_key: "sub1", eep: "M5-38-08:eltako", model: "FSR14-4x", fields: [{ label: "on", value: true }] },
    { time: at(30), dir: "rx", sender: "05-10-A2-B4", rorg: "A5", data: "0264A808", status: "00", destination: "FF-FF-FF-FF", dbm: -70, gateway: "gw1", gateway_name: "FAM-USB Keller", device: "Dimmer Flur", ha_device: "dev124", device_key: "sub2", eep: "A5-38-08:eltako", models: ["FUD14", "FUD61", "FD62"], fields: [{ label: "dim", value: 50 }] },
    { time: at(20), dir: "rx", sender: "01-99-88-77", rorg: "A5", data: "0064A808", status: "00", destination: "FF-FF-FF-FF", dbm: -88, gateway: "gw1", gateway_name: "FAM-USB Keller", candidates: ["A5-02-05", "A5-10-06"] },
  ];
  const pool = {
    id: "gw1", kind: "radio", title: "FAM-USB Keller", size: 128, free: 119, first: 0xffb74480, unavailable: [0xffb74490, 0xffb74491],
    start: "FF-B7-44-80", end: "FF-B7-44-FF", next_free: "FF-B7-44-82",
    rows: [
      { id: "FF-B7-44-81", decimal: 0xffb74481, device: "Licht Diele", profile: "central", state: "assigned" },
      { id: "FF-B7-44-85", decimal: 0xffb74485, device: null, ref: "abc", profile: "central", state: "blocked" },
    ],
  };
  const listeners = {};
  const sent = []; // websocket commands the panel sent (send, teach-in ...), for the checks
  let push = () => {};
  const hass = {
    language: params.get("lang") || "de",
    locale: { language: params.get("lang") || "de", number_format: "language", time_format: "language", time_zone: "local" },
    config: { time_zone: "Europe/Berlin" },
    themes: { darkMode: params.has("dark"), theme: "default" },
    selectedTheme: params.has("primary") ? { primaryColor: "#e91e63" } : null,
    connection: {
      connected: true,
      addEventListener: (event, callback) => (listeners[event] = callback),
      removeEventListener: () => {},
      subscribeMessage: (callback) => {
        for (const row of history) callback({ ...row, history: true });
        push = callback;
        return Promise.resolve(() => {});
      },
    },
    callWS: async (msg) => {
      sent.push(msg);
      switch (msg.type) {
        case "enocean_eltako/gateways":
          return gateways;
        case "enocean_eltako/takeover/status":
          return { available: !empty && !params.has("closed"), report: !empty, closed: params.has("closed") };
        case "enocean_eltako/sender_pools":
          return empty ? [] : [pool];
        case "enocean_eltako/takeover/preview":
          return { devices: takeoverDevices, old_active: true };
        case "enocean_eltako/takeover/mapping":
          return { rows: takeoverRows, devices: takeoverStored, missing: { "01-90-8C-14": ["area", "names"] }, old_active: true, old_entities: true };
        case "enocean_eltako/takeover/restore":
          return { restored: 2, blocked: 0 };
        case "enocean_eltako/takeover/close":
          return {};
        case "enocean_eltako/takeover/run":
        case "enocean_eltako/takeover/carry":
          return { count: 1, carried: 1, skipped: [] };
        case "enocean_eltako/send":
          return { result: "sent" };
        case "enocean_eltako/teach_in":
          return { ute: false, window: 0 };
        default:
          throw { code: "unknown_command", message: msg.type };
      }
    },
  };
  // a new telegram as the server would send it
  return { hass, sent, listeners, push: (row) => push({ gateway: "gw1", gateway_name: "FAM-USB Keller", destination: "FF-FF-FF-FF", ...row }) };
}
