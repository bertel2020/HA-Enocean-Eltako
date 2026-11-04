// The Installation view of the panel: what is known of the installation, and what the user writes
// down about it. Three tabs: the devices by area or place, a table of the devices with typed
// fields that are edited in place (also for a selection, or pasted from a spreadsheet), and the
// event log. Everything comes from the documentation command; edits go back with set_fields. Its
// methods are added to the panel class (this = the panel).

const VERSION = new URL(import.meta.url).search;
const { ICON, docBus, docTables, esc, foldFree, svg } = await import(`./shared.js${VERSION}`);
const { BUS_STYLE, busState, busView } = await import(`./bus.js${VERSION}`);

// the typed fields of a device, in table order; installed is a date
export const INSTALLATION_FIELDS = ["location", "group", "circuit", "bus_address", "feedback_id", "bus_power", "fuse", "installed", "revision", "power", "note"];
// the tabs: the devices (with a switch between the views), the sender IDs, the links, the log
const TABS = ["devices", "gwsenders", "links", "log"];
// the views of the devices tab, and the kinds of device each one shows
const VIEWS = ["all", "bus", "funk", "virt"];
const VIEW_KINDS = { all: null, bus: ["bus", "psu"], funk: ["sensor", "taster", "aktor"], virt: ["virt"] };
const VIEW_OF = { bus: "bus", psu: "bus", sensor: "funk", taster: "funk", aktor: "funk", virt: "virt" };
// which kinds a field makes sense for (a field not listed here is for every kind): a button has no circuit or
// fuse, a sensor no bus address, a bus device no battery
const FIELD_KINDS = {
  circuit: ["bus", "aktor"], fuse: ["bus", "aktor"], group: ["bus", "sensor", "aktor"], revision: ["bus", "aktor"],
  bus_address: ["bus"], feedback_id: ["bus"], bus_power: ["bus"], power: ["taster", "sensor", "aktor"],
};
// the fields every kind has: the table of all kinds shows only these; the others appear when a kind is chosen
const FUSE_KINDS = new Set(["bus", "aktor", "psu"]); // the kinds that hang on a circuit and a fuse
// the kind of a device: virtual (Home Assistant sends), on the Eltako bus (it has a bus address), else
// by what it is: a button, a sensor or an actuator on radio
// Home Assistant sends from it: a virtual sensor, or a button of the category virtual
const isVirtual = (d) => Boolean(d.virtual) || d.category === "virtual";
const idNum = (id) => parseInt(String(id).replace(/-/g, ""), 16);
// the sender numbers (0 to 127 of the radio pool) that each device holds, by its note key
const senderNumbers = (gw) => {
  const base = gw.base_id ? idNum(gw.base_id) : null;
  const pool = (gw.pools ?? []).find((p) => p.kind === "radio");
  const numbers = new Map();
  if (base === null || !pool) return numbers;
  for (const s of pool.senders) if (s.ref) numbers.set(s.ref, [...(numbers.get(s.ref) ?? []), idNum(s.id) - base].sort((a, b) => a - b));
  return numbers;
};
// the Eltako series 14 (FSR14, FUD14, FSB14, F3Z14D ...) hangs on the FAM14 bus
const BUS_MODEL = /^F[A-Z0-9]{1,4}14/;
// a device other devices can be taught into: lights and covers, and the heating actuators on the bus (not a room controller)
const isActuator = (d) => !isVirtual(d) && (["lighting", "covers"].includes(d.category) || (d.category === "climate" && kindOf(d) === "bus"));
const kindOf = (d) => (d.psu ? "psu" : d.manual ? (/^\d+$/.test(d.bus_address ?? "") ? "bus" : ["taster", "sensor", "aktor"].includes(d.kindRaw) ? d.kindRaw : "taster") : isVirtual(d) ? "virt" : /^\d+$/.test(d.bus_address ?? "") || BUS_MODEL.test(d.model ?? "") ? "bus" : d.category === "buttons" ? "taster" : ["sensors", "meters", "climate"].includes(d.category) ? "sensor" : "aktor");
// the columns of the radio view that can be shown; the first three at first
const FUNK_COLUMNS = ["loc", "id", "model", "sends", "pow", "circuit", "fuse", "grp", "sig", "conn"];
const FUNK_DEFAULT = ["id", "sig", "conn"];
const SIGNAL_FRESH = 24 * 3600; // heard within a day: fine; within a week: late; else: silent
const SIGNAL_LATE = 7 * 24 * 3600;
// a field of an entry written by hand, by the name the table gives it
const MANUAL_FIELD = { location: "location", power: "power", note: "function", bus_address: "bus_address", feedback_id: "feedback_id", bus_power: "bus_power", circuit: "circuit", fuse: "fuse", installed: "installed", model: "model" };
// 12 V DC supplies of Eltako for the bus, by their rated power (Eltako data sheets); the name is the type designation
const SUPPLY_PRESETS = [
  { name: "FSNT14-12V/12W", watts: "12" },
  { name: "SNT12-230V/12V DC-1A", watts: "12" },
  { name: "SNT15-12VDC/15W", watts: "15" },
  { name: "WNT15-12VDC/24W", watts: "24" },
];
const RESERVE_LIMIT = 2 / 3; // from this share of its rated power a supply gets the advice to plan another one
const SUPPLY_BLANK = { name: "", watts: "", first: "", last: "", location: "", circuit: "", fuse: "", note: "" };
const wnum = (text) => (text && /^\d+([.,]\d+)?$/.test(String(text).trim()) ? Number(String(text).trim().replace(",", ".")) : null);
const anum = (text) => (/^\d+$/.test(text ?? "") ? Number(text) : null);
const round2 = (n) => Math.round(n * 100) / 100;
// a place is written "cabinet · row · slot"; older notes held free text, split at a comma
const placeParts = (text) => {
  const value = String(text ?? "");
  const parts = value.split(value.includes("·") ? "·" : ",").map((p) => p.trim());
  return [parts[0] ?? "", parts[1] ?? "", parts.slice(2).join(", ")];
};
const joinPlace = (parts) => parts.map((p) => p.trim()).join(" · ").replace(/(\s·\s?)+$/, "").replace(/^\s·\s?$/, "");
const SAVE_DELAY = 600; // ms after the last key
// the columns of the device table in groups that are shown or hidden
const COLUMN_GROUPS = {
  place: ["area", "location", "circuit", "fuse"],
  bus: ["group", "bus_address", "feedback_id", "bus_power"],
  upkeep: ["installed", "revision", "power", "note"],
};
const COLUMNS_KEY = "enocean_eltako_installation_columns"; // before: the groups shown, per browser
const FIELDS_KEY = "enocean_eltako_installation_fields"; // the single columns shown, per browser
const GROUP_KEY = "enocean_eltako_installation_group"; // how the devices table is grouped, per browser
const GROUPS = ["", "area", "location", "gateway"];
const POOL_KEY = "enocean_eltako_installation_pool_closed"; // the sender ID pool is folded, per browser
const loadPoolOpen = () => {
  try {
    return localStorage.getItem(POOL_KEY) !== "1";
  } catch (err) {
    return true;
  }
};
const savePoolOpen = (open) => {
  try {
    localStorage.setItem(POOL_KEY, open ? "" : "1");
  } catch (err) {
    // not saved: shown for this visit
  }
};
const ALL_COLUMNS = Object.values(COLUMN_GROUPS).flat();
const loadColumns = () => {
  // the single columns; a choice of groups from before becomes the columns of those groups
  try {
    const fields = JSON.parse(localStorage.getItem(FIELDS_KEY));
    if (Array.isArray(fields)) return new Set(fields.filter((f) => ALL_COLUMNS.includes(f)));
    const groups = JSON.parse(localStorage.getItem(COLUMNS_KEY));
    if (Array.isArray(groups)) return new Set(groups.filter((g) => g in COLUMN_GROUPS).flatMap((g) => COLUMN_GROUPS[g]));
  } catch (err) {
    // no storage: the default
  }
  return new Set(COLUMN_GROUPS.place);
};
const saveColumns = (columns) => {
  try {
    localStorage.setItem(FIELDS_KEY, JSON.stringify([...columns]));
  } catch (err) {
    // not saved: shown for this visit
  }
};
const loadGroup = () => {
  try {
    const saved = localStorage.getItem(GROUP_KEY);
    if (saved !== null && GROUPS.includes(saved)) return saved;
  } catch (err) {
    // no storage: the default
  }
  return "location"; // by cabinet and row
};
const saveGroup = (group) => {
  try {
    localStorage.setItem(GROUP_KEY, group);
  } catch (err) {
    // not saved: shown for this visit
  }
};

// the view's state when the panel starts
export const installationState = () => ({
  doc: null, error: false, tab: "devices", view: "all", art: "all", miss: { loc: false, fuse: false }, folded: new Set(), colMenu: false, sheet: false, placeEdit: "", nameEdit: "", docDraft: {}, devSort: "name", devDir: 1, devPg: {}, devPs: 25, linkSort: "name", linkDir: 1, linkPg: 0, linkPs: 25, linkLearn: false, sid: {}, log: { kinds: new Set(), period: "all", dir: -1, pg: 0, ps: 25 }, funkCols: new Set(FUNK_DEFAULT), docForm: false, docError: "", hl: "", poolOpen: loadPoolOpen(), columns: loadColumns(), group: loadGroup(), placeText: new Set(), linkView: "actuator", linkFilter: "all", linkSource: "all", linkAdd: "", testing: new Set(), selected: new Set(), paste: "", pasteResult: "", q: "", bus: busState(), back: null,
});

