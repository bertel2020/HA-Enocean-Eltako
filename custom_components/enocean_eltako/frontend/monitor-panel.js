// "EnOcean" sidebar panel of the enocean_eltako integration: gateway overview and live
// telegram monitor. Plain web component, no build step. Own colours (the look of the Device
// Proxy app); light and dark mode follow Home Assistant, and a theme or primary colour of the
// user's own replaces the accent colour. Data: websocket enocean_eltako/telegrams/subscribe,
// enocean_eltako/gateways and enocean_eltako/discover.

// the parts load with this file's version (?v=<hash> from panel.py), so an update never mixes
// old and new files from the browser cache
const VERSION = new URL(import.meta.url).search;
const [{ ICON, MAX_ROWS, esc, svg }, { TEXT }, { TAKEOVER_STYLE, takeover }] = await Promise.all([
  import(`./shared.js${VERSION}`),
  import(`./texts.js${VERSION}`),
  import(`./takeover.js${VERSION}`),
]);

const PAGE_SIZES = [25, 50, 100, 200];
const STORAGE_KEY = "enocean_eltako_monitor"; // page size, sort order and filters, per browser
const HISTORY = 200;
// the keys of a capture line (service enocean_eltako.capture): exports can be used as test fixtures
const CAPTURE_KEYS = ["time", "gateway", "dir", "rorg", "data", "sender", "status", "destination", "dbm", "duplicate"];
const ANSWER_WINDOW = 3000; // ms in which a device answers a command
const WEAK_DBM = -85; // below this a sender is at the edge of the range (repeater or antenna)
const TREND_POINTS = 30; // telegrams in a sender's signal curve
const STATUS_INTERVAL = 5000; // ms between gateway status updates
const RORG = { F6: "RPS", D5: "1BS", A5: "4BS", D2: "VLD", D4: "UTE", D1: "MSC" };
// what the send form accepts per telegram type (as websocket.py SEND_LENGTHS), with an example
const SEND_TYPES = { F6: { bytes: [1, 1], example: "70", status: "30" }, D5: { bytes: [1, 1], example: "09", status: "00" },
  A5: { bytes: [4, 4], example: "02640009", status: "00" }, D2: { bytes: [1, 14], example: "0100", status: "00" } };

// the integration's icon (docs/assets/enocean-eltako-icon.svg), inline: no image to load,
// own dark tile, so it suits every header colour and theme
const LOGO = `<svg class="logo" viewBox="16 16 480 480" aria-hidden="true">
  <rect x="16" y="16" width="480" height="480" rx="112" fill="#142E42"/>
  <g fill="none" stroke="#66D8D0" stroke-width="34" stroke-linecap="round" stroke-linejoin="round">
    <path d="M137 144V368"/><path d="M137 145H284"/><path d="M137 256H265"/><path d="M137 367H284"/>
  </g>
  <circle cx="314" cy="256" r="17" fill="#F7B36B"/>
  <g fill="none" stroke="#F5FBFC" stroke-linecap="round">
    <path d="M345 211C365 220 378 235 378 256S365 292 345 301" stroke-width="25"/>
    <path d="M365 157C403 181 424 215 424 256S403 331 365 355" stroke-width="22"/>
  </g>
</svg>`;

