// The Installation view of the panel: what is known of the installation, and what the user writes
// down about it. Three tabs: the devices by area or place, a table of the devices with typed
// fields that are edited in place (also for a selection, or pasted from a spreadsheet), and the
// event log. Everything comes from the documentation command; edits go back with set_fields. Its
// methods are added to the panel class (this = the panel).

const VERSION = new URL(import.meta.url).search;
const { ICON, esc, svg } = await import(`./shared.js${VERSION}`);

// the typed fields of a device, in table order; installed is a date
export const INSTALLATION_FIELDS = ["location", "circuit", "fuse", "installed", "revision", "power", "note"];
const TABS = ["areas", "devices", "log"];
const SAVE_DELAY = 600; // ms after the last key

// the view's state when the panel starts
export const installationState = () => ({
  doc: null, error: false, tab: "areas", group: "area", selected: new Set(), paste: "", pasteResult: "", q: "",
});

export const INSTALLATION_STYLE = `
  .installation { padding-bottom: 8px; }
  .installation .itop { display: flex; flex-wrap: wrap; gap: 8px 12px; align-items: center; padding: 12px 16px; border-bottom: 1px solid var(--line); }
  .installation .itop .tabs { display: flex; gap: 6px; flex: 1; flex-wrap: wrap; }
  .installation .itools { display: flex; gap: 6px; flex-wrap: wrap; }
  .installation .ibody { padding: 12px 16px; display: grid; gap: 16px; }
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
  .installation .itable input.cell:hover { border-color: var(--line); }
  .installation .itable input.cell:focus { border-color: var(--accent); outline: none; background: var(--surface); }
  .installation .itable input.cell.bad { border-color: var(--warn); }
  .installation input.isearch { width: 100%; max-width: 320px; box-sizing: border-box; font: inherit; font-size: 13px; padding: 6px 10px; border: 1px solid var(--line); border-radius: 8px; background: transparent; color: inherit; }
  .installation .bulk { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; padding: 8px 12px; border: 1px solid var(--accent); border-radius: 10px; background: var(--accent-soft); }
  .installation .bulk input, .installation .bulk select { font: inherit; font-size: 13px; padding: 4px 8px; border: 1px solid var(--line); border-radius: 6px; background: var(--surface); color: inherit; }
  .installation textarea.paste { width: 100%; min-height: 90px; box-sizing: border-box; font: 12px ui-monospace, monospace; padding: 8px; border: 1px solid var(--line); border-radius: 8px; background: transparent; color: inherit; }
  .installation .log td.kind { white-space: nowrap; }
  .installation .none { color: var(--muted); padding: 8px 0; }
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
    const el = this.shadowRoot.getElementById("installation");
    if (!el || this._view !== "installation") return;
    const t = this._t;
    const state = this._in;
    if (state.error) {
      this._replace(el, `<div class="ibody"><div class="none">${esc(t.inst.failed)}</div></div>`);
      return;
    }
    if (!state.doc) {
      this._replace(el, `<div class="ibody"><div class="none">${esc(t.loading)}</div></div>`);
      return;
    }
    const tab = `<button class="chip" data-in-tab="%s" aria-pressed="%p">%l</button>`;
    const tabs = TABS.map((name) => tab.replace("%s", name).replace("%p", String(state.tab === name)).replace("%l", esc(t.inst.tabs[name]))).join("");
    const tools = `<button class="chip" data-in-act="print">${svg(ICON.print)}${esc(t.inst.print)}</button>
      <button class="chip" data-in-act="csv">${svg(ICON.download)}CSV</button>
      <button class="chip" data-in-act="json">${svg(ICON.download)}JSON</button>
      <button class="chip" data-in-act="import">${svg(ICON.upload)}${esc(t.inst.import)}</button>`;
    const body = { areas: this._instAreas(), devices: this._instDevices(), log: this._instLog() }[state.tab];
    this._replace(el, `<div class="itop"><div class="tabs" role="group">${tabs}</div><div class="itools">${tools}</div></div><div class="ibody">${body}</div>`);
  },

  _instAreas() {
    const t = this._t;
    const state = this._in;
    const groupBy = `<div class="isub">${esc(t.inst.groupBy)} <button class="chip" data-in-group="area" aria-pressed="${state.group === "area"}">${esc(t.inst.byArea)}</button> <button class="chip" data-in-group="location" aria-pressed="${state.group === "location"}">${esc(t.inst.byPlace)}</button></div>`;
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
      return `<section><h3>${esc(gw.title)}</h3><div class="cards">${cards || `<div class="none">${esc(t.inst.noDevices)}</div>`}</div></section>`;
    });
    return groupBy + sections.join("");
  },

  _instDevices() {
    const t = this._t;
    const state = this._in;
    const columns = INSTALLATION_FIELDS;
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
      return `<section><h3>${esc(gw.title)}</h3><div class="tablewrap"><table class="itable"><thead><tr><th></th><th>${esc(t.inst.device)}</th>${head}</tr></thead><tbody>${rows || `<tr><td colspan="${columns.length + 2}" class="none">${esc(t.inst.noDevices)}</td></tr>`}</tbody></table></div></section>`;
    });
    const picked = state.selected.size;
    const bulk = picked
      ? `<div class="bulk"><b>${esc(t.inst.selected(picked))}</b><select data-in-bulk-field aria-label="${esc(t.inst.setField)}">${INSTALLATION_FIELDS.map((f) => `<option value="${f}">${esc(label(t, f))}</option>`).join("")}</select><input data-in-bulk-value placeholder="${esc(t.inst.value)}" aria-label="${esc(t.inst.value)}"><button class="chip" data-in-act="bulk">${esc(t.inst.apply)}</button><button class="chip" data-in-act="unpick">${esc(t.inst.clearSelection)}</button></div>`
      : "";
    const paste = `<details><summary>${esc(t.inst.pasteTitle)}</summary><div style="display:grid;gap:8px;margin-top:8px"><span class="isub">${esc(t.inst.pasteHint)}</span><textarea class="paste" data-in-paste placeholder="${esc(t.inst.pastePlaceholder)}" aria-label="${esc(t.inst.pasteTitle)}">${esc(state.paste)}</textarea><div><button class="chip" data-in-act="paste">${esc(t.inst.apply)}</button> <button class="chip" data-in-act="copy-table">${esc(t.inst.copyTable)}</button> <span class="isub">${esc(state.pasteResult)}</span></div></div></details>`;
    return `${search}${bulk}${sections.join("")}${paste}`;
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
    const tab = e.target.closest("[data-in-tab]");
    if (tab) {
      state.tab = tab.dataset.inTab;
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
    if (act === "print") this._documentation("print");
    else if (act === "csv") this._documentation("csv");
    else if (act === "json") this._documentation("json");
    else if (act === "import") this.shadowRoot.getElementById("docFile").click();
    else if (act === "unpick") {
      state.selected.clear();
      this._renderInstallation();
    } else if (act === "bulk") this._instBulk();
    else if (act === "paste") this._instPaste();
    else if (act === "copy-table") this._instCopyTable();
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
    const cell = e.target.closest("[data-in-field]");
    if (!cell) return;
    cell.classList.remove("bad");
    clearTimeout(cell._saving);
    cell._saving = setTimeout(() => this._instSaveCell(cell), SAVE_DELAY);
  },

  _instDevice(entryId, key) {
    return gateways(this._in.doc).find((g) => g.entry_id === entryId)?.devices.find((d) => d.key === key);
  },

  async _instSaveCell(cell) {
    const { inGw: entryId, inKey: key, inField: field } = cell.dataset;
    const device = this._instDevice(entryId, key);
    if (!device || device[field] === cell.value) return;
    const reply = await this._instSend(entryId, [{ device: key, values: { [field]: cell.value } }]);
    if (reply?.saved) device[field] = cell.value;
    else cell.classList.add("bad"); // refused: a date that is none, or the device is gone
  },

  async _instSend(entryId, items) {
    try {
      return await this._hass.callWS({ type: "enocean_eltako/set_fields", entry_id: entryId, items });
    } catch (err) {
      this._notice(this._t.doc.noteFailed);
      return null;
    }
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