export const INSTALLATION_STYLE = `
  .installation { padding-bottom: 8px; }
  .installation .itop { display: flex; flex-wrap: wrap; gap: 8px 12px; align-items: center; padding: 12px 16px; border-bottom: 1px solid var(--line); }
  .installation .itop .tabs { display: flex; gap: 6px; flex: 1 1 340px; flex-wrap: wrap; }
  .installation .itools { display: flex; gap: 6px; flex: 1 1 auto; flex-wrap: wrap; justify-content: flex-end; }
  .installation .ibody { padding: 12px 16px; display: grid; grid-template-columns: minmax(0, 1fr); gap: 16px; }
  .installation h3 { margin: 0 0 8px; font-size: calc(14px * var(--fs)); font-weight: 500; }
  .installation .isub { color: var(--muted); font-size: calc(12px * var(--fs)); }
  .installation .cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 10px; }
  .installation .gcard { border: 1px solid var(--line); border-radius: 12px; padding: 12px 14px; display: grid; gap: 6px; align-content: start; }
  .installation .gcard b { font-weight: 500; }
  .installation .gcard ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 4px; font-size: calc(13px * var(--fs)); }
  .installation .gcard .open { font-size: calc(12px * var(--fs)); color: var(--warn); }
  .installation .tablewrap { overflow-x: auto; }
  .installation table.itable { width: 100%; border-collapse: collapse; font-size: calc(13px * var(--fs)); }
  .installation .itable th { text-align: left; font-weight: 500; font-size: calc(12px * var(--fs)); color: var(--muted); padding: 6px 8px 6px 0; border-bottom: 1px solid var(--line); white-space: nowrap; }
  .installation .itable td { padding: 4px 8px 4px 0; border-bottom: 1px solid var(--line); vertical-align: middle; }
  .installation .itable th:first-child, .installation .itable td:first-child { width: 36px; padding-left: 14px; padding-right: 4px; }
  .installation .tabwarn { color: var(--warn); font-weight: 500; }
  .installation .itable td.name { min-width: 160px; }
  .installation .unnamed { font-style: italic; color: var(--muted); }
  .installation .tag.doc { background: none; border: 1px dashed var(--line); color: var(--muted); }
  .installation summary.tag { list-style: none; cursor: pointer; }
  .installation summary.tag::-webkit-details-marker { display: none; }
  .installation details.kindmenu, .installation details.rowmenu { display: inline-block; }
  .installation details.kindmenu .items, .installation details.rowmenu .items { left: 0; right: auto; min-width: 0; z-index: 6; }
  .installation details.rowmenu .items { left: auto; right: 0; white-space: nowrap; }
  /* the narrow last column of every table: the row menu (⋮) at the same place in each row */
  .installation .itable th.rmenu, .installation .itable td.rmenu { width: 1%; padding: 2px 6px 2px 0; text-align: right; white-space: nowrap; }
  .installation details.colmenu .items, .installation details.rowmenu .items { max-width: calc(100vw - 32px); }
  .installation .colgroup { display: flex; align-items: baseline; gap: 6px; margin-top: 6px; }
  .installation .colgroup:first-child { margin-top: 0; }
  .installation .colgroup b { font-weight: 500; flex: 1; }
  .installation .colgroup .tag { cursor: pointer; border: 0; font: inherit; font-size: calc(11px * var(--fs)); }
  /* the counters of the devices view: text, not boxes */
  .installation .stiles.quiet { gap: 4px 14px; }
  .installation .stiles.quiet .stile { background: none; padding: 2px 4px; border-radius: 8px; }
  .installation .stiles.quiet .stile b { font-size: calc(15px * var(--fs)); }
  .installation .stiles.quiet .stile[aria-pressed="true"] { background: var(--accent-soft); border-color: transparent; }
  /* an empty place: a quiet dash that turns into "+ add place" on hover or focus */
  .installation .placeadd.empty { min-width: 90px; color: color-mix(in srgb, var(--muted) 70%, transparent); }
  .installation .placeadd.empty .hv { display: none; }
  .installation .placeadd.empty:hover .ph, .installation .placeadd.empty:focus-visible .ph { display: none; }
  .installation .placeadd.empty:hover .hv, .installation .placeadd.empty:focus-visible .hv { display: inline; }
  .installation .place select { flex: 1.5 1 0; min-width: 0; font: inherit; font-size: calc(12px * var(--fs)); padding: 4px 4px; border: 0; background: transparent; color: inherit; }
  .installation .place .placeclr { flex: none; all: unset; cursor: pointer; color: var(--muted); padding: 0 8px; font-size: calc(12px * var(--fs)); }
  .installation .place .placeclr:hover, .installation .place .placeclr:focus-visible { color: var(--bad); }
  /* one quiet dash for an empty field, a field that does not apply and an empty place */
  .installation .itable input.cell::placeholder, .installation .itable td .dash { color: color-mix(in srgb, var(--muted) 70%, transparent); opacity: 1; }
  .installation .itable input.cell:focus::placeholder { opacity: 0; }
  .installation details.kindmenu .items button, .installation details.rowmenu .items button { all: unset; cursor: pointer; padding: 4px 6px; border-radius: 4px; }
  .installation details.kindmenu .items button:hover, .installation details.rowmenu .items button:hover { background: var(--soft); }
  .installation .namelink { all: unset; cursor: pointer; color: inherit; }
  .installation .namelink:hover, .installation .namelink:focus-visible { color: var(--accent); text-decoration: underline; }
  .installation .itable input.cell { width: 100%; min-width: 90px; box-sizing: border-box; font: inherit; font-size: calc(13px * var(--fs)); padding: 4px 8px; border: 1px solid transparent; border-radius: 6px; background: transparent; color: inherit; }
  .installation .itable input.cell[data-in-field="location"], .installation .itable input.cell[data-in-field="note"] { min-width: 200px; }
  .installation .itable input.cell[data-in-field="group"] { min-width: 170px; }
  .installation .itable input.cell[data-in-field="bus_address"] { min-width: 70px; }
  .installation .itable input.cell[data-in-field="feedback_id"] { min-width: 100px; }
  .installation .itable input.cell[data-in-field="bus_power"] { min-width: 72px; max-width: 96px; text-align: right; }
  .installation .itable input.cell[data-in-field="bus_address"], .installation .itable input.cell[data-in-field="feedback_id"] { font-family: ui-monospace, monospace; font-size: calc(12px * var(--fs)); }
  .installation .itable input.cell::placeholder { color: color-mix(in srgb, var(--muted) 60%, transparent); }
  .installation .itable input.cell:hover { border-color: var(--line); }
  .installation .itable input.cell:focus { border-color: var(--accent); outline: none; background: var(--surface); }
  .installation .itable input.cell.bad { border-color: var(--warn); }
  .installation input.isearch { width: 100%; max-width: 320px; box-sizing: border-box; font: inherit; font-size: calc(13px * var(--fs)); padding: 6px 10px; border: 1px solid var(--line); border-radius: 8px; background: transparent; color: inherit; }
  .installation .bulk { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; padding: 8px 12px; border: 1px solid var(--accent); border-radius: 10px; background: var(--accent-soft); }
  .installation .bulk input, .installation .bulk select { font: inherit; font-size: calc(13px * var(--fs)); padding: 4px 8px; border: 1px solid var(--line); border-radius: 6px; background: var(--surface); color: inherit; }
  .installation textarea.paste { width: 100%; min-height: 90px; box-sizing: border-box; font: calc(12px * var(--fs)) ui-monospace, monospace; padding: 8px; border: 1px solid var(--line); border-radius: 8px; background: transparent; color: inherit; }
  .installation .log td.kind { white-space: nowrap; }
  .installation .none { color: var(--muted); padding: 8px 0; }
  .installation .itop { padding-bottom: 0; align-items: flex-end; }
  .installation .itop .itab { font-size: calc(15px * var(--fs)); padding: 10px 14px 12px; }
  .installation .itop .itools { padding-bottom: 8px; }
  .installation .itop .groups { display: flex; gap: 4px; flex: 1 1 340px; flex-wrap: wrap; }
  .installation .itab { font: inherit; font-size: calc(14px * var(--fs)); font-weight: 500; color: var(--muted); background: none; border: 0; border-bottom: 2px solid transparent; padding: 8px 12px 10px; margin-bottom: -1px; cursor: pointer; }
  .installation .itab:hover { color: var(--text); }
  .installation .itab[aria-selected="true"] { color: var(--accent); border-bottom-color: var(--accent); }
  .installation .itab:focus-visible { outline: 2px solid var(--accent); outline-offset: -2px; border-radius: 6px; }
  .installation .isubtabs { display: flex; gap: 4px; flex-wrap: wrap; padding: 10px 16px 0; }
  .installation .isubtabs .itab { font-size: calc(13px * var(--fs)); font-weight: 400; padding: 5px 12px; margin: 0; border: 0; border-radius: 14px; }
  .installation .isubtabs .itab[aria-selected="true"] { background: var(--accent-soft); font-weight: 500; }
  .installation section.gw { border: 1px solid var(--line); border-radius: 12px; padding: 12px 14px 14px; display: grid; grid-template-columns: minmax(0, 1fr); gap: 10px; min-width: 0; }
  .installation .itools .seg { flex-wrap: wrap; max-width: 100%; }
  .installation .lnone { overflow-wrap: anywhere; white-space: normal; }
  .installation .gwhead { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; }
  .installation .gwhead h3 { margin: 0; }
  .installation .gbar { display: flex; align-items: center; gap: 10px; }
  .installation .ibody > p.isub { max-width: 100ch; margin: 0; }
  .installation .gcard { grid-template-columns: minmax(0, 1fr); }
  .installation .gcard li { white-space: normal; overflow-wrap: anywhere; }
  .installation .seg { display: inline-flex; border: 1px solid var(--line); border-radius: 16px; overflow: hidden; }
  .installation .seg button { font: inherit; font-size: calc(13px * var(--fs)); color: var(--muted); background: none; border: 0; padding: 5px 14px; cursor: pointer; }
  .installation .seg button + button { border-left: 1px solid var(--line); }
  .installation .seg button[aria-pressed="true"] { background: var(--accent-soft); color: var(--accent); font-weight: 500; }
  .installation .gwempty { display: grid; justify-items: start; gap: 10px; padding: 8px 0 2px; color: var(--muted); font-size: calc(13px * var(--fs)); }
  .installation .gwempty p { margin: 0; max-width: 60ch; }
  .installation details.poolbox { border-bottom: 1px solid var(--line); }
  .installation details.poolbox > summary { cursor: pointer; padding: 10px 16px; font-size: calc(14px * var(--fs)); font-weight: 500; display: flex; gap: 8px; align-items: baseline; flex-wrap: wrap; }
  .installation details.poolbox > summary .isub { font-weight: 400; }
  .installation details.imenu { position: relative; }
  .installation details.imenu summary { list-style: none; cursor: pointer; }
  .installation details.imenu summary::-webkit-details-marker { display: none; }
  .installation .imenu .items { position: absolute; right: 0; z-index: 5; margin-top: 4px; min-width: 220px; display: grid; padding: 4px; background: var(--surface); border: 1px solid var(--line); border-radius: 10px; }
  .installation .imenu .items button { text-align: left; font: inherit; font-size: calc(13px * var(--fs)); color: inherit; background: none; border: 0; border-radius: 6px; padding: 7px 10px; cursor: pointer; }
  .installation .imenu .items button:hover { background: var(--soft); }
  .installation .imenu summary.iconbtn { width: 36px; height: 36px; border: 1px solid var(--line); border-radius: 18px; display: grid; place-items: center; color: var(--text); }
  .installation .imenu summary.iconbtn:hover { background: var(--soft); }
  .installation .imenu .items button { display: flex; align-items: center; gap: 10px; }
  .installation .imenu .items button svg { width: 18px; height: 18px; flex: none; color: var(--muted); }
  .installation .imenu .items hr { border: 0; border-top: 1px solid var(--line); margin: 4px 0; width: 100%; }
  .installation .itable td.num, .installation .itable th.num { text-align: right; white-space: nowrap; }
  .installation .itable tr.free td { color: var(--muted); background: var(--soft); font-size: calc(12px * var(--fs)); padding: 3px 8px 3px 0; }
  .installation .itable td.mono, .installation .mono { font-family: ui-monospace, monospace; font-size: calc(12px * var(--fs)); white-space: nowrap; }
  .installation .itable tr.outside td { font-weight: 500; color: var(--muted); border-top: 1px solid var(--line); }
  .installation .progress { display: flex; align-items: center; gap: 10px; font-size: calc(12px * var(--fs)); color: var(--muted); }
  .installation .progress .barbg { flex: 1; max-width: 260px; height: 6px; border-radius: 3px; background: var(--soft); border: 1px solid var(--line); overflow: hidden; }
  .installation .progress .barbg i { display: block; height: 100%; background: var(--ok); }
  .installation .cerr { font-size: calc(11px * var(--fs)); color: var(--warn); padding: 2px 8px; }
  .installation .tag { display: inline-block; padding: 1px 8px; border-radius: 10px; font-size: calc(11px * var(--fs)); background: var(--soft); color: var(--muted); white-space: nowrap; }
  .installation .tag.warn { background: color-mix(in srgb, var(--warn) 18%, transparent); color: inherit; }
  .installation .tag.ok { background: color-mix(in srgb, var(--ok) 15%, transparent); color: inherit; }
  .installation .load { display: grid; grid-template-columns: minmax(120px, 220px) minmax(80px, 1fr) minmax(120px, 200px); gap: 10px; align-items: center; font-size: calc(13px * var(--fs)); }
  .installation .load .barbg { height: 8px; border-radius: 4px; background: var(--soft); border: 1px solid var(--line); overflow: hidden; }
  .installation .load .barbg i { display: block; height: 100%; background: var(--accent); }
  .installation .load .barbg i.hot { background: var(--warn); }
  .installation .load .r { text-align: right; color: var(--muted); }
  .installation .notes p { margin: 2px 0; }
  .installation .gbar { flex-wrap: wrap; }
  .installation .sig { white-space: nowrap; }
  .installation .sig .dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; background: var(--muted); }
  .installation .sig .dot.ok { background: var(--ok); }
  .installation .sig .dot.late { background: var(--warn); }
  .installation .sig .dot.silent { background: #d33; }
  .installation .lk a { color: var(--accent); cursor: pointer; text-decoration: underline; }
  .installation .itable tr.hl td { background: color-mix(in srgb, var(--warn) 22%, transparent); }
  .installation .docform { padding: 12px 14px; border: 1px solid var(--accent); border-radius: 10px; background: var(--accent-soft); margin-bottom: 12px; }
  .installation .docform h4 { margin: 0 0 2px; font-size: calc(14px * var(--fs)); font-weight: 500; }
  .installation .docform .dfgrid { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 10px 12px; margin: 10px 0; }
  .installation .docform label { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
  .installation .docform label > span { font-size: calc(11px * var(--fs)); color: var(--muted); }
  .installation .docform label.wide { grid-column: span 2; }
  .installation .docform .place { display: flex; align-items: center; gap: 4px; }
  .installation .docform input, .installation .docform select { font: inherit; font-size: calc(13px * var(--fs)); padding: 6px 8px; border: 1px solid var(--line); border-radius: 6px; background: var(--surface); color: inherit; min-width: 0; width: 100%; box-sizing: border-box; }
  .installation .docform .dfbtns { display: flex; gap: 8px; }
  .installation .docform .cerr { margin-top: 8px; }
  .installation .itable select.cell { font: inherit; font-size: calc(12px * var(--fs)); padding: 2px 6px; border: 1px solid var(--line); border-radius: 6px; background: var(--surface); color: inherit; }
  .installation .lcard { border: 1px solid var(--line); border-radius: 12px; overflow: hidden; margin-bottom: 10px; }
  .installation .lhead { display: flex; flex-wrap: wrap; gap: 8px 10px; align-items: center; padding: 10px 12px; background: var(--soft); }
  .installation .lhead .grow { flex: 1; }
  .installation .lhead b { font-weight: 500; font-size: calc(14px * var(--fs)); }
  .installation .lrow { display: grid; grid-template-columns: minmax(170px, 1.4fr) minmax(84px, .5fr) minmax(84px, .5fr) minmax(110px, .9fr) minmax(200px, 1.3fr) 76px; gap: 8px 12px; align-items: center; padding: 9px 14px; border-top: 1px solid var(--line); min-height: 44px; box-sizing: border-box; }
  .installation .lrow .nm { display: flex; flex-wrap: wrap; gap: 4px 8px; align-items: center; }
  .installation .lrow .lcol .tag, .installation .lrow .nm .tag, .installation .lrow .lstate .tag { white-space: nowrap; }
  .installation .lrow .lacts { display: flex; justify-content: flex-end; gap: 2px; }
  .installation .lrow .lacts .icon-btn { width: 32px; height: 32px; }
  .installation .lrow .lstate { flex-wrap: nowrap; white-space: nowrap; overflow: hidden; }
  .installation .lrow .lstate .isub { overflow: hidden; text-overflow: ellipsis; }
  .installation .nolearn .lrow { grid-template-columns: minmax(170px, 1.4fr) minmax(84px, .5fr) minmax(84px, .5fr) minmax(200px, 1.3fr) 76px; }
  .installation .lrow input.cell { width: 100%; min-width: 0; box-sizing: border-box; font: inherit; font-size: calc(13px * var(--fs)); padding: 4px 8px; border: 1px solid var(--line); border-radius: 6px; background: transparent; color: inherit; }
  .installation .lrow input.cell:focus { border-color: var(--accent); outline: none; background: var(--surface); }
  .installation .lnone { padding: 10px 12px; color: var(--warn); font-size: calc(13px * var(--fs)); border-top: 1px solid var(--line); background: color-mix(in srgb, var(--warn) 12%, transparent); }
  .installation .ladd { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; padding: 8px 12px; border-top: 1px solid var(--line); }
  .installation .ladd input, .installation .ladd select { font: inherit; font-size: calc(13px * var(--fs)); padding: 5px 8px; border: 1px solid var(--line); border-radius: 6px; background: var(--surface); color: inherit; }
  .installation .tag.role { background: var(--accent-soft); color: var(--accent); }
  .installation .lrow > * { min-width: 0; }
  .installation .lrow .nm, .installation .lrow .lstate > span, .installation .lrow .nm a { overflow-wrap: anywhere; }
  .installation .lrow .lstate { min-width: 0; }
  .installation .lrow .lstate > span.isub { flex: 1 1 100%; min-width: 0; }
  .installation .lrow .tag { white-space: nowrap; }
  .installation .lstate { overflow-wrap: anywhere; display: flex; flex-wrap: wrap; gap: 6px; align-items: center; font-size: calc(12px * var(--fs)); }
  .installation table.matrix th, .installation table.matrix td { text-align: center; min-width: 76px; }
  .installation table.matrix th:first-child, .installation table.matrix td:first-child { text-align: left; min-width: 150px; }
  .installation .mcell { display: inline-block; padding: 2px 8px; border-radius: 6px; font-size: calc(11px * var(--fs)); border: 1px solid var(--line); }
  .installation .mcell.assigned { background: color-mix(in srgb, var(--warn) 20%, transparent); border-color: transparent; }
  .installation .mcell.declared { background: var(--accent-soft); color: var(--accent); border-color: transparent; }
  .installation .mcell.entered { background: color-mix(in srgb, var(--ok) 18%, transparent); border-color: transparent; }
  .installation .mplus { cursor: pointer; color: var(--muted); background: none; border: 0; font: inherit; width: 26px; height: 26px; border-radius: 50%; }
  .installation .mplus:hover { background: var(--accent-soft); color: var(--accent); }
  @media (max-width: 720px) {
    .installation .lrow, .installation .nolearn .lrow { grid-template-columns: minmax(0, 1fr) auto; }
    .installation .lrow .nm { grid-column: 1; }
    .installation .lrow .lacts { grid-column: 2; grid-row: 1; }
    .installation .lrow > .lcol { grid-column: 1 / -1; display: inline-flex; }
    .installation .lrow > .lcol + .lcol { margin-top: -6px; }
    .installation .lrow > input.cell, .installation .lrow > .lstate { grid-column: 1 / -1; }
  }
  .installation .sheet { border: 1px solid var(--line); border-radius: 12px; padding: 12px 16px 14px; margin: 0 0 12px; background: var(--surface); }
  .installation .sheet .sheethead { display: flex; align-items: center; justify-content: space-between; gap: 8px; font-size: calc(14px * var(--fs)); }
  .installation .sheet .sheethead .iconbtn { width: 28px; height: 28px; border-radius: 50%; display: grid; place-items: center; color: var(--muted); }
  .installation .sheet .sheethead .iconbtn:hover { background: var(--soft); color: var(--text); }
  .installation .sheet .sheethead svg { width: 18px; height: 18px; }
  .installation .sheet > p { margin: 4px 0 0; max-width: 90ch; }
  .installation ol.sheetsteps { list-style: none; margin: 12px 0 2px; padding: 0; display: grid; gap: 12px; }
  .installation ol.sheetsteps li { display: grid; grid-template-columns: 26px minmax(0, 1fr); gap: 10px; align-items: start; font-size: calc(13px * var(--fs)); }
  .installation ol.sheetsteps li > b { width: 24px; height: 24px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; background: var(--accent-soft); color: var(--accent); font-weight: 500; font-size: calc(12px * var(--fs)); }
  .installation ol.sheetsteps textarea.paste { min-height: 72px; font: inherit; font-size: calc(13px * var(--fs)); }
  .installation .sheetrun { margin-top: 8px; display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
  .installation .tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 8px; }
  .installation .tile { background: var(--soft); border-radius: 8px; padding: 8px 10px; font-size: calc(13px * var(--fs)); }
  .installation .tile small { display: block; color: var(--muted); font-size: calc(11px * var(--fs)); }
  .installation .tile.bad { background: color-mix(in srgb, var(--warn) 18%, transparent); }
  .installation .itable tr.psu td { background: var(--soft); padding: 8px; }
  .installation .itable tr.psu.bad td { background: color-mix(in srgb, var(--warn) 18%, transparent); }
  .installation .itable tr.dup td { background: color-mix(in srgb, var(--warn) 14%, transparent); }
  .installation .psurow { display: flex; flex-wrap: wrap; gap: 6px 10px; align-items: center; }
  .installation .psurow input.cell { border-color: var(--line); background: var(--surface); }
  .installation .psurow .barbg { width: 90px; height: 6px; border-radius: 3px; background: var(--surface); border: 1px solid var(--line); overflow: hidden; }
  .installation .psurow .barbg i { display: block; height: 100%; background: var(--accent); }
  .installation .psurow .barbg i.hot { background: var(--warn); }
  .installation .seg button .isub { margin-left: 4px; }
  .installation .gbar .seg { max-width: 100%; overflow-x: auto; }
  /* the filter bar of the devices tab: views and kinds in one line, alike in look */
  .installation .fbar { flex-wrap: nowrap; overflow-x: auto; gap: 8px; padding-bottom: 2px; scrollbar-width: thin; }
  .installation .fbar .seg { flex: none; overflow: visible; }
  .installation .fbar .chips { flex-wrap: nowrap; flex: none; gap: 4px; }
  .installation .fbar .chips .chip { min-height: 30px; padding: 0 12px; border-radius: 16px; white-space: nowrap; font-weight: 400; }
  .installation .fbar .chips .chip b { font-weight: 500; margin-left: 2px; }
  .installation .fbar .fsep { flex: none; width: 1px; align-self: stretch; background: var(--line); margin: 2px 2px; }
  .installation .gbar .seg button { white-space: nowrap; }
  .installation .chips { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
  .installation .chips .isub.lead { min-width: 40px; }
  .installation button.tag { border: 0; font: inherit; font-size: calc(11px * var(--fs)); cursor: pointer; }
  .installation button.tag:hover { color: var(--text); }
  .installation .tag.bus { background: var(--accent-soft); color: var(--accent); }
  .installation .itable tr.grp td { background: var(--soft); font-weight: 500; cursor: pointer; padding: 6px 8px; }
  .installation .itable td .dash { color: var(--muted); }
  .installation .placeadd { font: inherit; font-size: calc(13px * var(--fs)); color: var(--muted); background: none; border: 1px solid transparent; border-radius: 6px; padding: 4px 10px; cursor: pointer; text-align: left; }
  .installation .placeadd:hover { color: var(--accent); border-color: var(--accent); }
  .installation .itable th.sortable { cursor: pointer; user-select: none; }
  .installation .itable th.sortable .sarrow { font-style: normal; margin-left: 4px; opacity: 0; }
  .installation .itable th.sortable:hover .sarrow { opacity: .45; }
  .installation .itable th[aria-sort] .sarrow { opacity: 1; color: var(--accent); }
  .installation .stile small { margin: 0; }
  .installation .itools select { font: inherit; padding: 4px 8px; border: 1px solid var(--line); border-radius: 8px; background: var(--surface); color: inherit; }
  .installation .place { display: flex; align-items: center; min-width: 250px; border: 1px solid transparent; border-radius: 6px; }
  .installation .place:hover { border-color: var(--line); }
  .installation .place:focus-within { border-color: var(--accent); background: var(--surface); }
  .installation .place.blank { border: 1px dashed var(--line); }
  .installation .place input { flex: 1 1 0; min-width: 0; width: 33%; box-sizing: border-box; font: inherit; font-size: calc(12px * var(--fs)); padding: 4px 6px; border: 0; background: transparent; color: inherit; }
  .installation .place input:first-child { flex: 1.5 1 0; }
  .installation .place input:focus { outline: none; }
  .installation .place i { color: var(--muted); font-style: normal; }
  .installation details.colmenu { position: relative; }
  .installation details.colmenu summary { list-style: none; cursor: pointer; }
  .installation details.colmenu summary::-webkit-details-marker { display: none; }
  .installation details.colmenu .items { position: absolute; right: 0; z-index: 5; margin-top: 4px; min-width: 200px; display: grid; gap: 2px; padding: 8px 10px; background: var(--surface); border: 1px solid var(--line); border-radius: 10px; }
  .installation details.supplymenu .items { position: static; margin-top: 8px; justify-items: start; }
  .installation details.colmenu label { display: flex; gap: 8px; align-items: center; font-size: calc(13px * var(--fs)); padding: 3px 0; cursor: pointer; }

  .installation .stiles { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; }
  .installation .stile { flex: 0 1 auto; text-align: left; font: inherit; color: inherit; background: var(--soft); border: 1px solid transparent; border-radius: 12px; padding: 6px 14px; cursor: pointer; display: flex; align-items: baseline; gap: 8px; }
  .installation .stile b { font-size: calc(18px * var(--fs)); font-weight: 500; line-height: 1.2; }
  .installation .stile span { font-size: calc(13px * var(--fs)); color: var(--muted); }
  .installation .stile.u b { color: var(--accent); }
  .installation .stile.w b { color: var(--warn); }
  .installation .stile.f b { color: var(--ok); }
  .installation .stile.d b { color: var(--danger, var(--warn)); }
  .installation .stile.zero b { color: var(--muted); }
  .installation .nolearn .lrow input.cell[data-in-learn], .installation .nolearn .lrow input.cell[data-in-efield="learn"] { display: none; }
  .installation .stile[aria-pressed="true"] { border-color: var(--accent); background: color-mix(in srgb, var(--accent) 8%, var(--soft)); }
  .installation .snext { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 8px; padding: 8px 12px; border-radius: 10px; margin-bottom: 10px; background: color-mix(in srgb, var(--ok) 12%, transparent); font-size: calc(14px * var(--fs)); }
  .installation .snext.none { background: color-mix(in srgb, var(--warn) 18%, transparent); }
  .installation .snext b { font-weight: 500; }
  .installation .sintro .info { cursor: help; color: var(--muted); }
  .installation .swrap { border: 1px solid var(--line); border-radius: 12px; overflow: hidden; }
  .installation .swrap .tablewrap { margin: 0; }
  .installation .stable { font-size: calc(14px * var(--fs)); }
  .installation .stable input.cell { min-width: 64px; }
  .installation .stable td.mono { white-space: nowrap; }
  .installation .stable th { padding: 9px 10px; }
  .installation .stable td { padding: 8px 10px; }
  .installation .stable th:first-child, .installation .stable td:first-child { width: 64px; padding-left: 14px; }
  .installation .stable th.sortable { cursor: pointer; user-select: none; }
  .installation .stable th .sarrow { font-style: normal; margin-left: 4px; opacity: 0; }
  .installation .stable th.sortable:hover .sarrow { opacity: .45; }
  .installation .stable th[aria-sort] .sarrow { opacity: 1; color: var(--accent); }
  .installation .stable td.snr { font-weight: 500; font-size: calc(14px * var(--fs)); }
  .installation .stable tr.s-u > td:first-child { box-shadow: inset 3px 0 0 var(--accent); }
  .installation .stable tr.s-w > td:first-child { box-shadow: inset 3px 0 0 var(--warn); }
  .installation .stable tr.s-w > td { background: color-mix(in srgb, var(--warn) 12%, transparent); }
  .installation .stable tr.s-g > td:first-child, .installation .stable tr.s-x > td:first-child { box-shadow: inset 3px 0 0 var(--muted); }
  .installation .stable tr.s-f > td { color: var(--muted); }
  .installation .stag { font-size: calc(12px * var(--fs)); padding: 2px 10px; border-radius: 12px; background: var(--soft); color: var(--muted); white-space: nowrap; }
  .installation .stag.u { background: var(--accent-soft); color: var(--accent); }
  .installation .stag.w { background: color-mix(in srgb, var(--warn) 22%, transparent); color: var(--text); }
  .installation .spager { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 8px; padding: 8px 14px; border-top: 1px solid var(--line); font-size: calc(13px * var(--fs)); color: var(--muted); }
  .installation .spager > div { display: flex; align-items: center; gap: 8px; }
  .installation .spager select { font: inherit; padding: 2px 6px; border: 1px solid var(--line); border-radius: 6px; background: var(--surface); color: inherit; }
  .installation .spager .chip { min-height: 28px; padding: 0 12px; }
  .installation .spager .chip:disabled { opacity: .4; cursor: default; }

  .installation table.log td { padding: 9px 10px; vertical-align: top; }
  .installation table.log tr.logday td { background: var(--soft); font-size: calc(12px * var(--fs)); font-weight: 500; color: var(--muted); padding: 6px 14px; }
  .installation table.log td.logmain { padding-left: 14px; }
  .installation .logline { display: flex; flex-wrap: wrap; gap: 4px 10px; align-items: baseline; font-size: calc(14px * var(--fs)); }
  .installation .logdetail { margin-top: 4px; color: var(--muted); font-size: calc(13px * var(--fs)); display: flex; flex-wrap: wrap; gap: 4px 6px; align-items: center; }
  .installation .logdetail .mono { background: var(--soft); border-radius: 4px; padding: 0 5px; color: var(--text); }
  .installation table.log td.logwhen { width: 1%; white-space: nowrap; text-align: right; color: var(--muted); font-size: calc(12px * var(--fs)); padding-right: 14px; }
  .installation .lres { font-size: calc(12px * var(--fs)); padding: 1px 8px; border-radius: 12px; background: var(--soft); }
  .installation .lres.ok { background: color-mix(in srgb, var(--ok) 20%, transparent); color: var(--text); }
  .installation .lres.warn { background: color-mix(in srgb, var(--warn) 22%, transparent); color: var(--text); }
  .installation .lres.bad { background: color-mix(in srgb, var(--danger, #d33) 22%, transparent); color: var(--text); }
  .installation .logbar { display: flex; justify-content: space-between; align-items: center; padding: 8px 14px; background: var(--soft); border-bottom: 1px solid var(--line); font-size: calc(13px * var(--fs)); color: var(--muted); }
  .installation .logbar button { font: inherit; color: inherit; background: none; border: 0; cursor: pointer; }
  .installation .ev-chip[aria-pressed="true"] { border-color: var(--e); background: color-mix(in srgb, var(--e) 16%, transparent); color: color-mix(in srgb, var(--e) 72%, var(--text)); }
  .installation .ev-device_added { --e: var(--ok); }
  .installation .ev-device_removed, .installation .ev-sender_removed { --e: var(--warn); }
  .installation .ev-sender_assigned { --e: var(--k-bus); }
  .installation .ev-teach_in { --e: var(--k-taster); }
  .installation .ev-sender_test { --e: var(--k-sensor); }
  .installation .ev-import { --e: var(--k-psu); }

  /* colour: one hue per kind, used for tags, chips, row stripes and cards */
  .installation { --k-bus: #2f6fb5; --k-sensor: #139a87; --k-taster: #7b5cc9; --k-aktor: #d77f1f; --k-virt: #c2477f; --k-psu: #6b7b8d; }
  .installation .k-bus, .installation [data-k="bus"] { --k: var(--k-bus); }
  .installation .k-sensor, .installation [data-k="sensor"] { --k: var(--k-sensor); }
  .installation .k-taster, .installation [data-k="taster"] { --k: var(--k-taster); }
  .installation .k-aktor, .installation [data-k="aktor"] { --k: var(--k-aktor); }
  .installation .k-virt, .installation [data-k="virt"] { --k: var(--k-virt); }
  .installation .k-psu, .installation [data-k="psu"] { --k: var(--k-psu); }
  .installation .tag.kind { background: color-mix(in srgb, var(--k) 16%, transparent); color: color-mix(in srgb, var(--k) 70%, var(--text)); font-weight: 500; }
  .installation .tag.kind:hover { background: color-mix(in srgb, var(--k) 26%, transparent); }
  .installation .itable tr[data-k] > td:first-child { box-shadow: inset 3px 0 0 var(--k); }
  .installation .chip[data-k]::before { content: ""; width: 8px; height: 8px; border-radius: 50%; background: var(--k); display: inline-block; margin-right: 6px; }
  .installation .chip[data-k][aria-pressed="true"] { border-color: var(--k); background: color-mix(in srgb, var(--k) 14%, transparent); color: color-mix(in srgb, var(--k) 75%, var(--text)); }
  .installation .seg button[aria-pressed="true"] { background: var(--accent); color: var(--on-accent); }
  .installation .seg button[aria-pressed="true"] .isub { color: inherit; opacity: 0.85; }
  .installation .tile { border-left: 3px solid var(--accent); background: color-mix(in srgb, var(--accent) 7%, var(--soft)); font-size: calc(16px * var(--fs)); font-weight: 500; line-height: 1.35; }
  .installation .tile small { font-weight: 400; text-transform: none; letter-spacing: 0; }
  .installation .tile.ok { border-left-color: var(--ok); background: color-mix(in srgb, var(--ok) 9%, var(--soft)); }
  .installation .tile.bad { border-left-color: var(--warn); background: color-mix(in srgb, var(--warn) 18%, transparent); }
  .installation .itable th { border-bottom: 2px solid var(--line); }
  .installation .itable tbody tr:not(.grp):not(.psu):not(.free):hover td { background: color-mix(in srgb, var(--accent) 5%, transparent); }
  .installation .itable tr.grp td { background: color-mix(in srgb, var(--accent) 10%, var(--soft)); }
  .installation .itable tr.psu td { background: color-mix(in srgb, var(--k-psu) 14%, transparent); }
  .installation .itable tr.psu.bad td { background: color-mix(in srgb, var(--warn) 20%, transparent); }
  .installation .gwhead h3 { border-left: 3px solid var(--accent); padding-left: 10px; }
  .installation .progress .barbg { height: 8px; border-radius: 4px; }
  .installation .lcard { border-left: 4px solid var(--k, var(--line)); }
  .installation .lhead { background: color-mix(in srgb, var(--k, var(--accent)) 9%, var(--soft)); }
  .installation .tag.role, .installation .tag[class*="src-"] { font-weight: 500; }
  .installation [data-src="assigned"], .installation .tag.src-assigned { --s: var(--k-aktor); }
  .installation [data-src="declared"], .installation .tag.src-declared { --s: var(--k-bus); }
  .installation [data-src="entered"], .installation .tag.src-entered { --s: var(--ok); }
  .installation .tag[class*="src-"] { background: color-mix(in srgb, var(--s) 18%, transparent); color: color-mix(in srgb, var(--s) 70%, var(--text)); }
  .installation .chip[data-src]::before { content: ""; width: 8px; height: 8px; border-radius: 50%; background: var(--s); display: inline-block; margin-right: 6px; }
  .installation .chip[data-src][aria-pressed="true"] { border-color: var(--s); background: color-mix(in srgb, var(--s) 14%, transparent); color: color-mix(in srgb, var(--s) 75%, var(--text)); }
  .installation .itable tr[data-k] > td.name:first-child { padding-left: 14px; }
  .installation .tag.ev { --e: var(--k-psu); background: color-mix(in srgb, var(--e) 16%, transparent); color: color-mix(in srgb, var(--e) 72%, var(--text)); font-weight: 500; }
  .installation .tag.ev-device_added { --e: var(--ok); }
  .installation .tag.ev-device_removed, .installation .tag.ev-sender_removed { --e: var(--warn); }
  .installation .tag.ev-sender_assigned { --e: var(--k-bus); }
  .installation .tag.ev-teach_in { --e: var(--k-taster); }
  .installation .tag.ev-sender_test { --e: var(--k-sensor); }
  .installation .tag.ev-import { --e: var(--k-psu); }${BUS_STYLE}`;

