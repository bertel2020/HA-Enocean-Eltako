// The Installation view of the panel: what is known of the installation, and what the user writes
// down about it. Three tabs: the devices by area or place, a table of the devices with typed
// fields that are edited in place (also for a selection, or pasted from a spreadsheet), and the
// event log. Everything comes from the documentation command; edits go back with set_fields. Its
// methods are added to the panel class (this = the panel).

const VERSION = new URL(import.meta.url).search;
const { ICON, esc, svg } = await import(`./shared.js${VERSION}`);

// the typed fields of a device, in table order; installed is a date
export const INSTALLATION_FIELDS = ["location", "circuit", "bus_address", "feedback_id", "bus_power", "fuse", "installed", "revision", "power", "note"];
const TABS = ["areas", "devices", "links", "log"];
const SAVE_DELAY = 600; // ms after the last key

// the view's state when the panel starts
export const installationState = () => ({
  doc: null, error: false, tab: "areas", group: "area", linkGroup: "actuator", selected: new Set(), paste: "", pasteResult: "", q: "",
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
  .installation .itable input.cell[data-in-field="location"], .installation .itable input.cell[data-in-field="note"] { min-width: 200px; }
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
      <button class="chip" data-in-act="csv-tables">${svg(ICON.download)}${esc(t.inst.tablesCsv)}</button>
      <button class="chip" data-in-act="csv-links">${svg(ICON.download)}${esc(t.inst.links.csvShort)}</button>
      <button class="chip" data-in-act="json">${svg(ICON.download)}JSON</button>
      <button class="chip" data-in-act="import">${svg(ICON.upload)}${esc(t.inst.import)}</button>`;
    const body = { areas: this._instAreas(), devices: this._instDevices(), links: this._instLinks(), log: this._instLog() }[state.tab];
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

  _instLinks() {
    // who is taught into which actuator; every link says where it comes from and what proves it
    const t = this._t;
    const state = this._in;
    const L = t.inst.links;
    const when = (iso) => new Date(iso).toLocaleString(this._hass.language);
    const toggle = `<div class="isub">${esc(t.inst.groupBy)} <button class="chip" data-in-link-group="actuator" aria-pressed="${state.linkGroup === "actuator"}">${esc(L.byActuator)}</button> <button class="chip" data-in-link-group="sender" aria-pressed="${state.linkGroup === "sender"}">${esc(L.bySender)}</button></div>
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
      return `<section><h3>${esc(gw.title)}</h3>${body || `<div class="none">${esc(L.none)}</div>`}${add}</section>`;
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
    const tab = e.target.closest("[data-in-tab]");
    if (tab) {
      state.tab = tab.dataset.inTab;
      this._renderInstallation();
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
