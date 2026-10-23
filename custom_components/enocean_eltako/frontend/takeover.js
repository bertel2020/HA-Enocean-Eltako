// The Takeover view of the panel, in four steps: select the devices of the old eltako
// integration, choose what comes along and confirm, switch the old entity IDs over where they
// are used, clean up. The mapping of old to new IDs is kept by the integration as a report,
// which stays readable once the takeover is finished (opened from the Devices view).
// Its methods are added to the panel class (this = the panel).

const VERSION = new URL(import.meta.url).search;
const { ICON, csv, esc, svg } = await import(`./shared.js${VERSION}`);

// where an old entity ID of the takeover mapping is still used
const USAGE_KINDS = ["automation", "script", "scene", "dashboard"];
const OLD_INTEGRATION = "/config/integrations/integration/eltako";
// an old ID that the new entity has got back is not in the way anywhere
const isUsed = (row) => !row.restored && USAGE_KINDS.some((k) => row.usage[k].length);
// what can be carried over from the old integration, each chosen on its own
const CARRY_OPTIONS = ["area", "labels", "voice", "names", "icons", "visibility"];
const CARRY_KEY = "enocean_eltako_takeover_carry"; // the chosen options, per browser
const STEPS = ["select", "carry", "switch", "cleanup"];

function loadCarry() {
  // nothing is carried over until it is chosen once; then the choice is remembered
  try {
    const saved = JSON.parse(localStorage.getItem(CARRY_KEY) || "[]");
    return new Set(Array.isArray(saved) ? saved.filter((o) => CARRY_OPTIONS.includes(o)) : []);
  } catch (err) {
    return new Set();
  }
}

function saveCarry(carry) {
  try {
    localStorage.setItem(CARRY_KEY, JSON.stringify([...carry]));
  } catch (err) {
    // private window or blocked storage: the choice just is not remembered
  }
}

// the view's state when the panel starts
export const takeoverState = () => ({
  entry: "", tab: "", preview: null, previewError: "", mapping: null, selected: new Set(), carry: loadCarry(),
  open: new Set(), busy: false, mfilter: "used", mview: "place", later: false, q: "", folded: new Set(),
  showNot: false, report: false, archive: false,
});

