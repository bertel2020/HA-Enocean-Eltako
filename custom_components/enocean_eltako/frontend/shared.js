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

function docSenderText(s, t, profile) {
  const kind = s.ute ? t.teachUte : t.teachTelegram;
  const test = s.test ? ` · ${t.senderTestResult[s.test] || s.test}` : "";
  return `${profile(s.profile)} ${s.id} (${kind}${test})`;
}

function docWallText(w, t) {
  return w ? t.doc.wall(w.id, w.on, w.off) : "";
}

// One row per sender (a device without senders has one row); sender IDs that stay blocked after
// their device was deleted follow at the end of their gateway.
export function documentationCsv(doc, t, profile) {
  const head = [t.gateway, "Base ID", t.doc.cols.device, t.doc.cols.address, "EEP", t.doc.cols.area, t.doc.virtual, t.doc.cols.sender, t.doc.cols.senderId, t.doc.cols.teach, t.doc.cols.test, t.doc.cols.wall, t.doc.cols.poolState, t.doc.notes];
  const rows = [head];
  for (const gw of doc.gateways) {
    const state = new Map(gw.pools.flatMap((p) => p.senders.map((s) => [s.id, s.state])));
    for (const d of gw.devices) {
      const base = [gw.title, gw.base_id ?? "", d.name, d.id, [d.eep, ...d.eep_extra].filter(Boolean).join(", "), d.area ?? "", d.virtual ? t.yes : ""];
      const wall = docWallText(d.wall_switch, t);
      if (!d.senders.length) rows.push([...base, "", "", "", "", wall, "", d.note ?? ""]);
      for (const s of d.senders) rows.push([...base, profile(s.profile), s.id, s.ute ? t.teachUte : t.teachTelegram, s.test ? (t.senderTestResult[s.test] || s.test) : "", wall, t.doc.state[state.get(s.id)] || "", d.note ?? ""]);
    }
    for (const m of gw.manual ?? []) {
      rows.push([gw.title, gw.base_id ?? "", m.name, m.address, "", "", "", "", "", "", "", "", "", m.function]);
    }
    for (const h of gw.heard ?? []) {
      rows.push([gw.title, gw.base_id ?? "", t.doc.notSetUp, h.id, "", "", "", "", "", "", "", "", "", `${h.rorg}${h.dbm != null ? `, ${h.dbm} dBm` : ""}`]);
    }
    for (const p of gw.pools) {
      for (const s of p.senders.filter((x) => x.device == null)) {
        rows.push([gw.title, gw.base_id ?? "", t.doc.deleted, "", "", "", "", profile(s.profile), s.id, "", "", "", t.doc.state[s.state] || s.state, ""]);
      }
    }
  }
  return csv(rows);
}

