// Pieces the panel's files share: icons, HTML escaping, the list size.

export const MAX_ROWS = 1000; // telegrams the monitor keeps

// Material Design Icons (Apache 2.0), inlined so the panel needs no icon loading
export const ICON = {
  rx: "M20,5.41L18.59,4L7,15.59V9H5V19H15V17H8.41L20,5.41Z",
  tx: "M5,17.59L15.59,7H9V5H19V15H17V8.41L6.41,19L5,17.59Z",
  search:
    "M9.5,3A6.5,6.5 0 0,1 16,9.5C16,11.11 15.41,12.59 14.44,13.73L14.71,14H15.5L20.5,19L19,20.5L14,15.5V14.71L13.73,14.44C12.59,15.41 11.11,16 9.5,16A6.5,6.5 0 0,1 3,9.5A6.5,6.5 0 0,1 9.5,3M9.5,5C7,5 5,7 5,9.5C5,12 7,14 9.5,14C12,14 14,12 14,9.5C14,7 12,5 9.5,5Z",
  pause: "M14,19H18V5H14M6,19H10V5H6V19Z",
  label: "M17.63,5.84C17.27,5.33 16.67,5 16,5L5,5.01C3.9,5.01 3,5.9 3,7V17C3,18.1 3.9,18.99 5,18.99L16,19C16.67,19 17.27,18.67 17.63,18.16L22,12L17.63,5.84Z",
  pin: "M12,11.5A2.5,2.5 0 0,1 9.5,9A2.5,2.5 0 0,1 12,6.5A2.5,2.5 0 0,1 14.5,9A2.5,2.5 0 0,1 12,11.5M12,2A7,7 0 0,0 5,9C5,14.25 12,22 12,22C12,22 19,14.25 19,9A7,7 0 0,0 12,2Z",
  play: "M8,5.14V19.14L19,12.14L8,5.14Z",
  clear:
    "M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19M8,9H16V19H8V9M15.5,4L14.5,3H9.5L8.5,4H5V6H19V4H15.5Z",
  send: "M2,21L23,12L2,3V10L17,12L2,14V21Z",
  copy: "M19,21H8V7H19M19,5H8A2,2 0 0,0 6,7V21A2,2 0 0,0 8,23H19A2,2 0 0,0 21,21V7A2,2 0 0,0 19,5M16,1H4A2,2 0 0,0 2,3V17H4V3H16V1Z",
  download: "M5,20H19V18H5M19,9H15V3H9V9H5L12,16L19,9Z",
  close:
    "M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z",
  more: "M12,16A2,2 0 0,1 14,18A2,2 0 0,1 12,20A2,2 0 0,1 10,18A2,2 0 0,1 12,16M12,10A2,2 0 0,1 14,12A2,2 0 0,1 12,14A2,2 0 0,1 10,12A2,2 0 0,1 12,10M12,4A2,2 0 0,1 14,6A2,2 0 0,1 12,8A2,2 0 0,1 10,6A2,2 0 0,1 12,4Z",
  open: "M14,3V5H17.59L7.76,14.83L9.17,16.24L19,6.41V10H21V3M19,19H5V5H12V3H5C3.89,3 3,3.9 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19V12H19V19Z",
  hide: "M11.83,9L15,12.16C15,12.11 15,12.05 15,12A3,3 0 0,0 12,9C11.94,9 11.89,9 11.83,9M7.53,9.8L9.08,11.35C9.03,11.56 9,11.77 9,12A3,3 0 0,0 12,15C12.22,15 12.44,14.97 12.65,14.92L14.2,16.47C13.53,16.8 12.79,17 12,17A5,5 0 0,1 7,12C7,11.21 7.2,10.47 7.53,9.8M2,4.27L4.28,6.55L4.73,7C3.08,8.3 1.78,10 1,12C2.73,16.39 7,19.5 12,19.5C13.55,19.5 15.03,19.2 16.38,18.66L16.81,19.08L19.73,22L21,20.73L3.27,3M12,7A5,5 0 0,1 17,12C17,12.64 16.87,13.26 16.64,13.82L19.57,16.75C21.21,15.5 22.5,13.88 23,12C21.27,7.61 17,4.5 12,4.5C10.6,4.5 9.26,4.75 8,5.2L10.17,7.35C10.74,7.13 11.35,7 12,7Z",
  plus: "M19,13H13V19H11V13H5V11H11V5H13V11H19V13Z",
  check: "M21,7L9,19L3.5,13.5L4.91,12.09L9,16.17L19.59,5.59L21,7Z",
  list: "M7,5H21V7H7V5M7,13V11H21V13H7M4,4.5A1.5,1.5 0 0,1 5.5,6A1.5,1.5 0 0,1 4,7.5A1.5,1.5 0 0,1 2.5,6A1.5,1.5 0 0,1 4,4.5M4,10.5A1.5,1.5 0 0,1 5.5,12A1.5,1.5 0 0,1 4,13.5A1.5,1.5 0 0,1 2.5,12A1.5,1.5 0 0,1 4,10.5M7,19V17H21V19H7M4,16.5A1.5,1.5 0 0,1 5.5,18A1.5,1.5 0 0,1 4,19.5A1.5,1.5 0 0,1 2.5,18A1.5,1.5 0 0,1 4,16.5Z",
  teach: "M12,3L1,9L12,15L21,10.09V17H23V9M5,13.18V17.18L12,21L19,17.18V13.18L12,17L5,13.18Z",
  signal: "M3,21H6V18H3M8,21H11V14H8M13,21H16V9H13M18,21H21V3H18V21Z",
  chevron: "M7.41,8.58L12,13.17L16.59,8.58L18,10L12,16L6,10L7.41,8.58Z",
  first: "M18.41,16.59L13.82,12L18.41,7.41L17,6L11,12L17,18L18.41,16.59M6,6H8V18H6V6Z",
  prev: "M15.41,16.58L10.83,12L15.41,7.41L14,6L8,12L14,18L15.41,16.58Z",
  next: "M8.59,16.58L13.17,12L8.59,7.41L10,6L16,12L10,18L8.59,16.58Z",
  last: "M5.59,7.41L10.18,12L5.59,16.59L7,18L13,12L7,6L5.59,7.41M16,6H18V18H16V6Z",
  filter: "M14,12V19.88C14.04,20.18 13.94,20.5 13.71,20.71C13.32,21.1 12.69,21.1 12.3,20.71L10.29,18.7C10.06,18.47 9.96,18.16 10,17.87V12H9.97L4.21,4.62C3.87,4.19 3.95,3.56 4.38,3.22C4.57,3.08 4.78,3 5,3H19C19.22,3 19.43,3.08 19.62,3.22C20.05,3.56 20.13,4.19 19.79,4.62L14.03,12H14Z",
  bug: "M14,12H10V10H14M14,16H10V14H14M20,8H17.19C16.74,7.22 16.12,6.55 15.37,6.04L17,4.41L15.59,3L13.42,5.17C12.96,5.06 12.5,5 12,5C11.5,5 11.04,5.06 10.59,5.17L8.41,3L7,4.41L8.62,6.04C7.88,6.55 7.26,7.22 6.81,8H4V10H6.09C6.04,10.33 6,10.66 6,11V12H4V14H6V15C6,15.34 6.04,15.67 6.09,16H4V18H6.81C7.85,19.79 9.78,21 12,21C14.22,21 16.15,19.79 17.19,18H20V16H17.91C17.96,15.67 18,15.34 18,15V14H20V12H18V11C18,10.66 17.96,10.33 17.91,10H20V8Z",
  upload: "M9,16V10H5L12,3L19,10H15V16H9M5,20V18H19V20H5Z",
  print: "M18,3H6V7H18M19,12A1,1 0 0,1 18,11A1,1 0 0,1 19,10A1,1 0 0,1 20,11A1,1 0 0,1 19,12M16,19H8V14H16M19,8H5A3,3 0 0,0 2,11V17H6V21H18V17H22V11A3,3 0 0,0 19,8Z",
  tower:
    "M12,10A2,2 0 0,1 14,12C14,12.5 13.82,12.94 13.53,13.29L16.7,22H14.57L12,14.93L9.43,22H7.3L10.47,13.29C10.18,12.94 10,12.5 10,12A2,2 0 0,1 12,10M12,8A4,4 0 0,0 8,12C8,12.5 8.1,13 8.28,13.46L7.4,15.86C6.53,14.81 6,13.47 6,12A6,6 0 0,1 12,6A6,6 0 0,1 18,12C18,13.47 17.47,14.81 16.6,15.86L15.72,13.46C15.9,13 16,12.5 16,12A4,4 0 0,0 12,8M12,4A8,8 0 0,0 4,12C4,14.36 5,16.5 6.64,17.94L5.92,19.94C3.54,18.11 2,15.23 2,12A10,10 0 0,1 12,2A10,10 0 0,1 22,12C22,15.23 20.46,18.11 18.08,19.94L17.36,17.94C19,16.5 20,14.36 20,12A8,8 0 0,0 12,4Z",
};

