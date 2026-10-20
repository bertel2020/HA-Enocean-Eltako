// EnOcean telegram monitor: sidebar panel of the enocean_eltako integration.
// Plain web component, no build step. Data: websocket enocean_eltako/telegrams/subscribe.

const MAX_ROWS = 1000;
const HISTORY = 200;
const RORG = { F6: "RPS", D5: "1BS", A5: "4BS", D2: "VLD", D4: "UTE", D1: "MSC" };

const TEXT = {
  en: {
    title: "EnOcean monitor",
    all: "All gateways",
    search: "Filter: ID, device, data",
    dirAll: "Received and sent",
    rx: "Received",
    tx: "Sent",
    hideDup: "Hide duplicates",
    unknown: "Unknown senders only",
    pause: "Pause",
    resume: "Resume",
    clear: "Clear",
    export: "Export",
    count: (shown, total) => `${shown} of ${total} telegrams`,
    paused: (n) => `paused, ${n} new`,
    time: "Time",
    gateway: "Gateway",
    sender: "Sender",
    type: "Type",
    data: "Data",
    status: "Status",
    values: "Values",
    duplicate: "duplicate",
    teachIn: "teach-in",
    unknownDevice: "unknown",
    empty: "No telegrams yet. Press a button or switch an actuator.",
    filterHint: "Click an ID to filter by it",
  },
  de: {
    title: "EnOcean-Monitor",
    all: "Alle Gateways",
    search: "Filter: ID, Gerät, Daten",
    dirAll: "Empfangen und gesendet",
    rx: "Empfangen",
    tx: "Gesendet",
    hideDup: "Duplikate ausblenden",
    unknown: "Nur unbekannte Sender",
    pause: "Pause",
    resume: "Fortsetzen",
    clear: "Leeren",
    export: "Exportieren",
    count: (shown, total) => `${shown} von ${total} Telegrammen`,
    paused: (n) => `pausiert, ${n} neu`,
    time: "Zeit",
    gateway: "Gateway",
    sender: "Sender",
    type: "Typ",
    data: "Daten",
    status: "Status",
    values: "Werte",
    duplicate: "Duplikat",
    teachIn: "Lerntelegramm",
    unknownDevice: "unbekannt",
    empty: "Noch keine Telegramme. Eine Taste drücken oder einen Aktor schalten.",
    filterHint: "Auf eine ID klicken, um danach zu filtern",
  },
};

const STYLE = `
  :host { display: block; height: 100%; background: var(--primary-background-color);
    color: var(--primary-text-color); font-family: var(--paper-font-body1_-_font-family, inherit); }
  .header { display: flex; align-items: center; gap: 4px; height: var(--header-height, 56px);
    padding: 0 12px; background: var(--app-header-background-color, var(--primary-color));
    color: var(--app-header-text-color, var(--text-primary-color)); font-size: 20px; }
  .header .title { margin-left: 4px; }
  .toolbar { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; padding: 12px 16px; }
  select, input[type=search], button { font: inherit; font-size: 14px; color: var(--primary-text-color);
    background: var(--card-background-color); border: 1px solid var(--divider-color);
    border-radius: 6px; padding: 6px 10px; min-height: 34px; box-sizing: border-box; }
  input[type=search] { flex: 1 1 200px; min-width: 0; }
  button { cursor: pointer; }
  button.active { background: var(--primary-color); color: var(--text-primary-color); border-color: transparent; }
  label { display: inline-flex; align-items: center; gap: 4px; font-size: 14px; white-space: nowrap; }
  .count { padding: 0 16px 8px; font-size: 13px; color: var(--secondary-text-color); }
  .wrap { overflow-x: auto; padding: 0 16px 16px; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; background: var(--card-background-color);
    border-radius: 8px; overflow: hidden; }
  th, td { text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--divider-color);
    vertical-align: top; white-space: nowrap; }
  th { position: sticky; top: 0; background: var(--card-background-color); color: var(--secondary-text-color);
    font-weight: 500; }
  td.mono, .id { font-family: var(--code-font-family, monospace); }
  td.values { white-space: normal; min-width: 180px; }
  tr.tx td { background: color-mix(in srgb, var(--primary-color) 7%, transparent); }
  tr.dup td { opacity: 0.55; }
  .id { cursor: pointer; text-decoration: underline dotted; }
  .device { color: var(--secondary-text-color); font-size: 12px; }
  .badge { display: inline-block; margin-left: 4px; padding: 0 6px; border-radius: 8px; font-size: 11px;
    background: var(--secondary-background-color); color: var(--secondary-text-color); }
  .badge.teach { background: var(--warning-color, #f4b400); color: #000; }
  .dir { font-weight: 600; }
  .empty { padding: 32px 16px; text-align: center; color: var(--secondary-text-color); }
`;

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]
  );
}

