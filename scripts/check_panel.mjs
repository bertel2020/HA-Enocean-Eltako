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
  version: 2,
  generated: "2026-11-01T14:20:00+00:00",
  gateways: [
    {
      entry_id: "g1",
      title: "FAM-USB <Keller>",
      model: "fam_usb",
      base_id: "FF-B7-44-80",
      note: "Keller, rechts neben dem Zähler", log: [{ time: "2026-10-26T09:12:00+00:00", kind: "teach_in", device: "05-10-A2-C1", detail: "Licht Flur: central" }], links: [{ key: "assigned|05-10-A2-C1|central", source: "assigned", from_kind: "ha", from_id: "FF-B7-44-91", from_name: "", to_key: "05-10-A2-C1", to_id: "05-10-A2-C1", to_name: "Licht Flur", role: "central", learn: "Funktion 45", status: "confirmed", teach_in: "2026-10-26T09:14:00+00:00", tested: null }, { key: "entered|k1", id: "k1", source: "entered", from_kind: "entered", from_id: "00-12-34-56", from_name: "Taster <rechts>", to_key: "", to_id: "", to_name: "Fremder Aktor", role: "rocker", learn: "", status: "entered", teach_in: null, tested: null }], manual: [{ id: "m1", name: "Taster Flur <links>", address: "00-12-34-56", function: "direkt auf Licht Flur eingelernt" }], heard: [{ id: "00-21-63-43", rorg: "F6", dbm: -71, last: "2026-11-01T13:00:00+00:00" }], hidden_senders: ["00-11-22-33"],
      devices: [
        { name: "Licht Flur", id: "05-10-A2-C1", eep: "M5-38-08:eltako", eep_extra: [], area: "Flur", model: null, virtual: false, note: "Schrank 2, Platz 4", location: "Schrank 2", circuit: "Klemme 12", fuse: "F3 B16", installed: "2026-10-01", revision: "2214", power: "Netz", wall_switch: { id: "05-10-AA-01", on: "a0", off: "a1" }, senders: [{ profile: "central", id: "FF-B7-44-91", ute: false, test: "confirmed" }, { profile: "rocker", id: "FF-B7-44-92", ute: false, test: null }] },
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
for (const lang of ["en", "de"]) {
  const text = TEXT[lang].doc.importDone([{ matched: true, notes: 3, manual: 1 }, { matched: false }]);
  if (!/3/.test(text) || !/1/.test(text) || /undefined|NaN/.test(text)) errors.push(`texts.js: importDone (${lang}) says "${text}"`);
}

// the sender tables: gateway senders 0 to 127 with the other senders of a device, buttons with their rockers,
// radio senders and the entries by hand
const { docTables, docBus, foldFree } = await import(new URL("shared.js?v=check", frontend).href);
const tdev = (over) => ({ name: "", id: "", eep: "", eep_extra: [], area: null, model: null, virtual: false, category: "lighting", wall_switch: null, senders: [], location: "", bus_address: "", feedback_id: "", ...over });
const tgw = {
  title: "FAM14",
  base_id: "FF-B6-40-80",
  hidden_senders: [], heard: [], links: [], log: [], note: "",
  supplies: [{ name: "FSNT14-12V", watts: "1" }],
  manual: [{ id: "m1", name: "Taster Garage", address: "00-AA-00-01", function: "direkt eingelernt" }, { id: "m2", name: "Zähler F3Z14D", address: "", function: "Haus", bus_address: "12", feedback_id: "00008C0C", bus_power: "" }],
  devices: [
    tdev({ name: "Licht Flur", id: "05-10-A2-C1", note_key: "k1", model: "FSR14-4x", bus_address: "1", feedback_id: "00000081", bus_power: "0,4", location: "Flur", wall_switch: { id: "FE-8A-31-C2", on: "a0", off: "a1" } }),
    tdev({ name: "Rollladen Bad", id: "05-10-A2-C2", note_key: "k2", category: "covers", bus_address: "9", bus_power_table: 0.42, wall_switch: { id: "FE-8A-34-07", on: "a0", off: "b0" } }),
    tdev({ name: "Taster Haustür", id: "FE-8A-31-C2", category: "buttons", model: "F4T55E", location: "Flur" }),
    tdev({ name: "Raumregler Temperatur", id: "FE-91-2A-40", category: "climate", model: "FUTH55", group: "Raumregler Wohnzimmer", eep: "A5-10-06:eltako", eep_extra: ["A5-04-01:std"] }),
    tdev({ name: "Raumregler Taste", id: "FE-91-2A-41", category: "sensors", model: "FUTH55", group: "Raumregler Wohnzimmer", eep: "F6-02-01:std" }),
  ],
  pools: [{ id: "radio:g1", kind: "radio", start: "FF-B6-40-81", end: "FF-B6-40-FF", senders: [
    { id: "FF-B6-40-9D", device: "Licht Flur", ref: "k1", profile: "central", state: "assigned" },
    { id: "FF-B6-40-DD", device: "Licht Flur", ref: "k1", profile: "rocker", state: "assigned" },
    { id: "FF-B6-40-A4", device: "Rollladen Bad", ref: "k2", profile: "central", state: "assigned" },
    { id: "FF-B6-40-DE", device: null, ref: "gone", profile: "central", state: "blocked" },
  ] }],
};
const tprofile = (p) => p;
for (const lang of ["en", "de"]) {
  const t = TEXT[lang];
  // the buttons and fields the panel reads must have a text, or they show up empty
  for (const [where, text] of [["inst.links.tablesCsv", t.inst.links.tablesCsv], ["doc.manualFunctionHead", t.doc.manualFunctionHead], ["doc.manualBusAddress", t.doc.manualBusAddress], ["doc.manualFeedback", t.doc.manualFeedback], ["doc.manualWatts", t.doc.manualWatts], ["doc.supplyTitle", t.doc.supplyTitle], ["doc.supplyName", t.doc.supplyName], ["doc.supplyWatts", t.doc.supplyWatts], ...["group", "bus_address", "feedback_id", "bus_power"].map((f) => [`inst.fields.${f}`, t.inst.fields[f]])]) {
    if (!text) errors.push(`texts.js: ${where} (${lang}) is empty`);
  }
  const parts = docTables(tgw, t, tprofile);
  const at = (n) => parts.senders[n];
  if (parts.senders.length !== 128 || at(0).id !== "FFB64080" || !at(0).gateway) errors.push(`shared.js: docTables (${lang}) has ${parts.senders.length} gateway sender rows or a wrong base ID`);
  if (!at(1).free || at(29).id !== "FFB6409D" || at(29).bus !== "1" || at(29).feedback !== "00000081" || at(29).second !== "93 →" || at(93).second !== "← 29") errors.push(`shared.js: docTables (${lang}) gets the sender number, the fields or the second mode wrong`);
  // the pairing is the device's, not a distance: 29 and 93 are one device, a third sender of it points to both, a device with one sender points nowhere
  const threeSenders = { ...tgw, pools: [{ ...tgw.pools[0], senders: [...tgw.pools[0].senders, { id: "FF-B6-40-C0", device: "Licht Flur", ref: "k1", profile: "central", state: "assigned" }] }] };
  const three = docTables(threeSenders, t, tprofile).senders;
  if (three[29].second !== "64 →, 93 →") errors.push(`shared.js: docTables (${lang}) pairs a device's senders wrongly: ${three[29].second}`);
  if (three[64].second !== "← 29, 93 →" || at(36).second !== "") errors.push(`shared.js: docTables (${lang}) pairs wrongly or pairs a lone sender: ${three[64].second}/${at(36).second}`);
  if (!at(94).blocked || at(94).id !== "FFB640DE" || !at(127).free) errors.push(`shared.js: docTables (${lang}) misses the blocked or the free numbers`);
  const folded = foldFree(parts.senders);
  if (folded.length >= 128 || folded[1].nr !== 1 || folded[1].to !== 28) errors.push(`shared.js: foldFree (${lang}) does not fold the free numbers`);
  const haus = parts.buttons.find((b) => b.id === "FE-8A-31-C2");
  if (!haus || haus.device !== "F4T55E" || haus.left.join() !== "Licht Flur (29)" || haus.right.length !== 0) errors.push(`shared.js: docTables (${lang}) puts the wall switch rockers wrong`);
  const bad = parts.buttons.find((b) => b.id === "FE-8A-34-07");
  if (!bad || bad.left[0] !== `Rollladen Bad ${t.doc.tbl.on} (36)` || bad.right[0] !== `Rollladen Bad ${t.doc.tbl.off} (36)`) errors.push(`shared.js: docTables (${lang}) does not split on and off over two rockers`);
  if (parts.radio.length !== 3 || parts.radio[0].eep !== "A5-10-06:eltako, A5-04-01:std" || parts.radio[0].description !== "Raumregler Wohnzimmer" || parts.radio[1].sends !== "Raumregler Taste" || parts.radio[2].id !== "00-AA-00-01") errors.push(`shared.js: docTables (${lang}) has the wrong radio senders`);
  const grouped = documentationHtml({ version: 2, generated: "2026-11-01T14:20:00+00:00", gateways: [tgw] }, t, tprofile, lang);
  if (!grouped.split('<section class="sec sec-radio">')[1]?.split("</section>")[0].includes('rowspan="2">FUTH55')) errors.push(`shared.js: documentationHtml (${lang}) does not put the IDs of one device in one block`);
  const bus = docBus(tgw, t);
  if (bus.rows.map((r) => r.address).join() !== "1,9,12" || bus.sum !== 0.82 || bus.counted !== 2 || bus.rows[2].power !== null || bus.rows[0].from !== "user" || bus.rows[1].from !== "table") errors.push(`shared.js: docBus (${lang}) sorts, sums or takes the table wrongly: ${JSON.stringify(bus)}`);
  if (bus.percent !== 82 || bus.capacity !== 1 || bus.supplies.length !== 1 || bus.supplies[0].standard || bus.supplies[0].load !== 0.82 || bus.items.filter((x) => x.free).map((x) => `${x.from}-${x.to}`).join() !== "2-8,10-11,13-126") errors.push(`shared.js: docBus (${lang}) has the wrong load or free runs: ${JSON.stringify(bus.items.filter((x) => x.free))}`);
  const four = { devices: [1, 2, 3, 4].map((n) => tdev({ name: `Kanal ${n}`, id: `05-10-00-0${n}`, note_key: `c${n}`, model: "FSR14-4x", bus_address: String(n), bus_power_table: 0.7, group: n < 4 ? "Flur" : "" })), manual: [], supplies: [] };
  const grouped4 = docBus(four, t, { supply_watts: 12 });
  if (grouped4.sum !== 1.4 || grouped4.rows[1].from !== "group" || grouped4.capacity !== 12 || !grouped4.supplies[0].standard || grouped4.multi.length !== 0) errors.push(`shared.js: docBus (${lang}) counts the channels of one device wrongly: ${JSON.stringify([grouped4.sum, grouped4.multi])}`);
  const ungrouped = docBus({ ...four, devices: four.devices.map((d) => ({ ...d, group: "" })), supplies: [] }, t);
  if (ungrouped.multi.join() !== "FSR14-4x" || ungrouped.sum !== 2.8) errors.push(`shared.js: docBus (${lang}) does not warn about ungrouped channels`);
  const dup = docBus({ devices: [tdev({ name: "A", id: "1", bus_address: "5", bus_power: "1" }), tdev({ name: "B", id: "2", bus_address: "5", bus_power: "1" })], manual: [], supplies: [] }, t);
  if (dup.dups.join() !== "5") errors.push(`shared.js: docBus (${lang}) misses an address given twice`);
  // several supplies: each loaded by the addresses it feeds, and addresses no supply feeds are named
  const split = docBus({ devices: [1, 9, 20].map((n) => tdev({ name: `G${n}`, id: String(n), bus_address: String(n), bus_power: "2" })), manual: [], supplies: [{ name: "A", watts: "12", first: "1", last: "8" }, { name: "B", watts: "6", first: "9", last: "12" }] }, t);
  if (split.supplies.map((x) => `${x.load}/${x.percent}`).join() !== "2/17,2/33" || split.capacity !== 18 || split.percent !== 33 || split.unfed.join() !== "20") errors.push(`shared.js: docBus (${lang}) loads several supplies wrongly: ${JSON.stringify([split.supplies, split.unfed])}`);
  const noRange = docBus({ devices: [1, 9].map((n) => tdev({ name: `G${n}`, id: String(n), bus_address: String(n), bus_power: "2" })), manual: [], supplies: [{ name: "A", watts: "12" }, { name: "B", watts: "6" }] }, t);
  if (noRange.supplies.some((x) => x.load !== null) || noRange.capacity !== 18 || noRange.percent !== 22) errors.push(`shared.js: docBus (${lang}) invents a load per supply without ranges`);
  const splitPage = documentationHtml({ version: 2, generated: "2026-11-01T14:20:00+00:00", gateways: [{ ...tgw, supplies: split.supplies.map((x) => ({ name: x.name, watts: String(x.capacity), first: String(x.first), last: String(x.last) })) }] }, t, tprofile, lang);
  if (!splitPage.includes(t.doc.tbl.supplyRange(1, 8)) || /undefined|NaN/.test(splitPage)) errors.push(`shared.js: documentationHtml (${lang}) misses the range of a supply`);
  const busPage = documentationHtml({ version: 2, generated: "2026-11-01T14:20:00+00:00", gateways: [tgw] }, t, tprofile, lang);
  if (!busPage.includes(t.doc.tbl.busWarn) || !busPage.includes(t.doc.tbl.busMissing(1)) || !busPage.includes("FSNT14-12V") || !/0[.,]42 W\*/.test(busPage)) errors.push(`shared.js: documentationHtml bus (${lang}) misses the sum, the supply, the warning or the table mark`);
  const tcsv = documentationCsv({ gateways: [tgw] }, t, tprofile, "tables").trim().split("\n");
  if (tcsv.length < 128 + 10 || !tcsv.some((r) => r.includes("FE-8A-31-C2") && r.includes("Licht Flur (29)"))) errors.push(`shared.js: documentationCsv tables (${lang}) has ${tcsv.length} rows`);
  const tpage = documentationHtml({ version: 2, generated: "2026-11-01T14:20:00+00:00", gateways: [tgw] }, t, tprofile, lang);
  if (!tpage.includes("FFB6409D") || !tpage.includes("F4T55E") || !tpage.includes("FUTH55") || /undefined|NaN/.test(tpage)) errors.push(`shared.js: documentationHtml tables (${lang}) misses data or shows undefined`);
}
const profile = (p) => TEXT.en.profiles[p] || p;
for (const lang of ["en", "de"]) {
  const t = TEXT[lang];
  const rows = documentationCsv(doc, t, profile).trim().split("\n");
  if (rows.length !== 1 + 2 + 1 + 1 + 1 + 1) errors.push(`shared.js: documentationCsv (${lang}) has ${rows.length} rows, expected 7`);
  if (new Set(rows.map((r) => r.split('","').length)).size !== 1) errors.push(`shared.js: documentationCsv (${lang}) has rows of different widths`);
  const linkRows = documentationCsv(doc, t, profile, "links").trim().split("\n");
  if (linkRows.length !== 3 || !linkRows[1].includes("Funktion 45") || !linkRows[2].includes("Fremder Aktor")) errors.push(`shared.js: documentationCsv links (${lang}) has ${linkRows.length} rows`);
  if (!rows.some((r) => r.includes("00-21-63-43"))) errors.push(`shared.js: documentationCsv (${lang}) misses the heard sender`);
  const page = documentationHtml(doc, t, profile, lang);
  if (!page.includes("FF-B7-44-91") || !page.includes("05-10-AA-01") || !page.includes("00-11-22-33") || !page.includes("00-21-63-43")) errors.push(`shared.js: documentationHtml (${lang}) misses data`);
  if (!page.includes("Schrank 2, Platz 4") || !page.includes("Keller, rechts neben dem Zähler")) errors.push(`shared.js: documentationHtml (${lang}) misses the notes`);
  if (!documentationCsv(doc, t, profile).includes("Schrank 2, Platz 4")) errors.push(`shared.js: documentationCsv (${lang}) misses the note`);
  if (!page.includes("direkt auf Licht Flur eingelernt") || page.includes("<links>")) errors.push(`shared.js: documentationHtml (${lang}) misses or does not escape the manual entries`);
  if (!page.includes("table-header-group") || !page.includes("break-after:avoid")) errors.push(`shared.js: documentationHtml (${lang}) lets a table break without its header`);
  if (page.includes("<Keller>") || !page.includes("&lt;Keller&gt;")) errors.push(`shared.js: documentationHtml (${lang}) does not escape the gateway name`);
  if (/undefined|NaN/.test(page)) errors.push(`shared.js: documentationHtml (${lang}) shows undefined or NaN`);
  for (const section of ["handover", "cabinet", "gwsenders", "buttons", "radio", "links", "swap", "ids", "log"]) {
    if (!page.includes(`sec-${section}`) || !page.includes(`id="show-${section}"`)) errors.push(`shared.js: documentationHtml (${lang}) has no ${section} section`);
  }
  if (!page.includes("Klemme 12") || !page.includes("F3 B16") || !page.includes("Funktion 45") || !page.includes("Fremder Aktor")) errors.push(`shared.js: documentationHtml (${lang}) misses typed fields or links`);
  if (!page.includes('class="box"') || page.includes("<rechts>")) errors.push(`shared.js: documentationHtml (${lang}) has no checklist, or does not escape a link`);
  if (page.includes('id="show-log" checked')) errors.push(`shared.js: documentationHtml (${lang}) shows the log by default`);
}

if (errors.length) {
  console.error(errors.join("\n"));
  process.exit(1);
}
console.log(`panel ok (${fileURLToPath(frontend)})`);
