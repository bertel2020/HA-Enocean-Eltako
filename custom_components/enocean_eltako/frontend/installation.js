// The Installation view of the panel: what is known of the installation, and what the user writes
// down about it. Three tabs: the devices by area or place, a table of the devices with typed
// fields that are edited in place (also for a selection, or pasted from a spreadsheet), and the
// event log. Everything comes from the documentation command; edits go back with set_fields. Its
// methods are added to the panel class (this = the panel).

const VERSION = new URL(import.meta.url).search;
const { ICON, docBus, docTables, esc, foldFree, svg } = await import(`./shared.js${VERSION}`);

// the typed fields of a device, in table order; installed is a date
export const INSTALLATION_FIELDS = ["location", "group", "circuit", "bus_address", "feedback_id", "bus_power", "fuse", "installed", "revision", "power", "note"];
// the tabs: the devices (with a switch between the views), the sender IDs, the links, the log
const TABS = ["devices", "gwsenders", "links", "log"];
// the views of the devices tab, and the kinds of device each one shows
const VIEWS = ["all", "bus", "funk", "virt"];
const VIEW_KINDS = { all: null, bus: ["bus", "psu"], funk: ["sensor", "taster", "aktor"], virt: ["virt"] };
const VIEW_OF = { bus: "bus", psu: "bus", sensor: "funk", taster: "funk", aktor: "funk", virt: "virt" };
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
const kindOf = (d) => (d.psu ? "psu" : d.manual ? (/^\d+$/.test(d.bus_address ?? "") ? "bus" : ["taster", "sensor", "aktor"].includes(d.kindRaw) ? d.kindRaw : "taster") : isVirtual(d) ? "virt" : /^\d+$/.test(d.bus_address ?? "") ? "bus" : d.category === "buttons" ? "taster" : d.category === "sensors" || d.category === "meters" ? "sensor" : "aktor");
// the columns of the radio view that can be shown; the first three at first
const FUNK_COLUMNS = ["loc", "id", "sends", "pow", "grp", "sig", "conn"];
const FUNK_DEFAULT = ["id", "sig", "conn"];
const SIGNAL_FRESH = 24 * 3600; // heard within a day: fine; within a week: late; else: silent
const SIGNAL_LATE = 7 * 24 * 3600;
// a field of an entry written by hand, by the name the table gives it
const MANUAL_FIELD = { location: "location", power: "power", note: "function", bus_address: "bus_address", feedback_id: "feedback_id", bus_power: "bus_power" };
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
  place: ["location", "circuit", "fuse"],
  bus: ["group", "bus_address", "feedback_id", "bus_power"],
  upkeep: ["installed", "revision", "power", "note"],
};
const COLUMNS_KEY = "enocean_eltako_installation_columns"; // the groups shown, per browser
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
const loadColumns = () => {
  try {
    const saved = JSON.parse(localStorage.getItem(COLUMNS_KEY));
    if (Array.isArray(saved)) return new Set(saved.filter((g) => g in COLUMN_GROUPS));
  } catch (err) {
    // no storage: the default
  }
  return new Set(["place", "bus"]);
};