const gateways = (doc) => doc?.gateways ?? [];
// the last, narrow column of a table row: its menu (⋮), or an empty cell so all rows line up
const withMenu = (rows, menu = () => "") => rows.replace(/<\/tr>/g, () => `<td class="rmenu">${menu()}</td></tr>`);
const label = (t, field) => t.inst.fields[field];
const open = (device) => !device.location; // a device without a place is still to be written down

function matches(device, q) {
  if (!q) return true;
  const hay = [device.name, device.id, device.area, ...INSTALLATION_FIELDS.map((f) => device[f])].join(" ").toLowerCase();
  return hay.includes(q.toLowerCase());
}

// a pasted spreadsheet: a header row, then one row per device, matched by its address (a "Gateway"
// column narrows it to that gateway); empty cells change nothing
export function parseTable(text, t) {
  const rows = text.split(/\r?\n/).filter((line) => line.trim()).map((line) => line.split("\t").map((c) => c.trim()));
  if (rows.length < 2) return { rows: [], columns: [] };
  const names = new Map();
  for (const field of INSTALLATION_FIELDS) {
    names.set(field, field);
    names.set(t.inst.fields[field].toLowerCase(), field);
  }
  const head = rows[0].map((c) => c.toLowerCase());
  const address = head.findIndex((c) => ["address", "adresse", "id"].includes(c));
  const gateway = head.findIndex((c) => ["gateway"].includes(c));
  const columns = head.map((c, i) => [i, names.get(c)]).filter(([, field]) => field);
  return { address, gateway, columns, rows: rows.slice(1) };
}

