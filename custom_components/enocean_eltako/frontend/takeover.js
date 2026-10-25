// The Takeover view of the panel. The wizard has three steps: select the devices of the old
// eltako integration, review what comes along and take them over, retire the old integration
// (keep its entity IDs or switch the places that use them, delete it, remove its YAML). Next to
// it are the reports: one per takeover, kept by the integration, readable once the old
// integration is gone and deletable. Its methods are added to the panel class (this = the panel).

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
const STEPS = ["select", "carry", "release"];

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
  entry: "", tab: "", section: "", available: false, reports: 0, preview: null, previewError: "", mapping: null,
  selected: new Set(), carry: loadCarry(), open: new Set(), busy: false, q: "", folded: new Set(), showNot: false,
  runs: null, run: "", runData: null, openRun: new Set(), confirm: "",
});

export const TAKEOVER_STYLE = `
  .takeover { padding-bottom: 8px; }
  .takeover .steps { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); border-bottom: 1px solid var(--line); }
  .takeover .step { display: flex; gap: 10px; align-items: flex-start; text-align: left; font: inherit; font-size: 12px; color: var(--muted);
    background: none; border: 0; border-bottom: 2px solid transparent; padding: 12px 14px 10px; cursor: pointer; }
  .takeover .step:hover:not(:disabled) b { color: var(--accent); }
  .takeover .step:disabled { cursor: default; opacity: .55; }
  .takeover .step.cur { border-bottom-color: var(--accent); }
  .takeover .step b { display: block; font-weight: 500; font-size: 13px; color: var(--text); }
  .takeover .num { flex: none; width: 22px; height: 22px; border-radius: 50%; border: 1px solid var(--line); display: flex; align-items: center; justify-content: center; font-size: 12px; }
  .takeover .step.cur .num { border-color: var(--accent); color: var(--accent); background: color-mix(in srgb, var(--accent) 10%, var(--surface)); }
  .takeover .step.done .num { border-color: var(--ok); color: var(--ok); background: color-mix(in srgb, var(--ok) 15%, var(--surface)); }
  .takeover .step.warn .num { border-color: var(--warn); color: var(--warn); }
  .takeover .topbar { display: flex; flex-wrap: wrap; gap: 8px 12px; align-items: center; padding: 12px 16px; border-bottom: 1px solid var(--line); }
  .takeover .topbar b { flex: 1; font-size: 15px; font-weight: 500; }
  .takeover .toolbar { padding: 10px 16px; display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
  .takeover .toolbar .grow { flex: 1; }
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
  .takeover .section h3 { margin: 0 0 4px; font-size: 14px; font-weight: 500; }
  .takeover .section h3 .sub { font-weight: 400; }
  .takeover .section .lead { margin: 0 0 10px; font-size: 12px; color: var(--muted); }
  .takeover .optcards { display: grid; grid-template-columns: repeat(auto-fill, minmax(210px, 1fr)); gap: 8px; }
  .takeover .optcard { display: flex; gap: 10px; align-items: flex-start; padding: 9px 12px; border: 1px solid var(--input-line); border-radius: 10px; cursor: pointer; font-size: 13px; }
  .takeover .optcard b { display: block; font-weight: 500; }
  .takeover .optcard .sub { display: block; overflow-wrap: anywhere; }
  .takeover .optcard:has(input:checked) { border-color: var(--accent); background: var(--accent-soft); }
  .takeover .optcard.off { cursor: default; opacity: .55; }
  .takeover .optcard input { margin-top: 2px; }
  .takeover .note { margin: 8px 0 0; font-size: 12px; color: var(--muted); }
  .takeover .stratcards { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
  .takeover .stratcard { display: flex; gap: 10px; align-items: flex-start; padding: 12px 14px; border: 1px solid var(--input-line); border-radius: 12px; cursor: pointer; font-size: 13px; }
  .takeover .stratcard b { display: block; font-weight: 500; font-size: 14px; margin-bottom: 2px; }
  .takeover .stratcard .sub { display: block; margin-bottom: 8px; }
  .takeover .stratcard:has(input:checked) { border-color: var(--accent); background: var(--accent-soft); box-shadow: 0 0 0 1px var(--accent); }
  .takeover .stratcard input { margin-top: 3px; }
  .takeover .link { font: inherit; font-weight: 500; color: var(--accent); background: none; border: 0; padding: 0; cursor: pointer; }
  .takeover .link:hover { color: var(--accent-hover); text-decoration: underline; }
  .takeover .seg { display: inline-flex; border: 1px solid var(--input-line); border-radius: 20px; overflow: hidden; }
  .takeover .seg button { height: 32px; padding: 0 14px; font: inherit; font-size: 13px; color: var(--muted); background: var(--surface); border: 0; cursor: pointer; }
  .takeover .seg button[aria-pressed="true"] { color: var(--accent-hover); background: var(--accent-soft); font-weight: 500; }
  .takeover .devblock { border-top: 1px solid var(--line); }
  .takeover .devhead { display: flex; flex-wrap: wrap; gap: 4px 10px; align-items: center; padding: 8px 16px; font-size: 13px; }
  .takeover .devhead[data-tk-open], .takeover .devhead[data-tk-open-run] { cursor: pointer; }
  .takeover .devhead[data-tk-open]:hover, .takeover .devhead[data-tk-open-run]:hover { background: color-mix(in srgb, var(--soft) 60%, transparent); }
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
  .takeover .chip-s.val { background: var(--accent-soft); color: var(--accent-hover); }
  .takeover .chip-s.off { background: none; color: var(--muted); border: 1px dashed var(--line); }
  .takeover .chip-s.avail { color: var(--muted); border: 1px dashed var(--line); background: none; }
  .takeover button.chip-s { font: inherit; font-size: 11px; border: 0; cursor: pointer; text-align: left; }
  .takeover button.chip-s:hover { text-decoration: underline; }
  .takeover .mono.old, .takeover .old { color: var(--muted); }
  .takeover .check { display: flex; gap: 12px; align-items: flex-start; padding: 12px 16px; border-top: 1px solid var(--line); font-size: 13px; }
  .takeover .check.wait { opacity: .6; }
  .takeover .check > span:nth-child(2) { flex: 1; min-width: 0; }
  .takeover .check b { display: block; font-weight: 500; }
  .takeover .check .warnnote { display: block; margin-top: 4px; font-size: 12px; color: var(--text); }
  .takeover .mark { flex: none; width: 22px; height: 22px; border-radius: 50%; border: 1px solid var(--line); display: flex; align-items: center; justify-content: center; font-size: 12px; color: var(--muted); }
  .takeover .mark.ok { border-color: var(--ok); color: var(--ok); background: color-mix(in srgb, var(--ok) 15%, var(--surface)); }
  .takeover .mark.warn { border-color: var(--warn); color: var(--warn); }
  .takeover .runcard { display: flex; flex-wrap: wrap; gap: 8px 16px; align-items: center; padding: 14px 16px; border-top: 1px solid var(--line); }
  .takeover .runcard:first-of-type { border-top: 0; }
  .takeover .runmain { flex: 1; min-width: 220px; display: grid; gap: 3px; font-size: 13px; }
  .takeover .runmain b { font-weight: 500; font-size: 14px; }
  .takeover .runact { display: flex; gap: 8px; align-items: center; }
  .takeover .confirm { flex-basis: 100%; display: flex; flex-wrap: wrap; gap: 8px 12px; align-items: center; padding: 10px 12px; border-radius: 8px; font-size: 12px;
    background: color-mix(in srgb, var(--warn) 18%, transparent); }
  .takeover .confirm span { flex: 1; min-width: 200px; }
  @media (max-width: 760px) {
    /* the steps below each other, name and state side by side */
    .takeover .steps { grid-template-columns: minmax(0, 1fr); }
    .takeover .stratcards { grid-template-columns: minmax(0, 1fr); }
    .takeover .ent { grid-template-columns: minmax(0, 1fr); }
    .takeover .olddl { grid-template-columns: minmax(0, 1fr); gap: 0 12px; }
    .takeover .olddl dd { margin-bottom: 4px; }
    .takeover .stepbar .chip.primary { flex: 1; justify-content: center; }
    .takeover .check { flex-wrap: wrap; }
    .takeover .check > .chip { margin-left: 34px; }
  }
`;

