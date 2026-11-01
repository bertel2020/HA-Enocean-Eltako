// CI check of the sidebar panel (custom_components/enocean_eltako/frontend), no browser needed:
// every file loads (syntax, imports between the parts, names used at load time) and the
// English and German texts have the same keys. Run: node scripts/check_panel.mjs

import { fileURLToPath } from "node:url";

// just enough of a browser for the files to load
globalThis.HTMLElement = class {};
const defined = [];
globalThis.customElements = { define: (name) => defined.push(name) };

const frontend = new URL("../custom_components/enocean_eltako/frontend/", import.meta.url);
const errors = [];

await import(new URL("monitor-panel.js?v=check", frontend).href);
if (!defined.includes("enocean-eltako-monitor")) errors.push("monitor-panel.js defines no enocean-eltako-monitor");

// the panel picks the language at run time: a key missing in one of them shows as undefined
const { TEXT } = await import(new URL("texts.js?v=check", frontend).href);
function compare(a, b, path) {
  for (const key of new Set([...Object.keys(a), ...Object.keys(b)])) {
    const where = path ? `${path}.${key}` : key;
    if (!(key in a)) errors.push(`texts.js: ${where} missing in en`);
    else if (!(key in b)) errors.push(`texts.js: ${where} missing in de`);
    else if (typeof a[key] !== typeof b[key] || Array.isArray(a[key]) !== Array.isArray(b[key])) errors.push(`texts.js: ${where} differs in type`);
    else if (Array.isArray(a[key]) && a[key].length !== b[key].length) errors.push(`texts.js: ${where} differs in length`);
    else if (typeof a[key] === "object") compare(a[key], b[key], where);
  }
}
compare(TEXT.en, TEXT.de, "");

// a device report replaces IDs, gateway and times and keeps data, status and signal
const { anonymisedCapture } = await import(new URL("shared.js?v=check", frontend).href);
const keys = ["time", "gateway", "dir", "rorg", "data", "sender", "status", "destination", "dbm", "duplicate"];
const row = (time, sender, destination) => ({ time, gateway: "abc", dir: "rx", rorg: "F6", data: "70", sender, status: "30", destination, dbm: -61, duplicate: false });
const lines = anonymisedCapture(
  [row("2026-11-01T10:00:00.000Z", "00-21-63-43", "FF-FF-FF-FF"), row("2026-11-01T10:00:02.500Z", "FF-B7-44-81", "00-21-63-43")],
  keys,
).map((l) => JSON.parse(l));
if (lines[0].sender !== "05-00-00-01" || lines[1].sender !== "FF-80-00-01" || lines[1].destination !== "05-00-00-01") errors.push("shared.js: anonymisedCapture does not replace the IDs");
if (lines[0].destination !== "FF-FF-FF-FF" || lines[0].gateway !== "gw1") errors.push("shared.js: anonymisedCapture changes broadcast or misses the gateway");
if (lines[0].time !== "2000-01-01T00:00:00.000Z" || lines[1].time !== "2000-01-01T00:00:02.500Z") errors.push("shared.js: anonymisedCapture does not replace the times");
if (lines[0].data !== "70" || lines[0].status !== "30" || lines[0].dbm !== -61) errors.push("shared.js: anonymisedCapture changes the telegram data");