// A self-contained page for printing: one gateway per page, no scripts.
export function documentationHtml(doc, t, profile, lang) {
  const d = t.doc;
  const when = new Date(doc.generated).toLocaleString(lang);
  const cell = (html) => `<td>${html}</td>`;
  const gateways = doc.gateways
    .map((gw) => {
      const devices = gw.devices
        .map((x) => {
          const sub = [x.virtual ? d.virtual : "", x.area ?? "", x.model ?? ""].filter(Boolean).join(" · ");
          const senders = x.senders.length ? x.senders.map((s) => `<div>${esc(docSenderText(s, t, profile))}</div>`).join("") : `<span class="sub">${esc(x.virtual ? d.sentByHa : d.receiveOnly)}</span>`;
          return `<tr>${cell(`${esc(x.name)}${sub ? `<div class="sub">${esc(sub)}</div>` : ""}`)}${cell(`<span class="mono">${esc(x.id)}</span><div class="sub mono">${esc([x.eep, ...x.eep_extra].filter(Boolean).join(", "))}</div>`)}${cell(senders)}${cell(x.wall_switch ? esc(docWallText(x.wall_switch, t)) : `<span class="sub">${esc(d.none)}</span>`)}${cell(esc(x.note ?? ""))}</tr>`;
        })
        .join("");
      const pool = gw.pools.flatMap((p) => p.senders);
      const poolRows = pool.map((s) => `<tr>${cell(`<span class="mono">${esc(s.id)}</span>`)}${cell(esc(s.device ?? d.deleted))}${cell(esc(`${profile(s.profile)}`))}${cell(esc(d.state[s.state] || s.state))}</tr>`).join("");
      const heardRows = (gw.heard ?? []).map((h) => `<tr>${cell(`<span class="mono">${esc(h.id)}</span>`)}${cell(esc(h.rorg))}${cell(esc(h.dbm != null ? `${h.dbm} dBm` : ""))}${cell(esc(new Date(h.last).toLocaleString(lang)))}</tr>`).join("");
      const manualRows = (gw.manual ?? []).map((m) => `<tr>${cell(esc(m.name))}${cell(`<span class="mono">${esc(m.address)}</span>`)}${cell(esc(m.function))}</tr>`).join("");
      const blocked = pool.filter((s) => s.state === "blocked").length;
      return `<section class="gw">
<h2>${esc(gw.title)}</h2>
${gw.note ? `<p class="gwnote">${esc(gw.note)}</p>` : ""}
<p class="sub">${esc(gw.model_name ?? gw.model ?? "")}${gw.base_id ? ` · Base ID <span class="mono">${esc(gw.base_id)}</span>` : ""} · ${esc(d.counts(gw.devices.length, pool.length, blocked))}</p>
<h3>${esc(d.devices)}</h3>
<table><thead><tr><th>${esc(d.cols.device)}</th><th>${esc(d.cols.address)}</th><th>${esc(d.cols.senders)}</th><th>${esc(d.cols.wall)}</th><th>${esc(d.notes)}</th></tr></thead><tbody>${devices}</tbody></table>
${poolRows ? `<h3>${esc(d.pool)}</h3><table><thead><tr><th>${esc(d.cols.senderId)}</th><th>${esc(d.cols.usedBy)}</th><th>${esc(d.cols.sender)}</th><th>${esc(d.cols.poolState)}</th></tr></thead><tbody>${poolRows}</tbody></table>` : ""}
${manualRows ? `<h3>${esc(d.manualTitle)}</h3><table><thead><tr><th>${esc(d.cols.device)}</th><th>${esc(d.cols.senderId)}</th><th>${esc(d.manualFunction)}</th></tr></thead><tbody>${manualRows}</tbody></table>` : ""}
${heardRows ? `<h3>${esc(d.heard)}</h3><p class="sub">${esc(d.heardNote)}</p><table><thead><tr><th>${esc(d.cols.senderId)}</th><th>${esc(d.cols.type)}</th><th>${esc(d.cols.signal)}</th><th>${esc(d.cols.lastHeard)}</th></tr></thead><tbody>${heardRows}</tbody></table>` : ""}
${gw.hidden_senders.length ? `<h3>${esc(d.hidden)}</h3><p class="mono">${esc(gw.hidden_senders.join(", "))}</p>` : ""}
</section>`;
    })
    .join("");
  // several gateways: a first page with one line each
  const count = (gw) => {
    const pool = gw.pools.flatMap((p) => p.senders);
    return [gw.devices.length, pool.length, pool.filter((s) => s.state === "blocked").length, (gw.heard ?? []).length];
  };
  const overview = doc.gateways.length > 1
    ? `<section class="gw"><h2>${esc(d.overview)}</h2><table><thead><tr><th>${esc(d.cols.gateway)}</th><th>Base ID</th><th>${esc(d.devices)}</th><th>${esc(d.cols.senderIds)}</th><th>${esc(d.cols.blocked)}</th><th>${esc(d.cols.heard)}</th></tr></thead><tbody>${doc.gateways
        .map((gw) => `<tr>${cell(`${esc(gw.title)}${gw.note ? `<div class="sub">${esc(gw.note)}</div>` : ""}`)}${cell(`<span class="mono">${esc(gw.base_id ?? "")}</span>`)}${count(gw).map((n) => cell(esc(n))).join("")}</tr>`)
        .join("")}</tbody></table></section>`
    : "";
  return `<!doctype html><html lang="${esc(lang)}"><head><meta charset="utf-8"><title>${esc(d.title)}</title><style>
body{font:13px/1.45 system-ui,sans-serif;color:#1c1c1a;margin:24px}
h1{font-size:20px;font-weight:500;margin:0}h2{font-size:17px;font-weight:500;margin:0}h3{font-size:14px;font-weight:500;margin:18px 0 6px}
.sub{color:#5f5e5a;font-size:12px}.mono{font-family:ui-monospace,monospace;font-size:12px;white-space:nowrap}
table{width:100%;border-collapse:collapse}th{text-align:left;font-weight:500;color:#5f5e5a;font-size:12px;border-bottom:1px solid #888;padding:5px 8px 5px 0}
td{border-bottom:1px solid #ddd;padding:6px 8px 6px 0;vertical-align:top}tr{break-inside:avoid}thead{display:table-header-group}h2,h3{break-after:avoid}
section.gw{break-after:page;margin-top:24px}.gwnote{margin:2px 0 4px;font-style:italic}.note{margin-top:24px;padding:10px 14px;background:#f1efe8;border-radius:6px}
@page{margin:14mm}
</style></head><body>
<h1>${esc(d.title)}</h1><p class="sub">${esc(d.generated(when))}</p>
${overview}${gateways}
<div class="note"><b>${esc(d.notKnownTitle)}</b><br>${esc(d.notKnown)}</div>
</body></html>`;
}

