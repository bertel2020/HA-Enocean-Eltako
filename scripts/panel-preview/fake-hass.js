// A stand-in for Home Assistant: the hass object the panel gets, with sample gateways,
// telegrams, sender pools and takeover data. Used by the preview page (index.html) and by the
// CI render check (scripts/check_panel_render.mjs).
//
// Options (query string of the preview page): lang=en|de, dark, primary (own primary colour),
// two (a second gateway), hide (an unknown sender hidden from discovery), skew=<s> (server clock
// ahead of the browser), empty (no gateways and no telegrams).

export function fakeHass(params = new URLSearchParams()) {
  const now = Date.now() / 1000;
  const empty = params.has("empty");
  const gateway = {
    entry_id: "gw1", title: "FAM-USB Keller", model: "Eltako FAM-USB", base_id: "FF-B7-44-80", loaded: true, connected: true,
    on_demand: false, connection: "tcp 127.0.0.1:9100", per_minute: 4, last_telegram: now - 3, queue: 0, unconfirmed: 0,
    devices: 3, free_senders: 120, hidden: params.has("hide") ? ["01-99-88-77"] : [],
    server_time: now + Number(params.get("skew") || 0), disconnected_since: null, proxy: null, via_proxy: false,
    radio_devices: [
      { id: "05-10-A2-B3", device: "Licht Diele", last_seen: now - 30, silent: false, ha_device: "dev123", area: "Flur", entities: 3, eep: "M5-38-08:eltako", model: "FSR14" },
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
    { time: at(49.8), dir: "rx", sender: "05-10-A2-B3", rorg: "F6", data: "70", status: "30", destination: "FF-FF-FF-FF", dbm: -62, gateway: "gw1", gateway_name: "FAM-USB Keller", device: "Licht Diele", ha_device: "dev123", device_key: "sub1", eep: "M5-38-08:eltako", model: "FSR14", fields: [{ label: "on", value: true }] },
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
          return { available: !empty };
        case "enocean_eltako/sender_pools":
          return empty ? [] : [pool];
        case "enocean_eltako/takeover/preview":
          return { devices: [{ id: "05-10-A2-B3", name: "Licht Diele", ready: true, area: "Flur" }], old_active: true };
        case "enocean_eltako/takeover/mapping":
          return { rows: [], old_active: true };
        case "enocean_eltako/send":
          return { result: "sent" };
        default:
          throw { code: "unknown_command", message: msg.type };
      }
    },
  };
  // a new telegram as the server would send it
  return { hass, sent, listeners, push: (row) => push({ gateway: "gw1", gateway_name: "FAM-USB Keller", destination: "FF-FF-FF-FF", ...row }) };
}
