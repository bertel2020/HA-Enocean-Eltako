// The Takeover view of the panel: devices of the old eltako integration set up here, then an
// overview of the devices set up, with the mapping of old to new entity IDs and where the old
// ones are still used. Its methods are added to the panel class (this = the panel).

const VERSION = new URL(import.meta.url).search;
const { ICON, csv, esc, svg } = await import(`./shared.js${VERSION}`);

// where an old entity ID of the takeover mapping is still used
const USAGE_KINDS = ["automation", "script", "scene", "dashboard"];
const OLD_INTEGRATION = "/config/integrations/integration/eltako";
const isUsed = (row) => USAGE_KINDS.some((k) => row.usage[k].length);
// what can be carried over from the old integration, each chosen on its own
const CARRY_OPTIONS = ["area", "labels", "voice", "names", "icons", "visibility"];
const CARRY_KEY = "enocean_eltako_takeover_carry"; // the chosen options, per browser

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
  open: new Set(), busy: false, confirm: false, filter: "ready", mfilter: "all", mview: "device", later: false, q: "", folded: new Set(),
});

export const TAKEOVER_STYLE = `
  .takeover { padding-bottom: 8px; }
  .takeover .steps { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; padding: 14px 16px 12px; border-bottom: 1px solid var(--line); }
  .takeover .step { display: flex; gap: 8px; align-items: flex-start; text-align: left; font: inherit; font-size: 12px; color: var(--muted); background: none; border: 0; padding: 0; }
  .takeover button.step { cursor: pointer; }
  .takeover button.step[data-tk-go] .num { border-color: var(--warn); color: var(--warn); }
  .takeover button.step[data-tk-go]:hover b { color: var(--accent); }
  .takeover button.step:disabled { cursor: default; opacity: .6; }
  .takeover .step b { display: block; font-weight: 500; font-size: 13px; color: var(--text); }
  .takeover .num { flex: none; width: 22px; height: 22px; border-radius: 50%; border: 1px solid var(--line); display: flex; align-items: center; justify-content: center; font-size: 12px; }
  .takeover .step.cur .num { border-color: var(--accent); color: var(--accent); background: color-mix(in srgb, var(--accent) 10%, var(--surface)); }
  .takeover .step.done .num { border-color: var(--ok); color: var(--ok); background: color-mix(in srgb, var(--ok) 15%, var(--surface)); }
  .takeover .toolbar { padding: 10px 16px; display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
  /* filter pills and search as in the other views */
  .takeover .pill { height: 32px; padding: 0 14px; border-radius: 20px; border: 1px solid var(--input-line); font-size: 13px; font-weight: 500; color: var(--accent); background: var(--surface); white-space: nowrap; }
  .takeover .pill:hover { background: var(--accent-soft); }
  .takeover .pill[aria-pressed="true"] { border-color: var(--accent); color: var(--accent-hover); background: var(--accent-soft); }
  .takeover .search { flex: 1; min-width: 140px; height: 38px; border-radius: 10px; border: 1px solid var(--input-line); background: var(--surface);
    color: var(--text); font: inherit; font-size: 14px; padding: 0 12px; }
  .takeover .banner { margin: 0 16px 10px; padding: 8px 12px; border-radius: 8px; font-size: 12px; background: color-mix(in srgb, var(--warn) 18%, transparent); }
  .takeover .banner.ok { background: color-mix(in srgb, var(--ok) 15%, transparent); }
  .takeover .group { display: flex; gap: 10px; align-items: center; padding: 7px 16px; border-top: 1px solid var(--line); background: var(--soft); font-size: 12px; }
  .takeover .group .sub { margin-left: auto; }
  .takeover .fold { font: inherit; font-weight: 500; color: var(--text); background: none; border: 0; padding: 0; cursor: pointer; }
  .takeover .pickrow { display: flex; gap: 10px; align-items: center; padding: 6px 16px 6px 40px; border-top: 1px solid var(--line); font-size: 13px; cursor: pointer; }
  .takeover .pick-name { flex: 1; }
  .takeover .sub { color: var(--muted); font-size: 12px; }
  .takeover .skiprow { display: flex; justify-content: space-between; gap: 12px; padding: 6px 16px; font-size: 13px; color: var(--muted); border-top: 1px solid var(--line); }
  .takeover .actionbar { position: sticky; bottom: 0; display: grid; grid-template-columns: minmax(0, 1fr) auto auto;
    grid-template-areas: "count all run" "carry carry carry"; align-items: center; gap: 6px 12px; padding: 10px 16px;
    border-top: 1px solid var(--line); background: var(--soft); }
  .takeover .bar-count { grid-area: count; font-size: 13px; font-weight: 500; }
  .takeover .bar-all { grid-area: all; }
  .takeover .bar-run { grid-area: run; }
  .takeover .carry { grid-area: carry; display: flex; flex-direction: column; gap: 6px; font-size: 12px; }
  .takeover .opts { display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 4px 16px; }
  .takeover .opt { display: flex; gap: 6px; align-items: center; color: var(--text); }
  .takeover .opt small { margin-left: auto; color: var(--muted); }
  .takeover .opt.off { color: var(--muted); }
  .takeover .actionbar.later { position: static; grid-template-areas: "count all all" "carry carry carry"; }
  .takeover .actionbar.later .bar-all { justify-self: end; }
  .takeover .actionbar.later .carry > .chip { align-self: flex-start; }
  .takeover .hint { margin: 0 16px 10px; padding: 7px 12px; border-radius: 8px; font-size: 12px; color: var(--muted); background: var(--soft);
    display: flex; flex-wrap: wrap; gap: 4px 12px; align-items: center; }
  .takeover .link { margin-left: auto; font: inherit; font-weight: 500; color: var(--accent); background: none; border: 0; padding: 0; cursor: pointer; }
  .takeover .link:hover { color: var(--accent-hover); text-decoration: underline; }
  .takeover .seg { display: inline-flex; border: 1px solid var(--input-line); border-radius: 20px; overflow: hidden; }
  .takeover .seg button { height: 30px; padding: 0 12px; font: inherit; font-size: 13px; color: var(--muted); background: var(--surface); border: 0; cursor: pointer; }
  .takeover .seg button[aria-pressed="true"] { color: var(--accent-hover); background: var(--accent-soft); font-weight: 500; }
  .takeover .devblock { border-top: 1px solid var(--line); }
  .takeover .devhead { display: flex; flex-wrap: wrap; gap: 4px 10px; align-items: center; padding: 8px 16px; font-size: 13px; }
  .takeover .devhead[data-tk-open] { cursor: pointer; }
  .takeover .devhead[data-tk-open]:hover { background: color-mix(in srgb, var(--soft) 60%, transparent); }
  .takeover .devhead b { font-weight: 500; }
  .takeover .devchips { display: flex; flex-wrap: wrap; }
  .takeover .devstate { margin-left: auto; }
  .takeover .ents { padding: 0 16px 8px 34px; }
  .takeover .ent { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 4px 12px; padding: 6px 0; border-top: 1px dashed var(--line); font-size: 12px; overflow-wrap: anywhere; }
  .takeover .old { color: var(--muted); }
  .takeover .chip-s { display: inline-block; font-size: 11px; padding: 1px 7px; border-radius: 999px; margin: 0 4px 2px 0; background: var(--soft); color: var(--text); }
  .takeover .chip-s.used { background: color-mix(in srgb, var(--warn) 25%, transparent); }
  .takeover .chip-s.ok { background: color-mix(in srgb, var(--ok) 20%, transparent); }
  .takeover .chip-s.avail { color: var(--muted); border: 1px dashed var(--line); background: none; }
  .takeover button.chip-s { font: inherit; font-size: 11px; border: 0; cursor: pointer; text-align: left; }
  .takeover button.chip-s:hover { text-decoration: underline; }
  .takeover .confirm-head { padding: 12px 16px 10px; }
  .takeover .confirm-head b { display: block; font-size: 15px; font-weight: 500; margin-bottom: 2px; }
  .takeover .stats { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; padding: 0 16px 10px; }
  .takeover .stat { border-radius: 8px; padding: 6px 12px; background: var(--soft); font-size: 12px; color: var(--muted); }
  .takeover .stat b { display: block; font-size: 20px; font-weight: 500; color: var(--text); }
  .takeover .stat.warn b { color: var(--warn); }
  .takeover .confirm-carry { display: flex; flex-wrap: wrap; gap: 4px 6px; align-items: center; padding: 0 16px 10px; font-size: 12px; }
  .takeover .idhead { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 12px; padding: 6px 16px; border-top: 1px solid var(--line); font-size: 12px; color: var(--muted); }
  .takeover .confirm-dev { border-top: 1px solid var(--line); padding: 8px 16px; font-size: 13px; }
  .takeover .confirm-dev > b { font-weight: 500; }
  .takeover .idrow { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 2px 12px; padding: 3px 0; font-size: 12px; overflow-wrap: anywhere; }
  .takeover .confirm-bar { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 8px; padding: 10px 16px; border-top: 1px solid var(--line); background: var(--soft); }
  @media (max-width: 760px) {
    .takeover .idhead { display: none; }
    .takeover .idrow { grid-template-columns: minmax(0, 1fr); padding: 4px 0; }
    .takeover .confirm-bar button { flex: 1; justify-content: center; }
    /* phones: the main button gets the whole width */
    .takeover .actionbar { grid-template-columns: minmax(0, 1fr) auto; grid-template-areas: "count all" "carry carry" "run run"; }
    .takeover .actionbar.later { grid-template-areas: "count all" "carry carry"; }
    .takeover .ent { grid-template-columns: minmax(0, 1fr); }
    .takeover .bar-run { justify-content: center; }
    /* the steps one below the other: name and state on one line */
    .takeover .steps { grid-template-columns: minmax(0, 1fr); gap: 10px; }
    .takeover .step { align-items: center; }
    .takeover .step b { display: inline; margin-right: 6px; }
  }
`;