// The cabinet sheet: one dense table per gateway (landscape), to hang in the distribution board.
// The learn function to set on an actuator depends on its revision, so it points to the table.
export function documentationSheet(doc, t, profile, lang) {
  const d = t.doc;
  const when = new Date(doc.generated).toLocaleString(lang);
  const sections = doc.gateways
    .map((gw) => {
      const rows = gw.devices
        .filter((x) => !x.virtual)
        .map((x) => {
          const senders = x.senders.map((s) => `<span class="mono">${esc(s.id)}</span> ${esc(profile(s.profile))}`).join("<br>");
          const wall = x.wall_switch ? `<span class="mono">${esc(x.wall_switch.id)}</span>` : "";
          return `<tr><td>${esc(x.name)}</td><td class="mono">${esc(x.id)}</td><td>${esc(x.area ?? "")}</td><td>${senders}</td><td>${wall}</td><td>${esc(x.note ?? "")}</td></tr>`;
        })
        .join("");
      const manual = (gw.manual ?? []).map((m) => `<tr><td>${esc(m.name)}</td><td class="mono">${esc(m.address)}</td><td></td><td colspan="3">${esc(m.function)}</td></tr>`).join("");
      return `<section><h2>${esc(gw.title)}${gw.base_id ? ` <small class="mono">${esc(gw.base_id)}</small>` : ""}</h2>${gw.note ? `<p class="gwnote">${esc(gw.note)}</p>` : ""}<table><thead><tr><th>${esc(d.cols.device)}</th><th>${esc(d.cols.address)}</th><th>${esc(d.cols.area)}</th><th>${esc(d.cols.senders)}</th><th>${esc(d.cols.wall)}</th><th>${esc(d.notes)}</th></tr></thead><tbody>${rows}${manual}</tbody></table></section>`;
    })
    .join("");
  return `<!doctype html><html lang="${esc(lang)}"><head><meta charset="utf-8"><title>${esc(d.sheetTitle)}</title><style>
body{font:11px/1.35 system-ui,sans-serif;color:#1c1c1a;margin:0}
h1{font-size:16px;font-weight:500;margin:0}h2{font-size:14px;font-weight:500;margin:14px 0 4px}small{font-weight:400;font-size:11px}
.sub{color:#5f5e5a}.mono{font-family:ui-monospace,monospace}.gwnote{margin:0 0 4px;font-style:italic}
table{width:100%;border-collapse:collapse}th{text-align:left;font-weight:500;color:#5f5e5a;border-bottom:1px solid #888;padding:3px 6px 3px 0}
td{border-bottom:1px solid #ddd;padding:3px 6px 3px 0;vertical-align:top}tr{break-inside:avoid}thead{display:table-header-group}
section{break-inside:auto}.foot{margin-top:14px;color:#5f5e5a}
@page{size:A4 landscape;margin:10mm}
</style></head><body>
<h1>${esc(d.sheetTitle)}</h1><p class="sub">${esc(d.generated(when))}</p>
${sections}
<p class="foot">${esc(d.sheetFoot)}</p>
</body></html>`;
}
