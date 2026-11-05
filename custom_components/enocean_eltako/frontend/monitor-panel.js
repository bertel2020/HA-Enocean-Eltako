// "EnOcean" sidebar panel of the enocean_eltako integration: gateway overview and live
// telegram monitor. Plain web component, no build step. Own colours (the look of the Device
// Proxy app); light and dark mode follow Home Assistant, and a theme or primary colour of the
// user's own replaces the accent colour. Data: websocket enocean_eltako/telegrams/subscribe,
// enocean_eltako/gateways and enocean_eltako/discover.

// the parts load with this file's version (?v=<hash> from panel.py), so an update never mixes
// old and new files from the browser cache. They load after the element is defined, with retries:
// a failed import is remembered by the browser, so a top-level await here would leave the panel
// blank until a hard reload (a part fetched while Home Assistant starts or a proxy hiccups).
const VERSION = new URL(import.meta.url).search;
let applyAppearance, cleanPrefs, DEFAULTS, MODES, SCHEMES, SIZES, tokens, ICON, MAX_ROWS, anonymisedCapture, csv, documentationCsv, documentationHtml, esc, svg, TEXT, TAKEOVER_STYLE, takeover, takeoverState, INSTALLATION_STYLE, installation, installationState;
const LOAD_TRIES = 4;

async function loadParts() {
  let error;
  for (let i = 0; i < LOAD_TRIES; i++) {
    // a retry asks for a new URL: the failed one stays failed in the module map
    const v = i ? `${VERSION}${VERSION ? "&" : "?"}r=${i}` : VERSION;
    try {
      const [shared, texts, tk, inst, theme] = await Promise.all([
        import(`./shared.js${v}`),
        import(`./texts.js${v}`),
        import(`./takeover.js${v}`),
        import(`./installation.js${v}`),
        import(`./theme.js${v}`),
      ]);
      ({ ICON, MAX_ROWS, anonymisedCapture, csv, documentationCsv, documentationHtml, esc, svg } = shared);
      ({ TEXT } = texts);
      ({ applyAppearance, cleanPrefs, DEFAULTS, MODES, SCHEMES, SIZES, tokens } = theme);
      ({ TAKEOVER_STYLE, takeover, takeoverState } = tk);
      ({ INSTALLATION_STYLE, installation, installationState } = inst);
      return;
    } catch (err) {
      error = err;
      await new Promise((resolve) => setTimeout(resolve, 500 * (i + 1)));
    }
  }
  throw error;
}
let partsLoaded = null; // one shared load for every panel instance