const STYLE = `
  /* look of the Device Proxy app: own tokens (light-dark), the colour scheme follows Home Assistant's theme */
  :host {
    display: block; min-height: 100%; background: var(--bg); color: var(--text);
    font-family: Roboto, "Noto Sans", system-ui, -apple-system, sans-serif; font-size: 14px;
    --bg: light-dark(#f3f4f6, #111418); --surface: light-dark(#ffffff, #1b1f24); --soft: light-dark(#f5f7f9, #22272e);
    --line: light-dark(#e1e5ea, #2d333b); --line-2: light-dark(#eef0f3, #262c33); --input-line: light-dark(#c3cbd5, #3a424c);
    --text: light-dark(#1b1f24, #e6e9ed); --muted: light-dark(#5b6270, #9aa4b1);
    --accent: light-dark(#0a6aa8, #5bb2ea); --accent-hover: light-dark(#07507f, #8ccaf2); --accent-soft: light-dark(#eaf3fa, #16324a);
    --on-accent: light-dark(#ffffff, #0b1a26); --focus: #7db8e0;
    --ok: light-dark(#1e6b34, #7fd49a); --warn: light-dark(#8a4b00, #f2c27a); --bad: light-dark(#a1261b, #f2a29a);
    --tag-bg: light-dark(#eef1f4, #2a3038); --tag-text: light-dark(#3a414c, #c5ccd5);
    --radius: 16px;
  }
  /* older browsers (iOS before 17.5, Chrome before 123) know no light-dark(): the same tokens,
     the scheme from the dark attribute */
  @supports not (color: light-dark(#000, #fff)) {
    :host {
      --bg: #f3f4f6; --surface: #ffffff; --soft: #f5f7f9; --line: #e1e5ea; --line-2: #eef0f3; --input-line: #c3cbd5;
      --text: #1b1f24; --muted: #5b6270; --accent: #0a6aa8; --accent-hover: #07507f; --accent-soft: #eaf3fa; --on-accent: #ffffff;
      --ok: #1e6b34; --warn: #8a4b00; --bad: #a1261b; --tag-bg: #eef1f4; --tag-text: #3a414c;
    }
    :host([dark]) {
      --bg: #111418; --surface: #1b1f24; --soft: #22272e; --line: #2d333b; --line-2: #262c33; --input-line: #3a424c;
      --text: #e6e9ed; --muted: #9aa4b1; --accent: #5bb2ea; --accent-hover: #8ccaf2; --accent-soft: #16324a; --on-accent: #0b1a26;
      --ok: #7fd49a; --warn: #f2c27a; --bad: #f2a29a; --tag-bg: #2a3038; --tag-text: #c5ccd5;
    }
  }
  /* a theme or primary colour of the user's own: its colour is the accent */
  :host([themed]) {
    --theme-accent: var(--primary-color, #0a6aa8);
    --accent: var(--theme-accent); --accent-hover: color-mix(in srgb, var(--theme-accent) 75%, var(--text));
    --accent-soft: color-mix(in srgb, var(--theme-accent) 14%, var(--surface)); --on-accent: var(--text-primary-color, #ffffff);
  }
  * { box-sizing: border-box; }
  svg { width: 20px; height: 20px; fill: currentColor; flex: none; }
  button { font: inherit; color: inherit; background: none; border: 0; cursor: pointer; }
  button:focus-visible, input:focus-visible { outline: 3px solid var(--focus); outline-offset: 2px; }

  .header { display: flex; flex-wrap: wrap; align-items: flex-end; justify-content: space-between;
    gap: 0 24px; padding: 0 24px; background: var(--surface); border-bottom: 1px solid var(--line); }
  .brand { display: flex; align-items: center; gap: 12px; padding: 10px 0; min-height: 60px; }
  .brand ha-menu-button { margin-left: -12px; color: var(--text); }
  .brand b { display: block; font-size: 18px; font-weight: 500; line-height: 1.2; }
  .brand small { display: block; font-size: 12px; color: var(--muted); }
  .header .logo { width: 36px; height: 36px; flex: none; }
  /* the view tabs: their own look, not the segmented filter buttons */
  #view { display: flex; flex-wrap: wrap; }
  #view button { display: inline-flex; align-items: center; min-height: 48px; padding: 0 16px; font-size: 14px; font-weight: 500; white-space: nowrap;
    color: var(--muted); border-bottom: 3px solid transparent; }
  #view button:hover { color: var(--text); }
  #view button[aria-selected="true"] { color: var(--accent); border-bottom-color: var(--accent); }
  #view button[hidden] { display: none; }
  main { max-width: 1200px; margin: 0 auto; padding: 24px 24px 48px; display: grid;
    grid-template-columns: minmax(0, 1fr); gap: 16px; }
  main > section { min-width: 0; }
  h2 { margin: 0; font-size: 16px; font-weight: 500; }
  .mono { font-family: var(--code-font-family, ui-monospace, monospace); }

  /* gateway summary: status first, technical information under Details */
  .cards { display: flex; flex-direction: column; gap: 12px; }
  .card { display: flex; flex-wrap: wrap; align-items: center; gap: 16px; padding: 20px;
    background: var(--surface); border-radius: var(--radius); border: 1px solid var(--line);
    box-shadow: none; transition: border-color .15s, box-shadow .15s; }
  .card.selected { border: 2px solid var(--accent); padding: 19px; background: var(--accent-soft); }
  .card .name { font-size: 16px; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .card .sub { font-size: 12px; color: var(--muted); overflow-wrap: anywhere; }
  .gateway-icon { display: grid; place-items: center; width: 40px; height: 40px; border-radius: 12px;
    color: var(--accent); background: var(--accent-soft); }
  .gateway-title { flex: 1 1 170px; min-width: 0; }
  .gateway-status { display: flex; flex-wrap: wrap; gap: 4px 10px; align-items: center; margin-top: 3px; }
  .pill { display: inline-flex; align-items: center; gap: 6px; font-size: 12px; white-space: nowrap; }
  .pill i { width: 8px; height: 8px; border-radius: 50%; background: currentColor; }
  .pill.ok i { background: var(--ok); }
  .pill.bad i { background: var(--bad); }
  .pill.idle i { background: var(--warn); }
  .rate, .gateway-count { display: flex; flex-direction: column; align-items: flex-start; gap: 3px;
    padding-left: 18px; border-left: 1px solid var(--line); }
  .rate b { font-size: 16px; font-weight: 500; line-height: 1; }
  .rate span { font-size: 13px; color: var(--muted); }
  .rate .last { font-size: 12px; }
  .gateway-count { font-size: 12px; color: var(--muted); }
  .gateway-count b { font-size: 14px; font-weight: 500; color: var(--text); }
  .gateway-actions { display: flex; flex-wrap: wrap; gap: 8px; }
  .gateway-details { flex-basis: 100%; border-top: 1px solid var(--line); padding-top: 12px; display: grid; gap: 12px; }
  .connection { font-size: 12px; color: var(--muted); overflow-wrap: anywhere; }
  .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 4px 14px;
    font-size: 12px; color: var(--muted); }
  .stats > span { display: flex; justify-content: space-between; gap: 8px; }
  .stats b { color: var(--text); font-weight: 500; }
  .stats b.warn { color: var(--bad); }
  .hint { color: var(--muted); font-size: 14px; padding: 4px; }
  .proxy { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 10px; font-size: 12px;
    color: var(--muted); padding-top: 8px; border-top: 1px solid var(--line); }
  .proxy .muted { color: var(--muted); }
  .airtime { display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 8px;
    font-size: 12px; color: var(--muted); }
  .airtime b { color: var(--text); font-weight: 500; }
  .meter { height: 6px; border-radius: 3px; background: var(--soft); overflow: hidden; }
  .meter i { display: block; height: 100%; background: var(--accent); }
  .meter i.warn { background: var(--warn); }
  .meter i.bad { background: var(--bad); }

  /* telegram section */
  .panel { background: var(--surface); border-radius: var(--radius); border: 1px solid var(--line);
    box-shadow: none; overflow: clip; }
  .bar { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; padding: 12px 12px 12px 16px;
    border-bottom: 1px solid var(--line); }
  .live { display: inline-flex; align-items: center; gap: 6px; font-size: 12px; font-weight: 500; min-height: 24px; padding: 0 10px;
    border-radius: 12px; background: color-mix(in srgb, var(--ok) 16%, transparent); color: var(--ok); }
  .live i { width: 8px; height: 8px; border-radius: 50%; background: currentColor; }
  .live.paused, .live.connecting { color: var(--warn); background: color-mix(in srgb, var(--warn) 16%, transparent); }
  .live.offline { color: var(--bad); background: color-mix(in srgb, var(--bad) 16%, transparent); }
  .spacer { flex: 1; }
  .icon-btn { width: 40px; height: 40px; border-radius: 50%; display: inline-grid; place-items: center; color: var(--muted); }
  .icon-btn:hover { background: var(--accent-soft); color: var(--accent-hover); }
  .icon-btn[hidden] { display: none; }
  .icon-btn.on { color: var(--accent); }
  /* phones: export and clear sit in the "more" menu, so the bar stays on one line */
  .more { position: relative; }
  .menu { position: absolute; right: 0; top: calc(100% + 4px); z-index: 3; display: grid; min-width: 220px; padding: 6px 0;
    background: var(--surface); border: 1px solid var(--line); border-radius: 12px; box-shadow: 0 6px 24px rgb(0 0 0 / 18%); }
  .menu[hidden] { display: none; }
  .menu button { display: flex; align-items: center; gap: 12px; min-height: 44px; padding: 0 16px; text-align: left; white-space: nowrap; }
  .menu button:hover, .menu button:focus-visible { background: var(--accent-soft); }
  .menu svg { color: var(--muted); }

  .filters { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; padding: 12px 16px; border-bottom: 1px solid var(--line); }
  .search { flex: 1 1 260px; min-width: 0; display: flex; align-items: center; gap: 8px; height: 42px; padding: 0 6px 0 12px;
    border-radius: 10px; border: 1px solid var(--input-line); background: var(--surface); color: var(--muted); }
  .search input { flex: 1; min-width: 0; height: 100%; border: 0; background: none; outline: none; font: inherit;
    font-size: 14px; color: var(--text); }
  .search input::placeholder { color: var(--muted); }
  .search input::-webkit-search-cancel-button, .search input::-webkit-search-decoration { -webkit-appearance: none; appearance: none; display: none; }
  .search .icon-btn { width: 30px; height: 30px; }
  .search .icon-btn svg { width: 18px; height: 18px; }
  .segmented { display: inline-flex; border: 1px solid var(--input-line); border-radius: 10px; overflow: hidden; }
  .segmented button { min-height: 38px; padding: 0 14px; font-size: 13px; font-weight: 500; color: var(--text); background: var(--surface); white-space: nowrap; }
  .segmented button + button { border-left: 1px solid var(--input-line); }
  .segmented button[aria-pressed="true"] { color: var(--on-accent); background: var(--accent); }
  .chip { min-height: 36px; padding: 0 16px; border-radius: 20px; border: 1px solid var(--input-line); font-size: 13px; font-weight: 500;
    display: inline-flex; align-items: center; justify-content: center; gap: 6px; color: var(--accent); background: var(--surface); white-space: nowrap; }
  .chip:hover:not(:disabled) { background: var(--accent-soft); color: var(--accent-hover); }
  .chip svg { width: 16px; height: 16px; }
  .chip[aria-pressed="true"] { border-color: var(--accent); color: var(--accent-hover); background: var(--accent-soft); }
  .chip.add { color: var(--accent); }
  .chip.primary { background: var(--accent); color: var(--on-accent); border-color: var(--accent); }
  .chip.primary:hover:not(:disabled) { background: var(--accent-hover); color: var(--on-accent); }
  .chip:disabled { opacity: .5; cursor: default; }
  .meta { display: flex; justify-content: space-between; gap: 8px; padding: 8px 16px; font-size: 12px; color: var(--muted); }
  .notice { margin: 8px 16px 0; padding: 12px 14px; border-radius: 12px; font-size: 13px;
    background: color-mix(in srgb, var(--warn) 14%, transparent); display: flex; gap: 8px; align-items: center; }
  .notice[hidden] { display: none; }
  .notice span { flex: 1; }

  /* telegram table: sortable columns, one page at a time */
  .select { height: 38px; border-radius: 10px; border: 1px solid var(--input-line); background: var(--surface);
    color: var(--text); font: inherit; font-size: 13px; padding: 0 8px; max-width: 220px; }
  .select[hidden] { display: none; }
  .telegrams { width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 13px; }
  .telegrams col.c-time { width: 128px; } /* room for "10:04:40 PM" */
  .telegrams col.c-dir { width: 48px; }
  .telegrams col.c-who { width: 30%; }
  .telegrams col.c-type { width: 76px; }
  .telegrams col.c-signal { width: 92px; }
  .telegrams col.c-gw { width: 140px; }
  .telegrams col.c-end { width: 48px; }
  .telegrams th { position: sticky; top: 0; z-index: 1; padding: 0; text-align: left;
    background: var(--soft); border-bottom: 1px solid var(--line); }
  .telegrams th > button, .telegrams th > span { display: flex; align-items: center; gap: 2px; width: 100%; height: 38px;
    padding: 0 8px; font-size: 12px; font-weight: 500; color: var(--muted); text-align: left; white-space: nowrap; }
  .telegrams th:first-child > * { padding-left: 16px; }
  .telegrams th > button:hover, .telegrams th[aria-sort] > button { color: var(--text); }
  .telegrams th .sort { width: 16px; height: 16px; opacity: 0; transition: transform .15s, opacity .15s; }
  .telegrams th > button:hover .sort { opacity: .45; }
  .telegrams th[aria-sort] .sort { opacity: 1; }
  .telegrams th[aria-sort="ascending"] .sort { transform: rotate(180deg); }
  .telegrams td { padding: 10px 8px; border-top: 1px solid var(--line); vertical-align: middle; min-width: 0; }
  .telegrams td:first-child { padding-left: 16px; }
  .telegrams tbody tr:first-child td { border-top: 0; }
  tr.row { cursor: pointer; }
  tr.row:hover > td { background: color-mix(in srgb, var(--soft) 60%, transparent); }
  tr.row.open > td, tr.detail-row > td { background: color-mix(in srgb, var(--accent) 6%, transparent); }
  tr.row.fresh > td { animation: fresh 1.2s ease-out; }
  @keyframes fresh { from { background: color-mix(in srgb, var(--accent) 16%, transparent); } }
  tr.row.dup { opacity: .6; }
  tr.detail-row > td { border-top: 0; padding: 0 12px 12px 16px; cursor: default; }
  tr.empty-row > td { padding: 0; }
  .time { font-family: var(--code-font-family, ui-monospace, monospace); white-space: nowrap; }
  .time small { color: var(--muted); }
  .dir { width: 28px; height: 28px; border-radius: 50%; display: grid; place-items: center; color: var(--muted); background: var(--soft); }
  .dir svg { width: 16px; height: 16px; }
  .dir.tx { color: var(--accent); background: var(--accent-soft); }
  .who .line1 { display: flex; align-items: center; gap: 8px; min-width: 0; }
  .who .name { font-size: 14px; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .who .name.unknown { font-weight: 400; color: var(--muted); }
  .who .line2 { font-size: 12px; color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin-top: 2px; }
  .tag { flex: none; font-size: 12px; font-weight: 500; padding: 2px 10px; border-radius: 12px; background: var(--tag-bg); color: var(--tag-text); white-space: nowrap; }
  .tag.teach, .tag.warn { background: color-mix(in srgb, var(--warn) 22%, transparent); color: var(--text); }
  .values { display: flex; flex-wrap: wrap; align-items: center; gap: 4px 12px; min-width: 0; }
  .value { white-space: nowrap; }
  .value span { color: var(--muted); }
  .value b { font-weight: 500; }
  .raw { font-size: 12px; color: var(--muted); overflow-wrap: anywhere; }
  .gw { color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .signal { display: flex; align-items: center; gap: 6px; color: var(--muted); font-size: 12px; white-space: nowrap; }
  .end { text-align: right; }
  .end .chev { transition: transform .15s; }
  .expand { width: 32px; height: 32px; border-radius: 50%; display: inline-grid; place-items: center; color: var(--muted); }
  .expand:hover { background: var(--soft); }
  .expand[aria-expanded="true"] .chev { transform: rotate(180deg); }
  .bars { width: 18px; height: 14px; }
  .bars rect { fill: var(--line); }
  .bars rect.on { fill: var(--muted); }
  .details { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 14px 20px;
    margin: 0; padding: 14px 16px; border-radius: 12px; background: var(--surface); border: 1px solid var(--line); }
  .details div { min-width: 0; }
  .details dt { font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: .03em; }
  .details dd { margin: 2px 0 0; font-size: 13px; overflow-wrap: anywhere; }
  .details .wide { grid-column: 1 / -1; }
  .chg { background: color-mix(in srgb, var(--warn) 35%, transparent); border-radius: 3px; padding: 0 2px; }
  .details .actions { grid-column: 1 / -1; display: flex; flex-wrap: wrap; gap: 8px; }
  .m-only { display: none; }
  .sendform { padding: 12px 16px; border-bottom: 1px solid var(--line); background: color-mix(in srgb, var(--warn) 8%, transparent); }
  .sendform[hidden] { display: none; }
  .sendform h3 { margin: 0 0 4px; font-size: 14px; font-weight: 500; }
  .sendform p { margin: 0 0 10px; font-size: 12px; color: var(--muted); }
  .sendform .fields { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 10px 12px; }
  .sendform label { display: grid; gap: 4px; font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: .03em; min-width: 0; }
  .sendform .text { height: 38px; border-radius: 10px; border: 1px solid var(--input-line); background: var(--surface); color: var(--text);
    padding: 0 10px; font: 13px ui-monospace, monospace; text-transform: none; min-width: 0; }
  .sendform .buttons { display: flex; justify-content: flex-end; gap: 8px; margin-top: 12px; }
  .panel[data-view="devices"] .tg-only, .panel[data-view="senders"] .tg-only, .panel[data-view="senders"] .list-only,
  .panel[data-view="takeover"] .tg-only, .panel[data-view="takeover"] .list-only { display: none !important; }
  .panel:not([data-view="devices"]) .devices, .panel:not([data-view="senders"]) .senders,
  .panel:not([data-view="takeover"]) .takeover { display: none; }
  .senders .pool { display: grid; grid-template-columns: minmax(120px, 1fr) minmax(0, 2fr); gap: 12px 16px; align-items: center; padding: 14px 16px; }
  .senders .meta-label { font-size: 13px; color: var(--muted); }
  .senders .pool .big { font-size: 24px; font-weight: 500; }
  .senders .pool .big small { font-size: 13px; font-weight: 400; color: var(--muted); }
  .senders .pool .range { font-size: 12px; color: var(--muted); margin-top: 6px; }
  .senders .meter { display: block; height: 6px; border-radius: 3px; background: var(--soft); overflow: hidden; }
  .senders .meter i { display: block; height: 100%; background: var(--accent); }
  .senders .sid-group { padding: 4px 0 8px; border-top: 1px solid var(--line); }
  .senders .sid-group.blocked { background: color-mix(in srgb, var(--warn) 10%, transparent); }
  .senders .sid-head { display: flex; align-items: baseline; gap: 8px; padding: 8px 16px 2px; min-width: 0; }
  .senders .sid-name { font-size: 14px; font-weight: 500; overflow-wrap: anywhere; }
  .senders .sid-head .sub { font-size: 12px; color: var(--muted); white-space: nowrap; }
  .senders .sid-row { display: grid; grid-template-columns: 120px 110px minmax(0, 1fr) 96px auto; gap: 2px 12px; align-items: center;
    min-height: 34px; padding: 2px 16px 2px 28px; font-size: 13px; }
  .senders .sid-profile { color: var(--muted); overflow-wrap: anywhere; }
  .senders .sid-dec { color: var(--muted); }
  .senders .map { display: grid; grid-template-columns: repeat(16, minmax(0, 1fr)); gap: 3px; padding: 4px 16px 14px; }
  .senders .map button { all: unset; box-sizing: border-box; aspect-ratio: 1; border-radius: 3px; border: 1px solid var(--line); cursor: default; }
  .senders .map button[data-goto] { cursor: pointer; }
  .senders .map button:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
  .senders .map .t-assigned { background: var(--accent); border-color: var(--accent); }
  .senders .map .t-blocked { background: var(--warn); border-color: var(--warn); }
  .senders .map .t-unavailable { background: repeating-linear-gradient(45deg, var(--line) 0 2px, transparent 2px 4px); }
  .senders .pool .next { margin-top: 6px; font-size: 12px; color: var(--muted); }
  .senders .sid-head { cursor: pointer; }
  .senders .sid-head .fold { margin-left: auto; width: 16px; text-align: center; color: var(--muted); font-size: 12px; }
  .senders .sid-group.folded .sid-row, .senders .sid-group.folded .sid-hint, .senders .sid-group.folded .confirm { display: none; }
  .senders .sid-cols { display: grid; grid-template-columns: 120px 110px minmax(0, 1fr) 96px auto; gap: 2px 12px; padding: 8px 16px 6px 28px;
    border-top: 1px solid var(--line); font-size: 12px; font-weight: 500; color: var(--muted); }
  .senders .sid-cols span:last-child { width: 0; }
  .senders .act { text-align: right; }
  .senders .act .chip { height: 30px; }
  .senders .deleted { color: var(--muted); font-weight: 400; }
  .senders .tag.ok { background: color-mix(in srgb, var(--ok) 20%, transparent); }
  .senders .sid-hint { margin: 4px 16px 0 28px; font-size: 12px; color: var(--muted); }
  .senders .confirm { margin: 10px 16px 0 28px; padding: 12px 14px; border-radius: 8px; border: 1px solid var(--line); background: var(--surface); }
  .senders .confirm b { display: block; font-weight: 500; margin-bottom: 4px; }
  .senders .confirm p { margin: 0 0 12px; font-size: 13px; color: var(--muted); }
  .senders .confirm .buttons { display: flex; justify-content: flex-end; gap: 8px; }
  .senders .pick { padding: 12px 16px 0; }
  @media (max-width: 760px) {
    /* phones: ID and status on top, profile and button below */
    .senders .sid-row { grid-template-columns: minmax(0, 1fr) auto; grid-template-areas: "id state" "dec act" "profile profile"; padding: 6px 16px; }
    .senders .sid-cols { display: none; }
    .senders .sid-dec { grid-area: dec; }
    .senders .sid-id { grid-area: id; }
    .senders .sid-state { grid-area: state; }
    .senders .sid-profile { grid-area: profile; }
    .senders .act { grid-area: act; }
    .senders .sid-hint, .senders .confirm { margin-left: 16px; }
  }
  /* one grid for all senders (subgrid): names, values and numbers line up in columns */
  .panel:not([data-view="devices"]) .dev-only { display: none !important; }
  .devices { display: grid; grid-template-columns: minmax(170px, 2fr) 96px minmax(64px, 1fr) 76px minmax(0, 1.6fr) 140px auto; column-gap: 16px; }
  .devices > .empty { grid-column: 1 / -1; }
  .devices .dev-head, .devices .dev { grid-column: 1 / -1; display: grid; grid-template-columns: subgrid; gap: 4px 16px; align-items: center; padding: 12px 16px; }
  .devices .dev-head { padding-top: 8px; padding-bottom: 8px; font-size: 12px; font-weight: 500; color: var(--muted); }
  .devices .dev-head button { all: unset; box-sizing: border-box; display: inline-flex; align-items: center; gap: 4px; cursor: pointer; border-radius: 4px; }
  .devices .dev-head button:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  .devices .dev-head button:hover { color: var(--text); }
  .devices .dev-head button svg { width: 12px; height: 12px; opacity: 0; transition: transform .15s; }
  .devices .dev-head [aria-sort] { color: var(--text); }
  .devices .dev-head [aria-sort] svg { opacity: 1; }
  .devices .dev-head [aria-sort="ascending"] svg { transform: rotate(180deg); }
  .devices .dev { border-top: 1px solid var(--line); cursor: pointer; }
  .devices .dev .acts { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 6px; }
  .devices .dev .acts .chip { height: 30px; padding: 0 10px; }
  .devices .dev:hover { background: color-mix(in srgb, var(--soft) 60%, transparent); }
  .devices .dev .ident { min-width: 0; }
  .devices .dev .c-area, .devices .dev .c-ent { font-size: 13px; overflow-wrap: anywhere; }
  .devices .dev .c-ent { text-align: right; padding-right: 12px; font-variant-numeric: tabular-nums; }
  .devices .dev-head .h-ent { text-align: right; padding-right: 12px; }
  /* the buttons are icons; the label of "add" stays, and all labels show on wide screens */
  .devices .dev .acts .lbl { display: none; }
  .devices .dev .acts .chip { width: 34px; padding: 0; justify-content: center; }
  @media (min-width: 761px) {
    .devices .dev .acts .chip.add { width: auto; padding: 0 10px; }
    .devices .dev .acts .chip.add .lbl { display: inline; }
  }
  @media (min-width: 1300px) {
    .devices .dev .acts .chip { width: auto; padding: 0 10px; }
    .devices .dev .acts .lbl { display: inline; }
  }
  .devices .dev .none { color: var(--muted); }
  .devices .dev .msub { display: none; }
  .devices .dev.quiet { cursor: default; }
  .devices .dev.quiet .name { color: var(--muted); }
  .spark { display: block; }
  .spark polyline { fill: none; stroke: var(--muted); stroke-width: 1.5; stroke-linejoin: round; stroke-linecap: round; }
  .devices .dev .sub { color: var(--muted); font-size: 12px; overflow-wrap: anywhere; }
  .devices .dev .stats { display: flex; flex-direction: column; align-items: flex-end; gap: 2px; font-size: 12px; color: var(--muted); white-space: nowrap; }
  @media (max-width: 760px) {
    .devices { grid-template-columns: minmax(0, 1fr) auto; }
    .devices .dev-head { display: none; }
    .devices .dev { grid-template-columns: subgrid; }
    .devices .dev .c-type, .devices .dev .c-area, .devices .dev .c-ent { display: none; }
    .devices .dev .msub { display: block; }
    .devices .dev .sub { overflow-wrap: break-word; }
    .devices .dev .stats > span:nth-child(2), .devices .dev .stats .spark, .devices .dev .stats .tag { display: none; }
    .devices .dev .values { min-width: 0; flex-wrap: wrap; }
    .devices .dev .values { grid-column: 1; grid-row: 2; }
    /* phones: the buttons shrink to their icons, next to the values */
    .devices .dev .acts { grid-column: 2; grid-row: 2; flex-wrap: nowrap; }
    .devices .dev .acts .chip { width: 34px; padding: 0; justify-content: center; }
    .devices .dev .acts .lbl { display: none; }
  }

  .pager { display: flex; flex-wrap: wrap; align-items: center; justify-content: flex-end; gap: 6px 12px;
    padding: 8px 8px 8px 16px; border-top: 1px solid var(--line); font-size: 13px; color: var(--muted); }
  .pager label { display: inline-flex; align-items: center; gap: 8px; white-space: nowrap; }
  .pager .range { min-width: 110px; text-align: right; white-space: nowrap; }
  .pager .nav { display: inline-flex; }
  .pager .icon-btn { width: 36px; height: 36px; }
  .pager .icon-btn:disabled { opacity: .35; cursor: default; background: none; color: var(--muted); }
  .pager[hidden] { display: none; }
  .pager .newer { margin-right: auto; }
  .pager .newer[hidden] { display: none; }
  .meta .chip { height: 26px; font-size: 12px; }
  .meta .chip[hidden] { display: none; }

  .empty { display: grid; justify-items: center; gap: 6px; padding: 48px 16px; text-align: center; color: var(--muted); }
  .empty svg { width: 48px; height: 48px; opacity: .5; }
  .empty b { color: var(--text); font-weight: 500; font-size: 16px; }
  .empty .chip { margin-top: 8px; }

  @media (max-width: 760px) {
    main { padding: 16px 16px 32px; }
    .header { padding: 0 16px; }
    .card { gap: 12px; }
    .gateway-title { flex-basis: calc(100% - 60px); }
    .rate { border: 0; padding: 0; flex: 1; }
    .gateway-count { flex: 1; }
    .gateway-actions { flex-basis: 100%; }
    .telegrams colgroup, .telegrams thead { display: none; }
    .telegrams, .telegrams tbody { display: block; }
    tr.row { display: grid; grid-template-columns: 28px minmax(0, 1fr) auto auto; gap: 4px 10px; padding: 12px;
      grid-template-areas: "dir who who time" "dir values signal end"; border-top: 1px solid var(--line); }
    .telegrams tbody tr:first-child { border-top: 0; }
    tr.row > td { display: block; padding: 0; border: 0; background: none !important; }
    tr.row:hover, tr.row.open { background: color-mix(in srgb, var(--soft) 60%, transparent); }
    tr.row.fresh { animation: fresh 1.2s ease-out; }
    tr.row > td.time { grid-area: time; font-size: 12px; text-align: right; }
    tr.row > td.dirc { grid-area: dir; align-self: start; }
    tr.row > td.who { grid-area: who; }
    tr.row > td.content { grid-area: values; }
    tr.row > td.sig { grid-area: signal; align-self: center; }
    tr.row > td.sig .dbm { display: none; }
    tr.row > td.end { grid-area: end; }
    tr.row > td.type, tr.row > td.gwc { display: none; }
    tr.detail-row, tr.detail-row > td { display: block; }
    tr.detail-row > td { padding: 0 12px 12px; }
    tr.empty-row, tr.empty-row > td { display: block; }
    .m-only { display: inline; }
    .d-only { display: none; }
    /* the bar stays on one line: title, badge and at most three buttons */
    .bar { flex-wrap: nowrap; gap: 6px; padding-right: 6px; }
    .bar h2 { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .bar .live { flex: none; }
    .bar .icon-btn { width: 38px; height: 38px; flex: none; }
    select.m-only { display: block; }
    .time small { display: none; }
    .pager { justify-content: space-between; gap: 4px; padding: 8px; }
    .pager .range { min-width: 0; margin-left: auto; }
    .pager .icon-btn { width: 34px; height: 34px; }
    .pager label span { display: none; }
    .filters .search { flex-basis: 100%; }
    /* the view switch gets a line of its own and scrolls instead of cutting off a view */
    #view { flex-basis: 100%; flex-wrap: nowrap; overflow-x: auto; scrollbar-width: none; }
    #view::-webkit-scrollbar { display: none; }
    #view button { flex: 1 0 auto; justify-content: center; padding: 0 10px; }
    .filters .chip { padding: 0 10px; font-size: 12px; flex: 1 1 auto; justify-content: center; }
    .who .line1 { flex-wrap: wrap; row-gap: 4px; }
    .who .name { flex: 1 1 100%; }
  }
  @media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation: none !important; transition: none !important; } }
`;