export const takeover = {
  async _checkTakeover() {
    // the Takeover view exists only while there is something to take over or to look up
    try {
      const { available } = await this._hass.callWS({ type: "enocean_eltako/takeover/status" });
      const button = this.shadowRoot.querySelector('#view button[data-view="takeover"]');
      if (button) button.hidden = !available;
      if (!available && this._view === "takeover") this._setView("telegrams");
    } catch (err) {
      // not an admin or the integration is still starting: no view
    }
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
    const ready = (tk.preview?.devices || []).filter((d) => d.ready);
    tk.selected = new Set(ready.map((d) => d.id));
    tk.filter = "ready";
    if (!tk.tab || !tk.mapping?.rows.length) tk.tab = ready.length || !tk.mapping?.rows.length ? "preview" : "mapping";
    this._renderTakeover();
  },

  async _tkRecheck() {
    // the overview again, after references were switched over elsewhere
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
    // the overview's rows by device, in their order
    const blocks = new Map();
    for (const r of rows) {
      if (!blocks.has(r.id)) blocks.set(r.id, []);
      blocks.get(r.id).push(r);
    }
    return blocks;
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
    const devices = this._tkDevices();
    const ready = devices.filter((d) => d.ready);
    const rows = tk.mapping?.rows || [];
    const taken = new Set(rows.filter((r) => r.taken).map((r) => r.id));
    const used = new Set(rows.filter(isUsed).map((r) => r.id)).size;
    const oldActive = !!(tk.mapping?.old_active ?? tk.preview?.old_active);
    const st = t.tkStepState;
    const mapping = tk.tab === "mapping";
    const steps = [
      { text: ready.length ? st.todo(ready.length) : taken.size ? st.done(taken.size, devices.length || taken.size) : "–", done: !ready.length && taken.size > 0, cur: !mapping, tab: "preview" },
      { text: used ? st.used(used) : st.check, cur: mapping, tab: "mapping", off: !rows.length },
      // while the old integration runs, the step opens its page, where it can be switched off
      { text: oldActive ? st.oldOn : st.oldOff, done: !oldActive && taken.size > 0, go: oldActive ? OLD_INTEGRATION : "" },
    ];
    const stepsHtml = steps
      .map((s, i) => {
        const cls = `step${s.done ? " done" : ""}${s.cur ? " cur" : ""}`;
        const inner = `<span class="num">${s.done ? "✓" : i + 1}</span><span><b>${esc(t.tkSteps[i])}</b>${esc(s.text)}</span>`;
        if (s.tab) return `<button class="${cls}" data-tk-tab="${s.tab}"${s.cur ? ' aria-current="step"' : ""}${s.off ? " disabled" : ""}>${inner}</button>`;
        if (s.go) return `<button class="${cls}" data-tk-go="${esc(s.go)}">${inner}</button>`;
        return `<div class="${cls}">${inner}</div>`;
      })
      .join("");
    const select = gateways.length > 1
      ? `<select class="select" id="tkGateway" aria-label="${esc(t.gateway)}">${gateways
          .map((g) => `<option value="${esc(g.entry_id)}"${g.entry_id === tk.entry ? " selected" : ""}>${esc(g.title)}</option>`)
          .join("")}</select>`
      : "";
    const body = mapping ? this._renderMapping(rows, oldActive, select) : this._renderPreview(devices, ready, select, rows.length > 0);
    this._replace(container, `<div class="steps">${stepsHtml}</div>${body}`);
    container.querySelectorAll("[data-partial]").forEach((box) => { box.indeterminate = true; });
  },

  _tkMatches(...fields) {
    const q = this._tk.q.trim().toLowerCase();
    return !q || fields.some((f) => String(f || "").toLowerCase().includes(q));
  },

  _tkToolbar(select, pills, attr, active, extra = "", lead = "") {
    const t = this._t;
    const pillHtml = pills
      .map(([key, label, n]) => `<button class="pill" ${attr}="${key}" aria-pressed="${key === active}">${esc(label)} ${n}</button>`)
      .join("");
    return `<div class="toolbar">${select}${lead}${pillHtml}<input class="search" id="tkSearch" type="search" placeholder="${esc(t.tkSearch)}" value="${esc(this._tk.q)}" aria-label="${esc(t.tkSearch)}">${extra}</div>`;
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
    // one checkbox per option with the number of devices it concerns; none to carry: greyed out
    const t = this._t;
    return `<div class="opts">${CARRY_OPTIONS.map((o) => {
      const n = counts[o] || 0;
      return `<label class="opt${n ? "" : " off"}"><input type="checkbox" ${attr}="${o}"${this._tk.carry.has(o) ? " checked" : ""}${n ? "" : " disabled"}>${esc(t.tkCarryOpt[o])}<small>${n}</small></label>`;
    }).join("")}</div>`;
  },

  _renderPreview(devices, ready, select, overview) {
    const t = this._t;
    const tk = this._tk;
    if (tk.previewError) return `<p class="banner">${esc(t.tkErrors[tk.previewError] || t.tkErrors.unknown)}</p>`;
    const chosen = ready.filter((d) => tk.selected.has(d.id));
    if (tk.confirm && chosen.length) return this._tkRenderConfirm(chosen);
    // devices already set up are not offered here: they are in the overview of step 2
    const exists = devices.filter((d) => d.reason === "takeover_exists").length;
    const lists = { ready, not: devices.filter((d) => !d.ready && d.reason !== "takeover_exists") };
    const labels = { ready: t.tkReady, not: t.tkNot };
    const pills = Object.keys(lists).filter((k) => k === "ready" || lists[k].length).map((k) => [k, labels[k], lists[k].length]);
    const active = pills.some(([k]) => k === tk.filter) ? tk.filter : "ready";
    const visible = lists[active].filter((d) => this._tkMatches(d.name, d.id, d.area, ...(d.labels || [])));
    const toolbar = this._tkToolbar(select, pills, "data-tk-filter", active);
    const hint = exists
      ? `<p class="hint">${esc(t.tkExistsHint(exists))}${overview ? `<button class="link" data-tk-tab="mapping">${esc(t.tkToOverview)}</button>` : ""}</p>`
      : "";
    let list;
    if (!visible.length) {
      list = this._emptyState(ICON.search, t.tkNoMatch, "", "", true);
    } else if (active === "ready") {
      const q = tk.q.trim();
      list = this._tkGroups(visible)
        .map((g) => {
          const picked = g.items.filter((d) => tk.selected.has(d.id)).length;
          const folded = !q && tk.folded.has(g.area);
          const rowsHtml = folded
            ? ""
            : g.items
                .map((d) => `<label class="pickrow"><input type="checkbox" data-tk-pick="${esc(d.id)}"${tk.selected.has(d.id) ? " checked" : ""}>
                  <span class="pick-name">${esc(d.name)} <span class="sub mono">${esc(d.id)}</span></span>
                  ${(d.labels || []).map((l) => `<span class="chip-s">${esc(l)}</span>`).join("")}
                  ${(d.carry || []).filter((o) => o !== "area" && o !== "labels").map((o) => `<span class="chip-s">${esc(t.tkCarryOpt[o])}</span>`).join("")}
                  ${d.used ? `<span class="chip-s used">${esc(t.tkPlaces(d.used))}</span>` : ""}</label>`)
                .join("");
          return `<div class="group"><input type="checkbox" data-tk-group="${esc(g.area)}" aria-label="${esc(g.area || t.tkNoArea)}"${picked === g.items.length ? " checked" : ""}${picked && picked < g.items.length ? " data-partial" : ""}>
            <button class="fold" data-tk-fold="${esc(g.area)}" aria-expanded="${!folded}"><span aria-hidden="true">${folded ? "▸" : "▾"}</span> ${esc(g.area || t.tkNoArea)}</button>
            <span class="sub">${esc(t.tkGroupCount(picked, g.items.length))}</span></div>${rowsHtml}`;
        })
        .join("");
    } else {
      list = visible
        .map((d) => `<div class="skiprow"><span>${esc(d.name)} <span class="mono">${esc(d.id)}</span></span><span>${esc(t.tkReasons[d.reason] || d.reason || "")}</span></div>`)
        .join("");
    }
    const picked = chosen.length;
    const counts = Object.fromEntries(CARRY_OPTIONS.map((o) => [o, chosen.filter((d) => (d.carry || []).includes(o)).length]));
    const bar = ready.length
      ? `<div class="actionbar"><b class="bar-count">${esc(t.tkSelected(picked, ready.length))}</b>
          <button class="chip bar-all" data-tk-all="${picked === ready.length ? "none" : "all"}">${esc(picked === ready.length ? t.tkSelectNone : t.tkSelectAll)}</button>
          <button class="chip primary bar-run" data-tk-run ${picked && !tk.busy ? "" : "disabled"}>${esc(tk.busy ? t.tkBusy : picked ? t.tkRun(picked) : t.tkNothing)}</button>
          <div class="carry"><span class="sub">${esc(t.tkCarryTitle)}</span>${this._tkCarryOptions(counts, "data-tk-carry")}</div></div>`
      : "";
    return `${toolbar}${hint}${list}${bar}`;
  },

  _tkPlaceChip(kind, place) {
    // a place that uses an old ID; one with an editor opens it
    const label = `${this._t.tkKind[kind]}: ${place.name}`;
    return place.path
      ? `<button class="chip-s used place" data-tk-go="${esc(place.path)}" title="${esc(this._t.tkEdit)}">${esc(label)}</button>`
      : `<span class="chip-s used">${esc(label)}</span>`;
  },

  _renderMapping(rows, oldActive, select) {
    const t = this._t;
    const tk = this._tk;
    if (!rows.length) return this._emptyState(ICON.check, t.tkEmpty, "", "", true);
    const blocks = this._tkBlocks(rows);
    const missing = tk.mapping?.missing || {};
    const usedIds = new Set(rows.filter(isUsed).map((r) => r.id));
    const doneIds = [...blocks.entries()].filter(([id, items]) => items[0].taken && !usedIds.has(id));
    const lead = `<span class="seg" role="group">${["device", "place"]
      .map((v) => `<button data-tk-mview="${v}" aria-pressed="${tk.mview === v}">${esc(t.tkByView[v])}</button>`)
      .join("")}</span>`;
    const pills = tk.mview === "device"
      ? [["all", t.tkFilterAll, blocks.size], ["used", t.tkFilterUsed, usedIds.size], ["done", t.tkFilterDone, doneIds.length]]
      : [];
    const extra = `<button class="chip" data-tk-recheck>${esc(t.tkRecheck)}</button><button class="chip" data-tk-copy>${svg(ICON.copy)}${esc(t.tkCopy)}</button><button class="chip" data-tk-csv>${svg(ICON.download)}${esc(t.tkCsv)}</button>`;
    const toolbar = this._tkToolbar(select, pills, "data-tk-mfilter", tk.mfilter, extra, lead);
    const banner = `<p class="banner ${oldActive ? "" : "ok"}">${esc(oldActive ? t.tkOldActive : t.tkOldGone)}</p>`;
    const body = tk.mview === "place" ? this._tkRenderPlaces(rows) : this._tkRenderDevices(blocks, usedIds, missing);
    return `${toolbar}${banner}${body}${this._tkRenderLater(missing)}`;
  },

  _tkRenderConfirm(chosen) {
    // what "take over now" will do, before anything is written
    const t = this._t;
    const tk = this._tk;
    const entities = chosen.reduce((n, d) => n + (d.entities || []).length, 0);
    const places = new Set(chosen.flatMap((d) => d.places || [])).size;
    const carry = CARRY_OPTIONS.filter((o) => tk.carry.has(o) && chosen.some((d) => (d.carry || []).includes(o)));
    const devices = chosen
      .map((d) => {
        const meta = [d.area, d.used ? t.tkPlaces(d.used) : t.tkUnused].filter(Boolean).join(" · ");
        const rows = (d.entities || []).length
          ? d.entities
              .map((e) => `<div class="idrow"><span class="mono old">${esc(e.old)}</span>${e.new ? `<span class="mono">→ ${esc(e.new)}</span>` : `<span class="old">→ ${esc(t.tkNewLater)}</span>`}</div>`)
              .join("")
          : `<div class="idrow"><span class="old">${esc(t.tkNoOldEntities)}</span></div>`;
        return `<div class="confirm-dev"><b>${esc(d.name)}</b> <span class="sub"><span class="mono">${esc(d.id)}</span> · ${esc(meta)}</span>${rows}</div>`;
      })
      .join("");
    return `<div class="confirm-head"><b>${esc(t.tkConfirmTitle)}</b><span class="sub">${esc(t.tkConfirmNote)}</span></div>
      <div class="stats">
        <div class="stat">${esc(t.tkStatDevices)}<b>${chosen.length}</b></div>
        <div class="stat">${esc(t.tkStatEntities)}<b>${entities}</b></div>
        <div class="stat${places ? " warn" : ""}">${esc(t.tkStatPlaces)}<b>${places}</b></div>
      </div>
      <div class="confirm-carry"><span class="sub">${esc(t.tkConfirmCarry)}</span>${
        carry.length ? carry.map((o) => `<span class="chip-s">${esc(t.tkCarryOpt[o])}</span>`).join("") : `<span>${esc(t.tkCarryNone)}</span>`
      }</div>
      <div class="idhead"><span>${esc(t.tkColOldEntity)}</span><span>${esc(t.tkColNewProbable)}</span></div>
      ${devices}
      <p class="banner${places ? "" : " ok"}" style="margin-top:10px">${esc(t.tkConfirmPlaces(places))}</p>
      <div class="confirm-bar"><button class="chip" data-tk-back>${esc(t.tkBack)}</button>
        <button class="chip primary" data-tk-confirm ${tk.busy ? "disabled" : ""}>${esc(tk.busy ? t.tkBusy : t.tkRunNow)}</button></div>`;
  },

  _tkIdLine(r) {
    const target = r.new ? esc(r.new) : `<span class="old">${esc(r.taken ? this._t.tkNoNew : this._t.tkNotTaken)}</span>`;
    return `<span class="mono"><span class="old">${esc(r.old)}</span><br>→ ${target}</span>`;
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
        const places = new Set(items.flatMap((r) => USAGE_KINDS.flatMap((k) => r.usage[k].map((p) => `${k}:${p.name}`)))).size;
        const state = !first.taken
          ? `<span class="chip-s">${esc(t.tkNotTaken)}</span>`
          : places ? `<span class="chip-s used">${esc(t.tkPlaces(places))}</span>` : `<span class="chip-s ok">${esc(t.tkDoneState)}</span>`;
        const chips = [
          first.area ? `<span class="chip-s">${esc(first.area)}</span>` : "",
          ...(missing[id] || []).map((o) => `<span class="chip-s avail" title="${esc(t.tkAvailable)}">+ ${esc(t.tkCarryOpt[o])}</span>`),
        ].join("");
        const entities = open
          ? `<div class="ents">${items
              .map((r) => `<div class="ent">${this._tkIdLine(r)}<span>${USAGE_KINDS.flatMap((k) => r.usage[k].map((p) => this._tkPlaceChip(k, p))).join("") || `<span class="chip-s ok">${esc(t.tkUnused)}</span>`}</span></div>`)
              .join("")}</div>`
          : "";
        return `<div class="devblock"><div class="devhead" data-tk-open="${esc(id)}">
            <button class="fold" aria-expanded="${open}"><span aria-hidden="true">${open ? "▾" : "▸"}</span> ${esc(first.device)}</button>
            <span class="sub mono">${esc(id)}</span><span class="devchips">${chips}</span><span class="devstate">${state}</span></div>${entities}</div>`;
      })
      .join("");
    return html || this._emptyState(ICON.search, t.tkNoMatch, "", "", true);
  },

  _tkRenderPlaces(rows) {
    // the same rows by the automation, script, scene or dashboard that uses them: one place is
    // edited once for all its old IDs
    const t = this._t;
    const places = new Map();
    for (const r of rows) {
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
          <span class="devstate">${e.place.path ? `<button class="link" data-tk-go="${esc(e.place.path)}">${esc(t.tkEdit)}</button>` : `<span class="sub">${esc(t.tkNoEditor)}</span>`}</span></div>
          <div class="ents">${e.rows.map((r) => `<div class="ent">${this._tkIdLine(r)}<span class="sub">${esc(r.device)}</span></div>`).join("")}</div></div>`)
      .join("");
    if (html) return html;
    return places.size ? this._emptyState(ICON.search, t.tkNoMatch, "", "", true) : this._emptyState(ICON.check, t.tkNoPlaces, "", "", true);
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
      ? `<div class="carry">${this._tkCarryOptions(counts, "data-tk-carry")}
          <button class="chip primary" data-tk-later-run ${devices && !tk.busy ? "" : "disabled"}>${esc(tk.busy ? t.tkBusy : devices ? t.tkCarryRun(devices) : t.tkNothing)}</button></div>`
      : "";
    return `<div class="actionbar later"><span class="sub bar-count">${esc(summary)}</span>
      <button class="chip bar-all" data-tk-later aria-expanded="${tk.later}">${esc(t.tkCarryLater)}</button>${panel}</div>`;
  },

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
      tk.confirm = false;
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
        if (!d.ready || (d.area || "") !== area || !this._tkMatches(d.name, d.id, d.area, ...(d.labels || []))) continue;
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
    const filter = e.target.closest("[data-tk-filter], [data-tk-mfilter]");
    const mview = e.target.closest("[data-tk-mview]");
    if (e.target.closest("[data-tk-go]")) {
      this._navigate(e.target.closest("[data-tk-go]").dataset.tkGo);
    } else if (tab) {
      if (tk.tab !== tab.dataset.tkTab) tk.q = "";
      tk.confirm = false;
      tk.tab = tab.dataset.tkTab;
      this._renderTakeover();
    } else if (mview) {
      tk.mview = mview.dataset.tkMview;
      this._renderTakeover();
    } else if (filter) {
      if (filter.dataset.tkFilter) tk.filter = filter.dataset.tkFilter;
      else tk.mfilter = filter.dataset.tkMfilter;
      this._renderTakeover();
    } else if (fold) {
      const area = fold.dataset.tkFold;
      if (tk.folded.has(area)) tk.folded.delete(area);
      else tk.folded.add(area);
      this._renderTakeover();
    } else if (e.target.closest("[data-tk-all]")) {
      const all = e.target.closest("[data-tk-all]").dataset.tkAll === "all";
      tk.selected = new Set(all ? this._tkDevices().filter((d) => d.ready).map((d) => d.id) : []);
      this._renderTakeover();
    } else if (e.target.closest("[data-tk-run]")) {
      // first the confirmation: nothing is written before "take over now"
      tk.confirm = true;
      this._renderTakeover();
    } else if (e.target.closest("[data-tk-back]")) {
      tk.confirm = false;
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
    tk.confirm = false;
    // something taken over: on to step 2, the old IDs that still need switching over
    tk.tab = result?.count ? "mapping" : "";
    tk.mfilter = "all";
    tk.q = "";
    await this._refreshStatus();
    await this._loadTakeover();
    this._checkTakeover(); // nothing left to take over or to look up: the view goes
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

  _mappingTable() {
    const t = this._t;
    const head = [t.tkColDevice, "ID", t.tkColOld, t.tkColNew, t.tkAutomations, t.tkScripts, t.tkScenes, t.tkDashboards];
    const names = (places) => places.map((p) => p.name).join("; ");
    const lines = (this._tk.mapping?.rows || []).map((r) => [
      r.device, r.id, r.old, r.new || "", names(r.usage.automation), names(r.usage.script), names(r.usage.scene), names(r.usage.dashboard),
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