// the values behind a carry option, as the old device has them (for the preview of a device)
function optionValues(t, d, o) {
  const det = d.details || {};
  const ents = d.entities || [];
  switch (o) {
    case "area": return det.area ? [det.area] : [];
    case "labels": return [...new Set([...(det.labels || []), ...ents.flatMap((e) => e.labels || [])])];
    case "names": return [det.name, ...ents.map((e) => e.name)].filter(Boolean);
    case "icons": return ents.map((e) => e.icon).filter(Boolean);
    case "visibility": return [...new Set(ents.flatMap((e) => (e.visibility || []).map((v) => t.tkHiddenKind[v])))];
    case "voice": return [...new Set(ents.flatMap((e) => Object.entries(e.voice || {}).map(([a, on]) => `${t.tkAssistant[a] || a} ${on ? t.tkOn : t.tkOff}`)))];
    default: return [];
  }
}

const listed = (values, max) => values.slice(0, max).join(", ") + (values.length > max ? ` +${values.length - max}` : "");

export const takeover = {
  async _checkTakeover() {
    // the Takeover view exists while there is something to do or a report to read
    try {
      const status = await this._hass.callWS({ type: "enocean_eltako/takeover/status" });
      const tk = this._tk;
      const wasWizard = this._tkSection() === "wizard";
      tk.available = !!status.available;
      tk.reports = status.reports || 0;
      const shown = tk.available || tk.reports > 0;
      const button = this.shadowRoot.querySelector('#view button[data-view="takeover"]');
      if (button) button.hidden = !shown;
      const report = this.shadowRoot.getElementById("tkReport");
      if (report) report.hidden = !tk.reports;
      if (!shown && this._view === "takeover") this._setView("telegrams");
      else if (this._view === "takeover" && wasWizard !== (this._tkSection() === "wizard")) this._renderTakeover();
    } catch (err) {
      // not an admin or the integration is still starting: no view
    }
  },

  _openReport() {
    // the reports, from the Devices view
    const tk = this._tk;
    tk.section = "reports";
    tk.run = "";
    this._setView("takeover");
  },

  _tkSection() {
    const tk = this._tk;
    if (!tk.available) return "reports";
    if (!tk.reports) return "wizard";
    return tk.section || "wizard";
  },

  _tkGateways() {
    return this._gateways.filter((g) => g.loaded);
  },

  async _tkLoadRuns() {
    const tk = this._tk;
    try {
      tk.runs = await this._hass.callWS({ type: "enocean_eltako/takeover/reports" });
      tk.reports = tk.runs.length;
      if (tk.run && !tk.runs.some((r) => r.id === tk.run)) tk.run = "";
      tk.runData = tk.run ? await this._hass.callWS({ type: "enocean_eltako/takeover/report", run_id: tk.run }) : null;
    } catch (err) {
      tk.runs = tk.runs || [];
      tk.run = "";
      tk.runData = null;
    }
  },

  async _loadTakeover() {
    const tk = this._tk;
    await this._tkLoadRuns();
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
    if (!STEPS.includes(tk.tab)) tk.tab = ready.length ? "select" : (tk.mapping?.rows || []).length ? "release" : "select";
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
    this._checkTakeover();
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

  _tkRelease() {
    // what the last step finds in the current state
    const tk = this._tk;
    const rows = tk.mapping?.rows || [];
    const oldGone = !(tk.mapping?.old_active ?? tk.preview?.old_active) && !tk.mapping?.old_entities;
    const restorable = rows.some((r) => r.taken && r.new && !r.restored && r.new !== r.old && r.new.split(".")[0] === r.old.split(".")[0]);
    const places = this._tkPlaceCount(rows);
    const yamlGone = tk.previewError === "no_config";
    const strategy = tk.mapping?.strategy || "";
    const done = strategy === "keep" ? [oldGone, oldGone && !restorable, yamlGone] : strategy === "new" ? [!places, oldGone, yamlGone] : [];
    return { rows, oldGone, restorable, places, yamlGone, strategy, restored: rows.filter((r) => r.restored).length, done, doneCount: done.filter(Boolean).length };
  },

  _renderTakeover() {
    const container = this.shadowRoot.getElementById("takeover");
    const section = this._tkSection();
    const bar = this._tkTopbar(section);
    this._replace(container, bar + (section === "reports" ? this._renderReports() : this._renderWizard()));
    container.querySelectorAll("[data-partial]").forEach((box) => { box.indeterminate = true; });
  },

  _tkTopbar(section) {
    // the switch between the wizard and the reports, when both exist
    const t = this._t;
    const tk = this._tk;
    if (!tk.available || !tk.reports) return "";
    const seg = ["wizard", "reports"]
      .map((s) => `<button data-tk-section="${s}" aria-pressed="${s === section}">${esc(t.tkSections[s])}${s === "reports" ? ` · ${tk.reports}` : ""}</button>`)
      .join("");
    return `<div class="topbar"><span class="seg" role="group">${seg}</span></div>`;
  },

  _tkGatewaySelect() {
    const t = this._t;
    const gateways = this._tkGateways();
    if (gateways.length < 2) return "";
    return `<select class="select" id="tkGateway" aria-label="${esc(t.gateway)}">${gateways
      .map((g) => `<option value="${esc(g.entry_id)}"${g.entry_id === this._tk.entry ? " selected" : ""}>${esc(g.title)}</option>`)
      .join("")}</select>`;
  },

  // ---- the wizard -------------------------------------------------------------------------

  _renderWizard() {
    const t = this._t;
    const tk = this._tk;
    if (!this._tkGateways().length) return this._noGateway();
    const select = this._tkGatewaySelect();
    const devices = this._tkDevices();
    const ready = devices.filter((d) => d.ready);
    const chosen = ready.filter((d) => tk.selected.has(d.id));
    const rows = tk.mapping?.rows || [];
    const later = Object.values(tk.mapping?.missing || {}).filter((m) => m.length).length;
    const rel = this._tkRelease();
    const st = t.tkStepState;
    const steps = [
      { text: ready.length ? st.open(ready.length) : st.none, done: !ready.length && rows.length > 0 },
      {
        text: ready.length ? (chosen.length ? st.chosen(chosen.length) : st.nothing) : later ? st.later(later) : st.waiting,
        off: !ready.length && !later,
      },
      {
        text: !rows.length ? st.waiting : !rel.strategy ? st.choose : st.progress(rel.doneCount, 3),
        done: rel.strategy && rel.doneCount === 3, warn: rows.length > 0 && !(rel.strategy && rel.doneCount === 3), off: !rows.length,
      },
    ];
    if (!STEPS.includes(tk.tab)) tk.tab = "select";
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
      carry: () => this._renderCarry(chosen, ready, select),
      release: () => this._renderRelease(rel, select),
    }[tk.tab]();
    return `<div class="steps">${stepsHtml}</div>${body}`;
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

  // ---- step 1: select ---------------------------------------------------------------------

  _renderSelect(devices, ready, chosen, select) {
    const t = this._t;
    const tk = this._tk;
    if (tk.previewError) {
      const text = t.tkErrors[tk.previewError] || t.tkErrors.unknown;
      return `${select ? `<div class="toolbar">${select}</div>` : ""}${this._emptyState(ICON.check, text, "", "", true)}`;
    }
    // devices already set up are not offered here: step 2 completes them
    const exists = devices.filter((d) => d.reason === "takeover_exists").length;
    const not = devices.filter((d) => !d.ready && d.reason !== "takeover_exists");
    const counts = `<div class="counts"><span class="chip-s">${esc(t.tkInYaml(devices.length))}</span>${
      exists ? `<button class="chip-s ok" data-tk-tab="carry">${esc(t.tkExisting(exists))}</button>` : ""
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

  // ---- step 2: review what comes along and take over --------------------------------------

  _tkEntityChips(e, show) {
    // what is set on an old entity, as chips; show(option) tells whether it comes along
    const t = this._t;
    const out = [];
    const add = (option, text) => {
      const state = show(option);
      if (state) out.push(`<span class="chip-s val${state === "off" ? " off" : ""}"${state === "off" ? ` title="${esc(t.tkOld.notCarried)}"` : ""}>${esc(text)}</span>`);
    };
    if (e.labels?.length) add("labels", `${t.tkEntLabels}: ${e.labels.join(", ")}`);
    if (e.name) add("names", `${t.tkEntName}: ${e.name}`);
    if (e.icon) add("icons", `${t.tkEntIcon}: ${e.icon}`);
    for (const v of e.visibility || []) add("visibility", t.tkHiddenKind[v]);
    for (const [a, on] of Object.entries(e.voice || {})) add("voice", `${t.tkAssistant[a] || a}: ${on ? t.tkOn : t.tkOff}`);
    return out.join("");
  },

  _tkPreviewDevice(d) {
    // one device of the preview: what comes along in the head, opened the entities in detail
    const t = this._t;
    const tk = this._tk;
    const open = tk.open.has(d.id);
    const det = d.details || {};
    const on = (o) => tk.carry.has(o);
    const summary = CARRY_OPTIONS.filter(on)
      .map((o) => [o, optionValues(t, d, o)])
      .filter(([, values]) => values.length)
      .map(([o, values]) => `<span class="chip-s val">${esc(t.tkCarryOpt[o])}: ${esc(listed(values, 2))}</span>`)
      .join("");
    let body = "";
    if (open) {
      const lines = [
        [t.tkDevArea, on("area") && det.area ? esc(det.area) : ""],
        [t.tkDevLabels, on("labels") && det.labels?.length ? det.labels.map((l) => `<span class="chip-s val">${esc(l)}</span>`).join("") : ""],
        [t.tkDevName, on("names") && det.name ? esc(det.name) : ""],
      ].filter(([, v]) => v);
      const dl = lines.length ? `<dl class="olddl">${lines.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${v}</dd>`).join("")}</dl>` : "";
      const ents = (d.entities?.length ? d.entities : [{ old: null, new: null }])
        .map((e) => {
          const ids = e.old
            ? `<span class="mono"><span class="old">${esc(e.old)}</span><br>→ ${e.new ? esc(e.new) : `<span class="old">${esc(t.tkNewLater)}</span>`}</span>`
            : `<span class="old">${esc(t.tkNoOldEntities)}</span>`;
          const chips = this._tkEntityChips(e, (o) => (on(o) ? "on" : ""));
          const maybe = chips && !e.new ? `<br><span class="sub">${esc(t.tkEntMaybe)}</span>` : "";
          return `<div class="ent">${ids}<span>${chips}${maybe}</span></div>`;
        })
        .join("");
      body = `<div class="ents">${dl}${ents}</div>`;
    }
    const state = d.used ? `<span class="chip-s used">${esc(t.tkPlaces(d.used))}</span>` : `<span class="chip-s">${esc(t.tkUnused)}</span>`;
    return `<div class="devblock"><div class="devhead" data-tk-open="${esc(d.id)}">
      <button class="fold" aria-expanded="${open}"><span aria-hidden="true">${open ? "▾" : "▸"}</span> ${esc(d.name)}</button>
      <span class="sub mono">${esc(d.id)}</span><span class="devchips">${summary}</span><span class="devstate">${state}</span></div>${body}</div>`;
  },

  _renderCarry(chosen, ready, select) {
    const t = this._t;
    const tk = this._tk;
    const missing = Object.values(tk.mapping?.missing || {});
    const laterBy = Object.fromEntries(CARRY_OPTIONS.map((o) => [o, missing.filter((m) => m.includes(o)).length]));
    if (!chosen.length && !missing.some((m) => m.length)) {
      return this._emptyState(ICON.check, t.tkNoneChosen, "", `<button class="chip" data-tk-tab="select">${esc(t.tkBack)}</button>`, true);
    }
    const cards = CARRY_OPTIONS.map((o) => {
      const having = chosen.filter((d) => (d.carry || []).includes(o));
      const values = [...new Set(having.flatMap((d) => optionValues(t, d, o)))];
      const n = having.length;
      const k = laterBy[o];
      const detail = [
        n ? [listed(values, 3), t.tkCarryOf(n, chosen.length)].filter(Boolean).join(" · ") : chosen.length ? t.tkCarryNone : "",
        k ? t.tkCarryAlso(k) : "",
      ].filter(Boolean).join(" · ");
      const usable = n || k;
      return `<label class="optcard${usable ? "" : " off"}" title="${esc(values.join(", "))}"><input type="checkbox" data-tk-carry="${o}"${tk.carry.has(o) && usable ? " checked" : ""}${usable ? "" : " disabled"}>
        <span><b>${esc(t.tkCarryOpt[o])}</b><span class="sub">${esc(detail || t.tkCarryNone)}</span></span></label>`;
    }).join("");
    let preview = "";
    if (chosen.length) {
      const entities = chosen.reduce((n, d) => n + (d.entities || []).length, 0);
      const places = new Set(chosen.flatMap((d) => d.places || [])).size;
      const shown = chosen
        .filter((d) => this._tkMatches(d.name, d.id, d.area, d.old, ...(d.labels || []), ...(d.details?.labels || []), ...(d.entities || []).flatMap((e) => [e.old, e.new, e.name, ...(e.labels || [])])))
        .sort((x, y) => x.name.localeCompare(y.name));
      const all = chosen.every((d) => tk.open.has(d.id));
      preview = `<div class="section"><h3>${esc(t.tkPreview)} <span class="sub">· ${esc(t.tkPreviewSum(chosen.length, entities, places))}</span></h3>
        <p class="lead">${esc(t.tkAfterwards)}</p></div>
        <div class="toolbar">${this._tkSearch()}<button class="chip" data-tk-expand="${all ? "none" : "all"}">${esc(all ? t.tkCollapseAll : t.tkExpandAll)}</button></div>
        ${shown.length ? shown.map((d) => this._tkPreviewDevice(d)).join("") : this._emptyState(ICON.search, t.tkNoMatch, "", "", true)}
        <p class="note" style="padding:0 16px">${esc(t.tkEntityNote)}</p>`;
    }
    // devices already set up: what the old integration has and they still lack
    let laterHtml = "";
    const laterDevices = missing.filter((m) => m.some((o) => tk.carry.has(o))).length;
    if (missing.some((m) => m.length)) {
      const summary = CARRY_OPTIONS.filter((o) => laterBy[o]).map((o) => t.tkCarryCount(t.tkCarryOpt[o], laterBy[o])).join(", ");
      laterHtml = `<div class="section"><h3>${esc(t.tkLater.title)} <span class="sub">· ${esc(summary)}</span></h3>
        <p class="lead">${esc(t.tkLater.text)}</p>
        <button class="chip primary" data-tk-later-run ${laterDevices && !tk.busy ? "" : "disabled"}>${esc(tk.busy ? t.tkBusy : laterDevices ? t.tkLater.run(laterDevices) : t.tkLater.pick)}</button></div>`;
    }
    const bar = `<div class="stepbar"><span class="left">${ready.length ? `<button class="chip" data-tk-tab="select">${esc(t.tkBack)}</button>` : ""}</span>
      <span class="left">${(tk.mapping?.rows || []).length ? `<button class="link" data-tk-tab="release">${esc(t.tkNext.release)}</button>` : ""}
      ${chosen.length ? `<button class="chip primary" data-tk-confirm ${tk.busy ? "disabled" : ""}>${esc(tk.busy ? t.tkBusy : t.tkRun(chosen.length))}</button>` : ""}</span></div>`;
    return `<div class="section"><h3>${esc(t.tkCarryTitle)}</h3><div class="optcards">${cards}</div><p class="note">${esc(t.tkCarryNote)}</p></div>${preview}${laterHtml}${bar}`;
  },

  // ---- step 3: retire the old integration -------------------------------------------------

  _tkPlaceChip(kind, place) {
    // a place that uses an old ID; one with an editor opens it
    const label = `${this._t.tkKind[kind]}: ${place.name}`;
    return place.path
      ? `<button class="chip-s used place" data-tk-go="${esc(place.path)}" title="${esc(this._t.tkEdit)}">${esc(label)}</button>`
      : `<span class="chip-s used">${esc(label)}</span>`;
  },

  _tkIdLine(r) {
    const t = this._t;
    if (r.restored) return `<span class="mono">${esc(r.old)}</span><span class="sub"> · ${esc(t.tkRestoredState)}</span>`;
    const target = r.new ? esc(r.new) : `<span class="old">${esc(r.taken ? t.tkNoNew : t.tkNotTaken)}</span>`;
    return `<span class="mono"><span class="old">${esc(r.old)}</span><br>→ ${target}</span>`;
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

  _renderRelease(rel, select) {
    const t = this._t;
    const tk = this._tk;
    const r = t.tkRelease;
    if (!rel.rows.length) return `${select ? `<div class="toolbar">${select}</div>` : ""}${this._emptyState(ICON.check, t.tkEmpty, "", "", true)}`;
    const card = (key) => `<label class="stratcard"><input type="radio" name="tkStrategy" data-tk-strategy="${key}"${rel.strategy === key ? " checked" : ""}>
      <span><b>${esc(r[key].title)}</b><span class="sub">${esc(r[key].text)}</span></span></label>`;
    const strategy = `<div class="section">${select ? `<div style="margin-bottom:10px">${select}</div>` : ""}<h3>${esc(r.title)}</h3>
      <p class="lead">${esc(`${r.used(rel.places)}. ${r.choose}`)}</p><div class="stratcards" role="radiogroup" aria-label="${esc(r.title)}">${card("keep")}${card("new")}</div></div>`;
    // one step of the checklist; its number, or a tick when done
    const item = (n, ok, title, text, action = "", wait = false, extra = "") =>
      `<div class="check${wait ? " wait" : ""}"><span class="mark${ok ? " ok" : ""}">${ok ? "✓" : n}</span><span><b>${esc(title)}</b><span class="sub">${esc(text)}</span>${extra}</span>${action}</div>`;
    const oldAction = rel.oldGone ? "" : `<button class="chip" data-tk-go="${OLD_INTEGRATION}">${svg(ICON.open)}${esc(r.oldOpen)}</button>`;
    const oldWarn = rel.oldGone ? "" : `<span class="warnnote">⚠ ${esc(r.oldWarn)}</span>`;
    const yaml = (n) => item(n, rel.yamlGone, r.yaml, rel.yamlGone ? r.yamlDone : r.yamlText);
    let items = "";
    let after = "";
    if (rel.strategy === "keep") {
      const restoreText = rel.oldGone ? (rel.restorable ? r.restoreText : rel.restored ? r.restoreDone(rel.restored) : r.restoreNone) : r.restoreWait;
      const restoreAction = rel.oldGone && rel.restorable ? `<button class="chip primary" data-tk-restore ${tk.busy ? "disabled" : ""}>${esc(tk.busy ? t.tkBusy : r.restoreRun)}</button>` : "";
      items = [
        item(1, rel.done[0], r.old, rel.oldGone ? r.oldDone : r.oldKeep, oldAction, false, oldWarn),
        item(2, rel.done[1], r.restore, restoreText, restoreAction, !rel.oldGone),
        yaml(3),
      ].join("");
    } else if (rel.strategy === "new") {
      items = [
        item(1, rel.done[0], r.refs, rel.places ? r.refsOpen(rel.places) : r.refsDone, rel.places ? `<button class="chip" data-tk-recheck>${esc(t.tkRecheck)}</button>` : ""),
        item(2, rel.done[1], r.old, rel.oldGone ? r.oldDone : r.oldNew, oldAction, false, oldWarn),
        yaml(3),
      ].join("");
      if (rel.places) after = `<div class="section"><h3>${esc(r.refsTitle)}</h3></div><div class="toolbar">${this._tkSearch()}</div>${this._tkRenderPlaces(rel.rows)}`;
    }
    const list = items ? `<div class="section" style="padding-bottom:0"><h3>${esc(r.steps)}</h3></div>${items}` : "";
    const bar = `<div class="stepbar"><span class="left sub">${esc(r.reports)}</span><button class="chip" data-tk-reports>${esc(r.reportsOpen)}</button></div>`;
    return `${strategy}${list}${after}${bar}`;
  },

  // ---- the reports ------------------------------------------------------------------------

  _tkDate(at) {
    const lang = this._hass.locale?.language || this._hass.language;
    return new Date(at).toLocaleString(lang, { dateStyle: "long", timeStyle: "short" });
  },

  _tkRunTitle(run) {
    const v = this._t.tkReportsView;
    return run.manual ? v.byHand : `${v.takenOn}: ${this._tkDate(run.at)}`;
  },

  _tkConfirm(run) {
    const v = this._t.tkReportsView;
    return `<div class="confirm"><span>${esc(v.confirm(run.devices))}</span>
      <button class="chip warn" data-tk-del-yes="${esc(run.id)}"${this._tk.busy ? " disabled" : ""}>${esc(v.confirmYes)}</button>
      <button class="chip" data-tk-del-no>${esc(v.cancel)}</button></div>`;
  },

  _renderReports() {
    const t = this._t;
    const tk = this._tk;
    const v = t.tkReportsView;
    if (tk.run && tk.runData) return this._renderRun();
    const runs = tk.runs || [];
    if (!runs.length) return this._emptyState(ICON.check, v.empty, "", "", true);
    const cards = runs
      .map((run) => {
        const carried = run.manual ? "" : run.carry.length ? `${v.carried}: ${run.carry.map((c) => t.tkCarryOpt[c]).join(", ")}` : v.nothingCarried;
        return `<div class="runcard"><div class="runmain"><b>${esc(this._tkRunTitle(run))}</b>
          <span class="sub">${esc([run.gateway || v.gatewayGone, v.counts(run.devices, run.entities)].join(" · "))}</span>
          <span class="sub">${esc([carried, run.restored ? v.restored(run.restored, run.entities) : ""].filter(Boolean).join(" · "))}</span></div>
          <div class="runact"><button class="chip" data-tk-run="${esc(run.id)}">${esc(v.open)}</button>
          <button class="chip text warn" data-tk-del="${esc(run.id)}">${esc(v.remove)}</button></div>${tk.confirm === run.id ? this._tkConfirm(run) : ""}</div>`;
      })
      .join("");
    return `<div class="section"><h3>${esc(v.title)}</h3><p class="lead" style="margin:0">${esc(v.note)}</p></div>${cards}`;
  },

  _renderRun() {
    const t = this._t;
    const tk = this._tk;
    const v = t.tkReportsView;
    const run = tk.runData;
    const blocks = this._tkBlocks(run.rows);
    const q = tk.q.trim();
    const html = [...blocks.entries()]
      .filter(([id, items]) => items.some((r) => this._tkMatches(r.device, r.id, r.old, r.new, r.area, ...(run.devices[id]?.old?.details?.labels || run.devices[id]?.old?.labels || []))))
      .map(([id, items]) => {
        const open = tk.openRun.has(id) || !!q;
        const device = run.devices[id];
        const places = this._tkPlaceCount(items);
        const state = places ? `<span class="chip-s used">${esc(t.tkPlaces(places))}</span>` : `<span class="chip-s ok">${esc(items.every((r) => r.restored) ? t.tkRestoredState : t.tkFree)}</span>`;
        const entities = open
          ? `<div class="ents">${this._tkOldDetails(device, run)}${items
              .map((r) => `<div class="ent">${this._tkIdLine(r)}<span>${r.restored ? "" : USAGE_KINDS.flatMap((k) => r.usage[k].map((p) => this._tkPlaceChip(k, p))).join("") || `<span class="chip-s ok">${esc(t.tkUnused)}</span>`}</span></div>`)
              .join("")}</div>`
          : "";
        return `<div class="devblock"><div class="devhead" data-tk-open-run="${esc(id)}">
          <button class="fold" aria-expanded="${open}"><span aria-hidden="true">${open ? "▾" : "▸"}</span> ${esc(device.name)}</button>
          <span class="sub mono">${esc(id)}</span><span class="devchips">${device.old.area ? `<span class="chip-s">${esc(device.old.area)}</span>` : ""}</span>
          <span class="devstate">${state}</span></div>${entities}</div>`;
      })
      .join("");
    const head = `<div class="topbar"><button class="chip" data-tk-run-back>${esc(v.back)}</button><b>${esc(this._tkRunTitle(run))}<br><span class="sub">${esc([run.gateway || v.gatewayGone, v.counts(Object.keys(run.devices).length, run.entities)].join(" · "))}</span></b>
      <button class="chip" data-tk-copy>${svg(ICON.copy)}${esc(t.tkCopy)}</button><button class="chip" data-tk-csv>${svg(ICON.download)}${esc(t.tkCsv)}</button>
      <button class="chip text warn" data-tk-del="${esc(run.id)}">${esc(v.remove)}</button></div>`;
    const confirm = tk.confirm === run.id ? `<div style="padding:10px 16px 0">${this._tkConfirm({ ...run, devices: Object.keys(run.devices).length })}</div>` : "";
    return `${head}${confirm}<div class="toolbar">${this._tkSearch()}</div>${html || this._emptyState(ICON.search, t.tkNoMatch, "", "", true)}
      <p class="note" style="padding:0 16px">${esc(v.note)}</p>`;
  },

  _tkOldDetails(d, run) {
    // what the device was in the old integration, as the report keeps it, and what came along
    const t = this._t;
    const o = t.tkOld;
    const det = d.old.details || {};
    const carried = run.carry || [];
    const mark = (option, html) => (carried.includes(option) ? html : `<span class="chip-s off" title="${esc(o.notCarried)}">${html}</span>`);
    const when = run.at ? this._tkDate(run.at) : "";
    const lines = [
      [o.taken, run.at ? [when, carried.length ? `${o.carried}: ${carried.map((c) => t.tkCarryOpt[c]).join(", ")}` : ""].filter(Boolean).join(" · ") : o.byHand, true],
      [o.config, d.old.config ? `<span class="mono">${esc(d.old.config)}</span>` : ""],
      [o.name, esc(d.old.name || "")],
      [o.device, esc(d.old.device_name || "")],
      [o.area, det.area ? (carried.includes("area") ? `<span class="chip-s val">${esc(det.area)}</span>` : mark("area", esc(det.area))) : ""],
      [o.labels, (det.labels || d.old.labels || []).map((l) => (carried.includes("labels") ? `<span class="chip-s val">${esc(l)}</span>` : mark("labels", esc(l)))).join("")],
      [o.senders, d.old.senders?.length ? `<span class="mono">${esc(d.old.senders.join(", "))}</span>` : ""],
    ];
    const extras = (det.entities || [])
      .map((e) => ({ e, chips: this._tkEntityChips(e, (option) => (carried.includes(option) ? "on" : "off")) }))
      .filter((x) => x.chips)
      .map((x) => `<div><span class="mono old">${esc(x.e.old)}</span><br>${x.chips}</div>`)
      .join("");
    if (extras) lines.push([o.entities, extras]);
    return `<dl class="olddl"><span class="title">${esc(o.title)}</span>${lines
      .filter(([, v]) => v)
      .map(([k, v, plain]) => `<dt>${esc(k)}</dt><dd>${plain ? esc(v) : v}</dd>`)
      .join("")}</dl>`;
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
      tk.tab = "";
      this._loadTakeover();
    } else if (e.target.dataset.tkStrategy) {
      this._tkSetStrategy(e.target.dataset.tkStrategy);
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
    const hit = (sel) => e.target.closest(sel);
    const tab = hit("[data-tk-tab]");
    const fold = hit("[data-tk-fold]");
    if (hit("[data-tk-go]")) {
      this._navigate(hit("[data-tk-go]").dataset.tkGo);
    } else if (tab) {
      if (tk.tab !== tab.dataset.tkTab) tk.q = "";
      tk.tab = tab.dataset.tkTab;
      this._renderTakeover();
      this.shadowRoot.getElementById("takeover").scrollIntoView?.({ block: "nearest" });
    } else if (hit("[data-tk-section]")) {
      tk.section = hit("[data-tk-section]").dataset.tkSection;
      tk.q = "";
      this._renderTakeover();
    } else if (hit("[data-tk-reports]")) {
      tk.section = "reports";
      tk.run = "";
      tk.q = "";
      this._tkLoadRuns().then(() => this._renderTakeover());
    } else if (hit("[data-tk-run]")) {
      tk.run = hit("[data-tk-run]").dataset.tkRun;
      tk.q = "";
      tk.confirm = "";
      tk.openRun = new Set();
      this._tkLoadRuns().then(() => this._renderTakeover());
    } else if (hit("[data-tk-run-back]")) {
      tk.run = "";
      tk.runData = null;
      tk.q = "";
      tk.confirm = "";
      this._renderTakeover();
    } else if (hit("[data-tk-del-yes]")) {
      this._tkDeleteRun(hit("[data-tk-del-yes]").dataset.tkDelYes);
    } else if (hit("[data-tk-del-no]")) {
      tk.confirm = "";
      this._renderTakeover();
    } else if (hit("[data-tk-del]")) {
      tk.confirm = hit("[data-tk-del]").dataset.tkDel;
      this._renderTakeover();
    } else if (fold) {
      const area = fold.dataset.tkFold;
      if (tk.folded.has(area)) tk.folded.delete(area);
      else tk.folded.add(area);
      this._renderTakeover();
    } else if (hit("[data-tk-not]")) {
      tk.showNot = !tk.showNot;
      this._renderTakeover();
    } else if (hit("[data-tk-all]")) {
      const all = hit("[data-tk-all]").dataset.tkAll === "all";
      tk.selected = new Set(all ? this._tkDevices().filter((d) => d.ready).map((d) => d.id) : []);
      this._renderTakeover();
    } else if (hit("[data-tk-expand]")) {
      const all = hit("[data-tk-expand]").dataset.tkExpand === "all";
      tk.open = new Set(all ? this._tkDevices().filter((d) => tk.selected.has(d.id)).map((d) => d.id) : []);
      this._renderTakeover();
    } else if (hit("[data-tk-confirm]")) {
      this._takeOver();
    } else if (hit("[data-tk-later-run]")) {
      this._tkCarryLater();
    } else if (hit("[data-tk-recheck]")) {
      this._tkRecheck();
    } else if (hit("[data-tk-copy]")) {
      this._copyMapping();
    } else if (hit("[data-tk-csv]")) {
      this._downloadMapping();
    } else if (hit("[data-tk-restore]")) {
      this._tkRestore();
    } else {
      const row = hit("[data-tk-open]");
      const runRow = hit("[data-tk-open-run]");
      if ((row || runRow) && !this._selecting(this.shadowRoot.getElementById("takeover"))) {
        const set = row ? tk.open : tk.openRun;
        const id = row ? row.dataset.tkOpen : runRow.dataset.tkOpenRun;
        if (set.has(id)) set.delete(id);
        else set.add(id);
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
    // something taken over: on to retiring the old integration
    tk.tab = result?.count ? "release" : "select";
    tk.q = "";
    await this._refreshStatus();
    await this._loadTakeover();
    // no old entity found for what was taken over: nothing to retire, stay with the selection
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
      this._notice(t.tkCarried(carried), true);
    } catch (err) {
      this._notice(t.tkErrors[err.code] || t.tkErrors.unknown);
    }
    tk.busy = false;
    await this._tkRecheck();
  },

  async _tkSetStrategy(strategy) {
    const tk = this._tk;
    try {
      await this._hass.callWS({ type: "enocean_eltako/takeover/strategy", entry_id: tk.entry, strategy });
      if (tk.mapping) tk.mapping.strategy = strategy;
    } catch (err) {
      this._notice(this._t.tkErrors[err.code] || this._t.tkErrors.unknown);
    }
    this._renderTakeover();
    this._checkTakeover();
  },

  async _tkRestore() {
    // the new entities get the old entity IDs back
    const t = this._t;
    const tk = this._tk;
    if (tk.busy) return;
    tk.busy = true;
    this._renderTakeover();
    try {
      const { restored, blocked, in_use: inUse } = await this._hass.callWS({ type: "enocean_eltako/takeover/restore", entry_id: tk.entry });
      this._notice(t.tkRelease.restoreResult(restored, blocked, inUse), !blocked && !inUse);
    } catch (err) {
      this._notice(t.tkErrors[err.code] || t.tkErrors.unknown);
    }
    tk.busy = false;
    await this._tkRecheck();
  },

  async _tkDeleteRun(id) {
    const tk = this._tk;
    if (tk.busy) return;
    tk.busy = true;
    try {
      await this._hass.callWS({ type: "enocean_eltako/takeover/report_delete", run_id: id });
      this._notice(this._t.tkReportsView.deleted, true);
    } catch (err) {
      this._notice(this._t.tkErrors[err.code] || this._t.tkErrors.unknown);
    }
    tk.busy = false;
    tk.confirm = "";
    if (tk.run === id) tk.run = "";
    await this._tkLoadRuns();
    this._renderTakeover();
    this._checkTakeover();
  },

  _mappingTable() {
    const t = this._t;
    const head = [t.tkColDevice, "ID", t.tkColOld, t.tkColNew, t.tkColState, t.tkAutomations, t.tkScripts, t.tkScenes, t.tkDashboards];
    const names = (places) => places.map((p) => p.name).join("; ");
    const rows = this._tk.runData?.rows || [];
    const lines = rows.map((r) => [
      r.device, r.id, r.old, r.new || "", !r.taken ? t.tkNotTaken : r.restored ? t.tkRestoredState : isUsed(r) ? t.tkPlaces(this._tkPlaceCount([r])) : t.tkFree,
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