const PAGE_SIZES = [25, 50, 100, 200];
const LOOK_KEY = "enocean_eltako_look"; // colour scheme, mode and font size: per Home Assistant user, cached per browser
const STORAGE_KEY = "enocean_eltako_monitor"; // page size, sort order and filters, per browser
const HISTORY = 200;
// the keys of a capture line (service enocean_eltako.capture): exports can be used as test fixtures
const RECORD_SECONDS = 60; // how long a device report listens to one sender
const REPORT_TELEGRAMS = 60; // telegrams of an unknown sender that a device report carries
const DEVICE_REQUEST_URL = "https://github.com/bertel2020/HA-Enocean-Eltako/issues/new?template=device_request.yml";
const CAPTURE_KEYS = ["time", "gateway", "dir", "rorg", "data", "sender", "status", "destination", "dbm", "duplicate"];
const ANSWER_WINDOW = 3000; // ms in which a device answers a command
const WEAK_DBM = -85; // below this a sender is at the edge of the range (repeater or antenna)
const TREND_POINTS = 30; // telegrams in a sender's signal curve
const STATUS_INTERVAL = 5000; // ms between gateway status updates
const NOTICE_TIME = 4000; // ms a success message stays
const TAKEOVER_CHECK = 12; // status updates between checks whether the Takeover view is needed
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
  /* the palette and the size factor --fs come from theme.js, set on the panel element */
  :host {
    display: block; min-height: 100%; background: var(--bg); color: var(--text);
    font-family: Roboto, "Noto Sans", system-ui, -apple-system, sans-serif; font-size: calc(14px * var(--fs));
    --radius: 18px; --shadow: 0 1px 2px var(--shadow-c), 0 6px 18px -10px var(--shadow-c);
  }
  * { box-sizing: border-box; }
  svg { width: 20px; height: 20px; fill: currentColor; flex: none; }
  button { font: inherit; color: inherit; background: none; border: 0; cursor: pointer; }
  button:focus-visible, input:focus-visible, select:focus-visible { outline: 3px solid var(--focus); outline-offset: 2px; }
  /* checkboxes in the accent colour, at one size */
  input[type="checkbox"] { appearance: none; -webkit-appearance: none; width: 18px; height: 18px; margin: 0; flex: none; cursor: pointer; border: 2px solid var(--muted); border-radius: 5px; background: transparent; display: inline-grid; place-content: center; vertical-align: middle; transition: background .12s, border-color .12s; }
  input[type="checkbox"]:hover { border-color: var(--accent); }
  input[type="checkbox"]:checked, input[type="checkbox"]:indeterminate { background: var(--accent); border-color: var(--accent); }
  input[type="checkbox"]:checked::after { content: ""; width: 9px; height: 5px; border: solid var(--surface); border-width: 0 0 2px 2px; transform: translateY(-1px) rotate(-45deg); }
  input[type="checkbox"]:indeterminate::after { content: ""; width: 8px; height: 2px; background: var(--surface); border-radius: 1px; }

  .header { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between;
    gap: 0 24px; background: var(--surface); border-bottom: 1px solid var(--line);
    /* logo and tabs line up with the content (max 1200 px, centred), not with the window's edges */
    padding: 0 max(24px, calc((100% - 1200px) / 2 + 24px)); }
  .brand { display: flex; align-items: center; gap: 12px; padding: 10px 0; min-height: 60px; }
  .brand ha-menu-button { margin-left: -12px; color: var(--text); }
  .brand b { display: block; font-size: calc(18px * var(--fs)); font-weight: 500; line-height: 1.2; }
  .brand small { display: block; font-size: calc(12px * var(--fs)); color: var(--muted); }
  .header .logo { width: 36px; height: 36px; flex: none; }
  /* the view tabs: their own look, not the segmented filter buttons */
  #view { display: flex; flex-wrap: wrap; gap: 4px; padding: 8px 0; }
  #view button { display: inline-flex; align-items: center; min-height: 40px; padding: 0 16px; font-size: calc(14px * var(--fs)); font-weight: 500; white-space: nowrap;
    color: var(--muted); border-radius: 20px; transition: background .15s, color .15s; }
  #view button:hover { color: var(--text); background: var(--neutral-soft); }
  #view button[aria-selected="true"] { color: var(--accent-hover); background: var(--accent-soft); }
  #view button[hidden] { display: none; }
  .header-end { display: flex; align-items: center; gap: 8px; min-width: 0; }
  .integration-link { color: var(--accent); }
  main { max-width: 1200px; margin: 0 auto; padding: 24px 24px 48px; display: grid;
    grid-template-columns: minmax(0, 1fr); gap: 16px; }
  main > section { min-width: 0; }
  h2 { margin: 0; font-size: calc(16px * var(--fs)); font-weight: 500; }
  .mono { font-family: var(--code-font-family, ui-monospace, monospace); }

  /* gateway summary: status first, technical information under Details */
  .cards { display: flex; flex-direction: column; gap: 12px; }
  .card { display: flex; flex-wrap: wrap; align-items: center; gap: 16px; padding: 20px;
    background: var(--surface); border-radius: var(--radius); border: 1px solid var(--line);
    box-shadow: var(--shadow); transition: border-color .15s, box-shadow .15s; }
  .card.selected { border: 2px solid var(--accent); padding: 19px; background: var(--accent-soft); }
  .card .name { font-size: calc(16px * var(--fs)); font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .card .sub { font-size: calc(12px * var(--fs)); color: var(--muted); overflow-wrap: anywhere; }
  .gateway-icon { display: grid; place-items: center; width: 40px; height: 40px; border-radius: 12px;
    color: var(--accent); background: var(--accent-soft); }
  .gateway-title { flex: 1 1 170px; min-width: 0; }
  .gateway-status { display: flex; flex-wrap: wrap; gap: 4px 10px; align-items: center; margin-top: 3px; }
  .pill { display: inline-flex; align-items: center; gap: 6px; font-size: calc(12px * var(--fs)); white-space: nowrap; }
  .pill i { width: 8px; height: 8px; border-radius: 50%; background: currentColor; }
  .pill.ok i { background: var(--ok); }
  .pill.bad i { background: var(--bad); }
  .pill.idle i { background: var(--warn); }
  .rate, .gateway-count { display: flex; flex-direction: column; align-items: flex-start; gap: 3px;
    padding-left: 18px; border-left: 1px solid var(--line); }
  .rate b { font-size: calc(16px * var(--fs)); font-weight: 500; line-height: 1; }
  .rate span { font-size: calc(13px * var(--fs)); color: var(--muted); }
  .rate .last { font-size: calc(12px * var(--fs)); }
  .gateway-count { font-size: calc(12px * var(--fs)); color: var(--muted); }
  .gateway-count b { font-size: calc(14px * var(--fs)); font-weight: 500; color: var(--text); }
  .gateway-actions { display: flex; flex-wrap: wrap; gap: 8px; }
  .gateway-details { flex-basis: 100%; border-top: 1px solid var(--line); padding-top: 12px; display: grid; gap: 12px; }
  .connection { font-size: calc(12px * var(--fs)); color: var(--muted); overflow-wrap: anywhere; }
  .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 4px 14px;
    font-size: calc(12px * var(--fs)); color: var(--muted); }
  .stats > span { display: flex; justify-content: space-between; gap: 8px; }
  .stats b { color: var(--text); font-weight: 500; }
  .stats b.warn { color: var(--bad); }
  .hint { color: var(--muted); font-size: calc(14px * var(--fs)); padding: 4px; }
  .proxy { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 10px; font-size: calc(12px * var(--fs));
    color: var(--muted); padding-top: 8px; border-top: 1px solid var(--line); }
  .proxy .muted { color: var(--muted); }
  .airtime { display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 8px;
    font-size: calc(12px * var(--fs)); color: var(--muted); }
  .airtime b { color: var(--text); font-weight: 500; }
  .meter { height: 6px; border-radius: 3px; background: var(--soft); overflow: hidden; }
  .meter i { display: block; height: 100%; background: var(--accent); }
  .meter i.warn { background: var(--warn); }
  .meter i.bad { background: var(--bad); }

  /* telegram section */
  .panel { background: var(--surface); border-radius: var(--radius); border: 1px solid var(--line);
    box-shadow: var(--shadow); overflow: clip; }
  .bar { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; padding: 12px 12px 12px 16px;
    border-bottom: 1px solid var(--line); position: sticky; top: 0; z-index: 2; background: var(--surface); }
  /* the gateway status in the bar, once the cards are scrolled away */
  .mini { display: inline-flex; align-items: center; gap: 12px; min-width: 0; padding: 0 4px; font-size: calc(12px * var(--fs)); color: var(--muted); border-radius: 8px; }
  .mini[hidden] { display: none; }
  .mini:hover { color: var(--text); }
  .mini > span { display: inline-flex; align-items: center; gap: 6px; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .mini i { width: 8px; height: 8px; border-radius: 50%; flex: none; background: var(--muted); }
  .mini i.ok { background: var(--ok); }
  .mini i.bad { background: var(--bad); }
  .mini i.idle { background: var(--warn); }
  .live { display: inline-flex; align-items: center; gap: 6px; font-size: calc(12px * var(--fs)); font-weight: 500; min-height: 24px; padding: 0 10px;
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
  /* clearing the list lives in the more menu; its export item repeats the icon only where the icon is hidden */
  #clear, .menu .dup { display: none; }
  .look-menu { min-width: 260px; padding: 8px 0; gap: 4px; }
  .lookgroup { display: grid; padding: 4px 0; }
  .lookgroup + .lookgroup { border-top: 1px solid var(--line-2); }
  .lookhead { padding: 4px 16px; font-size: calc(11px * var(--fs)); color: var(--muted); text-transform: uppercase; letter-spacing: .04em; }
  .look-menu button { min-height: 38px; font-size: calc(14px * var(--fs)); }
  .look-menu button[aria-checked="true"] { color: var(--accent-hover); background: var(--accent-soft); font-weight: 500; }
  .look-menu .dot { width: 14px; height: 14px; border-radius: 50%; flex: none; border: 1px solid var(--line); }
  .menu button { display: flex; align-items: center; gap: 12px; min-height: 44px; padding: 0 16px; text-align: left; white-space: nowrap; }
  .menu button:hover, .menu button:focus-visible { background: var(--accent-soft); }
  .menu svg { color: var(--muted); }
  /* the menu of the + button of an unknown sender: set up as a device, or only written down */
  .addmenu { position: fixed; z-index: 5; display: grid; min-width: 240px; padding: 6px 0; background: var(--surface); border: 1px solid var(--line); border-radius: 12px; box-shadow: 0 6px 24px rgb(0 0 0 / 18%); }
  .addmenu button { display: flex; align-items: center; gap: 12px; min-height: 48px; padding: 0 16px; text-align: left; font-size: calc(14px * var(--fs)); }
  .addmenu button:hover, .addmenu button:focus-visible { background: var(--accent-soft); }
  .addmenu svg { color: var(--muted); flex: none; }
  .addmenu small { display: block; color: var(--muted); font-size: calc(12px * var(--fs)); }

  .filters { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; padding: 12px 16px; border-bottom: 1px solid var(--line); }
  .search { flex: 1 1 260px; min-width: 0; display: flex; align-items: center; gap: 8px; height: 42px; padding: 0 6px 0 12px;
    border-radius: 10px; border: 1px solid var(--input-line); background: var(--surface); color: var(--muted); }
  .search input { flex: 1; min-width: 0; height: 100%; border: 0; background: none; outline: none; font: inherit;
    font-size: calc(14px * var(--fs)); color: var(--text); }
  .search input::placeholder { color: var(--muted); }
  .search input::-webkit-search-cancel-button, .search input::-webkit-search-decoration { -webkit-appearance: none; appearance: none; display: none; }
  .search .key { flex: none; min-width: 20px; height: 20px; padding: 0 5px; box-sizing: border-box; border: 1px solid var(--input-line); border-radius: 5px;
    font: calc(12px * var(--fs))/calc(18px * var(--fs)) var(--code-font-family, ui-monospace, monospace); color: var(--muted); text-align: center; }
  .search:focus-within .key, .search:has(input:not(:placeholder-shown)) .key { display: none; }
  @media (hover: none) { .search .key { display: none; } }
  .search .icon-btn { width: 30px; height: 30px; }
  .search .icon-btn svg { width: 18px; height: 18px; }
  .segmented { display: inline-flex; border: 1px solid var(--input-line); border-radius: 10px; overflow: hidden; }
  .segmented button { min-height: 38px; padding: 0 14px; font-size: calc(13px * var(--fs)); font-weight: 500; color: var(--text); background: var(--surface); white-space: nowrap; }
  .segmented button + button { border-left: 1px solid var(--input-line); }
  .segmented button[aria-pressed="true"] { color: var(--on-accent); background: var(--accent); }
  .chip { min-height: 36px; padding: 0 16px; border-radius: 20px; border: 1px solid var(--input-line); font-size: calc(13px * var(--fs)); font-weight: 500;
    display: inline-flex; align-items: center; justify-content: center; gap: 6px; color: var(--accent); background: var(--surface); white-space: nowrap; }
  .chip:hover:not(:disabled) { background: var(--accent-soft); color: var(--accent-hover); }
  .chip svg { width: 16px; height: 16px; }
  .chip[aria-pressed="true"] { border-color: var(--accent); color: var(--accent-hover); background: var(--accent-soft); }
  .chip.add { color: var(--accent); }
  .chip.primary { background: var(--accent); color: var(--on-accent); border-color: var(--accent); }
  .chip.primary:hover:not(:disabled) { background: var(--accent-hover); color: var(--on-accent); }
  .chip:disabled { opacity: .5; cursor: default; }
  .chip.only-icon { padding: 0; width: 36px; }
  /* three ranks of buttons: filled for the main action, outlined for others, text only for minor ones */
  .chip.text { border-color: transparent; background: none; padding: 0 10px; }
  .chip.text.warn { color: var(--warn); }
  .chip[hidden] { display: none; }
  .meta { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 6px 8px; padding: 8px 16px; font-size: calc(12px * var(--fs)); color: var(--muted); }
  .meta .active { display: flex; flex-wrap: wrap; gap: 6px; flex: 1; }
  .meta .active:empty { display: none; }
  .chip.set { padding: 0 6px 0 10px; color: var(--text); background: var(--accent-soft); border-color: transparent; }
  .chip.set svg { width: 14px; height: 14px; color: var(--muted); }
  .chip.set:hover svg { color: var(--text); }
  .filters:has(+ .statusrow) { border-bottom: 0; }
  .meta:not(:has(> :not([hidden], :empty))) { display: none; }
  #tkReport { margin-left: auto; }
  .filters[hidden], .statusrow[hidden] { display: none; }
  .statusrow { display: flex; flex-wrap: wrap; gap: 6px; padding: 0 16px 12px; border-bottom: 1px solid var(--line); }
  .statusrow .chip { min-height: 32px; color: var(--text); }
  .statusrow .chip[aria-pressed="true"] { color: var(--accent-hover); }
  /* the status filter: a calm tab strip under the tools, the pressed one underlined */
  .filters > .statusrow { order: 10; flex: 1 0 calc(100% + 32px); gap: 2px; flex-wrap: nowrap; margin: 4px -16px -12px; padding: 0 8px; border-top: 1px solid var(--line); overflow-x: auto; scrollbar-width: none; }
  .filters > .statusrow::-webkit-scrollbar { display: none; }
  .filters > .statusrow .chip { position: relative; flex: none; min-height: 42px; padding: 0 12px; border: 0; border-radius: 0; background: none; color: var(--muted); }
  .filters > .statusrow .chip:hover:not(:disabled) { background: none; color: var(--text); }
  .filters > .statusrow .chip[aria-pressed="true"] { color: var(--accent); }
  .filters > .statusrow .chip[aria-pressed="true"]::after { content: ""; position: absolute; left: 10px; right: 10px; bottom: 0; height: 2px; border-radius: 2px; background: var(--accent); }
  .filters > .statusrow .chip.zero { opacity: .55; }
  .filters > .statusrow .chip[data-status="weak"]:not(.zero) { color: var(--warn); }
  .filters > .statusrow .chip[data-status="weak"]:not(.zero)::before { content: ""; width: 7px; height: 7px; border-radius: 50%; background: var(--warn); }
  /* the filter menu */
  .chip.on { border-color: var(--accent); }
  #filterBtn[aria-expanded="true"] { background: var(--accent-soft); color: var(--accent-hover); }
  .chip .count { display: inline-grid; place-items: center; min-width: 18px; height: 18px; padding: 0 5px; border-radius: 9px;
    font-size: calc(11px * var(--fs)); font-weight: 500; background: var(--accent); color: var(--on-accent); }
  .chip .count[hidden] { display: none; }
  .filtermenu { display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); align-items: end; gap: 10px 16px;
    padding: 12px 16px 14px; border-bottom: 1px solid var(--line); background: var(--soft); }
  .filtermenu[hidden] { display: none; }
  .filtermenu .field { display: grid; gap: 4px; font-size: calc(11px * var(--fs)); color: var(--muted); text-transform: uppercase; letter-spacing: .03em; min-width: 0; }
  .filtermenu .field[hidden] { display: none; }
  .filtermenu .field .select { max-width: none; width: 100%; text-transform: none; letter-spacing: 0; }
  .filtermenu .opt { display: flex; align-items: center; gap: 10px; min-height: 38px; font-size: calc(13px * var(--fs)); cursor: pointer; }
  .notice { margin: 8px 16px 0; padding: 12px 14px; border-radius: 12px; font-size: calc(13px * var(--fs));
    background: color-mix(in srgb, var(--warn) 14%, transparent); display: flex; gap: 8px; align-items: center; }
  .notice[hidden] { display: none; }
  .notice.ok { background: color-mix(in srgb, var(--ok) 14%, transparent); }
  .notice span { flex: 1; }

  /* telegram table: sortable columns, one page at a time */
  /* own look for the lists: the browser's arrow replaced by a chevron that follows the theme */
  .select { height: 38px; border-radius: 10px; border: 1px solid var(--input-line); background-color: var(--surface);
    color: var(--text); font: inherit; font-size: calc(13px * var(--fs)); padding: 0 30px 0 10px; max-width: 220px; cursor: pointer;
    -webkit-appearance: none; appearance: none;
    background-image: linear-gradient(45deg, transparent 50%, var(--muted) 50%), linear-gradient(135deg, var(--muted) 50%, transparent 50%);
    background-position: calc(100% - 16px) 55%, calc(100% - 11px) 55%; background-size: 5px 5px; background-repeat: no-repeat; }
  .select:hover { border-color: var(--muted); }
  .select option { background: var(--surface); color: var(--text); }
  .select[hidden] { display: none; }
  .telegrams { width: 100%; border-collapse: collapse; table-layout: fixed; font-size: calc(13px * var(--fs)); }
  .telegrams col.c-time { width: 128px; } /* room for "10:04:40 PM" */
  .telegrams col.c-dir { width: 48px; }
  .telegrams col.c-who { width: 30%; }
  .telegrams col.c-type { width: 76px; }
  .telegrams col.c-signal { width: 92px; }
  .telegrams col.c-gw { width: 140px; }
  .telegrams col.c-end { width: 48px; }
  .telegrams th { position: sticky; top: var(--bar-height, 0px); z-index: 1; padding: 0; text-align: left;
    background: var(--soft); border-bottom: 1px solid var(--line); }
  .telegrams th > button, .telegrams th > span { display: flex; align-items: center; gap: 2px; width: 100%; height: 38px;
    padding: 0 8px; font-size: calc(11px * var(--fs)); font-weight: 500; color: var(--muted); text-align: left; white-space: nowrap; text-transform: uppercase; letter-spacing: .04em; }
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
  tr.row.noans > td:first-child { box-shadow: inset 3px 0 0 var(--warn); }
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
  .dir.rx { color: var(--ok); background: color-mix(in srgb, var(--ok) 16%, transparent); }
  .dir.tx { color: var(--accent); background: var(--accent-soft); }
  .who .line1 { display: flex; align-items: center; gap: 8px; min-width: 0; }
  .who .name { font-size: calc(14px * var(--fs)); font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .rorg { font-size: calc(12px * var(--fs)); color: var(--muted); }
  .who .name.unknown { font-weight: 400; color: var(--muted); }
  .who .line2 { font-size: calc(12px * var(--fs)); color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin-top: 2px; }
  .tag { flex: none; font-size: calc(12px * var(--fs)); font-weight: 500; padding: 2px 10px; border-radius: 12px; background: var(--tag-bg); color: var(--tag-text); white-space: nowrap; }
  .tag.tx { background: var(--accent-soft); color: var(--accent); }
  .who .name .to { font-weight: 400; color: var(--muted); }
  .tag.teach, .tag.warn { background: color-mix(in srgb, var(--warn) 22%, transparent); color: var(--text); }
  .tag.ok { background: color-mix(in srgb, var(--ok) 18%, transparent); color: var(--ok); }
  .values { display: flex; flex-wrap: wrap; align-items: center; gap: 4px 12px; min-width: 0; }
  .value { white-space: nowrap; }
  .value span { color: var(--muted); }
  .value b { font-weight: 500; }
  .raw { font-size: calc(12px * var(--fs)); color: var(--muted); overflow-wrap: anywhere; }
  .gw { color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .signal { display: flex; align-items: center; gap: 6px; color: var(--muted); font-size: calc(12px * var(--fs)); white-space: nowrap; }
  .end { text-align: right; }
  .end .chev { transition: transform .15s; }
  .expand { width: 32px; height: 32px; border-radius: 50%; display: inline-grid; place-items: center; color: var(--muted); }
  .expand:hover { background: var(--soft); }
  .expand[aria-expanded="true"] .chev { transform: rotate(180deg); }
  .bars { width: 18px; height: 14px; }
  .bars rect { fill: var(--line); }
  .bars rect.on { fill: var(--muted); }
  .bars.ok rect.on { fill: var(--ok); }
  .bars.warn rect.on { fill: var(--warn); }
  .bars.bad rect.on { fill: var(--bad); }
  .details { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 12px 16px; margin: 0; padding: 14px 16px; border-radius: 12px; background: var(--surface); border: 1px solid var(--line); }
  .details div { min-width: 0; }
  .details .hero { display: grid; grid-template-columns: auto minmax(0, 1fr); gap: 4px 14px; align-items: baseline; align-self: start; background: var(--soft); border-radius: 8px; padding: 10px 12px; }
  .details .hero .l { font-size: calc(11px * var(--fs)); color: var(--muted); text-transform: uppercase; letter-spacing: .04em; }
  .details .hero .v { font-size: calc(16px * var(--fs)); letter-spacing: .06em; overflow-wrap: anywhere; }
  .details .hero .v.prev { color: var(--muted); }
  .details .hero .hint { grid-column: 1 / -1; font-size: calc(12px * var(--fs)); color: var(--muted); }
  .details .acts { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 4px; align-items: flex-start; }
  .details .acts .icon-btn { width: 34px; height: 34px; border: 1px solid var(--input-line); color: var(--accent); background: var(--surface); }
  .details .acts .icon-btn:hover { background: var(--accent-soft); color: var(--accent-hover); }
  .details .acts .icon-btn svg { width: 18px; height: 18px; }
  .details .acts .icon-btn.add { background: var(--accent); border-color: var(--accent); color: var(--on-accent); }
  .details .acts .icon-btn.add:hover { background: var(--accent-hover); border-color: var(--accent-hover); }
  .details .meta { grid-column: 1 / -1; display: grid; grid-template-columns: minmax(0, 1.5fr) minmax(0, 1fr) minmax(0, 1fr); gap: 12px 16px; margin: 0; padding-top: 12px; border-top: 1px solid var(--line); }
  .details dt { font-size: calc(11px * var(--fs)); color: var(--muted); text-transform: uppercase; letter-spacing: .04em; }
  .details dd { margin: 2px 0 0; font-size: calc(14px * var(--fs)); overflow-wrap: anywhere; }
  .details .wide { grid-column: 1 / -1; }
  .chg { background: color-mix(in srgb, var(--warn) 35%, transparent); border-radius: 3px; padding: 0 2px; }
  .m-only { display: none; }
  .panel[data-view="devices"] .more.m-only, .panel[data-view="telegrams"] .more.m-only { display: inline; } /* the documentation entries live in this menu */
  .sr-only { position: absolute; width: 1px; height: 1px; margin: -1px; padding: 0; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; border: 0; }
  .sendform { padding: 12px 16px; border-bottom: 1px solid var(--line); background: color-mix(in srgb, var(--warn) 8%, transparent); }
  .sendform[hidden] { display: none; }
  .sendform h3 { margin: 0 0 4px; font-size: calc(14px * var(--fs)); font-weight: 500; }
  .sendform p { margin: 0 0 10px; font-size: calc(12px * var(--fs)); color: var(--muted); }
  .sendform .fields { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 10px 12px; }
  .sendform label { display: grid; gap: 4px; font-size: calc(11px * var(--fs)); color: var(--muted); text-transform: uppercase; letter-spacing: .03em; min-width: 0; }
  .sendform .text { height: 38px; border-radius: 10px; border: 1px solid var(--input-line); background: var(--surface); color: var(--text);
    padding: 0 10px; font: calc(13px * var(--fs)) ui-monospace, monospace; text-transform: none; min-width: 0; }
  .sendform label.check { display: flex; align-items: center; gap: 8px; align-self: end; height: 38px; text-transform: none; letter-spacing: 0; font-size: calc(13px * var(--fs)); color: var(--text); }
  .sendform label.check[hidden] { display: none; }
  .sendform .buttons { display: flex; justify-content: flex-end; gap: 8px; margin-top: 12px; }
  .sendform .err { margin-top: 6px; font-size: calc(12px * var(--fs)); color: var(--bad); }
  .sendform .err[hidden] { display: none; }
  .sendform .picklist { display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 4px 12px; margin-bottom: 10px; }
  .sendform .picklist small { margin-left: auto; color: var(--muted); font-size: calc(12px * var(--fs)); }
  .sendform ul.names { margin: 0 0 10px; padding-left: 18px; font-size: calc(13px * var(--fs)); }
  .sendform .newlabel { display: flex; gap: 8px; align-items: end; }
  .sendform .newlabel label { flex: 1; }
  .selbar { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; min-height: 48px; padding: 8px 16px; background: var(--accent-soft); border-top: 1px solid var(--line); }
  .panel[data-picked] .meta { display: none; }
  .selbar[hidden] { display: none; }
  .selbar .count { font-weight: 500; margin-right: 4px; }
  .selbar .grow { flex: 1; }
  .selbar .chip { height: 32px; background: var(--surface); }
  .selbar .chip.danger { color: var(--bad); border-color: var(--bad); }
  .sendform .chip.danger { background: var(--bad); border-color: var(--bad); color: #fff; }
  .selall { display: none; align-items: center; gap: 6px; font-size: calc(12px * var(--fs)); cursor: pointer; }
  .selbox { width: 16px; height: 16px; margin: 0; cursor: pointer; accent-color: var(--accent); }
  .devices .c-sel { display: flex; align-items: center; justify-content: center; align-self: stretch; }
  .devices .dev .quiet-note { color: var(--muted); font-size: calc(12px * var(--fs)); }
  @media (hover: hover) {
    .devices .dev .acts .icon-btn { opacity: .55; transition: opacity .15s; }
    .devices .dev:hover .acts .icon-btn, .devices .dev .acts .icon-btn:focus-visible { opacity: 1; }
  }
  .devices .dev.picked { background: var(--accent-soft); }
  .dev-detail .labels { display: flex; flex-wrap: wrap; gap: 4px; }
  .panel[data-view="devices"] .tg-only, .panel[data-view="senders"] .tg-only, .panel[data-view="senders"] .list-only,
  .panel[data-view="takeover"] .tg-only, .panel[data-view="takeover"] .list-only,
  .panel[data-view="installation"] .tg-only, .panel[data-view="installation"] .list-only { display: none !important; }
  .panel:not([data-view="devices"]) .devices, .panel:not([data-isub="manage"]) .poolbox,
  .panel:not([data-view="takeover"]) .takeover, .panel:not([data-view="installation"]) .installation { display: none; }
  /* the pool at a glance: four tiles, one bar, a note when something waits, then the map */
  .senders .pnote { margin: 14px 16px 0; display: flex; align-items: center; gap: 10px; flex-wrap: wrap; padding: 10px 14px; border-radius: 12px; font-size: calc(13px * var(--fs));
    background: color-mix(in srgb, var(--warn) 14%, var(--surface)); border: 1px solid color-mix(in srgb, var(--warn) 35%, transparent); color: var(--warn); }
  .senders .pnote button { margin-left: auto; font-weight: 500; text-decoration: underline; color: var(--warn); }
  .senders .pread { margin: 0 16px 12px; min-height: 36px; display: flex; align-items: center; gap: 4px 12px; flex-wrap: wrap; padding: 6px 12px; border-radius: 12px;
    background: var(--soft); font-size: calc(13px * var(--fs)); color: var(--muted); }
  .senders .pread b { color: var(--text); font-weight: 500; }
  /* the pool map: the full width, 32 to a row (16 on phones), each row labelled with its first
     ID's last byte; details in the tooltip */
  .senders .map { display: grid; grid-template-columns: 56px repeat(32, minmax(0, 1fr)); gap: 3px; align-items: center; padding: 16px 16px 8px; }
  .senders .map button { all: unset; box-sizing: border-box; height: 18px; border-radius: 3px; border: 1px solid var(--line); cursor: default; }
  .senders .map .row-id { font: calc(11px * var(--fs))/1 var(--code-font-family, ui-monospace, monospace); color: var(--muted); }
  .senders .map .row-id.half { display: none; }
  .senders .map .row-id .lh { display: none; }
  .senders .map button.sel { outline: 2px solid var(--text); outline-offset: 1px; }
  .senders .map button[data-goto]:hover { transform: scale(1.25); }
  .senders .mapscope { margin: -6px 16px 12px; font-size: calc(12px * var(--fs)); color: var(--muted); }
  .senders .legend { display: flex; flex-wrap: wrap; gap: 4px 16px; padding: 0 16px 14px; font-size: calc(12px * var(--fs)); color: var(--muted); }
  .senders .legend span { display: inline-flex; align-items: center; gap: 6px; }
  .senders .legend i { width: 10px; height: 10px; border-radius: 2px; border: 1px solid var(--line); }
  .senders .legend .t-assigned { background: var(--accent); border-color: var(--accent); }
  .senders .legend .t-blocked { background: var(--warn); border-color: var(--warn); }
  .senders .legend .t-unavailable { background: repeating-linear-gradient(45deg, var(--line) 0 2px, transparent 2px 4px); }
  @media (max-width: 760px) {
    .senders .map { grid-template-columns: 44px repeat(16, minmax(0, 1fr)); }
    .senders .map .row-id.half { display: block; }
    .senders .map .row-id .lf { display: none; }
    .senders .map .row-id .lh { display: inline; }
  }
  .senders .map button[data-goto] { cursor: pointer; }
  .senders .map button:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
  .senders .map .t-assigned { background: var(--accent); border-color: var(--accent); }
  .senders .map .t-blocked { background: var(--warn); border-color: var(--warn); }
  .senders .map .t-unavailable { background: repeating-linear-gradient(45deg, var(--line) 0 2px, transparent 2px 4px); }
  .senders .confirm { margin: 10px 16px 0; padding: 12px 14px; border-radius: 8px; border: 1px solid var(--line); background: var(--surface); }
  .senders .confirm b { display: block; font-weight: 500; margin-bottom: 4px; }
  .senders .confirm p { margin: 0 0 12px; font-size: calc(13px * var(--fs)); color: var(--muted); }
  .senders .confirm .buttons { display: flex; justify-content: flex-end; gap: 8px; }
  .senders .pick { padding: 12px 16px 0; }
  /* one grid for all senders (subgrid): names, values and numbers line up in columns */
  .panel:not([data-view="devices"]) .dev-only { display: none !important; }
  .devices { display: grid; grid-template-columns: 28px minmax(220px, 1.8fr) minmax(130px, 1fr) minmax(0, 1.5fr) minmax(150px, auto) 96px; column-gap: 16px; }
  .devices > .empty { grid-column: 1 / -1; }
  .devices .dev-head, .devices .dev { grid-column: 1 / -1; display: grid; grid-template-columns: subgrid; gap: 4px 16px; align-items: center; padding: 12px 16px; }
  .devices .dev-head { padding-top: 8px; padding-bottom: 8px; font-size: calc(11px * var(--fs)); font-weight: 500; color: var(--muted); text-transform: uppercase; letter-spacing: .04em;
    background: var(--soft); border-top: 1px solid var(--line); }
  .devices .dev-head button { all: unset; box-sizing: border-box; display: inline-flex; align-items: center; gap: 4px; cursor: pointer; border-radius: 4px; }
  .devices .dev-head button:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  .devices .dev-head button:hover { color: var(--text); }
  .devices .dev-head button svg { width: 12px; height: 12px; opacity: 0; transition: transform .15s; }
  .devices .dev-head [aria-sort] { color: var(--text); }
  .devices .dev-head [aria-sort] svg { opacity: 1; }
  .devices .dev-head [aria-sort="ascending"] svg { transform: rotate(180deg); }
  .devices .dev { border-top: 1px solid var(--line); cursor: pointer; min-height: 64px; }
  .devices .dev .acts { display: flex; flex-wrap: wrap; justify-content: flex-end; align-items: center; gap: 2px; }
  .devices .dev .acts .icon-btn { width: 36px; height: 36px; }
  .devices .dev .acts .icon-btn svg { width: 18px; height: 18px; }
  .devices .dev .acts .chip { height: 32px; padding: 0 12px; margin-left: 4px; }
  /* "add" is the one action of an unknown sender: a round filled button, its name is the tooltip */
  .devices .dev .acts .chip.add { width: 32px; padding: 0; border-radius: 50%; background: var(--accent); border-color: var(--accent); color: var(--on-accent); }
  .devices .dev .acts .chip.add:hover:not(:disabled) { background: var(--accent-hover); border-color: var(--accent-hover); color: var(--on-accent); }
  .devices .dev .acts .chip.add .lbl { display: none; }
  .devices .dev:hover { background: color-mix(in srgb, var(--soft) 60%, transparent); }
  .devices .dev .ident { min-width: 0; display: flex; align-items: center; gap: 12px; }
  .devices .dev .idtext { min-width: 0; flex: 1; }
  /* the kind of device as a tile: the tooltip names it, the color only groups */
  .devices .tile { flex: none; width: 36px; height: 36px; border-radius: 10px; display: inline-flex; align-items: center; justify-content: center; background: var(--tag-bg); color: var(--tag-text); }
  .devices .tile svg { width: 20px; height: 20px; }
  .devices .tile.lighting, .devices .tile.meters { background: color-mix(in srgb, var(--warn) 22%, transparent); color: var(--text); }
  .devices .tile.covers { background: var(--accent-soft); color: var(--accent); }
  .devices .tile.climate { background: color-mix(in srgb, var(--bad) 18%, transparent); color: var(--bad); }
  .devices .tile.sensors { background: color-mix(in srgb, var(--ok) 18%, transparent); color: var(--ok); }
  .devices .tile.unknown { background: none; border: 1px dashed var(--line); color: var(--muted); }
  /* type over area in one cell: the area is the second line, not a column of its own */
  .devices .dev .c-area { display: grid; min-width: 0; font-size: calc(13px * var(--fs)); overflow-wrap: anywhere; }
  .devices .dev .c-area .sub svg { width: 12px; height: 12px; vertical-align: -1px; margin-right: 3px; }
  .devices .dgroup { grid-column: 1 / -1; display: flex; gap: 10px; align-items: baseline; padding: 9px 16px; background: var(--soft); border-top: 1px solid var(--line); cursor: pointer; font-size: calc(13px * var(--fs)); }
  .devices .dgroup:focus-visible { outline: 2px solid var(--accent); outline-offset: -2px; }
  .devices .dgroup .chev { align-self: center; width: 14px; height: 14px; color: var(--muted); transition: transform .15s; }
  .devices .dgroup[aria-expanded="false"] .chev { transform: rotate(-90deg); }
  .devices .dgroup .sub { color: var(--muted); font-size: calc(12px * var(--fs)); }
  .devices .dgroup .attn { color: var(--warn); }
  .devices .dgroup b { white-space: nowrap; }
  .devices .dgroup { flex-wrap: wrap; }
  .devices .dev-head .h-heard { text-align: right; }
  .devices .dev .none { color: var(--muted); }
  .devices .dev .msub { display: none; }
  .devices .dev.quiet:not(.expandable) { cursor: default; }
  .devices .dev .expand .chev { transition: transform .15s; }
  .devices .dev.open { background: color-mix(in srgb, var(--soft) 60%, transparent); }
  .devices .dev.open .expand .chev { transform: rotate(180deg); }
  .devices .dev-detail { grid-column: 1 / -1; cursor: default; padding: 4px 4px 8px; display: flex; flex-direction: column; gap: 12px; min-width: 0; }
  .dev-detail .acts-row { margin-top: 8px; }
  input.note[aria-invalid="true"] { border-color: var(--warn); }
  input.note { width: 100%; box-sizing: border-box; font: inherit; font-size: calc(13px * var(--fs)); padding: 6px 10px; border: 1px solid var(--line); border-radius: 8px; background: transparent; color: inherit; }
  .dev-detail .dsec h4 { margin: 0 0 8px; font-size: calc(13px * var(--fs)); font-weight: 600; color: var(--text); display: flex; gap: 8px; align-items: center; }
  .dev-detail .dsec h4::before { content: ""; flex: none; width: 3px; height: 13px; border-radius: 2px; background: var(--accent); }
  .dev-detail .dsec h4 .sub { font-weight: 400; }
  /* values as small tiles, like the Device Proxy's statistics */
  /* one card grid for every section: the cards of a row are alike in height, wide content takes two columns */
  .dev-detail .dgrid { display: grid; grid-auto-flow: dense; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); margin: 0; background: var(--surface); border: 1px solid var(--line-2); border-radius: 12px; overflow: hidden; }
  .dev-detail .dgrid > div { padding: 11px 16px 12px; min-width: 0; display: grid; grid-template-rows: auto 1fr; gap: 3px; box-shadow: 1px 0 0 var(--line-2), 0 1px 0 var(--line-2); }
  .dev-detail .dgrid > div.wide { grid-column: span 2; }
  .dev-detail .dgrid > div.full { grid-column: 1 / -1; }
  .dev-detail .tg { display: flex; flex-wrap: wrap; align-items: center; gap: 4px 14px; }
  .dev-detail .tg .raw { margin-top: 0; }
  .dev-detail .dgrid dt { font-size: calc(12px * var(--fs)); font-weight: 500; color: var(--muted); }
  .dev-detail .dgrid dd { margin: 0; overflow-wrap: anywhere; align-self: start; }
  .dev-detail .raw { display: flex; flex-wrap: wrap; gap: 4px 6px; align-items: center; margin-top: 2px; }
  .dev-detail .tag.mono, .dev-detail .raw .tag { font-family: ui-monospace, monospace; white-space: nowrap; }
  /* one row component for values, senders, settings and entities: inner space and fixed columns */
  .dev-detail .rows { display: grid; grid-template-columns: minmax(150px, 1.2fr) minmax(140px, 1fr) auto; column-gap: 16px; background: var(--surface); border: 1px solid var(--line-2); border-radius: 12px; overflow: hidden; }
  .dev-detail .rows > * { grid-column: 1 / -1; }
  .dev-detail .rows .li { display: grid; grid-template-columns: subgrid; gap: 4px 16px; align-items: center; padding: 9px 14px; border-top: 1px solid var(--line-2); font-size: calc(13px * var(--fs)); }
  .dev-detail .rows .li:first-child { border-top: 0; }
  .dev-detail .rows .li > :last-child { justify-self: end; text-align: right; }
  .dev-detail .rows .li > * { min-width: 0; overflow-wrap: anywhere; }
  .dev-detail .rows .li .k { color: var(--muted); }
  .dev-detail .rows .li b { font-weight: 500; }
  .dev-detail .rows .li.value b { font-size: calc(15px * var(--fs)); }
  .dev-detail .rows .foot { display: flex; flex-wrap: wrap; gap: 6px 8px; align-items: center; padding: 8px 14px; border-top: 1px solid var(--line-2); background: var(--soft); }
  .dev-detail .rows .foot .acts-row { margin: 0; }
  @media (max-width: 760px) {
    .dev-detail .dgrid { grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); }
    .dev-detail .dgrid > div.wide, .dev-detail .dgrid > div.full { grid-column: 1 / -1; }
    .dev-detail .rows { grid-template-columns: minmax(0, 1fr) auto; }
    .dev-detail .rows .li > :nth-child(2) { grid-column: 1 / -1; grid-row: 2; }
  }
  .dev-detail .dtbl, .dev-detail .vbox { background: var(--surface); border: 1px solid var(--line-2); border-radius: 12px; padding: 4px 12px; }
  .dev-detail .vbox { padding: 10px 12px; display: flex; flex-direction: column; gap: 4px; }
  .dev-detail .dtbl { width: 100%; border-collapse: collapse; font-size: calc(13px * var(--fs)); }
  .dev-detail .dtbl td { padding: 8px 12px 8px 0; border-top: 1px solid var(--line-2); overflow-wrap: anywhere; vertical-align: top; }
  .dev-detail .dtbl tr:first-child td { border-top: 0; }
  .dev-detail .values { display: flex; flex-wrap: wrap; gap: 4px 14px; }
  .dev-detail .dact { display: flex; flex-wrap: wrap; gap: 8px; }
  .dev-detail .mini { height: 32px; max-width: 100%; min-width: 0; width: 100%; box-sizing: border-box; }
  .dev-detail input.mini { margin-top: 4px; width: 100%; border: 1px solid var(--input-line); border-radius: 8px; padding: 0 10px; background: var(--surface); color: var(--text); font: inherit; }
  .devices .dev.quiet .name { color: var(--muted); }
  .spark { display: block; flex: none; width: 96px; height: 32px; }
  .spark .weak { stroke: var(--line); stroke-dasharray: 2 2; }
  .spark.ok { color: var(--ok); } .spark.warn { color: var(--warn); } .spark.bad { color: var(--bad); }
  .spark circle { fill: currentColor; }
  .spark polyline { fill: none; stroke: currentColor; stroke-width: 2; stroke-linejoin: round; stroke-linecap: round; }
  .devices .dev .sub { color: var(--muted); font-size: calc(12px * var(--fs)); overflow-wrap: anywhere; }
  .devices .dev .stats { display: flex; flex-direction: column; align-items: flex-end; gap: 2px; font-size: calc(12px * var(--fs)); color: var(--muted); white-space: nowrap; min-width: 0; }
  /* last heard in two lines: when, signal and dBm; then the telegrams with their trend */
  .devices .dev .stats .l1 { display: inline-flex; align-items: center; gap: 8px; font-size: calc(13px * var(--fs)); color: var(--text); }
  /* the name in one line; the whole name is its tooltip */
  .devices .dev .line1 .name { display: block; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  /* long hints ("could be A5-02-05, A5-10-06") wrap inside their column instead of running into the next */
  .values .maybe { flex: 1 0 100%; min-width: 0; }
  .values .tag { flex: 0 1 auto; min-width: 0; white-space: normal; overflow-wrap: break-word; }
  /* the state of a device: the text always names it, the color only backs it up */
  .chip .n { margin-left: 6px; font-weight: 500; font-variant-numeric: tabular-nums; opacity: .75; }
  .devices .pill { flex: none; display: inline-flex; align-items: center; gap: 6px; font-size: calc(12px * var(--fs)); font-weight: 500; padding: 2px 10px; border-radius: 12px; white-space: nowrap; background: var(--tag-bg); color: var(--tag-text); }
  .devices .pill::before { content: ""; width: 7px; height: 7px; border-radius: 50%; background: currentColor; }
  .devices .pill.active { background: color-mix(in srgb, var(--ok) 18%, transparent); color: var(--ok); }
  .devices .pill.silent { background: color-mix(in srgb, var(--warn) 22%, transparent); color: var(--text); }
  .devices .pill.silent::before { background: var(--warn); }
  .devices .pill.unknown { background: var(--accent-soft); color: var(--accent); }
  @media (max-width: 760px) {
    .devices { grid-template-columns: 28px minmax(0, 1fr) auto; }
    .devices .dev-head { display: none; }
    .devices .c-sel { grid-column: 1; grid-row: 1 / span 2; align-items: flex-start; padding-top: 4px; }
    .selall:not([hidden]) { display: inline-flex; }
    .devices .dev { grid-template-columns: subgrid; }
    .devices .dev .c-area { display: none; }
    .devices .dev .msub { display: block; }
    .devices .dev .ident { gap: 10px; }
    .devices .tile { width: 30px; height: 30px; border-radius: 8px; }
    .devices .tile svg { width: 17px; height: 17px; }
    .devices .dev .sub { overflow-wrap: break-word; }
    .devices .dev .stats .tag { display: none; }
    .devices .dev .values { min-width: 0; flex-wrap: wrap; }
    .devices .dev .values { grid-column: 2; grid-row: 2; }
    .devices .dev .acts { grid-column: 3; grid-row: 2; flex-wrap: nowrap; }
    .devices .dev .acts .chip { width: 32px; padding: 0; }
    .devices .dev .acts .lbl { display: none; }
  }

  .pager { display: flex; flex-wrap: wrap; align-items: center; justify-content: flex-end; gap: 6px 12px;
    padding: 8px 8px 8px 16px; border-top: 1px solid var(--line); font-size: calc(13px * var(--fs)); color: var(--muted); }
  .pager label { display: inline-flex; align-items: center; gap: 8px; white-space: nowrap; }
  .pager .range { min-width: 110px; text-align: right; white-space: nowrap; }
  .pager .nav { display: inline-flex; }
  .pager .icon-btn { width: 36px; height: 36px; }
  .pager .icon-btn:disabled { opacity: .35; cursor: default; background: none; color: var(--muted); }
  .pager[hidden] { display: none; }
  .pager .newer { margin-right: auto; }
  .pager .newer[hidden] { display: none; }
  .meta .chip { height: 26px; font-size: calc(12px * var(--fs)); }
  .meta .chip[hidden] { display: none; }

  /* empty states: an icon in a soft circle, a title, one sentence and the action that helps */
  .empty { display: grid; justify-items: center; gap: 6px; padding: 48px 16px; text-align: center; color: var(--muted); }
  .empty .ico { display: grid; place-items: center; width: 64px; height: 64px; margin-bottom: 6px; border-radius: 50%;
    color: var(--accent); background: var(--accent-soft); }
  .empty .ico svg { width: 30px; height: 30px; }
  .senders .empty { padding: 24px 16px; }
  .empty b { color: var(--text); font-weight: 500; font-size: calc(16px * var(--fs)); }
  .empty span { max-width: 420px; }
  .empty .chip { margin-top: 8px; }
  .empty.small { padding: 28px 16px; }
  .empty.small .ico { width: 48px; height: 48px; }
  .empty.small .ico svg { width: 24px; height: 24px; }

  @media (max-width: 760px) {
    main { padding: 16px 16px 32px; }
    .header { padding: 0 16px; }
    /* the link moves up to the logo's line, the tabs keep their own */
    .header-end { display: contents; }
    .brand { order: -2; }
    .look { order: -1; margin-left: auto; }
    .integration-link { order: -1; padding: 0 10px; }
    .integration-link span { display: none; }
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
    tr.row > td { display: block; padding: 0; border: 0; background: none !important; box-shadow: none !important; }
    tr.row.noans { box-shadow: inset 3px 0 0 var(--warn); }
    tr.row:hover, tr.row.open { background: color-mix(in srgb, var(--soft) 60%, transparent); }
    tr.row.fresh { animation: fresh 1.2s ease-out; }
    tr.row > td.time { grid-area: time; font-size: calc(12px * var(--fs)); text-align: right; }
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
    .menu .dup { display: flex; }
    /* the bar stays on one line: title, badge and at most three buttons */
    .bar { flex-wrap: nowrap; gap: 6px; padding-right: 6px; }
    .bar h2 { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .bar .live { flex: none; }
    .mini { gap: 4px; }
    .mini .mini-text { display: none; }
    .bar .icon-btn { width: 38px; height: 38px; flex: none; }
    select.m-only { display: block; }
    .time small { display: none; }
    .pager { justify-content: space-between; gap: 4px; padding: 8px; }
    .pager .range { min-width: 0; margin-left: auto; }
    .pager .icon-btn { width: 34px; height: 34px; }
    .pager label span { display: none; }
    .filters .search { flex-basis: 100%; }
    /* the view switch gets a line of its own and scrolls instead of cutting off a view */
    #view { flex-basis: calc(100% + 32px); margin: 0 -16px; padding: 0 8px; flex-wrap: nowrap; overflow-x: auto; scrollbar-width: none; }
    #view::-webkit-scrollbar { display: none; }
    #view button { flex: 1 0 auto; justify-content: center; padding: 0 8px; }
    /* tabs beyond the edge fade out there: a sign that the row scrolls */
    #view.fade-end { mask-image: linear-gradient(to right, #000 calc(100% - 40px), transparent); }
    #view.fade-start { mask-image: linear-gradient(to left, #000 calc(100% - 40px), transparent); }
    #view.fade-start.fade-end { mask-image: linear-gradient(to right, transparent, #000 40px, #000 calc(100% - 40px), transparent); }
    .filters .chip { padding: 0 12px; font-size: calc(12px * var(--fs)); }
    .filters #tkReport { padding: 0 8px; }
    /* the status chips scroll in one line, sorting and grouping share a row: the list starts higher */
    .filters .select { flex: 1 1 0; min-width: 0; }
    .filters .select { padding-right: 24px; background-position: calc(100% - 12px) 55%, calc(100% - 7px) 55%; }
    .filters #tkReport .lbl { display: none; }
    .who .line1 { flex-wrap: wrap; row-gap: 4px; }
    .who .name { flex: 1 1 100%; }
  }
  @media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation: none !important; transition: none !important; } }
`;

// the profile candidates of an unknown sender: the first two, the rest as "+n" (all in the tooltip)
const MAYBE_SHOWN = 2;
function maybeTag(t, candidates, label = t.maybe, hint = t.maybeHint) {
  if (!candidates?.length) return "";
  const shown = candidates.slice(0, MAYBE_SHOWN).join(", ");
  const more = candidates.length > MAYBE_SHOWN ? ` +${candidates.length - MAYBE_SHOWN}` : "";
  return `<div class="maybe"><span class="tag" title="${esc(`${hint}: ${candidates.join(", ")}`)}">${esc(label)} ${esc(shown)}${more}</span></div>`;
}

function bars(dbm) {
  if (dbm == null) return "";
  dbm = Number(dbm);
  const level = dbm >= -70 ? 4 : dbm >= -80 ? 3 : dbm >= -90 ? 2 : 1;
  const rects = [0, 1, 2, 3]
    .map((i) => `<rect x="${i * 5}" y="${10 - i * 3}" width="3" height="${4 + i * 3}" rx="1" class="${i < level ? "on" : ""}"></rect>`)
    .join("");
  const tone = level >= 3 ? "ok" : level === 2 ? "warn" : "bad"; // colour follows the bars
  return `<svg class="bars ${tone}" viewBox="0 0 18 14" role="img" aria-label="${dbm} dBm"><title>${dbm} dBm</title>${rects}</svg>`;
}

// buttons that keep the keyboard focus when their row or card is drawn again
const FOCUSABLE = [".rowmore", "[data-sel]", ".expand", "[data-copy]", "[data-only]", "[data-hide]", ".add", "[data-free]", "[data-teach]", "[data-device-page]", "[data-resend]", '[data-gateway-action="filter"]', '[data-gateway-action="details"]'];

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
  kind: (a, b) => collator.compare(a.category || "\uffff", b.category || "\uffff") || collator.compare(a.area || "\uffff", b.area || "\uffff") || byName(a, b),
  entities: (a, b) => (a.entities ?? -1) - (b.entities ?? -1) || byName(a, b),
  heard: (a, b) => (a.time ?? -1) - (b.time ?? -1) || byName(a, b),
  signal: (a, b) => (a.dbm ?? 0) - (b.dbm ?? 0) || byName(a, b), // no signal (bus): as the strongest
  busy: (a, b) => a.count - b.count || byName(a, b),
};
const DEV_DESC_FIRST = new Set(["entities", "heard", "busy"]); // first click: most, newest
// ICON is bound after the parts have loaded, so the table is built when it is first needed
const categoryIcon = (category) => ({ lighting: ICON.bulb, covers: ICON.slats, climate: ICON.thermometer, buttons: ICON.button, sensors: ICON.thermometer, meters: ICON.flash, virtual: ICON.cloud })[category];
const DEV_STATUS = ["", "known", "unknown", "silent", "unheard", "weak"];
const DEV_GROUPS = ["", "area", "kind"];
const GROUP_KEY = "enocean_eltako_dev_group";

const NO_FILTER = { gateway: "", text: "", dir: "", type: "", repeats: false, unknown: false, devStatus: "", area: "" };

const VIEWS = ["telegrams", "devices", "senders", "installation", "takeover"];

function loadView() {
  const fallback = { view: "telegrams", pageSize: 50, sort: { key: "time", desc: true }, devSort: { key: "name", desc: false }, filter: { ...NO_FILTER } };
  try {
    const view = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
    const saved = view.filter || {};
    const text = (v) => (typeof v === "string" ? v : "");
    return {
      view: VIEWS.includes(view.view) ? view.view : "telegrams",
      pageSize: PAGE_SIZES.includes(view.pageSize) ? view.pageSize : 50,
      sort: SORTERS[view.sort?.key] ? { key: view.sort.key, desc: !!view.sort.desc } : fallback.sort,
      devSort: fallback.devSort, // not kept: the device list always opens by name
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

// what a panel leaves behind when Home Assistant takes it off the page: the next one starts from it
// and refreshes in the background, so leaving and coming back does not show empty lists. Kept in
// the page only; a reload starts empty, as telegrams are not for the browser's storage.
const KEPT = {};

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
    this._tk = null; // set once the parts are loaded
    this._pools = [];
    this._pool = ""; // shown pool
    this._poolSel = ""; // the square chosen on the pool map (its ID)
    this._freeing = null; // blocked sender ID waiting for its confirmation
    this._sidBlocked = []; // the blocked IDs of the pool: what Free all frees
    const view = loadView();
    this._savedView = view.view; // shown once the gateways and the Takeover check are in
    this._filter = view.filter;
    this._sort = view.sort;
    this._devSort = view.devSort;
    try {
      const saved = localStorage.getItem(GROUP_KEY);
      this._devGroup = DEV_GROUPS.includes(saved) ? saved : "area"; // grouped by area unless chosen otherwise
    } catch (err) {
      this._devGroup = "area";
    }
    this._devCollapsed = new Set(); // groups folded in this session
    this._pageSize = view.pageSize;
    this._offset = 0; // first row of the page within the sorted, filtered rows
    this._pageFirst = null; // that row: new rows sorting before it keep the page in place
    this._newAbove = 0;
    this._multi = false; // more than one gateway: gateway column and filter
    this._gateways = [];
    this._expanded = new Set();
    this._devOpen = new Set(); // devices view: opened rows (device keys)
    this._sel = new Set(); // devices view: ticked rows (device keys)
    this._pick = null; // the open form of the selection: "area", "labels" or "remove"
    this._areas = [];
    this._labels = [];
    this._devDetails = new Map(); // device key -> what the server knows of it
    this._recordings = new Map(); // sender -> {start} while recording, {start, rows} when done
    this._senderTests = new Map(); // device key -> {running} | {results: {profile: result}} | {error}
    this._devOrder = null; // order kept while a row is open, so it does not move away
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
    // a link into the open panel (same page, new query) applies its view and filters
    this._onLocation = () => {
      if (this._restored) this._applyUrl();
    };
    // a click anywhere outside the "more" menu closes it
    this._onPointer = (e) => {
      const look = this.shadowRoot.querySelector(".look");
      if (look && !e.composedPath().includes(look) && !this.shadowRoot.getElementById("lookMenu").hidden) this._toggleLook(false);
      if (!e.composedPath().some((el) => el.classList?.contains("addmenu") || el.classList?.contains("add") || el.classList?.contains("rowmore"))) this._closeAddMenu();
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
    if (!this._ready) {
      this._waiting = hass;
      if (!this._loading) this._loading = this._loadParts();
      return;
    }
    const first = !this._hass;
    this._hass = hass;
    if (first) {
      try {
        this._look = cleanPrefs(JSON.parse(localStorage.getItem(LOOK_KEY)));
      } catch {
        this._look = { ...DEFAULTS };
      }
    }
    this._applyLook();
    if (first) {
      this._t = TEXT[(hass.language || "en").startsWith("de") ? "de" : "en"];
      this._build();
      this._loadLook();
    }
    if (this._menu) this._menu.hass = hass;
    if (this.isConnected) this._watchConnection();
    if (this.isConnected && !this._unsub) this._subscribe();
  }

  // the palette is set again only when the choice or Home Assistant's mode changed
  _applyLook() {
    const dark = this._hass?.themes?.darkMode;
    const key = `${this._look.scheme}|${this._look.mode}|${this._look.size}|${dark}`;
    if (key === this._lookKey) return;
    this._lookKey = key;
    applyAppearance(this, this._look, dark);
  }

  // the choice of this Home Assistant user wins over the browser's cache
  async _loadLook() {
    try {
      const { value } = await this._hass.callWS({ type: "frontend/get_user_data", key: LOOK_KEY });
      if (!value) return;
      this._look = cleanPrefs(value);
      localStorage.setItem(LOOK_KEY, JSON.stringify(this._look));
      this._applyLook();
      this._renderLookMenu();
    } catch {
      // no user data (older Home Assistant): the browser's cache stays
    }
  }

  _setLook(patch) {
    this._look = cleanPrefs({ ...this._look, ...patch });
    try {
      localStorage.setItem(LOOK_KEY, JSON.stringify(this._look));
    } catch {
      // storage blocked: the choice holds until the page is closed
    }
    this._hass.callWS({ type: "frontend/set_user_data", key: LOOK_KEY, value: this._look }).catch(() => {});
    this._applyLook();
    this._renderLookMenu();
  }

  _renderLookMenu() {
    const t = this._t.look;
    const dark = this.hasAttribute("dark");
    const group = (kind, label, options) => `<div class="lookgroup" role="radiogroup" aria-label="${esc(label)}"><span class="lookhead">${esc(label)}</span>${options
      .map(([value, text, dot]) => `<button role="radio" aria-checked="${this._look[kind] === value}" data-look="${kind}" data-value="${esc(value)}">${dot ? `<i class="dot" style="background:${dot}"></i>` : ""}${esc(text)}</button>`)
      .join("")}</div>`;
    const accent = (name) => tokens({ ...this._look, scheme: name }, dark)["--accent"];
    this.shadowRoot.getElementById("lookMenu").innerHTML =
      group("scheme", t.scheme, Object.keys(SCHEMES).map((name) => [name, t.schemes[name], accent(name)])) +
      group("mode", t.mode, MODES.map((name) => [name, t.modes[name]])) +
      group("size", t.size, Object.keys(SIZES).map((name) => [name, t.sizes[name]]));
  }

  _toggleLook(open = this.shadowRoot.getElementById("lookMenu").hidden) {
    const $ = (id) => this.shadowRoot.getElementById(id);
    if (open) this._renderLookMenu();
    $("lookMenu").hidden = !open;
    $("lookBtn").setAttribute("aria-expanded", String(open));
  }

  async _loadParts() {
    try {
      partsLoaded ||= loadParts().catch((err) => {
        partsLoaded = null; // the next opening tries again
        throw err;
      });
      await partsLoaded;
    } catch (err) {
      console.error("enocean_eltako: panel parts failed to load", err);
      this._loading = null;
      const de = (this._waiting?.language || navigator.language || "en").startsWith("de");
      this.shadowRoot.innerHTML = `<div style="padding:24px;font-family:sans-serif">
        <p>${de ? "Das EnOcean-Panel konnte nicht geladen werden." : "The EnOcean panel could not be loaded."}</p>
        <button id="reload">${de ? "Neu laden" : "Reload"}</button></div>`;
      this.shadowRoot.getElementById("reload").onclick = () => location.reload();
      return;
    }
    Object.assign(EnOceanEltakoPanel.prototype, takeover); // the Takeover view (takeover.js) adds its methods
    Object.assign(EnOceanEltakoPanel.prototype, installation); // the Installation view (installation.js)
    this._tk = takeoverState();
    this._in = installationState();
    this._restoreKept(this._waiting?.connection);
    this._ready = true;
    this._loading = null;
    this.hass = this._waiting;
    this._waiting = null;
  }

  _restoreKept(connection) {
    if (!KEPT.rows || KEPT.connection !== connection) return; // another Home Assistant connection: nothing of it
    this._rows = KEPT.rows;
    this._keys = KEPT.keys;
    this._cleared = KEPT.cleared;
    this._gateways = KEPT.gateways;
    this._skew = KEPT.skew;
    this._pools = KEPT.pools;
    this._pool = KEPT.pool;
    this._devDetails = KEPT.devDetails;
    this._areas = KEPT.areas;
    this._labels = KEPT.labels;
    this._multi = KEPT.multi;
    this._in.doc = KEPT.doc;
    this._initialised = true; // the rows are not new: no highlight for them
  }

  _keepForNext() {
    if (!this._ready || (!this._rows.length && !this._gateways.length)) return;
    Object.assign(KEPT, {
      connection: this._hass?.connection,
      rows: this._rows,
      keys: this._keys,
      cleared: this._cleared,
      gateways: this._gateways,
      skew: this._skew,
      pools: this._pools,
      pool: this._pool,
      devDetails: this._devDetails,
      areas: this._areas,
      labels: this._labels,
      multi: this._multi,
      doc: this._in.doc,
    });
  }

  _lastTelegram(l, now) {
    // the last telegram of a sender as stored: when, what kind, the bytes and what they say; it survives a restart
    const t = this._t;
    const bytes = l.data.match(/../g)?.join(" ") ?? "";
    const head = `${esc(t.ago(Math.max(0, Math.round(now / 1000 - l.time))))} · ${esc(RORG[l.rorg] || l.rorg)}${l.dbm != null ? ` · ${esc(l.dbm)} dBm` : ""}`;
    // when and what kind, and the bytes and the status byte as tags that never break; what they say is under Last values
    return `<div class="tg"><span>${head}</span><span class="raw"><span class="tag mono">${esc(bytes)}</span><span class="tag mono">${esc(t.status)} ${esc(l.status.toString(16).toUpperCase().padStart(2, "0"))}</span></span></div>`;
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
    // screen readers hear a lost stream and its return, not the first connection on opening
    if (state !== this._link && this._t) {
      if (state === "offline") this._announce(this._t.offline);
      else if (state === "live" && this._lost) this._announce(this._t.live);
      this._lost = state === "offline" || (this._lost && state !== "live");
    }
    this._link = state;
    this._renderBar();
  }

  _announce(text) {
    // one live region that is always there (a hidden notice would not be read out when shown)
    const region = this.shadowRoot.getElementById("announce");
    if (region) region.textContent = text;
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
    window.addEventListener("location-changed", this._onLocation);
    if (this._hass) this._watchConnection();
    if (this._hass && !this._unsub) this._subscribe();
  }

  disconnectedCallback() {
    window.removeEventListener("keydown", this._onKey);
    document.removeEventListener("selectionchange", this._onSelection);
    document.removeEventListener("visibilitychange", this._onVisible);
    document.removeEventListener("pointerdown", this._onPointer);
    window.removeEventListener("location-changed", this._onLocation);
    this._keepForNext();
    clearInterval(this._timer);
    this._timer = null;
    clearTimeout(this._tkTyping);
    clearTimeout(this._noticeTimer);
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
      <style>${STYLE}${TAKEOVER_STYLE}${INSTALLATION_STYLE}</style>
      <header class="header">
        <div class="brand"><ha-menu-button></ha-menu-button>${LOGO}<div><b>${esc(t.title)}</b></div></div>
        <div class="header-end">
        <nav role="tablist" id="view" aria-label="${esc(t.title)}">
          <button role="tab" data-view="telegrams" aria-controls="panel" aria-selected="true">${esc(t.viewTelegrams)}</button>
          <button role="tab" data-view="devices" aria-controls="panel" aria-selected="false" tabindex="-1">${esc(t.viewDevices)}</button>
          <button role="tab" data-view="installation" aria-controls="panel" aria-selected="false" tabindex="-1">${esc(t.viewInstallation)}</button>
          <button role="tab" data-view="takeover" aria-controls="panel" aria-selected="false" tabindex="-1" hidden>${esc(t.viewTakeover)}</button>
        </nav>
        <span class="more look">
          <button class="icon-btn" id="lookBtn" title="${esc(t.look.title)}" aria-label="${esc(t.look.title)}" aria-haspopup="true" aria-expanded="false" aria-controls="lookMenu">${svg(ICON.palette)}</button>
          <div class="menu look-menu" id="lookMenu" aria-label="${esc(t.look.title)}" hidden></div>
        </span>
        <button class="chip integration-link" data-open-integration title="${esc(t.integration)}" aria-label="${esc(t.integration)}">${svg(ICON.open)}<span>${esc(t.integration)}</span></button>
        </div>
      </header>
      <main>
        <section id="gatewaySection" aria-label="${esc(t.gateways)}">
          <div class="cards" id="cards"></div>
        </section>
        <section class="panel" id="panel" role="tabpanel" data-view="telegrams" aria-label="${esc(t.telegrams)}">
          <div class="bar">
            <h2 id="viewTitle">${esc(t.telegrams)}</h2>
            <span class="live list-only" id="live"><i></i><span></span></span>
            <button class="mini" id="mini" hidden></button>
            <span class="sr-only" id="announce" role="status" aria-live="polite"></span>
            <span class="spacer"></span>
            <button class="icon-btn list-only" id="pause"></button>
            <button class="icon-btn tg-only" id="send" title="${esc(t.send)}" aria-label="${esc(t.send)}" aria-expanded="false">${svg(ICON.send)}</button>
            <button class="icon-btn list-only d-only" id="export" title="${esc(t.export)}" aria-label="${esc(t.export)}">${svg(ICON.download)}</button>
            <button class="icon-btn tg-only d-only" id="clear" title="${esc(t.clear)}" aria-label="${esc(t.clear)}">${svg(ICON.clear)}</button>
            <span class="more m-only list-only">
              <button class="icon-btn" id="more" title="${esc(t.more)}" aria-label="${esc(t.more)}" aria-haspopup="menu" aria-expanded="false" aria-controls="moreMenu">${svg(ICON.more)}</button>
              <span class="menu" id="moreMenu" role="menu" hidden>
                <button role="menuitem" class="dup" data-act="export">${svg(ICON.download)}<span id="moreExport">${esc(t.exportShort)}</span></button>
                <button role="menuitem" class="tg-only" data-act="clear">${svg(ICON.clear)}${esc(t.clear)}</button>
                <button role="menuitem" class="dev-only" data-act="doc-print">${svg(ICON.print)}${esc(t.doc.print)}</button>
                <button role="menuitem" class="dev-only" data-act="doc-csv">${svg(ICON.download)}${esc(t.doc.csvItem)}</button>
                <button role="menuitem" class="dev-only" data-act="doc-csv-links">${svg(ICON.download)}${esc(t.doc.linksCsvItem)}</button>
                <button role="menuitem" class="dev-only" data-act="doc-json">${svg(ICON.download)}${esc(t.doc.jsonItem)}</button>
                <button role="menuitem" class="dev-only" data-act="doc-import">${svg(ICON.upload)}${esc(t.doc.importItem)}</button>
                <input type="file" id="docFile" accept="application/json,.json" hidden>
              </span>
            </span>
          </div>
          <div class="filters list-only">
            <div class="statusrow dev-only list-only" id="devStatus" role="group" aria-label="${esc(t.filterStatus)}">${Object.entries(t.devStatus)
              .map(([key, label]) => `<button class="chip" data-status="${key}" aria-pressed="false">${esc(label)}</button>`)
              .join("")}</div>
            <label class="search">
              ${svg(ICON.search)}
              <input id="text" type="search" placeholder="${esc(t.search)}" aria-label="${esc(t.search)}" autocomplete="off" aria-keyshortcuts="/">
              <kbd class="key" title="${esc(t.searchKey)}" aria-hidden="true">/</kbd>
              <button class="icon-btn" id="clearText" aria-label="${esc(t.clearSearch)}" title="${esc(t.clearSearch)}" hidden>${svg(ICON.close)}</button>
            </label>
            <div class="segmented tg-only" role="group" id="dir">
              <button data-dir="" aria-pressed="true">${esc(t.dirAll)}</button>
              <button data-dir="rx" aria-pressed="false">${esc(t.rx)}</button>
              <button data-dir="tx" aria-pressed="false">${esc(t.tx)}</button>
            </div>
            <button class="chip tg-only" id="unknown" aria-pressed="false">${esc(t.unknownOnly)}</button>
            <!-- the rarer filters open below the row; the set ones show as chips above the list -->
            <button class="chip" id="filterBtn" aria-expanded="false" aria-controls="filterMenu">${svg(ICON.filter)}<span>${esc(t.filters)}</span><b class="count" id="filterCount" hidden></b></button>
            <select class="select m-only tg-only" id="sortSelect" aria-label="${esc(t.sortLabel)}"></select>
            <select class="select m-only dev-only" id="devSort" aria-label="${esc(t.devSort)}" title="${esc(t.devSort)}"></select>
            <select class="select dev-only" id="devGroup" aria-label="${esc(t.devGroup)}" title="${esc(t.devGroup)}">${Object.entries(t.devGroups).map(([v, label]) => `<option value="${v}">${esc(label)}</option>`).join("")}</select>
            <button class="chip text dev-only" id="tkReport" hidden title="${esc(t.tkReportButton)}" aria-label="${esc(t.tkReportButton)}">${svg(ICON.download)}<span class="lbl">${esc(t.tkReportButton)}</span></button>
          </div>
          <div class="filtermenu list-only" id="filterMenu" role="group" aria-label="${esc(t.filters)}" hidden>
            <label class="field" id="gatewayRow" hidden><span>${esc(t.gateway)}</span><select class="select" id="gatewayFilter"></select></label>
            <label class="field tg-only"><span>${esc(t.type)}</span><select class="select" id="typeFilter"></select></label>
            <label class="field dev-only" id="devAreaRow" hidden><span>${esc(t.devCols.area)}</span><select class="select" id="devArea"></select></label>
            <label class="opt tg-only"><input type="checkbox" id="repeats"><span>${esc(t.repeats)}</span></label>
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
              <label class="check" id="sendReleaseRow" title="${esc(t.sendReleaseHint)}"><input type="checkbox" id="sendRelease" checked><span>${esc(t.sendRelease)}</span></label>
            </div>
            <div class="buttons"><button class="chip" type="button" id="sendCancel">${esc(t.sendCancel)}</button><button class="chip primary" type="submit" id="sendGo">${svg(ICON.send)}${esc(t.sendAction)}</button></div>
          </form>
          <form class="sendform dev-only" id="teachForm" hidden></form>
          <div class="notice" id="notice" hidden><span></span><button class="icon-btn" id="closeNotice" aria-label="${esc(t.closeNotice)}" title="${esc(t.closeNotice)}">${svg(ICON.close)}</button></div>
          <div class="meta list-only"><label class="selall dev-only" id="selAllRow" hidden><input type="checkbox" id="selAll"><span>${esc(t.selAll)}</span></label><span id="count"></span><span class="active" id="activeFilters"></span><button class="chip text reset" id="resetTop" hidden>${esc(t.resetFilters)}</button></div>
          <div class="selbar dev-only" id="selBar" hidden></div>
          <form class="sendform dev-only" id="pickForm" hidden></form>
          <div class="devices" id="devices"></div>
          <div class="installation" id="installation"><div id="instHead"></div>
          <details class="poolbox" id="poolBox" open><summary id="poolSummary"></summary>
          <div class="senders" id="senders">
            <div id="sidTop"></div>
            <div id="sidList"></div>
          </div>
          </details>
          <div id="instBody"></div></div>
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
    $("view").addEventListener("scroll", () => this._fadeTabs(), { passive: true });
    // the table head sticks below the bar; the bar shows the gateways once their cards are out of view
    new ResizeObserver(() => this.style.setProperty("--bar-height", `${this.shadowRoot.querySelector(".bar").offsetHeight}px`)).observe(this.shadowRoot.querySelector(".bar"));
    new IntersectionObserver(([entry]) => {
      this._cardsAway = !entry.isIntersecting && entry.boundingClientRect.top < 0; // scrolled off above
      this._renderMini();
    }).observe($("cards"));
    $("mini").addEventListener("click", () => $("gatewaySection").scrollIntoView({ behavior: "smooth", block: "start" }));
    new ResizeObserver(() => this._fadeTabs()).observe($("view"));
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
    $("takeover").addEventListener("click", (e) => this._takeoverClick(e));
    $("installation").addEventListener("click", (e) => this._installationClick(e));
    $("installation").addEventListener("focusout", (e) => this._instNameDone(e));
    // a datalist lists only what matches the typed text: clear the type while it has focus so all types show
    $("installation").addEventListener("focusin", (e) => {
      const type = e.target.closest?.('[data-bvf="type"]');
      if (!type || type.dataset.prev !== undefined) return;
      type.dataset.prev = type.value;
      type.placeholder = type.value || type.placeholder;
      type.value = "";
    });
    $("installation").addEventListener("focusout", (e) => {
      const type = e.target.closest?.('[data-bvf="type"]');
      if (!type || type.dataset.prev === undefined) return;
      if (!type.value) type.value = type.dataset.prev;
      delete type.dataset.prev;
    });
    $("installation").addEventListener("change", (e) => this._installationChange(e));
    $("installation").addEventListener("input", (e) => this._installationInput(e));
    $("installation").addEventListener("keydown", (e) => this._busKey(e)); // Esc closes the bus view's drawer
    // the empty state without a gateway and the gateway details: to the integration
    this.shadowRoot.addEventListener("click", (e) => {
      const link = e.target.closest("[data-open-integration]");
      if (!link) return;
      // from a gateway card: straight to that gateway's entry
      const entry = link.dataset.openIntegration;
      this._navigate(`/config/integrations/integration/enocean_eltako${entry ? `#config_entry=${entry}` : ""}`);
    });
    $("takeover").addEventListener("change", (e) => this._takeoverChange(e));
    $("takeover").addEventListener("input", (e) => this._takeoverInput(e));
    $("senders").addEventListener("change", (e) => {
      if (e.target.id !== "poolSelect") return;
      this._pool = e.target.value;
      this._freeing = null;
      this._renderSenderIds();
    });
    $("poolBox").addEventListener("toggle", (e) => this._poolToggled(e.target.open));
    $("selAll").addEventListener("change", (e) => this._selectAll(e.target.checked));
    $("selBar").addEventListener("click", (e) => {
      const act = e.target.closest("[data-sel-act]")?.dataset.selAct;
      if (act === "clear") this._clearSel();
      else if (act === "toggle") this._toggleDisabled();
      else if (act) this._openPick(act);
    });
    $("pickForm").addEventListener("click", (e) => {
      if (e.target.closest("[data-pick-cancel]")) this._openPick(null);
      else if (e.target.closest("[data-pick-new]")) this._createLabel();
    });
    $("pickForm").addEventListener("keydown", (e) => {
      if (e.key !== "Enter" || e.target.id !== "pickNew") return;
      e.preventDefault();
      this._createLabel();
    });
    $("pickForm").addEventListener("submit", (e) => {
      e.preventDefault();
      this._applyPick();
    });
    $("devices").addEventListener("click", (e) => {
      if (e.target.closest("[data-sel-all]")) return;
      const box = e.target.closest("[data-sel]");
      if (box) {
        this._toggleSel(box.dataset.sel, box.checked);
        return;
      }
      if (e.target.closest(".reset")) {
        this._resetFilters();
        return;
      }
      const group = e.target.closest("[data-dgroup]");
      if (group) {
        const key = group.dataset.dgroup;
        if (this._devCollapsed.has(key)) this._devCollapsed.delete(key);
        else this._devCollapsed.add(key);
        this._render();
        return;
      }
      const head = e.target.closest("[data-dsort]");
      if (head) {
        const key = head.dataset.dsort;
        this._setDevSort(key, this._devSort.key === key ? !this._devSort.desc : DEV_DESC_FIRST.has(key));
        return;
      }
      const rowMore = e.target.closest(".rowmore");
      if (rowMore) {
        this._rowMenu(rowMore);
        return;
      }
      const add = e.target.closest(".add");
      if (add) {
        this._addMenu(add);
        return;
      }
      const page = e.target.closest("[data-device-page]");
      if (page) {
        this._navigate(`/config/devices/device/${page.dataset.devicePage}`);
        return;
      }
      const teach = e.target.closest("[data-teach]");
      if (teach) {
        this._openTeach(teach.dataset.teach);
        return;
      }
      const devLinks = e.target.closest("[data-dev-links]");
      if (devLinks) {
        // the links of this device: its card in the Installation's links tab
        Object.assign(this._in, { tab: "links", linkView: "actuator", q: devLinks.dataset.devLinks, linkFilter: "all", linkSource: "all", linkPg: 0 });
        this._setView("installation");
        return;
      }
      const senderTest = e.target.closest("[data-sender-test]");
      if (senderTest) {
        this._testSenders(senderTest.dataset.senderTest, senderTest.dataset.gateway);
        return;
      }
      const only = e.target.closest("[data-only]:is(button)");
      if (only) {
        this._setText(only.dataset.only);
        this._setView("telegrams");
        return;
      }
      if (e.target.closest(".dev-detail") || this._selecting($("devices"))) return;
      const dev = e.target.closest(".dev");
      if (!dev) return;
      if (dev.dataset.dev) {
        this._toggleDev(dev.dataset.dev, dev.dataset.gateway);
        return;
      }
      if (dev.classList.contains("quiet")) return; // a device not heard has no telegrams to show
      this._setText(dev.dataset.only);
      this._setView("telegrams");
    });
    $("devices").addEventListener("change", (e) => {
      if (e.target.matches?.("[data-sel-all]")) {
        this._selectAll(e.target.checked);
        return;
      }
      const select = e.target.closest("[data-model-for]");
      if (select) {
        const input = select.parentElement.querySelector("[data-model-text]");
        if (select.value === "__other") {
          input.hidden = false;
          input.focus();
        } else {
          input.hidden = true;
          this._saveModel(select.dataset.modelFor, select.value);
        }
        return;
      }
      const text = e.target.closest("[data-model-text]");
      if (text && text.value.trim()) this._saveModel(text.dataset.modelText, text.value.trim());
    });
    $("devices").addEventListener("keydown", (e) => {
      if (e.key === "Enter" && e.target.matches?.("[data-model-text]")) e.target.dispatchEvent(new Event("change", { bubbles: true }));
    });
    $("devices").addEventListener("focusout", () => {
      // back to the live list once the pick is done
      setTimeout(() => this._view === "devices" && !this._editing() && this._render(), 0);
    });
    $("unknown").addEventListener("click", () => this._set("unknown", !this._filter.unknown));
    $("repeats").addEventListener("change", (e) => this._set("repeats", e.target.checked));
    $("filterBtn").addEventListener("click", () => this._toggleFilters());
    $("filterMenu").addEventListener("keydown", (e) => {
      if (e.key !== "Escape") return;
      e.stopPropagation();
      this._toggleFilters(false);
      $("filterBtn").focus();
    });
    $("activeFilters").addEventListener("click", (e) => {
      const chip = e.target.closest("[data-unset]");
      if (chip) this._set(chip.dataset.unset, NO_FILTER[chip.dataset.unset]);
    });
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
    $("devStatus").addEventListener("click", (e) => {
      const button = e.target.closest("[data-status]");
      if (!button) return;
      this._set("devStatus", button.dataset.status);
      // the weak-signal tab lists the weakest first
      if (button.dataset.status === "weak") this._setDevSort("signal", false);
    });
    $("tkReport").addEventListener("click", () => this._openReport());
    $("devGroup").addEventListener("change", (e) => {
      this._devGroup = e.target.value;
      try {
        localStorage.setItem(GROUP_KEY, this._devGroup);
      } catch (err) {
        // blocked storage: the choice just is not remembered
      }
      this._offset = 0;
      this._render();
    });
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
    $("lookBtn").addEventListener("click", () => this._toggleLook());
    $("lookMenu").addEventListener("click", (e) => {
      const b = e.target.closest("[data-look]");
      if (b) this._setLook({ [b.dataset.look]: b.dataset.value });
    });
    $("lookMenu").addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        this._toggleLook(false);
        $("lookBtn").focus();
      }
    });
    $("moreMenu").addEventListener("click", (e) => {
      const item = e.target.closest("[data-act]");
      if (!item) return;
      this._toggleMenu(false);
      if (item.dataset.act === "export") this._export();
      else if (item.dataset.act === "doc-import") $("docFile").click();
      else if (item.dataset.act.startsWith("doc-")) this._documentation(item.dataset.act.slice(4));
      else $("clear").click();
    });
    $("docFile").addEventListener("change", (e) => {
      const file = e.target.files[0];
      e.target.value = "";
      if (file) this._importDocumentation(file);
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
    $("teachForm").addEventListener("click", (e) => {
      if (e.target.closest("[data-teach-cancel]")) this._openTeach(null);
    });
    $("teachForm").addEventListener("change", (e) => {
      if (e.target.id === "teachProfile") this._renderTeach();
    });
    $("teachForm").addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        this._openTeach(null);
      }
    });
    $("teachForm").addEventListener("submit", (e) => {
      e.preventDefault();
      this._teachIn();
    });
    $("sendForm").addEventListener("submit", (e) => {
      e.preventDefault();
      this._send();
    });
    $("closeNotice").addEventListener("click", () => this._notice(""));
    const saveNote = (e) => {
      // a note is saved a moment after the last key; the list is not redrawn under the field
      const field = e.target.closest?.("[data-note-device], [data-note-gateway-only]");
      if (!field) return;
      clearTimeout(field._saving);
      field._saving = setTimeout(() => this._saveNote(field), 600);
    };
    $("devices").addEventListener("input", saveNote);
    $("cards").addEventListener("input", saveNote);
    $("cards").addEventListener("click", (e) => {
      const prune = e.target.closest("[data-prune-notes]");
      if (prune) {
        this._pruneNotes(prune.dataset.pruneNotes);
        return;
      }
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
    } else if (e.key === "Escape" && this.shadowRoot.querySelector(".addmenu")) {
      this._closeAddMenu(true);
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
    await this._checkTakeover();
    if (this._unsub !== unsub) return; // removed from the page (or subscribed anew) meanwhile
    if (!this._restored) {
      this._restored = true;
      const takeover = this.shadowRoot.querySelector('#view button[data-view="takeover"]');
      this._applyUrl() || this._setView(this._savedView === "takeover" && takeover?.hidden ? "telegrams" : this._savedView);
    }
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
    // the Takeover view comes and goes with the old configuration: checked about once a minute
    this._statusCount = (this._statusCount || 0) + 1;
    if (this._statusCount % TAKEOVER_CHECK === 0) this._checkTakeover();
    const server = gateways.find((g) => g.server_time != null)?.server_time;
    if (server != null) this._skew = server * 1000 - Date.now();
    // a remembered gateway filter for a gateway that is gone would hide everything
    if (this._filter.gateway && !gateways.some((g) => g.entry_id === this._filter.gateway)) {
      this._set("gateway", "");
    }
    this._renderCards(true);
    if (this._view === "devices") {
      for (const key of this._devOpen) {
        const gateway = this._deviceItems().find((d) => d.devKey === key)?.gateway;
        if (gateway) this._loadDevDetail(key, gateway);
      }
      this._render(true); // "heard x ago" moves on
    }
    if (this._managing() && !this._freeing) this._loadPools();
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
    if (this._holding()) {
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
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ view: this._view, pageSize: this._pageSize, sort: this._sort, filter: this._filter }));
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
    if (view === "senders") {
      // the sender ID pools live in the Installation view, Senders > Gateway senders, above the table
      this._in.tab = "gwsenders";
      view = "installation";
    }
    this._view = view;
    this._offset = 0;
    this._release(); // an open telegram holds only the telegram list
    const $ = (id) => this.shadowRoot.getElementById(id);
    $("panel").dataset.view = view;
    this._setManage();
    // the gateway cards filter the telegrams; Sender IDs and Takeover pick their gateway themselves
    $("gatewaySection").hidden = view === "takeover" || view === "installation";
    this._renderMini();
    // export saves what the view shows: telegrams, or the sender list
    const exportLabel = view === "devices" ? this._t.exportDevices : this._t.export;
    $("moreExport").textContent = view === "devices" ? this._t.exportDevicesShort : this._t.exportShort;
    this._toggleMenu(false);
    this._renderFilters();
    $("export").title = exportLabel;
    $("export").setAttribute("aria-label", exportLabel);
    if (view !== "telegrams") this._toggleSend(false);
    // the heading names the view; the section's label follows it
    const title = { telegrams: this._t.telegrams, devices: this._t.viewDevices, senders: this._t.viewSenders, takeover: this._t.viewTakeover, installation: this._t.viewInstallation }[view];
    $("viewTitle").textContent = title;
    $("panel").setAttribute("aria-label", title);
    if (view === "takeover") this._loadTakeover();
    if (view === "installation") this._loadInstallation();
    if (this._managing()) this._loadPools();
    if (view === "devices") this._loadRegistries().then(() => this._view === "devices" && this._render(true));
    for (const button of $("view").querySelectorAll("button")) {
      // tabs: only the chosen one is in the tab order, the arrow keys move between them
      button.setAttribute("aria-selected", String(button.dataset.view === view));
      button.tabIndex = button.dataset.view === view ? 0 : -1;
    }
    // phones: the chosen tab scrolls into the row
    const tabs = $("view");
    const tab = tabs.querySelector('[aria-selected="true"]');
    if (tab && tabs.scrollWidth > tabs.clientWidth) tabs.scrollTo({ left: tab.offsetLeft - (tabs.clientWidth - tab.offsetWidth) / 2 });
    this._fadeTabs();
    this._render();
    this._saveView();
  }

  _fadeTabs() {
    const tabs = this.shadowRoot.getElementById("view");
    const end = tabs.scrollWidth - tabs.clientWidth;
    tabs.classList.toggle("fade-start", end > 1 && tabs.scrollLeft > 1);
    tabs.classList.toggle("fade-end", end > 1 && tabs.scrollLeft < end - 1);
  }

  _applyUrl() {
    // a link into the panel: /enocean-eltako?view=devices&sender=05-10-A2-B3&gateway=<entry id>
    // sets view and filters once; the query then leaves the address so a reload keeps the view
    const params = new URLSearchParams(location.search);
    if (!location.pathname.endsWith("/enocean-eltako") || !["view", "sender", "gateway"].some((k) => params.has(k))) return false;
    const gateway = params.get("gateway");
    if (gateway && this._gateways.some((g) => g.entry_id === gateway)) this._set("gateway", gateway);
    if (params.has("sender")) this._setText(params.get("sender"));
    const view = params.get("view");
    const takeover = this.shadowRoot.querySelector('#view button[data-view="takeover"]');
    this._setView(VIEWS.includes(view) && !(view === "takeover" && takeover?.hidden) ? view : params.has("sender") ? "telegrams" : this._view);
    history.replaceState(history.state, "", location.pathname);
    return true;
  }

  _setText(value) {
    const input = this.shadowRoot.getElementById("text");
    input.value = value;
    this.shadowRoot.getElementById("clearText").hidden = !value;
    this._set("text", value);
  }

  // new telegrams are held back while the user paused, and while a telegram is open in the
  // list: the row being read must not move away; closing the last one lets them in again
  _holding() {
    return this._paused || (this._view === "telegrams" && this._expanded.size > 0);
  }

  _release() {
    if (this._holding()) return;
    for (const row of this._pending) this._keepPlace(row);
    this._rows = [...this._pending.reverse(), ...this._rows];
    this._pending = [];
    this._missed = 0;
    this._trim();
  }

  _togglePause() {
    this._paused = !this._paused;
    this._missed = 0;
    this._release();
    this._renderBar();
    this._render();
  }

  _toggleRow(key) {
    if (this._expanded.has(key)) this._expanded.delete(key);
    else this._expanded.add(key);
    this._release();
    this._renderBar();
    this._render();
  }

  _listClick(e) {
    const hide = e.target.closest("[data-hide]");
    if (hide) {
      e.stopPropagation();
      this._hideSender(hide.dataset.gateway, hide.dataset.hide);
      return;
    }
    const report = e.target.closest("[data-report]");
    if (report) {
      e.stopPropagation();
      this._reportDevice(report.dataset.report);
      return;
    }
    const record = e.target.closest("[data-record]");
    if (record) {
      e.stopPropagation();
      this._startRecording(record.dataset.record);
      return;
    }
    const recorded = e.target.closest("[data-report-recorded]");
    if (recorded) {
      e.stopPropagation();
      this._reportRows(this._recordings.get(recorded.dataset.reportRecorded)?.rows ?? []);
      return;
    }
    const add = e.target.closest(".add");
    if (add) {
      e.stopPropagation();
      this._addMenu(add);
      return;
    }
    const page = e.target.closest("[data-device-page]");
    if (page) {
      this._navigate(`/config/devices/device/${page.dataset.devicePage}`);
      return;
    }
    const inPanel = e.target.closest("[data-dev-panel]");
    if (inPanel) {
      this._showDevice(inPanel.dataset.devPanel);
      return;
    }
    const resend = e.target.closest("[data-resend]");
    if (resend) {
      this._resend(resend);
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
    if (e.target.closest("[data-empty-send]")) {
      this._toggleSend(true);
      this.shadowRoot.getElementById("sendData").focus();
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

  _reportDevice(sender) {
    // the sender's recent telegrams
    return this._reportRows(this._rows.filter((r) => r.sender === sender && r.dir === "rx" && !r.duplicate).slice(0, REPORT_TELEGRAMS).reverse());
  }

  _recordButton(sender) {
    const t = this._t;
    const rec = this._recordings.get(sender);
    if (!rec) return `<button class="icon-btn" data-record="${esc(sender)}" title="${esc(t.recordHint(RECORD_SECONDS))}" aria-label="${esc(t.record)}">${svg(ICON.play)}</button>`;
    if (!rec.rows) return `<span class="tag warn">${esc(t.recording)}</span>`;
    return rec.rows.length ? `<button class="chip text" data-report-recorded="${esc(sender)}">${svg(ICON.bug)}${esc(t.recordCopy(rec.rows.length))}</button>` : `<span class="tag">${esc(t.recordNone)}</span>`;
  }

  _startRecording(sender) {
    // listen to one sender for a minute, so the telegrams of what the user does with the device are
    // in the report; the copy needs a click again (browsers want a gesture for the clipboard)
    if (this._recordings.has(sender) && !this._recordings.get(sender).rows) return;
    const start = Date.now();
    this._recordings.set(sender, { start });
    this._notice(this._t.recordStarted(RECORD_SECONDS), true);
    this._render(true);
    setTimeout(() => {
      const rows = this._rows.filter((r) => r.sender === sender && r.dir === "rx" && !r.duplicate && new Date(r.time).getTime() >= start).slice(0, REPORT_TELEGRAMS * 5).reverse();
      this._recordings.set(sender, { start, rows });
      this._notice(this._t.recordDone(rows.length), true);
      if (this._view === "telegrams") this._render(true);
    }, RECORD_SECONDS * 1000);
  }

  async _reportRows(rows) {
    // anonymised on the clipboard; the issue form opens empty (no data in the URL)
    if (!rows.length) return;
    try {
      await navigator.clipboard.writeText(anonymisedCapture(rows, CAPTURE_KEYS).join("\n") + "\n");
    } catch (err) {
      this._notice(this._t.copyFailed);
      return;
    }
    this._notice(this._t.reportCopied(rows.length), true);
    window.open(DEVICE_REQUEST_URL, "_blank", "noopener");
  }

  async _hideSender(gateway, sender) {
    this._notice("");
    try {
      await this._hass.callWS({ type: "enocean_eltako/hide_sender", entry_id: gateway, sender });
    } catch (err) {
      this._notice(this._t.hideResult[err.code] || this._t.hideResult.failed);
      return;
    }
    await this._refreshStatus();
    this._render();
    this._notice(this._t.hideResult.done(sender), true);
  }

  _addMenu(button) {
    // the + of an unknown sender asks: set it up as a device in Home Assistant, or only write it down
    const t = this._t;
    this._popupMenu(
      button,
      button.dataset.id,
      `<button role="menuitem" data-addact="device">${svg(ICON.plus)}<span>${esc(t.addAsDevice)}<small>${esc(t.addAsDeviceHint)}</small></span></button>
      <button role="menuitem" data-addact="document">${svg(ICON.list)}<span>${esc(t.addDocOnly)}<small>${esc(t.addDocOnlyHint)}</small></span></button>`,
      (act) => (act === "device" ? this._addDevice(button.dataset.id) : this._documentSender(button.dataset.gateway, button.dataset.id))
    );
  }

  _rowMenu(button) {
    // the ⋮ of a device row: what else can be done with it, so the row's buttons never move around
    const t = this._t;
    const d = button.dataset;
    const item = (act, icon, label) => `<button role="menuitem" data-addact="${act}">${svg(icon)}<span>${esc(label)}</span></button>`;
    this._popupMenu(
      button,
      d.rowmore,
      (d.mTeach ? item("teach", ICON.teach, t.teachHint) : "") + (d.mPage ? item("page", ICON.open, t.openDeviceHint) : "") + (d.mOnly ? item("only", ICON.filter, t.showTelegrams) : "") + (d.mRemove ? item("remove", ICON.clear, t.selRemove) : ""),
      (act) => {
        if (act === "teach") this._openTeach(d.mTeach);
        else if (act === "remove") {
          // the row's own device goes through the same confirmation as a ticked selection
          this._sel = new Set([d.mRemove]);
          this._pick = null;
          this._openPick("remove");
        }
        else if (act === "page") this._navigate(`/config/devices/device/${d.mPage}`);
        else {
          this._setText(d.mOnly);
          this._setView("telegrams");
        }
      }
    );
  }

  _popupMenu(button, ref, items, onAct) {
    const open = this.shadowRoot.querySelector(".addmenu");
    const again = open && open._for === ref;
    this._closeAddMenu();
    if (again) return;
    const menu = document.createElement("div");
    menu.className = "addmenu";
    menu.setAttribute("role", "menu");
    menu._for = ref;
    menu.innerHTML = items;
    menu.addEventListener("click", (e) => {
      const act = e.target.closest("[data-addact]")?.dataset.addact;
      if (!act) return;
      e.stopPropagation();
      this._closeAddMenu();
      onAct(act);
    });
    this.shadowRoot.appendChild(menu);
    const box = button.getBoundingClientRect();
    const width = menu.offsetWidth;
    menu.style.left = `${Math.max(8, Math.min(box.right - width, window.innerWidth - width - 8))}px`;
    const below = box.bottom + 4;
    menu.style.top = `${below + menu.offsetHeight > window.innerHeight ? Math.max(8, box.top - menu.offsetHeight - 4) : below}px`;
    menu._anchor = button;
    button.setAttribute("aria-expanded", "true");
    menu.querySelector("button").focus();
  }

  _closeAddMenu(refocus = false) {
    const menu = this.shadowRoot.querySelector(".addmenu");
    if (!menu) return;
    menu._anchor?.removeAttribute("aria-expanded");
    if (refocus) menu._anchor?.focus();
    menu.remove();
  }

  async _documentSender(gateway, sender) {
    // only for the documentation: the form of "Write down as device" opens with the ID filled in and a kind guessed
    // from what the sender sent; an ID written down before is shown in its row instead
    const gw = this._gateways.find((g) => g.entry_id === gateway);
    if (!gw) {
      this._notice(this._t.addResult.failed);
      return;
    }
    const same = (a) => String(a).replace(/[^0-9a-f]/gi, "").toLowerCase();
    const entry = (gw.manual ?? []).find((e) => same(e.address) === same(sender));
    const last = this._rows.find((r) => same(r.sender) === same(sender));
    // a press or release telegram is a button, a contact or data telegram a sensor, a VLD telegram an actuator
    const kind = { F6: "taster", D2: "aktor" }[last?.rorg] ?? (last ? "sensor" : "taster");
    this._in.tab = "devices";
    this._in.view = "funk";
    if (entry) this._in.hl = `manual|${entry.id}`;
    else {
      this._in.docForm = true;
      this._in.docError = "";
      this._in.docDraft = { kind, address: sender, gateway };
    }
    this._setView("installation");
    // the Installation view fills in a moment after it opens: wait up to two seconds for the form or the row
    for (let tries = 0; tries < 40; tries++) {
      const target = this.shadowRoot.querySelector(entry ? `#installation [data-in-row="manual|${entry.id}"]` : '#installation [data-in-doc-field="name"]');
      if (target) {
        target.scrollIntoView({ block: "center" });
        if (!entry) target.focus();
        return;
      }
      await new Promise((resolve) => setTimeout(resolve, 50));
    }
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

  _toggleFilters(open = this.shadowRoot.getElementById("filterMenu").hidden) {
    const $ = (id) => this.shadowRoot.getElementById(id);
    $("filterMenu").hidden = !open;
    $("filterBtn").setAttribute("aria-expanded", String(open));
    if (open) [...$("filterMenu").querySelectorAll("select, input")].find((el) => el.offsetParent)?.focus();
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
    $("sendReleaseRow").hidden = $("sendType").value !== "F6"; // only a rocker is let go
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
    const send = (data, status) =>
      this._hass.callWS({
        type: "enocean_eltako/send",
        entry_id: $("sendGateway").value,
        sender: $("sendSender").value,
        rorg: $("sendType").value,
        data,
        status,
      });
    try {
      let result = await send($("sendData").value.trim(), $("sendStatus").value.trim());
      const ok = ["sent", "confirmed"].includes(result.result);
      // a rocker press, then its release (energy bow up: no button, T21 set, NU clear)
      if (ok && $("sendType").value === "F6" && $("sendRelease").checked) {
        const release = await send("00", "20");
        if (!["sent", "confirmed"].includes(release.result)) result = release;
      }
      this._notice(t.sendResult[result.result] || t.sendResult.unknown, ["sent", "confirmed"].includes(result.result));
    } catch (err) {
      this._notice(t.sendResult[err.code] || t.sendResult.unknown);
    }
    $("sendGo").disabled = false;
  }

  _canResend(r) {
    // a sent telegram of a type the send form knows, from a sender ID one of the devices uses
    return r.dir === "tx" && !!SEND_TYPES[r.rorg] && !!this._gateways.find((g) => g.entry_id === r.gateway && g.loaded)?.senders?.some((s) => s.id === r.sender);
  }

  async _resend(button) {
    // the same telegram again; a rocker press is released right after, as by the send form
    const t = this._t;
    const r = this._rows.find((row) => rowKey(row) === button.dataset.resend);
    if (!r) return;
    const send = (data, status) => this._hass.callWS({ type: "enocean_eltako/send", entry_id: r.gateway, sender: r.sender, rorg: r.rorg, data, status });
    button.disabled = true;
    try {
      let result = await send(r.data, r.status);
      const ok = (res) => ["sent", "confirmed"].includes(res.result);
      if (ok(result) && r.rorg === "F6" && r.data !== "00") {
        const release = await send("00", "20");
        if (!ok(release)) result = release;
      }
      this._notice(t.sendResult[result.result] || t.sendResult.unknown, ok(result));
    } catch (err) {
      this._notice(t.sendResult[err.code] || t.sendResult.unknown);
    }
    button.disabled = false;
  }

  _notice(text, done = false) {
    // a success ("done") goes after a few seconds; errors and hints stay until closed
    const notice = this.shadowRoot.getElementById("notice");
    clearTimeout(this._noticeTimer);
    notice.hidden = !text;
    notice.classList.toggle("ok", done);
    notice.querySelector("span").textContent = text;
    if (text) this._announce(text);
    if (text && done) this._noticeTimer = setTimeout(() => this._notice(""), NOTICE_TIME);
  }

  _number(value, options = {}) {
    // as the user's profile says: number format ("language", "system", "comma_decimal" ...)
    const locale = this._hass.locale || {};
    const language = locale.language || this._hass.language;
    const locales = { system: undefined, comma_decimal: ["en-US", "en"], decimal_comma: ["de", "es", "it"], space_comma: ["fr", "sv", "cs"] };
    const format = locale.number_format;
    return value.toLocaleString(format in locales ? locales[format] : language, { ...options, ...(format === "none" ? { useGrouping: false } : {}) });
  }

  _timeFormat(withDate = false, ms = false) {
    // as the user's profile says: 12 or 24 hours, and the browser's or the server's time zone
    const locale = this._hass.locale || {};
    return new Intl.DateTimeFormat(locale.time_format === "system" ? undefined : locale.language || this._hass.language, {
      hour: "2-digit", minute: "2-digit", second: "2-digit",
      hour12: locale.time_format === "12" ? true : locale.time_format === "24" ? false : undefined,
      timeZone: locale.time_zone === "server" ? this._hass.config?.time_zone : undefined,
      ...(withDate ? { year: "numeric", month: "2-digit", day: "2-digit" } : {}),
      ...(ms ? { fractionalSecondDigits: 3 } : {}),
    });
  }

  _time(date, withDate = false, ms = false) {
    return this._timeFormat(withDate, ms).format(date);
  }

  _clock(date) {
    // the list's time: milliseconds small, where the locale puts them ("1:02:03.456 PM")
    const parts = this._timeFormat(false, true).formatToParts(date);
    return parts
      .map((p, i) => {
        if (p.type === "fractionalSecond") return `<small>${esc(parts[i - 1]?.type === "literal" ? parts[i - 1].value : "")}${esc(p.value)}</small>`;
        if (p.type === "literal" && parts[i + 1]?.type === "fractionalSecond") return "";
        return esc(p.value);
      })
      .join("");
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
      [r.device, r.data, r.teach_in, r.profile, r.eep, r.model, r.gateway_name, ...(r.candidates || []), ...(r.fits || []), ...extra].some((v) => v && String(v).toLowerCase().includes(text)) ||
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
      this._notice(this._t.copied, true);
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
    this._download(csv([head, ...lines]), "text/csv", `enocean-devices-${new Date().toISOString().replace(/[:.]/g, "-")}.csv`);
  }

  async _saveNote(field) {
    const msg = { type: "enocean_eltako/set_note", text: field.value };
    if (field.dataset.noteDevice) Object.assign(msg, { entry_id: field.dataset.noteGateway, device: field.dataset.noteDevice });
    else msg.entry_id = field.dataset.noteGatewayOnly;
    try {
      await this._hass.callWS(msg);
    } catch (err) {
      this._notice(this._t.doc.noteFailed);
      return;
    }
    // what the panel shows next time it asks
    if (field.dataset.noteDevice) {
      const known = this._devDetails.get(field.dataset.noteDevice);
      if (known) known.note = field.value;
    } else {
      const gateway = this._gateways.find((g) => g.entry_id === field.dataset.noteGatewayOnly);
      if (gateway) gateway.note = field.value;
    }
  }

  async _documentation(kind) {
    // the installation documentation of every gateway: a page to print, a CSV or the JSON
    this._notice("");
    let doc;
    try {
      doc = await this._hass.callWS({ type: "enocean_eltako/documentation" });
    } catch (err) {
      this._notice(this._t.doc.failed);
      return;
    }
    const stamp = new Date().toISOString().replace(/[:.]/g, "-");
    const profile = (p) => this._profile(p);
    if (kind === "json") this._download(JSON.stringify(doc, null, 2) + "\n", "application/json", `enocean-documentation-${stamp}.json`);
    else if (kind === "csv" || kind === "csv-links" || kind === "csv-tables") {
      const table = { csv: "devices", "csv-links": "links", "csv-tables": "tables" }[kind];
      this._download(documentationCsv(doc, this._t, profile, table), "text/csv", `enocean-${table === "devices" ? "installation" : table}-${stamp}.csv`);
    }
    else {
      const page = documentationHtml(doc, this._t, profile, this._hass.language || "en");
      const win = window.open("", "_blank");
      if (!win) {
        this._download(page, "text/html", `enocean-documentation-${stamp}.html`); // pop-ups blocked: open the file and print it
        this._notice(this._t.doc.popupBlocked, true);
        return;
      }
      win.document.write(page);
      win.document.close();
      win.focus();
      win.print();
    }
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
    const state = this._link !== "live" ? this._link : this._holding() ? "paused" : "live";
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
    // the chip counts the unknown senders in the buffer, so it shows whether there is something to look at
    const unknown = new Set(this._rows.filter((r) => !r.device && r.dir === "rx" && !this._isHidden(r.gateway, r.sender)).map((r) => `${r.gateway}|${r.sender}`)).size;
    $("unknown").innerHTML = `${esc(this._t.unknownOnly)}${unknown ? ` <span class="n">${unknown}</span>` : ""}`;
    for (const button of $("devStatus").querySelectorAll("button")) {
      button.setAttribute("aria-pressed", String(button.dataset.status === f.devStatus));
    }
    $("repeats").checked = f.repeats;
    const t = this._t;
    this._options($("gatewayFilter"), [["", t.allGateways], ...this._gateways.map((g) => [g.entry_id, g.title])], f.gateway);
    $("gatewayRow").hidden = !this._multi && !f.gateway;
    const devices = this._view === "devices";
    $("resetTop").hidden = !(f.gateway || f.text || (devices ? f.devStatus || f.area : f.dir || f.type || f.repeats || f.unknown));
    // the filters of the menu that are set: a chip each, its cross removes it
    const gateway = this._gateways.find((g) => g.entry_id === f.gateway);
    const chips = [
      f.gateway && ["gateway", `${t.gateway}: ${gateway?.title || f.gateway}`],
      ...(devices
        ? [f.area && ["area", `${t.devCols.area}: ${f.area}`]]
        : [f.type && ["type", `${t.type}: ${RORG[f.type] || f.type}`], f.repeats && ["repeats", t.repeats]]),
    ].filter(Boolean);
    $("activeFilters").innerHTML = chips
      .map(([key, label]) => `<button class="chip set" data-unset="${key}" title="${esc(t.removeFilter(label))}" aria-label="${esc(t.removeFilter(label))}">${esc(label)}${svg(ICON.close)}</button>`)
      .join("");
    $("filterCount").hidden = !chips.length;
    $("filterCount").textContent = chips.length;
    $("filterBtn").classList.toggle("on", chips.length > 0);
    this._syncFilterBtn();
  }

  _syncFilterBtn() {
    // the devices view has nothing behind Filter without several gateways or areas
    const $ = (id) => this.shadowRoot.getElementById(id);
    const any = this._view !== "devices" || !$("gatewayRow").hidden || !$("devAreaRow").hidden;
    $("filterBtn").hidden = !any;
    if (!any && !$("filterMenu").hidden) this._toggleFilters(false);
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
        return `<th scope="col"${state}><button data-sort="${sort}" aria-label="${esc(aria || label)}">${esc(label)}${svg(ICON.chevron, "sort")}</button></th>`;
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

  async _importDocumentation(file) {
    // notes and entries made by hand from an earlier JSON export; only what is empty is filled in
    const t = this._t.doc;
    let reply;
    try {
      const doc = JSON.parse(await file.text());
      reply = await this._hass.callWS({ type: "enocean_eltako/import_documentation", doc });
      // a swapped gateway has another base ID: one gateway of the file and one set up here that
      // got nothing belong together, if the user says so
      const lost = reply.gateways.filter((g) => !g.matched);
      const matched = new Set(reply.gateways.filter((g) => g.matched).map((g) => g.title));
      const free = this._gateways.filter((g) => g.loaded && !matched.has(g.title));
      if (lost.length === 1 && free.length === 1 && lost[0].base_id && window.confirm(t.importMap(lost[0].title, free[0].title))) {
        reply = await this._hass.callWS({ type: "enocean_eltako/import_documentation", doc, gateway_map: { [lost[0].base_id]: free[0].entry_id } });
      }
    } catch (err) {
      this._notice(err.code === "unsupported_version" || err instanceof SyntaxError ? t.importUnsupported : t.importFailed);
      return;
    }
    await this._refreshStatus();
    this._render();
    this._notice(t.importDone(reply.gateways), true);
  }

  async _pruneNotes(entryId) {
    try {
      await this._hass.callWS({ type: "enocean_eltako/prune_notes", entry_id: entryId });
    } catch (err) {
      this._notice(this._t.doc.noteFailed);
      return;
    }
    const gateway = this._gateways.find((g) => g.entry_id === entryId);
    if (gateway) gateway.orphan_notes = 0;
    this._renderCards();
  }

  _renderCards(background = false) {
    const t = this._t;
    const cards = this.shadowRoot.getElementById("cards");
    if (!cards || this._hold("cards", cards, background)) return;
    if (!this._gateways.length) {
      this._replace(cards, `<div class="panel">${this._noGateway()}</div>`);
      return;
    }
    this._renderMini();
    const now = this._now() / 1000;
    this._replace(cards, this._gateways
      .map((gw) => {
        let pill = ["", t.notLoaded];
        if (gw.loaded) {
          if (gw.connected && gw.proxy?.via_fallback) pill = ["idle", t.viaFallback(gw.proxy.fallback_name)];
          else if (gw.connected) pill = ["ok", t.connected];
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
          ${gw.loaded ? `<div class="rate"><div><b>${esc(rate)}</b> <span>${esc(t.perMinute)}</span></div><span class="last">${esc(last)}</span></div><div class="gateway-count"><b>${esc(t.devicesN(gw.devices ?? "–"))}</b><span>${esc(t.freeN(gw.free_senders ?? "–"))}</span></div>` : ""}
          <div class="gateway-actions">${this._gateways.length > 1 || selected ? `<button class="chip" data-gateway-action="filter" title="${esc(t.cardHint)}" aria-pressed="${selected}">${svg(ICON.filter)}${esc(t.telegrams)}</button>` : ""}<button class="chip text" data-gateway-action="details" aria-expanded="${expanded}">${esc(t.details)}${svg(ICON.chevron)}</button></div>
          ${expanded ? `<div class="gateway-details"><div class="connection mono">${esc(gw.connection)}</div><div class="stats">${stat(t.queue, gw.queue ?? "–", gw.queue > 5)}${stat(t.unconfirmed, gw.unconfirmed ?? "–", gw.unconfirmed > 0)}${stat(t.freeSenders, gw.free_senders ?? "–", gw.free_senders === 0)}</div>${gw.via_proxy ? this._proxyLine(gw) : ""}<input class="note" data-note-gateway-only="${esc(gw.entry_id)}" value="${esc(gw.note ?? "")}" maxlength="500" placeholder="${esc(t.doc.gatewayNotePlaceholder)}" aria-label="${esc(t.doc.notes)}" autocomplete="off">${gw.orphan_notes ? `<div><button class="chip text" data-prune-notes="${esc(gw.entry_id)}" title="${esc(t.doc.pruneHint)}">${esc(t.doc.prune(gw.orphan_notes))}</button></div>` : ""}<div class="gateway-actions"><button class="chip" data-open-integration="${esc(gw.entry_id)}">${svg(ICON.open)}${esc(t.openIntegration)}</button></div></div>` : ""}
        </article>`;
      })
      .join(""));
  }

  _renderMini() {
    const mini = this.shadowRoot.getElementById("mini");
    const show = this._cardsAway && this._gateways.length > 0 && !this.shadowRoot.getElementById("gatewaySection").hidden;
    mini.hidden = !show;
    if (!show) return;
    const t = this._t;
    const state = (gw) => (!gw.loaded ? ["", t.notLoaded] : gw.connected && gw.proxy?.via_fallback ? ["idle", t.viaFallback(gw.proxy.fallback_name)]
      : gw.connected ? ["ok", t.connected] : gw.on_demand ? ["idle", t.onDemand] : ["bad", t.disconnected]);
    const html = this._gateways
      .map((gw) => {
        const [cls, label] = state(gw);
        const rate = gw.loaded ? ` · ${gw.per_minute ?? "–"} ${t.perMinute}` : "";
        return `<span title="${esc(`${gw.title}: ${label}`)}"><i class="${cls}"></i><span class="mini-text">${esc(gw.title)}${esc(rate)}</span></span>`;
      })
      .join("");
    if (mini.innerHTML !== html) mini.innerHTML = html;
    mini.title = t.gateways;
    mini.setAttribute("aria-label", `${t.gateways}: ${this._gateways.map((gw) => `${gw.title} ${state(gw)[1]}`).join(", ")}`);
  }

  _proxyLine(gw) {
    const t = this._t;
    const p = gw.proxy;
    if (!p) {
      return `<div class="proxy"><span class="tag">${esc(t.viaProxy("", ""))}</span><span class="muted">${esc(gw.proxy_error?.kind === "gateway" ? t.proxyGatewayMissing : t.proxyUnreachable)}</span></div>`;
    }
    const share = Number(p.duty_of_limit ?? 0);
    const level = share >= 80 ? "bad" : share >= 50 ? "warn" : "";
    return `<div class="proxy">
        <span class="tag">${esc(t.viaProxy(p.app, p.version))}</span>
        <span>${esc(t.programs(p.programs ?? 0))}</span>
        ${p.exclusive_peer ? `<span class="tag warn">${esc(t.alone(p.exclusive_peer))}</span>` : ""}
        ${p.via_fallback ? `<span class="tag warn">${esc(t.fallbackActive(p.fallback_name))}</span>`
          : p.fallback_ready === true ? `<span class="tag">${esc(t.fallbackReady(p.fallback_name))}</span>`
          : p.fallback_ready === false ? `<span class="tag warn">${esc(t.fallbackNotReady(p.fallback_name))}</span>` : ""}
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
    return this._t.commandValues[value] || String(value);
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
    const mark = (list) => list.map((b, i) => (same && b === (list === bytes ? before : bytes)[i] ? esc(b) : `<span class="chg">${esc(b)}</span>`)).join(" ");
    const raw = mark(bytes);
    const differing = same ? bytes.flatMap((b, i) => (b === before[i] ? [] : [i])) : [];
    const bytesText = differing.length === 1 ? this._t.byteChanged(differing[0] + 1, before[differing[0]], bytes[differing[0]]) : differing.length > 1 ? this._t.bytesChanged(differing.length) : "";
    const now = new Map((r.fields || []).map((f) => [f.label, f]));
    const changes = (prev.fields || [])
      .map((old) => [old, now.get(old.label)])
      .filter(([old, cur]) => cur && cur.value !== old.value)
      .map(([old, cur]) => `${this._label(cur.label)}: ${this._value(old.value)} → ${this._value(cur.value)}${cur.unit ? ` ${cur.unit}` : ""}`);
    const unchanged = same && r.data === prev.data;
    const text = changes.length ? changes.join(" · ") : unchanged ? this._t.noChange : "";
    return { raw, prev: mark(before), text: [bytesText, text].filter(Boolean).join(" · ") };
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
    const clock = this._clock(time);
    const unknown = !r.device && r.dir === "rx";
    const hidden = unknown && this._isHidden(r.gateway, r.sender);
    // a telegram we sent is addressed to the device, it did not come from it
    const sent = r.dir === "tx";
    const name = r.device
      ? `<span class="name">${esc(r.device)}</span>`
      : `<span class="name unknown">${esc(unknown ? t.unknownDevice : r.sender)}</span>`;
    // the one case that asks for attention: a command nobody answered
    const pairText = sent || expanded ? this._pairText(r) : "";
    const unanswered = sent && pairText === t.noAnswer;
    const tags = (sent ? `<span class="tag tx">${esc(t.tx)}</span>` : "") + (unanswered ? `<span class="tag warn" title="${esc(t.noAnswer)}">${esc(t.noAnswerTag)}</span>` : "") + (r.duplicate ? `<span class="tag">${esc(t.duplicate)}</span>` : "") +
      (hidden ? `<span class="tag" title="${esc(t.hiddenHint)}">${esc(t.hiddenTag)}</span>` : "");
    const extra = r.teach_in ? `<span class="tag teach">${esc(t.teachIn)} ${esc(r.teach_in)}</span>` : "";
    const maybe = r.fits ? maybeTag(t, r.fits, t.fits, t.fitsHint) : maybeTag(t, r.candidates);
    const type = RORG[r.rorg] || r.rorg;
    // on phones type and gateway have no column of their own
    const line2 = [`${sent ? `${esc(t.sentFrom)} ` : ""}<span class="mono">${esc(r.sender)}</span>`, r.profile ? esc(this._profile(r.profile)) : "", r.eep ? esc(r.eep) : "", r.eep?.endsWith(":eltako") && r.model ? esc(r.model) : ""].filter(Boolean).join(" · ") +
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
    const pair = expanded ? pairText : "";
    const diff = expanded ? this._diff(r) : null;
    const copies = expanded && !r.duplicate ? this._repeats(r) : 0;
    const hops = parseInt(r.status, 16) & 0x0f; // low nibble of the status byte: repeater count
    const details = expanded
      ? `<tr class="detail-row" data-key="${esc(key)}"><td colspan="${this._multi ? 8 : 7}"><div class="details">
          <div class="hero">
            <span class="l">${esc(t.raw)}</span><span class="v mono">${diff ? diff.raw : esc(r.data)}</span>
            ${diff ? `<span class="l">${esc(t.before)}</span><span class="v prev mono">${diff.prev}</span>` : ""}
            ${diff?.text ? `<span class="hint">${esc(diff.text)}</span>` : ""}
          </div>
          <div class="acts">
            <button class="icon-btn" data-copy="${esc(key)}" title="${esc(t.copy)}" aria-label="${esc(t.copy)}">${svg(ICON.copy)}</button>
            <button class="icon-btn" data-only="${esc(r.device || r.sender)}" title="${esc(r.device ? t.filterDevice : t.filterSender)}" aria-label="${esc(r.device ? t.filterDevice : t.filterSender)}">${svg(ICON.filter)}</button>
            ${r.device_key && this._inPanel(r.device_key) ? `<button class="icon-btn" data-dev-panel="${esc(r.device_key)}" title="${esc(t.inPanelHint)}" aria-label="${esc(t.inPanel)}">${svg(ICON.list)}</button>` : ""}
            ${r.ha_device ? `<button class="icon-btn" data-device-page="${esc(r.ha_device)}" title="${esc(t.openDeviceHint)}" aria-label="${esc(t.openDevice)}">${svg(ICON.open)}</button>` : ""}
            ${this._canResend(r) ? `<button class="icon-btn" data-resend="${esc(key)}" title="${esc(t.resendHint)}" aria-label="${esc(t.resend)}">${svg(ICON.send)}</button>` : ""}
            ${unknown ? `<button class="icon-btn" data-report="${esc(r.sender)}" title="${esc(t.reportHint)}" aria-label="${esc(t.report)}">${svg(ICON.bug)}</button>${this._recordButton(r.sender)}` : ""}
            ${unknown && !hidden ? `<button class="icon-btn" data-hide="${esc(r.sender)}" data-gateway="${esc(r.gateway)}" title="${esc(t.hideSenderHint)}" aria-label="${esc(t.hideSender)}">${svg(ICON.hide)}</button><button class="icon-btn add" data-id="${esc(r.sender)}" data-gateway="${esc(r.gateway)}" aria-haspopup="menu" title="${esc(t.addHint)}" aria-label="${esc(t.add)}">${svg(ICON.plus)}</button>` : ""}
          </div>
          <dl class="meta">
          <div><dt>${esc(t.time)}</dt><dd class="mono">${esc(this._time(time, true, true))}</dd></div>
          <div><dt>${esc(t.gateway)}</dt><dd>${esc(r.gateway_name)}</dd></div>
          <div><dt>${esc(t.type)}</dt><dd>${esc(type)} (${esc(r.rorg)})</dd></div>
          <div><dt>${esc(t.destination)}</dt><dd class="mono">${esc(r.destination)}</dd></div>
          <div><dt>${esc(t.status)}</dt><dd class="mono">${esc(r.status)}</dd></div>
          ${hops ? `<div><dt>${esc(t.repeater)}</dt><dd>${hops}</dd></div>` : ""}
          ${copies ? `<div><dt>${esc(t.repeated)}</dt><dd>${esc(t.heardTimes(copies))}</dd></div>` : ""}
          ${r.candidates ? `<div class="wide"><dt>${esc(t.maybe)}</dt><dd class="mono">${esc(r.candidates.join(", "))}</dd></div>` : ""}
          ${r.fits ? `<div class="wide"><dt>${esc(t.fits)}</dt><dd>${esc(r.fits.join(", "))}</dd></div>` : ""}
          ${r.eep ? `<div><dt>${esc(t.eep)}</dt><dd class="mono">${esc(r.eep)}</dd></div>` : ""}
          ${r.model ? `<div><dt>${esc(t.model)}</dt><dd>${esc(r.model)}</dd></div>` : r.models?.length ? `<div class="wide"><dt>${esc(t.models)}</dt><dd>${esc(r.models.join(", "))}</dd></div>` : ""}
          ${pair ? `<div><dt>${esc(t.pair)}</dt><dd>${esc(pair)}</dd></div>` : ""}
          ${r.profile ? `<div><dt>${esc(t.profile)}</dt><dd>${esc(this._profile(r.profile))}</dd></div>` : ""}
          </dl>
        </div></td></tr>`
      : "";
    const classes = ["row", r.dir === "tx" ? "tx" : "", unanswered ? "noans" : "", r.duplicate ? "dup" : "", expanded ? "open" : "", this._fresh.has(key) ? "fresh" : ""].filter(Boolean).join(" ");
    return `<tr class="${classes}" data-key="${esc(key)}">
      <td class="time">${clock}</td>
      <td class="dirc"><span class="dir ${r.dir === "rx" ? "rx" : "tx"}" role="img" title="${esc(r.dir === "rx" ? t.rx : t.tx)}" aria-label="${esc(r.dir === "rx" ? t.rx : t.tx)}">${svg(r.dir === "rx" ? ICON.rx : ICON.tx)}</span></td>
      <td class="who" title="${esc([r.device, r.sender, r.gateway_name].filter(Boolean).join(" · "))}"><div class="line1">${name}${tags}</div><div class="line2">${line2}</div></td>
      <td class="type"><span class="rorg mono" title="${esc(r.rorg)}">${esc(type)}</span></td>
      <td class="content"><div class="values">${extra}${values}${maybe}</div></td>
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
    if (this._view === "takeover" || this._view === "installation") return;
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
      const empty = filtered
        ? this._emptyState(ICON.search, t.noMatchTitle, t.noMatchText, `<button class="chip reset">${esc(t.resetFilters)}</button>`)
        : this._emptyState(ICON.tower, t.emptyTitle, t.emptyText, this._gateways.some((g) => g.loaded) ? `<button class="chip" data-empty-send>${svg(ICON.send)}${esc(t.send)}</button>` : "");
      this._replace(list, `<tr class="empty-row"><td colspan="${this._multi ? 8 : 7}">${empty}</td></tr>`);
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
    const $ = (id) => this.shadowRoot.getElementById(id);
    const pool = this._pools.find((p) => p.id === this._pool);
    if (!pool) {
      this._replace($("sidTop"), this._noGateway());
      this._replace($("sidList"), "");
      return;
    }
    const blocked = pool.rows.filter((r) => r.state === "blocked");
    this._sidBlocked = blocked.map((r) => r.id);
    const select = this._pools.length > 1
      ? `<div class="pick"><select class="select" id="poolSelect" aria-label="${esc(t.pools)}">${this._pools
          .map((p) => `<option value="${esc(p.id)}"${p.id === pool.id ? " selected" : ""}>${esc(this._poolLabel(p))}</option>`)
          .join("")}</select></div>`
      : "";
    const byId = new Map(pool.rows.map((r) => [r.decimal, r]));
    const away = new Set(pool.unavailable);
    const lastByte = (n) => (n & 255).toString(16).toUpperCase().padStart(2, "0");
    const lastId = pool.first + pool.size - 1;
    let readout = `<span>${esc(t.mapHint)}</span>`;
    const tiles = Array.from({ length: pool.size }, (_, i) => {
      const n = pool.first + i;
      const hex = [24, 16, 8, 0].map((sh) => ((n >>> sh) & 255).toString(16).toUpperCase().padStart(2, "0")).join("-");
      const r = byId.get(n);
      const state = r ? r.state : away.has(n) ? "unavailable" : "free";
      const label = { assigned: t.stateAssigned, blocked: t.stateBlocked, unavailable: t.stateUnavailable, free: t.stateFree }[state];
      const who = r?.device ? ` · ${r.device}` : "";
      const text = `${hex} (${i + 1}) · ${label}${who}`;
      const chosen = this._poolSel === hex;
      if (chosen) readout = `<span class="mono"><b>${esc(hex)}</b></span><span>${i + 1}</span><span>${esc(label)}</span>${r?.device ? `<span><b>${esc(r.device)}</b>${r.profile ? ` · ${esc(this._profile(r.profile))}` : ""}</span>` : ""}`;
      // a label starts every row: its range, every 32 IDs (16 on phones, which break in between)
      const range = (len) => `${lastByte(n)}–${lastByte(Math.min(n + len - 1, lastId))}`;
      const row = i % 16 ? "" : `<span class="row-id${i % 32 ? " half" : ""}" aria-hidden="true" title="${esc(hex)}">${i % 32 ? "" : `<span class="lf">${range(32)}</span>`}<span class="lh">${range(16)}</span></span>`;
      return `${row}<button class="t-${state}${chosen ? " sel" : ""}" data-tile="${esc(hex)}"${r ? ` data-goto="${i + 1}"` : ""} title="${esc(text)}" aria-label="${esc(text)}"></button>`;
    }).join("");
    const assigned = pool.rows.length - blocked.length;
    // the legend names the states the map shows, with their numbers; free is always there to compare with
    const shown = new Set(["free", ...pool.rows.map((r) => r.state), ...(away.size ? ["unavailable"] : [])]);
    const counts = { free: pool.free, assigned, blocked: blocked.length, unavailable: away.size };
    const legend = [["free", t.stateFree], ["assigned", t.stateAssigned], ["blocked", t.stateBlocked], ["unavailable", t.stateUnavailable]]
      .filter(([state]) => shown.has(state))
      .map(([state, label]) => `<span><i class="t-${state}"></i>${esc(label)} ${counts[state]}</span>`)
      .join("");
    const note = blocked.length
      ? `<div class="pnote"><span>${esc(t.poolBlockedNote(blocked.length))}</span><button data-free-all>${esc(t.freeAllAction(blocked.length))}</button></div>`
      : "";
    this._replace($("sidTop"), `${select}
      ${note}
      <div class="map" role="group" aria-label="${esc(t.mapLabel)}">${tiles}</div>
      <div class="pread" aria-live="polite">${readout}</div>
      <div class="legend" aria-hidden="true">${legend}</div>
      <p class="mapscope">${esc(t.mapScope)}</p>`);
    // the release asks first: for one ID or for all blocked ones
    const confirm = this._freeing?.all
      ? `<b>${esc(t.freeAllConfirmTitle(this._freeing.ids.length))}</b><p>${esc(t.freeAllConfirmText)}</p>`
      : this._freeing
      ? `<b>${esc(t.freeConfirmTitle(this._freeing.id))}</b><p>${esc(t.freeConfirmText)}</p>`
      : "";
    const ok = this._freeing?.all ? t.freeAllConfirm : t.freeConfirm;
    this._replace($("sidList"), confirm
      ? `<div class="confirm" style="margin:0 16px 12px">${confirm}<div class="buttons"><button class="chip" data-free-cancel>${esc(t.sendCancel)}</button><button class="chip primary" data-free-confirm>${esc(ok)}</button></div></div>`
      : "");
  }

  _sendersClick(e) {
    const goto = e.target.closest("[data-goto]");
    const tile = e.target.closest("[data-tile]");
    const copyId = e.target.closest("[data-copy-id]");
    if (tile) {
      this._poolSel = tile.dataset.tile === this._poolSel ? "" : tile.dataset.tile;
      this._renderSenderIds();
    }
    if (copyId) {
      navigator.clipboard.writeText(copyId.dataset.copyId).then(() => this._notice(this._t.idCopied, true), () => this._notice(this._t.copyFailed));
      return;
    }
    if (e.target.closest("[data-free-all]")) {
      this._freeing = { all: true, ids: this._sidBlocked };
      this._renderSenderIds();
      this.shadowRoot.querySelector("#senders .confirm")?.scrollIntoView({ block: "center", behavior: "smooth" });
    } else if (goto) {
      // the row of this number in the table below the map
      const rows = [...this.shadowRoot.querySelectorAll("#installation [data-in-row^='snd|']")].filter((r) => r.dataset.inRow.endsWith(`|${goto.dataset.goto}`));
      const row = rows.find((r) => r.dataset.inRow.split("|")[1] === this._pool) ?? rows[0];
      row?.scrollIntoView({ block: "center", behavior: "smooth" });
    } else if (e.target.closest("[data-free-cancel]")) {
      this._freeing = null;
      this._renderSenderIds();
    } else if (e.target.closest("[data-free-confirm]")) {
      this._freeSender();
    }
  }

  async _freeSender() {
    const t = this._t;
    const { id, all, ids } = this._freeing;
    try {
      if (all) {
        const { freed } = await this._hass.callWS({ type: "enocean_eltako/sender_pools/free_all", pool: this._pool, senders: ids });
        this._notice(t.freedMany(freed), true);
      } else {
        await this._hass.callWS({ type: "enocean_eltako/sender_pools/free", pool: this._pool, sender: id });
        this._notice(t.freed, true);
      }
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
        hidden: !r.device && this._isHidden(r.gateway, r.sender), page: info?.ha_device || r.ha_device || null, devKey: info?.key || null, senders: info?.teach || [],
        category: info?.category || "", models: info?.models || [], entityIds: info?.entity_ids || [], eepFull: info?.eep || r.eep || "", eep: this._eepLabel(info?.eep || r.eep || RORG[r.rorg] || r.rorg),
        model: info?.model || (r.eep?.endsWith(":eltako") && r.model) || "", area: info?.area || null, entities: info?.entities ?? null, labels: info?.labels || [], disabled: !!info?.disabled,
        gateway: r.gateway, gateway_name: r.gateway_name, time: Date.parse(r.time), count: d.count, perMinute: d.perMinute,
        dbm: r.dbm, trend: d.dbm, fields: d.fields, data: r.data, teach: d.teach, candidates: d.candidates, rorg: r.rorg,
      });
    }
    for (const d of setup.values()) {
      if (heardIds.has(d.id) || (f.gateway && d.gateway !== f.gateway)) continue;
      items.push({
        key: `quiet|${d.id}`, id: d.id, name: d.device, unknown: false, silent: d.silent, quiet: true, page: d.ha_device || null, devKey: d.key || null, senders: d.teach || [],
        category: d.category || "", models: d.models || [], entityIds: d.entity_ids || [], eepFull: d.eep || "", eep: this._eepLabel(d.eep || ""), model: d.model || "", area: d.area, entities: d.entities, labels: d.labels || [], disabled: !!d.disabled,
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

  _inStatus(d, status) {
    if (status === "known") return !d.unknown;
    if (status === "unknown") return d.unknown && !d.hidden;
    if (status === "silent") return !!d.silent;
    if (status === "unheard") return !d.unknown && !d.disabled && d.time == null;
    if (status === "weak") return d.dbm != null && d.dbm < WEAK_DBM;
    return true;
  }

  _devMatches(d) {
    const f = this._filter;
    if (f.area && d.area !== f.area) return false;
    if (!this._inStatus(d, f.devStatus)) return false;
    const text = f.text.toLowerCase();
    if (!text) return true;
    const compact = text.replace(/[-:\s]/g, "");
    return (
      [d.name, d.eepFull, d.model, d.area, d.gateway_name, d.data, d.teach, ...(d.candidates || []), ...this._labelNames(d)].some((v) => v && String(v).toLowerCase().includes(text)) ||
      (d.fields || []).some((field) => String(field.label).toLowerCase().includes(text)) ||
      (!!compact && d.id.replace(/-/g, "").toLowerCase().includes(compact))
    );
  }

  _deviceList() {
    // filtered and in the chosen order
    const { key, desc } = this._devSort;
    const sorter = DEV_SORTERS[key];
    const items = this._deviceItems().filter((d) => this._devMatches(d)).sort((a, b) => (desc ? sorter(b, a) : sorter(a, b)));
    // grouped: the groups in name order (the ones without a name last), the chosen order inside each
    if (this._devGroup) {
      const name = (d) => this._groupOf(d) || "\uffff";
      items.sort((a, b) => collator.compare(name(a), name(b)));
    }
    // an open row keeps its place: the order is frozen until the last one closes or the sort or filter changes
    const signature = JSON.stringify([this._devSort, this._filter, this._devGroup]);
    if (!this._devOpen.size) {
      this._devOrder = null;
      return items;
    }
    if (!this._devOrder || this._devOrder.signature !== signature) {
      this._devOrder = { signature, keys: items.map((d) => d.key) };
      return items;
    }
    const at = new Map(this._devOrder.keys.map((k, i) => [k, i]));
    const fresh = items.filter((d) => !at.has(d.key));
    return [...items.filter((d) => at.has(d.key)).sort((a, b) => at.get(a.key) - at.get(b.key)), ...fresh];
  }

  _kindName(d) {
    // the kind of device in words: its category, or "unknown sender" for what is not set up
    const t = this._t;
    return d.unknown ? t.unknownDevice : t.doc.tbl.categories[d.category] || t.kindOther;
  }

  _groupOf(d) {
    // the heading a device is listed under; empty: the group of those without one
    return this._devGroup === "area" ? d.area || "" : this._devGroup === "kind" ? this._kindName(d) : "";
  }

  _needsAttention(d) {
    return d.unknown || !!d.silent || (d.dbm != null && d.dbm < WEAK_DBM) || (!d.unknown && !d.disabled && d.time == null);
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
    // the count only says something when a filter narrows the list
    this.shadowRoot.getElementById("count").textContent = total === all.length ? "" : t.devCount(total, all.length);
    this._renderSel(all, devices);
    this._renderPager(total, page.length);
    // the area filter offers the areas in use (and a chosen one that has just emptied)
    const areas = [...new Set([...all.map((d) => d.area).filter(Boolean), ...(this._filter.area ? [this._filter.area] : [])])].sort(collator.compare);
    const areaSelect = this.shadowRoot.getElementById("devArea");
    this._options(areaSelect, [["", t.allAreas], ...areas.map((a) => [a, a])], this._filter.area);
    this.shadowRoot.getElementById("devAreaRow").hidden = !areas.length && !this._filter.area;
    this._syncFilterBtn();
    // each status chip says how many devices it would show (of the gateway chosen, whatever else is filtered)
    for (const button of this.shadowRoot.getElementById("devStatus").querySelectorAll("button")) {
      const status = button.dataset.status;
      const n = all.filter((d) => this._inStatus(d, status)).length;
      const html = `${esc(t.devStatus[status])}<span class="n">${n}</span>`;
      if (button.innerHTML !== html) button.innerHTML = html;
      button.classList.toggle("zero", !n && !!status);
    }
    if (this._hold("devices", container, background) || this._editing()) return;
    if (!page.length) {
      const filtered = all.length > 0;
      this._replace(container, filtered
        ? this._emptyState(ICON.search, t.noMatchTitle, t.noMatchText, `<button class="chip reset">${esc(t.resetFilters)}</button>`)
        : this._emptyState(ICON.tower, t.noDevices, t.noDevicesText));
      return;
    }
    const now = this._now();
    const cols = [["name", t.devCols.name], ["kind", t.devCols.kind], ["values", t.devCols.state], ["heard", t.devCols.heard, "h-heard"]];
    this.shadowRoot.getElementById("devGroup").value = this._devGroup;
    const listed = devices.filter((d) => d.devKey);
    const ticked = listed.filter((d) => this._sel.has(d.devKey)).length;
    const all_ = `<span class="c-sel">${listed.length ? `<input type="checkbox" class="selbox" data-sel-all${listed.length && ticked === listed.length ? " checked" : ""} aria-label="${esc(t.selAll)}">` : ""}</span>`;
    const head = `<div class="dev-head">${all_}${cols
      .map(([key, label, cls]) => {
        if (!DEV_SORTERS[key]) return `<span>${esc(label)}</span>`;
        const state = this._devSort.key === key ? ` aria-sort="${this._devSort.desc ? "descending" : "ascending"}"` : "";
        return `<span class="${cls || ""}"><button data-dsort="${key}"${state} aria-label="${esc(`${t.sortHint}: ${label}`)}">${esc(label)}${svg(ICON.chevron, "sort")}</button></span>`;
      })
      .join("")}<span></span></div>`;
    // the page in groups: a heading per group with its count and how many there need a look
    let body = "";
    if (this._devGroup) {
      const groups = new Map();
      for (const d of page) {
        const name = this._groupOf(d);
        if (!groups.has(name)) groups.set(name, []);
        groups.get(name).push(d);
      }
      for (const [name, list] of groups) {
        const key = `${this._devGroup}:${name}`;
        const folded = this._devCollapsed.has(key);
        const attention = list.filter((d) => this._needsAttention(d)).length;
        const title = name || (this._devGroup === "area" ? t.noArea : t.kindOther);
        body += `<div class="dgroup" role="button" tabindex="0" data-dgroup="${esc(key)}" aria-expanded="${!folded}">${svg(ICON.chevron, "chev")}<b>${esc(title)}</b><span class="sub">${esc(t.devicesN(list.length))}${attention ? ` · <span class="attn">${esc(t.needAttention(attention))}</span>` : ""}</span></div>`;
        if (!folded) body += list.map((d) => this._deviceRow(d, now)).join("");
      }
    } else {
      body = page.map((d) => this._deviceRow(d, now)).join("");
    }
    this._replace(container, head + body);
    const headBox = container.querySelector("[data-sel-all]");
    if (headBox) headBox.indeterminate = ticked > 0 && ticked < listed.length;
  }

  _labelNames(d) {
    return (d.labels || []).map((id) => this._labels.find((l) => l.label_id === id)?.name).filter(Boolean);
  }

  async _loadRegistries() {
    // the areas and labels of Home Assistant: for the chips, the search and the forms of the selection
    try {
      const [areas, labels] = await Promise.all([this._hass.callWS({ type: "config/area_registry/list" }), this._hass.callWS({ type: "config/label_registry/list" })]);
      this._areas = areas;
      this._labels = labels;
    } catch (err) {
      // the lists stay as they were
    }
  }

  _selected() {
    const seen = new Set();
    return this._deviceItems().filter((d) => d.devKey && this._sel.has(d.devKey) && !seen.has(d.devKey) && seen.add(d.devKey));
  }

  _toggleSel(key, on) {
    if (on) this._sel.add(key);
    else this._sel.delete(key);
    this._render();
  }

  _selectAll(on) {
    for (const d of this._deviceList()) {
      if (!d.devKey) continue;
      if (on) this._sel.add(d.devKey);
      else this._sel.delete(d.devKey);
    }
    this._render();
  }

  _clearSel() {
    this._sel.clear();
    this._pick = null;
    this._render();
  }

  _renderSel(all, devices) {
    // the bar over the list: what can be done with the ticked devices; the "select all" box in the header line
    const t = this._t;
    const $ = (id) => this.shadowRoot.getElementById(id);
    const present = new Set(all.filter((d) => d.devKey).map((d) => d.devKey));
    for (const key of this._sel) if (!present.has(key)) this._sel.delete(key);
    const listed = devices.filter((d) => d.devKey);
    const ticked = listed.filter((d) => this._sel.has(d.devKey)).length;
    $("selAllRow").hidden = !listed.length;
    const box = $("selAll");
    box.checked = !!listed.length && ticked === listed.length;
    box.indeterminate = ticked > 0 && ticked < listed.length;
    const items = all.filter((d) => d.devKey && this._sel.has(d.devKey));
    if (!items.length) this._pick = null;
    const bar = $("selBar");
    bar.hidden = !items.length;
    $("panel").toggleAttribute("data-picked", items.length > 0);
    $("pickForm").hidden = !this._pick;
    if (!items.length) return;
    const off = items.every((d) => d.disabled);
    this._replace(bar, `<span class="count">${esc(t.selCount(items.length))}</span>
      <button class="chip" data-sel-act="area" aria-expanded="${this._pick === "area"}">${svg(ICON.pin)}${esc(t.selArea)}</button>
      <button class="chip" data-sel-act="labels" aria-expanded="${this._pick === "labels"}">${svg(ICON.label)}${esc(t.selLabel)}</button>
      <button class="chip" data-sel-act="toggle">${svg(off ? ICON.play : ICON.pause)}${esc(off ? t.selEnable : t.selDisable)}</button>
      <span class="grow"></span>
      <button class="chip" data-sel-act="clear">${esc(t.selClear)}</button>
      <button class="chip danger" data-sel-act="remove" aria-expanded="${this._pick === "remove"}">${svg(ICON.clear)}${esc(t.selRemove)}</button>`);
  }

  async _openPick(kind) {
    this._pick = kind && this._pick !== kind ? kind : null;
    if (this._pick === "area" || this._pick === "labels") await this._loadRegistries();
    this._renderPick();
    this._renderSel(this._deviceItems(), this._deviceList());
    this.shadowRoot.getElementById("pickForm").querySelector("select, input, button")?.focus();
  }

  _renderPick(draft) {
    const t = this._t;
    const form = this.shadowRoot.getElementById("pickForm");
    const items = this._selected();
    form.hidden = !this._pick || !items.length;
    if (form.hidden) return;
    const active = this.shadowRoot.activeElement;
    if (active && form.contains(active)) active.blur(); // the form is drawn anew: focus leaves it first
    const n = items.length;
    const buttons = (label, cls = "primary") => `<div class="buttons"><button class="chip" type="button" data-pick-cancel>${esc(t.sendCancel)}</button><button class="chip ${cls}" type="submit">${esc(label)}</button></div>`;
    if (this._pick === "area") {
      const areas = [...this._areas].sort((a, b) => collator.compare(a.name, b.name));
      form.innerHTML = `<h3>${esc(t.areaTitle(n))}</h3><div class="fields"><label><span>${esc(t.devCols.area)}</span><select class="select" id="pickArea">
        <option value="__keep">${esc(t.areaKeep)}</option><option value="">${esc(t.areaNone)}</option>${areas.map((a) => `<option value="${esc(a.area_id)}">${esc(a.name)}</option>`).join("")}</select></label></div>${buttons(t.pickApply)}`;
    } else if (this._pick === "labels") {
      const labels = [...this._labels].sort((a, b) => collator.compare(a.name, b.name));
      const rows = labels
        .map((l) => {
          const c = items.filter((d) => d.labels.includes(l.label_id)).length;
          const state = draft?.get(l.label_id) || { checked: c === n, indeterminate: c > 0 && c < n };
          return `<label class="check"><input type="checkbox" data-label="${esc(l.label_id)}" data-indeterminate="${state.indeterminate}"${state.checked ? " checked" : ""}><span>${esc(l.name)}</span><small>${c}/${n}</small></label>`;
        })
        .join("");
      form.innerHTML = `<h3>${esc(t.labelTitle(n))}</h3><p>${esc(t.labelHint)}</p>${rows ? `<div class="picklist">${rows}</div>` : `<p>${esc(t.labelNone)}</p>`}
        <div class="newlabel"><label><span>${esc(t.labelNew)}</span><input class="text" id="pickNew" autocomplete="off" maxlength="64"></label><button class="chip" type="button" data-pick-new>${esc(t.labelCreate)}</button></div>
        <div class="err" id="pickErr" role="alert" hidden></div>${buttons(t.pickApply)}`;
      for (const cb of form.querySelectorAll("[data-label]")) cb.indeterminate = cb.dataset.indeterminate === "true";
    } else {
      const named = items.map((d) => `<li>${esc(d.name || d.id)} <span class="mono">${esc(d.id)}</span></li>`).join("");
      form.innerHTML = `<h3>${esc(t.rmTitle(n))}</h3><ul class="names">${named}</ul><p>${esc(t.rmText)}</p><p>${esc(t.rmBlocked)}</p>${buttons(t.rmRun(n), "primary danger")}`;
    }
  }

  async _createLabel() {
    const t = this._t;
    const form = this.shadowRoot.getElementById("pickForm");
    const input = form.querySelector("#pickNew");
    const err = form.querySelector("#pickErr");
    const name = input.value.trim();
    if (!name) {
      err.textContent = t.labelNameEmpty;
      err.hidden = false;
      input.focus();
      return;
    }
    const draft = new Map([...form.querySelectorAll("[data-label]")].map((cb) => [cb.dataset.label, { checked: cb.checked, indeterminate: cb.indeterminate }]));
    try {
      const label = await this._hass.callWS({ type: "config/label_registry/create", name });
      this._labels = [...this._labels, label];
      draft.set(label.label_id, { checked: true, indeterminate: false });
    } catch (e) {
      err.textContent = e.message || t.selFailed(1);
      err.hidden = false;
      return;
    }
    this._renderPick(draft);
    this.shadowRoot.getElementById("pickNew")?.focus();
  }

  async _bulkDevices(items, update, message) {
    // Home Assistant's own device registry does the area, labels and disabling; devices not in it are skipped
    let failed = 0;
    for (const d of items) {
      const patch = d.page ? update(d) : null;
      if (!patch) continue;
      try {
        await this._hass.callWS({ type: "config/device_registry/update", device_id: d.page, ...patch });
      } catch (err) {
        failed += 1;
      }
    }
    this._pick = null;
    await this._refreshStatus();
    this._notice(failed ? this._t.selFailed(failed) : message, !failed);
  }

  async _applyPick() {
    const t = this._t;
    const items = this._selected();
    const form = this.shadowRoot.getElementById("pickForm");
    if (this._pick === "area") {
      const area = form.querySelector("#pickArea").value;
      if (area === "__keep") return this._openPick(null);
      return this._bulkDevices(items, () => ({ area_id: area || null }), t.areaDone(items.length));
    }
    if (this._pick === "labels") {
      const wanted = [...form.querySelectorAll("[data-label]")].filter((cb) => !cb.indeterminate).map((cb) => [cb.dataset.label, cb.checked]);
      return this._bulkDevices(
        items,
        (d) => {
          const labels = new Set(d.labels);
          for (const [id, on] of wanted) {
            if (on) labels.add(id);
            else labels.delete(id);
          }
          return labels.size === d.labels.length && d.labels.every((l) => labels.has(l)) ? null : { labels: [...labels] };
        },
        t.labelsDone(items.length)
      );
    }
    if (this._pick === "remove") return this._removeSelected(items);
  }

  _toggleDisabled() {
    const t = this._t;
    const items = this._selected();
    const off = !items.every((d) => d.disabled);
    return this._bulkDevices(items, (d) => (d.disabled === off ? null : { disabled_by: off ? "user" : null }), (off ? t.disabledDone : t.enabledDone)(items.length));
  }

  async _removeSelected(items) {
    const t = this._t;
    const byGateway = new Map();
    for (const d of items) byGateway.set(d.gateway, [...(byGateway.get(d.gateway) || []), d.devKey]);
    this._notice("");
    try {
      for (const [entry_id, devices] of byGateway) await this._hass.callWS({ type: "enocean_eltako/remove_devices", entry_id, devices });
    } catch (err) {
      this._notice(t.rmFailed);
      return;
    } finally {
      this._pick = null;
      this._sel.clear();
      await this._refreshStatus();
    }
    this._notice(t.rmDone(items.length), true);
  }

  _openTeach(key) {
    // the teach-in form above the device list, for one set-up device with sender IDs
    const item = key && this._deviceItems().find((d) => d.devKey === key && d.senders.length);
    this._teaching = item ? { key, gateway: item.gateway, name: item.name, teach: item.senders } : null;
    this._renderTeach();
    if (item) this.shadowRoot.getElementById("teachGo")?.focus();
  }

  _renderTeach() {
    const t = this._t;
    const form = this.shadowRoot.getElementById("teachForm");
    const teaching = this._teaching;
    form.hidden = !teaching;
    if (!teaching) return;
    const chosen = this.shadowRoot.getElementById("teachProfile")?.value;
    const sender = teaching.teach.find((s) => s.profile === chosen) || teaching.teach[0];
    const label = (s) => `${this._profile(s.profile)} · ${s.id}`;
    const pick = teaching.teach.length > 1
      ? `<label><span>${esc(t.teachSender)}</span><select class="select" id="teachProfile">${teaching.teach
          .map((s) => `<option value="${esc(s.profile)}"${s === sender ? " selected" : ""}>${esc(label(s))}</option>`)
          .join("")}</select></label>`
      : `<label><span>${esc(t.teachSender)}</span><span class="mono">${esc(label(sender))}</span></label>`;
    form.innerHTML = `<h3>${esc(t.teachTitle(teaching.name))}</h3><p>${esc(sender.ute ? t.teachUteSteps : t.teachSteps)}</p>
      <div class="fields">${pick}</div>
      <div class="buttons"><button class="chip" type="button" data-teach-cancel>${esc(t.sendCancel)}</button><button class="chip primary" type="submit" id="teachGo">${svg(ICON.teach)}${esc(t.teachSend)}</button></div>`;
    form.dataset.profile = sender.profile;
  }

  async _teachIn() {
    const t = this._t;
    const teaching = this._teaching;
    if (!teaching) return;
    const form = this.shadowRoot.getElementById("teachForm");
    try {
      const result = await this._hass.callWS({ type: "enocean_eltako/teach_in", entry_id: teaching.gateway, device: teaching.key, profile: form.dataset.profile });
      this._notice(result.ute ? t.teachArmed(result.window) : t.teachSent(teaching.name), !result.ute);
      this._openTeach(null);
    } catch (err) {
      this._notice(t.teachFailed);
    }
  }

  _emptyState(icon, title, text = "", action = "", small = false) {
    return `<div class="empty${small ? " small" : ""}"><span class="ico">${svg(icon)}</span><b>${esc(title)}</b>${text ? `<span>${esc(text)}</span>` : ""}${action}</div>`;
  }

  _noGateway() {
    return this._emptyState(ICON.plus, this._t.noGateways, this._t.noGatewaysText, `<button class="chip primary" data-open-integration>${esc(this._t.openIntegration)}</button>`);
  }

  _sparkline(dbm) {
    // the signal of the last telegrams as a curve; the band follows the data (at least 16 dB
    // wide, so a steady sender stays calm), the dashed "weak" line shows only inside the band
    if (dbm.length < 2) return "";
    const [w, h] = [96, 32];
    const lo0 = Math.min(...dbm);
    const hi0 = Math.max(...dbm);
    const span = Math.max(16, hi0 - lo0);
    const lo = (hi0 + lo0) / 2 - span / 2;
    const y = (v) => (h - 3 - ((v - lo) / span) * (h - 6)).toFixed(1);
    const points = dbm.map((v, i) => `${((i / (dbm.length - 1)) * w).toFixed(1)},${y(v)}`).join(" ");
    const title = this._t.trend(dbm.length, lo0, hi0);
    // the colour follows the last value like the bars
    const last = dbm[dbm.length - 1];
    const tone = last >= -80 ? "ok" : last >= -90 ? "warn" : "bad";
    const end = points.slice(points.lastIndexOf(" ") + 1).split(",");
    const weak = WEAK_DBM > lo && WEAK_DBM < lo + span ? `<line class="weak" x1="0" x2="${w}" y1="${y(WEAK_DBM)}" y2="${y(WEAK_DBM)}"/>` : "";
    return `<svg class="spark ${tone}" viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" role="img" aria-label="${esc(title)}"><title>${esc(title)}</title>${weak}<polyline points="${points}"/><circle cx="${end[0]}" cy="${end[1]}" r="3"/></svg>`;
  }

  _stateValues(d) {
    // a device with no telegram in the buffer: what its entities hold, the first two that have a value
    const states = this._hass?.states ?? {};
    return d.entityIds
      .map((id) => states[id])
      .filter((st) => st && !["unavailable", "unknown"].includes(st.state))
      .slice(0, 2)
      .map((st) => {
        const text = this._hass.formatEntityState ? this._hass.formatEntityState(st) : `${st.state}${st.attributes?.unit_of_measurement ? ` ${st.attributes.unit_of_measurement}` : ""}`;
        return `<span class="value" title="${esc(st.attributes?.friendly_name ?? st.entity_id)}"><b>${esc(text)}</b></span>`;
      })
      .join("");
  }

  _deviceRow(d, now) {
    const t = this._t;
    const name = d.unknown ? `<span class="name unknown">${esc(t.unknownDevice)}</span>` : `<span class="name" title="${esc(d.name)}">${esc(d.name)}</span>`;
    const none = `<span class="none">${esc(t.noValue)}</span>`;
    // a model that is not fixed (one EEP, several devices) names the candidates instead of nothing
    const model = d.model || (d.models.length ? d.models.join(" / ") : "");
    const sub = [`<span class="mono">${esc(d.id)}</span>`, model ? esc(model) : d.eep ? `<span class="mono" title="${esc(d.eepFull)}">${esc(d.eep)}</span>` : "", this._multi ? esc(d.gateway_name) : ""].filter(Boolean).join(" · ");
    const kind = d.unknown ? "unknown" : categoryIcon(d.category) ? d.category : "other";
    const kindName = kind === "unknown" ? t.unknownDevice : t.doc.tbl.categories[kind] || "";
    const tile = `<span class="tile ${kind}" title="${esc(kindName)}" aria-hidden="true">${svg(kind === "unknown" ? ICON.help : categoryIcon(kind) || ICON.tower)}</span>`;
    // phones have no columns: the type and the area go below the ID
    const msub = [esc(this._kindName(d)), d.area ? esc(d.area) : ""].filter(Boolean).join(" · ");
    const values = d.fields && d.fields.length
      ? d.fields
          .map((f) =>
            f.label === "on" || f.label === "state"
              ? `<span class="value"><b>${esc(this._value(f.value))}</b></span>`
              : `<span class="value"><span>${esc(this._label(f.label))}</span> <b>${esc(this._value(f.value))}</b>${f.unit ? ` ${esc(f.unit)}` : ""}</span>`
          )
          .join("")
      : this._stateValues(d) || (d.quiet ? "" : `<span class="raw mono">${esc(d.data)}</span>`);
    // one state per device, the first that applies: a disabled device is not judged by its silence
    const state = d.disabled ? "disabled" : d.unknown ? "unknown" : d.silent ? "silent" : d.time == null ? "unheard" : "active";
    const pill = `<span class="pill ${state}" title="${esc(t.deviceStateHint[state])}">${esc(t.deviceState[state])}</span>`;
    const hints =
      pill +
      (d.unknown
        ? (d.hidden ? `<span class="tag" title="${esc(t.hiddenHint)}">${esc(t.hiddenTag)}</span>` : "") +
          (d.teach ? `<span class="tag teach">${esc(t.teachIn)} ${esc(d.teach)}</span>` : "")
        : "");
    const maybe = d.unknown ? maybeTag(t, d.candidates) : "";
    const weak = d.dbm != null && d.dbm < WEAK_DBM;
    // the state pill already says "not heard": the time column then stays empty
    const heard = d.time != null ? t.ago(Math.max(0, Math.round((now - d.time) / 1000))) : t.noValue;
    const stats = d.quiet
      ? `<span${d.time == null ? ' class="quiet-note"' : ""} title="${esc(t.quietHint)}">${esc(heard)}</span>`
      : `<span class="l1"><span>${esc(heard)}</span><span class="signal">${bars(d.dbm)}<span class="dbm">${d.dbm != null ? `${esc(d.dbm)} dBm` : ""}</span></span>${weak ? `<span class="tag warn" title="${esc(t.weakHint)}">${esc(t.weak)}</span>` : ""}</span>
        `;
    const only = d.name || d.id;
    const open = !!d.devKey && this._devOpen.has(d.devKey);
    // everything but the one main action sits in the ⋮ menu: the buttons of a row stay where they are
    const add = d.unknown && !d.hidden ? `<button class="chip add" data-id="${esc(d.id)}" data-gateway="${esc(d.gateway)}" aria-haspopup="menu" title="${esc(t.addHint)}" aria-label="${esc(t.addHint)}">${svg(ICON.plus)}<span class="lbl">${esc(t.add)}</span></button>` : "";
    const menuTeach = d.senders.length ? d.devKey : "";
    const menuOnly = d.quiet && d.time == null ? "" : only;
    const more =
      menuTeach || d.page || menuOnly || d.devKey
        ? `<button class="icon-btn rowmore" data-rowmore="${esc(d.devKey || d.key)}" data-m-remove="${esc(d.devKey || "")}" data-m-teach="${esc(menuTeach)}" data-m-page="${esc(d.page || "")}" data-m-only="${esc(menuOnly)}" aria-haspopup="menu" title="${esc(t.more)}" aria-label="${esc(t.more)}">${svg(ICON.more)}</button>`
        : "";
    const acts = add + more;
    const chevron = d.devKey ? `<button class="icon-btn expand" data-dev-open="${esc(d.devKey)}" aria-expanded="${open}" aria-label="${esc(t.details)}" title="${esc(t.details)}">${svg(ICON.chevron, "chev")}</button>` : "";
    const picked = !!d.devKey && this._sel.has(d.devKey);
    const box = d.devKey ? `<input type="checkbox" class="selbox" data-sel="${esc(d.devKey)}"${picked ? " checked" : ""} aria-label="${esc(t.selBoxLabel(d.name || d.id))}">` : "";
    return `<div class="dev${d.quiet ? " quiet" : ""}${open ? " open" : ""}${picked ? " picked" : ""}${d.devKey ? " expandable" : ""}" data-key="${esc(d.key)}" data-only="${esc(only)}"${d.devKey ? ` data-dev="${esc(d.devKey)}" data-gateway="${esc(d.gateway)}"` : ""}>
      <div class="c-sel">${box}</div>
      <div class="ident">${tile}<div class="idtext"><div class="line1">${name}</div><div class="sub">${sub}</div>${msub ? `<div class="sub msub">${msub}</div>` : ""}</div></div>
      <div class="c-area"><span>${esc(this._kindName(d))}</span><span class="sub">${d.area ? `${svg(ICON.pin)}${esc(d.area)}` : `<span class="none">${esc(t.noArea)}</span>`}</span></div>
      <div class="values">${hints}${values}${maybe}</div>
      <div class="stats">${stats}</div>
      <div class="acts">${acts}${chevron}</div>
      ${open ? this._devDetail(d, now) : ""}
    </div>`;
  }

  _heardBy(h) {
    // the gateways that hear the device, the strongest first; only shown for several gateways or
    // a device that only a repeater carries
    const t = this._t;
    if (!h || (h.gateways.length < 2 && !h.repeater_only)) return "";
    const rows = h.gateways.map((g) => `<div>${esc(g.name)} <span class="sub">${g.rssi != null ? `${esc(g.rssi)} dBm, ` : ""}${esc(t.heardCount(g.count))}</span>${g.entry_id === h.best ? ` <span class="tag" title="${esc(t.bestHint)}">${esc(t.best)}</span>` : ""}</div>`);
    if (h.repeater_only) rows.push(`<div><span class="tag warn" title="${esc(t.repeaterOnlyHint)}">${esc(t.repeaterOnly)}</span></div>`);
    return rows.join("");
  }

  _devDetail(d, now) {
    const t = this._t;
    const x = this._devDetails.get(d.devKey);
    if (!x) return `<div class="dev-detail"><span class="none">${esc(t.loading)}</span></div>`;
    const none = `<span class="none">${esc(t.noValue)}</span>`;
    const item = (label, html, cls = "") => (html ? `<div${cls ? ` class="${cls}"` : ""}><dt>${esc(label)}</dt><dd>${html}</dd></div>` : "");
    const group = (title, body, count = "") => (body ? `<section class="dsec"><h4>${esc(title)}${count !== "" ? ` <span class="sub">${esc(count)}</span>` : ""}</h4>${body}</section>` : "");
    const list = (items) => `<dl class="dgrid">${items.join("")}</dl>`;
    // rows of three columns (name, detail, value); a foot for actions or raw data
    const rows = (lines, foot = "") => `<div class="rows">${lines.map((r) => `<div class="li${r.cls ? ` ${r.cls}` : ""}">${r.cells.map((c) => `<span>${c}</span>`).join("")}</div>`).join("")}${foot ? `<div class="foot">${foot}</div>` : ""}</div>`;
    const mono = (v) => `<span class="tag mono">${esc(v)}</span>`;
    const heard = d.time != null ? t.ago(Math.max(0, Math.round((now - d.time) / 1000))) : t.notHeard;
    const sig = x.signal;
    const identity = list([
      item(t.model, x.models.length ? this._modelPicker(d.devKey, x) : x.model ? esc(x.model) : ""),
      item(t.eep, x.eep ? mono([x.eep, ...x.eep_extra].join(", ")) : ""),
      item(t.devCols.kind, esc(this._kindName(d))),
      item(t.devCols.area, d.area ? esc(d.area) : ""),
      item(t.selLabel, this._labelNames(d).length ? `<div class="labels">${this._labelNames(d).map((l) => `<span class="tag">${esc(l)}</span>`).join("")}</div>` : ""),
      item(t.gateway, esc(x.gateway_name)),
      item(t.devId, mono(d.id)),
    ]);
    const radio = list([
      item(t.devCols.heard, esc(heard) + (x.silent ? ` <span class="tag warn" title="${esc(t.silentHint)}">${esc(t.silent)}</span>` : "")),
      item(t.signal, sig.rssi != null ? `${esc(sig.rssi)} dBm${sig.min != null ? ` <span class="sub">${esc(t.signalRange(sig.min, sig.max))}</span>` : ""}` : ""),
      item(t.repeater, x.repeat != null ? esc(x.repeat) : ""),
      item(t.telegramsSinceStart, `${esc(x.telegrams.toLocaleString())}${d.perMinute ? ` <span class="sub">${esc(d.perMinute)}/min</span>` : ""}`),
      item(t.interval, x.interval ? esc(t.minutes(Math.round(x.interval / 60))) : ""),
      item(t.heardBy, this._heardBy(x.heard_by), "full"),
      ...(x.last_telegrams ?? []).map((l) => item(x.last_telegrams.length > 1 ? `${t.lastTelegram} ${l.sender}` : t.lastTelegram, this._lastTelegram(l, now), "full")),
    ]);
    // the last values: what the live telegram says, else what the server read from the last
    // telegram of each ID (a restart in between); raw bytes only when nothing could be read
    const fieldRow = (f, source) => ({ cls: "value", cells: [`<span class="k">${esc(f.label === "on" || f.label === "state" ? t.devState : this._label(f.label))}</span>`, source ? `<span class="sub">${esc(source)}</span>` : "", `<b>${esc(this._value(f.value))}${f.unit ? ` ${esc(f.unit)}` : ""}</b>`] });
    const live = (d.fields ?? []).map((f) => fieldRow(f, [d.rorg ? RORG[d.rorg] || d.rorg : "", d.eep].filter(Boolean).join(" · ")));
    const stored = live.length ? [] : (x.last_telegrams ?? []).flatMap((l) => (l.fields ?? []).map((f) => fieldRow(f, [RORG[l.rorg] || l.rorg, x.last_telegrams.length > 1 ? l.sender : ""].filter(Boolean).join(" · "))));
    const rawTags = [
      d.data ? `<span class="tag mono">${esc([d.rorg ? RORG[d.rorg] || d.rorg : "", d.data].filter(Boolean).join(" "))}</span>` : "",
      ...(live.length ? [] : (x.last_telegrams ?? []).map((l) => `<span class="tag mono">${esc(`${RORG[l.rorg] || l.rorg} ${l.data.match(/../g)?.join(" ") ?? ""}`)}</span>`)),
    ].filter(Boolean);
    const valueRows = [...live, ...stored];
    const raw = rawTags.length && !x.last_telegrams?.length ? `<span class="sub">${esc(t.rawData)}</span>${[...new Set(rawTags)].join("")}` : "";
    const values = valueRows.length ? rows(valueRows, raw) : raw ? rows([], raw) : "";
    const test = this._senderTests.get(d.devKey) || {};
    const verdict = (profile) => {
      const result = test.results?.[profile];
      return result ? `<span class="tag ${result === "confirmed" ? "ok" : "warn"}" title="${esc(t.senderTestResultHint[result] || "")}">${esc(t.senderTestResult[result] || result)}</span>` : "";
    };
    const senders = x.senders.length
      ? rows(
          x.senders.map((s) => ({ cells: [esc(this._profile(s.profile)), `${mono(s.id)} <span class="sub">${esc(s.ute ? t.teachUte : t.teachTelegram)}</span>`, verdict(s.profile) || `<span class="sub">${esc(t.senderUntested)}</span>`] })),
          x.sender_test ? `<div class="acts-row"><button class="chip text" data-sender-test="${esc(d.devKey)}" data-gateway="${esc(x.entry_id)}" title="${esc(t.senderTestHint)}"${test.running ? " disabled" : ""}>${esc(test.running ? t.senderTesting : t.senderTest)}</button>${test.error ? ` <span class="tag warn">${esc(test.error)}</span>` : ""}</div>` : ""
        )
      : "";
    const c = x.commands;
    const commands = c && c.sent
      ? list([
          item(t.cmdSent, esc(c.sent)),
          item(t.cmdConfirmed, `${esc(c.confirmed)}${c.rate != null ? ` <span class="tag ${c.rate < 90 ? "warn" : "ok"}">${esc(c.rate.toLocaleString(undefined, { maximumFractionDigits: 1 }))} %</span>` : ""}`),
          item(t.cmdLatency, c.latency_avg != null ? esc(t.latency(c.latency_avg, c.latency_max)) : ""),
        ])
      : "";
    const yes = (v) => (v === true ? t.yes : v === false ? t.no : v);
    const settings = Object.entries(x.settings).length
      ? rows(Object.entries(x.settings).map(([k, v]) => ({ cells: [`<span class="k">${esc(t.settingNames[k] || k)}</span>`, "", `<b>${esc(yes(v))}</b>`] })))
      : "";
    const entities = x.entities.length
      ? rows(x.entities.map((e) => ({ cells: [esc(e.name), `<span class="mono sub">${esc(e.entity_id)}</span>`, e.state != null ? `<b>${esc(this._entityState(e, now))}</b>` : ""] })))
      : "";
    const only = d.name || d.id;
    const actions = `<div class="dact">${d.page ? `<button class="chip" data-device-page="${esc(d.page)}">${svg(ICON.open)}${esc(t.openDevice)}</button>` : ""}${
      d.quiet && d.time == null ? "" : `<button class="chip" data-only="${esc(only)}">${svg(ICON.filter)}${esc(t.showTelegrams)}</button>`
    }${d.senders.length ? `<button class="chip" data-teach="${esc(d.devKey)}">${svg(ICON.teach)}${esc(t.teach)}</button>` : ""}${d.name ? `<button class="chip" data-dev-links="${esc(d.name)}" title="${esc(t.showLinksHint)}">${svg(ICON.list)}${esc(t.showLinks)}</button>` : ""}</div>`;
    return `<div class="dev-detail">${group(t.dIdentity, identity)}${group(t.dRadio, radio)}${group(t.devCols.values, values)}${group(t.dSenders, senders, x.senders.length || "")}${group(t.dCommands, commands)}${group(t.dSettings, settings)}${group(t.dEntitiesTitle, entities, x.entities.length || "")}${group(t.doc.notes, `<input class="note" data-note-device="${esc(d.devKey)}" data-note-gateway="${esc(x.entry_id)}" value="${esc(x.note)}" maxlength="500" placeholder="${esc(t.doc.notePlaceholder)}" aria-label="${esc(t.doc.notes)}" autocomplete="off">`)}${actions}</div>`;
  }

  _entityState(e, now) {
    // a state as people read it: a time as "ago", a number in the language's format, on / off translated
    const t = this._t;
    const lang = this._hass?.language || "en";
    if (e.device_class === "timestamp" && !Number.isNaN(Date.parse(e.state))) {
      return t.ago(Math.max(0, Math.round((now - Date.parse(e.state)) / 1000)));
    }
    if (t.stateWords[e.state] !== undefined) return t.stateWords[e.state];
    const n = Number(e.state);
    const shown = e.state !== "" && Number.isFinite(n) ? n.toLocaleString(lang, { maximumFractionDigits: 3 }) : e.state;
    return `${shown}${e.unit ? ` ${e.unit}` : ""}`;
  }

  _modelPicker(key, x) {
    // the type is not told by the radio: a pick from the kind's models, or a model typed in
    const t = this._t;
    const custom = x.model_name && !x.models.includes(x.model_name);
    const options = [["", t.modelNone], ...x.models.map((m) => [m, m]), ...(custom ? [[x.model_name, x.model_name]] : []), ["__other", t.modelOther]];
    const select = `<select class="select mini" data-model-for="${esc(key)}" aria-label="${esc(t.model)}">${options
      .map(([v, label]) => `<option value="${esc(v)}"${v === x.model_name ? " selected" : ""}>${esc(label)}</option>`)
      .join("")}</select>`;
    return `${select}<input class="mini" data-model-text="${esc(key)}" placeholder="${esc(t.modelPlaceholder)}" maxlength="64" autocomplete="off" hidden>${x.model_name ? "" : `<div class="sub">${esc(t.modelUnknown)}</div>`}`;
  }

  async _saveModel(key, modelName) {
    const gateway = this._deviceItems().find((d) => d.devKey === key)?.gateway;
    if (!gateway) return;
    this._notice("");
    try {
      await this._hass.callWS({ type: "enocean_eltako/set_model", entry_id: gateway, device: key, model_name: modelName });
    } catch (err) {
      this._notice(this._t.modelFailed);
      return;
    }
    const x = this._devDetails.get(key);
    if (x) Object.assign(x, { model_name: modelName, model: modelName });
    this._render();
  }

  // a select or text box being used in an opened row keeps the list from being redrawn under it
  _editing() {
    const active = this.shadowRoot.activeElement;
    return !!active && !!active.closest?.(".dev-detail") && active.matches("select, input");
  }

  _inPanel(devKey) {
    // a set-up device with telegrams of its own has a row in the Devices view
    return this._deviceItems().some((d) => d.devKey === devKey);
  }

  _showDevice(devKey) {
    // the Devices view with this device's row opened, on the page it is on
    let list = this._deviceList();
    if (!list.some((d) => d.devKey === devKey)) {
      this._resetFilters(); // a filter hides it
      list = this._deviceList();
    }
    const item = this._deviceItems().find((d) => d.devKey === devKey);
    if (!item) return;
    if (!this._devOpen.has(devKey)) {
      this._devOpen.add(devKey);
      this._loadDevDetail(devKey, item.gateway);
    }
    this._setView("devices");
    const at = this._deviceList().findIndex((d) => d.devKey === devKey);
    this._offset = at > 0 ? Math.floor(at / this._pageSize) * this._pageSize : 0;
    this._render();
    requestAnimationFrame(() => this.shadowRoot.querySelector(`.dev[data-dev="${CSS.escape(devKey)}"]`)?.scrollIntoView({ block: "center", behavior: "smooth" }));
  }

  async _testSenders(key, gateway) {
    // the actuator's current state through each sender in turn; the answer shows who it knows
    if (this._senderTests.get(key)?.running) return;
    this._senderTests.set(key, { running: true });
    this._render(true);
    try {
      const reply = await this._hass.callWS({ type: "enocean_eltako/sender_test", entry_id: gateway, device: key });
      this._senderTests.set(key, { results: Object.fromEntries(reply.results.map((r) => [r.profile, r.result])) });
    } catch (err) {
      this._senderTests.set(key, { error: this._t.senderTestError[err.code] || this._t.senderTestError.failed });
    }
    if (this._view === "devices") this._render(true);
  }

  async _loadDevDetail(key, gateway) {
    try {
      this._devDetails.set(key, await this._hass.callWS({ type: "enocean_eltako/device_details", entry_id: gateway, device: key }));
    } catch (err) {
      return; // reloading or gone: the next status update tries again
    }
    if (this._view === "devices") this._render(true);
  }

  _toggleDev(key, gateway) {
    if (this._devOpen.has(key)) this._devOpen.delete(key);
    else {
      this._devOpen.add(key);
      this._loadDevDetail(key, gateway);
    }
    this._render();
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
    const typing = this.shadowRoot.activeElement?.matches?.("input.note") && container.contains(this.shadowRoot.activeElement);
    this._stale[name] = background && (typing || this._selecting(container)); // or typing a note
    return this._stale[name];
  }

  _replace(container, html) {
    // redraw, keeping the keyboard focus on the same button of the same row or card
    if (this._drawn.get(container) === html) return;
    this._drawn.set(container, html);
    let active = null;
    try {
      active = this.shadowRoot.activeElement;
    } catch (err) {
      // the focused element was removed by the last redraw (happy-dom throws here)
    }
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

customElements.define("enocean-eltako-monitor", EnOceanEltakoPanel);
