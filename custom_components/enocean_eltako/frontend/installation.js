// The Installation view of the panel: what is known of the installation, and what the user writes
// down about it. Three tabs: the devices by area or place, a table of the devices with typed
// fields that are edited in place (also for a selection, or pasted from a spreadsheet), and the
// event log. Everything comes from the documentation command; edits go back with set_fields. Its
// methods are added to the panel class (this = the panel).

const VERSION = new URL(import.meta.url).search;
const { ICON, docBus, docTables, esc, foldFree, svg } = await import(`./shared.js${VERSION}`);

// the typed fields of a device, in table order; installed is a date
export const INSTALLATION_FIELDS = ["location", "group", "circuit", "bus_address", "feedback_id", "bus_power", "fuse", "installed", "revision", "power", "note"];
// the tabs in groups: the second row of tabs shows the tabs of the group that is open
const GROUPS = [
  { id: "site", tabs: ["areas", "devices"] },
  { id: "senders", tabs: ["gwsenders", "buttons", "radio"] },
  { id: "bus", tabs: ["bus", "supplies"] },
  { id: "links", tabs: ["links"] },
  { id: "log", tabs: ["log"] },
];
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
  doc: null, error: false, tab: "areas", last: {}, poolOpen: loadPoolOpen(), columns: loadColumns(), group: "area", linkGroup: "actuator", selected: new Set(), paste: "", pasteResult: "", q: "",
});