// A device report: the telegrams of one sender as capture lines (oldest first) with the IDs, the
// gateway and the times replaced, like scripts/capture_to_fixture.py. IDs in the base ID range
// (FF-...) stay in it, broadcast and 00-00-00-00 stay as they are.
export function anonymisedCapture(rows, keys) {
  const ids = new Map();
  const gateways = new Map();
  const keep = new Set(["00-00-00-00", "FF-FF-FF-FF"]);
  const alias = (id) => {
    if (keep.has(id)) return id;
    if (!ids.has(id)) {
      const base = id.startsWith("FF-");
      const number = [...ids.values()].filter((v) => v.startsWith("FF-") === base).length + 1;
      ids.set(id, `${base ? "FF-80-00" : "05-00-00"}-${number.toString(16).toUpperCase().padStart(2, "0")}`);
    }
    return ids.get(id);
  };
  const first = Math.min(...rows.map((r) => new Date(r.time).getTime()));
  return rows.map((r) => {
    const line = Object.fromEntries(keys.map((k) => [k, r[k]]));
    line.time = new Date(Date.UTC(2000, 0, 1) + new Date(r.time).getTime() - first).toISOString();
    if (!gateways.has(r.gateway)) gateways.set(r.gateway, `gw${gateways.size + 1}`);
    line.gateway = gateways.get(r.gateway);
    line.sender = alias(r.sender);
    line.destination = alias(r.destination);
    return JSON.stringify(line);
  });
}