export const TAKEOVER_STYLE = `
  .takeover { padding-bottom: 8px; }
  .takeover .steps { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); border-bottom: 1px solid var(--line); }
  .takeover .step { display: flex; gap: 8px; align-items: flex-start; text-align: left; font: inherit; font-size: 12px; color: var(--muted);
    background: none; border: 0; border-bottom: 2px solid transparent; padding: 12px 14px 10px; cursor: pointer; }
  .takeover .step:hover:not(:disabled) b { color: var(--accent); }
  .takeover .step:disabled { cursor: default; opacity: .55; }
  .takeover .step.cur { border-bottom-color: var(--accent); }
  .takeover .step b { display: block; font-weight: 500; font-size: 13px; color: var(--text); }
  .takeover .num { flex: none; width: 22px; height: 22px; border-radius: 50%; border: 1px solid var(--line); display: flex; align-items: center; justify-content: center; font-size: 12px; }
  .takeover .step.cur .num { border-color: var(--accent); color: var(--accent); background: color-mix(in srgb, var(--accent) 10%, var(--surface)); }
  .takeover .step.done .num { border-color: var(--ok); color: var(--ok); background: color-mix(in srgb, var(--ok) 15%, var(--surface)); }
  .takeover .step.warn .num { border-color: var(--warn); color: var(--warn); }
  .takeover .archive-head { display: flex; flex-wrap: wrap; gap: 8px 12px; align-items: center; padding: 12px 16px; border-bottom: 1px solid var(--line); }
  .takeover .archive-head b { flex: 1; font-size: 15px; font-weight: 500; }
  .takeover .toolbar { padding: 10px 16px; display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
  /* filter pills and search as in the other views */
  .takeover .pill { height: 32px; padding: 0 14px; border-radius: 20px; border: 1px solid var(--input-line); font-size: 13px; font-weight: 500; color: var(--accent); background: var(--surface); white-space: nowrap; cursor: pointer; }
  .takeover .pill:hover { background: var(--accent-soft); }
  .takeover .pill[aria-pressed="true"] { border-color: var(--accent); color: var(--accent-hover); background: var(--accent-soft); }
  .takeover .search { flex: 1; min-width: 140px; height: 38px; border-radius: 10px; border: 1px solid var(--input-line); background: var(--surface);
    color: var(--text); font: inherit; font-size: 14px; padding: 0 12px; }
  .takeover .banner { margin: 0 16px 10px; padding: 8px 12px; border-radius: 8px; font-size: 12px; background: color-mix(in srgb, var(--warn) 18%, transparent); }
  .takeover .banner.ok { background: color-mix(in srgb, var(--ok) 15%, transparent); }
  .takeover .counts { display: flex; flex-wrap: wrap; gap: 6px; padding: 12px 16px 0; }
  .takeover .group { display: flex; gap: 10px; align-items: center; padding: 7px 16px; border-top: 1px solid var(--line); background: var(--soft); font-size: 12px; }
  .takeover .group .sub { margin-left: auto; }
  .takeover .fold { font: inherit; font-weight: 500; color: var(--text); background: none; border: 0; padding: 0; cursor: pointer; text-align: left; }
  .takeover .pickrow { display: flex; gap: 10px; align-items: center; padding: 7px 16px 7px 40px; border-top: 1px solid var(--line); font-size: 13px; cursor: pointer; }
  .takeover .pick-name { flex: 1; min-width: 0; }
  .takeover .sub { color: var(--muted); font-size: 12px; }
  .takeover .skiprow { display: flex; justify-content: space-between; gap: 12px; padding: 6px 16px 6px 40px; font-size: 13px; color: var(--muted); border-top: 1px solid var(--line); }
  .takeover .stepbar { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 8px 12px; padding: 10px 16px;
    border-top: 1px solid var(--line); background: var(--soft); position: sticky; bottom: 0; }
  .takeover .stepbar .left { display: flex; flex-wrap: wrap; gap: 6px 12px; align-items: center; font-size: 13px; }
  .takeover .section { padding: 14px 16px; border-top: 1px solid var(--line); }
  .takeover .section:first-child { border-top: 0; }
  .takeover .section h3 { margin: 0 0 10px; font-size: 14px; font-weight: 500; }
  .takeover .section h3 .sub { font-weight: 400; }
  .takeover .optcards { display: grid; grid-template-columns: repeat(auto-fill, minmax(210px, 1fr)); gap: 8px; }
  .takeover .optcard { display: flex; gap: 10px; align-items: flex-start; padding: 9px 12px; border: 1px solid var(--input-line); border-radius: 10px; cursor: pointer; font-size: 13px; }
  .takeover .optcard b { display: block; font-weight: 500; }
  .takeover .optcard:has(input:checked) { border-color: var(--accent); background: var(--accent-soft); }
  .takeover .optcard.off { cursor: default; opacity: .55; }
  .takeover .optcard input { margin-top: 2px; }
  .takeover .note { margin: 8px 0 0; font-size: 12px; color: var(--muted); }
  .takeover .opts { display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 4px 16px; }
  .takeover .opt { display: flex; gap: 6px; align-items: center; color: var(--text); font-size: 12px; }
  .takeover .opt small { margin-left: auto; color: var(--muted); }
  .takeover .opt.off { color: var(--muted); }
  .takeover .idtable { width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 12px; }
  .takeover .idtable th { text-align: left; font-weight: 500; color: var(--muted); padding: 6px 8px; border-bottom: 1px solid var(--line); }
  .takeover .idtable td { padding: 5px 8px; border-bottom: 1px solid var(--line); overflow-wrap: anywhere; vertical-align: top; }
  .takeover .idtable td.dev { font-size: 13px; }
  .takeover .idtable tr.first td { border-top: 1px solid var(--line); }
  .takeover .old { color: var(--muted); }
  .takeover .later { padding: 10px 16px; border-top: 1px solid var(--line); background: var(--soft); display: grid; gap: 8px; font-size: 12px; }
  .takeover .later-head { display: flex; flex-wrap: wrap; gap: 6px 12px; align-items: center; }
  .takeover .later-head .sub { flex: 1; }
  .takeover .later > .chip { justify-self: start; }
  .takeover .seg { display: inline-flex; border: 1px solid var(--input-line); border-radius: 20px; overflow: hidden; }
  .takeover .seg button { height: 32px; padding: 0 12px; font: inherit; font-size: 13px; color: var(--muted); background: var(--surface); border: 0; cursor: pointer; }
  .takeover .seg button[aria-pressed="true"] { color: var(--accent-hover); background: var(--accent-soft); font-weight: 500; }
  .takeover .link { font: inherit; font-weight: 500; color: var(--accent); background: none; border: 0; padding: 0; cursor: pointer; }
  .takeover .link:hover { color: var(--accent-hover); text-decoration: underline; }
  .takeover .devblock { border-top: 1px solid var(--line); }
  .takeover .devhead { display: flex; flex-wrap: wrap; gap: 4px 10px; align-items: center; padding: 8px 16px; font-size: 13px; }
  .takeover .devhead[data-tk-open] { cursor: pointer; }
  .takeover .devhead[data-tk-open]:hover { background: color-mix(in srgb, var(--soft) 60%, transparent); }
  .takeover .devhead b { font-weight: 500; }
  .takeover .devchips { display: flex; flex-wrap: wrap; }
  .takeover .devstate { margin-left: auto; display: flex; gap: 8px; align-items: center; }
  .takeover .ents { padding: 0 16px 8px 34px; }
  .takeover .ent { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 4px 12px; padding: 6px 0; border-top: 1px dashed var(--line); font-size: 12px; overflow-wrap: anywhere; }
  .takeover .olddl { display: grid; grid-template-columns: 150px minmax(0, 1fr); gap: 4px 12px; margin: 0 0 6px; padding: 8px 12px; border-radius: 8px; background: var(--soft); font-size: 12px; }
  .takeover .olddl dt { color: var(--muted); }
  .takeover .olddl dd { margin: 0; overflow-wrap: anywhere; }
  .takeover .olddl .title { grid-column: 1 / -1; font-weight: 500; color: var(--text); }
  .takeover .chip-s { display: inline-block; font-size: 11px; padding: 1px 7px; border-radius: 999px; margin: 0 4px 2px 0; background: var(--soft); color: var(--text); }
  .takeover .chip-s.used { background: color-mix(in srgb, var(--warn) 25%, transparent); }
  .takeover .chip-s.ok { background: color-mix(in srgb, var(--ok) 20%, transparent); }
  .takeover .chip-s.avail { color: var(--muted); border: 1px dashed var(--line); background: none; }
  .takeover button.chip-s { font: inherit; font-size: 11px; border: 0; cursor: pointer; text-align: left; }
  .takeover button.chip-s:hover { text-decoration: underline; }
  .takeover .check { display: flex; gap: 12px; align-items: flex-start; padding: 12px 16px; border-top: 1px solid var(--line); font-size: 13px; }
  .takeover .check:first-child { border-top: 0; }
  .takeover .check > span:nth-child(2) { flex: 1; min-width: 0; }
  .takeover .check b { display: block; font-weight: 500; }
  .takeover .mark { flex: none; width: 22px; height: 22px; border-radius: 50%; border: 1px solid var(--line); display: flex; align-items: center; justify-content: center; font-size: 12px; color: var(--muted); }
  .takeover .mark.ok { border-color: var(--ok); color: var(--ok); background: color-mix(in srgb, var(--ok) 15%, var(--surface)); }
  .takeover .mark.warn { border-color: var(--warn); color: var(--warn); }
  @media (max-width: 760px) {
    /* the steps two by two, name and state below each other */
    .takeover .steps { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .takeover .ent { grid-template-columns: minmax(0, 1fr); }
    .takeover .olddl { grid-template-columns: minmax(0, 1fr); gap: 0 12px; }
    .takeover .olddl dd { margin-bottom: 4px; }
    .takeover .idtable, .takeover .idtable tbody { display: block; }
    .takeover .idtable colgroup, .takeover .idtable thead { display: none; }
    .takeover .idtable tr { display: grid; grid-template-columns: minmax(0, 1fr); }
    .takeover .idtable td { border-bottom: 0; padding: 2px 8px; }
    .takeover .idtable tr { border-bottom: 1px solid var(--line); padding: 4px 0; }
    .takeover .stepbar .chip.primary { flex: 1; justify-content: center; }
    .takeover .check { flex-wrap: wrap; }
    .takeover .check > .chip { margin-left: 34px; }
  }
`;