export const installation = {
  ...busView,

  _managing() {
    // the sender ID pools sit above the table of the gateway senders
    return this._view === "installation" && this._in.tab === "gwsenders";
  },

  _setManage() {
    // the pool block above the table shows only on the gateway senders tab
    const panel = this.shadowRoot.getElementById("panel");
    if (panel) panel.dataset.isub = this._managing() ? "manage" : "";
    const box = this.shadowRoot.getElementById("poolBox");
    if (box) {
      const t = this._t.inst;
      this._replace(this.shadowRoot.getElementById("poolSummary"), `${esc(t.poolTitle)} <span class="isub">${esc(t.manageHint)}</span>`);
      if (box.open !== this._in.poolOpen) box.open = this._in.poolOpen;
    }
  },

  _poolToggled(open) {
    this._in.poolOpen = open;
    savePoolOpen(open);
  },

  async _loadInstallation() {
    const state = this._in;
    try {
      state.doc = await this._hass.callWS({ type: "enocean_eltako/documentation" });
      for (const gw of state.doc.gateways) {
        gw.supplies = (gw.supplies ?? []).map((x) => ({ ...SUPPLY_BLANK, ...x }));
        gw.numbers = senderNumbers(gw);
      }
      state.error = false;
    } catch (err) {
      state.error = true;
    }
    this._renderInstallation();
  },

  _renderInstallation() {
    const head = this.shadowRoot.getElementById("instHead");
    const el = this.shadowRoot.getElementById("instBody");
    if (!el || this._view !== "installation") return;
    const t = this._t;
    const state = this._in;
    if (state.error || !state.doc) {
      this._replace(head, "");
      this._replace(el, `<div class="ibody"><div class="none">${esc(state.error ? t.inst.failed : t.loading)}</div></div>`);
      return;
    }
    const tab = (name, label, selected, badge = 0) => `<button class="itab" role="tab" data-in-tab="${name}" aria-selected="${selected}" tabindex="${selected ? 0 : -1}">${esc(label)}${badge ? ` <b class="tabwarn" title="${esc(t.inst.sid.blocked)}">${badge}</b>` : ""}</button>`;
    // blocked sender IDs wait for a release: the tab says so from anywhere
    const blocked = gateways(state.doc).reduce((n, gw) => n + docTables(gw, t, (p) => this._profile(p)).senders.filter((r) => r.blocked).length, 0);
    const groups = TABS.map((name) => tab(name, t.inst.tabNames[name], state.tab === name, name === "gwsenders" ? blocked : 0)).join("");
    const subtabs = "";
    const item = (act, icon, label) => `<button data-in-act="${act}">${icon ? svg(icon) : ""}${esc(label)}</button>`;
    const tools = `<details class="imenu"><summary class="iconbtn" title="${esc(t.more)}" aria-label="${esc(t.more)}">${svg(ICON.more)}</summary><div class="items">${item("print", ICON.print, t.inst.print)}${item("csv", ICON.download, t.inst.csvDevices)}${item("csv-tables", ICON.download, t.inst.links.tablesCsv)}${item("csv-links", ICON.download, t.inst.links.csvShort)}${item("json", ICON.download, "JSON")}<hr>${item("import", ICON.upload, t.inst.import)}</div></details>`;
    const body = { devices: () => this._instDevicesTab(), gwsenders: () => this._instSenders(), links: () => this._instLinks(), log: () => this._instLog() }[state.tab]();
    this._setManage();
    const back = state.back ? `<button class="chip text" data-in-back>← ${esc(t.inst.back)}</button>` : "";
    this._replace(head, `<div class="itop"><div class="groups" role="tablist">${groups}</div><div class="itools">${back}${tools}</div></div>${subtabs}`);
    this._replace(el, `<div class="ibody">${body}</div>`);
    if (state.hl) {
      const row = [...el.querySelectorAll("[data-in-row]")].find((r) => r.dataset.inRow === state.hl);
      state.hl = "";
      if (row) {
        row.classList.add("hl");
        row.scrollIntoView({ block: "center" });
        setTimeout(() => row.classList.remove("hl"), 2000);
      }
    }
  },

  // ---- the tables of the sender and bus groups, from the same rows as the printout ------------------

  _instCell(gw, key, field, value, label, placeholder = "") {
    // a field of a device, edited in the table; an entry without a device (by hand) is plain text
    if (!key) return esc(value);
    return `<input class="cell" data-in-field="${field}" data-in-gw="${esc(gw.entry_id)}" data-in-key="${esc(key)}" value="${esc(value ?? "")}" placeholder="${esc(placeholder)}" aria-label="${esc(label)}" autocomplete="off">`;
  },

  _instTable(head, rows, cls = "") {
    return `<div class="tablewrap"><table class="itable${cls}"><thead><tr>${head.map((h) => `<th>${esc(h)}</th>`).join("")}</tr></thead><tbody>${rows}</tbody></table></div>`;
  },

  _instGwHead(gw, count = null) {
    // the name of a gateway with its base ID, and optionally how many devices it has
    const t = this._t.inst;
    return `<header class="gwhead"><h3><button class="namelink" data-in-gwopen="${esc(gw.entry_id)}" title="${esc(t.openGateway)}">${esc(gw.title)}</button></h3><span class="isub mono">${esc(gw.base_id ?? "")}</span>${count === null ? "" : `<span class="isub">${esc(t.deviceCount(count))}</span>`}</header>`;
  },

  _instEmpty(gw) {
    // a gateway without devices says what to do next
    const t = this._t.inst;
    return `<div class="gwempty"><p>${esc(t.emptyGateway)}</p><button class="chip" data-open-integration="${esc(gw.entry_id)}">${esc(t.addDevice)}</button></div>`;
  },

  _instPerGateway(build) {
    const t = this._t;
    const parts = gateways(this._in.doc).map((gw) => {
      const inner = build(gw, docTables(gw, t, (p) => this._profile(p)));
      return inner ? `<section class="gw">${this._instGwHead(gw)}${inner}</section>` : "";
    });
    return parts.join("") || `<div class="none">${esc(t.inst.noDevices)}</div>`;
  },

  _instSenders() {
    // the sender IDs of each gateway: how full the pool is, the next free ID, and a table to filter, sort and page
    const t = this._t;
    const T = t.doc.tbl;
    const S = t.inst.sid;
    const state = this._in;
    const hue = (fn) => ["bus", "sensor", "taster", "aktor", "virt"][[...fn].reduce((n, c) => n + c.charCodeAt(0), 0) % 5];
    const sorters = { nr: (r) => r.nr ?? 999, name: (r) => r.name || "", fn: (r) => r.fn || "", use: (r) => r.use || "", st: (r) => S.state[r.st] };
    const html = this._instPerGateway((gw, parts) => {
      if (!parts.senders.length && !parts.externals.length) return "";
      const v = (state.sid[gw.entry_id] ??= { f: "used", fn: "", sort: "nr", dir: 1, pg: 0, ps: 25 });
      const all = [
        ...parts.senders.map((r) => ({ ...r, st: r.gateway ? "g" : r.free ? "f" : r.blocked ? "w" : "u" })),
        ...parts.externals.map((r) => ({ ...r, nr: null, st: "x", fn: "" })),
      ];
      const count = (st) => all.filter((r) => st.includes(r.st)).length;
      const key = esc(gw.entry_id);
      const tile = (f, label, n, cls) => `<button class="stile ${cls}" data-in-sidf="${key}|${f}" aria-pressed="${v.f === f}"><b>${n}</b><span>${esc(label)}</span></button>`;
      const tiles = `<div class="stiles">${tile("used", S.used, count("uwx"), "u")}${tile("w", S.blocked, count("w"), "w")}${tile("f", S.free, count("f"), "f")}${tile("all", S.all, all.length, "")}</div>`;
      const free = all.find((r) => r.st === "f");
      const next = free
        ? `<div class="snext"><span>${esc(S.next)} <b class="mono">${esc(S.nr)} ${free.nr} · ${esc(free.id)}</b></span><button class="chip" data-in-act="copy-id" data-id="${esc(free.id)}">${esc(S.copy)}</button></div>`
        : `<div class="snext none">${esc(S.full)}</div>`;
      const fns = [...new Set(all.map((r) => r.fn).filter(Boolean))].sort((x, y) => x.localeCompare(y));
      const chips = fns.map((fn) => `<button class="chip" data-k="${hue(fn)}" data-in-sidfn="${key}|${esc(fn)}" aria-pressed="${v.fn === fn}">${esc(fn)}</button>`).join("");
      const q = state.q.trim().toLowerCase();
      let rows = all.filter((r) => (v.f === "all" ? true : v.f === "used" ? "uwxg".includes(r.st) : r.st === v.f) && (!v.fn || r.fn === v.fn) && (!q || [r.nr, r.id, r.name, r.place, r.device, r.fn, r.use].join(" ").toLowerCase().includes(q)));
      const by = sorters[v.sort];
      rows = rows.sort((x, y) => {
        // blocked IDs need a hand: they stay on top while the table is ordered by number
        if (v.sort === "nr" && (x.st === "w") !== (y.st === "w")) return x.st === "w" ? -1 : 1;
        const a = by(x);
        const b = by(y);
        return ((typeof a === "number" ? a - b : String(a).localeCompare(String(b))) || (x.nr ?? 999) - (y.nr ?? 999)) * v.dir;
      });
      const pages = Math.max(1, Math.ceil(rows.length / v.ps));
      v.pg = Math.min(v.pg, pages - 1);
      const page = rows.slice(v.pg * v.ps, (v.pg + 1) * v.ps);
      const th = (col, label) => `<th class="sortable" data-in-sids="${key}|${col}"${v.sort === col ? ` aria-sort="${v.dir > 0 ? "ascending" : "descending"}"` : ""}><span>${esc(label)}</span><i class="sarrow">${v.sort === col && v.dir < 0 ? "↓" : "↑"}</i></th>`;
      const head = `<tr>${th("nr", S.nr)}<th>${esc(T.senderId)}</th>${th("name", S.device)}${th("fn", T.function)}${th("use", S.role)}<th>${esc(T.busAddress)}</th><th>${esc(T.feedbackId)}</th>${th("st", S.status)}<th class="rmenu"></th></tr>`;
      const tag = (st) => `<span class="stag ${st}">${esc(S.state[st])}</span>`;
      const body = withMenu(page.map((r) => {
        const base = `<tr class="s-${r.st}"${r.st === "u" ? ` data-in-row="snd|${key}|${r.nr}"` : ""}><td class="mono snr">${r.nr ?? "–"}</td><td class="mono">${esc(r.id)}${r.second ? `<div class="isub">+ ${esc(r.second)}</div>` : ""}</td>`;
        if (r.st === "f") return `${base}<td colspan="5" class="isub">${esc(T.free)}</td><td>${tag("f")}</td></tr>`;
        if (r.st === "g") return `${base}<td colspan="5">${esc(T.gateway)}</td><td>${tag("g")}</td></tr>`;
        if (r.st === "w") return `${base}<td colspan="4" class="isub">${esc(T.blocked)}</td><td><button class="chip" data-in-free="${esc(r.id)}">${esc(t.freeAction)}</button></td><td>${tag("w")}</td></tr>`;
        if (r.st === "x") return `${base}<td>${esc(r.name)}<div class="isub">${esc(r.device)}</div></td><td></td><td>${r.use ? `<span class="tag">${esc(r.use)}</span>` : ""}</td><td></td><td></td><td>${tag("x")}</td></tr>`;
        const name = [r.key ? `<a data-in-goto="${esc(r.key)}">${esc(r.name)}</a>` : esc(r.name), r.place].filter(Boolean).join(", ") + ` <button class="tag" data-in-sndlinks="${esc(r.id)}" title="${esc(t.inst.linksOfSender)}">→ ${esc(t.inst.tabNames.links)}</button>`;
        return `${base}<td>${name}${r.device ? `<div class="isub">${esc(r.device)}</div>` : ""}</td><td>${r.fn ? `<span class="tag kind k-${hue(r.fn)}">${esc(r.fn)}</span>` : ""}</td><td>${r.use ? `<span class="tag">${esc(r.use)}</span>` : ""}</td><td>${this._instCell(gw, r.key, "bus_address", r.bus, T.busAddress, "1–126")}</td><td>${this._instCell(gw, r.key, "feedback_id", r.feedback, T.feedbackId, "00000081")}</td><td>${tag("u")}</td></tr>`;
      }).join(""));
      const sizes = [25, 50, 100].map((n) => `<option${v.ps === n ? " selected" : ""}>${n}</option>`).join("");
      const from = rows.length ? v.pg * v.ps + 1 : 0;
      const pager = `<div class="spager"><span>${esc(S.range(from, from + page.length - (rows.length ? 1 : 0), rows.length))}</span><div><label>${esc(S.perPage)} <select data-in-sidps="${key}" aria-label="${esc(S.perPage)}">${sizes}</select></label><button class="chip" data-in-sidpg="${key}|-1" aria-label="${esc(S.prev)}"${v.pg === 0 ? " disabled" : ""}>‹</button><span>${esc(S.page(v.pg + 1, pages))}</span><button class="chip" data-in-sidpg="${key}|1" aria-label="${esc(S.next2)}"${v.pg >= pages - 1 ? " disabled" : ""}>›</button></div></div>`;
      const search = `<input class="isearch" data-in-search value="${esc(state.q)}" placeholder="${esc(S.search)}" aria-label="${esc(S.search)}">`;
      return `${tiles}${next}<div class="itools" style="align-items:center">${search}${chips ? `<span class="chips">${chips}</span>` : ""}</div><div class="swrap"><div class="tablewrap"><table class="itable stable"><thead>${head}</thead><tbody>${body || `<tr><td colspan="9" class="none">${esc(S.none)}</td></tr>`}</tbody></table></div>${pager}</div>`;
    });
    return `<p class="isub sintro">${esc(S.intro)} <span class="info" title="${esc(`${T.sendersIntro} ${t.inst.editHint}`)}">ⓘ</span></p>${html}`;
  },

  _instExtras(gw) {
    // what the device table lists besides the devices: the power supplies and the entries written by hand
    const t = this._t;
    const supplies = (gw.supplies ?? []).map((x) => ({ psu: true, sid: x.id, key: `psu|${x.id}`, name: x.name || t.doc.tbl.supplyNoName, id: "", area: "", virtual: false, bus_address: "", location: x.location, circuit: x.circuit, fuse: x.fuse, note: x.note, model: x.watts ? `${x.watts} W` : "" }));
    const manual = (gw.manual ?? []).map((m) => ({ manual: true, mid: m.id, key: `manual|${m.id}`, kindRaw: m.kind, named: Boolean(m.name), name: m.name || t.inst.funk.unnamed, id: m.address, model: m.model ?? "", area: "", virtual: false, bus_address: m.bus_address, feedback_id: m.feedback_id, bus_power: m.bus_power, location: m.location, power: m.power, note: m.function, group: "", circuit: m.circuit ?? "", fuse: m.fuse ?? "", installed: m.installed ?? "", revision: "" }));
    return [...supplies, ...manual];
  },

  _instLinksOf(gw, d) {
    // what a radio device controls (its ID as the sender of a link) and what controls it
    const T = this._t.inst.funk;
    const plain = (id) => String(id ?? "").replaceAll("-", "").toUpperCase();
    const mine = new Set([d.id, ...(d.ids ?? []).map((x) => x.id)].filter(Boolean).map(plain));
    const goto = (key, name) => (key && gw.devices.some((x) => x.note_key === key) ? `<a data-in-goto="${esc(gw.devices.find((x) => x.note_key === key).key)}">${esc(name)}</a>` : esc(name));
    const out = gw.links.filter((l) => mine.has(plain(l.from_id)));
    const into = d.note_key ? gw.links.filter((l) => l.to_key === d.note_key) : [];
    const lines = [];
    if (out.length) lines.push(`${esc(T.controls)} ${out.map((l) => `${goto(l.to_key, l.to_name)}${l.role ? ` <span class="isub">${esc(l.source === "assigned" ? this._profile(l.role) : l.role)}</span>` : ""}`).join(", ")}`);
    if (into.length) lines.push(`${esc(T.controlledBy)} ${into.map((l) => esc(l.from_name || l.from_id)).join(", ")}`);
    return lines.length ? lines.join("<br>") : `<span class="isub">${esc(d.category === "buttons" || d.manual ? T.noLink : "–")}</span>`;
  },

  _instVirt() {
    // what Home Assistant sends: the virtual devices with their sender numbers, what they follow and what they were taught into
    const t = this._t;
    const I = t.inst;
    const V = I.virt;
    const state = this._in;
    const plain = (id) => String(id ?? "").replaceAll("-", "").toUpperCase();
    const all = gateways(state.doc).flatMap((gw) => gw.devices.filter(isVirtual).map((d) => ({ gw, d })));
    const taught = ({ gw, d }) => gw.links.filter((l) => l.source === "entered" && plain(l.from_id) === plain(d.id));
    const tile = (title, value, bad = false) => `<div class="tile${bad === "ok" ? " ok" : bad ? " bad" : ""}"><small>${esc(title)}</small>${value}</div>`;
    const sensors = all.filter(({ d }) => d.virtual);
    const tiles = `<div class="tiles">${tile(V.tileDevices, esc(I.funk.devicesN(all.length)))}${tile(V.tileLinked, `${all.filter((x) => taught(x).length).length} ${esc(I.of)} ${all.length}`)}${tile(V.tileNoSource, String(sensors.filter(({ d }) => !d.follows?.length).length), sensors.some(({ d }) => !d.follows?.length))}</div>`;
    const search = `<input class="isearch" data-in-search value="${esc(state.q)}" placeholder="${esc(I.search)}" aria-label="${esc(I.search)}">`;
    const sections = gateways(state.doc).map((gw) => {
      const rows = withMenu(gw.devices.filter((d) => isVirtual(d) && matches(d, state.q)).map((d) => {
        const numbers = gw.numbers?.get(d.note_key) ?? [];
        const nr = numbers.length ? numbers.map((n) => `<a data-in-snd="${esc(gw.entry_id)}|${n}">${n}</a>`).join(", ") : "–";
        const follows = d.follows?.length ? d.follows.map((e) => `<span class="mono">${esc(e)}</span>`).join("<br>") : `<span class="isub">${esc(d.virtual ? V.noSource : V.sendsPress)}</span>`;
        const into = taught({ gw, d }).map((l) => (l.to_key && gw.devices.some((x) => x.note_key === l.to_key) ? `<a data-in-goto="${esc(gw.devices.find((x) => x.note_key === l.to_key).key)}">${esc(l.to_name)}</a>` : esc(l.to_name)) + (l.role ? ` <span class="isub">${esc(l.role)}</span>` : "") + (l.learn ? ` <span class="isub">· ${esc(l.learn)}</span>` : ""));
        return `<tr data-in-row="${esc(d.key)}" data-k="virt"><td class="name">${esc(d.name)}<div class="isub">${esc(d.model ?? "")}</div><div>${this._instKindTag(d)}</div></td><td class="mono">${nr}</td><td class="mono">${esc(d.id)}</td><td>${follows}</td><td class="lk">${into.length ? into.join("<br>") : `<span class="isub">${esc(V.noLink)}</span>`}</td></tr>`;
      }).join(""));
      const head = [I.device, V.cols.nr, V.cols.id, V.cols.follows, V.cols.taught].map((h) => `<th>${esc(h)}</th>`).join("");
      return `<section class="gw">${this._instGwHead(gw)}<div class="tablewrap"><table class="itable"><thead><tr>${head}<th class="rmenu"></th></tr></thead><tbody>${rows || `<tr><td colspan="6" class="none">${esc(V.none)}</td></tr>`}</tbody></table></div></section>`;
    });
    return `${tiles}<div class="itools" style="align-items:center">${search}</div>${sections.join("")}<p class="isub">${esc(V.hint)}</p>`;
  },

  _instSignal(d) {
    const T = this._t;
    const sig = d.signal;
    if (!sig || sig.last == null) return `<span class="isub">${esc(d.manual ? T.inst.funk.notWatched : T.inst.funk.notHeard)}</span>`;
    const age = Math.max(0, Math.round(this._now() / 1000 - sig.last));
    const level = age <= SIGNAL_FRESH ? "ok" : age <= SIGNAL_LATE ? "late" : "silent";
    return `<span class="sig"><i class="dot ${level}"></i>${esc(T.ago(age))}</span><div class="isub">${[sig.rssi != null ? `${sig.rssi} dBm` : "", sig.repeater_only ? T.repeaterOnly : ""].filter(Boolean).map(esc).join(" · ")}</div>`;
  },

  _instFunk() {
    // the devices that send by radio, with where they sit, what supplies them, how they are heard and what they control
    const t = this._t;
    const I = t.inst;
    const F = I.funk;
    const state = this._in;
    const cols = FUNK_COLUMNS.filter((c) => state.funkCols.has(c));
    const radio = (gw) => [...gw.devices.filter((d) => ["sensor", "taster", "aktor"].includes(kindOf(d))), ...this._instExtras(gw).filter((d) => d.manual && kindOf(d) !== "bus")]
      .filter((d) => (state.art === "all" || kindOf(d) === state.art) && matches(d, state.q))
      .sort((a, b) => a.name.localeCompare(b.name));
    const all = gateways(state.doc).flatMap((gw) => [...gw.devices.filter((d) => ["sensor", "taster", "aktor"].includes(kindOf(d))), ...this._instExtras(gw).filter((d) => d.manual && kindOf(d) !== "bus")]);
    const now = this._now() / 1000;
    const late = all.filter((d) => d.signal?.last != null && now - d.signal.last > SIGNAL_LATE).length;
    const tile = (title, value, bad = false) => `<div class="tile${bad === "ok" ? " ok" : bad ? " bad" : ""}"><small>${esc(title)}</small>${value}</div>`;
    const tiles = `<div class="tiles">${tile(F.tileDevices, esc(F.devicesN(all.length)))}${tile(F.tileDocumented, String(all.filter((d) => d.manual).length))}${tile(F.tileSilent, String(late), late > 0)}${tile(F.tileRepeater, String(all.filter((d) => d.signal?.repeater_only).length))}</div>`;
    const kinds = ["taster", "sensor", "aktor"];
    const artChips = `<div class="chips"><button class="chip" data-in-art="all" aria-pressed="${state.art === "all"}">${esc(I.all)} <b>${all.length}</b></button>${kinds.map((k) => `<button class="chip" data-k="${k}" data-in-art="${k}" aria-pressed="${state.art === k}">${esc(I.kinds[k])} <b>${all.filter((d) => kindOf(d) === k).length}</b></button>`).join("")}</div>`;
    const menu = `<details class="colmenu" ${state.colMenu ? "open" : ""}><summary class="chip">${esc(I.columns)}</summary><div class="items">${FUNK_COLUMNS.map((c) => `<label><input type="checkbox" data-in-funkcol="${c}" ${state.funkCols.has(c) ? "checked" : ""}>${esc(F.cols[c])}</label>`).join("")}</div></details>`;
    const search = `<input class="isearch" data-in-search value="${esc(state.q)}" placeholder="${esc(I.search)}" aria-label="${esc(I.search)}">`;
    const form = state.docForm ? this._instDocForm(kinds) : "";
    const tools = `<div class="itools" style="align-items:center">${search}<span style="flex:1"></span><button class="chip" data-in-act="doc-open">${esc(F.document)}</button>${menu}</div>`;
    const input = (d, gw, field, value, placeholder, extra = "") => (d.manual
      ? `<input class="cell" data-in-mfield="${MANUAL_FIELD[field] ?? field}" data-in-gw="${esc(gw.entry_id)}" data-in-mid="${esc(d.mid)}" value="${esc(value ?? "")}" placeholder="${esc(placeholder)}" aria-label="${esc(placeholder)}: ${esc(d.name)}" autocomplete="off" ${extra}>`
      : `<input class="cell" data-in-field="${field}" data-in-gw="${esc(gw.entry_id)}" data-in-key="${esc(d.key)}" value="${esc(value ?? "")}" placeholder="${esc(placeholder)}" aria-label="${esc(placeholder)}: ${esc(d.name)}" autocomplete="off" ${extra}>`);
    const cell = (c, gw, d) => {
      if (c === "loc") return `<td>${this._instPlace(gw, d)}</td>`;
      if (c === "id") return `<td class="mono">${esc(d.id)}${(d.ids ?? []).filter((x) => x.id !== d.id).map((x) => `<br>${esc(x.id)}`).join("")}${d.ids?.length > 1 ? `<div class="isub" style="font-family:inherit">${esc(F.manyIds(d.ids.length))}</div>` : ""}</td>`;
      if (c === "sends") return `<td>${d.manual ? input(d, gw, "note", d.note, t.doc.manualFunctionHead) : esc([t.doc.tbl.categories[d.category], d.eep].filter(Boolean).join(" · ") || "–")}</td>`;
      if (c === "pow") return `<td>${input(d, gw, "power", d.power, label(t, "power"))}</td>`;
      if (c === "circuit" || c === "fuse") return `<td>${d.manual && !(!FIELD_KINDS[c] || FIELD_KINDS[c].includes(kindOf(d))) ? '<span class="dash">–</span>' : input(d, gw, c, d[c], label(t, c))}</td>`;
      if (c === "model") return `<td>${d.manual ? input(d, gw, "model", d.model, F.cols.model) : esc(d.model ?? "") || '<span class="dash">–</span>'}</td>`;
      if (c === "grp") return `<td>${d.manual ? '<span class="dash">–</span>' : input(d, gw, "group", d.group, label(t, "group"))}</td>`;
      if (c === "sig") return `<td>${this._instSignal(d)}</td>`;
      return `<td class="lk">${this._instLinksOf(gw, d)}</td>`;
    };
    const sections = gateways(state.doc).map((gw) => {
      const rows = radio(gw).map((d) => {
        const name = d.manual ? this._instManualName(gw, d) : esc(d.name);
        const sub = d.manual ? "" : `<div class="isub">${esc([d.model, d.eep].filter(Boolean).join(" · "))}</div>`;
        const delete_ = `<td class="rmenu">${d.manual ? this._instManualMenu(gw, d) : ""}</td>`;
        return `<tr data-in-row="${esc(d.key)}" data-k="${kindOf(d)}"><td class="name">${name}${sub}${d.manual ? this._instManualTags(gw, d) : `<div>${this._instKindTag(d)}${this._instSendTag(gw, d)}</div>`}</td>${cols.map((c) => cell(c, gw, d)).join("")}${delete_}</tr>`;
      }).join("");
      const head = cols.map((c) => `<th>${esc(F.cols[c])}</th>`).join("");
      return `<section class="gw">${this._instGwHead(gw)}<div class="tablewrap"><table class="itable"><thead><tr><th>${esc(I.device)}</th>${head}<th class="rmenu"></th></tr></thead><tbody>${rows || `<tr><td colspan="${cols.length + 2}" class="none">${esc(F.none)}</td></tr>`}</tbody></table></div></section>`;
    });
    this._artChips = artChips;
    return `${tiles}${tools}${form}${sections.join("")}<p class="isub">${esc(F.hint)}</p>`;
  },

  _instBus() {
    // the bus as documented, by its master; a server without the installation store: per gateway as before
    if (this._in.doc?.installation) return this._busView();
    const t = this._t;
    return `<p class="isub">${esc(t.doc.tbl.busIntro.replace(" (*)", ""))} ${esc(t.inst.editHint)}</p>` + this._instPerGateway((gw) => this._instBusOf(gw));
  },

  _instManualName(gw, d) {
    // the name of an entry written by hand: plain text to click, or "give it a name" while it has none
    const F = this._t.inst.funk;
    const who = `data-in-gw="${esc(gw.entry_id)}" data-in-mid="${esc(d.mid)}"`;
    if (this._in.nameEdit === d.mid) return `<input class="cell" data-in-mfield="name" ${who} data-in-focus data-in-nameend value="${esc(d.named ? d.name : "")}" placeholder="${esc(this._t.doc.manualName)}" aria-label="${esc(this._t.doc.manualName)}" autocomplete="off">`;
    if (d.named) return `<button class="namelink" data-in-nameedit="${esc(d.mid)}" title="${esc(F.editName)}">${esc(d.name)}</button>`;
    return `<span class="unnamed">${esc(F.unnamed)}</span> <button class="placeadd" data-in-nameedit="${esc(d.mid)}">+ ${esc(F.giveName)}</button>`;
  },

  _instDocForm(kinds) {
    // the form of an entry for the documentation: what it is, where it sits, what feeds it; the draft survives a redraw
    const t = this._t;
    const I = t.inst;
    const F = I.funk;
    const state = this._in;
    const draft = state.docDraft;
    const v = (name) => esc(draft[name] ?? "");
    const kind = draft.kind || "taster";
    const field = (name, label, extra = "", cls = "") => `<label class="${cls}"><span>${esc(label)}</span><input data-in-doc-field="${name}" value="${v(name)}" autocomplete="off" ${extra}></label>`;
    const places = I.placeParts.map((label, i) => `<input data-in-doc-field="loc${i}" value="${v(`loc${i}`)}" placeholder="${esc(label)}" aria-label="${esc(label)}" autocomplete="off">`).join("<i>·</i>");
    const gws = gateways(state.doc);
    const gateway = gws.length > 1 ? `<label><span>${esc(F.gateway)}</span><select data-in-doc-field="gateway">${gws.map((g) => `<option value="${esc(g.entry_id)}" ${draft.gateway === g.entry_id ? "selected" : ""}>${esc(g.title)}</option>`).join("")}</select></label>` : "";
    const fused = ["bus", "aktor"].includes(kind);
    return `<div class="docform"><h4>${esc(F.formTitle)}</h4><p class="isub">${esc(I.funk.documentedHint)}.</p><div class="dfgrid">
      ${field("name", t.doc.manualName)}
      ${field("address", t.doc.manualAddress, `class="mono" maxlength="11" placeholder="${esc(F.idPlaceholder)}"`)}
      <label><span>${esc(I.art)}</span><select data-in-doc-field="kind">${kinds.map((k) => `<option value="${k}" ${kind === k ? "selected" : ""}>${esc(I.kinds[k])}</option>`).join("")}</select></label>
      ${gateway}
      ${field("model", F.cols.model, `placeholder="${esc(F.modelExample)}"`)}
      <label class="wide"><span>${esc(label(t, "location"))}</span><div class="place" data-in-docplace>${places}</div></label>
      ${field("function", t.doc.manualFunctionHead, `placeholder="${esc(t.doc.manualFunction)}"`, "wide")}
      ${fused ? field("circuit", label(t, "circuit")) + field("fuse", label(t, "fuse")) : ""}
      ${field("installed", label(t, "installed"), 'type="date"')}
      ${field("power", label(t, "power"))}
    </div><div class="dfbtns"><button class="chip primary" data-in-act="doc-add">${esc(F.add)}</button><button class="chip" data-in-act="doc-cancel">${esc(F.cancel)}</button></div>${state.docError ? `<div class="cerr" role="alert">${esc(state.docError)}</div>` : ""}</div>`;
  },

  _instNameDone(e) {
    // leaving the name field of an entry: back to the plain name, only that cell redrawn so a click elsewhere is not lost
    const input = e.target;
    if (!input.matches?.("[data-in-nameend]")) return;
    this._in.nameEdit = "";
    const gw = gateways(this._in.doc).find((g) => g.entry_id === input.dataset.inGw);
    const d = gw && this._instExtras(gw).find((x) => x.mid === input.dataset.inMid);
    const cell = input.closest("td");
    if (d && cell) cell.innerHTML = `${this._instManualName(gw, d)}${this._instManualTags(gw, d)}`;
  },

  _instManualTags(gw, d) {
    // under the name: the ID (with its type), the kind to change, and that Home Assistant does not know it
    const I = this._t.inst;
    const kinds = ["taster", "sensor", "aktor"];
    const items = kinds.map((k) => `<button data-in-mkind="${esc(gw.entry_id)}|${esc(d.mid)}|${k}">${esc(I.kinds[k])}</button>`).join("");
    const kind = `<details class="colmenu kindmenu"><summary class="tag kind k-${kindOf(d)}" title="${esc(I.art)}">${esc(I.kinds[kindOf(d)])} ⌄</summary><div class="items">${items}</div></details>`;
    return `<div class="isub mono">${esc([d.id, d.model].filter(Boolean).join(" · "))}</div><div>${kind} <span class="tag doc" title="${esc(I.funk.documentedHint)}">${esc(I.funk.documented)}</span></div>`;
  },

  _instRowMenu(gw, d) {
    // the more menu of a row of the devices table: an entry by hand, or a power supply
    const t = this._t;
    if (d.manual) return this._instManualMenu(gw, d);
    if (!d.psu) return "";
    return `<details class="colmenu rowmenu"><summary class="icon-btn" title="${esc(t.more)}" aria-label="${esc(t.more)}">${svg(ICON.more)}</summary><div class="items"><button data-in-supply-del="${esc(d.sid)}" data-in-gw="${esc(gw.entry_id)}">${esc(t.doc.supplyRemove)}</button></div></details>`;
  },

  _instManualMenu(gw, d) {
    // the more menu of an entry: set it up in Home Assistant, or remove it
    const t = this._t;
    const item = (act, label) => `<button data-in-mact="${act}|${esc(gw.entry_id)}|${esc(d.mid)}">${esc(label)}</button>`;
    return `<details class="colmenu rowmenu"><summary class="icon-btn" title="${esc(t.more)}" aria-label="${esc(t.more)}">${svg(ICON.more)}</summary><div class="items">${item("device", t.addAsDevice)}${item("remove", t.doc.manualRemove)}</div></details>`;
  },

  _instKindTag(d) {
    const kind = kindOf(d);
    const modules = this._in.doc?.installation?.modules ?? [];
    // on the bus as documented: the tag opens its channel (or the supply's module) in the bus tab
    let target = "";
    if (d.psu) target = modules.find((m) => m.supply_id === d.sid) ? `module|${modules.find((m) => m.supply_id === d.sid).id}` : "";
    else if (d.manual) {
      const m = modules.find((x) => x.channels.some((c) => c.manual_id === d.mid));
      target = m ? `channel|${m.id}:${m.channels.find((c) => c.manual_id === d.mid).n}` : "";
    } else if (d.note_key) {
      const m = modules.find((x) => x.channels.some((c) => c.device_key === d.note_key));
      target = m ? `channel|${m.id}:${m.channels.find((c) => c.device_key === d.note_key).n}` : "";
    }
    const link = target ? `data-in-busgo="${esc(target)}" title="${esc(this._t.inst.inBus)}"` : `data-in-kind="${kind}" title="${esc(this._t.inst.kindHint)}"`;
    return `<button class="tag kind k-${kind}" ${link}>${esc(this._t.inst.kinds[kind])}${kind === "bus" && d.bus_address ? ` · ${esc(d.bus_address)}` : ""}</button>`;
  },

  _instSndLink(entryId, id) {
    // a sender ID: its row in the Sender IDs tab when it is a number of the gateway's pool
    const gw = gateways(this._in.doc).find((g) => g.entry_id === entryId);
    const plain = (x) => String(x ?? "").replace(/[^0-9A-Fa-f]/g, "");
    const raw = plain(String(id).split(" ")[0]);
    const n = gw?.base_id && raw.length === 8 ? parseInt(raw, 16) - parseInt(plain(gw.base_id), 16) : null;
    return n != null && n >= 0 && n <= 127 ? `<button class="tag mono" data-in-snd="${esc(entryId)}|${n}">${esc(id)}</button>` : `<span class="mono">${esc(id)}</span>`;
  },

  _instSendTag(gw, d) {
    // the sender numbers of a device: a jump to its rows in the Sender IDs tab
    const numbers = gw.numbers?.get(d.note_key) ?? [];
    return numbers.length ? ` <button class="tag" data-in-snd="${esc(gw.entry_id)}|${numbers[0]}" title="${esc(this._t.inst.senderTagHint)}">${esc(this._t.inst.senderTag(numbers.join(", ")))}</button>` : "";
  },

  _instBusOf(gw) {
    // the Eltako bus of one gateway: addresses grouped by the power supply that feeds them
    const t = this._t;
    const T = t.doc.tbl;
    const B = t.inst.bus;
    const lang = this._hass?.language || "en";
    const num = (n) => `${n.toLocaleString(lang, { maximumFractionDigits: 2 })} W`;
    const bus = docBus(gw, t, this._in.doc.bus_info);
    const own = gw.supplies ?? [];
    // devices of the bus series without an address yet: they get one in a group of their own
    const unaddressed = gw.devices.filter((d) => kindOf(d) === "bus" && !/^\d+$/.test(d.bus_address ?? ""));
    const addItem = (label, preset) => `<button class="chip" data-in-supply-add="${esc(gw.entry_id)}" data-in-preset="${preset}">${esc(label)}</button>`;
    const addButton = `<div><details class="colmenu supplymenu"><summary class="chip">${esc(t.doc.supplyAdd)}</summary><div class="items">${SUPPLY_PRESETS.map((p, i) => addItem(`${p.name} · ${p.watts} W`, i)).join("")}${addItem(t.doc.supplyCustom, "")}</div></details></div>`;
    if (!bus.rows.length && !own.length && !unaddressed.length) return `<div class="none">${esc(T.busEmpty)}</div>${addButton}`;
    // a supply feeds the addresses in its range; a lone supply without a range feeds them all
    const supplies = own.map((s) => ({ s, first: anum(s.first), last: anum(s.last), capacity: wnum(s.watts) }));
    const ranged = (x) => x.first !== null || x.last !== null;
    const inRange = (x, r) => r.address >= (x.first ?? 1) && r.address <= (x.last ?? 126);
    const lone = supplies.length === 1 && !ranged(supplies[0]);
    const rowsOf = supplies.map(() => []);
    const without = [];
    for (const r of bus.rows) {
      const i = own.length ? (lone ? 0 : supplies.findIndex((x) => ranged(x) && inRange(x, r))) : -1;
      if (i >= 0) rowsOf[i].push(r);
      else without.push(r);
    }
    const load = (rows) => round2(rows.reduce((n, r) => n + (r.power ?? 0), 0));
    const dups = new Set(bus.dups);
    const cell = (r, field, value, label, placeholder) => this._instCell(gw, r.key, field, value, label, placeholder);
    const row = (r) => {
      const d = r.key ? gw.devices.find((x) => x.key === r.key) : null;
      const name = d ? `${esc(d.name)}<div class="isub">${esc(d.id)}</div><div>${this._instKindTag(d)}${this._instSendTag(gw, d)}</div>` : `${esc(r.device)}<div class="isub">${esc(r.name)}</div>`;
      const tag = r.pending ? "" : r.from === "table" ? `<span class="tag" title="${esc(bus.source)}">${esc(T.busSourceTableShort)}</span>` : r.from === "group" ? `<span class="isub">${esc(T.busGroupLine)}</span>` : r.power === null ? `<span class="tag warn">${esc(T.noValue)}</span>` : "";
      const power = r.key ? `<span style="display:inline-flex;gap:6px;align-items:center;justify-content:flex-end">${cell(r, "bus_power", r.raw, `${T.power} (W)`, r.table !== null ? String(r.table).replace(".", ",") : "W")}${tag}</span>` : r.power === null ? tag : esc(num(r.power));
      return `<tr data-k="bus"${dups.has(r.address) ? ' class="dup"' : ""}><td class="name">${name}</td><td class="mono">${r.key ? cell(r, "bus_address", r.address === "" ? "" : String(r.address), T.busAddress, t.inst.shortField.bus_address) : r.address}</td><td>${r.key ? cell(r, "feedback_id", r.feedback, T.feedbackId, t.inst.shortField.feedback_id) : esc(r.feedback)}</td><td class="num">${power}</td><td>${r.key ? cell(r, "group", r.group, T.partOf) : esc(r.group)}</td></tr>`;
    };
    const sfield = (x, field, ph, width) => `<input class="cell" data-in-sfield="${field}" data-in-gw="${esc(gw.entry_id)}" data-in-sid="${esc(x.s.id)}" value="${esc(x.s[field] ?? "")}" placeholder="${esc(ph)}" aria-label="${esc(ph)}" style="width:${width}px;min-width:0" autocomplete="off"${field === "watts" ? ' inputmode="decimal"' : field === "name" ? "" : ' inputmode="numeric"'}>`;
    const usage = (capacity, rows) => {
      const l = load(rows);
      const pct = capacity ? Math.round((l / capacity) * 100) : null;
      // Eltako's manuals name 8 to 12 W for the FSNT14-12V/12W; a third of reserve (8 W of 12 W) is the cautious one
      return { l, pct, over: capacity !== null && l > capacity, advise: capacity !== null && l > capacity * RESERVE_LIMIT && l <= capacity };
    };
    const bar = (u) => (u.pct === null ? "" : `<span class="barbg"><i class="${u.advise || u.over ? "hot" : ""}" style="width:${Math.min(u.pct, 100)}%"></i></span>`);
    const groups = supplies.map((x, i) => {
      const u = usage(x.capacity, rowsOf[i]);
      const text = x.capacity !== null ? `${num(u.l)} ${t.inst.of} ${num(x.capacity)}${u.over ? ` · ${B.overloaded}` : u.advise ? ` · ${B.supplyAdvice}` : ""}` : num(u.l);
      const place = [x.s.location, x.s.circuit, x.s.fuse].filter(Boolean).join(", ");
      return { u, html: `<tr class="psu${u.over ? " bad" : ""}" data-k="psu"><td colspan="5"><div class="psurow">${sfield(x, "name", t.doc.supplyName, 150)}${sfield(x, "watts", t.doc.supplyWatts, 64)}<span class="isub">W</span><span class="isub">${esc(T.busAddress)}</span>${sfield(x, "first", t.doc.supplyFirst, 96)}<span>–</span>${sfield(x, "last", t.doc.supplyLast, 96)}${bar(u)}<span class="isub">${esc(text)}</span>${place ? `<span class="isub">· ${esc(place)}</span>` : ""}<button class="icon-btn" data-in-supply-del="${esc(x.s.id)}" data-in-gw="${esc(gw.entry_id)}" title="${esc(t.doc.supplyRemove)}" aria-label="${esc(t.doc.supplyRemove)}">${svg(ICON.close)}</button></div></td></tr>${rowsOf[i].map(row).join("")}` };
    });
    let body = groups.map((g) => g.html).join("");
    if (!own.length) {
      const standard = bus.supplies[0];
      body += `<tr class="psu"><td colspan="5"><div class="psurow"><b>${esc(standard.name)}</b><span class="isub">${esc(num(standard.capacity ?? 0))}${standard.percent !== null ? ` · ${standard.percent} %` : ""}</span><span class="isub">${esc(B.standardNote)}</span></div></td></tr>`;
    }
    if (without.length) body += `${own.length ? `<tr class="psu bad"><td colspan="5"><b>${esc(B.noSupply)}</b> <span class="isub">${without.length}</span></td></tr>` : ""}${without.map(row).join("")}`;
    if (unaddressed.length) body += `<tr class="psu bad"><td colspan="5"><b>${esc(B.noAddress)}</b> <span class="isub">${unaddressed.length} · ${esc(B.noAddressHint)}</span></td></tr>${unaddressed.map((d) => row({ key: d.key, address: "", feedback: d.feedback_id ?? "", group: d.group ?? "", raw: d.bus_power ?? "", table: d.bus_power_table ?? null, from: "", power: null, pending: true })).join("")}`;
    const sum = `<tr><td colspan="3"><b>${esc(T.busSum(bus.counted, bus.rows.length))}</b></td><td class="num"><b>${esc(num(bus.sum))}</b></td><td></td></tr>`;
    const overCount = groups.filter((g) => g.u.over).length;
    const runs = bus.items.filter((r) => r.free).map((r) => (r.from === r.to ? `${r.from}` : `${r.from}–${r.to}`));
    const missing = bus.rows.length - bus.counted;
    const tile = (title, value, bad = false) => `<div class="tile${bad === "ok" ? " ok" : bad ? " bad" : ""}"><small>${esc(title)}</small>${value}</div>`;
    const tiles = `<div class="tiles">${tile(B.duplicates, esc(bus.dups.length ? B.dupText(bus.dups.join(", ")) : B.none), bus.dups.length > 0 ? true : "ok")}${tile(B.used, esc(B.usedOf(new Set(bus.rows.map((r) => r.address)).size)))}${tile(B.free, esc(runs.slice(0, 6).join(", ") + (runs.length > 6 ? " …" : "")))}${tile(B.power, `${esc(num(bus.sum))}${missing ? ` <span class="isub">${esc(B.withoutValue(missing))}</span>` : ""}`)}${tile(B.supplies, esc(overCount ? B.supplyOver(overCount) : without.length && own.length ? B.supplyWithout(without.length) : B.supplyOk), overCount > 0 || (own.length > 0 && without.length > 0) ? true : "ok")}</div>`;
    const notes = [
      bus.fromTable ? T.busFromTable(bus.source).replace(/^\* /, "") : "",
      bus.multi.length ? T.busMulti(bus.multi.join(", ")) : "",
    ].filter(Boolean).map((n) => `<p class="isub">${esc(n)}</p>`).join("");
    return `${tiles}${this._instTable([t.inst.device, T.busAddress, T.feedbackId, T.power, T.partOf], body + sum)}${addButton}<div class="notes">${notes}</div>`;
  },

  _instDevicesTab() {
    // the devices in one of four views: all, on the Eltako bus, on radio, virtual
    const t = this._t.inst;
    const state = this._in;
    const all = gateways(state.doc).flatMap((gw) => [...gw.devices, ...this._instExtras(gw)]);
    // each view counts the rows of the devices table it stands for, as the kind chips do
    const count = (view) => all.filter((d) => !VIEW_KINDS[view] || VIEW_KINDS[view].includes(kindOf(d))).length;
    const seg = VIEWS.map((v) => `<button data-in-view="${v}" aria-pressed="${state.view === v}">${esc(t.views[v])}<span class="isub">${count(v)}</span></button>`).join("");
    this._artChips = "";
    const body = { all: () => this._instDevices(), virt: () => this._instVirt(), bus: () => this._instBus(), funk: () => this._instFunk() }[state.view]();
    // one filter bar: the views, then the kinds of the view
    return `<div class="gbar fbar"><div class="seg" role="group" aria-label="${esc(t.views.label)}">${seg}</div>${this._artChips ? `<span class="fsep" aria-hidden="true"></span>${this._artChips}` : ""}</div>${body}`;
  },

  _instPlace(gw, d) {
    // the place: cabinet and row from the documented cabinets, the slot as a number, ✕ clears it;
    // a place that names no documented cabinet stays as three free fields (nothing is lost)
    const I = this._t.inst;
    const state = this._in;
    const parts = placeParts(d.location);
    const who = d.psu ? `data-in-sid="${esc(d.sid)}"` : d.manual ? `data-in-mid="${esc(d.mid)}"` : `data-in-key="${esc(d.key)}"`;
    const id = d.psu ? d.sid : d.manual ? d.mid : d.key;
    if (!d.location && state.placeEdit !== id) return `<button class="placeadd empty" data-in-placeedit="${esc(id)}" aria-label="${esc(I.placeAdd)}: ${esc(d.name)}" title="${esc(I.placeAdd)}"><span class="ph">–</span><span class="hv">+ ${esc(I.placeAdd)}</span></button>`;
    const focus = state.placeEdit === id ? " data-in-focus" : "";
    const clear = `<button class="placeclr" data-in-placeclear title="${esc(I.placeClear)}" aria-label="${esc(I.placeClear)}: ${esc(d.name)}">✕</button>`;
    const rows = (state.doc?.installation?.cabinets ?? []).flatMap((c) => c.rows.map((r) => `${c.name} · ${r.name}`));
    const current = parts.slice(0, 2).filter(Boolean).join(" · ");
    const free = state.placeText.has(id) || (current && !rows.includes(current)) || !state.doc?.installation;
    if (free) {
      const inputs = I.placeParts.map((label, i) => `<input data-in-part="${i}" value="${esc(parts[i])}" placeholder="${esc(label)}" aria-label="${esc(label)}: ${esc(d.name)}" autocomplete="off">`).join("<i>·</i>");
      return `<div class="place${d.location ? "" : " blank"}" data-in-place data-in-gw="${esc(gw.entry_id)}" ${who}>${inputs.replace("<input ", `<input${focus} `)}${clear}</div>`;
    }
    const options = [`<option value="">${esc(I.placeChoose)}</option>`, ...rows.map((r) => `<option value="${esc(r)}"${r === current ? " selected" : ""}>${esc(r)}</option>`), `<option value="__new">${esc(I.placeNewCabinet)}</option>`, `<option value="__text">${esc(I.placeFreeText)}</option>`].join("");
    const select = `<select data-in-prow${focus} aria-label="${esc(I.placeParts[0])} · ${esc(I.placeParts[1])}: ${esc(d.name)}">${options}</select>`;
    const slot = `<input data-in-part="2" value="${esc(parts[2])}" placeholder="${esc(I.placeParts[2])}" aria-label="${esc(I.placeParts[2])}: ${esc(d.name)}" inputmode="decimal" autocomplete="off">`;
    return `<div class="place${d.location ? "" : " blank"}" data-in-place data-in-gw="${esc(gw.entry_id)}" ${who}>${select}<i>·</i>${slot}${clear}</div>`;
  },

  _instPlaceValue(box) {
    // the place a cell holds, as the notes write it: "cabinet · row · slot"
    const select = box.querySelector("[data-in-prow]");
    if (!select) return joinPlace([...box.querySelectorAll("input")].map((i) => i.value));
    const [cabinet = "", row = ""] = select.value.startsWith("__") ? [] : select.value.split(" · ");
    return joinPlace([cabinet, row, box.querySelector('[data-in-part="2"]')?.value ?? ""]);
  },

  async _instPlaceCabinet(box) {
    // "add cabinet" in a place cell: a cabinet with one row (12 TE), then the place goes there
    const I = this._t.inst;
    const select = box.querySelector("[data-in-prow]");
    const name = (globalThis.prompt?.(I.placeCabinetPrompt, I.busv.cabinetDefault((this._in.doc.installation?.cabinets.length ?? 0) + 1)) ?? "").trim();
    if (!name) {
      select.value = "";
      return;
    }
    const row = I.busv.rowDefault(1);
    try {
      await this._hass.callWS({ type: "enocean_eltako/installation/set", kind: "cabinet", item: { name, note: "", rows: [{ name: row, te: 12 }] } });
    } catch (err) {
      box.classList.add("bad");
      return;
    }
    this._in.doc.installation.cabinets.push({ id: "", name, note: "", rows: [{ id: "", name: row, te: 12 }] });
    const option = document.createElement("option");
    option.value = `${name} · ${row}`;
    option.textContent = option.value;
    select.insertBefore(option, select.querySelector('option[value="__new"]'));
    select.value = option.value;
    await this._instSavePlace(box);
  },

  _instProgress() {
    // how many devices have a place; virtual devices have none to give
    const t = this._t.inst;
    const all = gateways(this._in.doc).flatMap((gw) => [...gw.devices.filter((d) => !isVirtual(d)), ...(gw.supplies ?? []), ...(gw.manual ?? [])]);
    const placed = all.filter((d) => d.location).length;
    if (!all.length) return "";
    const pct = Math.round((placed / all.length) * 100);
    return `<div class="progress"><span>${esc(t.progress(placed, all.length))}</span><div class="barbg"><i style="width:${pct}%"></i></div><span>${pct} %</span>${placed < all.length ? `<button class="chip" data-in-act="next-open">${esc(t.nextOpen)}</button>` : ""}</div>`;
  },

  _instDevices() {
    const t = this._t;
    const I = t.inst;
    const state = this._in;
    const kinds = VIEW_KINDS[state.view];
    // the fields the column menu has on; a table shows those that some of its rows can use
    const enabled = INSTALLATION_FIELDS.filter((f) => state.columns.has(f));
    const showArea = state.columns.has("area");
    const multi = gateways(state.doc).length > 1;
    const key = (gw, d) => `${gw.entry_id}|${d.key}`;
    const applies = (d, f) => {
      if (d.psu) return ["location", "circuit", "fuse", "note"].includes(f);
      if (d.manual) return f === "location" || f === "note" || (["circuit", "fuse", "installed"].includes(f) && (!FIELD_KINDS[f] || FIELD_KINDS[f].includes(kindOf(d)))) || (kindOf(d) === "bus" ? ["bus_address", "feedback_id", "bus_power"].includes(f) : f === "power");
      if (isVirtual(d)) return f === "note";
      return !FIELD_KINDS[f] || FIELD_KINDS[f].includes(kindOf(d));
    };
    const psus = (gw) => this._instExtras(gw);
    const pass = (d) => matches(d, state.q)
      && (!kinds || kinds.includes(kindOf(d)))
      && (state.art === "all" || kindOf(d) === state.art)
      && (!state.miss.loc || (!isVirtual(d) && !d.location))
      && (!state.miss.fuse || (FUSE_KINDS.has(kindOf(d)) && !d.fuse));
    const row = (gw, d, columns) => {
      const cells = columns
        .map((f) => {
          if (!applies(d, f)) return `<td><span class="dash">–</span></td>`;
          if (f === "location") return `<td>${this._instPlace(gw, d)}</td>`;
          // an empty field shows the same quiet dash as a field that does not apply; the label is its name
          if (d.manual) return `<td><input class="cell" data-in-mfield="${MANUAL_FIELD[f]}" data-in-gw="${esc(gw.entry_id)}" data-in-mid="${esc(d.mid)}" value="${esc(d[f] ?? "")}" placeholder="–" title="${esc(label(t, f))}" aria-label="${esc(label(t, f))}: ${esc(d.name)}" autocomplete="off"></td>`;
          if (d.psu) return `<td><input class="cell" data-in-sfield="${f}" data-in-gw="${esc(gw.entry_id)}" data-in-sid="${esc(d.sid)}" value="${esc(d[f] ?? "")}" placeholder="–" title="${esc(label(t, f))}" aria-label="${esc(label(t, f))}: ${esc(d.name)}" autocomplete="off"></td>`;
          return `<td><input class="cell" ${f === "installed" ? 'type="date"' : ""} data-in-field="${f}" data-in-gw="${esc(gw.entry_id)}" data-in-key="${esc(d.key)}" value="${esc(d[f] ?? "")}" placeholder="–" title="${esc(label(t, f))}" aria-label="${esc(label(t, f))}: ${esc(d.name)}" autocomplete="off"></td>`;
        })
        .join("");
      const picked = state.selected.has(key(gw, d));
      const area = showArea ? `<td class="isub">${esc(d.area || "–")}</td>` : "";
      const pick = d.psu || d.manual ? "" : `<input type="checkbox" data-in-pick="${esc(key(gw, d))}" ${picked ? "checked" : ""} aria-label="${esc(d.name)}">`;
      const gwTag = multi && state.group !== "gateway" ? ` <span class="tag" title="${esc(t.gateway)}">${esc(gw.title)}</span>` : "";
      return `<tr data-in-row="${esc(d.key)}" data-k="${kindOf(d)}"><td>${pick}</td><td class="name">${d.manual ? this._instManualName(gw, d) : d.key && !d.psu && this._inPanel(d.key) ? `<button class="namelink" data-in-device="${esc(d.key)}" title="${esc(t.inPanelHint)}">${esc(d.name)}</button>` : esc(d.name)}${d.manual ? this._instManualTags(gw, d) : `<div class="isub">${esc(d.psu ? d.model : d.id)}</div><div>${this._instKindTag(d)}${d.psu ? "" : this._instSendTag(gw, d)}${gwTag}</div>`}</td>${area}${cells}<td class="rmenu">${this._instRowMenu(gw, d)}</td></tr>`;
    };
    // one table for all gateways; the gateway is a tag, or the group
    const found = gateways(state.doc).flatMap((gw) => [...gw.devices, ...psus(gw)].filter(pass).map((d) => ({ gw, d })));
    const columns = enabled.filter((f) => found.some(({ d }) => applies(d, f)));
    const sortValue = (d) => String(state.devSort === "name" ? d.name : state.devSort === "area" ? d.area : d[state.devSort] ?? "");
    found.sort((a, b) => {
      const x = sortValue(a.d);
      const y = sortValue(b.d);
      return (!x - !y || x.localeCompare(y, undefined, { numeric: true }) * state.devDir) || a.d.name.localeCompare(b.d.name);
    });
    const pages = Math.max(1, Math.ceil(found.length / state.devPs));
    const pg = Math.min(state.devPg.all ?? 0, pages - 1);
    state.devPg.all = pg;
    const devices = found.slice(pg * state.devPs, (pg + 1) * state.devPs);
    const span = columns.length + (showArea ? 1 : 0) + 3;
    let rows;
    if (state.group && devices.length) {
      const groups = new Map();
      const place = (d) => placeParts(d.location).slice(0, 2).filter(Boolean).join(" · ");
      for (const item of devices) {
        const { gw, d } = item;
        const name = state.group === "gateway" ? gw.title : isVirtual(d) && state.group === "location" ? I.virtualNoPlace : (state.group === "area" ? d.area : place(d)) || (state.group === "area" ? I.noGroup : I.noPlace);
        groups.set(name, [...(groups.get(name) ?? []), item]);
      }
      const rank = (n) => (n === I.virtualNoPlace ? 2 : n === I.noGroup || n === I.noPlace ? 1 : 0);
      rows = [...groups.entries()]
        .sort(([a], [b]) => rank(a) - rank(b) || a.localeCompare(b, undefined, { numeric: true }))
        .map(([name, list]) => {
          const id = `${state.group}|${name}`;
          const closed = state.folded.has(id);
          const busRow = state.group === "location" ? (state.doc.installation?.cabinets ?? []).flatMap((c) => c.rows.map((r) => [`${c.name} · ${r.name}`, r.id])).find(([n]) => n === name)?.[1] : null;
          const busLink = busRow ? ` <button class="tag" data-in-busgo="row|${esc(busRow)}" title="${esc(I.busRowHint)}">→ ${esc(I.views.bus)}</button>` : "";
          return `<tr class="grp" data-in-fold="${esc(id)}"><td colspan="${span}">${closed ? "▸" : "▾"} ${esc(name)} <span class="tag">${list.length}</span>${busLink}</td></tr>${closed ? "" : list.map(({ gw, d }) => row(gw, d, columns)).join("")}`;
        })
        .join("");
    } else rows = devices.map(({ gw, d }) => row(gw, d, columns)).join("");
    const th = (f, text) => `<th class="sortable" data-in-devsort="${f}"${state.devSort === f ? ` aria-sort="${state.devDir > 0 ? "ascending" : "descending"}"` : ""}><span>${esc(text)}</span><i class="sarrow">${state.devSort === f && state.devDir < 0 ? "↓" : "↑"}</i></th>`;
    const head = columns.map((f) => th(f, label(t, f))).join("");
    const sizes = [25, 50, 100].map((n) => `<option${state.devPs === n ? " selected" : ""}>${n}</option>`).join("");
    const from = found.length ? pg * state.devPs + 1 : 0;
    const pager = found.length > 25 || state.devPs !== 25 ? `<div class="spager"><span>${esc(I.sid.range(from, from + devices.length - (found.length ? 1 : 0), found.length))}</span><div><label>${esc(I.sid.perPage)} <select data-in-devps aria-label="${esc(I.sid.perPage)}">${sizes}</select></label><button class="chip" data-in-devpg="all|-1"${pg === 0 ? " disabled" : ""} aria-label="${esc(I.sid.prev)}">‹</button><span>${esc(I.sid.page(pg + 1, pages))}</span><button class="chip" data-in-devpg="all|1"${pg >= pages - 1 ? " disabled" : ""} aria-label="${esc(I.sid.next2)}">›</button></div></div>` : "";
    const sections = [`<section class="gw"><header class="gwhead"><h3>${esc(I.views.all)}</h3><span class="isub">${esc(I.deviceCount(found.length))}</span></header><div class="tablewrap"><table class="itable"><thead><tr><th></th>${th("name", I.device)}${showArea ? th("area", I.area) : ""}${head}<th class="rmenu"></th></tr></thead><tbody>${rows || `<tr><td colspan="${span}" class="none">${esc(I.noDevices)}</td></tr>`}</tbody></table></div>${pager}</section>`];
    const picked = state.selected.size;
    const bulk = picked
      ? `<div class="bulk"><b>${esc(I.selected(picked))}</b><select data-in-bulk-field aria-label="${esc(I.setField)}">${INSTALLATION_FIELDS.map((f) => `<option value="${f}">${esc(label(t, f))}</option>`).join("")}</select><input data-in-bulk-value placeholder="${esc(I.value)}" aria-label="${esc(I.value)}"><button class="chip" data-in-act="bulk">${esc(I.apply)}</button><button class="chip" data-in-act="unpick">${esc(I.clearSelection)}</button></div>`
      : "";
    const paste = !state.sheet ? "" : `<div class="sheet"><div class="sheethead"><b>${esc(I.pasteTitle)}</b><button class="iconbtn" data-in-act="sheet" aria-label="${esc(I.sheetClose)}" title="${esc(I.sheetClose)}">${svg(ICON.close)}</button></div><p class="isub">${esc(I.pasteHint)}</p>
      <ol class="sheetsteps">
        <li><b>1</b><div><button class="chip" data-in-act="copy-table">${esc(I.copyTable)}</button> <span class="isub">${esc(I.sheetCopyHint)}</span></div></li>
        <li><b>2</b><div>${esc(I.sheetEdit)}</div></li>
        <li><b>3</b><div><textarea class="paste" data-in-paste placeholder="${esc(I.pastePlaceholder)}" aria-label="${esc(I.pasteTitle)}">${esc(state.paste)}</textarea><div class="sheetrun"><button class="chip" data-in-act="paste">${esc(I.sheetApply)}</button> <span class="isub" data-in-paste-info>${esc(state.pasteResult || this._instPasteSeen())}</span></div></div></li>
      </ol></div>`;
    const colName = (f) => (f === "area" ? I.area : label(t, f));
    const menu = `<details class="colmenu" ${state.colMenu ? "open" : ""}><summary class="chip">${esc(I.columns)}</summary><div class="items">${Object.entries(COLUMN_GROUPS).map(([g, fields]) => `<div class="colgroup"><b>${esc(I.columnGroups[g])}</b><button class="tag" data-in-colgroup="${g}|all">${esc(I.colAll)}</button><button class="tag" data-in-colgroup="${g}|none">${esc(I.colNone)}</button></div>${fields.map((f) => `<label><input type="checkbox" data-in-col="${f}" ${state.columns.has(f) ? "checked" : ""}>${esc(colName(f))}</label>`).join("")}`).join("")}<span class="isub">${esc(I.columnsHint)}</span></div></details>`;
    const present = gateways(state.doc).flatMap((gw) => [...gw.devices, ...psus(gw)]);
    const kindList = kinds ?? ["bus", "sensor", "taster", "aktor", "virt", "psu"];
    const artChips = kindList.length > 1
      ? `<div class="chips"><button class="chip" data-in-art="all" aria-pressed="${state.art === "all"}">${esc(I.all)} <b>${present.filter((d) => !kinds || kinds.includes(kindOf(d))).length}</b></button>${kindList.filter((k) => state.art === k || present.some((d) => kindOf(d) === k)).map((k) => `<button class="chip" data-k="${k}" data-in-art="${k}" aria-pressed="${state.art === k}">${esc(I.kinds[k])} <b>${present.filter((d) => kindOf(d) === k).length}</b></button>`).join("")}</div>`
      : "";
    const placeable = present.filter((d) => !isVirtual(d));
    const fusable = present.filter((d) => FUSE_KINDS.has(kindOf(d)));
    const missTile = (name, list, field, text) => {
      const miss = list.filter((d) => !d[field]).length;
      return `<button class="stile ${miss ? "w" : "f"}" data-in-miss="${name}" aria-pressed="${state.miss[name]}"><b>${miss ? miss : "✓"}</b><span>${esc(text)}</span><small class="isub">${esc(I.recorded(list.length - miss, list.length))}</small></button>`;
    };
    const missChips = state.view === "all"
      ? `<div class="stiles quiet">${missTile("loc", placeable, "location", I.missPlace)}${missTile("fuse", fusable, "fuse", I.missFuse)}${placeable.some((d) => !d.location) ? `<button class="chip text" data-in-act="next-open" style="align-self:center">${esc(I.nextOpen)}</button>` : ""}</div>`
      : "";
    const group = state.view === "all"
      ? `<label class="isub">${esc(I.groupBy)} <select data-in-groupsel aria-label="${esc(I.groupBy)}"><option value="">${esc(I.groupNone)}</option><option value="area" ${state.group === "area" ? "selected" : ""}>${esc(I.byArea)}</option><option value="location" ${state.group === "location" ? "selected" : ""}>${esc(I.byPlace)}</option><option value="gateway" ${state.group === "gateway" ? "selected" : ""}>${esc(I.byGateway)}</option></select></label>`
      : "";
    const search = `<input class="isearch" data-in-search value="${esc(state.q)}" placeholder="${esc(I.search)}" aria-label="${esc(I.search)}">`;
    this._artChips = artChips;
    return `<div class="itools" style="align-items:center">${search}${group}<span style="flex:1"></span><button class="chip" data-in-act="sheet" aria-pressed="${state.sheet}">${svg(ICON.table)}${esc(I.sheetButton)}</button>${menu}</div>${paste}${missChips}${bulk}${sections.join("")}`;
  },

  _instLinks() {
    // who is taught into which actuator: cards by actuator or by sender, or a matrix of both
    const t = this._t;
    const state = this._in;
    const L = t.inst.links;
    const seg = (view, text) => `<button data-in-linkview="${view}" aria-pressed="${state.linkView === view}">${esc(text)}</button>`;
    const bar = `<div class="gbar"><div class="seg" role="group">${seg("actuator", L.byActuator)}${seg("sender", L.bySender)}${seg("matrix", L.matrix)}</div></div><p class="isub sintro">${esc(L.intro)} <span class="info" title="${esc(L.honest)}">ⓘ</span></p>`;
    const sections = gateways(state.doc).map((gw) => `<section class="gw">${this._instGwHead(gw)}${this._instLinksOf2(gw)}</section>`);
    return bar + (sections.join("") || `<div class="none">${esc(t.inst.noDevices)}</div>`);
  },

  _instLinkModel(gw) {
    // the actuators and the senders of a gateway as the cards show them
    const plain = (id) => String(id ?? "").replaceAll("-", "").toUpperCase();
    const byNote = new Map(gw.devices.map((d) => [d.note_key, d]));
    const byId = new Map(gw.devices.filter((d) => d.id).map((d) => [plain(d.id), d]));
    const actuators = new Map();
    for (const d of gw.devices) if (isActuator(d)) actuators.set(d.note_key, { key: d.note_key, device: d, name: d.name, id: d.id, links: [] });
    for (const l of gw.links) {
      const key = l.to_key || `name|${l.to_name}`;
      if (!actuators.has(key)) actuators.set(key, { key, device: byNote.get(l.to_key) ?? null, name: l.to_name, id: l.to_id, links: [] });
      actuators.get(key).links.push(l);
    }
    const senders = new Map();
    for (const l of gw.links) {
      const key = l.from_id ? plain(l.from_id) : `name|${l.from_name}`;
      if (!senders.has(key)) senders.set(key, { key, id: l.from_id, name: l.from_kind === "entered" ? l.from_name : "", kind: l.from_kind, device: byId.get(plain(l.from_id)) ?? null, links: [] });
      senders.get(key).links.push(l);
    }
    return { plain, byNote, byId, actuators: [...actuators.values()].sort((a, b) => a.name.localeCompare(b.name)), senders: [...senders.values()].sort((a, b) => (a.name || a.id).localeCompare(b.name || b.id)) };
  },

  _instLinksOf2(gw) {
    const t = this._t;
    const L = t.inst.links;
    const state = this._in;
    const model = this._instLinkModel(gw);
    const testable = (a) => a.device && a.device.category === "lighting" && (a.device.senders ?? []).length > 0;
    const untested = (l) => l.source === "assigned" && l.status === "unverified";
    const nTested = model.actuators.flatMap((a) => (testable(a) ? a.links.filter((l) => l.source === "assigned") : []));
    const interactive = state.linkView !== "matrix";
    const tile = (title, value, tone, filter) => interactive ? `<button class="stile ${tone}${value === "0" && filter !== "all" ? " zero" : ""}" data-in-linkfilter="${filter}" aria-pressed="${state.linkFilter === filter}"><b>${value}</b><span>${esc(title)}</span></button>` : `<div class="stile ${tone}"><b>${value}</b><span>${esc(title)}</span></div>`;
    const without = model.actuators.filter((a) => !a.links.length && a.device).length;
    const noAnswer = gw.links.filter((l) => l.status === "no_answer").length;
    const notTested = nTested.filter(untested).length;
    const confirmed = gw.links.filter((l) => l.status === "confirmed").length;
    const tiles = `<div class="stiles">${tile(L.tiles.actuators, String(model.actuators.length), "u", "all")}${tile(L.tiles.none, String(without), "w", "none")}${tile(L.tiles.noAnswer, String(noAnswer), "d", "noanswer")}${tile(L.tiles.untested, String(notTested), "w", "untested")}${tile(L.tiles.answered, String(confirmed), "f", "confirmed")}</div>`;
    const chip = (attr, value, current, text, count = null) => `<button class="chip" ${attr}="${value}" aria-pressed="${current === value}">${esc(text)}${count === null ? "" : ` <b>${count}</b>`}</button>`;
    const filtered = state.linkFilter !== "all" || state.linkSource !== "all" || state.q;
    const filters = state.linkView === "matrix" ? "" : `<div class="chips" style="margin-bottom:8px"><span class="isub lead">${esc(L.source.title)}</span>${["assigned", "declared", "entered"].map((x) => `<button class="chip" data-src="${x}" data-in-linksource="${state.linkSource === x ? "all" : x}" aria-pressed="${state.linkSource === x}" title="${esc(L.sourceHint[x])}">${esc(L.source[x])} <b>${gw.links.filter((l) => l.source === x).length}</b></button>`).join("")}<span style="flex:1"></span>${filtered ? `<button class="chip" data-in-linkreset="1">${esc(L.reset)}</button>` : ""}</div><div class="itools" style="align-items:center"><input class="isearch" data-in-search value="${esc(state.q)}" placeholder="${esc(L.search)}" aria-label="${esc(L.search)}"><span style="flex:1"></span><span class="isub">${esc(L.sort)}</span><span class="seg" role="group">${["name", "status", "count"].map((k) => `<button data-in-linksort="${k}" aria-pressed="${state.linkSort === k}">${esc(L.sorts[k])}${state.linkSort === k ? (state.linkDir > 0 ? " ↑" : " ↓") : ""}</button>`).join("")}</span><button class="chip" data-in-linklearn="1" aria-pressed="${state.linkLearn}" title="${esc(L.learnHint)}">${esc(L.learn)}</button></div>`;
    const passLink = (l) => (state.linkSource === "all" || l.source === state.linkSource) && (state.linkFilter !== "untested" || untested(l)) && (state.linkFilter !== "noanswer" || l.status === "no_answer") && (state.linkFilter !== "confirmed" || l.status === "confirmed");
    const body = state.linkView === "matrix" ? this._instLinkMatrix(gw, model) : state.linkView === "sender" ? this._instLinkBySender(gw, model, passLink) : this._instLinkByActuator(gw, model, passLink, testable);
    return `${tiles}${filters}<div class="${state.linkLearn ? "" : "nolearn"}">${body}</div>`;
  },

  _instLinkRow(gw, l, model, mode) {
    // one link in fixed columns: the other end (name and ID) | role | where it comes from | learn
    // position | state with a short time (the full one as tooltip) | actions at the right
    const t = this._t;
    const L = t.inst.links;
    const lang = this._hass.language;
    const plain = model.plain;
    const goto = (key, name) => (key ? `<a data-in-goto="${esc(key)}">${esc(name)}</a>` : esc(name));
    let who;
    if (mode === "actuator") {
      const device = model.byId.get(plain(l.from_id)) ?? null;
      // a sender written down by hand that is an entry by hand: its row in the devices table
      const manual = !device && l.from_id ? (gw.manual ?? []).find((m) => plain(m.address) === plain(l.from_id)) : null;
      const name = l.from_kind === "entered" ? l.from_name || L.from.entered : L.from[l.from_kind];
      const target = device ? device.key : manual ? `manual|${manual.id}` : "";
      const number = l.from_kind === "ha" && gw.base_id && l.from_id ? parseInt(plain(l.from_id), 16) - parseInt(plain(gw.base_id), 16) : null;
      const id = l.from_id ? (number != null && number >= 0 && number <= 127 ? `<button class="tag mono" data-in-snd="${esc(gw.entry_id)}|${number}" title="${esc(t.inst.senderTagHint)}">${esc(l.from_id)}</button>` : `<span class="tag mono">${esc(l.from_id)}</span>`) : "";
      who = `<div class="nm">${goto(target, name)} ${id}</div>`;
    } else {
      const target = model.byNote.get(l.to_key) ?? null;
      who = `<div class="nm">${goto(target?.key, l.to_name)} ${l.to_id ? `<span class="tag mono">${esc(l.to_id)}</span>` : ""}</div>`;
    }
    const role = l.source === "assigned" ? this._profile(l.role) : l.role;
    const learn = l.source === "entered"
      ? `<input class="cell" data-in-efield="learn" data-in-eid="${esc(l.id)}" data-in-gw="${esc(gw.entry_id)}" value="${esc(l.learn)}" placeholder="${esc(L.learn)}" aria-label="${esc(L.learn)}" autocomplete="off">`
      : `<input class="cell" data-in-learn="${esc(l.key)}" data-in-gw="${esc(gw.entry_id)}" value="${esc(l.learn)}" placeholder="${esc(L.learn)}" aria-label="${esc(L.learn)}" autocomplete="off">`;
    // the newest proof, short: tested or taught in "3 d ago"; both in full as the tooltip
    const full = [l.teach_in ? L.teachIn(new Date(l.teach_in).toLocaleString(lang)) : "", l.tested ? L.tested(new Date(l.tested).toLocaleString(lang)) : ""].filter(Boolean).join(" · ");
    const newest = [l.tested && ["tested", l.tested], l.teach_in && ["taught", l.teach_in]].filter(Boolean).sort((a, b) => b[1].localeCompare(a[1]))[0];
    const ago = newest ? `<span class="isub" title="${esc(full)}">${esc(L.when[newest[0]](t.ago(Math.max(0, Math.round((this._now() - Date.parse(newest[1])) / 1000)))))}</span>` : "";
    const state = l.source === "assigned"
      ? `<span class="tag ${l.status === "confirmed" ? "ok" : l.status === "no_answer" ? "warn" : ""}" title="${esc(L.statusHint[l.status])}">${esc(L.status[l.status])}</span>${ago}`
      : "";
    const device = model.byNote.get(l.to_key)?.key ?? "";
    const actions = `${device && mode === "actuator" && l.source !== "entered" ? `<button class="icon-btn" data-in-goto="${esc(device)}" title="${esc(L.changeAtDevice)}" aria-label="${esc(L.changeAtDevice)}">${svg(ICON.open)}</button>` : ""}${mode === "sender" && device ? `<button class="icon-btn" data-in-goto="${esc(device)}" title="${esc(L.changeAtDevice)}" aria-label="${esc(L.changeAtDevice)}">${svg(ICON.open)}</button>` : ""}${l.source === "entered" ? `<button class="icon-btn" data-in-del="${esc(l.id)}" data-in-gw="${esc(gw.entry_id)}" title="${esc(L.remove)}" aria-label="${esc(L.remove)}">${svg(ICON.close)}</button>` : ""}`;
    return `<div class="lrow">${who}<span class="lcol"><span class="tag role">${esc(role || "–")}</span></span><span class="lcol"><span class="tag src-${l.source}" title="${esc(L.sourceHint[l.source])}">${esc(L.source[l.source])}</span></span>${learn}<div class="lstate">${state}</div><div class="lacts">${actions}</div></div>`;
  },

  _instLinkAddForm(gw, model, key, mode) {
    // adding a link by hand: the other end, the role and where it was taught
    const L = this._t.inst.links;
    if (this._in.linkAdd !== key) return "";
    const known = mode === "actuator"
      ? [...gw.devices.filter((d) => !isActuator(d)).map((d) => `<option value="d|${esc(d.key)}">${esc(d.name)}</option>`), `<option value="other">${esc(L.otherSender)}</option>`]
      : [...model.actuators.map((a) => `<option value="a|${esc(a.key)}">${esc(a.name)}</option>`), `<option value="other">${esc(L.otherTarget)}</option>`];
    return `<div class="ladd" data-in-linkform="${esc(key)}" data-in-gw="${esc(gw.entry_id)}" data-in-linkmode="${mode}"><select data-in-new="other" aria-label="${esc(mode === "actuator" ? L.fromName : L.target)}">${known.join("")}</select><input data-in-new="name" placeholder="${esc(L.nameOrId)}" aria-label="${esc(L.nameOrId)}" hidden><input data-in-new="id" class="mono" placeholder="${esc(L.fromId)}" aria-label="${esc(L.fromId)}" hidden><input data-in-new="role" placeholder="${esc(L.role)}" aria-label="${esc(L.role)}" list="in-roles"><input data-in-new="learn" placeholder="${esc(L.learn)}" aria-label="${esc(L.learn)}"><button class="chip" data-in-act="link-add">${esc(L.add)}</button><button class="chip" data-in-act="link-cancel">${esc(L.cancel)}</button></div><datalist id="in-roles">${L.roles.map((r) => `<option value="${esc(r)}"></option>`).join("")}</datalist>`;
  },

  _instLinkByActuator(gw, model, pass, testable) {
    const L = this._t.inst.links;
    const state = this._in;
    const q = state.q.trim().toLowerCase();
    const worst = (a) => Math.min(3, ...a.links.map((l) => ({ no_answer: 0, unverified: 1, confirmed: 2 })[l.status] ?? 3), a.links.length ? 3 : -1);
    const sorters = { name: (a, b) => a.name.localeCompare(b.name), status: (a, b) => worst(a) - worst(b) || a.name.localeCompare(b.name), count: (a, b) => a.links.length - b.links.length || a.name.localeCompare(b.name) };
    const actuators = model.actuators.filter((a) => !q || [a.name, a.id, a.device?.model, ...a.links.flatMap((l) => [l.from_name, l.from_id, l.role])].join(" ").toLowerCase().includes(q)).sort((a, b) => sorters[state.linkSort](a, b) * state.linkDir);
    const cards = actuators.map((a) => {
      const shown = a.links.filter(pass);
      if (state.linkFilter === "none" ? a.links.length > 0 || !a.device : state.linkFilter !== "all" ? !shown.length : state.linkSource !== "all" && !shown.length) return "";
      const key = `a|${a.key}`;
      const running = state.testing.has(a.key);
      const numbers = a.device ? (gw.numbers?.get(a.device.note_key) ?? []) : [];
      const head = `<div class="lhead"><div><b>${a.device ? `<a data-in-goto="${esc(a.device.key)}">${esc(a.name)}</a>` : esc(a.name)}</b><div class="isub">${esc([a.device?.model, a.id].filter(Boolean).join(" · "))}</div></div>${a.device ? this._instKindTag(a.device) : ""}${numbers.length ? ` <button class="tag" data-in-snd="${esc(gw.entry_id)}|${numbers[0]}">${esc(this._t.inst.senderTag(numbers.join(", ")))}</button>` : ""}<span class="grow"></span><span class="isub">${a.links.length ? L.count(a.links.length) : ""}</span>${testable(a) ? `<button class="chip" data-in-test="${esc(a.device.key)}" data-in-gw="${esc(gw.entry_id)}" ${running ? "disabled" : ""}>${esc(running ? L.testing : L.test)}</button>` : ""}<button class="chip" data-in-linkadd="${esc(key)}">${esc(L.addLink)}</button></div>`;
      const rows = a.links.length ? shown.map((l) => this._instLinkRow(gw, l, model, "actuator")).join("") : `<div class="lnone">${esc(L.noLink)}</div>`;
      return `<div class="lcard" data-k="${a.device ? kindOf(a.device) : "aktor"}">${head}${rows}${this._instLinkAddForm(gw, model, key, "actuator")}</div>`;
    }).filter(Boolean);
    return this._instLinkPage(cards);
  },

  _instLinkPage(cards) {
    // the cards of one gateway, one page at a time
    const t = this._t;
    const state = this._in;
    const L = t.inst.links;
    if (!cards.length) return `<div class="none">${esc(L.none)}</div>`;
    const pages = Math.max(1, Math.ceil(cards.length / state.linkPs));
    state.linkPg = Math.min(state.linkPg, pages - 1);
    const from = state.linkPg * state.linkPs;
    const page = cards.slice(from, from + state.linkPs);
    const sizes = [25, 50, 100].map((n) => `<option${state.linkPs === n ? " selected" : ""}>${n}</option>`).join("");
    const pager = `<div class="spager" style="border:1px solid var(--line);border-radius:12px"><span>${esc(t.inst.sid.range(from + 1, from + page.length, cards.length))}</span><div><label>${esc(t.inst.sid.perPage)} <select data-in-linkps aria-label="${esc(t.inst.sid.perPage)}">${sizes}</select></label><button class="chip" data-in-linkpg="-1"${state.linkPg === 0 ? " disabled" : ""} aria-label="${esc(t.inst.sid.prev)}">‹</button><span>${esc(t.inst.sid.page(state.linkPg + 1, pages))}</span><button class="chip" data-in-linkpg="1"${state.linkPg >= pages - 1 ? " disabled" : ""} aria-label="${esc(t.inst.sid.next2)}">›</button></div></div>`;
    return page.join("") + pager;
  },

  _instLinkBySender(gw, model, pass) {
    const L = this._t.inst.links;
    const state = this._in;
    const wallWithoutDevice = (x) => x.kind === "wall" && !x.device;
    const q = state.q.trim().toLowerCase();
    const senders = model.senders.filter((x) => !q || [x.name, x.id, ...x.links.flatMap((l) => [l.to_name, l.to_id, l.role])].join(" ").toLowerCase().includes(q));
    if (state.linkSort === "count") senders.sort((a, b) => (a.links.length - b.links.length) * state.linkDir);
    else if (state.linkDir < 0) senders.reverse();
    const cards = senders.map((x) => {
      const shown = x.links.filter(pass);
      if (!shown.length) return "";
      const key = `s|${x.key}`;
      const title = x.kind === "ha" ? `${L.from.ha} · ${x.id}` : [x.name, x.id].filter(Boolean).join(" · ");
      const head = `<div class="lhead"><div><b>${x.device ? `<a data-in-goto="${esc(x.device.key)}">${esc(title)}</a>` : esc(title)}</b></div><span class="grow"></span>${wallWithoutDevice(x) || (x.kind === "entered" && !x.device && x.id) ? `<button class="chip" data-in-walldoc="${esc(x.id)}" data-in-gw="${esc(gw.entry_id)}" title="${esc(L.documentHint)}">${esc(L.document)}</button>` : ""}<button class="chip" data-in-linkadd="${esc(key)}">${esc(L.addActuator)}</button></div>`;
      return `<div class="lcard" data-k="${x.device ? kindOf(x.device) : x.kind === "ha" ? "virt" : "taster"}">${head}${shown.map((l) => this._instLinkRow(gw, l, model, "sender")).join("")}${this._instLinkAddForm(gw, model, key, "sender")}</div>`;
    });
    return this._instLinkPage(cards.filter(Boolean));
  },

  _instLinkMatrix(gw, model) {
    const L = this._t.inst.links;
    const senders = model.senders;
    if (!senders.length || !model.actuators.length) return `<div class="none">${esc(L.none)}</div>`;
    const short = (r) => String(r ?? "").replace(/\s+/g, " ").slice(0, 14) || "·";
    const head = `<tr><th></th>${senders.map((x) => `<th>${esc(x.kind === "ha" ? `${L.from.ha} ${String(x.id).slice(-2)}` : x.name || x.id)}</th>`).join("")}</tr>`;
    const rows = model.actuators.map((a) => `<tr><td>${a.device ? `<a data-in-goto="${esc(a.device.key)}">${esc(a.name)}</a>` : esc(a.name)}</td>${senders.map((x) => {
      const l = a.links.find((y) => (y.from_id ? model.plain(y.from_id) : `name|${y.from_name}`) === x.key);
      return `<td>${l ? `<span class="mcell ${l.source}" title="${esc(L.source[l.source])}${l.learn ? ` · ${esc(l.learn)}` : ""}">${esc(short(l.source === "assigned" ? this._profile(l.role) : l.role))}</span>` : `<button class="mplus" data-in-mx data-in-gw="${esc(gw.entry_id)}" data-in-a="${esc(a.key)}" data-in-s="${esc(x.key)}" title="${esc(L.addLink)}">+</button>`}</td>`;
    }).join("")}</tr>`).join("");
    return `<div class="tablewrap"><table class="itable matrix"><thead>${head}</thead><tbody>${rows}</tbody></table></div><p class="isub">${esc(L.matrixHint)}</p>`;
  },

  _instLogRows() {
    // every event of every gateway with the device name split from its detail, newest first
    return gateways(this._in.doc)
      .flatMap((gw) => gw.log.map((e) => {
        const at = (e.detail || "").indexOf(": ");
        const name = at > 0 ? e.detail.slice(0, at) : e.device && at < 0 && e.kind !== "import" ? e.detail : "";
        const rest = at > 0 ? e.detail.slice(at + 2) : e.kind === "import" ? e.detail : "";
        const d = gw.devices.find((x) => e.device && x.note_key === e.device);
        return { ...e, gateway: gw.title, entry_id: gw.entry_id, name, rest, goto: d?.key ?? "", ts: Date.parse(e.time) };
      }))
      .sort((a, b) => b.ts - a.ts);
  },

  _instLogText(e) {
    // what an event says in words: plain text for the search and the CSV, and the same as HTML
    const L = this._t.inst.log;
    const profile = (p) => this._profile(p);
    const parts = [];
    if (e.kind === "sender_test") {
      for (const pair of e.rest.split(", ")) {
        const [p, r = ""] = pair.split("=");
        const key = Object.keys(L.results).find((k) => r.toLowerCase().includes(k)) ?? "";
        parts.push({ text: profile(p), result: key ? L.results[key][0] : r, tone: key ? L.results[key][1] : "neu" });
      }
    } else if (e.kind === "teach_in") parts.push({ text: L.taughtIn(profile(e.profile || e.rest)) });
    else if (e.kind === "sender_assigned") parts.push({ text: L.sender, id: e.rest });
    else if (e.kind === "sender_removed") parts.push({ text: L.sender, id: e.rest, result: L.blocked, tone: "warn" });
    else if (e.kind === "import") {
      const n = e.rest.match(/\d+/g) ?? [];
      parts.push({ text: n.length === 3 ? L.imported(...n) : e.rest });
    } else if (e.rest) parts.push({ text: e.rest });
    return parts;
  },

  _instLog() {
    const t = this._t;
    const L = t.inst.log;
    const v = this._in.log;
    const q = this._in.q.trim().toLowerCase();
    const all = this._instLogRows();
    if (!all.length) return `<div class="none">${esc(t.inst.noLog)}</div>`;
    const now = Date.now();
    const midnight = new Date(now).setHours(0, 0, 0, 0);
    const since = { all: 0, today: midnight, week: midnight - 6 * 864e5 }[v.period];
    const words = (e) => `${t.inst.events[e.kind] || e.kind} ${e.name} ${this._instLogText(e).map((p) => `${p.text} ${p.id ?? ""} ${p.result ?? ""}`).join(" ")}`.toLowerCase();
    const base = all.filter((e) => e.ts >= since && (!q || words(e).includes(q)));
    const kinds = Object.keys(t.inst.events);
    const count = (k) => base.filter((e) => e.kind === k).length;
    const chips = `<button class="chip" data-in-logk="" aria-pressed="${!v.kinds.size}">${esc(L.all)} <b>${base.length}</b></button>${kinds.map((k) => `<button class="chip ev-chip ev-${k}" data-in-logk="${k}" aria-pressed="${v.kinds.has(k)}"${count(k) ? "" : ' style="opacity:.5"'}>${esc(t.inst.events[k])} <b>${count(k)}</b></button>`).join("")}`;
    const period = ["today", "week", "all"].map((p) => `<button data-in-logp="${p}" aria-pressed="${v.period === p}">${esc(L.periods[p])}</button>`).join("");
    const list = base.filter((e) => !v.kinds.size || v.kinds.has(e.kind)).sort((a, b) => (a.ts - b.ts) * -v.dir);
    const pages = Math.max(1, Math.ceil(list.length / v.ps));
    v.pg = Math.min(v.pg, pages - 1);
    const page = list.slice(v.pg * v.ps, (v.pg + 1) * v.ps);
    const lang = this._hass.language;
    const day = (ts) => {
      const diff = Math.round((midnight - new Date(ts).setHours(0, 0, 0, 0)) / 864e5);
      const date = new Date(ts).toLocaleDateString(lang, { weekday: "long", day: "numeric", month: "long" });
      return diff === 0 ? `${L.today} · ${date}` : diff === 1 ? `${L.yesterday} · ${date}` : date;
    };
    const perDay = new Map();
    for (const e of list) perDay.set(day(e.ts), (perDay.get(day(e.ts)) ?? 0) + 1);
    const multi = gateways(this._in.doc).length > 1;
    let last = "";
    const body = page.map((e) => {
      const label = day(e.ts);
      const sep = label === last ? "" : `<tr class="logday"><td colspan="2">${esc(label)} <span class="isub">${perDay.get(label)}</span></td></tr>`;
      last = label;
      const who = e.name ? (e.goto ? `<a data-in-goto="${esc(e.goto)}">${esc(e.name)}</a>` : esc(e.name)) : "";
      const parts = this._instLogText(e).map((p) => `${esc(p.text)}${p.id ? ` ${this._instSndLink(e.entry_id, p.id)}` : ""}${p.result ? ` <span class="lres ${p.tone}">${esc(p.result)}</span>` : ""}`).join(`<span class="isub"> · </span>`);
      const age = Math.max(0, Math.round((now - e.ts) / 1000));
      const when = age < 86400 ? t.ago(age) : new Date(e.ts).toLocaleTimeString(lang, { hour: "2-digit", minute: "2-digit" });
      return `${sep}<tr><td class="logmain"><div class="logline"><span class="tag ev ev-${esc(e.kind)}">${esc(t.inst.events[e.kind] || e.kind)}</span>${who}${multi ? ` <span class="isub">${esc(e.gateway)}</span>` : ""}</div>${parts ? `<div class="logdetail">${parts}</div>` : ""}</td><td class="logwhen" title="${esc(new Date(e.ts).toLocaleString(lang))}">${esc(when)}</td></tr>`;
    }).join("");
    const from = list.length ? v.pg * v.ps + 1 : 0;
    const sizes = [25, 50, 100].map((n) => `<option${v.ps === n ? " selected" : ""}>${n}</option>`).join("");
    const pager = `<div class="spager"><span>${esc(t.inst.sid.range(from, from + page.length - (list.length ? 1 : 0), list.length))}</span><div><label>${esc(t.inst.sid.perPage)} <select data-in-logps aria-label="${esc(t.inst.sid.perPage)}">${sizes}</select></label><button class="chip" data-in-logpg="-1"${v.pg === 0 ? " disabled" : ""} aria-label="${esc(t.inst.sid.prev)}">‹</button><span>${esc(t.inst.sid.page(v.pg + 1, pages))}</span><button class="chip" data-in-logpg="1"${v.pg >= pages - 1 ? " disabled" : ""} aria-label="${esc(t.inst.sid.next2)}">›</button></div></div>`;
    const search = `<input class="isearch" data-in-search value="${esc(this._in.q)}" placeholder="${esc(L.search)}" aria-label="${esc(L.search)}">`;
    const empty = `<tr><td colspan="2" class="none">${esc(L.none)}</td></tr>`;
    return `<div class="itools" style="align-items:center">${search}<span class="seg" role="group">${period}</span><span style="flex:1"></span><button class="chip" data-in-act="log-csv">${svg(ICON.download)}${esc(L.csv)}</button></div><div class="chips" style="margin-bottom:10px">${chips}</div><div class="swrap"><div class="logbar"><span>${esc(L.count(list.length, all.length))}</span><button data-in-logsort="1">${esc(t.time)} ${v.dir < 0 ? "↓" : "↑"} ${esc(v.dir < 0 ? L.newest : L.oldest)}</button></div><div class="tablewrap"><table class="itable log"><tbody>${body || empty}</tbody></table></div>${pager}</div>`;
  },

  _installationClick(e) {
    const state = this._in;
    const back = e.target.closest("[data-in-back]");
    if (back) {
      // back to where the last jump came from
      const from = state.back;
      state.back = null;
      if (from) {
        Object.assign(state, { tab: from.tab, view: from.view, art: from.art, q: from.q, linkView: from.linkView });
        Object.assign(state.bus, { sub: from.sub, drawer: from.drawer, history: [] });
      }
      this._renderInstallation();
      return;
    }
    // a jump to another place of the installation keeps where it came from, for Back
    if (e.target.closest("[data-in-goto], [data-in-snd], [data-in-kind], [data-in-busgo], [data-in-sndlinks], [data-in-rowdevices]")) {
      state.back = { tab: state.tab, view: state.view, art: state.art, q: state.q, linkView: state.linkView, sub: state.bus.sub, drawer: state.bus.drawer };
    }
    const busgo = e.target.closest("[data-in-busgo]");
    if (busgo) {
      // a device, supply or row on the bus: its channel, module or row in the bus tab
      const [type, ...rest] = busgo.dataset.inBusgo.split("|");
      Object.assign(state, { tab: "devices", view: "bus" });
      if (type === "row") {
        this._renderInstallation();
        this._bvGo("row", rest.join("|"));
      } else {
        Object.assign(state.bus, { sub: "list", drawer: { type, id: rest.join("|") }, history: [] });
        this._renderInstallation();
      }
      return;
    }
    const rowdevices = e.target.closest("[data-in-rowdevices]");
    if (rowdevices) {
      // a row of a cabinet: its devices in the devices table, grouped by place
      Object.assign(state, { tab: "devices", view: "all", art: "all", group: "location", q: rowdevices.dataset.inRowdevices });
      this._renderInstallation();
      return;
    }
    const gwopen = e.target.closest("[data-in-gwopen]");
    if (gwopen) {
      // a gateway: its card in the telegram view, opened
      this._gatewayDetails?.add(gwopen.dataset.inGwopen);
      this._setView("telegrams");
      return;
    }
    const sndlinks = e.target.closest("[data-in-sndlinks]");
    if (sndlinks) {
      // a sender ID: the links it is in, by sender
      Object.assign(state, { tab: "links", linkView: "sender", q: sndlinks.dataset.inSndlinks, linkFilter: "all", linkSource: "all", linkPg: 0 });
      this._renderInstallation();
      return;
    }
    if (this._busClick(e)) return;
    if (state.colMenu && !e.target.closest(".colmenu")) {
      state.colMenu = false;
      this.shadowRoot.querySelector("#installation details.colmenu")?.removeAttribute("open");
    }
    const device = e.target.closest("[data-in-device]");
    if (device) {
      this._showDevice(device.dataset.inDevice);
      return;
    }
    const sidf = e.target.closest("[data-in-sidf]");
    const sidfn = e.target.closest("[data-in-sidfn]");
    const sids = e.target.closest("[data-in-sids]");
    const sidpg = e.target.closest("[data-in-sidpg]");
    if (sidf || sidfn || sids || sidpg) {
      const [gw, arg] = (sidf || sidfn || sids || sidpg).dataset[sidf ? "inSidf" : sidfn ? "inSidfn" : sids ? "inSids" : "inSidpg"].split("|");
      const v = state.sid[gw];
      if (!v) return;
      if (sidf) Object.assign(v, { f: arg, pg: 0 });
      else if (sidfn) Object.assign(v, { fn: v.fn === arg ? "" : arg, pg: 0 });
      else if (sids) Object.assign(v, v.sort === arg ? { dir: -v.dir } : { sort: arg, dir: 1 });
      else v.pg = Math.max(0, v.pg + Number(arg));
      this._renderInstallation();
      return;
    }
    const logk = e.target.closest("[data-in-logk]");
    const logp = e.target.closest("[data-in-logp]");
    const logsort = e.target.closest("[data-in-logsort]");
    const logpg = e.target.closest("[data-in-logpg]");
    if (logk || logp || logsort || logpg) {
      const v = state.log;
      if (logk) {
        const k = logk.dataset.inLogk;
        if (!k) v.kinds.clear();
        else if (v.kinds.has(k)) v.kinds.delete(k);
        else v.kinds.add(k);
        v.pg = 0;
      } else if (logp) Object.assign(v, { period: logp.dataset.inLogp, pg: 0 });
      else if (logsort) v.dir = -v.dir;
      else v.pg = Math.max(0, v.pg + Number(logpg.dataset.inLogpg));
      this._renderInstallation();
      return;
    }
    const tab = e.target.closest("[data-in-tab]");
    if (tab) {
      state.tab = tab.dataset.inTab;
      this._renderInstallation();
      if (this._managing()) this._loadPools();
      return;
    }
    const view = e.target.closest("[data-in-view]");
    if (view) {
      state.view = view.dataset.inView;
      state.art = "all";
      state.selected.clear();
      this._renderInstallation();
      return;
    }
    const art = e.target.closest("[data-in-art]");
    if (art) {
      state.art = art.dataset.inArt;
      this._renderInstallation();
      return;
    }
    const miss = e.target.closest("[data-in-miss]");
    if (miss) {
      state.miss[miss.dataset.inMiss] = !state.miss[miss.dataset.inMiss];
      this._renderInstallation();
      return;
    }
    const kind = e.target.closest("[data-in-kind]");
    if (kind) {
      // a kind tag opens the view that belongs to it
      state.tab = "devices";
      state.view = VIEW_OF[kind.dataset.inKind] ?? "all";
      state.art = "all";
      this._renderInstallation();
      return;
    }
    const snd = e.target.closest("[data-in-snd]");
    if (snd) {
      // the sender number of a device: its row in the Sender IDs tab
      state.tab = "gwsenders";
      state.hl = `snd|${snd.dataset.inSnd}`;
      this._renderInstallation();
      if (this._managing()) this._loadPools();
      return;
    }
    const goto = e.target.closest("[data-in-goto]");
    if (goto) {
      // a link's device opens in the Devices view; without a row there, the table of the Installation marks it
      if (this._inPanel(goto.dataset.inGoto)) {
        this._showDevice(goto.dataset.inGoto);
        return;
      }
      state.tab = "devices";
      state.view = "all";
      state.art = "all";
      state.q = "";
      state.hl = goto.dataset.inGoto;
      this._renderInstallation();
      return;
    }
    for (const menu of this.shadowRoot.querySelectorAll("#installation details.supplymenu[open], #installation details.kindmenu[open], #installation details.rowmenu[open]")) if (!menu.contains(e.target)) menu.removeAttribute("open");
    const nameEdit = e.target.closest("[data-in-nameedit]");
    if (nameEdit) {
      state.nameEdit = nameEdit.dataset.inNameedit;
      this._renderInstallation();
      this.shadowRoot.querySelector("#installation [data-in-focus]")?.focus();
      return;
    }
    const mkindSet = e.target.closest("[data-in-mkind]");
    if (mkindSet) {
      const [entryId, mid, kind] = mkindSet.dataset.inMkind.split("|");
      const gw = gateways(state.doc).find((g) => g.entry_id === entryId);
      const entry = gw?.manual.find((x) => x.id === mid);
      if (entry) {
        entry.kind = kind;
        this._renderInstallation();
        this._instSaveManual(gw);
      }
      return;
    }
    const mact = e.target.closest("[data-in-mact]");
    if (mact) {
      const [act, entryId, mid] = mact.dataset.inMact.split("|");
      const gw = gateways(state.doc).find((g) => g.entry_id === entryId);
      const entry = gw?.manual.find((x) => x.id === mid);
      if (!entry) return;
      if (act === "device") this._addDevice(entry.address);
      else {
        gw.manual = gw.manual.filter((x) => x.id !== mid);
        this._renderInstallation();
        this._instSaveManual(gw);
      }
      return;
    }
    const supplyAdd = e.target.closest("[data-in-supply-add]");
    if (supplyAdd) {
      const gw = gateways(state.doc).find((g) => g.entry_id === supplyAdd.dataset.inSupplyAdd);
      if (!gw) return;
      const preset = SUPPLY_PRESETS[supplyAdd.dataset.inPreset];
      gw.supplies = [...gw.supplies, { ...SUPPLY_BLANK, ...preset, id: Math.random().toString(36).slice(2, 10) }];
      this._renderInstallation();
      if (preset) this._instSaveSupplies(gw);
      [...this.shadowRoot.querySelectorAll(`#installation [data-in-sfield="${preset ? "first" : "name"}"]`)].pop()?.focus();
      return;
    }
    const supplyDel = e.target.closest("[data-in-supply-del]");
    if (supplyDel) {
      const gw = gateways(state.doc).find((g) => g.entry_id === supplyDel.dataset.inGw);
      if (!gw) return;
      gw.supplies = gw.supplies.filter((x) => x.id !== supplyDel.dataset.inSupplyDel);
      this._renderInstallation();
      this._instSaveSupplies(gw);
      return;
    }
    const fold = e.target.closest("[data-in-fold]");
    if (fold) {
      const id = fold.dataset.inFold;
      if (state.folded.has(id)) state.folded.delete(id);
      else state.folded.add(id);
      this._renderInstallation();
      return;
    }
    const free = e.target.closest("[data-in-free]");
    if (free) {
      // the release is confirmed in the pool above the table, next to its map
      const plain = (id) => id.replaceAll("-", "").toUpperCase(); // the table writes IDs without dashes
      let row = null;
      const pool = this._pools.find((p) => (row = p.rows.find((r) => plain(r.id) === plain(free.dataset.inFree))));
      if (!pool) return;
      this._pool = pool.id;
      this._freeing = { id: row.id, device: row.device || row.ref || "" };
      state.poolOpen = true;
      this._setManage();
      this._renderSenderIds();
      this.shadowRoot.querySelector("#senders .confirm")?.scrollIntoView({ block: "center", behavior: "smooth" });
      return;
    }
    const linkView = e.target.closest("[data-in-linkview]");
    if (linkView) {
      state.linkView = linkView.dataset.inLinkview;
      state.linkAdd = "";
      this._renderInstallation();
      return;
    }
    const devMore = e.target.closest("[data-in-devsort], [data-in-devpg], [data-in-placeedit]");
    if (devMore) {
      const d = devMore.dataset;
      if (d.inDevsort) Object.assign(state, state.devSort === d.inDevsort ? { devDir: -state.devDir } : { devSort: d.inDevsort, devDir: 1 });
      else if (d.inDevpg) {
        const [gw, step] = d.inDevpg.split("|");
        state.devPg[gw] = Math.max(0, (state.devPg[gw] ?? 0) + Number(step));
      } else state.placeEdit = d.inPlaceedit;
      this._renderInstallation();
      this.shadowRoot.querySelector("#installation [data-in-focus]")?.focus();
      return;
    }
    const linkMore = e.target.closest("[data-in-linksort], [data-in-linklearn], [data-in-linkreset], [data-in-linkpg]");
    if (linkMore) {
      const d = linkMore.dataset;
      if (d.inLinksort) Object.assign(state, state.linkSort === d.inLinksort ? { linkDir: -state.linkDir } : { linkSort: d.inLinksort, linkDir: 1 });
      else if (d.inLinklearn) state.linkLearn = !state.linkLearn;
      else if (d.inLinkreset) Object.assign(state, { linkFilter: "all", linkSource: "all", q: "" });
      else state.linkPg = Math.max(0, state.linkPg + Number(d.inLinkpg));
      this._renderInstallation();
      return;
    }
    const linkFilter = e.target.closest("[data-in-linkfilter]");
    if (linkFilter) {
      state.linkFilter = state.linkFilter === linkFilter.dataset.inLinkfilter ? "all" : linkFilter.dataset.inLinkfilter;
      state.linkPg = 0;
      this._renderInstallation();
      return;
    }
    const linkSource = e.target.closest("[data-in-linksource]");
    if (linkSource) {
      state.linkSource = linkSource.dataset.inLinksource;
      this._renderInstallation();
      return;
    }
    const linkAdd = e.target.closest("[data-in-linkadd]");
    if (linkAdd) {
      state.linkAdd = state.linkAdd === linkAdd.dataset.inLinkadd ? "" : linkAdd.dataset.inLinkadd;
      this._renderInstallation();
      return;
    }
    const test = e.target.closest("[data-in-test]");
    if (test) {
      this._instTest(test.dataset.inGw, test.dataset.inTest);
      return;
    }
    const wallDoc = e.target.closest("[data-in-walldoc]");
    if (wallDoc) {
      this._instDocumentId(wallDoc.dataset.inGw, wallDoc.dataset.inWalldoc);
      return;
    }
    const matrixCell = e.target.closest("[data-in-mx]");
    if (matrixCell) {
      this._instMatrixAdd(matrixCell.dataset.inGw, matrixCell.dataset.inA, matrixCell.dataset.inS);
      return;
    }
    const del = e.target.closest("[data-in-del]");
    if (del) {
      this._instRemoveLink(del.dataset.inGw, del.dataset.inDel);
      return;
    }
    const funkcol = e.target.closest("[data-in-funkcol]");
    if (funkcol) {
      const name = funkcol.dataset.inFunkcol;
      state.colMenu = true;
      if (state.funkCols.has(name)) state.funkCols.delete(name);
      else state.funkCols.add(name);
      this._renderInstallation();
      return;
    }
    const column = e.target.closest("[data-in-col], [data-in-colgroup]");
    if (column) {
      // a single column, or all / none of a group
      state.colMenu = true;
      if (column.dataset.inCol) {
        const name = column.dataset.inCol;
        if (state.columns.has(name)) state.columns.delete(name);
        else state.columns.add(name);
      } else {
        const [group, how] = column.dataset.inColgroup.split("|");
        for (const f of COLUMN_GROUPS[group] ?? []) {
          if (how === "all") state.columns.add(f);
          else state.columns.delete(f);
        }
      }
      saveColumns(state.columns);
      this._renderInstallation();
      return;
    }
    const clear = e.target.closest("[data-in-placeclear]");
    if (clear) {
      // ✕ in a place cell: cabinet, row and slot are cleared and saved
      const box = clear.closest("[data-in-place]");
      box.querySelectorAll("input").forEach((i) => (i.value = ""));
      const select = box.querySelector("[data-in-prow]");
      if (select) select.value = "";
      state.placeEdit = "";
      state.placeText.delete(box.dataset.inKey || box.dataset.inSid || box.dataset.inMid);
      this.shadowRoot.activeElement?.blur?.(); // the cell is drawn anew: nothing in it keeps the focus
      this._instSavePlace(box).then(() => this._renderInstallation());
      return;
    }
    const act = e.target.closest("[data-in-act]")?.dataset.inAct;
    if (!act) return;
    this.shadowRoot.querySelector("#installation details.imenu")?.removeAttribute("open");
    if (act === "print") this._documentation("print");
    else if (act === "copy-id") navigator.clipboard?.writeText(e.target.closest("[data-in-act]").dataset.id.replace(/(..)(?=.)/g, "$1-")).catch(() => {});
    else if (act === "log-csv") {
      const L = this._t.inst.log;
      const q = (x) => `"${String(x).replace(/"/g, '""')}"`;
      const rows = this._instLogRows().map((e) => [e.time, this._t.inst.events[e.kind] || e.kind, e.name, this._instLogText(e).map((p) => [p.text, p.id, p.result].filter(Boolean).join(" ")).join(", ")].map(q).join(";"));
      const a = document.createElement("a");
      a.href = URL.createObjectURL(new Blob(["\ufeff" + [[this._t.time, this._t.inst.event, this._t.inst.device, this._t.inst.detail].map(q).join(";"), ...rows].join("\n")], { type: "text/csv" }));
      a.download = L.file;
      a.click();
    } else if (act === "csv") this._documentation("csv");
    else if (act === "csv-links") this._documentation("csv-links");
    else if (act === "csv-tables") this._documentation("csv-tables");
    else if (act === "json") this._documentation("json");
    else if (act === "import") this.shadowRoot.getElementById("docFile").click();
    else if (act === "unpick") {
      state.selected.clear();
      this._renderInstallation();
    } else if (act === "bulk") this._instBulk();
    else if (act === "sheet") {
      state.sheet = !state.sheet;
      this._renderInstallation();
    } else if (act === "paste") this._instPaste();
    else if (act === "copy-table") this._instCopyTable();
    else if (act === "doc-open") {
      state.docForm = true;
      state.docError = "";
      state.docDraft = { kind: "taster" };
      this._renderInstallation();
      this.shadowRoot.querySelector('#installation [data-in-doc-field="name"]')?.focus();
    } else if (act === "doc-cancel") {
      state.docForm = false;
      state.docDraft = {};
      this._renderInstallation();
    } else if (act === "doc-add") this._instDocAdd();
    else if (act === "next-open") {
      // the devices without a place, the cursor in the first one
      state.view = "all";
      state.art = "all";
      state.miss.loc = true;
      this._renderInstallation();
      this.shadowRoot.querySelector("#installation .place input")?.focus();
    }
    else if (act === "link-add") this._instLinkAdd(e.target.closest("[data-in-linkform]"));
    else if (act === "link-cancel") {
      state.linkAdd = "";
      this._renderInstallation();
    }
  },

  _installationChange(e) {
    if (this._busInput(e)) return;
    if (e.target.matches("select[data-in-doc-field]")) {
      // the kind decides which fields the form has: redraw, the draft keeps what was typed
      this._in.docDraft[e.target.dataset.inDocField] = e.target.value;
      if (e.target.dataset.inDocField === "kind") this._renderInstallation();
      return;
    }
    const other = e.target.closest('select[data-in-new="other"]');
    if (other) {
      const form = other.closest("[data-in-linkform]");
      const free = other.value === "other";
      form.querySelector('[data-in-new="name"]').hidden = !free;
      form.querySelector('[data-in-new="id"]').hidden = !free || form.dataset.inLinkmode === "sender";
      return;
    }
    const devps = e.target.closest("[data-in-devps]");
    if (devps) {
      Object.assign(this._in, { devPs: Number(devps.value), devPg: {} });
      this._renderInstallation();
      return;
    }
    const linkps = e.target.closest("[data-in-linkps]");
    if (linkps) {
      Object.assign(this._in, { linkPs: Number(linkps.value), linkPg: 0 });
      this._renderInstallation();
      return;
    }
    const logps = e.target.closest("[data-in-logps]");
    if (logps) {
      Object.assign(this._in.log, { ps: Number(logps.value), pg: 0 });
      this._renderInstallation();
      return;
    }
    const sidps = e.target.closest("[data-in-sidps]");
    if (sidps && this._in.sid[sidps.dataset.inSidps]) {
      Object.assign(this._in.sid[sidps.dataset.inSidps], { ps: Number(sidps.value), pg: 0 });
      this._renderInstallation();
      return;
    }
    const prow = e.target.closest("select[data-in-prow]");
    if (prow) {
      const box = prow.closest("[data-in-place]");
      const id = box.dataset.inKey || box.dataset.inSid || box.dataset.inMid;
      if (prow.value === "__text") {
        // free text for a place that is no documented cabinet
        this._in.placeText.add(id);
        this._in.placeEdit = id;
        this._renderInstallation();
        this.shadowRoot.querySelector("#installation [data-in-focus]")?.focus();
      } else if (prow.value === "__new") this._instPlaceCabinet(box);
      else this._instSavePlace(box);
      return;
    }
    const groupsel = e.target.closest("[data-in-groupsel]");
    if (groupsel) {
      this._in.group = groupsel.value;
      saveGroup(groupsel.value);
      this._renderInstallation();
      return;
    }
    const pick = e.target.closest("[data-in-pick]");
    if (!pick) return;
    const selected = this._in.selected;
    if (pick.checked) selected.add(pick.dataset.inPick);
    else selected.delete(pick.dataset.inPick);
    this._renderInstallation();
  },

  _installationInput(e) {
    const state = this._in;
    if (e.target.closest?.("[data-bv-form], [data-bv-busform]")) state.bus.dirty = true;
    if (e.target.matches("[data-in-paste]")) {
      state.paste = e.target.value;
      state.pasteResult = "";
      const info = this.shadowRoot.querySelector("#installation [data-in-paste-info]");
      if (info) info.textContent = this._instPasteSeen();
      return;
    }
    if (e.target.matches("[data-in-search]")) {
      state.q = e.target.value;
      clearTimeout(this._inSearch);
      this._inSearch = setTimeout(() => {
        this._renderInstallation();
        this.shadowRoot.querySelector("[data-in-search]")?.focus();
      }, 250);
      return;
    }
    if (e.target.matches("[data-in-doc-field]")) {
      state.docDraft[e.target.dataset.inDocField] = e.target.value;
      return;
    }
    const sfield = e.target.closest("[data-in-sfield]");
    if (sfield) {
      this._instSupplyInput(sfield);
      return;
    }
    const mfield = e.target.closest("[data-in-mfield]");
    if (mfield) {
      this._instManualInput(mfield);
      return;
    }
    const part = e.target.closest("[data-in-part]");
    if (part) {
      const box = part.closest("[data-in-place]");
      box.classList.toggle("blank", ![...box.querySelectorAll("input")].some((i) => i.value.trim()));
      clearTimeout(box._saving);
      box._saving = setTimeout(() => this._instSavePlace(box), SAVE_DELAY);
      return;
    }
    const learn = e.target.closest("[data-in-learn], [data-in-efield]");
    if (learn) {
      clearTimeout(learn._saving);
      learn._saving = setTimeout(() => this._instSaveLink(learn), SAVE_DELAY);
      return;
    }
    const cell = e.target.closest("[data-in-field]");
    if (!cell) return;
    cell.classList.remove("bad");
    cell.nextElementSibling?.matches(".cerr") && cell.nextElementSibling.remove();
    clearTimeout(cell._saving);
    const problem = this._instProblem(cell.dataset.inField, cell.value);
    if (problem) {
      this._instMark(cell, this._t.inst.errors[problem]);
      return; // nothing goes to the server while the value is wrong
    }
    cell._saving = setTimeout(() => this._instSaveCell(cell), SAVE_DELAY);
  },

  _instDevice(entryId, key) {
    return gateways(this._in.doc).find((g) => g.entry_id === entryId)?.devices.find((d) => d.key === key);
  },

  _instProblem(field, value) {
    // a value the server would refuse, caught while typing; "" is always fine (it clears the field)
    const text = value.trim();
    if (!text) return "";
    if (field === "bus_address" && !(/^\d{1,3}$/.test(text) && Number(text) >= 1 && Number(text) <= 126)) return "bus_address";
    if (field === "bus_power" && !/^\d{1,4}([.,]\d{1,3})?$/.test(text)) return "bus_power";
    return "";
  },

  _instMark(cell, message) {
    cell.classList.add("bad");
    if (!cell.nextElementSibling?.matches(".cerr")) cell.insertAdjacentHTML("afterend", `<div class="cerr" role="alert">${esc(message)}</div>`);
  },

  async _instSaveCell(cell) {
    const { inGw: entryId, inKey: key, inField: field } = cell.dataset;
    const device = this._instDevice(entryId, key);
    if (!device || device[field] === cell.value) return;
    const reply = await this._instSend(entryId, [{ device: key, values: { [field]: cell.value } }]);
    if (reply?.saved) {
      device[field] = cell.value;
      // the same field of the same device in another row of a table (a device with several senders)
      this.shadowRoot.querySelectorAll(`#installation [data-in-gw="${CSS.escape(entryId)}"][data-in-key="${CSS.escape(key)}"][data-in-field="${field}"]`).forEach((other) => {
        if (other !== cell && other.value !== cell.value) other.value = cell.value;
      });
    } else this._instMark(cell, this._t.inst.errors.refused); // refused: a date that is none, or the device is gone
  },

  async _instSavePlace(box) {
    // the three parts of a place go to the server as one text, "cabinet · row · slot"
    const { inGw: entryId, inKey: key, inSid: sid, inMid: mid } = box.dataset;
    const value = this._instPlaceValue(box);
    if (mid) {
      // an entry written by hand keeps its place in its own list
      const gw = gateways(this._in.doc).find((g) => g.entry_id === entryId);
      const entry = gw?.manual.find((x) => x.id === mid);
      if (!entry || entry.location === value) return;
      entry.location = value;
      if (await this._instSaveManual(gw)) {
        const bar = this.shadowRoot.querySelector("#installation .progress");
        if (bar) bar.outerHTML = this._instProgress();
      } else box.classList.add("bad");
      return;
    }
    if (sid) {
      // a power supply keeps its place in its own list
      const gw = gateways(this._in.doc).find((g) => g.entry_id === entryId);
      const supply = gw?.supplies.find((x) => x.id === sid);
      if (!supply || supply.location === value) return;
      supply.location = value;
      if (await this._instSaveSupplies(gw)) {
        const bar = this.shadowRoot.querySelector("#installation .progress");
        if (bar) bar.outerHTML = this._instProgress();
      } else box.classList.add("bad");
      return;
    }
    const device = this._instDevice(entryId, key);
    if (!device || (device.location ?? "") === value) return;
    const reply = await this._instSend(entryId, [{ device: key, values: { location: value } }]);
    if (!reply?.saved) {
      box.classList.add("bad");
      return;
    }
    device.location = value;
    box.classList.remove("bad");
    // the progress follows; the rows stay as they are, so the cursor stays where it is
    const bar = this.shadowRoot.querySelector("#installation .progress");
    if (bar) bar.outerHTML = this._instProgress();
  },

  _instManualInput(input) {
    // a field of an entry written by hand: checked while typing, the whole list goes to the server after a pause
    const gw = gateways(this._in.doc).find((g) => g.entry_id === input.dataset.inGw);
    const entry = gw?.manual.find((x) => x.id === input.dataset.inMid);
    if (!entry) return;
    const field = input.dataset.inMfield;
    entry[field] = input.value;
    const text = input.value.trim();
    const bad = (field === "bus_address" && text !== "" && !(/^\d{1,3}$/.test(text) && Number(text) >= 1 && Number(text) <= 126)) || (field === "bus_power" && text !== "" && !/^\d{1,4}([.,]\d{1,3})?$/.test(text));
    input.classList.toggle("bad", bad);
    clearTimeout(gw._manualSaving);
    if (!this.shadowRoot.querySelector("#installation [data-in-mfield].bad")) gw._manualSaving = setTimeout(() => this._instSaveManual(gw), SAVE_DELAY);
  },

  async _instSaveManual(gw) {
    const entries = gw.manual.map(({ bus_power_table, ...entry }) => entry);
    try {
      await this._hass.callWS({ type: "enocean_eltako/set_manual", entry_id: gw.entry_id, entries });
    } catch (err) {
      this._notice(this._t.doc.noteFailed);
      return false;
    }
    const status = this._gateways.find((g) => g.entry_id === gw.entry_id);
    if (status) status.manual = entries.map((x) => ({ ...x }));
    return true;
  },

  async _instDocAdd() {
    // an entry written by hand from the form: what it is, where it sits, what feeds it
    const state = this._in;
    const draft = state.docDraft;
    for (const input of this.shadowRoot.querySelectorAll("#installation .docform [data-in-doc-field]")) draft[input.dataset.inDocField] = input.value; // autofill fires no input event
    const get = (name) => String(draft[name] ?? "").trim();
    const gw = gateways(state.doc).find((g) => g.entry_id === draft.gateway) ?? gateways(state.doc)[0];
    const plain = get("address").replaceAll("-", "").toUpperCase();
    state.docError = "";
    if (!get("name")) state.docError = this._t.inst.funk.needName;
    else if (!/^[0-9A-F]{8}$/.test(plain)) state.docError = this._t.inst.funk.badId;
    else if (gw.manual.some((m) => m.address.replaceAll("-", "").toUpperCase() === plain)) state.docError = this._t.inst.funk.known;
    else if (get("installed") && !/^\d{4}-\d{2}-\d{2}$/.test(get("installed"))) state.docError = this._t.inst.funk.badDate;
    if (state.docError) {
      this._renderInstallation();
      return;
    }
    const kind = get("kind") || "taster";
    const fused = ["bus", "aktor"].includes(kind);
    const id = Math.random().toString(36).slice(2, 10);
    gw.manual = [...gw.manual, {
      id, name: get("name"), address: plain.match(/../g).join("-"), function: get("function"), bus_address: "", feedback_id: "", bus_power: "", kind,
      location: joinPlace([get("loc0"), get("loc1"), get("loc2")]), power: get("power"), circuit: fused ? get("circuit") : "", fuse: fused ? get("fuse") : "", installed: get("installed"), model: get("model"),
    }];
    state.docForm = false;
    state.docDraft = {};
    state.hl = `manual|${id}`;
    this._renderInstallation();
    this._instSaveManual(gw);
  },

  _instSupplyInput(input) {
    // a field of a power supply: checked while typing, the whole list goes to the server after a pause
    const gw = gateways(this._in.doc).find((g) => g.entry_id === input.dataset.inGw);
    const supply = gw?.supplies.find((x) => x.id === input.dataset.inSid);
    if (!supply) return;
    const field = input.dataset.inSfield;
    supply[field] = input.value;
    const text = input.value.trim();
    const badAddress = (v) => v !== "" && !(/^\d{1,3}$/.test(v) && Number(v) >= 1 && Number(v) <= 126);
    const bad = (field === "watts" && text !== "" && !/^\d{1,4}([.,]\d{1,3})?$/.test(text)) || (["first", "last"].includes(field) && badAddress(text));
    input.classList.toggle("bad", bad);
    // first after last: both are marked
    const row = input.closest(".psurow");
    if (row && ["first", "last"].includes(field)) {
      const order = supply.first !== "" && supply.last !== "" && Number(supply.first) > Number(supply.last);
      row.querySelectorAll('[data-in-sfield="first"], [data-in-sfield="last"]').forEach((i) => i.classList.toggle("bad", order || badAddress(i.value.trim())));
    }
    clearTimeout(gw._supplySaving);
    if (!this.shadowRoot.querySelector("#installation [data-in-sfield].bad")) gw._supplySaving = setTimeout(() => this._instSaveSupplies(gw, input), SAVE_DELAY);
  },

  async _instSaveSupplies(gw, input = null) {
    try {
      await this._hass.callWS({ type: "enocean_eltako/set_supplies", entry_id: gw.entry_id, supplies: gw.supplies });
    } catch (err) {
      this._notice(this._t.doc.noteFailed);
      input?.classList.add("bad");
      return false;
    }
    const status = this._gateways.find((g) => g.entry_id === gw.entry_id);
    if (status) status.supplies = gw.supplies.map((x) => ({ ...x }));
    if (input && ["watts", "first", "last"].includes(input.dataset.inSfield)) {
      // the load bars follow; the cursor stays in the field
      const selector = `[data-in-sfield="${input.dataset.inSfield}"][data-in-sid="${CSS.escape(input.dataset.inSid)}"]`;
      this._renderInstallation();
      const again = this.shadowRoot.querySelector(`#installation ${selector}`);
      if (again) {
        again.focus();
        again.setSelectionRange(again.value.length, again.value.length);
      }
    }
    return true;
  },

  async _instSend(entryId, items) {
    try {
      return await this._hass.callWS({ type: "enocean_eltako/set_fields", entry_id: entryId, items });
    } catch (err) {
      this._notice(this._t.doc.noteFailed);
      return null;
    }
  },

  _instEntered(gw) {
    // the links entered by hand, in the shape the server stores them
    return gw.links
      .filter((l) => l.source === "entered")
      .map((l) => ({ id: l.id, from_id: l.from_id, from_name: l.from_name, to_key: l.to_key, to_name: l.to_key ? "" : l.to_name, role: l.role, learn: l.learn }));
  },

  async _instSetLinks(gw, entered) {
    try {
      await this._hass.callWS({ type: "enocean_eltako/set_links", entry_id: gw.entry_id, links: entered });
    } catch (err) {
      this._notice(this._t.doc.noteFailed);
      return false;
    }
    return true;
  },

  async _instSaveLink(field) {
    // a learn position of a derived link, or a field of a link entered by hand
    const gw = gateways(this._in.doc).find((g) => g.entry_id === field.dataset.inGw);
    if (!gw) return;
    if (field.dataset.inLearn) {
      const link = gw.links.find((l) => l.key === field.dataset.inLearn);
      try {
        await this._hass.callWS({ type: "enocean_eltako/set_link_learn", entry_id: gw.entry_id, link_key: field.dataset.inLearn, learn: field.value });
        if (link) link.learn = field.value;
      } catch (err) {
        field.classList.add("bad");
      }
      return;
    }
    const link = gw.links.find((l) => l.id === field.dataset.inEid);
    if (!link) return;
    link[field.dataset.inEfield] = field.value;
    if (!(await this._instSetLinks(gw, this._instEntered(gw)))) field.classList.add("bad");
  },

  async _instLinkAdd(form) {
    // a link written down: from a known device or an ID, to an actuator, with its role and learn position
    const state = this._in;
    const gw = gateways(state.doc).find((g) => g.entry_id === form.dataset.inGw);
    if (!gw) return;
    const get = (name) => form.querySelector(`[data-in-new="${name}"]`).value.trim();
    const [side, ref] = get("other").split("|");
    const mode = form.dataset.inLinkmode;
    const link = { id: Math.random().toString(36).slice(2, 10), from_id: "", from_name: "", to_key: "", to_name: "", role: get("role"), learn: get("learn") };
    const fixed = form.dataset.inLinkform.slice(2);
    if (mode === "actuator") {
      // the actuator is the card; the other end is chosen
      if (fixed.startsWith("name|")) link.to_name = fixed.slice(5);
      else link.to_key = fixed;
      if (side === "d") {
        const d = gw.devices.find((x) => x.key === ref);
        Object.assign(link, { from_id: d?.id ?? "", from_name: d?.name ?? "" });
      } else Object.assign(link, { from_id: get("id"), from_name: get("name") });
    } else {
      // the sender is the card; the actuator is chosen
      const sender = this._instLinkModel(gw).senders.find((x) => x.key === fixed);
      Object.assign(link, { from_id: sender?.id ?? "", from_name: sender?.name ?? "" });
      if (side === "a" && !ref.startsWith("name|")) link.to_key = ref;
      else if (side === "a") link.to_name = ref.slice(5);
      else link.to_name = get("name");
    }
    if (!(link.from_id || link.from_name) || !(link.to_key || link.to_name)) {
      this._notice(this._t.inst.links.incomplete);
      return;
    }
    state.linkAdd = "";
    if (await this._instSetLinks(gw, [...this._instEntered(gw), link])) await this._loadInstallation();
  },

  async _instMatrixAdd(entryId, actuatorKey, senderKey) {
    // a + in the matrix: a link with no role yet, written down at once
    const gw = gateways(this._in.doc).find((g) => g.entry_id === entryId);
    if (!gw) return;
    const model = this._instLinkModel(gw);
    const actuator = model.actuators.find((a) => a.key === actuatorKey);
    const sender = model.senders.find((x) => x.key === senderKey);
    if (!actuator || !sender) return;
    const link = { id: Math.random().toString(36).slice(2, 10), from_id: sender.id ?? "", from_name: sender.name ?? "", to_key: actuator.device ? actuator.key : "", to_name: actuator.device ? "" : actuator.name, role: "", learn: "" };
    if (await this._instSetLinks(gw, [...this._instEntered(gw), link])) await this._loadInstallation();
  },

  async _instTest(entryId, key) {
    // the actuator's state through each of its senders in turn; the links show who answered
    const state = this._in;
    const gw = gateways(state.doc).find((g) => g.entry_id === entryId);
    const device = gw?.devices.find((d) => d.key === key);
    if (!device || state.testing.has(device.note_key)) return;
    state.testing.add(device.note_key);
    this._renderInstallation();
    try {
      await this._hass.callWS({ type: "enocean_eltako/sender_test", entry_id: entryId, device: key });
    } catch (err) {
      this._notice(this._t.senderTestError[err.code] || this._t.senderTestError.failed);
    }
    state.testing.delete(device.note_key);
    await this._loadInstallation();
  },

  async _instDocumentId(entryId, id) {
    // a button ID that an actuator names but Home Assistant has no device for: an entry written down, ID filled in
    const state = this._in;
    const gw = gateways(state.doc).find((g) => g.entry_id === entryId);
    if (!gw) return;
    const plain = (x) => String(x ?? "").replaceAll("-", "").toUpperCase();
    let entry = gw.manual.find((m) => plain(m.address) === plain(id));
    if (!entry) {
      const link = gw.links.find((l) => plain(l.from_id) === plain(id));
      entry = { id: Math.random().toString(36).slice(2, 10), name: link?.from_name || "", address: id, function: "", bus_address: "", feedback_id: "", bus_power: "", kind: "taster", location: "", power: "" };
      gw.manual = [...gw.manual, entry];
      if (!(await this._instSaveManual(gw))) return;
    }
    state.tab = "devices";
    state.view = "funk";
    state.art = "all";
    state.hl = `manual|${entry.id}`;
    this._renderInstallation();
  },

  async _instRemoveLink(entryId, id) {
    const gw = gateways(this._in.doc).find((g) => g.entry_id === entryId);
    if (gw && (await this._instSetLinks(gw, this._instEntered(gw).filter((l) => l.id !== id)))) await this._loadInstallation();
  },

  async _instBulk() {
    // one value into one field of every selected device
    const root = this.shadowRoot;
    const field = root.querySelector("[data-in-bulk-field]").value;
    const value = root.querySelector("[data-in-bulk-value]").value;
    const byGateway = new Map();
    for (const picked of this._in.selected) {
      const [entryId, key] = picked.split("|");
      byGateway.set(entryId, [...(byGateway.get(entryId) ?? []), key]);
    }
    let saved = 0;
    for (const [entryId, keys] of byGateway) {
      const reply = await this._instSend(entryId, keys.map((device) => ({ device, values: { [field]: value } })));
      for (const key of keys) {
        const device = this._instDevice(entryId, key);
        if (device && !reply?.rejected.includes(key)) device[field] = value;
      }
      saved += reply?.saved ?? 0;
    }
    this._notice(this._t.inst.bulkDone(saved), saved > 0);
    this._renderInstallation();
  },

  _instPasteSeen() {
    // what the pasted text is taken for, before it is applied
    if (!this._in.paste.trim()) return "";
    const parsed = parseTable(this._in.paste, this._t);
    return parsed.address === undefined || parsed.address < 0 || !parsed.columns.length ? this._t.inst.pasteBad : this._t.inst.pasteSeen(parsed.rows.length, parsed.columns.length);
  },

  async _instPaste() {
    // a spreadsheet's rows, matched by address; the result is told next to the button
    const state = this._in;
    const parsed = parseTable(state.paste, this._t);
    if (parsed.address === undefined || parsed.address < 0 || !parsed.columns.length) {
      state.pasteResult = this._t.inst.pasteBad;
      this._renderInstallation();
      return;
    }
    const items = new Map(); // entry id -> items
    let missing = 0;
    for (const row of parsed.rows) {
      const found = gateways(state.doc).flatMap((gw) =>
        gw.devices.filter((d) => d.id === row[parsed.address] && (parsed.gateway < 0 || !row[parsed.gateway] || row[parsed.gateway] === gw.title)).map((d) => [gw.entry_id, d]),
      );
      if (!found.length) missing += 1;
      const values = Object.fromEntries(parsed.columns.map(([i, field]) => [field, row[i]]).filter(([, v]) => v));
      if (!Object.keys(values).length) continue;
      for (const [entryId, device] of found) items.set(entryId, [...(items.get(entryId) ?? []), { device: device.key, values }]);
    }
    let saved = 0;
    let rejected = 0;
    for (const [entryId, list] of items) {
      const reply = await this._instSend(entryId, list);
      saved += reply?.saved ?? 0;
      rejected += reply?.rejected.length ?? 0;
      for (const item of list) {
        const device = this._instDevice(entryId, item.device);
        if (device && !reply?.rejected.includes(item.device)) Object.assign(device, item.values);
      }
    }
    state.pasteResult = this._t.inst.pasteDone(saved, missing, rejected);
    this._renderInstallation();
  },

  async _instCopyTable() {
    // the table as tab separated text for a spreadsheet; edit there, paste it back
    const t = this._t;
    const head = [t.inst.addressColumn, t.gateway, t.inst.device, ...INSTALLATION_FIELDS.map((f) => label(t, f))].join("\t");
    const lines = gateways(this._in.doc).flatMap((gw) => gw.devices.map((d) => [d.id, gw.title, d.name, ...INSTALLATION_FIELDS.map((f) => d[f] ?? "")].join("\t")));
    try {
      await navigator.clipboard.writeText([head, ...lines].join("\n") + "\n");
      this._in.pasteResult = t.inst.copied;
    } catch (err) {
      this._in.pasteResult = t.copyFailed;
    }
    this._renderInstallation();
  },
};