export function esc(value) {
  return String(value ?? "").replace(
    /[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]
  );
}

export function svg(path, cls = "") {
  return `<svg class="${cls}" viewBox="0 0 24 24" aria-hidden="true"><path d="${path}"></path></svg>`;
}

// CSV for spreadsheets: every cell quoted; text that a spreadsheet would run as a formula
// (=, +, -, @, tab or CR first) gets a leading apostrophe, numbers like -62 stay numbers
export function csv(rows) {
  const cell = (v) => {
    let text = String(v ?? "");
    if (/^[=+\-@\t\r]/.test(text) && !/^-?\d+([.,]\d+)?$/.test(text)) text = `'${text}`;
    return `"${text.replace(/"/g, '""')}"`;
  };
  return rows.map((row) => row.map(cell).join(",")).join("\n") + "\n";
}

// ---- installation documentation (the structure of the documentation websocket command) ------------

const FIELD_KEYS = ["location", "circuit", "group", "bus_address", "feedback_id", "bus_power", "fuse", "installed", "revision", "power", "note"];
// the handover page leaves out what has a table of its own (group, bus address, feedback ID, bus power)
const HANDOVER_KEYS = FIELD_KEYS.filter((f) => !["group", "bus_address", "feedback_id", "bus_power"].includes(f));

function docSenderText(s, t, profile) {
  const kind = s.ute ? t.teachUte : t.teachTelegram;
  const test = s.test ? ` · ${t.senderTestResult[s.test] || s.test}` : "";
  return `${profile(s.profile)} ${s.id} (${kind}${test})`;
}

function docWallText(w, t) {
  return w ? t.doc.wall(w.id, w.on, w.off) : "";
}

function docLinkFrom(l, t) {
  return l.from_kind === "entered" ? [l.from_name, l.from_id].filter(Boolean).join(" · ") : `${t.inst.links.from[l.from_kind]} · ${l.from_id}`;
}