function bars(dbm) {
  if (dbm == null) return "";
  const level = dbm >= -70 ? 4 : dbm >= -80 ? 3 : dbm >= -90 ? 2 : 1;
  const rects = [0, 1, 2, 3]
    .map((i) => `<rect x="${i * 5}" y="${10 - i * 3}" width="3" height="${4 + i * 3}" rx="1" class="${i < level ? "on" : ""}"></rect>`)
    .join("");
  return `<svg class="bars" viewBox="0 0 18 14" role="img" aria-label="${dbm} dBm"><title>${dbm} dBm</title>${rects}</svg>`;
}

// buttons that keep the keyboard focus when their row or card is drawn again
const FOCUSABLE = [".expand", "[data-copy]", "[data-only]", ".add", "[data-free]", '[data-gateway-action="filter"]', '[data-gateway-action="details"]'];

// column sort: each compares ascending; equal rows stay newest first
const collator = new Intl.Collator(undefined, { numeric: true, sensitivity: "base" });
const SORTERS = {
  time: (a, b) => (a.time < b.time ? -1 : a.time > b.time ? 1 : 0),
  dir: (a, b) => collator.compare(a.dir, b.dir),
  sender: (a, b) => collator.compare(a.device || `\uffff${a.sender}`, b.device || `\uffff${b.sender}`), // unknown last
  type: (a, b) => collator.compare(RORG[a.rorg] || a.rorg, RORG[b.rorg] || b.rorg),
  dbm: (a, b) => (a.dbm ?? -999) - (b.dbm ?? -999),
  gateway: (a, b) => collator.compare(a.gateway_name || "", b.gateway_name || ""),
};
const DESC_FIRST = new Set(["time", "dbm"]); // first click: newest, strongest
// Devices view: column sort on the merged list; equal rows by name, a missing value sorts as the lowest
const byName = (a, b) => collator.compare(a.name || `\uffff${a.id}`, b.name || `\uffff${b.id}`);
const DEV_SORTERS = {
  name: byName,
  type: (a, b) => collator.compare(a.eep || "\uffff", b.eep || "\uffff") || byName(a, b),
  area: (a, b) => collator.compare(a.area || "\uffff", b.area || "\uffff") || byName(a, b),
  entities: (a, b) => (a.entities ?? -1) - (b.entities ?? -1) || byName(a, b),
  heard: (a, b) => (a.time ?? -1) - (b.time ?? -1) || byName(a, b),
  signal: (a, b) => (a.dbm ?? 0) - (b.dbm ?? 0) || byName(a, b), // no signal (bus): as the strongest
  busy: (a, b) => a.count - b.count || byName(a, b),
};
const DEV_DESC_FIRST = new Set(["entities", "heard", "busy"]); // first click: most, newest
const DEV_STATUS = ["", "known", "unknown", "silent"];
const OLD_DEV_SORTS = { name: { key: "name", desc: false }, recent: { key: "heard", desc: true }, weak: { key: "signal", desc: false }, busy: { key: "busy", desc: true } };

const NO_FILTER = { gateway: "", text: "", dir: "", type: "", repeats: false, unknown: false, devStatus: "", area: "" };

function loadView() {
  const fallback = { pageSize: 50, sort: { key: "time", desc: true }, devSort: { key: "name", desc: false }, filter: { ...NO_FILTER } };
  try {
    const view = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
    const saved = view.filter || {};
    const text = (v) => (typeof v === "string" ? v : "");
    return {
      pageSize: PAGE_SIZES.includes(view.pageSize) ? view.pageSize : 50,
      sort: SORTERS[view.sort?.key] ? { key: view.sort.key, desc: !!view.sort.desc } : fallback.sort,
      devSort: DEV_SORTERS[view.devSort?.key] ? { key: view.devSort.key, desc: !!view.devSort.desc } : OLD_DEV_SORTS[view.devSort] || fallback.devSort,
      filter: {
        gateway: text(saved.gateway),
        text: text(saved.text),
        dir: ["rx", "tx"].includes(saved.dir) ? saved.dir : "",
        type: text(saved.type),
        repeats: saved.repeats === true,
        unknown: saved.unknown === true,
        devStatus: DEV_STATUS.includes(saved.devStatus) ? saved.devStatus : "",
        area: text(saved.area),
      },
    };
  } catch (err) {
    return fallback;
  }
}

function rowKey(r) {
  return `${r.time}|${r.dir}|${r.sender}|${r.data}|${r.gateway}`;
}

class EnOceanEltakoPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._rows = [];
    this._pending = [];
    this._missed = 0; // telegrams while paused, also those beyond the held-back ones
    this._paused = false;
    this._link = "connecting"; // the telegram stream: "connecting", "live" or "offline"
    this._conn = null; // the websocket connection whose events are followed
    this._onReady = () => this._setLink(this._unsub ? "live" : "connecting");
    this._onDisconnected = () => this._setLink("offline");
    this._view = "telegrams"; // or "devices" (one line per sender) or "senders" (sender ID pools)
    this._tk = { entry: "", tab: "", preview: null, previewError: "", mapping: null, selected: new Set(), carry: true, open: new Set(), busy: false, filter: "ready", mfilter: "all", q: "", folded: new Set(), more: new Set() };
    this._pools = [];
    this._pool = ""; // shown pool
    this._freeing = null; // blocked sender ID waiting for its confirmation
    this._sidFolded = new Set(); // devices whose IDs are hidden in the Sender IDs view
    const view = loadView();
    this._filter = view.filter;
    this._sort = view.sort;
    this._devSort = view.devSort;
    this._pageSize = view.pageSize;
    this._offset = 0; // first row of the page within the sorted, filtered rows
    this._pageFirst = null; // that row: new rows sorting before it keep the page in place
    this._newAbove = 0;
    this._multi = false; // more than one gateway: gateway column and filter
    this._gateways = [];
    this._expanded = new Set();
    this._keys = new Set(); // rows shown or pending, so a repeated history is not added twice
    this._cleared = new Set(); // rows removed with "clear display"
    this._gatewayDetails = new Set();
    this._fresh = new Set();
    this._unsub = null;
    this._frame = null;
    this._timer = null;
    this._drawn = new WeakMap(); // last HTML per container: unchanged status costs nothing
    this._stale = { list: false, cards: false, devices: false }; // redraw held back while text is selected
    this._onKey = (e) => this._keydown(e);
    // a click anywhere outside the "more" menu closes it
    this._onPointer = (e) => {
      const more = this.shadowRoot.querySelector(".more");
      if (more && !e.composedPath().includes(more) && !this.shadowRoot.getElementById("moreMenu").hidden) this._toggleMenu(false);
    };
    // a hidden tab asks for no status; back in view it catches up at once
    this._onVisible = () => {
      if (!document.hidden && this._hass) this._refreshStatus();
    };
    this._onSelection = () => {
      if (this._stale.list) this._render(true);
      if (this._stale.cards) this._renderCards(true);
      if (this._stale.devices) this._render(true);
    };
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    this.style.colorScheme = hass.themes?.darkMode ? "dark" : "light";
    this.toggleAttribute("dark", !!hass.themes?.darkMode);
    // the default theme keeps the panel's own accent; any other theme or colour sets it
    const theme = hass.selectedTheme?.theme || hass.themes?.theme;
    this.toggleAttribute("themed", !!((theme && theme !== "default") || hass.selectedTheme?.primaryColor));
    if (first) {
      this._t = TEXT[(hass.language || "en").startsWith("de") ? "de" : "en"];
      this._build();
    }
    if (this._menu) this._menu.hass = hass;
    if (this.isConnected) this._watchConnection();
    if (this.isConnected && !this._unsub) this._subscribe();
  }

  _watchConnection() {
    // the websocket resubscribes by itself after a reconnect; the badge follows its state
    const conn = this._hass?.connection;
    if (conn === this._conn) return;
    this._unwatchConnection();
    this._conn = conn;
    conn?.addEventListener("ready", this._onReady);
    conn?.addEventListener("disconnected", this._onDisconnected);
  }

  _unwatchConnection() {
    this._conn?.removeEventListener?.("ready", this._onReady);
    this._conn?.removeEventListener?.("disconnected", this._onDisconnected);
    this._conn = null;
  }

  _setLink(state) {
    this._link = state;
    this._renderBar();
  }

  set narrow(narrow) {
    this._narrow = narrow;
    if (this._menu) this._menu.narrow = narrow;
  }

  connectedCallback() {
    window.addEventListener("keydown", this._onKey);
    document.addEventListener("selectionchange", this._onSelection);
    document.addEventListener("visibilitychange", this._onVisible);
    document.addEventListener("pointerdown", this._onPointer);
    if (this._hass) this._watchConnection();
    if (this._hass && !this._unsub) this._subscribe();
  }

  disconnectedCallback() {
    window.removeEventListener("keydown", this._onKey);
    document.removeEventListener("selectionchange", this._onSelection);
    document.removeEventListener("visibilitychange", this._onVisible);
    document.removeEventListener("pointerdown", this._onPointer);
    clearInterval(this._timer);
    this._timer = null;
    clearTimeout(this._tkTyping);
    this._unwatchConnection();
    if (this._unsub) {
      this._unsub.then((unsub) => unsub()).catch(() => {});
      this._unsub = null;
    }
  }

  // ---- structure ---------------------------------------------------------------------------

  _build() {
    const t = this._t;
    this.shadowRoot.innerHTML = `
      <style>${STYLE}${TAKEOVER_STYLE}</style>
      <header class="header">
        <div class="brand"><ha-menu-button></ha-menu-button>${LOGO}<div><b>${esc(t.title)}</b></div></div>
        <nav role="tablist" id="view" aria-label="${esc(t.title)}">
          <button role="tab" data-view="telegrams" aria-controls="panel" aria-selected="true">${esc(t.viewTelegrams)}</button>
          <button role="tab" data-view="devices" aria-controls="panel" aria-selected="false" tabindex="-1">${esc(t.viewDevices)}</button>
          <button role="tab" data-view="senders" aria-controls="panel" aria-selected="false" tabindex="-1">${esc(t.viewSenders)}</button>
          <button role="tab" data-view="takeover" aria-controls="panel" aria-selected="false" tabindex="-1" hidden>${esc(t.viewTakeover)}</button>
        </nav>
      </header>
      <main>
        <section id="gatewaySection" aria-label="${esc(t.gateways)}">
          <div class="cards" id="cards"></div>
        </section>
        <section class="panel" id="panel" role="tabpanel" data-view="telegrams" aria-label="${esc(t.telegrams)}">
          <div class="bar">
            <h2 id="viewTitle">${esc(t.telegrams)}</h2>
            <span class="live list-only" id="live"><i></i><span></span></span>
            <span class="spacer"></span>
            <button class="icon-btn list-only" id="pause"></button>
            <button class="icon-btn tg-only" id="send" title="${esc(t.send)}" aria-label="${esc(t.send)}" aria-expanded="false">${svg(ICON.send)}</button>
            <button class="icon-btn list-only d-only" id="export" title="${esc(t.export)}" aria-label="${esc(t.export)}">${svg(ICON.download)}</button>
            <button class="icon-btn tg-only d-only" id="clear" title="${esc(t.clear)}" aria-label="${esc(t.clear)}">${svg(ICON.clear)}</button>
            <span class="more m-only list-only">
              <button class="icon-btn" id="more" title="${esc(t.more)}" aria-label="${esc(t.more)}" aria-haspopup="menu" aria-expanded="false" aria-controls="moreMenu">${svg(ICON.more)}</button>
              <span class="menu" id="moreMenu" role="menu" hidden>
                <button role="menuitem" data-act="export">${svg(ICON.download)}<span id="moreExport">${esc(t.exportShort)}</span></button>
                <button role="menuitem" class="tg-only" data-act="clear">${svg(ICON.clear)}${esc(t.clear)}</button>
              </span>
            </span>
          </div>
          <div class="filters list-only">
            <label class="search" title="${esc(t.searchKey)}">
              ${svg(ICON.search)}
              <input id="text" type="search" placeholder="${esc(t.search)}" aria-label="${esc(t.search)}" autocomplete="off">
              <button class="icon-btn" id="clearText" aria-label="${esc(t.clearSearch)}" title="${esc(t.clearSearch)}" hidden>${svg(ICON.close)}</button>
            </label>
            <div class="segmented tg-only" role="group" id="dir">
              <button data-dir="" aria-pressed="true">${esc(t.dirAll)}</button>
              <button data-dir="rx" aria-pressed="false">${esc(t.rx)}</button>
              <button data-dir="tx" aria-pressed="false">${esc(t.tx)}</button>
            </div>
            <select class="select" id="gatewayFilter" aria-label="${esc(t.gateway)}" hidden></select>
            <select class="select tg-only" id="typeFilter" aria-label="${esc(t.type)}"></select>
            <button class="chip tg-only" id="unknown" aria-pressed="false">${esc(t.unknownOnly)}</button>
            <button class="chip tg-only" id="repeats" aria-pressed="false">${esc(t.repeats)}</button>
            <select class="select m-only tg-only" id="sortSelect" aria-label="${esc(t.sortLabel)}"></select>
            <select class="select dev-only" id="devStatus" aria-label="${esc(t.devStatus[""])}">${Object.entries(t.devStatus)
              .map(([key, label]) => `<option value="${key}">${esc(label)}</option>`)
              .join("")}</select>
            <select class="select dev-only" id="devArea" aria-label="${esc(t.devCols.area)}" hidden></select>
            <select class="select m-only dev-only" id="devSort" aria-label="${esc(t.devSort)}" title="${esc(t.devSort)}"></select>
          </div>
          <form class="sendform tg-only" id="sendForm" hidden>
            <h3>${esc(t.sendTitle)}</h3>
            <p>${esc(t.sendHint)}</p>
            <div class="fields">
              <label id="sendGatewayRow"><span>${esc(t.sendGateway)}</span><select class="select" id="sendGateway"></select></label>
              <label><span>${esc(t.sendSender)}</span><select class="select" id="sendSender"></select></label>
              <label><span>${esc(t.sendType)}</span><select class="select" id="sendType">${[["F6", "RPS"], ["D5", "1BS"], ["A5", "4BS"], ["D2", "VLD"]].map(([v, l]) => `<option value="${v}">${l} (${v})</option>`).join("")}</select></label>
              <label><span>${esc(t.sendData)}</span><input class="text" id="sendData" autocomplete="off" spellcheck="false" placeholder="70" required></label>
              <label><span>${esc(t.sendStatus)}</span><input class="text" id="sendStatus" autocomplete="off" spellcheck="false" value="30" required></label>
            </div>
            <div class="buttons"><button class="chip" type="button" id="sendCancel">${esc(t.sendCancel)}</button><button class="chip primary" type="submit" id="sendGo">${svg(ICON.send)}${esc(t.sendAction)}</button></div>
          </form>
          <div class="notice" id="notice" hidden><span></span><button class="icon-btn" id="closeNotice" aria-label="${esc(t.closeNotice)}" title="${esc(t.closeNotice)}">${svg(ICON.close)}</button></div>
          <div class="meta list-only"><span id="count"></span><button class="chip reset" id="resetTop" hidden>${esc(t.resetFilters)}</button></div>
          <div class="devices" id="devices"></div>
          <div class="senders" id="senders"></div>
          <div class="takeover" id="takeover"></div>
          <table class="telegrams tg-only" id="table"><colgroup id="cols"></colgroup><thead id="thead"></thead><tbody id="list"></tbody></table>
          <div class="pager list-only" id="pager">
            <button class="chip newer" id="newer" hidden></button>
            <label><span>${esc(t.rowsPerPage)}</span><select class="select" id="pageSize" aria-label="${esc(t.rowsPerPage)}">${PAGE_SIZES.map((n) => `<option value="${n}">${n}</option>`).join("")}</select></label>
            <span class="range" id="range" aria-live="polite"></span>
            <span class="nav">
              <button class="icon-btn" id="pgFirst" title="${esc(t.firstPage)}" aria-label="${esc(t.firstPage)}">${svg(ICON.first)}</button>
              <button class="icon-btn" id="pgPrev" title="${esc(t.prevPage)}" aria-label="${esc(t.prevPage)}">${svg(ICON.prev)}</button>
              <button class="icon-btn" id="pgNext" title="${esc(t.nextPage)}" aria-label="${esc(t.nextPage)}">${svg(ICON.next)}</button>
              <button class="icon-btn" id="pgLast" title="${esc(t.lastPage)}" aria-label="${esc(t.lastPage)}">${svg(ICON.last)}</button>
            </span>
          </div>
        </section>
      </main>`;
    const $ = (id) => this.shadowRoot.getElementById(id);
    this._menu = this.shadowRoot.querySelector("ha-menu-button");
    this._menu.hass = this._hass;
    this._menu.narrow = this._narrow;

    $("text").addEventListener("input", (e) => {
      $("clearText").hidden = !e.target.value;
      this._set("text", e.target.value.trim());
    });
    $("clearText").addEventListener("click", (e) => {
      e.preventDefault();
      this._setText("");
    });
    $("dir").addEventListener("click", (e) => {
      const button = e.target.closest("button");
      if (button) this._set("dir", button.dataset.dir);
    });
    $("view").addEventListener("click", (e) => {
      const button = e.target.closest("button");
      if (button) this._setView(button.dataset.view);
    });
    $("view").addEventListener("keydown", (e) => {
      const tabs = [...$("view").querySelectorAll("button:not([hidden])")];
      const at = tabs.indexOf(e.target);
      const to = { ArrowRight: at + 1, ArrowLeft: at - 1, Home: 0, End: tabs.length - 1 }[e.key];
      if (at < 0 || to === undefined) return;
      e.preventDefault();
      const tab = tabs[(to + tabs.length) % tabs.length];
      this._setView(tab.dataset.view);
      tab.focus();
    });
    $("senders").addEventListener("click", (e) => this._sendersClick(e));
    $("senders").addEventListener("keydown", (e) => {
      if ((e.key === "Enter" || e.key === " ") && e.target.matches("[data-fold]")) {
        e.preventDefault();
        this._sendersClick(e);
      }
    });
    $("takeover").addEventListener("click", (e) => this._takeoverClick(e));
    $("takeover").addEventListener("change", (e) => this._takeoverChange(e));
    $("takeover").addEventListener("input", (e) => this._takeoverInput(e));
    $("senders").addEventListener("change", (e) => {
      if (e.target.id !== "poolSelect") return;
      this._pool = e.target.value;
      this._freeing = null;
      this._renderSenderIds();
    });
    $("devices").addEventListener("click", (e) => {
      if (e.target.closest(".reset")) {
        this._resetFilters();
        return;
      }
      const head = e.target.closest("[data-dsort]");
      if (head) {
        const key = head.dataset.dsort;
        this._setDevSort(key, this._devSort.key === key ? !this._devSort.desc : DEV_DESC_FIRST.has(key));
        return;
      }
      const add = e.target.closest(".add");
      if (add) {
        this._addDevice(add.dataset.id);
        return;
      }
      const dev = e.target.closest(".dev:not(.quiet)"); // a device not heard has no telegrams to show
      if (!dev || this._selecting($("devices"))) return;
      this._setText(dev.dataset.only);
      this._setView("telegrams");
    });
    $("unknown").addEventListener("click", () => this._set("unknown", !this._filter.unknown));
    $("repeats").addEventListener("click", () => this._set("repeats", !this._filter.repeats));
    $("gatewayFilter").addEventListener("change", (e) => this._set("gateway", e.target.value));
    $("typeFilter").addEventListener("change", (e) => this._set("type", e.target.value));
    $("resetTop").addEventListener("click", () => this._resetFilters());
    $("thead").addEventListener("click", (e) => {
      const button = e.target.closest("[data-sort]");
      if (!button) return;
      const key = button.dataset.sort;
      this._setSort(key, this._sort.key === key ? !this._sort.desc : DESC_FIRST.has(key));
    });
    $("devSort").addEventListener("change", (e) => {
      const [key, dir] = e.target.value.split(":");
      this._setDevSort(key, dir === "desc");
    });
    $("devStatus").addEventListener("change", (e) => this._set("devStatus", e.target.value));
    $("devArea").addEventListener("change", (e) => this._set("area", e.target.value));
    $("sortSelect").addEventListener("change", (e) => {
      const [key, dir] = e.target.value.split(":");
      this._setSort(key, dir === "desc");
    });
    $("pageSize").addEventListener("change", (e) => {
      this._pageSize = Number(e.target.value);
      this._offset = Math.floor(this._offset / this._pageSize) * this._pageSize;
      this._saveView();
      this._render();
    });
    $("pager").addEventListener("click", (e) => {
      const button = e.target.closest("button");
      if (!button || button.disabled) return;
      const size = this._pageSize;
      const total = this._total || 0;
      const moves = {
        pgFirst: 0,
        newer: 0,
        pgPrev: Math.max(0, this._offset - size),
        pgNext: this._offset + size,
        pgLast: Math.max(0, Math.floor((total - 1) / size) * size),
      };
      if (!(button.id in moves)) return;
      this._offset = moves[button.id];
      this._render();
    });
    $("pause").addEventListener("click", () => this._togglePause());
    $("clear").addEventListener("click", () => {
      this._offset = 0;
      // added up: a second clear must not bring back what the first one removed
      for (const key of this._keys) this._cleared.add(key);
      // the server repeats at most HISTORY telegrams: older keys are no longer needed
      for (const key of [...this._cleared].slice(0, Math.max(0, this._cleared.size - MAX_ROWS))) this._cleared.delete(key);
      this._keys = new Set();
      this._rows = [];
      this._pending = [];
      this._missed = 0;
      this._expanded.clear();
      this._renderBar();
      this._render();
    });
    $("export").addEventListener("click", () => this._export());
    $("more").addEventListener("click", () => this._toggleMenu());
    $("moreMenu").addEventListener("click", (e) => {
      const item = e.target.closest("[data-act]");
      if (!item) return;
      this._toggleMenu(false);
      if (item.dataset.act === "export") this._export();
      else $("clear").click();
    });
    $("moreMenu").addEventListener("keydown", (e) => {
      // arrow keys move through the items, Escape closes and returns to the button
      const items = [...$("moreMenu").querySelectorAll("button")].filter((b) => b.offsetParent);
      const at = items.indexOf(this.shadowRoot.activeElement);
      if (e.key === "Escape") {
        e.stopPropagation();
        this._toggleMenu(false);
        $("more").focus();
      } else if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        items[(at + (e.key === "ArrowDown" ? 1 : -1) + items.length) % items.length]?.focus();
      }
    });
    $("send").addEventListener("click", () => this._toggleSend());
    $("sendCancel").addEventListener("click", () => this._toggleSend(false));
    $("sendGateway").addEventListener("change", () => this._renderSenders());
    $("sendType").addEventListener("change", () => this._sendTypeChanged());
    $("sendForm").addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        this._toggleSend(false);
        $("send").focus();
      }
    });
    $("sendForm").addEventListener("submit", (e) => {
      e.preventDefault();
      this._send();
    });
    $("closeNotice").addEventListener("click", () => this._notice(""));
    $("cards").addEventListener("click", (e) => {
      const button = e.target.closest("[data-gateway-action]");
      if (!button) return;
      const entry = button.closest(".card").dataset.entry;
      if (button.dataset.gatewayAction === "details") {
        if (this._gatewayDetails.has(entry)) this._gatewayDetails.delete(entry);
        else this._gatewayDetails.add(entry);
        this._renderCards();
      } else this._set("gateway", this._filter.gateway === entry ? "" : entry);
    });
    $("list").addEventListener("click", (e) => this._listClick(e));
    $("pageSize").value = String(this._pageSize);
    this._renderDevSort();
    $("text").value = this._filter.text;
    $("clearText").hidden = !this._filter.text;
    this._renderHead();
    this._renderFilters();
    this._renderBar();
    this._renderCards();
    this._render();
  }

  _keydown(e) {
    const input = this.shadowRoot.getElementById("text");
    const target = e.composedPath()[0];
    const typing = target?.isContentEditable || target?.matches?.("input, textarea, select");
    // search and pause exist only in the views with the telegram list
    const shortcut = (this._view === "telegrams" || this._view === "devices") && !typing && !e.defaultPrevented && !e.ctrlKey && !e.metaKey && !e.altKey;
    if (e.key === "/" && input && shortcut) {
      e.preventDefault();
      input.focus();
    } else if ((e.key === "p" || e.key === "P") && shortcut) {
      e.preventDefault();
      this._togglePause();
    } else if (e.key === "Escape" && this.shadowRoot.activeElement === input) {
      this._setText("");
      input.blur();
    }
  }

  // ---- data --------------------------------------------------------------------------------

  async _subscribe() {
    const unsub = this._hass.connection.subscribeMessage((row) => this._add(row), {
      type: "enocean_eltako/telegrams/subscribe",
      history: HISTORY,
    });
    this._unsub = unsub;
    this._setLink(this._hass.connection.connected === false ? "offline" : "connecting");
    unsub.then(
      () => {
        if (this._unsub === unsub) this._setLink("live");
      },
      () => {
        // failed (e.g. connection lost while subscribing): the next hass update tries again
        if (this._unsub === unsub) this._unsub = null;
        this._setLink("offline");
      }
    );
    await this._refreshStatus();
    this._checkTakeover();
    clearInterval(this._timer);
    this._timer = setInterval(() => {
      if (!document.hidden) this._refreshStatus();
    }, STATUS_INTERVAL);
  }

  async _refreshStatus() {
    let gateways;
    try {
      gateways = await this._hass.callWS({ type: "enocean_eltako/gateways" });
    } catch (err) {
      return;
    }
    this._gateways = gateways;
    // the browser's clock may be off: times from the server are measured against the server's
    const server = gateways.find((g) => g.server_time != null)?.server_time;
    if (server != null) this._skew = server * 1000 - Date.now();
    // a remembered gateway filter for a gateway that is gone would hide everything
    if (this._filter.gateway && !gateways.some((g) => g.entry_id === this._filter.gateway)) {
      this._set("gateway", "");
    }
    this._renderCards(true);
    if (this._view === "devices") this._render(true); // "heard x ago" moves on
    if (this._view === "senders" && !this._freeing) this._loadPools();
    const multi = gateways.length > 1;
    if (multi !== this._multi) {
      this._multi = multi;
      this._renderHead();
      this._render();
    }
    this._renderFilters();
  }

  _add(row) {
    // every (re)subscription sends the buffered telegrams again: after a websocket reconnect
    // and when Home Assistant reattaches the panel; keep only those not seen yet
    const key = rowKey(row);
    if (row.history) {
      delete row.history;
      if (this._keys.has(key) || this._cleared.has(key)) return;
    }
    this._keys.add(key);
    if (this._paused) {
      // held back up to the list size; older ones would drop out on resume anyway
      this._pending.push(row);
      this._missed += 1;
      for (const r of this._pending.splice(0, this._pending.length - MAX_ROWS)) this._keys.delete(rowKey(r));
      this._renderBar();
      return;
    }
    this._keepPlace(row);
    this._rows.unshift(row);
    this._trim();
    if (this._initialised) this._fresh.add(key);
    this._schedule();
  }

  _trim() {
    for (const r of this._rows.splice(MAX_ROWS)) {
      const key = rowKey(r);
      this._keys.delete(key);
      this._expanded.delete(key);
      // the oldest drop out; sorted oldest first they stood before the page
      if (this._offset && this._pageFirst && this._matches(r) && this._compare(r, this._pageFirst) < 0) this._offset -= 1;
    }
  }

  _keepPlace(row) {
    // on a later page, a new row sorting before it moves the page along: the rows being
    // read stay where they are, and a button offers the new ones
    if (!this._offset || !this._pageFirst || !this._matches(row)) return;
    if (this._compare(row, this._pageFirst) < 0) {
      this._offset += 1;
      this._newAbove += 1;
    }
  }

  _compare(a, b) {
    const order = SORTERS[this._sort.key](a, b);
    return (this._sort.desc ? -order : order) || SORTERS.time(b, a);
  }

  _setSort(key, desc) {
    this._sort = { key, desc };
    this._offset = 0;
    this._saveView();
    this._renderHead();
    this._render();
  }

  _saveView() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ pageSize: this._pageSize, sort: this._sort, devSort: this._devSort, filter: this._filter }));
    } catch (err) {
      // private window or blocked storage: the view just is not remembered
    }
  }

  _schedule() {
    if (this._frame) return;
    this._frame = requestAnimationFrame(() => {
      this._frame = null;
      this._render(true);
      this._initialised = true;
    });
  }

  _set(key, value) {
    this._filter[key] = value;
    this._offset = 0;
    this._saveView();
    if (key === "gateway") this._renderCards();
    this._renderFilters();
    this._render();
  }

  _setView(view) {
    this._view = view;
    this._offset = 0;
    const $ = (id) => this.shadowRoot.getElementById(id);
    $("panel").dataset.view = view;
    // the gateway cards filter the telegrams; Sender IDs and Takeover pick their gateway themselves
    $("gatewaySection").hidden = view === "senders" || view === "takeover";
    // export saves what the view shows: telegrams, or the sender list
    const exportLabel = view === "devices" ? this._t.exportDevices : this._t.export;
    $("moreExport").textContent = view === "devices" ? this._t.exportDevicesShort : this._t.exportShort;
    this._toggleMenu(false);
    this._renderFilters();
    $("export").title = exportLabel;
    $("export").setAttribute("aria-label", exportLabel);
    if (view !== "telegrams") this._toggleSend(false);
    // the heading names the view; the section's label follows it
    const title = { telegrams: this._t.telegrams, devices: this._t.viewDevices, senders: this._t.viewSenders, takeover: this._t.viewTakeover }[view];
    $("viewTitle").textContent = title;
    $("panel").setAttribute("aria-label", title);
    if (view === "senders") this._loadPools();
    if (view === "takeover") this._loadTakeover();
    for (const button of $("view").querySelectorAll("button")) {
      // tabs: only the chosen one is in the tab order, the arrow keys move between them
      button.setAttribute("aria-selected", String(button.dataset.view === view));
      button.tabIndex = button.dataset.view === view ? 0 : -1;
    }
    this._render();
  }

  _setText(value) {
    const input = this.shadowRoot.getElementById("text");
    input.value = value;
    this.shadowRoot.getElementById("clearText").hidden = !value;
    this._set("text", value);
  }

  _togglePause() {
    this._paused = !this._paused;
    this._missed = 0;
    if (!this._paused) {
      for (const row of this._pending) this._keepPlace(row);
      this._rows = [...this._pending.reverse(), ...this._rows];
      this._pending = [];
      this._trim();
    }
    this._renderBar();
    this._render();
  }

  _toggleRow(key) {
    if (this._expanded.has(key)) this._expanded.delete(key);
    else this._expanded.add(key);
    this._render();
  }

  _listClick(e) {
    const add = e.target.closest(".add");
    if (add) {
      e.stopPropagation();
      this._addDevice(add.dataset.id);
      return;
    }
    const copy = e.target.closest("[data-copy]");
    if (copy) {
      this._copy(copy.dataset.copy);
      return;
    }
    const only = e.target.closest("[data-only]");
    if (only) {
      this._setText(only.dataset.only);
      return;
    }
    if (e.target.closest(".reset")) {
      this._resetFilters();
      return;
    }
    if (e.target.closest(".details") || this._selecting(this.shadowRoot.getElementById("list"))) return;
    const row = e.target.closest(".row");
    if (row) this._toggleRow(row.dataset.key);
  }

  _resetFilters() {
    this._filter = { ...NO_FILTER };
    this._offset = 0;
    this._saveView();
    this.shadowRoot.getElementById("text").value = "";
    this.shadowRoot.getElementById("clearText").hidden = true;
    this._renderCards();
    this._renderFilters();
    this._render();
  }

  async _addDevice(sender) {
    this._notice("");
    let result;
    try {
      result = await this._hass.callWS({ type: "enocean_eltako/discover", sender });
    } catch (err) {
      this._notice(this._t.addResult[err.code] || this._t.addResult.failed);
      return;
    }
    if (result.entry_id) {
      // the sender waits under "Add device" of its gateway on the integration page
      // the hash makes the integration page scroll to and highlight that gateway
      this._navigate(`/config/integrations/integration/enocean_eltako#config_entry=${result.entry_id}`);
      return;
    }
    this._notice(this._t.addResult[result.reason] || this._t.addResult.failed);
  }

  _navigate(path) {
    // Home Assistant's own navigation: no page reload
    history.pushState(null, "", path);
    window.dispatchEvent(new CustomEvent("location-changed", { detail: { replace: false } }));
    if (path.includes("#")) window.dispatchEvent(new HashChangeEvent("hashchange"));
  }

  _toggleMenu(open = this.shadowRoot.getElementById("moreMenu").hidden) {
    const $ = (id) => this.shadowRoot.getElementById(id);
    $("moreMenu").hidden = !open;
    $("more").setAttribute("aria-expanded", String(open));
    if (open) [...$("moreMenu").querySelectorAll("button")].find((b) => b.offsetParent)?.focus();
  }

  _toggleSend(open = this.shadowRoot.getElementById("sendForm").hidden) {
    const $ = (id) => this.shadowRoot.getElementById(id);
    $("sendForm").hidden = !open;
    $("send").setAttribute("aria-expanded", String(open));
    $("send").classList.toggle("on", open);
    if (open) {
      const loaded = this._gateways.filter((g) => g.loaded);
      this._options($("sendGateway"), loaded.map((g) => [g.entry_id, g.title]), this._filter.gateway || loaded[0]?.entry_id || "");
      $("sendGatewayRow").hidden = loaded.length < 2;
      this._renderSenders();
      this._sendTypeChanged(false);
    } else if ($("notice").querySelector("span").textContent === this._t.noSenders) {
      this._notice(""); // the hint belongs to the form
    }
  }

  _sendTypeChanged(status = true) {
    // a rocker telegram carries its button state in the status byte; the example shows the length
    const $ = (id) => this.shadowRoot.getElementById(id);
    const type = SEND_TYPES[$("sendType").value];
    if (status) $("sendStatus").value = type.status;
    $("sendData").placeholder = type.example;
    $("sendData").maxLength = type.bytes[1] * 3; // room for spaces between the bytes
  }

  _sendCheck() {
    // the same checks as the server, before anything goes out
    const $ = (id) => this.shadowRoot.getElementById(id);
    const [min, max] = SEND_TYPES[$("sendType").value].bytes;
    const data = $("sendData").value.replace(/\s/g, "");
    const status = $("sendStatus").value.replace(/\s/g, "");
    if (!/^([0-9a-f]{2})+$/i.test(data) || !/^[0-9a-f]{2}$/i.test(status)) return "invalid_format";
    return data.length / 2 < min || data.length / 2 > max ? "invalid_length" : "";
  }

  _renderSenders() {
    const t = this._t;
    const $ = (id) => this.shadowRoot.getElementById(id);
    const gateway = this._gateways.find((g) => g.entry_id === $("sendGateway").value);
    const senders = gateway?.senders || [];
    const keep = senders.some((s) => s.id === $("sendSender").value) ? $("sendSender").value : senders[0]?.id || "";
    this._options($("sendSender"), senders.map((s) => [s.id, `${s.device} · ${s.id}`]), keep);
    $("sendGo").disabled = !senders.length;
    if (!senders.length) this._notice(t.noSenders);
    else if (this.shadowRoot.getElementById("notice").textContent === t.noSenders) this._notice("");
  }

  async _send() {
    const t = this._t;
    const $ = (id) => this.shadowRoot.getElementById(id);
    if (!$("sendSender").value) return;
    const invalid = this._sendCheck();
    if (invalid) {
      this._notice(t.sendResult[invalid]);
      return;
    }
    $("sendGo").disabled = true;
    try {
      const result = await this._hass.callWS({
        type: "enocean_eltako/send",
        entry_id: $("sendGateway").value,
        sender: $("sendSender").value,
        rorg: $("sendType").value,
        data: $("sendData").value.trim(),
        status: $("sendStatus").value.trim(),
      });
      this._notice(t.sendResult[result.result] || t.sendResult.unknown);
    } catch (err) {
      this._notice(t.sendResult[err.code] || t.sendResult.unknown);
    }
    $("sendGo").disabled = false;
  }

  _notice(text) {
    const notice = this.shadowRoot.getElementById("notice");
    notice.hidden = !text;
    notice.querySelector("span").textContent = text;
  }

  _number(value, options = {}) {
    // as the user's profile says: number format ("language", "system", "comma_decimal" ...)
    const locale = this._hass.locale || {};
    const language = locale.language || this._hass.language;
    const locales = { system: undefined, comma_decimal: ["en-US", "en"], decimal_comma: ["de", "es", "it"], space_comma: ["fr", "sv", "cs"] };
    const format = locale.number_format;
    return value.toLocaleString(format in locales ? locales[format] : language, { ...options, ...(format === "none" ? { useGrouping: false } : {}) });
  }

  _time(date, withDate = false) {
    // as the user's profile says: 12 or 24 hours, and the browser's or the server's time zone
    const locale = this._hass.locale || {};
    const options = {
      hour: "2-digit", minute: "2-digit", second: "2-digit",
      hour12: locale.time_format === "12" ? true : locale.time_format === "24" ? false : undefined,
      timeZone: locale.time_zone === "server" ? this._hass.config?.time_zone : undefined,
      ...(withDate ? { year: "numeric", month: "2-digit", day: "2-digit" } : {}),
    };
    return date.toLocaleString(locale.time_format === "system" ? undefined : locale.language || this._hass.language, options);
  }

  _now() {
    // now on the server's clock (milliseconds), see _refreshStatus
    return Date.now() + (this._skew || 0);
  }

  _isHidden(gateway, sender) {
    // a sender hidden from the gateway's discovery is not offered as a new device here either
    return !!this._gateways.find((g) => g.entry_id === gateway)?.hidden?.includes(sender);
  }

  _matches(r) {
    const f = this._filter;
    return (
      (!f.gateway || r.gateway === f.gateway) &&
      (!f.dir || r.dir === f.dir) &&
      (!f.type || r.rorg === f.type) &&
      (f.repeats || !r.duplicate) &&
      !(f.unknown && (r.device || r.dir === "tx" || this._isHidden(r.gateway, r.sender))) &&
      this._textMatches(r)
    );
  }

  _textMatches(r, extra = []) {
    // the search box, the same in Telegrams and Devices: names, data, profiles, values, the ID
    const text = this._filter.text.toLowerCase();
    if (!text) return true;
    const compact = text.replace(/[-:\s]/g, "");
    return (
      [r.device, r.data, r.teach_in, r.profile, r.eep, r.model, r.gateway_name, ...(r.candidates || []), ...extra].some((v) => v && String(v).toLowerCase().includes(text)) ||
      (r.fields || []).some((field) => String(field.label).toLowerCase().includes(text)) ||
      (!!compact && String(r.sender).replace(/-/g, "").toLowerCase().includes(compact))
    );
  }

  _visible() {
    return this._rows.filter((r) => this._matches(r));
  }

  _captureLine(r) {
    // gateway as the entry ID, like the capture service writes it
    return JSON.stringify(Object.fromEntries(CAPTURE_KEYS.map((k) => [k, r[k]])));
  }

  async _copy(key) {
    const row = this._rows.find((r) => rowKey(r) === key);
    if (!row) return;
    try {
      await navigator.clipboard.writeText(this._captureLine(row));
      this._notice(this._t.copied);
    } catch (err) {
      this._notice(this._t.copyFailed);
    }
  }

  _export() {
    if (this._view === "devices") {
      this._exportDevices();
      return;
    }
    const lines = this._visible().slice().reverse().map((r) => this._captureLine(r)).join("\n");
    this._download(lines + "\n", "application/x-ndjson", `enocean-telegrams-${new Date().toISOString().replace(/[:.]/g, "-")}.jsonl`);
  }

  _exportDevices() {
    // the device list as shown (filter and order, all pages), one CSV row per device
    const t = this._t;
    // like the list: a switch state as its value alone, raw data where nothing is decoded
    const values = (fields, data) => (fields?.length
      ? fields.map((f) => (f.label === "on" || f.label === "state" ? this._value(f.value) : `${this._label(f.label)} ${this._value(f.value)}${f.unit ? ` ${f.unit}` : ""}`)).join("; ")
      : data);
    const head = [t.devCols.name, "ID", t.eep, t.devCols.area, t.devCols.entities, t.gateway, t.lastHeardAt, t.telegrams, t.perMinute, "dBm", t.content];
    const lines = this._deviceList().map((d) => [
      d.name || t.unknownDevice, d.id, d.eepFull || d.eep, d.area ?? "", d.entities ?? "", d.gateway_name,
      d.time != null ? new Date(d.time).toISOString() : "", d.count, d.perMinute, d.dbm ?? "", d.silent ? t.silent : values(d.fields, d.data),
    ]);
    const csv = [head, ...lines].map((l) => l.map((v) => `"${String(v).replace(/"/g, '""')}"`).join(",")).join("\n");
    this._download(csv + "\n", "text/csv", `enocean-devices-${new Date().toISOString().replace(/[:.]/g, "-")}.csv`);
  }

  _download(text, type, name) {
    const link = document.createElement("a");
    link.href = URL.createObjectURL(new Blob([text], { type }));
    link.download = name;
    link.click();
    setTimeout(() => URL.revokeObjectURL(link.href), 1000);
  }

  // ---- rendering ---------------------------------------------------------------------------

  _renderBar() {
    const t = this._t;
    const live = this.shadowRoot.getElementById("live");
    if (!live) return;
    // pausing is the user's choice; a lost stream matters more and shows through it
    const state = this._link !== "live" ? this._link : this._paused ? "paused" : "live";
    live.classList.toggle("paused", state === "paused");
    live.classList.toggle("connecting", state === "connecting");
    live.classList.toggle("offline", state === "offline");
    live.querySelector("span").textContent = { live: t.live, paused: t.paused(this._missed), connecting: t.connecting, offline: t.offline }[state];
    const pause = this.shadowRoot.getElementById("pause");
    const label = `${this._paused ? t.resume : t.pause} (P)`;
    pause.innerHTML = svg(this._paused ? ICON.play : ICON.pause);
    pause.title = label;
    pause.setAttribute("aria-label", label);
    pause.classList.toggle("on", this._paused);
  }

  _renderFilters() {
    const f = this._filter;
    const $ = (id) => this.shadowRoot.getElementById(id);
    for (const button of $("dir").querySelectorAll("button")) {
      button.setAttribute("aria-pressed", String(button.dataset.dir === f.dir));
    }
    $("unknown").setAttribute("aria-pressed", String(f.unknown));
    $("repeats").setAttribute("aria-pressed", String(f.repeats));
    const gateways = $("gatewayFilter");
    this._options(gateways, [["", this._t.allGateways], ...this._gateways.map((g) => [g.entry_id, g.title])], f.gateway);
    gateways.hidden = !this._multi && !f.gateway;
    const devices = this._view === "devices";
    $("resetTop").hidden = !(f.gateway || f.text || (devices ? f.devStatus || f.area : f.dir || f.type || f.repeats || f.unknown));
  }

  _options(select, options, value) {
    // rebuilt only when the choices change, so an open list stays open
    const key = JSON.stringify(options);
    if (select.dataset.options !== key) {
      select.innerHTML = options.map(([v, label]) => `<option value="${esc(v)}">${esc(label)}</option>`).join("");
      select.dataset.options = key;
    }
    select.value = value;
  }

  _renderHead() {
    // static header: rebuilt only for a new sort or when the gateway column comes or goes
    const t = this._t;
    const columns = [
      ["time", t.time, "time"],
      ["dir", "", "dir", t.direction],
      ["who", t.sender, "sender"],
      ["type", t.type, "type"],
      ["content", t.content],
      ["signal", t.signal, "dbm"],
      ...(this._multi ? [["gw", t.gateway, "gateway"]] : []),
      ["end", ""],
    ];
    const $ = (id) => this.shadowRoot.getElementById(id);
    const focused = this.shadowRoot.activeElement?.dataset?.sort;
    $("cols").innerHTML = columns.map(([id]) => `<col class="c-${id}">`).join("");
    $("thead").innerHTML = `<tr>${columns
      .map(([id, label, sort, aria]) => {
        if (!sort) return `<th scope="col"><span>${esc(label)}</span></th>`;
        const active = this._sort.key === sort;
        const state = active ? ` aria-sort="${this._sort.desc ? "descending" : "ascending"}"` : "";
        return `<th scope="col"${state}><button data-sort="${sort}" title="${esc(t.sortHint)}" aria-label="${esc(aria || label)}">${esc(label)}${svg(ICON.chevron, "sort")}</button></th>`;
      })
      .join("")}</tr>`;
    if (focused) $("thead").querySelector(`[data-sort="${focused}"]`)?.focus({ preventScroll: true });
    const options = Object.entries(t.sortOptions).filter(([v]) => this._multi || !v.startsWith("gateway"));
    const current = `${this._sort.key}:${this._sort.desc ? "desc" : "asc"}`;
    // a column order without a preset (e.g. a second click on a header): named after the column
    const column = { time: t.time, dir: t.direction, sender: t.sender, type: t.type, dbm: t.signal, gateway: t.gateway }[this._sort.key];
    if (!options.some(([v]) => v === current)) options.push([current, `${column} ${this._sort.desc ? "↓" : "↑"}`]);
    this._options($("sortSelect"), options, current);
  }

  _renderPager(total, shown) {
    const t = this._t;
    const $ = (id) => this.shadowRoot.getElementById(id);
    const last = this._offset + shown >= total;
    $("range").textContent = total ? t.range(this._offset + 1, this._offset + shown, total) : t.range(0, 0, 0);
    $("pgFirst").disabled = $("pgPrev").disabled = this._offset === 0;
    $("pgNext").disabled = $("pgLast").disabled = last;
    const newer = $("newer");
    newer.hidden = !(this._offset && this._newAbove);
    newer.textContent = t.newAbove(this._newAbove);
    $("pager").hidden = total <= PAGE_SIZES[0] && this._offset === 0; // a short list needs no pages
  }

  _renderCards(background = false) {
    const t = this._t;
    const cards = this.shadowRoot.getElementById("cards");
    if (!cards || this._hold("cards", cards, background)) return;
    if (!this._gateways.length) {
      this._replace(cards, `<div class="hint">${esc(t.noGateways)}</div>`);
      return;
    }
    const now = this._now() / 1000;
    this._replace(cards, this._gateways
      .map((gw) => {
        let pill = ["", t.notLoaded];
        if (gw.loaded) {
          if (gw.connected) pill = ["ok", t.connected];
          else if (gw.on_demand) pill = ["idle", t.onDemand];
          else pill = ["bad", gw.disconnected_since ? `${t.disconnected} ${t.since(Math.round(now - gw.disconnected_since))}` : t.disconnected];
        }
        const last = gw.last_telegram != null ? `${t.lastHeard} ${t.ago(Math.max(0, Math.round(now - gw.last_telegram)))}` : t.never;
        const rate = gw.per_minute ?? "–";
        const stat = (label, value, warn) => `<span>${esc(label)} <b class="${warn ? "warn" : ""}">${esc(value)}</b></span>`;
        const selected = this._filter.gateway === gw.entry_id;
        // with a single gateway its filter would show the same list: no button (unless it is set)
        const expanded = this._gatewayDetails.has(gw.entry_id);
        const sub = [gw.model !== gw.title ? gw.model : "", gw.base_id].filter(Boolean).join(" · ");
        return `<article class="card${selected ? " selected" : ""}" data-entry="${esc(gw.entry_id)}">
          <div class="gateway-icon">${svg(ICON.tower)}</div>
          <div class="gateway-title"><span class="name">${esc(gw.title)}</span><div class="gateway-status"><span class="pill ${pill[0]}"><i></i>${esc(pill[1])}</span><span class="sub">${esc(sub)}</span></div></div>
          ${gw.loaded ? `<div class="rate"><div><b>${esc(rate)}</b> <span>${esc(t.perMinute)}</span></div><span class="last">${esc(last)}</span></div><div class="gateway-count"><b>${esc(gw.devices ?? "–")} ${esc(t.devices)}</b><span>${esc(gw.free_senders ?? "–")} ${esc(t.freeSenders)}</span></div>` : ""}
          <div class="gateway-actions">${this._gateways.length > 1 || selected ? `<button class="chip" data-gateway-action="filter" title="${esc(t.cardHint)}" aria-pressed="${selected}">${svg(ICON.filter)}${esc(t.telegrams)}</button>` : ""}<button class="chip" data-gateway-action="details" aria-expanded="${expanded}">${esc(t.details)}${svg(ICON.chevron)}</button></div>
          ${expanded ? `<div class="gateway-details"><div class="connection mono">${esc(gw.connection)}</div><div class="stats">${stat(t.queue, gw.queue ?? "–", gw.queue > 5)}${stat(t.unconfirmed, gw.unconfirmed ?? "–", gw.unconfirmed > 0)}${stat(t.freeSenders, gw.free_senders ?? "–", gw.free_senders === 0)}</div>${gw.via_proxy ? this._proxyLine(gw) : ""}</div>` : ""}
        </article>`;
      })
      .join(""));
  }

  _proxyLine(gw) {
    const t = this._t;
    const p = gw.proxy;
    if (!p) {
      return `<div class="proxy"><span class="tag">${esc(t.viaProxy("", ""))}</span><span class="muted">${esc(t.proxyUnreachable)}</span></div>`;
    }
    const share = Number(p.duty_of_limit ?? 0);
    const level = share >= 80 ? "bad" : share >= 50 ? "warn" : "";
    return `<div class="proxy">
        <span class="tag">${esc(t.viaProxy(p.app, p.version))}</span>
        <span>${esc(t.programs(p.programs ?? 0))}</span>
        ${p.exclusive_peer ? `<span class="tag warn">${esc(t.alone(p.exclusive_peer))}</span>` : ""}
      </div>
      <div class="airtime" title="${esc(t.airtimeHint)}">
        <span>${esc(t.airtime)}</span>
        <span class="meter" role="meter" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${share}" aria-label="${esc(t.airtimeHint)}"><i class="${level}" style="width:${Math.min(100, share)}%"></i></span>
        <b>${esc(this._number(share, { maximumFractionDigits: 1 }))} %</b>
      </div>`;
  }

  _value(value) {
    if (value === true) return this._t.on;
    if (value === false) return this._t.off;
    if (typeof value === "number") return this._number(value, { maximumFractionDigits: 2 });
    return String(value);
  }

  _previous(r) {
    // the telegram before this one from the same sender: same direction and type, no repetition
    const start = this._rows.indexOf(r);
    if (start < 0 || r.duplicate) return null;
    for (let i = start + 1; i < this._rows.length; i++) {
      const o = this._rows[i];
      if (o.sender === r.sender && o.dir === r.dir && o.rorg === r.rorg && !o.duplicate && o.gateway === r.gateway) return o;
    }
    return null;
  }

  _diff(r) {
    // the data bytes that differ from the previous telegram, and the values that changed
    const prev = this._previous(r);
    if (!prev) return null;
    const bytes = r.data.match(/../g) || [];
    const before = prev.data.match(/../g) || [];
    const same = bytes.length === before.length;
    const raw = bytes.map((b, i) => (same && b === before[i] ? b : `<span class="chg">${esc(b)}</span>`)).join(" ");
    const now = new Map((r.fields || []).map((f) => [f.label, f]));
    const changes = (prev.fields || [])
      .map((old) => [old, now.get(old.label)])
      .filter(([old, cur]) => cur && cur.value !== old.value)
      .map(([old, cur]) => `${this._label(cur.label)}: ${this._value(old.value)} → ${this._value(cur.value)}${cur.unit ? ` ${cur.unit}` : ""}`);
    const unchanged = same && r.data === prev.data;
    return { raw, prev: prev.data, text: changes.length ? changes.join(" · ") : unchanged ? this._t.noChange : "" };
  }

  _repeats(r) {
    // copies of this telegram the gateway heard (repeaters, a second path), within one second
    const at = Date.parse(r.time);
    return this._rows.filter(
      (o) => o.duplicate && o.sender === r.sender && o.data === r.data && o.gateway === r.gateway && Math.abs(Date.parse(o.time) - at) <= 1000
    ).length;
  }

  _profile(profile) {
    return this._t.profiles[profile] || profile;
  }

  _label(label) {
    return this._t.fields[label] || label.replace(/_/g, " ");
  }

  _pairText(r) {
    // a command we sent and the answer of the same device, matched by time (3 s window)
    if (!r.device || r.duplicate) return "";
    const at = Date.parse(r.time);
    let best = null;
    for (const o of this._rows) {
      // the device's key, not its name: two devices may share a name (older servers: the name)
      const same = r.device_key ? o.device_key === r.device_key : o.device === r.device;
      if (!same || o.dir === r.dir || o.duplicate) continue;
      const delta = r.dir === "tx" ? Date.parse(o.time) - at : at - Date.parse(o.time);
      if (delta >= 0 && delta <= ANSWER_WINDOW && (best === null || delta < best)) best = delta;
    }
    if (best !== null) return r.dir === "tx" ? this._t.answerAfter(best) : this._t.answerTo(best);
    // the newest telegrams may still be waiting for their answer: only call it missing when old
    return r.dir === "tx" && this._now() - at > ANSWER_WINDOW ? this._t.noAnswer : "";
  }

  _row(r) {
    const t = this._t;
    const key = rowKey(r);
    const expanded = this._expanded.has(key);
    const time = new Date(r.time);
    const clock = this._time(time);
    const ms = String(time.getMilliseconds()).padStart(3, "0");
    const unknown = !r.device && r.dir === "rx";
    const hidden = unknown && this._isHidden(r.gateway, r.sender);
    const name = r.device
      ? `<span class="name">${esc(r.device)}</span>`
      : `<span class="name unknown">${esc(unknown ? t.unknownDevice : r.sender)}</span>`;
    const tags = (r.duplicate ? `<span class="tag">${esc(t.duplicate)}</span>` : "") +
      (hidden ? `<span class="tag" title="${esc(t.hiddenHint)}">${esc(t.hiddenTag)}</span>` : "");
    const extra =
      (r.teach_in ? `<span class="tag teach">${esc(t.teachIn)} ${esc(r.teach_in)}</span>` : "") +
      (r.candidates ? `<span class="tag" title="${esc(t.maybeHint)}">${esc(t.maybe)} ${esc(r.candidates.join(", "))}</span>` : "");
    const type = RORG[r.rorg] || r.rorg;
    // on phones type and gateway have no column of their own
    const line2 = [`<span class="mono">${esc(r.sender)}</span>`, r.profile ? esc(this._profile(r.profile)) : "", r.eep ? esc(r.eep) : "", r.eep?.endsWith(":eltako") && r.model ? esc(r.model) : ""].filter(Boolean).join(" · ") +
      `<span class="m-only"> · ${esc(type)}${this._multi ? ` · ${esc(r.gateway_name)}` : ""}</span>`;
    const fields = r.fields || (r.values ? Object.entries(r.values).map(([label, value]) => ({ label, value })) : null);
    const values = fields && fields.length
      ? fields
          .map((f) =>
            f.label === "on" || f.label === "state"
              ? `<span class="value"><b>${esc(this._value(f.value))}</b></span>`
              : `<span class="value"><span>${esc(this._label(f.label))}</span> <b>${esc(this._value(f.value))}</b>${f.unit ? ` ${esc(f.unit)}` : ""}</span>`
          )
          .join("")
      : `<span class="raw mono">${esc(r.data)}</span>`;
    const pair = expanded ? this._pairText(r) : "";
    const diff = expanded ? this._diff(r) : null;
    const copies = expanded && !r.duplicate ? this._repeats(r) : 0;
    const hops = parseInt(r.status, 16) & 0x0f; // low nibble of the status byte: repeater count
    const details = expanded
      ? `<tr class="detail-row" data-key="${esc(key)}"><td colspan="${this._multi ? 8 : 7}"><dl class="details">
          <div><dt>${esc(t.time)}</dt><dd class="mono">${esc(this._time(time, true))}.${ms}</dd></div>
          <div><dt>${esc(t.gateway)}</dt><dd>${esc(r.gateway_name)}</dd></div>
          <div><dt>${esc(t.type)}</dt><dd>${esc(type)} (${esc(r.rorg)})</dd></div>
          <div><dt>${esc(t.raw)}</dt><dd class="mono">${diff ? diff.raw : esc(r.data)}</dd></div>
          ${diff ? `<div><dt>${esc(t.previous)}</dt><dd class="mono">${esc(diff.prev)}</dd></div>` : ""}
          ${diff?.text ? `<div class="wide"><dt>${esc(t.change)}</dt><dd>${esc(diff.text)}</dd></div>` : ""}
          <div><dt>${esc(t.status)}</dt><dd class="mono">${esc(r.status)}</dd></div>
          <div><dt>${esc(t.destination)}</dt><dd class="mono">${esc(r.destination)}</dd></div>
          <div><dt>${esc(t.signal)}</dt><dd>${r.dbm != null ? `${esc(r.dbm)} dBm` : esc(t.unavailable)}</dd></div>
          ${hops ? `<div><dt>${esc(t.repeater)}</dt><dd>${hops}</dd></div>` : ""}
          ${copies ? `<div><dt>${esc(t.repeated)}</dt><dd>${esc(t.heardTimes(copies))}</dd></div>` : ""}
          ${r.candidates ? `<div class="wide"><dt>${esc(t.maybe)}</dt><dd class="mono">${esc(r.candidates.join(", "))}</dd></div>` : ""}
          ${r.eep ? `<div><dt>${esc(t.eep)}</dt><dd class="mono">${esc(r.eep)}</dd></div>` : ""}
          ${r.model ? `<div><dt>${esc(t.model)}</dt><dd>${esc(r.model)}</dd></div>` : ""}
          ${pair ? `<div><dt>${esc(t.pair)}</dt><dd>${esc(pair)}</dd></div>` : ""}
          ${r.profile ? `<div><dt>${esc(t.profile)}</dt><dd>${esc(this._profile(r.profile))}</dd></div>` : ""}
          <div class="actions"><button class="chip" data-copy="${esc(key)}">${svg(ICON.copy)}${esc(t.copy)}</button><button class="chip" data-only="${esc(r.device || r.sender)}">${svg(ICON.filter)}${esc(r.device ? t.filterDevice : t.filterSender)}</button>${unknown && !hidden ? `<button class="chip add" data-id="${esc(r.sender)}" title="${esc(t.addHint)}">${svg(ICON.plus)}${esc(t.add)}</button>` : ""}</div>
        </dl></td></tr>`
      : "";
    const classes = ["row", r.duplicate ? "dup" : "", expanded ? "open" : "", this._fresh.has(key) ? "fresh" : ""].filter(Boolean).join(" ");
    return `<tr class="${classes}" data-key="${esc(key)}">
      <td class="time">${esc(clock)}<small>.${ms}</small></td>
      <td class="dirc"><span class="dir ${r.dir}" title="${esc(r.dir === "rx" ? t.rx : t.tx)}">${svg(r.dir === "rx" ? ICON.rx : ICON.tx)}</span></td>
      <td class="who" title="${esc([r.device, r.sender, r.gateway_name].filter(Boolean).join(" · "))}"><div class="line1">${name}${tags}</div><div class="line2">${line2}</div></td>
      <td class="type"><span class="tag mono" title="${esc(r.rorg)}">${esc(type)}</span></td>
      <td class="content"><div class="values">${extra}${values}</div></td>
      <td class="sig"><span class="signal">${bars(r.dbm)}<span class="dbm">${r.dbm != null ? `${esc(r.dbm)} dBm` : ""}</span></span></td>
      ${this._multi ? `<td class="gwc"><div class="gw">${esc(r.gateway_name)}</div></td>` : ""}
      <td class="end"><button class="expand" aria-expanded="${expanded}" aria-label="${esc(t.details)}" title="${esc(t.details)}">${svg(ICON.chevron, "chev")}</button></td>
    </tr>${details}`;
  }

  _render(background = false) {
    const t = this._t;
    const list = this.shadowRoot.getElementById("list");
    if (!list) return;
    this._renderTypes();
    if (this._view === "devices") {
      this._renderDevices(background);
      return;
    }
    if (this._view === "senders" || this._view === "takeover") return;
    const rows = this._visible().sort((a, b) => this._compare(a, b));
    const total = rows.length;
    this._total = total;
    if (this._offset >= total) this._offset = total ? Math.floor((total - 1) / this._pageSize) * this._pageSize : 0;
    if (this._offset === 0) this._newAbove = 0;
    const page = rows.slice(this._offset, this._offset + this._pageSize);
    this._pageFirst = page[0] || null;
    this.shadowRoot.getElementById("count").textContent = t.count(total, this._rows.length);
    this._renderPager(total, page.length);
    if (this._hold("list", list, background)) return;
    if (!page.length) {
      const filtered = this._rows.length > 0;
      this._replace(list, `<tr class="empty-row"><td colspan="8"><div class="empty">${svg(ICON.tower)}<b>${esc(filtered ? t.noMatchTitle : t.emptyTitle)}</b><span>${esc(filtered ? t.noMatchText : t.emptyText)}</span>${
        filtered ? `<button class="chip reset">${esc(t.resetFilters)}</button>` : ""
      }</div></td></tr>`);
    } else {
      this._replace(list, page.map((r) => this._row(r)).join(""));
    }
    this._fresh.clear();
  }

  async _loadPools() {
    try {
      this._pools = await this._hass.callWS({ type: "enocean_eltako/sender_pools" });
    } catch (err) {
      return;
    }
    if (!this._pools.some((p) => p.id === this._pool)) this._pool = this._pools[0]?.id || "";
    this._renderSenderIds();
  }

  _poolLabel(pool) {
    return pool.kind === "bus" ? this._t.poolBus(pool.title) : pool.title;
  }

  _renderSenderIds() {
    const t = this._t;
    const container = this.shadowRoot.getElementById("senders");
    const pool = this._pools.find((p) => p.id === this._pool);
    if (!pool) {
      this._replace(container, `<div class="empty">${svg(ICON.tower)}<b>${esc(t.noGateways)}</b></div>`);
      return;
    }
    const blocked = pool.rows.filter((r) => r.state === "blocked");
    const used = pool.size - pool.free;
    const select = this._pools.length > 1
      ? `<div class="pick"><select class="select" id="poolSelect" aria-label="${esc(t.pools)}">${this._pools
          .map((p) => `<option value="${esc(p.id)}"${p.id === pool.id ? " selected" : ""}>${esc(this._poolLabel(p))}</option>`)
          .join("")}</select></div>`
      : "";
    // one block per device with its IDs; blocked IDs (deleted devices) first, they need doing
    const groups = new Map();
    for (const r of pool.rows) {
      const key = r.ref || r.device || r.id;
      if (!groups.has(key)) groups.set(key, { device: r.device, ref: r.ref, rows: [] });
      groups.get(key).rows.push(r);
    }
    const isBlocked = (r) => r.state === "blocked";
    const list = [...groups.values()]
      .map((g) => ({ ...g, blocked: g.rows.some(isBlocked), rows: g.rows.sort((a, b) => isBlocked(b) - isBlocked(a) || collator.compare(a.id, b.id)) }))
      .sort((a, b) => b.blocked - a.blocked || (a.device == null) - (b.device == null) || collator.compare(a.device || "", b.device || ""));
    const html = list
      .map((g) => {
        const name = g.device
          ? `<span class="sid-name">${esc(g.device)}</span>`
          : `<span class="sid-name deleted" title="${esc(g.ref || "")}">${esc(t.deletedDevice)}</span>`;
        const rows = g.rows
          .map((r) => `<div class="sid-row${isBlocked(r) ? " blocked" : ""}" data-key="${esc(r.id)}">
            <span class="sid-id mono">${esc(r.id)}</span><span class="sid-dec mono" title="${esc(t.colDecimal)}">${esc(r.decimal)}</span><span class="sid-profile">${esc(r.profile ? this._profile(r.profile) : "–")}</span>
            <span class="sid-state"><span class="tag ${isBlocked(r) ? "warn" : "ok"}">${esc(isBlocked(r) ? t.stateBlocked : t.stateAssigned)}</span></span>
            <span class="act">${isBlocked(r) ? `<button class="chip" data-free="${esc(r.id)}" data-device="${esc(r.device || r.ref || "")}">${esc(t.freeAction)}</button>` : ""}</span>
          </div>`)
          .join("");
        const confirm = this._freeing && g.rows.some((r) => isBlocked(r) && r.id === this._freeing.id)
          ? `<div class="confirm"><b>${esc(t.freeConfirmTitle(this._freeing.id))}</b><p>${esc(t.freeConfirmText)}</p>
              <div class="buttons"><button class="chip" data-free-cancel>${esc(t.sendCancel)}</button><button class="chip primary" data-free-confirm>${esc(t.freeConfirm)}</button></div></div>`
          : "";
        const gkey = g.ref || g.device || "";
        const folded = !g.blocked && this._sidFolded.has(gkey);
        return `<div class="sid-group${g.blocked ? " blocked" : ""}${folded ? " folded" : ""}">
          <div class="sid-head" data-fold="${esc(gkey)}" role="button" tabindex="0" aria-expanded="${!folded}" title="${esc(t.foldGroup)}">${name}<span class="sub">${esc(t.idCount(g.rows.length))}</span><span class="fold" aria-hidden="true">${folded ? "▸" : "▾"}</span></div>
          ${rows}${g.blocked ? `<p class="sid-hint">${esc(t.blockedHint)}</p>` : ""}${confirm}</div>`;
      })
      .join("");
    const byId = new Map(pool.rows.map((r) => [r.decimal, r]));
    const away = new Set(pool.unavailable);
    const tiles = Array.from({ length: pool.size }, (_, i) => {
      const n = pool.first + i;
      const hex = [24, 16, 8, 0].map((sh) => ((n >>> sh) & 255).toString(16).toUpperCase().padStart(2, "0")).join("-");
      const r = byId.get(n);
      const state = r ? r.state : away.has(n) ? "unavailable" : "free";
      const label = { assigned: t.stateAssigned, blocked: t.stateBlocked, unavailable: t.stateUnavailable, free: t.stateFree }[state];
      const who = r?.device ? ` · ${r.device}` : "";
      const text = `${hex} (${n}) · ${label}${who}`;
      return `<button class="t-${state}"${r ? ` data-goto="${esc(r.id)}"` : ""} title="${esc(text)}" aria-label="${esc(text)}"></button>`;
    }).join("");
    this._replace(container, `${select}
      <div class="pool">
        <div><div class="meta-label">${esc(t.poolFree)}</div><div class="big">${esc(pool.free)} <small>${esc(t.poolOf(pool.size))}</small></div></div>
        <div><span class="meter" role="meter" aria-valuemin="0" aria-valuemax="${esc(pool.size)}" aria-valuenow="${esc(used)}" aria-label="${esc(t.pools)}"><i style="width:${pool.size ? Math.round((used / pool.size) * 100) : 0}%"></i></span>
          <div class="range"><span class="mono">${esc(pool.start)} – ${esc(pool.end)}</span> · ${esc(t.poolSummary(pool.rows.length - blocked.length, blocked.length))}</div>
          ${pool.next_free ? `<div class="next">${esc(t.poolNext)}: <span class="mono">${esc(pool.next_free)}</span></div>` : ""}</div>
      </div>
      <div class="map" role="group" aria-label="${esc(t.mapLabel)}">${tiles}</div>
      ${pool.rows.length ? `<div class="sid-cols"><span>${esc(t.colId)}</span><span>${esc(t.colDecimal)}</span><span>${esc(t.colProfile)}</span><span>${esc(t.colStatus)}</span><span></span></div><div class="sid-list">${html}</div>` : `<div class="hint">${esc(t.noSenderIds)}</div>`}`);
  }

  _sendersClick(e) {
    const free = e.target.closest("[data-free]");
    const fold = e.target.closest("[data-fold]");
    const goto = e.target.closest("[data-goto]");
    if (fold) {
      const key = fold.dataset.fold;
      if (!this._sidFolded.delete(key)) this._sidFolded.add(key);
      this._renderSenderIds();
    } else if (goto) {
      // a folded group opens so the row can be shown
      const row = [...this.shadowRoot.querySelectorAll(".sid-row")].find((r) => r.dataset.key === goto.dataset.goto);
      const head = row?.closest(".sid-group")?.querySelector("[data-fold]");
      if (head && this._sidFolded.delete(head.dataset.fold)) this._renderSenderIds();
      const shown = [...this.shadowRoot.querySelectorAll(".sid-row")].find((r) => r.dataset.key === goto.dataset.goto);
      shown?.scrollIntoView({ block: "center", behavior: "smooth" });
    } else if (free) {
      this._freeing = { id: free.dataset.free, device: free.dataset.device };
      this._renderSenderIds();
    } else if (e.target.closest("[data-free-cancel]")) {
      this._freeing = null;
      this._renderSenderIds();
    } else if (e.target.closest("[data-free-confirm]")) {
      this._freeSender();
    }
  }

  async _freeSender() {
    const t = this._t;
    const { id } = this._freeing;
    try {
      await this._hass.callWS({ type: "enocean_eltako/sender_pools/free", pool: this._pool, sender: id });
      this._notice(t.freed);
    } catch (err) {
      this._notice(t.freeErrors[err.code] || t.freeErrors.unknown);
    }
    this._freeing = null;
    await this._loadPools();
  }

  _deviceItems() {
    // one entry per sender: the latest telegram of each sender heard, joined with the set-up device
    // of that ID (area, entities, model), plus the set-up devices without a telegram in the buffer
    const f = this._filter;
    const since = this._now() - 60000;
    const setup = new Map();
    for (const g of this._gateways) {
      for (const d of g.radio_devices || []) setup.set(d.id, { ...d, gateway: g.entry_id, gateway_name: g.title });
    }
    const heard = new Map();
    const heardIds = new Set();
    for (const r of this._rows) {
      if (r.dir !== "rx" || r.duplicate) continue;
      heardIds.add(r.sender);
      if (f.gateway && r.gateway !== f.gateway) continue;
      const key = `${r.gateway}|${r.sender}`;
      let d = heard.get(key);
      if (!d) {
        d = { last: r, fields: null, teach: null, candidates: null, count: 0, perMinute: 0, dbm: [] };
        heard.set(key, d);
      }
      d.count += 1;
      if (!d.fields && (r.fields || r.values)) d.fields = r.fields || Object.entries(r.values).map(([label, value]) => ({ label, value }));
      // an unknown sender: what its telegrams tell about it, newest first
      d.teach ||= r.teach_in || null;
      d.candidates ||= r.candidates || null;
      if (Date.parse(r.time) >= since) d.perMinute += 1;
      if (r.dbm != null && d.dbm.length < TREND_POINTS) d.dbm.unshift(r.dbm); // oldest first
    }
    const items = [];
    for (const [key, d] of heard) {
      const r = d.last;
      const info = setup.get(r.sender);
      items.push({
        key, id: r.sender, name: r.device || null, unknown: !r.device, silent: !!info?.silent, quiet: false,
        hidden: !r.device && this._isHidden(r.gateway, r.sender),
        eepFull: info?.eep || r.eep || "", eep: this._eepLabel(info?.eep || r.eep || RORG[r.rorg] || r.rorg),
        model: info?.model || (r.eep?.endsWith(":eltako") && r.model) || "", area: info?.area || null, entities: info?.entities ?? null,
        gateway: r.gateway, gateway_name: r.gateway_name, time: Date.parse(r.time), count: d.count, perMinute: d.perMinute,
        dbm: r.dbm, trend: d.dbm, fields: d.fields, data: r.data, teach: d.teach, candidates: d.candidates, rorg: r.rorg,
      });
    }
    for (const d of setup.values()) {
      if (heardIds.has(d.id) || (f.gateway && d.gateway !== f.gateway)) continue;
      items.push({
        key: `quiet|${d.id}`, id: d.id, name: d.device, unknown: false, silent: d.silent, quiet: true,
        eepFull: d.eep || "", eep: this._eepLabel(d.eep || ""), model: d.model || "", area: d.area, entities: d.entities,
        gateway: d.gateway, gateway_name: d.gateway_name, time: d.last_seen != null ? d.last_seen * 1000 : null, count: 0, perMinute: 0,
        dbm: null, trend: [], fields: null, data: "", teach: null, candidates: null, rorg: "",
      });
    }
    return items;
  }

  _eepLabel(eep) {
    // "A5-08-01:std" -> "A5-08-01"; the Eltako variant is named in the tooltip
    return String(eep || "").replace(/:(std|eltako)$/, "");
  }

  _devMatches(d) {
    const f = this._filter;
    if (f.area && d.area !== f.area) return false;
    if (f.devStatus === "known" && d.unknown) return false;
    if (f.devStatus === "unknown" && (!d.unknown || d.hidden)) return false;
    if (f.devStatus === "silent" && !d.silent) return false;
    const text = f.text.toLowerCase();
    if (!text) return true;
    const compact = text.replace(/[-:\s]/g, "");
    return (
      [d.name, d.eepFull, d.model, d.area, d.gateway_name, d.data, d.teach, ...(d.candidates || [])].some((v) => v && String(v).toLowerCase().includes(text)) ||
      (d.fields || []).some((field) => String(field.label).toLowerCase().includes(text)) ||
      (!!compact && d.id.replace(/-/g, "").toLowerCase().includes(compact))
    );
  }

  _deviceList() {
    // filtered and in the chosen order
    const { key, desc } = this._devSort;
    const sorter = DEV_SORTERS[key];
    return this._deviceItems().filter((d) => this._devMatches(d)).sort((a, b) => (desc ? sorter(b, a) : sorter(a, b)));
  }

  _setDevSort(key, desc) {
    this._devSort = { key, desc };
    this._offset = 0;
    this._saveView();
    this._renderDevSort();
    this._render();
  }

  _renderDevSort() {
    const t = this._t;
    const current = `${this._devSort.key}:${this._devSort.desc ? "desc" : "asc"}`;
    const options = Object.entries(t.devSorts);
    // a column order without a preset (a second click on a header): named after the column
    if (!options.some(([v]) => v === current) && t.devCols[this._devSort.key]) options.push([current, `${t.devCols[this._devSort.key]} ${this._devSort.desc ? "↓" : "↑"}`]);
    this._options(this.shadowRoot.getElementById("devSort"), options, current);
  }

  _renderDevices(background) {
    const t = this._t;
    const container = this.shadowRoot.getElementById("devices");
    const all = this._deviceItems();
    const devices = this._deviceList();
    const total = devices.length;
    this._total = total;
    this._newAbove = 0;
    if (this._offset >= total) this._offset = total ? Math.floor((total - 1) / this._pageSize) * this._pageSize : 0;
    const page = devices.slice(this._offset, this._offset + this._pageSize);
    this.shadowRoot.getElementById("count").textContent = t.devCount(total, all.length);
    this._renderPager(total, page.length);
    // the area filter offers the areas in use (and a chosen one that has just emptied)
    const areas = [...new Set([...all.map((d) => d.area).filter(Boolean), ...(this._filter.area ? [this._filter.area] : [])])].sort(collator.compare);
    const areaSelect = this.shadowRoot.getElementById("devArea");
    this._options(areaSelect, [["", t.allAreas], ...areas.map((a) => [a, a])], this._filter.area);
    areaSelect.hidden = !areas.length;
    this.shadowRoot.getElementById("devStatus").value = this._filter.devStatus;
    if (this._hold("devices", container, background)) return;
    if (!page.length) {
      const filtered = all.length > 0;
      this._replace(container, `<div class="empty">${svg(ICON.tower)}<b>${esc(filtered ? t.noMatchTitle : t.noDevices)}</b>${
        filtered ? `<span>${esc(t.noMatchText)}</span><button class="chip reset">${esc(t.resetFilters)}</button>` : ""
      }</div>`);
      return;
    }
    const now = this._now();
    const cols = [["name", t.devCols.name], ["type", t.devCols.type], ["area", t.devCols.area], ["entities", t.devCols.entities, "h-ent"], ["values", t.devCols.values], ["heard", t.devCols.heard]];
    const head = `<div class="dev-head">${cols
      .map(([key, label, cls]) => {
        if (!DEV_SORTERS[key]) return `<span>${esc(label)}</span>`;
        const state = this._devSort.key === key ? ` aria-sort="${this._devSort.desc ? "descending" : "ascending"}"` : "";
        return `<span class="${cls || ""}"><button data-dsort="${key}"${state} title="${esc(t.sortHint)}">${esc(label)}${svg(ICON.chevron, "sort")}</button></span>`;
      })
      .join("")}<span></span></div>`;
    this._replace(container, head + page.map((d) => this._deviceRow(d, now)).join(""));
  }

  _sparkline(dbm) {
    // the signal of the last telegrams as a small curve; the band is fixed (-100 to -30 dBm),
    // so curves of different senders compare
    if (dbm.length < 2) return "";
    const [w, h] = [72, 18];
    const y = (v) => (h - 2 - ((Math.min(-30, Math.max(-100, v)) + 100) / 70) * (h - 4)).toFixed(1);
    const points = dbm.map((v, i) => `${((i / (dbm.length - 1)) * w).toFixed(1)},${y(v)}`).join(" ");
    const title = this._t.trend(dbm.length, Math.min(...dbm), Math.max(...dbm));
    return `<svg class="spark" viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" role="img" aria-label="${esc(title)}"><title>${esc(title)}</title><polyline points="${points}"/></svg>`;
  }

  _deviceRow(d, now) {
    const t = this._t;
    const name = d.unknown ? `<span class="name unknown">${esc(t.unknownDevice)}</span>` : `<span class="name">${esc(d.name)}</span>`;
    const none = `<span class="none">${esc(t.noValue)}</span>`;
    const sub = [`<span class="mono">${esc(d.id)}</span>`, d.model ? esc(d.model) : "", this._multi ? esc(d.gateway_name) : ""].filter(Boolean).join(" · ");
    // phones have no columns: type, area and entities go below the ID
    const msub = [d.eep ? `<span class="mono">${esc(d.eep)}</span>` : "", d.area ? esc(d.area) : "", d.entities != null ? esc(t.entitiesN(d.entities)) : ""].filter(Boolean).join(" · ");
    const values = d.fields && d.fields.length
      ? d.fields
          .map((f) =>
            f.label === "on" || f.label === "state"
              ? `<span class="value"><b>${esc(this._value(f.value))}</b></span>`
              : `<span class="value"><span>${esc(this._label(f.label))}</span> <b>${esc(this._value(f.value))}</b>${f.unit ? ` ${esc(f.unit)}` : ""}</span>`
          )
          .join("")
      : d.quiet ? "" : `<span class="raw mono">${esc(d.data)}</span>`;
    const hints = d.unknown
      ? (d.hidden ? `<span class="tag" title="${esc(t.hiddenHint)}">${esc(t.hiddenTag)}</span>` : "") +
        (d.teach ? `<span class="tag teach">${esc(t.teachIn)} ${esc(d.teach)}</span>` : "") +
        (d.candidates ? `<span class="tag" title="${esc(t.maybeHint)}">${esc(t.maybe)} ${esc(d.candidates.join(", "))}</span>` : "")
      : d.silent ? `<span class="tag warn" title="${esc(t.silentHint)}">${esc(t.silent)}</span>` : "";
    const weak = d.dbm != null && d.dbm < WEAK_DBM;
    const heard = d.time != null ? t.ago(Math.max(0, Math.round((now - d.time) / 1000))) : t.notHeard;
    const stats = d.quiet
      ? `<span title="${esc(t.quietHint)}">${esc(heard)}</span>`
      : `<span>${esc(heard)}</span><span title="${esc(t.bufferHint)}">${esc(t.telegramsCount(d.count))} · ${esc(d.perMinute)}/min</span>
        <span class="signal">${this._sparkline(d.trend)}${bars(d.dbm)}<span class="dbm">${d.dbm != null ? `${esc(d.dbm)} dBm` : ""}</span>${weak ? `<span class="tag warn" title="${esc(t.weakHint)}">${esc(t.weak)}</span>` : ""}</span>`;
    const only = d.name || d.id;
    const acts = d.quiet
      ? ""
      : `<button class="chip" data-only="${esc(only)}" title="${esc(t.showTelegrams)}" aria-label="${esc(t.showTelegrams)}">${svg(ICON.filter)}<span class="lbl">${esc(t.telegrams)}</span></button>${
          d.unknown && !d.hidden ? `<button class="chip add" data-id="${esc(d.id)}" title="${esc(t.addHint)}" aria-label="${esc(t.addHint)}">${svg(ICON.plus)}<span class="lbl">${esc(t.add)}</span></button>` : ""
        }`;
    return `<div class="dev${d.quiet ? " quiet" : ""}" data-key="${esc(d.key)}" data-only="${esc(only)}">
      <div class="ident"><div class="line1">${name}</div><div class="sub">${sub}</div>${msub ? `<div class="sub msub">${msub}</div>` : ""}</div>
      <div class="c-type">${d.eep ? `<span class="tag mono" title="${esc(d.eepFull)}">${esc(d.eep)}</span>` : none}</div>
      <div class="c-area">${d.area ? esc(d.area) : none}</div>
      <div class="c-ent">${d.entities != null ? esc(d.entities) : none}</div>
      <div class="values">${hints}${values}</div>
      <div class="stats">${stats}</div>
      <div class="acts">${acts}</div>
    </div>`;
  }

  _renderTypes() {
    // the telegram types heard so far, plus the chosen one
    const types = new Set(this._rows.map((r) => r.rorg));
    if (this._filter.type) types.add(this._filter.type);
    const options = [...types].sort().map((rorg) => [rorg, RORG[rorg] ? `${RORG[rorg]} (${rorg})` : rorg]);
    this._options(this.shadowRoot.getElementById("typeFilter"), [["", this._t.allTypes], ...options], this._filter.type);
  }

  _selecting(container) {
    // shadowRoot.getSelection: Chromium; elsewhere the document selection reaches into it
    const sel = this.shadowRoot.getSelection ? this.shadowRoot.getSelection() : document.getSelection();
    if (!sel || sel.isCollapsed) return false;
    return sel.anchorNode === this || container.contains(sel.anchorNode);
  }

  _hold(name, container, background) {
    // a new telegram or status update does not wipe text the user is selecting (to copy an ID)
    this._stale[name] = background && this._selecting(container);
    return this._stale[name];
  }

  _replace(container, html) {
    // redraw, keeping the keyboard focus on the same button of the same row or card
    if (this._drawn.get(container) === html) return;
    this._drawn.set(container, html);
    const active = this.shadowRoot.activeElement;
    let focus = null;
    if (active && container.contains(active)) {
      const holder = active.closest("[data-key], [data-entry]");
      const selector = FOCUSABLE.find((s) => active.matches(s));
      if (holder && selector) {
        const attr = holder.hasAttribute("data-key") ? "data-key" : "data-entry";
        focus = { attr, value: holder.getAttribute(attr), selector };
      }
    }
    container.innerHTML = html;
    if (focus) {
      // a row and its details share the key: take the one that has the button
      [...container.querySelectorAll(`[${focus.attr}]`)]
        .filter((h) => h.getAttribute(focus.attr) === focus.value)
        .map((h) => h.querySelector(focus.selector))
        .find(Boolean)
        ?.focus({ preventScroll: true });
    }
  }
}

// the Takeover view (takeover.js) adds its methods to the panel
Object.assign(EnOceanEltakoPanel.prototype, takeover);

customElements.define("enocean-eltako-monitor", EnOceanEltakoPanel);