// the documentation: CSV with one row per sender plus blocked IDs, and a printable page
const { documentationCsv, documentationHtml } = await import(new URL("shared.js?v=check", frontend).href);
const doc = {
  version: 1,
  generated: "2026-11-01T14:20:00+00:00",
  gateways: [
    {
      entry_id: "g1",
      title: "FAM-USB <Keller>",
      model: "fam_usb",
      base_id: "FF-B7-44-80",
      note: "Keller, rechts neben dem Zähler", manual: [{ id: "m1", name: "Taster Flur <links>", address: "00-12-34-56", function: "direkt auf Licht Flur eingelernt" }], heard: [{ id: "00-21-63-43", rorg: "F6", dbm: -71, last: "2026-11-01T13:00:00+00:00" }], hidden_senders: ["00-11-22-33"],
      devices: [
        { name: "Licht Flur", id: "05-10-A2-C1", eep: "M5-38-08:eltako", eep_extra: [], area: "Flur", model: null, virtual: false, note: "Schrank 2, Platz 4", wall_switch: { id: "05-10-AA-01", on: "a0", off: "a1" }, senders: [{ profile: "central", id: "FF-B7-44-91", ute: false, test: "confirmed" }, { profile: "rocker", id: "FF-B7-44-92", ute: false, test: null }] },
        { name: "Fenster", id: "00-8A-12-3F", eep: "D5-00-01:std", eep_extra: [], area: null, model: null, virtual: false, wall_switch: null, senders: [] },
      ],
      pools: [{ id: "radio:g1", kind: "radio", start: "FF-B7-44-81", end: "FF-B7-44-FF", senders: [{ id: "FF-B7-44-91", device: "Licht Flur", profile: "central", state: "assigned" }, { id: "FF-B7-44-95", device: null, profile: "central", state: "blocked" }] }],
    },
  ],
};
// several gateways: the print gets an overview page first, one gateway alone does not
const two = { ...doc, gateways: [...doc.gateways, { ...doc.gateways[0], title: "MGW-ETH Dach", note: "", devices: [], heard: [] }] };
for (const lang of ["en", "de"]) {
  const t = TEXT[lang];
  const many = documentationHtml(two, t, (p) => p, lang);
  if (!many.includes(`<h2>${t.doc.overview}</h2>`) || !many.includes("MGW-ETH Dach")) errors.push(`shared.js: documentationHtml (${lang}) has no overview for two gateways`);
  if (documentationHtml(doc, t, (p) => p, lang).includes(`<h2>${t.doc.overview}</h2>`)) errors.push(`shared.js: documentationHtml (${lang}) shows an overview for one gateway`);
}
const { documentationSheet } = await import(new URL("shared.js?v=check", frontend).href);
for (const lang of ["en", "de"]) {
  const sheet = documentationSheet(doc, TEXT[lang], (p) => p, lang);
  if (!sheet.includes("FF-B7-44-91") || !sheet.includes("Schrank 2, Platz 4") || !sheet.includes("00-12-34-56")) errors.push(`shared.js: documentationSheet (${lang}) misses data`);
  if (sheet.includes("<Keller>") || sheet.includes("<links>") || /undefined|NaN/.test(sheet)) errors.push(`shared.js: documentationSheet (${lang}) does not escape or shows undefined`);
  if (!sheet.includes("landscape")) errors.push(`shared.js: documentationSheet (${lang}) is not landscape`);
}
const profile = (p) => TEXT.en.profiles[p] || p;
for (const lang of ["en", "de"]) {
  const t = TEXT[lang];
  const rows = documentationCsv(doc, t, profile).trim().split("\n");
  if (rows.length !== 1 + 2 + 1 + 1 + 1 + 1) errors.push(`shared.js: documentationCsv (${lang}) has ${rows.length} rows, expected 7`);
  if (!rows.some((r) => r.includes("00-21-63-43"))) errors.push(`shared.js: documentationCsv (${lang}) misses the heard sender`);
  const page = documentationHtml(doc, t, profile, lang);
  if (!page.includes("FF-B7-44-91") || !page.includes("05-10-AA-01") || !page.includes("00-11-22-33") || !page.includes("00-21-63-43")) errors.push(`shared.js: documentationHtml (${lang}) misses data`);
  if (!page.includes("Schrank 2, Platz 4") || !page.includes("Keller, rechts neben dem Zähler")) errors.push(`shared.js: documentationHtml (${lang}) misses the notes`);
  if (!documentationCsv(doc, t, profile).includes("Schrank 2, Platz 4")) errors.push(`shared.js: documentationCsv (${lang}) misses the note`);
  if (!page.includes("direkt auf Licht Flur eingelernt") || page.includes("<links>")) errors.push(`shared.js: documentationHtml (${lang}) misses or does not escape the manual entries`);
  if (page.includes("<Keller>") || !page.includes("&lt;Keller&gt;")) errors.push(`shared.js: documentationHtml (${lang}) does not escape the gateway name`);
  if (/undefined|NaN/.test(page)) errors.push(`shared.js: documentationHtml (${lang}) shows undefined or NaN`);
}

if (errors.length) {
  console.error(errors.join("\n"));
  process.exit(1);
}
console.log(`panel ok (${fileURLToPath(frontend)})`);