// One table as CSV: "devices" (one row per sender, a device without senders has one row; sender IDs
// that stay blocked after their device was deleted and unknown senders follow at the end of their
// gateway) or "links" (one row per link).
export function documentationCsv(doc, t, profile, table = "devices") {
  const d = t.doc;
  if (table === "tables") {
    // the sender tables one below the other: a title row, the header, the rows, an empty row
    const T = t.doc.tbl;
    const rows = [];
    for (const gw of doc.gateways) {
      const parts = docTables(gw, t, profile);
      rows.push(
        [gw.title, d.sections.gwsenders],
        [T.nr, T.senderId, T.function, T.device, T.description, T.busAddress, T.feedbackId, T.use, T.second],
        ...parts.senders.map((r) => [r.nr, r.id, r.fn ?? "", r.gateway ? T.gateway : r.device ?? "", r.gateway ? "" : [r.name, r.place].filter(Boolean).join(", "), r.bus ?? "", r.feedback ?? "", r.free ? T.free : r.blocked ? T.blocked : r.use ?? "", r.second ?? ""]),
        [],
        [gw.title, d.sections.buttons],
        [T.id, T.device, T.place, T.description, T.left, T.right],
        ...parts.buttons.map((b) => [b.id, b.device, b.place, b.name, b.left.join("; "), b.right.join("; ")]),
        [],
        [gw.title, d.sections.radio],
        [T.id, T.device, T.place, T.description, T.eep, T.sends],
        ...parts.radio.map((r) => [r.id, r.device, r.place, r.description, r.eep, r.sends]),
        []
      );
      const bus = docBus(gw, t);
      if (bus.rows.length) {
        rows.push(
          [gw.title, d.sections.bus],
          [T.busAddress, T.type, T.device, T.description, T.feedbackId, `${T.power} (W)`],
          ...bus.rows.map((r) => [r.address, r.type, r.device, r.name, r.feedback, r.power ?? ""]),
          [T.sum, "", "", "", "", bus.sum],
          ...(bus.supply || bus.capacity ? [[T.supply, bus.supply, "", "", "", bus.capacity ?? ""]] : []),
          []
        );
      }
    }
    return csv(rows);
  }
  if (table === "links") {
    const L = t.inst.links;
    const rows = [[t.gateway, L.target, t.doc.cols.address, L.from.title, "ID", L.role, L.learn, L.source.title, L.state, L.teachIn("").trim(), L.tested("").trim()]];
    for (const gw of doc.gateways) {
      for (const l of gw.links ?? []) {
        rows.push([gw.title, l.to_name, l.to_id, l.from_kind === "entered" ? l.from_name : L.from[l.from_kind], l.from_id, l.source === "assigned" ? profile(l.role) : l.role, l.learn, L.source[l.source], L.status[l.status], l.teach_in ?? "", l.tested ?? ""]);
      }
    }
    return csv(rows);
  }
  const labels = FIELD_KEYS.map((f) => t.inst.fields[f]);
  const head = [t.gateway, "Base ID", t.doc.cols.device, t.doc.cols.address, "EEP", t.doc.cols.area, t.doc.virtual, ...labels, t.doc.cols.sender, t.doc.cols.senderId, t.doc.cols.teach, t.doc.cols.test, t.doc.cols.wall, t.doc.cols.poolState];
  const rows = [head];
  const blank = (n) => Array(n).fill("");
  for (const gw of doc.gateways) {
    const state = new Map(gw.pools.flatMap((p) => p.senders.map((s) => [s.id, s.state])));
    for (const d of gw.devices) {
      const base = [gw.title, gw.base_id ?? "", d.name, d.id, [d.eep, ...d.eep_extra].filter(Boolean).join(", "), d.area ?? "", d.virtual ? t.yes : "", ...FIELD_KEYS.map((f) => d[f] ?? "")];
      const wall = docWallText(d.wall_switch, t);
      if (!d.senders.length) rows.push([...base, "", "", "", "", wall, ""]);
      for (const s of d.senders) rows.push([...base, profile(s.profile), s.id, s.ute ? t.teachUte : t.teachTelegram, s.test ? (t.senderTestResult[s.test] || s.test) : "", wall, t.doc.state[state.get(s.id)] || ""]);
    }
    const extra = (name, address, note) => {
      const row = blank(head.length);
      Object.assign(row, { 0: gw.title, 1: gw.base_id ?? "", 2: name, 3: address, [7 + FIELD_KEYS.indexOf("note")]: note });
      rows.push(row);
    };
    for (const m of gw.manual ?? []) extra(m.name, m.address, m.function);
    for (const h of gw.heard ?? []) extra(t.doc.notSetUp, h.id, `${h.rorg}${h.dbm != null ? `, ${h.dbm} dBm` : ""}`);
    for (const p of gw.pools) {
      for (const s of p.senders.filter((x) => x.device == null)) {
        rows.push([gw.title, gw.base_id ?? "", t.doc.deleted, "", "", "", "", ...blank(FIELD_KEYS.length), profile(s.profile), s.id, "", "", "", t.doc.state[s.state] || s.state]);
      }
    }
  }
  return csv(rows);
}


// ---- the sender tables: gateway senders (number 0 to 127), buttons, radio senders ----------------------

const idNumber = (id) => parseInt(String(id).replace(/-/g, ""), 16);
const place = (d) => d.location || d.area || "";

// The rows of the three tables of one gateway, from what the documentation command holds:
// - gateway senders: one row per number of the radio pool, the base ID itself is number 0; a
//   second mode (+64) points to its counterpart
// - buttons: the devices that are buttons, and every wall switch an actuator names, with the
//   actuators on its left and right rocker (buttons a0/a1 left, b0/b1 right)
// - radio senders: every device that only sends (sensors, meters, climate), and the entries by hand
export function docTables(gw, t, profile) {
  const T = t.doc.tbl;
  const base = gw.base_id ? idNumber(gw.base_id) : null;
  const byRef = new Map(gw.devices.map((d) => [d.note_key, d]));
  const numbers = new Map(); // note_key -> its first sender number, to refer to it
  const senders = [];
  const pool = gw.pools.find((p) => p.kind === "radio");
  if (base !== null && pool) {
    const taken = new Map(pool.senders.map((s) => [idNumber(s.id) - base, s]));
    for (const [n, s] of taken) if (s.ref && !numbers.has(s.ref)) numbers.set(s.ref, n);
    for (let n = 0; n <= 127; n++) {
      const s = taken.get(n);
      const id = (base + n).toString(16).toUpperCase().padStart(8, "0");
      const row = { nr: n, id, free: false };
      if (n === 0) Object.assign(row, { gateway: true });
      else if (!s) row.free = true;
      else if (!s.device) row.blocked = true;
      else {
        const d = byRef.get(s.ref);
        const partner = taken.get(n + 64)?.ref === s.ref ? n + 64 : taken.get(n - 64)?.ref === s.ref ? n - 64 : null;
        Object.assign(row, {
          fn: T.categories[d?.category] ?? "",
          device: d?.model ?? s.device,
          name: s.device,
          place: d ? place(d) : "",
          bus: d?.bus_address ?? "",
          feedback: d?.feedback_id ?? "",
          use: profile(s.profile),
          second: partner === null ? "" : partner > n ? `${partner} →` : `← ${partner}`,
        });
      }
      senders.push(row);
    }
  }
  const nr = (key) => (numbers.has(key) ? ` (${numbers.get(key)})` : "");

  // buttons: a button device, or just an ID that an actuator names as its wall switch
  const buttons = new Map();
  const entry = (id) => {
    if (!buttons.has(id)) buttons.set(id, { id, device: "", place: "", name: "", left: [], right: [] });
    return buttons.get(id);
  };
  for (const d of gw.devices) if (d.category === "buttons" && !d.virtual) Object.assign(entry(d.id), { device: d.model ?? "", place: place(d), name: d.name });
  for (const d of gw.devices) {
    const w = d.wall_switch;
    if (!w?.id) continue;
    const e = entry(w.id);
    const on = (w.on || "").toLowerCase();
    const off = (w.off || "").toLowerCase();
    const split = on && off && on[0] !== off[0]; // on and off on different rockers: say which
    for (const [button, word] of [[on, t.doc.tbl.on], [off, t.doc.tbl.off]]) {
      const side = button[0] === "a" ? e.left : button[0] === "b" ? e.right : null;
      const text = `${d.name}${split ? ` ${word}` : ""}${nr(d.note_key)}`;
      if (side && !side.includes(text)) side.push(text);
    }
  }
  const buttonRows = [...buttons.values()].sort((a, b) => a.name.localeCompare(b.name) || a.id.localeCompare(b.id));

  // radio senders: devices that only send, then the entries made by hand
  // devices of one physical device (a room controller sends under several IDs) share a group name:
  // their rows follow each other, the group is the description and each ID says what it sends
  const radio = gw.devices
    .filter((d) => !d.virtual && ["sensors", "meters", "climate"].includes(d.category))
    .map((d) => ({ id: d.id, device: d.model ?? "", place: place(d), description: d.group || d.name, eep: [d.eep, ...d.eep_extra].filter(Boolean).join(", "), sends: d.group ? d.name : T.categories[d.category], group: d.group || "" }))
    .sort((a, b) => (a.group || a.description).localeCompare(b.group || b.description) || a.id.localeCompare(b.id));
  for (const m of (gw.manual ?? []).filter((e) => e.address)) radio.push({ id: m.address, device: m.name, place: "", description: m.function, eep: "", sends: T.byHand, group: "" });
  return { senders, buttons: buttonRows, radio };
}