class EnOceanEltakoMonitor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._rows = [];
    this._pending = [];
    this._paused = false;
    this._filter = { gateway: "", text: "", dir: "", hideDup: true, unknown: false };
    this._gateways = [];
    this._unsub = null;
    this._frame = null;
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (first) {
      this._t = TEXT[(hass.language || "en").startsWith("de") ? "de" : "en"];
      this._build();
    }
    if (this._menu) this._menu.hass = hass;
    if (this.isConnected && !this._unsub) this._subscribe();
  }

  set narrow(narrow) {
    this._narrow = narrow;
    if (this._menu) this._menu.narrow = narrow;
  }

  connectedCallback() {
    if (this._hass && !this._unsub) this._subscribe();
  }

  disconnectedCallback() {
    if (this._unsub) {
      this._unsub.then((unsub) => unsub()).catch(() => {});
      this._unsub = null;
    }
  }

  _build() {
    const t = this._t;
    this.shadowRoot.innerHTML = `
      <style>${STYLE}</style>
      <div class="header"><ha-menu-button></ha-menu-button><span class="title">${esc(t.title)}</span></div>
      <div class="toolbar">
        <select id="gateway"><option value="">${esc(t.all)}</option></select>
        <input id="text" type="search" placeholder="${esc(t.search)}" title="${esc(t.filterHint)}">
        <select id="dir">
          <option value="">${esc(t.dirAll)}</option>
          <option value="rx">${esc(t.rx)}</option>
          <option value="tx">${esc(t.tx)}</option>
        </select>
        <label><input id="hideDup" type="checkbox" checked>${esc(t.hideDup)}</label>
        <label><input id="unknown" type="checkbox">${esc(t.unknown)}</label>
        <button id="pause">${esc(t.pause)}</button>
        <button id="clear">${esc(t.clear)}</button>
        <button id="export">${esc(t.export)}</button>
      </div>
      <div class="count" id="count"></div>
      <div class="wrap" id="wrap"></div>`;
    const $ = (id) => this.shadowRoot.getElementById(id);
    this._menu = this.shadowRoot.querySelector("ha-menu-button");
    this._menu.hass = this._hass;
    this._menu.narrow = this._narrow;
    $("gateway").addEventListener("change", (e) => this._set("gateway", e.target.value));
    $("text").addEventListener("input", (e) => this._set("text", e.target.value.trim()));
    $("dir").addEventListener("change", (e) => this._set("dir", e.target.value));
    $("hideDup").addEventListener("change", (e) => this._set("hideDup", e.target.checked));
    $("unknown").addEventListener("change", (e) => this._set("unknown", e.target.checked));
    $("pause").addEventListener("click", () => this._togglePause());
    $("clear").addEventListener("click", () => {
      this._rows = [];
      this._pending = [];
      this._render();
    });
    $("export").addEventListener("click", () => this._export());
    $("wrap").addEventListener("click", (e) => {
      const id = e.target.closest(".id");
      if (!id) return;
      $("text").value = id.dataset.id;
      this._set("text", id.dataset.id);
    });
    this._render();
  }

  async _subscribe() {
    const conn = this._hass.connection;
    this._unsub = conn.subscribeMessage((row) => this._add(row), {
      type: "enocean_eltako/telegrams/subscribe",
      history: HISTORY,
    });
    try {
      this._gateways = await this._hass.callWS({ type: "enocean_eltako/gateways" });
    } catch (err) {
      this._gateways = [];
    }
    const select = this.shadowRoot.getElementById("gateway");
    select.length = 1; // keep "all gateways" after a reconnect
    for (const gw of this._gateways) {
      const option = document.createElement("option");
      option.value = gw.entry_id;
      option.textContent = gw.title;
      select.appendChild(option);
    }
  }

  _add(row) {
    if (this._paused) {
      this._pending.push(row);
      this._renderCount();
      return;
    }
    this._rows.unshift(row);
    if (this._rows.length > MAX_ROWS) this._rows.length = MAX_ROWS;
    this._schedule();
  }

  _togglePause() {
    this._paused = !this._paused;
    if (!this._paused) {
      this._rows = [...this._pending.reverse(), ...this._rows].slice(0, MAX_ROWS);
      this._pending = [];
    }
    const button = this.shadowRoot.getElementById("pause");
    button.textContent = this._paused ? this._t.resume : this._t.pause;
    button.classList.toggle("active", this._paused);
    this._render();
  }

  _set(key, value) {
    this._filter[key] = value;
    this._render();
  }

  _schedule() {
    if (this._frame) return;
    this._frame = requestAnimationFrame(() => {
      this._frame = null;
      this._render();
    });
  }

  _visible() {
    const f = this._filter;
    const text = f.text.toLowerCase();
    return this._rows.filter(
      (r) =>
        (!f.gateway || r.gateway === f.gateway) &&
        (!f.dir || r.dir === f.dir) &&
        !(f.hideDup && r.duplicate) &&
        !(f.unknown && (r.device || r.dir === "tx")) &&
        (!text ||
          [r.sender, r.device, r.data, r.teach_in, r.profile].some(
            (v) => v && String(v).toLowerCase().includes(text)
          ))
    );
  }

  _renderCount() {
    const t = this._t;
    let text = t.count(this._visible().length, this._rows.length);
    if (this._paused) text += ` · ${t.paused(this._pending.length)}`;
    this.shadowRoot.getElementById("count").textContent = text;
  }

  _render() {
    const t = this._t;
    const wrap = this.shadowRoot.getElementById("wrap");
    if (!wrap) return;
    const rows = this._visible();
    this._renderCount();
    if (!rows.length) {
      wrap.innerHTML = `<div class="empty">${esc(t.empty)}</div>`;
      return;
    }
    const showGateway = this._gateways.length !== 1;
    const body = rows
      .map((r) => {
        const time = new Date(r.time);
        const clock = `${time.toLocaleTimeString(this._hass.language, { hour12: false })}.${String(
          time.getMilliseconds()
        ).padStart(3, "0")}`;
        const name = r.device
          ? esc(r.device) + (r.profile ? ` · ${esc(r.profile)}` : "")
          : r.dir === "rx"
            ? esc(t.unknownDevice)
            : "";
        const badges =
          (r.teach_in ? `<span class="badge teach">${esc(t.teachIn)} ${esc(r.teach_in)}</span>` : "") +
          (r.duplicate ? `<span class="badge">${esc(t.duplicate)}</span>` : "");
        const values = r.values
          ? Object.entries(r.values)
              .map(([k, v]) => `${esc(k)}: <b>${esc(v)}</b>`)
              .join(", ")
          : "";
        return `<tr class="${r.dir}${r.duplicate ? " dup" : ""}">
          <td class="mono">${clock}</td>
          ${showGateway ? `<td>${esc(r.gateway_name)}</td>` : ""}
          <td class="dir" title="${esc(r.dir === "rx" ? t.rx : t.tx)}">${r.dir === "rx" ? "↓" : "↑"}</td>
          <td><span class="id" data-id="${esc(r.sender)}">${esc(r.sender)}</span><div class="device">${name}</div></td>
          <td>${esc(RORG[r.rorg] || r.rorg)}${badges}</td>
          <td class="mono">${esc(r.data)}</td>
          <td class="mono">${esc(r.status)}</td>
          <td class="mono">${r.dbm ?? ""}</td>
          <td class="values">${values}</td>
        </tr>`;
      })
      .join("");
    wrap.innerHTML = `<table>
      <thead><tr>
        <th>${esc(t.time)}</th>${showGateway ? `<th>${esc(t.gateway)}</th>` : ""}<th></th>
        <th>${esc(t.sender)}</th><th>${esc(t.type)}</th><th>${esc(t.data)}</th>
        <th>${esc(t.status)}</th><th>dBm</th><th>${esc(t.values)}</th>
      </tr></thead><tbody>${body}</tbody></table>`;
  }

  _export() {
    const lines = this._visible()
      .slice()
      .reverse()
      .map((r) => JSON.stringify(r))
      .join("\n");
    const blob = new Blob([lines + "\n"], { type: "application/x-ndjson" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `enocean-telegrams-${new Date().toISOString().replace(/[:.]/g, "-")}.jsonl`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(link.href), 1000);
  }
}

customElements.define("enocean-eltako-monitor", EnOceanEltakoMonitor);