export const takeover = {
  async _checkTakeover() {
    // the Takeover view exists while there is something to take over or to switch over and
    // until it is finished; the report stays reachable from the Devices view
    try {
      const status = await this._hass.callWS({ type: "enocean_eltako/takeover/status" });
      const tk = this._tk;
      tk.report = !!status.report;
      if (status.available) tk.archive = false;
      const button = this.shadowRoot.querySelector('#view button[data-view="takeover"]');
      if (button) button.hidden = !status.available;
      const report = this.shadowRoot.getElementById("tkReport");
      if (report) report.hidden = !tk.report;
      if (!status.available && this._view === "takeover" && !(tk.archive && tk.report)) this._setView("telegrams");
    } catch (err) {
      // not an admin or the integration is still starting: no view
    }
  },

  _openReport() {
    // the report after the takeover is finished: the same view, without the steps
    const tk = this._tk;
    tk.archive = true;
    tk.tab = "switch";
    tk.mview = "report";
    this._setView("takeover");
  },

  _tkGateways() {
    return this._gateways.filter((g) => g.loaded);
  },

  async _loadTakeover() {
    const tk = this._tk;
    const gateways = this._tkGateways();
    if (!gateways.some((g) => g.entry_id === tk.entry)) tk.entry = gateways[0]?.entry_id || "";
    if (!tk.entry) {
      this._renderTakeover();
      return;
    }
    tk.previewError = "";
    const [preview, mapping] = await Promise.allSettled([
      this._hass.callWS({ type: "enocean_eltako/takeover/preview", entry_id: tk.entry }),
      this._hass.callWS({ type: "enocean_eltako/takeover/mapping", entry_id: tk.entry }),
    ]);
    tk.preview = preview.status === "fulfilled" ? preview.value : null;
    tk.previewError = preview.status === "rejected" ? preview.reason?.code || "unknown" : "";
    tk.mapping = mapping.status === "fulfilled" ? mapping.value : null;
    const ready = this._tkDevices().filter((d) => d.ready);
    tk.selected = new Set(ready.map((d) => d.id));
    // opened: the first step with something left to do
    if (!STEPS.includes(tk.tab)) {
      const rows = tk.mapping?.rows || [];
      tk.tab = ready.length ? "select" : rows.some(isUsed) ? "switch" : rows.length ? "cleanup" : "select";
    }
    this._renderTakeover();
  },

  async _tkRecheck() {
    // the mapping again, after references were switched over elsewhere
    const tk = this._tk;
    try {
      tk.mapping = await this._hass.callWS({ type: "enocean_eltako/takeover/mapping", entry_id: tk.entry });
    } catch (err) {
      this._notice(this._t.tkErrors[err.code] || this._t.tkErrors.unknown);
    }
    this._renderTakeover();
  },

  _tkDevices() {
    // an ID listed twice in the old configuration: the first entry is the device
    const seen = new Map();
    for (const d of this._tk.preview?.devices || []) if (!seen.has(d.id)) seen.set(d.id, d);
    return [...seen.values()];
  },

  _tkBlocks(rows) {
    // the mapping's rows by device, in their order
    const blocks = new Map();
    for (const r of rows) {
      if (!blocks.has(r.id)) blocks.set(r.id, []);
      blocks.get(r.id).push(r);
    }
    return blocks;
  },

  _tkPlaceCount(rows) {
    return new Set(rows.filter((r) => !r.restored).flatMap((r) => USAGE_KINDS.flatMap((k) => r.usage[k].map((p) => `${k}:${p.name}`)))).size;
  },

  _tkCleanup() {
    // the checklist of the last step, each item found from the current state
    const tk = this._tk;
    const rows = tk.mapping?.rows || [];
    const ready = this._tkDevices().filter((d) => d.ready).length;
    const stored = Object.keys(tk.mapping?.devices || {}).length;
    const oldGone = !(tk.mapping?.old_active ?? tk.preview?.old_active) && !tk.mapping?.old_entities;
    return {
      ready, stored, oldGone, places: this._tkPlaceCount(rows),
      yamlGone: tk.previewError === "no_config",
      restorable: rows.some((r) => r.taken && r.new && !r.restored && r.new !== r.old),
      restored: rows.filter((r) => r.restored).length,
    };
  },

  _renderTakeover() {
    const t = this._t;
    const tk = this._tk;
    const container = this.shadowRoot.getElementById("takeover");
    const gateways = this._tkGateways();
    if (!gateways.length) {
      this._replace(container, this._noGateway());
      return;
    }
    const select = gateways.length > 1
      ? `<select class="select" id="tkGateway" aria-label="${esc(t.gateway)}">${gateways
          .map((g) => `<option value="${esc(g.entry_id)}"${g.entry_id === tk.entry ? " selected" : ""}>${esc(g.title)}</option>`)
          .join("")}</select>`
      : "";
    if (tk.archive) {
      const head = `<div class="archive-head"><b>${esc(t.tkReportTitle)}</b>${select}<button class="chip" data-tk-devices>${esc(t.tkReportBack)}</button></div>`;
      this._replace(container, head + this._renderSwitch("", true));
      return;
    }
    const devices = this._tkDevices();
    const ready = devices.filter((d) => d.ready);
    const chosen = ready.filter((d) => tk.selected.has(d.id));
    const rows = tk.mapping?.rows || [];
    const places = this._tkPlaceCount(rows);
    const clean = this._tkCleanup();
    const doneCount = [!clean.ready, clean.stored > 0, !clean.places, clean.oldGone, clean.yamlGone].filter(Boolean).length;
    const st = t.tkStepState;
    const steps = [
      { text: ready.length ? st.open(ready.length) : st.none, done: !ready.length && rows.length > 0 },
      { text: chosen.length ? st.chosen(chosen.length) : st.nothing, off: !ready.length },
      { text: !rows.length ? st.waiting : places ? st.places(places) : st.clear, done: rows.length > 0 && !places, warn: places > 0, off: !rows.length },
      { text: st.cleanup(doneCount, 5), done: doneCount === 5, warn: rows.length > 0 && doneCount < 5 },
    ];
    const stepsHtml = steps
      .map((s, i) => {
        const cur = STEPS[i] === tk.tab;
        const cls = `step${s.done ? " done" : s.warn ? " warn" : ""}${cur ? " cur" : ""}`;
        return `<button class="${cls}" data-tk-tab="${STEPS[i]}"${cur ? ' aria-current="step"' : ""}${s.off ? " disabled" : ""}>
          <span class="num">${s.done ? "✓" : i + 1}</span><span><b>${esc(t.tkSteps[i])}</b>${esc(s.text)}</span></button>`;
      })
      .join("");
    const body = {
      select: () => this._renderSelect(devices, ready, chosen, select),
      carry: () => this._renderCarry(chosen),
      switch: () => this._renderSwitch(select, false),
      cleanup: () => this._renderCleanup(clean, select),
    }[tk.tab]();
    this._replace(container, `<div class="steps">${stepsHtml}</div>${body}`);
    container.querySelectorAll("[data-partial]").forEach((box) => { box.indeterminate = true; });
  },

  _tkMatches(...fields) {
    const q = this._tk.q.trim().toLowerCase();
    return !q || fields.some((f) => String(f || "").toLowerCase().includes(q));
  },

  _tkSearch() {
    const t = this._t;
    return `<input class="search" id="tkSearch" type="search" placeholder="${esc(t.tkSearch)}" value="${esc(this._tk.q)}" aria-label="${esc(t.tkSearch)}">`;
  },

  _tkGroups(list) {
    // devices by area, areas alphabetical, devices without an area last
    const groups = new Map();
    for (const d of list) {
      const key = d.area || "";
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(d);
    }
    return [...groups.entries()]
      .sort(([a], [b]) => (a === "") - (b === "") || a.localeCompare(b))
      .map(([area, items]) => ({ area, items: items.sort((x, y) => x.name.localeCompare(y.name)) }));
  },

  _tkCarryOptions(counts, attr) {
    // the compact form, for carrying over later: one checkbox per option with its count
    const t = this._t;
    return `<div class="opts">${CARRY_OPTIONS.map((o) => {
      const n = counts[o] || 0;
      return `<label class="opt${n ? "" : " off"}"><input type="checkbox" ${attr}="${o}"${this._tk.carry.has(o) ? " checked" : ""}${n ? "" : " disabled"}>${esc(t.tkCarryOpt[o])}<small>${n}</small></label>`;
    }).join("")}</div>`;
  },

  // ---- step 1: select ---------------------------------------------------------------------

  _renderSelect(devices, ready, chosen, select) {
    const t = this._t;
    const tk = this._tk;
    if (tk.previewError) {
      const text = t.tkErrors[tk.previewError] || t.tkErrors.unknown;
      return `${select ? `<div class="toolbar">${select}</div>` : ""}${this._emptyState(ICON.check, text, "", "", true)}`;
    }
    // devices already set up are not offered here: they are under Switch over
    const exists = devices.filter((d) => d.reason === "takeover_exists").length;
    const not = devices.filter((d) => !d.ready && d.reason !== "takeover_exists");
    const counts = `<div class="counts"><span class="chip-s">${esc(t.tkInYaml(devices.length))}</span>${
      exists ? `<button class="chip-s ok" data-tk-tab="switch" data-tk-mview="device">${esc(t.tkExisting(exists))}</button>` : ""
    }${not.length ? `<span class="chip-s">${esc(t.tkNotCount(not.length))}</span>` : ""}</div>`;
    const toolbar = `<div class="toolbar">${select}${this._tkSearch()}</div>`;
    const visible = ready.filter((d) => this._tkMatches(d.name, d.id, d.area, d.old, ...(d.labels || [])));
    let list;
    if (!ready.length) {
      list = this._emptyState(ICON.check, t.tkNothingLeft, "", "", true);
    } else if (!visible.length) {
      list = this._emptyState(ICON.search, t.tkNoMatch, "", "", true);
    } else {
      const q = tk.q.trim();
      list = this._tkGroups(visible)
        .map((g) => {
          const picked = g.items.filter((d) => tk.selected.has(d.id)).length;
          const folded = !q && tk.folded.has(g.area);
          const rowsHtml = folded
            ? ""
            : g.items
                .map((d) => `<label class="pickrow"><input type="checkbox" data-tk-pick="${esc(d.id)}"${tk.selected.has(d.id) ? " checked" : ""}>
                  <span class="pick-name">${esc(d.name)} <span class="sub mono">${esc(d.id)}</span><br><span class="sub">${esc(d.old || "")}</span></span>
                  ${d.used ? `<span class="chip-s used">${esc(t.tkPlaces(d.used))}</span>` : `<span class="chip-s">${esc(t.tkUnused)}</span>`}</label>`)
                .join("");
          return `<div class="group"><input type="checkbox" data-tk-group="${esc(g.area)}" aria-label="${esc(g.area || t.tkNoArea)}"${picked === g.items.length ? " checked" : ""}${picked && picked < g.items.length ? " data-partial" : ""}>
            <button class="fold" data-tk-fold="${esc(g.area)}" aria-expanded="${!folded}"><span aria-hidden="true">${folded ? "▸" : "▾"}</span> ${esc(g.area || t.tkNoArea)}</button>
            <span class="sub">${esc(t.tkGroupCount(picked, g.items.length))}</span></div>${rowsHtml}`;
        })
        .join("");
    }
    const notHtml = not.length
      ? `<div class="group"><button class="fold" data-tk-not aria-expanded="${tk.showNot}"><span aria-hidden="true">${tk.showNot ? "▾" : "▸"}</span> ${esc(t.tkNotCount(not.length))}</button></div>${
          tk.showNot
            ? not.map((d) => `<div class="skiprow"><span>${esc(d.name)} <span class="mono">${esc(d.id)}</span></span><span>${esc(t.tkReasons[d.reason] || d.reason || "")}</span></div>`).join("")
            : ""
        }`
      : "";
    const picked = chosen.length;
    const bar = ready.length
      ? `<div class="stepbar"><span class="left"><b>${esc(t.tkSelected(picked, ready.length))}</b>
          <button class="link" data-tk-all="${picked === ready.length ? "none" : "all"}">${esc(picked === ready.length ? t.tkSelectNone : t.tkSelectAll)}</button></span>
          <button class="chip primary" data-tk-tab="carry" ${picked ? "" : "disabled"}>${esc(t.tkNext.carry)}</button></div>`
      : "";
    return `${counts}${toolbar}${list}${notHtml}${bar}`;
  },

  // ---- step 2: carry over and confirm ---------------------------------------------------

  _tkCarryValues(o, having) {
    // what the old integration has for an option, as far as the preview names it
    if (o === "area") return [...new Set(having.map((d) => d.area).filter(Boolean))];
    if (o === "labels") return [...new Set(having.flatMap((d) => d.labels || []))];
    return [];
  },

  _renderCarry(chosen) {
    const t = this._t;
    const tk = this._tk;
    if (!chosen.length) {
      return this._emptyState(ICON.check, t.tkNoneChosen, "", `<button class="chip" data-tk-tab="select">${esc(t.tkBack)}</button>`, true);
    }
    const cards = CARRY_OPTIONS.map((o) => {
      const having = chosen.filter((d) => (d.carry || []).includes(o));
      const values = this._tkCarryValues(o, having);
      const n = having.length;
      const detail = n ? [values.slice(0, 3).join(", ") + (values.length > 3 ? " …" : ""), t.tkCarryOf(n, chosen.length)].filter(Boolean).join(" · ") : t.tkCarryNone;
      return `<label class="optcard${n ? "" : " off"}"><input type="checkbox" data-tk-carry="${o}"${tk.carry.has(o) && n ? " checked" : ""}${n ? "" : " disabled"}>
        <span><b>${esc(t.tkCarryOpt[o])}</b><span class="sub">${esc(detail)}</span></span></label>`;
    }).join("");
    const entities = chosen.reduce((n, d) => n + (d.entities || []).length, 0);
    const places = new Set(chosen.flatMap((d) => d.places || [])).size;
    const idRows = chosen
      .map((d) => {
        const list = d.entities?.length ? d.entities : [{ old: null, new: null }];
        return list
          .map((e, i) => `<tr class="${i ? "" : "first"}"><td class="dev">${i ? "" : `${esc(d.name)} <span class="sub mono">${esc(d.id)}</span>`}</td>
            <td class="mono old">${e.old ? esc(e.old) : esc(t.tkNoOldEntities)}</td>
            <td>${e.new ? `<span class="mono">${esc(e.new)}</span>` : e.old ? `<span class="old">${esc(t.tkNewLater)}</span>` : ""}</td></tr>`)
          .join("");
      })
      .join("");
    return `<div class="section"><h3>${esc(t.tkCarryTitle)}</h3><div class="optcards">${cards}</div><p class="note">${esc(t.tkCarryNote)}</p></div>
      <div class="section"><h3>${esc(t.tkPreview)} <span class="sub">· ${esc(t.tkPreviewSum(chosen.length, entities, places))}</span></h3>
        <table class="idtable"><colgroup><col style="width:26%"><col style="width:37%"><col style="width:37%"></colgroup>
          <thead><tr><th>${esc(t.tkColDevice)}</th><th>${esc(t.tkColOldEntity)}</th><th>${esc(t.tkColNewProbable)}</th></tr></thead><tbody>${idRows}</tbody></table>
        <p class="note">${esc(t.tkAfterwards(places))}</p></div>
      <div class="stepbar"><button class="chip" data-tk-tab="select">${esc(t.tkBack)}</button>
        <button class="chip primary" data-tk-confirm ${tk.busy ? "disabled" : ""}>${esc(tk.busy ? t.tkBusy : t.tkRun(chosen.length))}</button></div>`;
  },

  // ---- step 3: switch over (and the report) -----------------------------------------------

  _tkPlaceChip(kind, place) {
    // a place that uses an old ID; one with an editor opens it
    const label = `${this._t.tkKind[kind]}: ${place.name}`;
    return place.path
      ? `<button class="chip-s used place" data-tk-go="${esc(place.path)}" title="${esc(this._t.tkEdit)}">${esc(label)}</button>`
      : `<span class="chip-s used">${esc(label)}</span>`;
  },

  _renderSwitch(select, archive) {
    const t = this._t;
    const tk = this._tk;
    const rows = tk.mapping?.rows || [];
    if (!rows.length) return `${select ? `<div class="toolbar">${select}</div>` : ""}${this._emptyState(ICON.check, t.tkEmpty, "", "", true)}`;
    const views = archive ? ["device", "report", "place"] : ["place", "device", "report"];
    if (!views.includes(tk.mview)) tk.mview = views[0];
    const seg = `<span class="seg" role="group">${views
      .map((v) => `<button data-tk-mview="${v}" aria-pressed="${tk.mview === v}">${esc(t.tkByView[v])}</button>`)
      .join("")}</span>`;
    const blocks = this._tkBlocks(rows);
    const usedIds = new Set(rows.filter(isUsed).map((r) => r.id));
    let pills = "";
    if (tk.mview === "device") {
      const done = [...blocks.entries()].filter(([id, items]) => items[0].taken && !usedIds.has(id)).length;
      pills = [["used", t.tkFilterUsed, usedIds.size], ["done", t.tkFilterDone, done], ["all", t.tkFilterAll, blocks.size]]
        .map(([key, label, n]) => `<button class="pill" data-tk-mfilter="${key}" aria-pressed="${key === tk.mfilter}">${esc(label)} ${n}</button>`)
        .join("");
    }
    const extra = tk.mview === "report"
      ? `<button class="chip" data-tk-copy>${svg(ICON.copy)}${esc(t.tkCopy)}</button><button class="chip" data-tk-csv>${svg(ICON.download)}${esc(t.tkCsv)}</button>`
      : `<button class="chip" data-tk-recheck>${esc(t.tkRecheck)}</button>`;
    const toolbar = `<div class="toolbar">${archive ? "" : select}${seg}${pills}${this._tkSearch()}${extra}</div>`;
    const missing = tk.mapping?.missing || {};
    const body = {
      place: () => this._tkRenderPlaces(rows),
      device: () => this._tkRenderDevices(blocks, usedIds, missing),
      report: () => this._tkRenderReport(rows),
    }[tk.mview]();
    const later = tk.mview === "device" && !archive ? this._tkRenderLater(missing) : "";
    const bar = archive ? "" : `<div class="stepbar"><span class="left sub">${esc(t.tkReportNote)}</span><button class="chip" data-tk-tab="cleanup">${esc(t.tkNext.cleanup)}</button></div>`;
    return `${toolbar}${body}${later}${bar}`;
  },

  _tkIdLine(r) {
    const t = this._t;
    if (r.restored) return `<span class="mono">${esc(r.old)}</span><span class="sub"> · ${esc(t.tkRestoredState)}</span>`;
    const target = r.new ? esc(r.new) : `<span class="old">${esc(r.taken ? t.tkNoNew : t.tkNotTaken)}</span>`;
    return `<span class="mono"><span class="old">${esc(r.old)}</span><br>→ ${target}</span>`;
  },

  _tkOldDetails(id) {
    // what the device was in the old integration, as the report keeps it
    const t = this._t;
    const d = this._tk.mapping?.devices?.[id];
    if (!d) return "";
    const o = t.tkOld;
    const when = d.taken_at ? new Date(d.taken_at).toLocaleDateString(this._hass.locale?.language || this._hass.language) : "";
    const lines = [
      [o.taken, d.taken_at ? [when, d.carried?.length ? `${o.carried}: ${d.carried.map((c) => t.tkCarryOpt[c]).join(", ")}` : ""].filter(Boolean).join(" · ") : o.byHand],
      [o.config, d.old.config ? `<span class="mono">${esc(d.old.config)}</span>` : ""],
      [o.name, esc(d.old.name || "")],
      [o.device, esc(d.old.device_name || "")],
      [o.area, esc([d.old.area, ...(d.old.labels || [])].filter(Boolean).join(" · "))],
      [o.senders, d.old.senders?.length ? `<span class="mono">${esc(d.old.senders.join(", "))}</span>` : ""],
    ];
    return `<dl class="olddl"><span class="title">${esc(o.title)}</span>${lines
      .filter(([, v]) => v)
      .map(([k, v]) => `<dt>${esc(k)}</dt><dd>${k === o.taken ? esc(v) : v}</dd>`)
      .join("")}</dl>`;
  },

  _tkRenderDevices(blocks, usedIds, missing) {
    const t = this._t;
    const tk = this._tk;
    const q = tk.q.trim();
    const html = [...blocks.entries()]
      .filter(([id, items]) => {
        const used = usedIds.has(id);
        if (tk.mfilter === "used" && !used) return false;
        if (tk.mfilter === "done" && (used || !items[0].taken)) return false;
        return items.some((r) => this._tkMatches(r.device, r.id, r.old, r.new, r.area));
      })
      .map(([id, items]) => {
        const first = items[0];
        const open = tk.open.has(id) || !!q;
        const places = this._tkPlaceCount(items);
        const stored = tk.mapping?.devices?.[id];
        const state = !first.taken
          ? `<span class="chip-s">${esc(t.tkNotTaken)}</span>`
          : places ? `<span class="chip-s used">${esc(t.tkPlaces(places))}</span>` : `<span class="chip-s ok">${esc(t.tkDoneState)}</span>`;
        const chips = [
          first.area ? `<span class="chip-s">${esc(first.area)}</span>` : "",
          stored && !stored.taken_at ? `<span class="chip-s">${esc(t.tkOld.byHand)}</span>` : "",
          ...(missing[id] || []).map((o) => `<span class="chip-s avail" title="${esc(t.tkAvailable)}">+ ${esc(t.tkCarryOpt[o])}</span>`),
        ].join("");
        const entities = open
          ? `<div class="ents">${this._tkOldDetails(id)}${items
              .map((r) => `<div class="ent">${this._tkIdLine(r)}<span>${r.restored ? "" : USAGE_KINDS.flatMap((k) => r.usage[k].map((p) => this._tkPlaceChip(k, p))).join("") || `<span class="chip-s ok">${esc(t.tkUnused)}</span>`}</span></div>`)
              .join("")}</div>`
          : "";
        return `<div class="devblock"><div class="devhead" data-tk-open="${esc(id)}">
            <button class="fold" aria-expanded="${open}"><span aria-hidden="true">${open ? "▾" : "▸"}</span> ${esc(first.device)}</button>
            <span class="sub mono">${esc(id)}</span><span class="devchips">${chips}</span><span class="devstate">${state}</span></div>${entities}</div>`;
      })
      .join("");
    return html || this._emptyState(ICON.search, tk.q ? t.tkNoMatch : t.tkNothingHere, "", "", true);
  },

  _tkRenderPlaces(rows) {
    // the rows by the automation, script, scene or dashboard that uses them: one place is
    // edited once for all its old IDs
    const t = this._t;
    const places = new Map();
    for (const r of rows) {
      if (r.restored) continue;
      for (const k of USAGE_KINDS) {
        for (const p of r.usage[k]) {
          const key = `${k}\u0000${p.name}`;
          if (!places.has(key)) places.set(key, { kind: k, place: p, rows: [] });
          places.get(key).rows.push(r);
        }
      }
    }
    const html = [...places.values()]
      .filter((e) => this._tkMatches(e.place.name, ...e.rows.flatMap((r) => [r.device, r.id, r.old, r.new])))
      .sort((a, b) => USAGE_KINDS.indexOf(a.kind) - USAGE_KINDS.indexOf(b.kind) || a.place.name.localeCompare(b.place.name))
      .map((e) => `<div class="devblock"><div class="devhead"><b>${esc(t.tkKind[e.kind])}: ${esc(e.place.name)}</b>
          <span class="devstate">${e.place.path ? `<button class="chip" data-tk-go="${esc(e.place.path)}">${svg(ICON.open)}${esc(t.tkEdit)}</button>` : `<span class="sub">${esc(t.tkNoEditor)}</span>`}</span></div>
          <div class="ents">${e.rows.map((r) => `<div class="ent">${this._tkIdLine(r)}<span class="sub">${esc(r.device)}</span></div>`).join("")}</div></div>`)
      .join("");
    if (html) return html;
    return places.size ? this._emptyState(ICON.search, t.tkNoMatch, "", "", true) : this._emptyState(ICON.check, t.tkNoPlaces, "", "", true);
  },

  _tkRenderReport(rows) {
    // the mapping as a table: one row per old entity
    const t = this._t;
    const visible = rows.filter((r) => this._tkMatches(r.device, r.id, r.old, r.new, r.area));
    if (!visible.length) return this._emptyState(ICON.search, t.tkNoMatch, "", "", true);
    let last = "";
    const body = visible
      .map((r) => {
        const first = r.id !== last;
        last = r.id;
        const places = this._tkPlaceCount([r]);
        const state = !r.taken
          ? `<span class="chip-s">${esc(t.tkNotTaken)}</span>`
          : r.restored ? `<span class="chip-s ok">${esc(t.tkRestoredState)}</span>`
          : places ? `<span class="chip-s used">${esc(t.tkPlaces(places))}</span>` : `<span class="chip-s ok">${esc(t.tkFree)}</span>`;
        return `<tr class="${first ? "first" : ""}"><td class="dev">${first ? `${esc(r.device)}<br><span class="sub mono">${esc(r.id)}</span>` : ""}</td>
          <td class="mono old">${esc(r.old)}</td><td class="mono">${r.new ? esc(r.new) : `<span class="old">${esc(r.taken ? t.tkNoNew : t.tkNotTaken)}</span>`}</td><td>${state}</td></tr>`;
      })
      .join("");
    return `<div style="padding:0 8px"><table class="idtable"><colgroup><col style="width:24%"><col style="width:31%"><col style="width:31%"><col style="width:14%"></colgroup>
      <thead><tr><th>${esc(t.tkColDevice)}</th><th>${esc(t.tkColOld)}</th><th>${esc(t.tkColNew)}</th><th>${esc(t.tkColState)}</th></tr></thead><tbody>${body}</tbody></table></div>
      <p class="note" style="padding:0 16px">${esc(t.tkReportNote)}</p>`;
  },

  _tkRenderLater(missing) {
    // what the old integration had and the devices set up still lack, to carry over now
    const t = this._t;
    const tk = this._tk;
    const lists = Object.values(missing);
    const counts = Object.fromEntries(CARRY_OPTIONS.map((o) => [o, lists.filter((m) => m.includes(o)).length]));
    const found = CARRY_OPTIONS.filter((o) => counts[o]);
    if (!found.length) return "";
    const summary = `${t.tkAvailable}: ${found.map((o) => t.tkCarryCount(t.tkCarryOpt[o], counts[o])).join(", ")}`;
    const devices = lists.filter((m) => m.some((o) => tk.carry.has(o))).length;
    const panel = tk.later
      ? `${this._tkCarryOptions(counts, "data-tk-carry")}
          <button class="chip primary" data-tk-later-run ${devices && !tk.busy ? "" : "disabled"}>${esc(tk.busy ? t.tkBusy : devices ? t.tkCarryRun(devices) : t.tkNothing)}</button>`
      : "";
    return `<div class="later"><div class="later-head"><span class="sub">${esc(summary)}</span>
      <button class="chip" data-tk-later aria-expanded="${tk.later}">${esc(t.tkCarryLater)}</button></div>${panel}</div>`;
  },

  // ---- step 4: clean up -----------------------------------------------------------------

  _renderCleanup(clean, select) {
    const t = this._t;
    const tk = this._tk;
    const c = t.tkClean;
    const item = (ok, warn, title, text, action = "") =>
      `<div class="check"><span class="mark${ok ? " ok" : warn ? " warn" : ""}">${ok ? "✓" : warn ? "!" : ""}</span><span><b>${esc(title)}</b><span class="sub">${esc(text)}</span></span>${action}</div>`;
    const restore = clean.oldGone
      ? clean.restorable
        ? `<button class="chip" data-tk-restore ${tk.busy ? "disabled" : ""}>${esc(c.restoreRun)}</button>`
        : ""
      : "";
    const items = [
      item(!clean.ready, false, c.taken, clean.ready ? c.takenOpen(clean.ready) : c.takenDone,
        clean.ready ? `<button class="chip" data-tk-tab="select">${esc(t.tkSteps[0])}</button>` : ""),
      item(clean.stored > 0, false, c.report, clean.stored ? c.reportText : c.reportNone),
      item(!clean.places, clean.places > 0, c.refs, clean.places ? c.refsOpen(clean.places) : c.refsDone,
        clean.places ? `<button class="chip" data-tk-tab="switch">${esc(t.tkSteps[2])}</button>` : ""),
      item(clean.oldGone, false, c.old, clean.oldGone ? c.oldDone : c.oldText,
        clean.oldGone ? "" : `<button class="chip" data-tk-go="${OLD_INTEGRATION}">${svg(ICON.open)}${esc(c.oldOpen)}</button>`),
      item(clean.yamlGone, false, c.yaml, clean.yamlGone ? c.yamlDone : c.yamlText),
      `<div class="check"><span class="mark${clean.restored && !clean.restorable ? " ok" : ""}">${clean.restored && !clean.restorable ? "✓" : ""}</span><span><b>${esc(c.restore)}</b><span class="sub">${esc(
        clean.restored && !clean.restorable ? c.restoreDone(clean.restored) : clean.oldGone ? c.restoreText : c.restoreWait
      )}</span></span>${restore}</div>`,
    ].join("");
    return `${select ? `<div class="toolbar">${select}</div>` : ""}${items}
      <div class="stepbar"><span class="left sub">${esc(t.tkFinishNote)}</span><button class="chip primary" data-tk-finish>${esc(t.tkFinish)}</button></div>`;
  },

  // ---- events -----------------------------------------------------------------------------

  _takeoverInput(e) {
    if (e.target.id !== "tkSearch" || e.isComposing) return;
    this._tk.q = e.target.value;
    // drawn once typing pauses, not on every key
    clearTimeout(this._tkTyping);
    this._tkTyping = setTimeout(() => {
      const before = this.shadowRoot.getElementById("tkSearch");
      const focused = this.shadowRoot.activeElement === before;
      const pos = before?.selectionStart ?? 0;
      this._renderTakeover();
      const input = this.shadowRoot.getElementById("tkSearch");
      if (focused && input) {
        input.focus();
        input.setSelectionRange(pos, pos);
      }
    }, 150);
  },

  _takeoverChange(e) {
    const tk = this._tk;
    if (e.target.id === "tkGateway") {
      tk.entry = e.target.value;
      if (!tk.archive) tk.tab = "";
      this._loadTakeover();
    } else if (e.target.dataset.tkCarry) {
      if (e.target.checked) tk.carry.add(e.target.dataset.tkCarry);
      else tk.carry.delete(e.target.dataset.tkCarry);
      saveCarry(tk.carry);
      this._renderTakeover();
    } else if (e.target.dataset.tkPick) {
      if (e.target.checked) tk.selected.add(e.target.dataset.tkPick);
      else tk.selected.delete(e.target.dataset.tkPick);
      this._renderTakeover();
    } else if (e.target.dataset.tkGroup !== undefined) {
      const area = e.target.dataset.tkGroup;
      for (const d of this._tkDevices()) {
        if (!d.ready || (d.area || "") !== area || !this._tkMatches(d.name, d.id, d.area, d.old, ...(d.labels || []))) continue;
        if (e.target.checked) tk.selected.add(d.id);
        else tk.selected.delete(d.id);
      }
      this._renderTakeover();
    }
  },

  _takeoverClick(e) {
    const tk = this._tk;
    const tab = e.target.closest("[data-tk-tab]");
    const fold = e.target.closest("[data-tk-fold]");
    const mfilter = e.target.closest("[data-tk-mfilter]");
    const mview = e.target.closest("[data-tk-mview]");
    if (e.target.closest("[data-tk-go]")) {
      this._navigate(e.target.closest("[data-tk-go]").dataset.tkGo);
    } else if (tab) {
      if (tk.tab !== tab.dataset.tkTab) tk.q = "";
      tk.tab = tab.dataset.tkTab;
      if (mview) {
        tk.mview = mview.dataset.tkMview;
        tk.mfilter = "all";
      }
      this._renderTakeover();
      this.shadowRoot.getElementById("takeover").scrollIntoView?.({ block: "nearest" });
    } else if (mview) {
      tk.mview = mview.dataset.tkMview;
      this._renderTakeover();
    } else if (mfilter) {
      tk.mfilter = mfilter.dataset.tkMfilter;
      this._renderTakeover();
    } else if (fold) {
      const area = fold.dataset.tkFold;
      if (tk.folded.has(area)) tk.folded.delete(area);
      else tk.folded.add(area);
      this._renderTakeover();
    } else if (e.target.closest("[data-tk-not]")) {
      tk.showNot = !tk.showNot;
      this._renderTakeover();
    } else if (e.target.closest("[data-tk-all]")) {
      const all = e.target.closest("[data-tk-all]").dataset.tkAll === "all";
      tk.selected = new Set(all ? this._tkDevices().filter((d) => d.ready).map((d) => d.id) : []);
      this._renderTakeover();
    } else if (e.target.closest("[data-tk-confirm]")) {
      this._takeOver();
    } else if (e.target.closest("[data-tk-later]")) {
      tk.later = !tk.later;
      this._renderTakeover();
    } else if (e.target.closest("[data-tk-later-run]")) {
      this._tkCarryLater();
    } else if (e.target.closest("[data-tk-recheck]")) {
      this._tkRecheck();
    } else if (e.target.closest("[data-tk-copy]")) {
      this._copyMapping();
    } else if (e.target.closest("[data-tk-csv]")) {
      this._downloadMapping();
    } else if (e.target.closest("[data-tk-restore]")) {
      this._tkRestore();
    } else if (e.target.closest("[data-tk-finish]")) {
      this._tkFinish();
    } else if (e.target.closest("[data-tk-devices]")) {
      tk.archive = false;
      this._setView("devices");
    } else {
      const row = e.target.closest("[data-tk-open]");
      if (row && !this._selecting(this.shadowRoot.getElementById("takeover"))) {
        const id = row.dataset.tkOpen;
        if (tk.open.has(id)) tk.open.delete(id);
        else tk.open.add(id);
        this._renderTakeover();
      }
    }
  },

  // ---- actions ----------------------------------------------------------------------------

  async _takeOver() {
    const t = this._t;
    const tk = this._tk;
    if (tk.busy || !tk.selected.size) return;
    tk.busy = true;
    this._renderTakeover();
    let result = null;
    try {
      result = await this._hass.callWS({
        type: "enocean_eltako/takeover/run",
        entry_id: tk.entry,
        devices: [...tk.selected],
        carry: [...tk.carry],
      });
    } catch (err) {
      this._notice(t.tkErrors[err.code] || t.tkErrors.unknown);
    }
    tk.busy = false;
    // something taken over: on to switching the old IDs over
    tk.tab = result?.count ? "switch" : "select";
    tk.mview = "place";
    tk.mfilter = "used";
    tk.q = "";
    await this._refreshStatus();
    await this._loadTakeover();
    // no old entity found for what was taken over: nothing to switch over, stay with the selection
    if (!(tk.mapping?.rows || []).length) tk.tab = "select";
    this._renderTakeover();
    this._checkTakeover();
    if (!result) return;
    const stillUsed = result.count ? (tk.mapping?.rows || []).filter(isUsed).length : 0;
    this._notice(
      t.tkDone(result.count, result.carried) +
        (stillUsed ? `. ${t.tkStillUsed(stillUsed)}` : "") +
        (result.skipped.length ? `. ${t.tkSkipped}: ${result.skipped.join("; ")}` : "")
    );
  },

  async _tkCarryLater() {
    const t = this._t;
    const tk = this._tk;
    if (tk.busy || !tk.carry.size) return;
    tk.busy = true;
    this._renderTakeover();
    try {
      const { carried } = await this._hass.callWS({ type: "enocean_eltako/takeover/carry", entry_id: tk.entry, carry: [...tk.carry] });
      tk.later = false;
      this._notice(t.tkCarried(carried), true);
    } catch (err) {
      this._notice(t.tkErrors[err.code] || t.tkErrors.unknown);
    }
    tk.busy = false;
    await this._tkRecheck();
  },

  async _tkRestore() {
    // the new entities get the old entity IDs back
    const t = this._t;
    const tk = this._tk;
    if (tk.busy) return;
    tk.busy = true;
    this._renderTakeover();
    try {
      const { restored, blocked } = await this._hass.callWS({ type: "enocean_eltako/takeover/restore", entry_id: tk.entry });
      this._notice(t.tkClean.restoreResult(restored, blocked), !blocked);
    } catch (err) {
      this._notice(t.tkErrors[err.code] || t.tkErrors.unknown);
    }
    tk.busy = false;
    await this._tkRecheck();
  },

  async _tkFinish() {
    // the tab goes; the report stays under Devices
    try {
      await this._hass.callWS({ type: "enocean_eltako/takeover/close" });
    } catch (err) {
      this._notice(this._t.tkErrors.unknown);
      return;
    }
    this._tk.tab = "";
    this._notice(this._t.tkFinished, true);
    await this._checkTakeover();
    if (this._view === "takeover") this._setView("devices");
  },

  _mappingTable() {
    const t = this._t;
    const head = [t.tkColDevice, "ID", t.tkColOld, t.tkColNew, t.tkColState, t.tkAutomations, t.tkScripts, t.tkScenes, t.tkDashboards];
    const names = (places) => places.map((p) => p.name).join("; ");
    const lines = (this._tk.mapping?.rows || []).map((r) => [
      r.device, r.id, r.old, r.new || "", !r.taken ? t.tkNotTaken : r.restored ? t.tkRestoredState : isUsed(r) ? t.tkFilterUsed : t.tkFree,
      names(r.usage.automation), names(r.usage.script), names(r.usage.scene), names(r.usage.dashboard),
    ]);
    return [head, ...lines];
  },

  async _copyMapping() {
    try {
      await navigator.clipboard.writeText(this._mappingTable().map((l) => l.join("\t")).join("\n"));
      this._notice(this._t.tkCopied, true);
    } catch (err) {
      this._notice(this._t.copyFailed);
    }
  },

  _downloadMapping() {
    this._download(csv(this._mappingTable()), "text/csv", "enocean-entity-mapping.csv");
  },
};