// The Eltako bus: every device with a bus address, from the typed fields of the devices and the
// entries by hand, by address, with the power each takes from the bus (from its data sheet), the
// sum and, when the power supply is written down, how much of it that uses. Home Assistant cannot
// read the bus yet, so what is not written down is not here.
const watts = (text) => (text && /^\d+([.,]\d+)?$/.test(String(text).trim()) ? Number(String(text).trim().replace(",", ".")) : null);
export function docBus(gw, t) {
  const T = t.doc.tbl;
  const rows = [
    ...gw.devices
      .filter((d) => d.bus_address && !d.virtual)
      .map((d) => ({ address: d.bus_address, type: ["lighting", "covers"].includes(d.category) ? T.busTypes.actuator : T.busTypes.sender, device: d.model ?? "", name: d.name, feedback: d.feedback_id ?? "", power: watts(d.bus_power) })),
    ...(gw.manual ?? [])
      .filter((m) => m.bus_address)
      .map((m) => ({ address: m.bus_address, type: T.busTypes.other, device: m.name, name: m.function, feedback: m.feedback_id ?? "", power: watts(m.bus_power) })),
  ].sort((a, b) => (parseInt(a.address, 10) || 0) - (parseInt(b.address, 10) || 0) || a.address.localeCompare(b.address));
  const counted = rows.filter((r) => r.power !== null);
  const sum = Math.round(counted.reduce((n, r) => n + r.power, 0) * 10) / 10;
  const capacity = watts(gw.supply?.watts);
  return {
    rows,
    sum,
    counted: counted.length,
    capacity,
    supply: gw.supply?.name ?? "",
    percent: capacity ? Math.round((sum / capacity) * 100) : null,
  };
}

// the gateway senders without runs of free numbers: "2 to 28 free" as one row
export function foldFree(rows) {
  const out = [];
  for (const r of rows) {
    const last = out[out.length - 1];
    if (r.free && last?.free) {
      last.to = r.nr;
      continue;
    }
    out.push(r.free ? { ...r, to: r.nr } : r);
  }
  return out;
}

// Sections of the page; each can be switched off above the page (and is then not printed)
export const DOC_SECTIONS = ["handover", "cabinet", "gwsenders", "buttons", "radio", "bus", "links", "swap", "ids", "log"];