export const INSTALLATION_STYLE = `
  .installation { padding-bottom: 8px; }
  .installation .itop { display: flex; flex-wrap: wrap; gap: 8px 12px; align-items: center; padding: 12px 16px; border-bottom: 1px solid var(--line); }
  .installation .itop .tabs { display: flex; gap: 6px; flex: 1 1 340px; flex-wrap: wrap; }
  .installation .itools { display: flex; gap: 6px; flex: 1 1 auto; flex-wrap: wrap; justify-content: flex-end; }
  .installation .ibody { padding: 12px 16px; display: grid; grid-template-columns: minmax(0, 1fr); gap: 16px; }
  .installation h3 { margin: 0 0 8px; font-size: 14px; font-weight: 500; }
  .installation .isub { color: var(--muted); font-size: 12px; }
  .installation .cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 10px; }
  .installation .gcard { border: 1px solid var(--line); border-radius: 12px; padding: 12px 14px; display: grid; gap: 6px; align-content: start; }
  .installation .gcard b { font-weight: 500; }
  .installation .gcard ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 4px; font-size: 13px; }
  .installation .gcard .open { font-size: 12px; color: var(--warn); }
  .installation .tablewrap { overflow-x: auto; }
  .installation table.itable { width: 100%; border-collapse: collapse; font-size: 13px; }
  .installation .itable th { text-align: left; font-weight: 500; font-size: 12px; color: var(--muted); padding: 6px 8px 6px 0; border-bottom: 1px solid var(--line); white-space: nowrap; }
  .installation .itable td { padding: 4px 8px 4px 0; border-bottom: 1px solid var(--line); vertical-align: middle; }
  .installation .itable td.name { min-width: 160px; }
  .installation .itable input.cell { width: 100%; min-width: 90px; box-sizing: border-box; font: inherit; font-size: 13px; padding: 4px 8px; border: 1px solid transparent; border-radius: 6px; background: transparent; color: inherit; }
  .installation .itable input.cell[data-in-field="location"], .installation .itable input.cell[data-in-field="note"] { min-width: 200px; }
  .installation .itable input.cell[data-in-field="group"] { min-width: 170px; }
  .installation .itable input.cell[data-in-field="bus_address"] { min-width: 70px; }
  .installation .itable input.cell[data-in-field="feedback_id"] { min-width: 100px; }
  .installation .itable input.cell[data-in-field="bus_power"] { min-width: 72px; max-width: 96px; text-align: right; }
  .installation .itable input.cell[data-in-field="bus_address"], .installation .itable input.cell[data-in-field="feedback_id"] { font-family: ui-monospace, monospace; font-size: 12px; }
  .installation .itable input.cell:hover { border-color: var(--line); }
  .installation .itable input.cell:focus { border-color: var(--accent); outline: none; background: var(--surface); }
  .installation .itable input.cell.bad { border-color: var(--warn); }
  .installation input.isearch { width: 100%; max-width: 320px; box-sizing: border-box; font: inherit; font-size: 13px; padding: 6px 10px; border: 1px solid var(--line); border-radius: 8px; background: transparent; color: inherit; }
  .installation .bulk { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; padding: 8px 12px; border: 1px solid var(--accent); border-radius: 10px; background: var(--accent-soft); }
  .installation .bulk input, .installation .bulk select { font: inherit; font-size: 13px; padding: 4px 8px; border: 1px solid var(--line); border-radius: 6px; background: var(--surface); color: inherit; }
  .installation textarea.paste { width: 100%; min-height: 90px; box-sizing: border-box; font: 12px ui-monospace, monospace; padding: 8px; border: 1px solid var(--line); border-radius: 8px; background: transparent; color: inherit; }
  .installation .log td.kind { white-space: nowrap; }
  .installation .none { color: var(--muted); padding: 8px 0; }
  .installation .itop { padding-bottom: 0; align-items: flex-end; }
  .installation .itop .itab { font-size: 15px; padding: 10px 14px 12px; }
  .installation .itop .itools { padding-bottom: 8px; }
  .installation .itop .groups { display: flex; gap: 4px; flex: 1 1 340px; flex-wrap: wrap; }
  .installation .itab { font: inherit; font-size: 14px; font-weight: 500; color: var(--muted); background: none; border: 0; border-bottom: 2px solid transparent; padding: 8px 12px 10px; margin-bottom: -1px; cursor: pointer; }
  .installation .itab:hover { color: var(--text); }
  .installation .itab[aria-selected="true"] { color: var(--accent); border-bottom-color: var(--accent); }
  .installation .itab:focus-visible { outline: 2px solid var(--accent); outline-offset: -2px; border-radius: 6px; }
  .installation .isubtabs { display: flex; gap: 4px; flex-wrap: wrap; padding: 10px 16px 0; }
  .installation .isubtabs .itab { font-size: 13px; font-weight: 400; padding: 5px 12px; margin: 0; border: 0; border-radius: 14px; }
  .installation .isubtabs .itab[aria-selected="true"] { background: var(--accent-soft); font-weight: 500; }
  .installation section.gw { border: 1px solid var(--line); border-radius: 12px; padding: 12px 14px 14px; display: grid; gap: 10px; min-width: 0; }
  .installation .gwhead { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; }
  .installation .gwhead h3 { margin: 0; }
  .installation .gbar { display: flex; align-items: center; gap: 10px; }
  .installation .ibody > p.isub { max-width: 100ch; margin: 0; }
  .installation .gcard { grid-template-columns: minmax(0, 1fr); }
  .installation .gcard li { white-space: normal; overflow-wrap: anywhere; }
  .installation .seg { display: inline-flex; border: 1px solid var(--line); border-radius: 16px; overflow: hidden; }
  .installation .seg button { font: inherit; font-size: 13px; color: var(--muted); background: none; border: 0; padding: 5px 14px; cursor: pointer; }
  .installation .seg button + button { border-left: 1px solid var(--line); }
  .installation .seg button[aria-pressed="true"] { background: var(--accent-soft); color: var(--accent); font-weight: 500; }
  .installation .gwempty { display: grid; justify-items: start; gap: 10px; padding: 8px 0 2px; color: var(--muted); font-size: 13px; }
  .installation .gwempty p { margin: 0; max-width: 60ch; }
  .installation details.poolbox { border-bottom: 1px solid var(--line); }
  .installation details.poolbox > summary { cursor: pointer; padding: 10px 16px; font-size: 14px; font-weight: 500; display: flex; gap: 8px; align-items: baseline; flex-wrap: wrap; }
  .installation details.poolbox > summary .isub { font-weight: 400; }
  .installation details.imenu { position: relative; }
  .installation details.imenu summary { list-style: none; cursor: pointer; }
  .installation details.imenu summary::-webkit-details-marker { display: none; }
  .installation .imenu .items { position: absolute; right: 0; z-index: 5; margin-top: 4px; min-width: 220px; display: grid; padding: 4px; background: var(--surface); border: 1px solid var(--line); border-radius: 10px; }
  .installation .imenu .items button { text-align: left; font: inherit; font-size: 13px; color: inherit; background: none; border: 0; border-radius: 6px; padding: 7px 10px; cursor: pointer; }
  .installation .imenu .items button:hover { background: var(--soft); }
  .installation .imenu .items hr { border: 0; border-top: 1px solid var(--line); margin: 4px 0; width: 100%; }
  .installation .itable td.num, .installation .itable th.num { text-align: right; white-space: nowrap; }
  .installation .itable tr.free td { color: var(--muted); background: var(--soft); font-size: 12px; padding: 3px 8px 3px 0; }
  .installation .itable td.mono, .installation .mono { font-family: ui-monospace, monospace; font-size: 12px; white-space: nowrap; }
  .installation .itable tr.outside td { font-weight: 500; color: var(--muted); border-top: 1px solid var(--line); }
  .installation .progress { display: flex; align-items: center; gap: 10px; font-size: 12px; color: var(--muted); }
  .installation .progress .barbg { flex: 1; max-width: 260px; height: 6px; border-radius: 3px; background: var(--soft); border: 1px solid var(--line); overflow: hidden; }
  .installation .progress .barbg i { display: block; height: 100%; background: var(--ok); }
  .installation .cerr { font-size: 11px; color: var(--warn); padding: 2px 8px; }
  .installation .tag { display: inline-block; padding: 1px 8px; border-radius: 10px; font-size: 11px; background: var(--soft); color: var(--muted); white-space: nowrap; }
  .installation .tag.warn { background: color-mix(in srgb, var(--warn) 18%, transparent); color: inherit; }
  .installation .tag.ok { background: color-mix(in srgb, var(--ok) 15%, transparent); color: inherit; }
  .installation .load { display: grid; grid-template-columns: minmax(120px, 220px) minmax(80px, 1fr) minmax(120px, 200px); gap: 10px; align-items: center; font-size: 13px; }
  .installation .load .barbg { height: 8px; border-radius: 4px; background: var(--soft); border: 1px solid var(--line); overflow: hidden; }
  .installation .load .barbg i { display: block; height: 100%; background: var(--accent); }
  .installation .load .barbg i.hot { background: var(--warn); }
  .installation .load .r { text-align: right; color: var(--muted); }
  .installation .notes p { margin: 2px 0; }
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
    const group = GROUPS.find((g) => g.tabs.includes(state.tab)) ?? GROUPS[0];
    state.last[group.id] = state.tab;
    const tab = (name, label, selected) => `<button class="itab" role="tab" data-in-tab="${name}" aria-selected="${selected}" tabindex="${selected ? 0 : -1}">${esc(label)}</button>`;
    const groups = GROUPS.map((g) => tab(state.last[g.id] ?? g.tabs[0], t.inst.groups[g.id], g === group)).join("");
    const subtabs = group.tabs.length > 1 ? `<div class="isubtabs" role="tablist">${group.tabs.map((name) => tab(name, t.inst.tabs[name], state.tab === name)).join("")}</div>` : "";
    const item = (act, icon, label) => `<button data-in-act="${act}">${esc(label)}</button>`;
    const tools = `<button class="chip" data-in-act="print">${svg(ICON.print)}${esc(t.inst.print)}</button>
      <details class="imenu"><summary class="chip">${svg(ICON.download)}${esc(t.inst.output)}</summary><div class="items">${item("csv", "", t.inst.csvDevices)}${item("csv-tables", "", t.inst.links.tablesCsv)}${item("csv-links", "", t.inst.links.csvShort)}<hr>${item("json", "", "JSON")}</div></details>
      <button class="chip" data-in-act="import">${svg(ICON.upload)}${esc(t.inst.import)}</button>`;
    const body = { areas: () => this._instAreas(), devices: () => this._instDevices(), gwsenders: () => this._instSenders(), buttons: () => this._instButtons(), radio: () => this._instRadio(), bus: () => this._instBus(), supplies: () => this._instSupplies(), links: () => this._instLinks(), log: () => this._instLog() }[state.tab]();
    this._setManage();
    this._replace(head, `<div class="itop"><div class="groups" role="tablist">${groups}</div><div class="itools">${tools}</div></div>${subtabs}`);
    this._replace(el, `<div class="ibody">${body}</div>`);
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
        return `<tr><td class="mono">${r.nr}</td><td class="mono">${esc(r.id)}</td><td>${esc(r.fn)}</td><td>${esc(r.device)}</td><td>${esc([r.name, r.place].filter(Boolean).join(", "))}</td><td>${this._instCell(gw, r.key, "bus_address", r.bus, T.busAddress, "1–126")}</td><td>${this._instCell(gw, r.key, "feedback_id", r.feedback, T.feedbackId, "00000081")}</td><td><span class="tag">${esc(r.use)}</span></td><td class="mono">${esc(r.second)}</td></tr>`;
      }).join("");
      const outside = externals.length
        ? `<tr class="outside"><td colspan="9">${esc(T.external)}</td></tr>${externals.map((r) => `<tr><td class="mono">–</td><td class="mono">${esc(r.id)}</td><td></td><td>${esc(r.device)}</td><td>${esc(r.name)}</td><td></td><td></td><td><span class="tag">${esc(r.use)}</span></td><td class="mono">${esc(r.second)}</td></tr>`).join("")}`
        : "";
      return body + outside;
    };
    const head = [T.nr, T.senderId, T.function, T.device, T.description, T.busAddress, T.feedbackId, T.use, T.second];
    return `<p class="isub">${esc(T.sendersIntro)} ${esc(t.inst.editHint)}</p>` + this._instPerGateway((gw, parts) => (parts.senders.length || parts.externals.length ? this._instTable(head, rows(gw, parts.senders, parts.externals)) : ""));
  },

  _instButtons() {
    const t = this._t;
    const T = t.doc.tbl;
    const side = (list) => (list.length ? list.map(esc).join("<br>") : `<span class="isub">${esc(T.unassigned)}</span>`);
    const head = [T.id, T.device, T.place, T.description, T.left, T.right];
    return `<p class="isub">${esc(T.buttonsIntro)} ${esc(t.inst.editHint)}</p>` + this._instPerGateway((gw, parts) => (parts.buttons.length ? this._instTable(head, parts.buttons.map((b) => `<tr><td class="mono">${esc(b.id)}</td><td>${esc(b.device)}</td><td>${b.key ? this._instCell(gw, b.key, "location", b.location, T.place, b.area) : esc(b.place)}</td><td>${esc(b.name)}</td><td>${side(b.left)}</td><td>${side(b.right)}</td></tr>`).join("")) : ""));
  },

  _instRadio() {
    const t = this._t;
    const T = t.doc.tbl;
    const head = [T.id, T.device, T.name, T.place, T.partOf, T.eep, T.sends];
    const rows = (gw, radio) => radio.map((r) => `<tr><td class="mono">${esc(r.id)}</td><td>${esc(r.device)}</td><td>${esc(r.key ? r.own : r.description)}</td><td>${r.key ? this._instCell(gw, r.key, "location", r.location, T.place, r.area) : esc(r.place)}</td><td>${r.key ? this._instCell(gw, r.key, "group", r.partOf, T.partOf) : ""}</td><td class="mono">${esc(r.eep)}</td><td>${esc(r.key ? r.category : r.sends)}</td></tr>`).join("");
    const manual = this._gateways.filter((g) => g.loaded).map((g) => this._manualEditor(g)).join("");
    return `<p class="isub">${esc(T.radioIntro)} ${esc(t.inst.editHint)}</p>` + this._instPerGateway((gw, parts) => (parts.radio.length ? this._instTable(head, rows(gw, parts.radio)) : "")) + manual;
  },

  _instBus() {
    const t = this._t;
    const T = t.doc.tbl;
    const lang = this._hass?.language || "en";
    const num = (n) => `${n.toLocaleString(lang, { maximumFractionDigits: 2 })} W`;
    return `<p class="isub">${esc(T.busIntro.replace(" (*)", ""))} ${esc(t.inst.editHint)}</p>` + this._instPerGateway((gw) => {
      const bus = docBus(gw, t, this._in.doc.bus_info);
      if (!bus.rows.length) return `<div class="none">${esc(T.busEmpty)}</div>`;
      const power = (r) => (r.from === "group" ? `<span class="isub">${esc(T.busGroupLine)}</span>` : r.power === null ? `<span class="tag warn">${esc(T.noValue)}</span>` : `${esc(num(r.power))}${r.from === "table" ? ` <span class="tag" title="${esc(bus.source)}">${esc(T.busSourceTableShort)}</span>` : ""}`);
      const rows = bus.items.map((r) => (r.free
        ? `<tr class="free"><td class="mono">${r.from === r.to ? r.from : `${r.from} – ${r.to}`}</td><td colspan="5">${esc(T.free)}</td></tr>`
        : `<tr><td class="mono">${r.address}</td><td>${esc(r.type)}</td><td>${esc(r.device)}</td><td>${esc([r.name, r.group && r.group !== r.name ? r.group : ""].filter(Boolean).join(", "))}</td><td>${this._instCell(gw, r.key, "feedback_id", r.feedback, T.feedbackId, "00000081")}</td><td class="num">${r.key ? `<span style="display:inline-flex;gap:6px;align-items:center;justify-content:flex-end">${this._instCell(gw, r.key, "bus_power", r.raw, `${T.power} (W)`, r.table !== null ? String(r.table).replace(".", ",") : "W")}${r.from === "table" ? `<span class="tag" title="${esc(bus.source)}">${esc(T.busSourceTableShort)}</span>` : r.from === "group" ? `<span class="isub">${esc(T.busGroupLine)}</span>` : r.power === null ? `<span class="tag warn">${esc(T.noValue)}</span>` : ""}</span>` : power(r)}</td></tr>`)).join("");
      const sum = `<tr><td colspan="5"><b>${esc(T.busSum(bus.counted, bus.rows.length))}</b></td><td class="num"><b>${esc(num(bus.sum))}</b></td></tr>`;
      const load = (name, capacity, percent, text) => `<div class="load"><span>${esc(name)}</span><div class="barbg"><i class="${percent >= 80 ? "hot" : ""}" style="width:${Math.min(percent ?? 0, 100)}%"></i></div><span class="r">${esc(text)}${percent >= 80 ? ` <span class="tag warn">${esc(T.busWarn)}</span>` : ""}</span></div>`;
      const range = (x) => (x.first !== null || x.last !== null ? `, ${T.supplyRange(x.first ?? 1, x.last ?? 126)}` : "");
      const bars = bus.supplies.filter((x) => x.percent !== null).map((x) => load(`${x.name || T.supplyNoName}, ${num(x.capacity ?? 0)}${range(x)}`, x.capacity, x.percent, `${num(x.load)} · ${x.percent} %`)).join("");
      const total = bus.capacity !== null && (bus.supplies.length > 1 || bus.supplies.some((x) => x.percent === null)) ? load(T.supplyTotal, bus.capacity, bus.percent, `${num(bus.sum)} ${t.inst.of} ${num(bus.capacity)} · ${bus.percent} %`) : "";
      const notes = [
        bus.rows.length - bus.counted ? T.busMissing(bus.rows.length - bus.counted) : "",
        bus.fromTable ? T.busFromTable(bus.source).replace(/^\* /, "") : "",
        bus.dups.length ? T.busDup(bus.dups.join(", ")) : "",
        bus.multi.length ? T.busMulti(bus.multi.join(", ")) : "",
        bus.unfed.length ? T.busUnfed(bus.unfed.join(", ")) : "",
      ].filter(Boolean).map((n) => `<p class="isub">${esc(n)}</p>`).join("");
      return this._instTable([T.busAddress, T.type, T.device, T.description, T.feedbackId, T.power], rows + sum) + `<div style="display:grid;gap:6px;margin-top:12px">${bars}${total}</div><div class="notes" style="margin-top:8px">${notes}</div>`;
    });
  },

  _instSupplies() {
    const t = this._t;
    const gw = this._gateways.filter((g) => g.loaded);
    return `<p class="isub">${esc(t.doc.supplyHint)}</p>` + (gw.map((g) => `<section class="gw">${this._instGwHead(g)}${this._manualEditor(g, "supply")}</section>`).join("") || `<div class="none">${esc(t.inst.noDevices)}</div>`);
  },

  _instAreas() {
    const t = this._t;
    const state = this._in;
    const seg = (group, label) => `<button data-in-group="${group}" aria-pressed="${state.group === group}">${esc(label)}</button>`;
    const groupBy = `<div class="gbar"><span class="isub">${esc(t.inst.groupBy)}</span><div class="seg" role="group">${seg("area", t.inst.byArea)}${seg("location", t.inst.byPlace)}</div></div>`;
    const sections = gateways(state.doc).map((gw) => {
      const groups = new Map();
      for (const d of gw.devices) {
        const key = (state.group === "area" ? d.area : d.location) || t.inst.noGroup;
        groups.set(key, [...(groups.get(key) ?? []), d]);
      }
      const cards = [...groups.entries()]
        .sort(([a], [b]) => (a === t.inst.noGroup) - (b === t.inst.noGroup) || a.localeCompare(b))
        .map(([name, devices]) => {
          const todo = devices.filter(open).length;
          const items = devices.map((d) => `<li>${esc(d.name)} <span class="isub">${esc(d.id)}${d.virtual ? ` · ${esc(t.doc.virtual)}` : ""}${d.location && state.group === "area" ? ` · ${esc(d.location)}` : ""}</span></li>`).join("");
          return `<div class="gcard"><b>${esc(name)}</b><ul>${items}</ul>${todo ? `<span class="open">${esc(t.inst.openItems(todo))}</span>` : ""}</div>`;
        })
        .join("");
      return `<section class="gw">${this._instGwHead(gw, gw.devices.length)}${cards ? `<div class="cards">${cards}</div>` : this._instEmpty(gw)}</section>`;
    });
    return groupBy + sections.join("");
  },

  _instDevices() {
    const t = this._t;
    const state = this._in;
    const columns = INSTALLATION_FIELDS.filter((f) => Object.entries(COLUMN_GROUPS).some(([g, fields]) => state.columns.has(g) && fields.includes(f)));
    const key = (gw, d) => `${gw.entry_id}|${d.key}`;
    const search = `<input class="isearch" data-in-search value="${esc(state.q)}" placeholder="${esc(t.inst.search)}" aria-label="${esc(t.inst.search)}">`;
    const sections = gateways(state.doc).map((gw) => {
      const devices = gw.devices.filter((d) => matches(d, state.q));
      const rows = devices
        .map((d) => {
          const cells = columns
            .map((f) => `<td><input class="cell" ${f === "installed" ? 'type="date"' : ""} data-in-field="${f}" data-in-gw="${esc(gw.entry_id)}" data-in-key="${esc(d.key)}" value="${esc(d[f] ?? "")}" placeholder="${esc(label(t, f))}" aria-label="${esc(label(t, f))}: ${esc(d.name)}" autocomplete="off"></td>`)
            .join("");
          const picked = state.selected.has(key(gw, d));
          return `<tr><td><input type="checkbox" data-in-pick="${esc(key(gw, d))}" ${picked ? "checked" : ""} aria-label="${esc(d.name)}"></td><td class="name">${esc(d.name)}<div class="isub">${esc(d.id)}${d.area ? ` · ${esc(d.area)}` : ""}</div></td>${cells}</tr>`;
        })
        .join("");
      const head = columns.map((f) => `<th>${esc(label(t, f))}</th>`).join("");
      return `<section class="gw">${this._instGwHead(gw, devices.length)}<div class="tablewrap"><table class="itable"><thead><tr><th></th><th>${esc(t.inst.device)}</th>${head}</tr></thead><tbody>${rows || `<tr><td colspan="${columns.length + 2}" class="none">${esc(t.inst.noDevices)}</td></tr>`}</tbody></table></div></section>`;
    });
    const picked = state.selected.size;
    const bulk = picked
      ? `<div class="bulk"><b>${esc(t.inst.selected(picked))}</b><select data-in-bulk-field aria-label="${esc(t.inst.setField)}">${INSTALLATION_FIELDS.map((f) => `<option value="${f}">${esc(label(t, f))}</option>`).join("")}</select><input data-in-bulk-value placeholder="${esc(t.inst.value)}" aria-label="${esc(t.inst.value)}"><button class="chip" data-in-act="bulk">${esc(t.inst.apply)}</button><button class="chip" data-in-act="unpick">${esc(t.inst.clearSelection)}</button></div>`
      : "";
    const paste = `<details><summary>${esc(t.inst.pasteTitle)}</summary><div style="display:grid;gap:8px;margin-top:8px"><span class="isub">${esc(t.inst.pasteHint)}</span><textarea class="paste" data-in-paste placeholder="${esc(t.inst.pastePlaceholder)}" aria-label="${esc(t.inst.pasteTitle)}">${esc(state.paste)}</textarea><div><button class="chip" data-in-act="paste">${esc(t.inst.apply)}</button> <button class="chip" data-in-act="copy-table">${esc(t.inst.copyTable)}</button> <span class="isub">${esc(state.pasteResult)}</span></div></div></details>`;
    const groupChips = Object.keys(COLUMN_GROUPS).map((g) => `<button class="chip" data-in-columns="${g}" aria-pressed="${state.columns.has(g)}">${esc(t.inst.columnGroups[g])}</button>`).join("");
    const all = gateways(state.doc).flatMap((gw) => gw.devices).filter((d) => !d.virtual);
    const placed = all.filter((d) => d.location).length;
    const progress = all.length
      ? `<div class="progress"><span>${esc(t.inst.progress(placed, all.length))}</span><div class="barbg"><i style="width:${Math.round((placed / all.length) * 100)}%"></i></div><span>${Math.round((placed / all.length) * 100)} %</span></div>`
      : "";
    return `${progress}<div class="itools" style="align-items:center"><span class="isub">${esc(t.inst.columns)}</span>${groupChips}<span style="flex:1"></span>${search}</div>${bulk}${sections.join("")}${paste}`;
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
      const options = [...gw.devices.filter((d) => !d.virtual).map((d) => `<option value="${esc(d.note_key)}">${esc(d.name)} · ${esc(d.id)}</option>`), `<option value="">${esc(L.otherTarget)}</option>`].join("");
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
    if (this._manualEdit(e)) return; // the rows of power supplies and entries by hand
    const tab = e.target.closest("[data-in-tab]");
    if (tab) {
      state.tab = tab.dataset.inTab;
      this._renderInstallation();
      if (this._managing()) this._loadPools();
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
    const columns = e.target.closest("[data-in-columns]");
    if (columns) {
      const name = columns.dataset.inColumns;
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
    const group = e.target.closest("[data-in-group]");
    if (group) {
      state.group = group.dataset.inGroup;
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
    else if (act === "add-link") this._instAddLink(e.target.closest("[data-in-act]").dataset.inGw);
  },

  _installationChange(e) {
    const pick = e.target.closest("[data-in-pick]");
    if (!pick) return;
    const selected = this._in.selected;
    if (pick.checked) selected.add(pick.dataset.inPick);
    else selected.delete(pick.dataset.inPick);
    this._renderInstallation();
  },

  _installationInput(e) {
    const state = this._in;
    if (this._manualEdit(e)) return;
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
