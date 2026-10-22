// The Takeover view of the panel: devices of the old eltako integration set up here, then the
// mapping of old to new entity IDs. Its methods are added to the panel class (this = the panel).

const VERSION = new URL(import.meta.url).search;
const { ICON, csv, esc, svg } = await import(`./shared.js${VERSION}`);

// where an old entity ID of the takeover mapping is still used
const USAGE_KINDS = ["automation", "script", "scene", "dashboard"];
const OLD_INTEGRATION = "/config/integrations/integration/eltako";
const isUsed = (row) => USAGE_KINDS.some((k) => row.usage[k].length);

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
  .takeover .carry { grid-area: carry; display: flex; gap: 6px; align-items: center; font-size: 12px; color: var(--muted); }
  .takeover table { width: 100%; border-collapse: collapse; font-size: 12px; table-layout: fixed; }
  .takeover th { text-align: left; font-weight: 400; font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: .03em; padding: 8px 12px; }
  .takeover td { padding: 6px 12px; vertical-align: top; overflow-wrap: anywhere; }
  .takeover tbody.block { border-top: 1px solid var(--line); }
  .takeover tbody.block tr:first-child td { padding-top: 10px; }
  .takeover tbody.block tr:last-child td { padding-bottom: 10px; }
  .takeover tr.more .fold { font-size: 12px; font-weight: 400; color: var(--muted); }
  .takeover tr.map { cursor: pointer; }
  .takeover tr.map:hover { background: color-mix(in srgb, var(--soft) 60%, transparent); }
  .takeover .old { color: var(--muted); }
  .takeover .chip-s { display: inline-block; font-size: 11px; padding: 1px 7px; border-radius: 999px; margin: 0 4px 2px 0; background: var(--soft); }
  .takeover .chip-s.used { background: color-mix(in srgb, var(--warn) 25%, transparent); }
  .takeover .chip-s.ok { background: color-mix(in srgb, var(--ok) 20%, transparent); }
  .takeover .where td { background: var(--soft); font-size: 12px; }
  @media (max-width: 760px) {
    /* phones: the main button gets the whole width */
    .takeover .actionbar { grid-template-columns: minmax(0, 1fr) auto; grid-template-areas: "count all" "carry carry" "run run"; }
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

  _tkDevices() {
    // an ID listed twice in the old configuration: the first entry is the device
    const seen = new Map();
    for (const d of this._tk.preview?.devices || []) if (!seen.has(d.id)) seen.set(d.id, d);
    return [...seen.values()];
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
    const oldActive = !!(tk.mapping?.old_active ?? tk.preview?.old_active);
    const st = t.tkStepState;
    const mapping = tk.tab === "mapping";
    const steps = [
      { text: ready.length ? st.todo(ready.length) : taken.size ? st.done(taken.size, devices.length || taken.size) : "–", done: !ready.length && taken.size > 0, cur: !mapping, tab: "preview" },
      { text: st.check, cur: mapping, tab: "mapping", off: !rows.length },
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
    const body = mapping ? this._renderMapping(rows, oldActive, select) : this._renderPreview(devices, ready, select);
    this._replace(container, `<div class="steps">${stepsHtml}</div>${body}`);
    container.querySelectorAll("[data-partial]").forEach((box) => { box.indeterminate = true; });
  },

  _tkMatches(...fields) {
    const q = this._tk.q.trim().toLowerCase();
    return !q || fields.some((f) => String(f || "").toLowerCase().includes(q));
  },

  _tkToolbar(select, pills, attr, active, extra = "") {
    const t = this._t;
    const pillHtml = pills
      .map(([key, label, n]) => `<button class="pill" ${attr}="${key}" aria-pressed="${key === active}">${esc(label)} ${n}</button>`)
      .join("");
    return `<div class="toolbar">${select}${pillHtml}<input class="search" id="tkSearch" type="search" placeholder="${esc(t.tkSearch)}" value="${esc(this._tk.q)}" aria-label="${esc(t.tkSearch)}">${extra}</div>`;
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

  _renderPreview(devices, ready, select) {
    const t = this._t;
    const tk = this._tk;
    if (tk.previewError) return `<p class="banner">${esc(t.tkErrors[tk.previewError] || t.tkErrors.unknown)}</p>`;
    const lists = {
      ready,
      exists: devices.filter((d) => d.reason === "takeover_exists"),
      not: devices.filter((d) => !d.ready && d.reason !== "takeover_exists"),
    };
    const labels = { ready: t.tkReady, exists: t.tkExists, not: t.tkNot };
    const pills = Object.keys(lists).filter((k) => k === "ready" || lists[k].length).map((k) => [k, labels[k], lists[k].length]);
    const active = pills.some(([k]) => k === tk.filter) ? tk.filter : "ready";
    const visible = lists[active].filter((d) => this._tkMatches(d.name, d.id, d.area, ...(d.labels || [])));
    const toolbar = this._tkToolbar(select, pills, "data-tk-filter", active);
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
                  ${(d.labels || []).map((l) => `<span class="chip-s">${esc(l)}</span>`).join("")}</label>`)
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
    const picked = ready.filter((d) => tk.selected.has(d.id)).length;
    const bar = ready.length
      ? `<div class="actionbar"><b class="bar-count">${esc(t.tkSelected(picked, ready.length))}</b>
          <button class="chip bar-all" data-tk-all="${picked === ready.length ? "none" : "all"}">${esc(picked === ready.length ? t.tkSelectNone : t.tkSelectAll)}</button>
          <button class="chip primary bar-run" data-tk-run ${picked && !tk.busy ? "" : "disabled"}>${esc(tk.busy ? t.tkBusy : picked ? t.tkRun(picked) : t.tkNothing)}</button>
          <label class="carry"><input type="checkbox" id="tkCarry"${tk.carry ? " checked" : ""}>${esc(t.tkCarry)}</label></div>`
      : "";
    return `${toolbar}${list}${bar}`;
  },

  _renderMapping(rows, oldActive, select) {
    const t = this._t;
    const tk = this._tk;
    if (!rows.length) return this._emptyState(ICON.check, t.tkEmpty, "", "", true);
    const used = rows.filter(isUsed).length;
    const pills = [["all", t.tkFilterAll, rows.length], ["used", t.tkFilterUsed, used], ["unused", t.tkFilterUnused, rows.length - used]];
    const active = tk.mfilter;
    const visible = rows.filter((r) => (active === "all" || (active === "used") === isUsed(r)) && this._tkMatches(r.device, r.id, r.old, r.new, r.area));
    const extra = `<button class="chip" data-tk-copy>${svg(ICON.copy)}${esc(t.tkCopy)}</button><button class="chip" data-tk-csv>${svg(ICON.download)}${esc(t.tkCsv)}</button>`;
    const usageChips = (r) => {
      const chips = USAGE_KINDS
        .filter((k) => r.usage[k].length)
        .map((k) => `<span class="chip-s used">${esc(t.tkUsage[k](r.usage[k].length))}</span>`)
        .join("");
      return chips || `<span class="chip-s ok">${esc(t.tkUnused)}</span>`;
    };
    const line = (r, first) => {
      const open = tk.open.has(r.old);
      const where = open && isUsed(r)
        ? `<tr class="where"><td colspan="3"><b>${esc(t.tkWhere)}:</b> ${USAGE_KINDS.filter((k) => r.usage[k].length).map((k) => `${esc(t.tkUsage[k](r.usage[k].length))}: ${esc(r.usage[k].join(", "))}`).join(" · ")}</td></tr>`
        : "";
      const target = r.new ? esc(r.new) : `<span class="old">${esc(r.taken ? t.tkNoNew : t.tkNotTaken)}</span>`;
      return `<tr class="map" data-tk-open="${esc(r.old)}">
        <td>${first ? `${esc(r.device)}<div class="sub">${esc([r.area, r.taken ? "" : t.tkNotTaken].filter(Boolean).join(" · "))}</div>` : ""}</td>
        <td class="mono"><span class="old">${esc(r.old)}</span><br>→ ${target}</td>
        <td>${usageChips(r)}</td></tr>${where}`;
    };
    // one block per device; side entities with no counterpart and no use fold away while
    // the whole, unsearched list is shown
    const blocks = new Map();
    for (const r of visible) {
      if (!blocks.has(r.id)) blocks.set(r.id, []);
      blocks.get(r.id).push(r);
    }
    const folding = active === "all" && !tk.q.trim();
    const body = [...blocks.entries()]
      .map(([id, items]) => {
        const minor = folding ? items.filter((r) => !r.primary && !r.new && !isUsed(r)) : [];
        const open = tk.more.has(id);
        const shown = open ? items : items.filter((r) => !minor.includes(r));
        const toggle = minor.length
          ? `<tr class="more"><td></td><td colspan="2"><button class="fold" data-tk-more="${esc(id)}" aria-expanded="${open}"><span aria-hidden="true">${open ? "▾" : "▸"}</span> ${esc(open ? t.tkLess : t.tkMore(minor.length))}</button></td></tr>`
          : "";
        return `<tbody class="block">${shown.map((r, i) => line(r, i === 0)).join("")}${toggle}</tbody>`;
      })
      .join("");
    return `${this._tkToolbar(select, pills, "data-tk-mfilter", active, extra)}
      <p class="banner ${oldActive ? "" : "ok"}">${esc(oldActive ? t.tkOldActive : t.tkOldGone)}</p>
      ${visible.length ? `<table><colgroup><col style="width:26%"><col style="width:40%"><col style="width:34%"></colgroup>
        <thead><tr><th>${esc(t.tkColDevice)}</th><th>${esc(t.tkColOld)} → ${esc(t.tkColNew)}</th><th>${esc(t.tkColUsed)}</th></tr></thead>${body}</table>` : this._emptyState(ICON.search, t.tkNoMatch, "", "", true)}`;
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
      this._loadTakeover();
    } else if (e.target.id === "tkCarry") {
      tk.carry = e.target.checked;
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
    const more = e.target.closest("[data-tk-more]");
    if (more) {
      const id = more.dataset.tkMore;
      if (tk.more.has(id)) tk.more.delete(id);
      else tk.more.add(id);
      this._renderTakeover();
    } else if (tab) {
      if (tk.tab !== tab.dataset.tkTab) tk.q = "";
      tk.tab = tab.dataset.tkTab;
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
    } else if (e.target.closest("[data-tk-go]")) {
      this._navigate(e.target.closest("[data-tk-go]").dataset.tkGo);
    } else if (e.target.closest("[data-tk-run]")) {
      this._takeOver();
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
        carry_over: tk.carry,
      });
    } catch (err) {
      this._notice(t.tkErrors[err.code] || t.tkErrors.unknown);
    }
    tk.busy = false;
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

  _mappingTable() {
    const t = this._t;
    const head = [t.tkColDevice, "ID", t.tkColOld, t.tkColNew, t.tkAutomations, t.tkScripts, t.tkScenes, t.tkDashboards];
    const lines = (this._tk.mapping?.rows || []).map((r) => [
      r.device, r.id, r.old, r.new || "", r.usage.automation.join("; "), r.usage.script.join("; "), r.usage.scene.join("; "), r.usage.dashboard.join("; "),
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