// One self-contained page, no scripts: check boxes above it show or hide the sections, printing
// leaves them out. Sections: the handover (every device with its senders and fields), the cabinet
// (devices by place, with circuit and fuse), the links, a checklist for moving to a gateway with
// another base ID, the sender IDs (pool, further devices, unknown senders) and the log.
export function documentationHtml(doc, t, profile, lang, shown = ["handover", "cabinet", "gwsenders", "buttons", "radio", "bus", "links", "swap", "ids"]) {
  const d = t.doc;
  const L = t.inst.links;
  const when = (iso) => new Date(iso).toLocaleString(lang);
  const cell = (html) => `<td>${html}</td>`;
  const field = (x, f) => esc(x[f] ?? "");
  const table = (head, rows) => (rows ? `<table><thead><tr>${head.map((h) => `<th>${esc(h)}</th>`).join("")}</tr></thead><tbody>${rows}</tbody></table>` : "");
  const perGateway = (build) =>
    doc.gateways
      .map((gw) => {
        const inner = build(gw);
        return inner ? `<div class="gw"><h3>${esc(gw.title)}${gw.base_id ? ` <span class="mono sub">${esc(gw.base_id)}</span>` : ""}</h3>${gw.note ? `<p class="gwnote">${esc(gw.note)}</p>` : ""}${inner}</div>` : "";
      })
      .join("");
  const section = (name, title, intro, body) => (body ? `<section class="sec sec-${name}"><h2>${esc(title)}</h2>${intro ? `<p class="sub">${esc(intro)}</p>` : ""}${body}</section>` : "");

  const overview = doc.gateways.length > 1
    ? `<section class="sec"><h2>${esc(d.overview)}</h2>${table([d.cols.gateway, "Base ID", d.devices, d.cols.senderIds, d.cols.blocked, d.cols.heard], doc.gateways.map((gw) => {
        const pool = gw.pools.flatMap((p) => p.senders);
        return `<tr>${cell(`${esc(gw.title)}${gw.note ? `<div class="sub">${esc(gw.note)}</div>` : ""}`)}${cell(`<span class="mono">${esc(gw.base_id ?? "")}</span>`)}${[gw.devices.length, pool.length, pool.filter((s) => s.state === "blocked").length, (gw.heard ?? []).length].map((n) => cell(esc(n))).join("")}</tr>`;
      }).join(""))}</section>`
    : "";

  const handover = section("handover", d.sections.handover, d.generated(when(doc.generated)), perGateway((gw) =>
    table([d.cols.device, d.cols.address, d.cols.senders, d.cols.wall, ...HANDOVER_KEYS.map((f) => t.inst.fields[f])], gw.devices.map((x) => {
      const sub = [x.virtual ? d.virtual : "", x.area ?? "", x.model ?? ""].filter(Boolean).join(" · ");
      const senders = x.senders.length ? x.senders.map((s) => `<div>${esc(docSenderText(s, t, profile))}</div>`).join("") : `<span class="sub">${esc(x.virtual ? d.sentByHa : d.receiveOnly)}</span>`;
      return `<tr>${cell(`${esc(x.name)}${sub ? `<div class="sub">${esc(sub)}</div>` : ""}`)}${cell(`<span class="mono">${esc(x.id)}</span><div class="sub mono">${esc([x.eep, ...x.eep_extra].filter(Boolean).join(", "))}</div>`)}${cell(senders)}${cell(x.wall_switch ? esc(docWallText(x.wall_switch, t)) : `<span class="sub">${esc(d.none)}</span>`)}${HANDOVER_KEYS.map((f) => cell(field(x, f))).join("")}</tr>`;
    }).join(""))));

  const cabinet = section("cabinet", d.sections.cabinet, "", perGateway((gw) =>
    table([t.inst.fields.location, d.cols.device, d.cols.address, t.inst.fields.circuit, t.inst.fields.fuse, t.inst.fields.revision, t.inst.fields.power], gw.devices
      .filter((x) => !x.virtual)
      .sort((a, b) => (a.location || "\uffff").localeCompare(b.location || "\uffff") || a.name.localeCompare(b.name))
      .map((x) => `<tr>${[field(x, "location") || `<span class="sub">${esc(d.none)}</span>`, esc(x.name), `<span class="mono">${esc(x.id)}</span>`, field(x, "circuit"), field(x, "fuse"), field(x, "revision"), field(x, "power")].map(cell).join("")}</tr>`)
      .join(""))));


  const T = d.tbl;
  const tbl = (name, intro, build) =>
    section(name, d.sections[name], intro, perGateway((gw) => build(docTables(gw, t, profile), gw)));
  const gwsenders = tbl("gwsenders", T.sendersIntro, ({ senders }) => {
    if (!senders.length) return "";
    const rows = foldFree(senders).map((r) => {
      if (r.free) return `<tr class="sub"><td class="mono">${r.nr === r.to ? r.nr : `${r.nr} – ${r.to}`}</td><td colspan="8">${esc(T.free)}</td></tr>`;
      if (r.gateway) return `<tr><td class="mono">0</td><td class="mono">${esc(r.id)}</td><td colspan="7">${esc(T.gateway)}</td></tr>`;
      if (r.blocked) return `<tr><td class="mono">${r.nr}</td><td class="mono">${esc(r.id)}</td><td colspan="7" class="sub">${esc(T.blocked)}</td></tr>`;
      return `<tr>${[`<span class="mono">${r.nr}</span>`, `<span class="mono">${esc(r.id)}</span>`, esc(r.fn), esc(r.device), esc([r.name, r.place].filter(Boolean).join(", ")), esc(r.bus), `<span class="mono">${esc(r.feedback)}</span>`, esc(r.use), `<span class="mono">${esc(r.second)}</span>`].map(cell).join("")}</tr>`;
    }).join("");
    return table([T.nr, T.senderId, T.function, T.device, T.description, T.busAddress, T.feedbackId, T.use, T.second], rows);
  });
  const buttonsTable = tbl("buttons", T.buttonsIntro, ({ buttons }) =>
    buttons.length
      ? table([T.id, T.device, T.place, T.description, T.left, T.right], buttons.map((b) => `<tr>${[`<span class="mono">${esc(b.id)}</span>`, esc(b.device), esc(b.place), esc(b.name), b.left.map(esc).join("<br>") || `<span class="sub">${esc(T.unassigned)}</span>`, b.right.map(esc).join("<br>") || `<span class="sub">${esc(T.unassigned)}</span>`].map(cell).join("")}</tr>`).join(""))
      : "");
  const radioTable = tbl("radio", T.radioIntro, ({ radio }) => {
    if (!radio.length) return "";
    // the rows of a group: device, place and description once, spanning the IDs of the group
    const rows = radio.map((r, i) => {
      const same = (x) => r.group && x?.group === r.group;
      const end = radio.findIndex((x, j) => j > i && !same(x));
      const span = !r.group ? 1 : same(radio[i - 1]) ? 0 : (end === -1 ? radio.length : end) - i;
      const spanned = (html) => (span === 0 ? "" : span > 1 ? `<td rowspan="${span}">${html}</td>` : cell(html));
      const cells = [cell(`<span class="mono">${esc(r.id)}</span>`), spanned(esc(r.device)), spanned(esc(r.place)), spanned(esc(r.description)), cell(`<span class="mono">${esc(r.eep)}</span>`), cell(esc(r.sends))];
      return `<tr>${cells.join("")}</tr>`;
    }).join("");
    return table([T.id, T.device, T.place, T.description, T.eep, T.sends], rows);
  });

  const busTable = tbl("bus", T.busIntro, (_parts, gw) => {
    const bus = docBus(gw, t);
    if (!bus.rows.length) return "";
    const num = (n) => `${n.toLocaleString(lang, { maximumFractionDigits: 1 })} W`;
    const rows = bus.rows.map((r) => `<tr>${[`<span class="mono">${esc(r.address)}</span>`, esc(r.type), esc(r.device), esc(r.name), `<span class="mono">${esc(r.feedback)}</span>`, r.power === null ? `<span class="sub">${esc(T.noValue)}</span>` : num(r.power)].map(cell).join("")}</tr>`).join("");
    const sum = `<tr><td colspan="5"><b>${esc(T.busSum(bus.counted, bus.rows.length))}</b></td><td><b>${esc(num(bus.sum))}</b></td></tr>`;
    const supply = bus.supply || bus.capacity ? `<p>${esc(T.supply)}: ${esc([bus.supply, bus.capacity ? num(bus.capacity) : ""].filter(Boolean).join(", "))}${bus.percent !== null ? ` · ${esc(T.busLoad(num(bus.sum), num(bus.capacity), bus.percent))}` : ""}${bus.percent >= 80 ? ` · <b>${esc(T.busWarn)}</b>` : ""}</p>` : "";
    const missing = bus.rows.length - bus.counted ? `<p class="sub">${esc(T.busMissing(bus.rows.length - bus.counted))}</p>` : "";
    return table([T.busAddress, T.type, T.device, T.description, T.feedbackId, T.power], rows + sum).replace("<table>", '<table class="rnum">') + supply + missing;
  });

  const links = section("links", d.sections.links, L.honest, perGateway((gw) => {
    const byTarget = new Map();
    for (const l of gw.links ?? []) byTarget.set(l.to_key || l.to_name, [...(byTarget.get(l.to_key || l.to_name) ?? []), l]);
    return [...byTarget.values()]
      .sort((a, b) => a[0].to_name.localeCompare(b[0].to_name))
      .map((list) => `<h4>${esc(list[0].to_name)} <span class="mono sub">${esc(list[0].to_id)}</span></h4>${table([L.from.title, L.role, L.learn, L.state], list.map((l) => `<tr>${cell(esc(docLinkFrom(l, t)))}${cell(esc(l.source === "assigned" ? profile(l.role) : l.role))}${cell(esc(l.learn))}${cell(`${esc(L.status[l.status])}<div class="sub">${esc([l.teach_in ? L.teachIn(when(l.teach_in)) : "", l.tested ? L.tested(when(l.tested)) : ""].filter(Boolean).join(" · "))}</div>`)}</tr>`).join(""))}`)
      .join("") + `<p class="sub">${esc(L.otherSenders)}</p>`;
  }));

  const swap = section("swap", d.sections.swap, d.swapIntro, perGateway((gw) => {
    const todo = (gw.links ?? []).filter((l) => l.source === "assigned");
    return todo.length
      ? `<ul class="check">${todo.map((l) => `<li><span class="box"></span>${esc(l.to_name)} <span class="mono sub">${esc(l.to_id)}</span>: ${esc(d.swapStep(profile(l.role)))}${l.learn ? ` <span class="sub">(${esc(L.learn)}: ${esc(l.learn)})</span>` : ""}</li>`).join("")}</ul>`
      : "";
  }));

  const ids = section("ids", d.sections.ids, "", perGateway((gw) => {
    const pool = gw.pools.flatMap((p) => p.senders);
    const poolRows = pool.map((s) => `<tr>${cell(`<span class="mono">${esc(s.id)}</span>`)}${cell(esc(s.device ?? d.deleted))}${cell(esc(profile(s.profile)))}${cell(esc(d.state[s.state] || s.state))}</tr>`).join("");
    const manualRows = (gw.manual ?? []).map((m) => `<tr>${cell(esc(m.name))}${cell(`<span class="mono">${esc(m.address)}</span>`)}${cell(esc(m.function))}</tr>`).join("");
    const heardRows = (gw.heard ?? []).map((h) => `<tr>${cell(`<span class="mono">${esc(h.id)}</span>`)}${cell(esc(h.rorg))}${cell(esc(h.dbm != null ? `${h.dbm} dBm` : ""))}${cell(esc(when(h.last)))}</tr>`).join("");
    return [
      poolRows ? `<h4>${esc(d.pool)}</h4>${table([d.cols.senderId, d.cols.usedBy, d.cols.sender, d.cols.poolState], poolRows)}` : "",
      manualRows ? `<h4>${esc(d.manualTitle)}</h4>${table([d.cols.device, d.cols.senderId, d.manualFunction], manualRows)}` : "",
      heardRows ? `<h4>${esc(d.heard)}</h4><p class="sub">${esc(d.heardNote)}</p>${table([d.cols.senderId, d.cols.type, d.cols.signal, d.cols.lastHeard], heardRows)}` : "",
      gw.hidden_senders.length ? `<h4>${esc(d.hidden)}</h4><p class="mono">${esc(gw.hidden_senders.join(", "))}</p>` : "",
    ].join("");
  }));

  const log = section("log", d.sections.log, "", perGateway((gw) =>
    table([t.time, t.inst.event, t.inst.detail], [...(gw.log ?? [])].reverse().map((e) => `<tr>${cell(`<span class="mono">${esc(when(e.time))}</span>`)}${cell(esc(t.inst.events[e.kind] || e.kind))}${cell(esc(e.detail || e.device))}</tr>`).join(""))));

  const toggles = DOC_SECTIONS.map((name) => `<label><input type="checkbox" id="show-${name}"${shown.includes(name) ? " checked" : ""}> ${esc(d.sections[name])}</label>`).join("");
  const rules = DOC_SECTIONS.map((name) => `body:has(#show-${name}:not(:checked)) .sec-${name}{display:none}`).join("\n");
  return `<!doctype html><html lang="${esc(lang)}"><head><meta charset="utf-8"><title>${esc(d.title)}</title><style>
body{font:13px/1.45 system-ui,sans-serif;color:#1c1c1a;margin:24px}
h1{font-size:20px;font-weight:500;margin:0}h2{font-size:17px;font-weight:500;margin:0 0 4px}h3{font-size:14px;font-weight:500;margin:14px 0 4px}h4{font-size:13px;font-weight:500;margin:12px 0 4px}
.sub{color:#5f5e5a;font-size:12px}table.rnum th:last-child,table.rnum td:last-child{text-align:right;white-space:nowrap}.mono{font-family:ui-monospace,monospace;font-size:12px;white-space:nowrap}.gwnote{margin:0 0 4px;font-style:italic}
table{width:100%;border-collapse:collapse}th{text-align:left;font-weight:500;color:#5f5e5a;font-size:12px;border-bottom:1px solid #888;padding:5px 8px 5px 0}
td{border-bottom:1px solid #ddd;padding:5px 8px 5px 0;vertical-align:top}tr{break-inside:avoid}thead{display:table-header-group}h2,h3,h4{break-after:avoid}
section.sec{margin-top:24px}.note{margin-top:24px;padding:10px 14px;background:#f1efe8;border-radius:6px}
.bar{display:flex;flex-wrap:wrap;gap:6px 16px;margin:12px 0;padding:8px 12px;background:#eef3f8;border-radius:6px}
ul.check{list-style:none;padding:0;margin:6px 0}ul.check li{padding:4px 0;border-bottom:1px solid #ddd}.box{display:inline-block;width:11px;height:11px;border:1.5px solid #444;margin-right:8px;vertical-align:-1px}
${rules}
@media print{.bar{display:none}}
@page{margin:14mm}
</style></head><body>
<h1>${esc(d.title)}</h1>
<div class="bar">${toggles}</div>
${overview}${handover}${cabinet}${gwsenders}${buttonsTable}${radioTable}${busTable}${links}${swap}${ids}${log}
<div class="note"><b>${esc(d.notKnownTitle)}</b><br>${esc(d.notKnown)}</div>
</body></html>`;
}