// the view's state when the panel starts
export const installationState = () => ({
  doc: null, error: false, tab: "devices", view: "all", art: "all", miss: { loc: false, fuse: false }, folded: new Set(), colMenu: false, funkCols: new Set(FUNK_DEFAULT), docForm: false, docError: "", hl: "", poolOpen: loadPoolOpen(), columns: loadColumns(), group: "", linkGroup: "actuator", selected: new Set(), paste: "", pasteResult: "", q: "",
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
  .installation .itable td.name { min-width: 160px; }
  .installation .itable input.cell { width: 100%; min-width: 90px; box-sizing: border-box; font: inherit; font-size: calc(13px * var(--fs)); padding: 4px 8px; border: 1px solid transparent; border-radius: 6px; background: transparent; color: inherit; }
  .installation .itable input.cell[data-in-field="location"], .installation .itable input.cell[data-in-field="note"] { min-width: 200px; }
  .installation .itable input.cell[data-in-field="group"] { min-width: 170px; }
  .installation .itable input.cell[data-in-field="bus_address"] { min-width: 70px; }
  .installation .itable input.cell[data-in-field="feedback_id"] { min-width: 100px; }
  .installation .itable input.cell[data-in-field="bus_power"] { min-width: 72px; max-width: 96px; text-align: right; }
  .installation .itable input.cell[data-in-field="bus_address"], .installation .itable input.cell[data-in-field="feedback_id"] { font-family: ui-monospace, monospace; font-size: calc(12px * var(--fs)); }
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
  .installation section.gw { border: 1px solid var(--line); border-radius: 12px; padding: 12px 14px 14px; display: grid; gap: 10px; min-width: 0; }
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
  .installation .docform { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; padding: 10px 12px; border: 1px solid var(--accent); border-radius: 10px; background: var(--accent-soft); }
  .installation .docform input, .installation .docform select { font: inherit; font-size: calc(13px * var(--fs)); padding: 5px 8px; border: 1px solid var(--line); border-radius: 6px; background: var(--surface); color: inherit; }
  .installation .docform .cerr { width: 100%; }
  .installation .itable select.cell { font: inherit; font-size: calc(12px * var(--fs)); padding: 2px 6px; border: 1px solid var(--line); border-radius: 6px; background: var(--surface); color: inherit; }
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
  .installation .chips { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
  .installation .chips .isub.lead { min-width: 40px; }
  .installation button.tag { border: 0; font: inherit; font-size: calc(11px * var(--fs)); cursor: pointer; }
  .installation button.tag:hover { color: var(--text); }
  .installation .tag.bus { background: var(--accent-soft); color: var(--accent); }
  .installation .itable tr.grp td { background: var(--soft); font-weight: 500; cursor: pointer; padding: 6px 8px; }
  .installation .itable td .dash { color: var(--muted); }
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
  .installation details.colmenu label { display: flex; gap: 8px; align-items: center; font-size: calc(13px * var(--fs)); padding: 3px 0; cursor: pointer; }
`;

const gateways = (doc) => doc?.gateways ?? [];
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
    const tab = (name, label, selected) => `<button class="itab" role="tab" data-in-tab="${name}" aria-selected="${selected}" tabindex="${selected ? 0 : -1}">${esc(label)}</button>`;
    const groups = TABS.map((name) => tab(name, t.inst.tabNames[name], state.tab === name)).join("");
    const subtabs = "";
    const item = (act, icon, label) => `<button data-in-act="${act}">${esc(label)}</button>`;
    const tools = `<button class="chip" data-in-act="print">${svg(ICON.print)}${esc(t.inst.print)}</button>
      <details class="imenu"><summary class="chip">${svg(ICON.download)}${esc(t.inst.output)}</summary><div class="items">${item("csv", "", t.inst.csvDevices)}${item("csv-tables", "", t.inst.links.tablesCsv)}${item("csv-links", "", t.inst.links.csvShort)}<hr>${item("json", "", "JSON")}</div></details>
      <button class="chip" data-in-act="import">${svg(ICON.upload)}${esc(t.inst.import)}</button>`;
    const body = { devices: () => this._instDevicesTab(), gwsenders: () => this._instSenders(), links: () => this._instLinks(), log: () => this._instLog() }[state.tab]();
    this._setManage();
    this._replace(head, `<div class="itop"><div class="groups" role="tablist">${groups}</div><div class="itools">${tools}</div></div>${subtabs}`);
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
    return `<header class="gwhead"><h3>${esc(gw.title)}</h3><span class="isub mono">${esc(gw.base_id ?? "")}</span>${count === null ? "" : `<span class="isub">${esc(t.deviceCount(count))}</span>`}</header>`;
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
    const t = this._t;
    const T = t.doc.tbl;
    const rows = (gw, senders, externals) => {
      const body = foldFree(senders).map((r) => {
        if (r.free) return `<tr class="free"><td class="mono">${r.nr === r.to ? r.nr : `${r.nr} – ${r.to}`}</td><td colspan="8">${esc(T.free)}</td></tr>`;
        if (r.gateway) return `<tr><td class="mono">0</td><td class="mono">${esc(r.id)}</td><td colspan="7">${esc(T.gateway)}</td></tr>`;
        if (r.blocked) return `<tr><td class="mono">${r.nr}</td><td class="mono">${esc(r.id)}</td><td colspan="6"><span class="tag warn">${esc(T.blocked)}</span></td><td><button class="chip" data-in-free="${esc(r.id)}">${esc(t.freeAction)}</button></td></tr>`;
        return `<tr data-in-row="snd|${esc(gw.entry_id)}|${r.nr}"><td class="mono">${r.nr}</td><td class="mono">${esc(r.id)}</td><td>${esc(r.fn)}</td><td>${esc(r.device)}</td><td>${[r.key ? `<a data-in-goto="${esc(r.key)}">${esc(r.name)}</a>` : esc(r.name), r.place].filter(Boolean).join(", ")}</td><td>${this._instCell(gw, r.key, "bus_address", r.bus, T.busAddress, "1–126")}</td><td>${this._instCell(gw, r.key, "feedback_id", r.feedback, T.feedbackId, "00000081")}</td><td><span class="tag">${esc(r.use)}</span></td><td class="mono">${esc(r.second)}</td></tr>`;
      }).join("");
      const outside = externals.length
        ? `<tr class="outside"><td colspan="9">${esc(T.external)}</td></tr>${externals.map((r) => `<tr><td class="mono">–</td><td class="mono">${esc(r.id)}</td><td></td><td>${esc(r.device)}</td><td>${esc(r.name)}</td><td></td><td></td><td><span class="tag">${esc(r.use)}</span></td><td class="mono">${esc(r.second)}</td></tr>`).join("")}`
        : "";
      return body + outside;
    };
    const head = [T.nr, T.senderId, T.function, T.device, T.description, T.busAddress, T.feedbackId, T.use, T.second];
    return `<p class="isub">${esc(T.sendersIntro)} ${esc(t.inst.editHint)}</p>` + this._instPerGateway((gw, parts) => (parts.senders.length || parts.externals.length ? this._instTable(head, rows(gw, parts.senders, parts.externals)) : ""));
  },

  _instExtras(gw) {
    // what the device table lists besides the devices: the power supplies and the entries written by hand
    const t = this._t;
    const supplies = (gw.supplies ?? []).map((x) => ({ psu: true, sid: x.id, key: `psu|${x.id}`, name: x.name || t.doc.tbl.supplyNoName, id: "", area: "", virtual: false, bus_address: "", location: x.location, circuit: x.circuit, fuse: x.fuse, note: x.note, model: x.watts ? `${x.watts} W` : "" }));
    const manual = (gw.manual ?? []).map((m) => ({ manual: true, mid: m.id, key: `manual|${m.id}`, kindRaw: m.kind, name: m.name || m.address || t.inst.funk.unnamed, id: m.address, area: "", virtual: false, bus_address: m.bus_address, feedback_id: m.feedback_id, bus_power: m.bus_power, location: m.location, power: m.power, note: m.function, group: "", circuit: "", fuse: "", installed: "", revision: "" }));
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
    const tile = (title, value, bad = false) => `<div class="tile${bad ? " bad" : ""}"><small>${esc(title)}</small>${value}</div>`;
    const sensors = all.filter(({ d }) => d.virtual);
    const tiles = `<div class="tiles">${tile(V.tileDevices, esc(I.funk.devicesN(all.length)))}${tile(V.tileLinked, `${all.filter((x) => taught(x).length).length} ${esc(I.of)} ${all.length}`)}${tile(V.tileNoSource, String(sensors.filter(({ d }) => !d.follows?.length).length), sensors.some(({ d }) => !d.follows?.length))}</div>`;
    const search = `<input class="isearch" data-in-search value="${esc(state.q)}" placeholder="${esc(I.search)}" aria-label="${esc(I.search)}">`;
    const sections = gateways(state.doc).map((gw) => {
      const rows = gw.devices.filter((d) => isVirtual(d) && matches(d, state.q)).map((d) => {
        const numbers = gw.numbers?.get(d.note_key) ?? [];
        const nr = numbers.length ? numbers.map((n) => `<a data-in-snd="${esc(gw.entry_id)}|${n}">${n}</a>`).join(", ") : "–";
        const follows = d.follows?.length ? d.follows.map((e) => `<span class="mono">${esc(e)}</span>`).join("<br>") : `<span class="isub">${esc(d.virtual ? V.noSource : V.sendsPress)}</span>`;
        const into = taught({ gw, d }).map((l) => (l.to_key && gw.devices.some((x) => x.note_key === l.to_key) ? `<a data-in-goto="${esc(gw.devices.find((x) => x.note_key === l.to_key).key)}">${esc(l.to_name)}</a>` : esc(l.to_name)) + (l.role ? ` <span class="isub">${esc(l.role)}</span>` : "") + (l.learn ? ` <span class="isub">· ${esc(l.learn)}</span>` : ""));
        return `<tr data-in-row="${esc(d.key)}"><td class="name">${esc(d.name)}<div class="isub">${esc(d.model ?? "")}</div><div>${this._instKindTag(d)}</div></td><td class="mono">${nr}</td><td class="mono">${esc(d.id)}</td><td>${follows}</td><td class="lk">${into.length ? into.join("<br>") : `<span class="isub">${esc(V.noLink)}</span>`}</td></tr>`;
      }).join("");
      const head = [I.device, V.cols.nr, V.cols.id, V.cols.follows, V.cols.taught].map((h) => `<th>${esc(h)}</th>`).join("");
      return `<section class="gw">${this._instGwHead(gw)}<div class="tablewrap"><table class="itable"><thead><tr>${head}</tr></thead><tbody>${rows || `<tr><td colspan="5" class="none">${esc(V.none)}</td></tr>`}</tbody></table></div></section>`;
    });
    return `${tiles}<div class="itools" style="align-items:center">${search}</div>${sections.join("")}<p class="isub">${esc(V.hint)}</p>`;
  },

  _instSignal(d) {
    const T = this._t;
    const sig = d.signal;
    if (!sig || sig.last == null) return `<span class="isub">${esc(d.manual ? T.inst.funk.documented : T.inst.funk.notHeard)}</span>`;
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
    const tile = (title, value, bad = false) => `<div class="tile${bad ? " bad" : ""}"><small>${esc(title)}</small>${value}</div>`;
    const tiles = `<div class="tiles">${tile(F.tileDevices, esc(F.devicesN(all.length)))}${tile(F.tileDocumented, String(all.filter((d) => d.manual).length))}${tile(F.tileSilent, String(late), late > 0)}${tile(F.tileRepeater, String(all.filter((d) => d.signal?.repeater_only).length))}</div>`;
    const kinds = ["taster", "sensor", "aktor"];
    const artChips = `<div class="chips"><span class="isub lead">${esc(I.art)}</span><button class="chip" data-in-art="all" aria-pressed="${state.art === "all"}">${esc(I.all)} <b>${all.length}</b></button>${kinds.map((k) => `<button class="chip" data-in-art="${k}" aria-pressed="${state.art === k}">${esc(I.kinds[k])} <b>${all.filter((d) => kindOf(d) === k).length}</b></button>`).join("")}</div>`;
    const menu = `<details class="colmenu" ${state.colMenu ? "open" : ""}><summary class="chip">${esc(I.columns)}</summary><div class="items">${FUNK_COLUMNS.map((c) => `<label><input type="checkbox" data-in-funkcol="${c}" ${state.funkCols.has(c) ? "checked" : ""}>${esc(F.cols[c])}</label>`).join("")}</div></details>`;
    const search = `<input class="isearch" data-in-search value="${esc(state.q)}" placeholder="${esc(I.search)}" aria-label="${esc(I.search)}">`;
    const form = state.docForm
      ? `<div class="docform"><input data-in-doc-field="name" placeholder="${esc(t.doc.manualName)}" aria-label="${esc(t.doc.manualName)}"><input data-in-doc-field="address" class="mono" maxlength="11" placeholder="${esc(F.idPlaceholder)}" aria-label="${esc(t.doc.manualAddress)}">${gateways(state.doc).length > 1 ? `<select data-in-doc-field="gateway" aria-label="${esc(F.gateway)}">${gateways(state.doc).map((g) => `<option value="${esc(g.entry_id)}">${esc(g.title)}</option>`).join("")}</select>` : ""}<select data-in-doc-field="kind" aria-label="${esc(I.art)}">${kinds.map((k) => `<option value="${k}">${esc(I.kinds[k])}</option>`).join("")}</select><input data-in-doc-field="function" placeholder="${esc(t.doc.manualFunction)}" aria-label="${esc(t.doc.manualFunctionHead)}" style="flex:1;min-width:160px"><button class="chip" data-in-act="doc-add">${esc(F.add)}</button><button class="chip" data-in-act="doc-cancel">${esc(F.cancel)}</button>${state.docError ? `<div class="cerr" role="alert">${esc(state.docError)}</div>` : ""}</div>`
      : "";
    const tools = `<div class="itools" style="align-items:center">${search}<span style="flex:1"></span><button class="chip" data-in-act="doc-open">${esc(F.document)}</button>${menu}</div>`;
    const input = (d, gw, field, value, placeholder, extra = "") => (d.manual
      ? `<input class="cell" data-in-mfield="${MANUAL_FIELD[field] ?? field}" data-in-gw="${esc(gw.entry_id)}" data-in-mid="${esc(d.mid)}" value="${esc(value ?? "")}" placeholder="${esc(placeholder)}" aria-label="${esc(placeholder)}: ${esc(d.name)}" autocomplete="off" ${extra}>`
      : `<input class="cell" data-in-field="${field}" data-in-gw="${esc(gw.entry_id)}" data-in-key="${esc(d.key)}" value="${esc(value ?? "")}" placeholder="${esc(placeholder)}" aria-label="${esc(placeholder)}: ${esc(d.name)}" autocomplete="off" ${extra}>`);
    const cell = (c, gw, d) => {
      if (c === "loc") return `<td>${this._instPlace(gw, d)}</td>`;
      if (c === "id") return `<td class="mono">${esc(d.id)}${(d.ids ?? []).filter((x) => x.id !== d.id).map((x) => `<br>${esc(x.id)}`).join("")}${d.ids?.length > 1 ? `<div class="isub" style="font-family:inherit">${esc(F.manyIds(d.ids.length))}</div>` : ""}</td>`;
      if (c === "sends") return `<td>${d.manual ? input(d, gw, "note", d.note, t.doc.manualFunctionHead) : esc([t.doc.tbl.categories[d.category], d.eep].filter(Boolean).join(" · ") || "–")}</td>`;
      if (c === "pow") return `<td>${input(d, gw, "power", d.power, label(t, "power"))}</td>`;
      if (c === "grp") return `<td>${d.manual ? '<span class="dash">–</span>' : input(d, gw, "group", d.group, label(t, "group"))}</td>`;
      if (c === "sig") return `<td>${this._instSignal(d)}</td>`;
      return `<td class="lk">${this._instLinksOf(gw, d)}</td>`;
    };
    const sections = gateways(state.doc).map((gw) => {
      const rows = radio(gw).map((d) => {
        const kindSelect = d.manual ? ` <select class="cell" data-in-mfield="kind" data-in-gw="${esc(gw.entry_id)}" data-in-mid="${esc(d.mid)}" aria-label="${esc(I.art)}: ${esc(d.name)}">${kinds.map((k) => `<option value="${k}" ${kindOf(d) === k ? "selected" : ""}>${esc(I.kinds[k])}</option>`).join("")}</select>` : "";
        const name = d.manual ? `<input class="cell" data-in-mfield="name" data-in-gw="${esc(gw.entry_id)}" data-in-mid="${esc(d.mid)}" value="${esc(d.name === F.unnamed ? "" : d.name)}" placeholder="${esc(t.doc.manualName)}" aria-label="${esc(t.doc.manualName)}" autocomplete="off">` : esc(d.name);
        const sub = d.manual ? "" : `<div class="isub">${esc([d.model, d.eep].filter(Boolean).join(" · "))}</div>`;
        const delete_ = d.manual ? `<td><button class="icon-btn" data-in-mdel="${esc(d.mid)}" data-in-gw="${esc(gw.entry_id)}" title="${esc(t.doc.manualRemove)}" aria-label="${esc(t.doc.manualRemove)}">${svg(ICON.close)}</button></td>` : "<td></td>";
        return `<tr data-in-row="${esc(d.key)}"><td class="name">${name}${sub}<div>${d.manual ? kindSelect : this._instKindTag(d)}${d.manual ? "" : this._instSendTag(gw, d)}${d.manual ? ` <span class="tag">${esc(F.documented)}</span>` : ""}</div></td>${cols.map((c) => cell(c, gw, d)).join("")}${delete_}</tr>`;
      }).join("");
      const head = cols.map((c) => `<th>${esc(F.cols[c])}</th>`).join("");
      return `<section class="gw">${this._instGwHead(gw)}<div class="tablewrap"><table class="itable"><thead><tr><th>${esc(I.device)}</th>${head}<th></th></tr></thead><tbody>${rows || `<tr><td colspan="${cols.length + 2}" class="none">${esc(F.none)}</td></tr>`}</tbody></table></div></section>`;
    });
    return `${tiles}${tools}${artChips}${form}${sections.join("")}<p class="isub">${esc(F.hint)}</p>`;
  },

  _instBus() {
    const t = this._t;
    return `<p class="isub">${esc(t.doc.tbl.busIntro.replace(" (*)", ""))} ${esc(t.inst.editHint)}</p>` + this._instPerGateway((gw) => this._instBusOf(gw));
  },

  _instKindTag(d) {
    const kind = kindOf(d);
    return `<button class="tag${kind === "bus" ? " bus" : ""}" data-in-kind="${kind}" title="${esc(this._t.inst.kindHint)}">${esc(this._t.inst.kinds[kind])}${kind === "bus" ? ` · ${esc(d.bus_address)}` : ""}</button>`;
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
    const addButton = `<div><button class="chip" data-in-supply-add="${esc(gw.entry_id)}">${esc(t.doc.supplyAdd)}</button></div>`;
    if (!bus.rows.length && !own.length) return `<div class="none">${esc(T.busEmpty)}</div>${addButton}`;
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
      const tag = r.from === "table" ? `<span class="tag" title="${esc(bus.source)}">${esc(T.busSourceTableShort)}</span>` : r.from === "group" ? `<span class="isub">${esc(T.busGroupLine)}</span>` : r.power === null ? `<span class="tag warn">${esc(T.noValue)}</span>` : "";
      const power = r.key ? `<span style="display:inline-flex;gap:6px;align-items:center;justify-content:flex-end">${cell(r, "bus_power", r.raw, `${T.power} (W)`, r.table !== null ? String(r.table).replace(".", ",") : "W")}${tag}</span>` : r.power === null ? tag : esc(num(r.power));
      return `<tr${dups.has(r.address) ? ' class="dup"' : ""}><td class="name">${name}</td><td class="mono">${r.key ? cell(r, "bus_address", String(r.address), T.busAddress, "1–126") : r.address}</td><td>${r.key ? cell(r, "feedback_id", r.feedback, T.feedbackId, "00000081") : esc(r.feedback)}</td><td class="num">${power}</td><td>${r.key ? cell(r, "group", r.group, T.partOf) : esc(r.group)}</td></tr>`;
    };
    const sfield = (x, field, ph, width) => `<input class="cell" data-in-sfield="${field}" data-in-gw="${esc(gw.entry_id)}" data-in-sid="${esc(x.s.id)}" value="${esc(x.s[field] ?? "")}" placeholder="${esc(ph)}" aria-label="${esc(ph)}" style="width:${width}px;min-width:0" autocomplete="off"${field === "watts" ? ' inputmode="decimal"' : field === "name" ? "" : ' inputmode="numeric"'}>`;
    const usage = (capacity, rows) => {
      const l = load(rows);
      const pct = capacity ? Math.round((l / capacity) * 100) : null;
      return { l, pct, over: capacity !== null && l > capacity };
    };
    const bar = (u) => (u.pct === null ? "" : `<span class="barbg"><i class="${u.pct >= 80 ? "hot" : ""}" style="width:${Math.min(u.pct, 100)}%"></i></span>`);
    const groups = supplies.map((x, i) => {
      const u = usage(x.capacity, rowsOf[i]);
      const text = x.capacity !== null ? `${num(u.l)} ${t.inst.of} ${num(x.capacity)}${u.over ? ` · ${B.overloaded}` : ""}` : num(u.l);
      const place = [x.s.location, x.s.circuit, x.s.fuse].filter(Boolean).join(", ");
      return { u, html: `<tr class="psu${u.over ? " bad" : ""}"><td colspan="5"><div class="psurow">${sfield(x, "name", t.doc.supplyName, 150)}${sfield(x, "watts", t.doc.supplyWatts, 64)}<span class="isub">W</span><span class="isub">${esc(T.busAddress)}</span>${sfield(x, "first", t.doc.supplyFirst, 56)}<span>–</span>${sfield(x, "last", t.doc.supplyLast, 56)}${bar(u)}<span class="isub">${esc(text)}</span>${place ? `<span class="isub">· ${esc(place)}</span>` : ""}<button class="icon-btn" data-in-supply-del="${esc(x.s.id)}" data-in-gw="${esc(gw.entry_id)}" title="${esc(t.doc.supplyRemove)}" aria-label="${esc(t.doc.supplyRemove)}">${svg(ICON.close)}</button></div></td></tr>${rowsOf[i].map(row).join("")}` };
    });
    let body = groups.map((g) => g.html).join("");
    if (!own.length) {
      const standard = bus.supplies[0];
      body += `<tr class="psu"><td colspan="5"><div class="psurow"><b>${esc(standard.name)}</b><span class="isub">${esc(num(standard.capacity ?? 0))}${standard.percent !== null ? ` · ${standard.percent} %` : ""}</span><span class="isub">${esc(B.standardNote)}</span></div></td></tr>`;
    }
    if (without.length) body += `${own.length ? `<tr class="psu bad"><td colspan="5"><b>${esc(B.noSupply)}</b> <span class="isub">${without.length}</span></td></tr>` : ""}${without.map(row).join("")}`;
    const sum = `<tr><td colspan="3"><b>${esc(T.busSum(bus.counted, bus.rows.length))}</b></td><td class="num"><b>${esc(num(bus.sum))}</b></td><td></td></tr>`;
    const overCount = groups.filter((g) => g.u.over).length;
    const runs = bus.items.filter((r) => r.free).map((r) => (r.from === r.to ? `${r.from}` : `${r.from}–${r.to}`));
    const missing = bus.rows.length - bus.counted;
    const tile = (title, value, bad = false) => `<div class="tile${bad ? " bad" : ""}"><small>${esc(title)}</small>${value}</div>`;
    const tiles = `<div class="tiles">${tile(B.duplicates, esc(bus.dups.length ? B.dupText(bus.dups.join(", ")) : B.none), bus.dups.length > 0)}${tile(B.used, esc(B.usedOf(new Set(bus.rows.map((r) => r.address)).size)))}${tile(B.free, esc(runs.slice(0, 6).join(", ") + (runs.length > 6 ? " …" : "")))}${tile(B.power, `${esc(num(bus.sum))}${missing ? ` <span class="isub">${esc(B.withoutValue(missing))}</span>` : ""}`)}${tile(B.supplies, esc(overCount ? B.supplyOver(overCount) : without.length && own.length ? B.supplyWithout(without.length) : B.supplyOk), overCount > 0 || (own.length > 0 && without.length > 0))}</div>`;
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
    const count = (view) => all.filter((d) => !VIEW_KINDS[view] || VIEW_KINDS[view].includes(kindOf(d))).length;
    const seg = VIEWS.map((v) => `<button data-in-view="${v}" aria-pressed="${state.view === v}">${esc(t.views[v])}<span class="isub">${count(v)}</span></button>`).join("");
    const body = { all: () => this._instDevices(), virt: () => this._instVirt(), bus: () => this._instBus(), funk: () => this._instFunk() }[state.view]();
    return `<div class="gbar"><div class="seg" role="group">${seg}</div></div>${body}`;
  },

  _instPlace(gw, d) {
    // the place as three fields that look like one: cabinet, row, slot
    const parts = placeParts(d.location);
    const inputs = this._t.inst.placeParts.map((label, i) => `<input data-in-part="${i}" value="${esc(parts[i])}" placeholder="${esc(label)}" aria-label="${esc(label)}: ${esc(d.name)}" autocomplete="off">`).join("<i>·</i>");
    const who = d.psu ? `data-in-sid="${esc(d.sid)}"` : d.manual ? `data-in-mid="${esc(d.mid)}"` : `data-in-key="${esc(d.key)}"`;
    return `<div class="place${d.location ? "" : " blank"}" data-in-place data-in-gw="${esc(gw.entry_id)}" ${who}>${inputs}</div>`;
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
    const columns = INSTALLATION_FIELDS.filter((f) => Object.entries(COLUMN_GROUPS).some(([g, fields]) => state.columns.has(g) && fields.includes(f)));
    const showArea = state.columns.has("place");
    const key = (gw, d) => `${gw.entry_id}|${d.key}`;
    const applies = (d, f) => (d.manual ? f in MANUAL_FIELD : d.psu ? ["location", "circuit", "fuse", "note"].includes(f) : isVirtual(d) ? f === "note" : ["circuit", "fuse"].includes(f) ? FUSE_KINDS.has(kindOf(d)) : true);
    const psus = (gw) => this._instExtras(gw);
    const pass = (d) => matches(d, state.q)
      && (!kinds || kinds.includes(kindOf(d)))
      && (state.art === "all" || kindOf(d) === state.art)
      && (!state.miss.loc || (!isVirtual(d) && !d.location))
      && (!state.miss.fuse || (FUSE_KINDS.has(kindOf(d)) && !d.fuse));
    const span = columns.length + (showArea ? 1 : 0) + 2;
    const row = (gw, d) => {
      const cells = columns
        .map((f) => {
          if (!applies(d, f)) return `<td><span class="dash">–</span></td>`;
          if (f === "location") return `<td>${this._instPlace(gw, d)}</td>`;
          if (d.manual) return `<td><input class="cell" data-in-mfield="${MANUAL_FIELD[f]}" data-in-gw="${esc(gw.entry_id)}" data-in-mid="${esc(d.mid)}" value="${esc(d[f] ?? "")}" placeholder="${esc(label(t, f))}" aria-label="${esc(label(t, f))}: ${esc(d.name)}" autocomplete="off"></td>`;
          if (d.psu) return `<td><input class="cell" data-in-sfield="${f}" data-in-gw="${esc(gw.entry_id)}" data-in-sid="${esc(d.sid)}" value="${esc(d[f] ?? "")}" placeholder="${esc(label(t, f))}" aria-label="${esc(label(t, f))}: ${esc(d.name)}" autocomplete="off"></td>`;
          return `<td><input class="cell" ${f === "installed" ? 'type="date"' : ""} data-in-field="${f}" data-in-gw="${esc(gw.entry_id)}" data-in-key="${esc(d.key)}" value="${esc(d[f] ?? "")}" placeholder="${esc(label(t, f))}" aria-label="${esc(label(t, f))}: ${esc(d.name)}" autocomplete="off"></td>`;
        })
        .join("");
      const picked = state.selected.has(key(gw, d));
      const area = showArea ? `<td class="isub">${esc(d.area || "–")}</td>` : "";
      const pick = d.psu || d.manual ? "" : `<input type="checkbox" data-in-pick="${esc(key(gw, d))}" ${picked ? "checked" : ""} aria-label="${esc(d.name)}">`;
      return `<tr data-in-row="${esc(d.key)}"><td>${pick}</td><td class="name">${esc(d.name)}<div class="isub">${esc(d.psu ? d.model : d.id)}</div><div>${this._instKindTag(d)}${d.psu || d.manual ? "" : this._instSendTag(gw, d)}${d.manual ? ` <span class="tag">${esc(I.funk.documented)}</span>` : ""}</div></td>${area}${cells}</tr>`;
    };
    const sections = gateways(state.doc).map((gw) => {
      const devices = [...gw.devices, ...psus(gw)].filter(pass);
      let rows;
      if (state.group && devices.length) {
        const groups = new Map();
        for (const d of devices) {
          const name = isVirtual(d) && state.group === "location" ? I.virtualNoPlace : (state.group === "area" ? d.area : placeParts(d.location)[0]) || (state.group === "area" ? I.noGroup : I.noPlace);
          groups.set(name, [...(groups.get(name) ?? []), d]);
        }
        const rank = (n) => (n === I.virtualNoPlace ? 2 : n === I.noGroup || n === I.noPlace ? 1 : 0);
        rows = [...groups.entries()]
          .sort(([a], [b]) => rank(a) - rank(b) || a.localeCompare(b))
          .map(([name, list]) => {
            const id = `${gw.entry_id}|${name}`;
            const closed = state.folded.has(id);
            return `<tr class="grp" data-in-fold="${esc(id)}"><td colspan="${span}">${closed ? "▸" : "▾"} ${esc(name)} <span class="isub">${list.length}</span></td></tr>${closed ? "" : list.map((d) => row(gw, d)).join("")}`;
          })
          .join("");
      } else rows = devices.map((d) => row(gw, d)).join("");
      const head = columns.map((f) => `<th>${esc(label(t, f))}</th>`).join("");
      return `<section class="gw">${this._instGwHead(gw, devices.length)}<div class="tablewrap"><table class="itable"><thead><tr><th></th><th>${esc(I.device)}</th>${showArea ? `<th>${esc(I.area)}</th>` : ""}${head}</tr></thead><tbody>${rows || `<tr><td colspan="${span}" class="none">${esc(I.noDevices)}</td></tr>`}</tbody></table></div></section>`;
    });
    const picked = state.selected.size;
    const bulk = picked
      ? `<div class="bulk"><b>${esc(I.selected(picked))}</b><select data-in-bulk-field aria-label="${esc(I.setField)}">${INSTALLATION_FIELDS.map((f) => `<option value="${f}">${esc(label(t, f))}</option>`).join("")}</select><input data-in-bulk-value placeholder="${esc(I.value)}" aria-label="${esc(I.value)}"><button class="chip" data-in-act="bulk">${esc(I.apply)}</button><button class="chip" data-in-act="unpick">${esc(I.clearSelection)}</button></div>`
      : "";
    const paste = `<details><summary>${esc(I.pasteTitle)}</summary><div style="display:grid;gap:8px;margin-top:8px"><span class="isub">${esc(I.pasteHint)}</span><textarea class="paste" data-in-paste placeholder="${esc(I.pastePlaceholder)}" aria-label="${esc(I.pasteTitle)}">${esc(state.paste)}</textarea><div><button class="chip" data-in-act="paste">${esc(I.apply)}</button> <button class="chip" data-in-act="copy-table">${esc(I.copyTable)}</button> <span class="isub">${esc(state.pasteResult)}</span></div></div></details>`;
    const menu = `<details class="colmenu" ${state.colMenu ? "open" : ""}><summary class="chip">${esc(I.columns)}</summary><div class="items">${Object.keys(COLUMN_GROUPS).map((g) => `<label><input type="checkbox" data-in-columns="${g}" ${state.columns.has(g) ? "checked" : ""}>${esc(I.columnGroups[g])}</label>`).join("")}</div></details>`;
    const present = gateways(state.doc).flatMap((gw) => [...gw.devices, ...psus(gw)]);
    const kindList = kinds ?? ["bus", "sensor", "taster", "aktor", "virt", "psu"];
    const artChips = kindList.length > 1
      ? `<div class="chips"><span class="isub lead">${esc(I.art)}</span><button class="chip" data-in-art="all" aria-pressed="${state.art === "all"}">${esc(I.all)} <b>${present.filter((d) => !kinds || kinds.includes(kindOf(d))).length}</b></button>${kindList.map((k) => `<button class="chip" data-in-art="${k}" aria-pressed="${state.art === k}">${esc(I.kinds[k])} <b>${present.filter((d) => kindOf(d) === k).length}</b></button>`).join("")}</div>`
      : "";
    const missChips = state.view === "all"
      ? `<div class="chips"><span class="isub lead">${esc(I.missing)}</span><button class="chip" data-in-miss="loc" aria-pressed="${state.miss.loc}">${esc(label(t, "location"))} <b>${present.filter((d) => !isVirtual(d) && !d.location).length}</b></button><button class="chip" data-in-miss="fuse" aria-pressed="${state.miss.fuse}">${esc(label(t, "fuse"))} <b>${present.filter((d) => FUSE_KINDS.has(kindOf(d)) && !d.fuse).length}</b></button></div>`
      : "";
    const group = state.view === "all"
      ? `<label class="isub">${esc(I.groupBy)} <select data-in-groupsel aria-label="${esc(I.groupBy)}"><option value="">${esc(I.groupNone)}</option><option value="area" ${state.group === "area" ? "selected" : ""}>${esc(I.byArea)}</option><option value="location" ${state.group === "location" ? "selected" : ""}>${esc(I.byPlace)}</option></select></label>`
      : "";
    const search = `<input class="isearch" data-in-search value="${esc(state.q)}" placeholder="${esc(I.search)}" aria-label="${esc(I.search)}">`;
    return `<div class="itools" style="align-items:center">${search}${group}<span style="flex:1"></span>${menu}</div>${artChips}${missChips}${state.view === "all" ? this._instProgress() : ""}${bulk}${sections.join("")}${paste}`;
  },

  _instLinks() {
    // who is taught into which actuator; every link says where it comes from and what proves it
    const t = this._t;
    const state = this._in;
    const L = t.inst.links;
    const when = (iso) => new Date(iso).toLocaleString(this._hass.language);
    const seg = (group, text) => `<button data-in-link-group="${group}" aria-pressed="${state.linkGroup === group}">${esc(text)}</button>`;
    const toggle = `<div class="gbar"><span class="isub">${esc(t.inst.groupBy)}</span><div class="seg" role="group">${seg("actuator", L.byActuator)}${seg("sender", L.bySender)}</div></div>
      <div class="isub">${esc(L.honest)}</div>`;
    const input = (gw, attr, value, placeholder, extra = "") => `<input class="cell" ${attr} data-in-gw="${esc(gw.entry_id)}" value="${esc(value)}" placeholder="${esc(placeholder)}" aria-label="${esc(placeholder)}" autocomplete="off" ${extra}>`;
    const fromLabel = (l) => (l.from_kind === "entered" ? [l.from_name, l.from_id].filter(Boolean).join(" · ") : `${L.from[l.from_kind]} · ${l.from_id}`);
    const role = (l) => (l.source === "assigned" ? this._profile(l.role) : l.role);
    const evidence = (l) => [l.teach_in ? L.teachIn(when(l.teach_in)) : "", l.tested ? L.tested(when(l.tested)) : ""].filter(Boolean).join(" · ");
    const status = (l) => `<span class="tag ${l.status === "confirmed" ? "ok" : l.status === "no_answer" ? "warn" : ""}" title="${esc(L.statusHint[l.status])}">${esc(L.status[l.status])}</span>`;
    const row = (gw, l, target) => {
      const learn = l.source === "entered"
        ? input(gw, `data-in-efield="learn" data-in-eid="${esc(l.id)}"`, l.learn, L.learn)
        : input(gw, `data-in-learn="${esc(l.key)}"`, l.learn, L.learn);
      const cells = l.source === "entered"
        ? `<td>${input(gw, `data-in-efield="from_name" data-in-eid="${esc(l.id)}"`, l.from_name, L.fromName)}${input(gw, `data-in-efield="from_id" data-in-eid="${esc(l.id)}"`, l.from_id, L.fromId)}</td><td>${input(gw, `data-in-efield="role" data-in-eid="${esc(l.id)}"`, l.role, L.role)}</td>`
        : `<td>${esc(target ? l.to_name : fromLabel(l))}<div class="isub">${esc(target ? l.to_id : "")}</div></td><td>${esc(role(l))}</td>`;
      const first = l.source === "entered" ? "" : "";
      return `<tr>${cells}<td>${learn}</td><td>${status(l)}<div class="isub">${esc(evidence(l))}</div></td><td>${l.source === "entered" ? `<button class="icon-btn" data-in-del="${esc(l.id)}" data-in-gw="${esc(gw.entry_id)}" title="${esc(L.remove)}" aria-label="${esc(L.remove)}">${svg(ICON.close)}</button>` : `<span class="isub">${esc(L.source[l.source])}</span>`}${first}</td></tr>`;
    };
    const head = `<thead><tr><th>${esc(L.from.title)}</th><th>${esc(L.role)}</th><th>${esc(L.learn)}</th><th>${esc(L.state)}</th><th></th></tr></thead>`;
    const sections = gateways(state.doc).map((gw) => {
      let body;
      if (state.linkGroup === "actuator") {
        const groups = new Map();
        for (const l of gw.links) {
          const key = l.to_key || `name|${l.to_name}`;
          groups.set(key, [...(groups.get(key) ?? []), l]);
        }
        body = [...groups.values()]
          .sort((a, b) => a[0].to_name.localeCompare(b[0].to_name))
          .map((links) => `<div class="gcard" style="margin-bottom:10px"><b>${esc(links[0].to_name)} <span class="isub">${esc(links[0].to_id)}</span></b><div class="tablewrap"><table class="itable">${head}<tbody>${links.map((l) => row(gw, l, false)).join("")}</tbody></table></div><div class="isub">${esc(L.otherSenders)}</div></div>`)
          .join("");
      } else {
        const groups = new Map();
        for (const l of gw.links) {
          const key = l.from_id || l.from_name;
          groups.set(key, [...(groups.get(key) ?? []), l]);
        }
        body = [...groups.values()]
          .map((links) => `<div class="gcard" style="margin-bottom:10px"><b>${esc(fromLabel(links[0]))}</b><div class="tablewrap"><table class="itable"><thead><tr><th>${esc(L.controls)}</th><th>${esc(L.role)}</th><th>${esc(L.learn)}</th><th>${esc(L.state)}</th><th></th></tr></thead><tbody>${links.map((l) => row(gw, l, true)).join("")}</tbody></table></div></div>`)
          .join("");
      }
      const options = [...gw.devices.filter((d) => !isVirtual(d)).map((d) => `<option value="${esc(d.note_key)}">${esc(d.name)} · ${esc(d.id)}</option>`), `<option value="">${esc(L.otherTarget)}</option>`].join("");
      const add = `<div class="bulk" data-in-link-form="${esc(gw.entry_id)}"><b>${esc(L.addTitle)}</b><input data-in-new="from_name" placeholder="${esc(L.fromName)}" aria-label="${esc(L.fromName)}"><input data-in-new="from_id" placeholder="${esc(L.fromId)}" aria-label="${esc(L.fromId)}"><span>→</span><select data-in-new="to_key" aria-label="${esc(L.target)}">${options}</select><input data-in-new="to_name" placeholder="${esc(L.otherName)}" aria-label="${esc(L.otherName)}"><input data-in-new="role" placeholder="${esc(L.role)}" aria-label="${esc(L.role)}"><input data-in-new="learn" placeholder="${esc(L.learn)}" aria-label="${esc(L.learn)}"><button class="chip" data-in-act="add-link" data-in-gw="${esc(gw.entry_id)}">${esc(L.add)}</button></div>`;
      return `<section class="gw">${this._instGwHead(gw)}${body || `<div class="none">${esc(L.none)}</div>`}${add}</section>`;
    });
    return toggle + sections.join("");
  },

  _instLog() {
    const t = this._t;
    const multi = gateways(this._in.doc).length > 1;
    const rows = gateways(this._in.doc)
      .flatMap((gw) => gw.log.map((e) => ({ ...e, gateway: gw.title })))
      .sort((a, b) => b.time.localeCompare(a.time))
      .map((e) => `<tr><td class="mono">${esc(new Date(e.time).toLocaleString(this._hass.language))}</td><td class="kind">${esc(t.inst.events[e.kind] || e.kind)}</td><td>${esc(e.detail || e.device)}</td>${multi ? `<td class="isub">${esc(e.gateway)}</td>` : ""}</tr>`)
      .join("");
    if (!rows) return `<div class="none">${esc(t.inst.noLog)}</div>`;
    return `<div class="tablewrap"><table class="itable log"><thead><tr><th>${esc(t.time)}</th><th>${esc(t.inst.event)}</th><th>${esc(t.inst.detail)}</th>${multi ? `<th>${esc(t.gateway)}</th>` : ""}</tr></thead><tbody>${rows}</tbody></table></div>`;
  },

  _installationClick(e) {
    const state = this._in;
    if (state.colMenu && !e.target.closest(".colmenu")) {
      state.colMenu = false;
      this.shadowRoot.querySelector("#installation details.colmenu")?.removeAttribute("open");
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
      // a link's device: the All devices view with its row marked
      state.tab = "devices";
      state.view = "all";
      state.art = "all";
      state.q = "";
      state.hl = goto.dataset.inGoto;
      this._renderInstallation();
      return;
    }
    const mdel = e.target.closest("[data-in-mdel]");
    if (mdel) {
      const gw = gateways(state.doc).find((g) => g.entry_id === mdel.dataset.inGw);
      if (!gw) return;
      gw.manual = gw.manual.filter((x) => x.id !== mdel.dataset.inMdel);
      this._renderInstallation();
      this._instSaveManual(gw);
      return;
    }
    const supplyAdd = e.target.closest("[data-in-supply-add]");
    if (supplyAdd) {
      const gw = gateways(state.doc).find((g) => g.entry_id === supplyAdd.dataset.inSupplyAdd);
      if (!gw) return;
      gw.supplies = [...gw.supplies, { ...SUPPLY_BLANK, id: Math.random().toString(36).slice(2, 10) }];
      this._renderInstallation();
      [...this.shadowRoot.querySelectorAll('#installation [data-in-sfield="name"]')].pop()?.focus();
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
      // the release is confirmed in the pool above the table, where the blocked ID is listed
      const plain = (id) => id.replaceAll("-", "").toUpperCase(); // the table writes IDs without dashes
      let row = null;
      const pool = this._pools.find((p) => (row = p.rows.find((r) => plain(r.id) === plain(free.dataset.inFree))));
      if (!pool) return;
      this._pool = pool.id;
      this._sid.text = row.id;
      this._sid.state = "";
      this.shadowRoot.getElementById("sidText").value = row.id;
      this._freeing = { id: row.id, device: row.device || row.ref || "" };
      state.poolOpen = true;
      this._setManage();
      this._renderSenderIds();
      this.shadowRoot.querySelector("#senders .confirm")?.scrollIntoView({ block: "center", behavior: "smooth" });
      return;
    }
    const linkGroup = e.target.closest("[data-in-link-group]");
    if (linkGroup) {
      state.linkGroup = linkGroup.dataset.inLinkGroup;
      this._renderInstallation();
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
    const columns = e.target.closest("[data-in-columns]");
    if (columns) {
      const name = columns.dataset.inColumns;
      state.colMenu = true;
      if (state.columns.has(name)) state.columns.delete(name);
      else state.columns.add(name);
      try {
        localStorage.setItem(COLUMNS_KEY, JSON.stringify([...state.columns]));
      } catch (err) {
        // not saved: shown for this visit
      }
      this._renderInstallation();
      return;
    }
    const act = e.target.closest("[data-in-act]")?.dataset.inAct;
    if (!act) return;
    this.shadowRoot.querySelector("#installation details.imenu")?.removeAttribute("open");
    if (act === "print") this._documentation("print");
    else if (act === "csv") this._documentation("csv");
    else if (act === "csv-links") this._documentation("csv-links");
    else if (act === "csv-tables") this._documentation("csv-tables");
    else if (act === "json") this._documentation("json");
    else if (act === "import") this.shadowRoot.getElementById("docFile").click();
    else if (act === "unpick") {
      state.selected.clear();
      this._renderInstallation();
    } else if (act === "bulk") this._instBulk();
    else if (act === "paste") this._instPaste();
    else if (act === "copy-table") this._instCopyTable();
    else if (act === "doc-open") {
      state.docForm = true;
      state.docError = "";
      this._renderInstallation();
      this.shadowRoot.querySelector('#installation [data-in-doc-field="name"]')?.focus();
    } else if (act === "doc-cancel") {
      state.docForm = false;
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
    else if (act === "add-link") this._instAddLink(e.target.closest("[data-in-act]").dataset.inGw);
  },

  _installationChange(e) {
    const mkind = e.target.closest("select[data-in-mfield]");
    if (mkind) {
      this._instManualInput(mkind);
      return;
    }
    const groupsel = e.target.closest("[data-in-groupsel]");
    if (groupsel) {
      this._in.group = groupsel.value;
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
    if (e.target.matches("[data-in-paste]")) {
      state.paste = e.target.value;
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
    const value = joinPlace([...box.querySelectorAll("input")].map((i) => i.value));
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
    // an entry written by hand from the form: name, ID, kind, what it does
    const state = this._in;
    const form = this.shadowRoot.querySelector("#installation .docform");
    const get = (name) => form.querySelector(`[data-in-doc-field="${name}"]`).value.trim();
    const gw = gateways(state.doc).find((g) => g.entry_id === form.querySelector('[data-in-doc-field="gateway"]')?.value) ?? gateways(state.doc)[0];
    const plain = get("address").replaceAll("-", "").toUpperCase();
    state.docError = "";
    if (!get("name")) state.docError = this._t.inst.funk.needName;
    else if (!/^[0-9A-F]{8}$/.test(plain)) state.docError = this._t.inst.funk.badId;
    else if (gw.manual.some((m) => m.address.replaceAll("-", "").toUpperCase() === plain)) state.docError = this._t.inst.funk.known;
    if (state.docError) {
      this._renderInstallation();
      return;
    }
    const id = Math.random().toString(36).slice(2, 10);
    gw.manual = [...gw.manual, { id, name: get("name"), address: plain.match(/../g).join("-"), function: get("function"), bus_address: "", feedback_id: "", bus_power: "", kind: get("kind"), location: "", power: "" }];
    state.docForm = false;
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

  async _instAddLink(entryId) {
    const gw = gateways(this._in.doc).find((g) => g.entry_id === entryId);
    const form = this.shadowRoot.querySelector(`[data-in-link-form="${CSS.escape(entryId)}"]`);
    if (!gw || !form) return;
    const get = (name) => form.querySelector(`[data-in-new="${name}"]`).value.trim();
    const link = { id: Math.random().toString(36).slice(2, 10), from_id: get("from_id"), from_name: get("from_name"), to_key: get("to_key"), to_name: get("to_name"), role: get("role"), learn: get("learn") };
    if (!(link.from_id || link.from_name) || !(link.to_key || link.to_name)) {
      this._notice(this._t.inst.links.incomplete);
      return;
    }
    if (await this._instSetLinks(gw, [...this._instEntered(gw), link])) await this._loadInstallation();
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
