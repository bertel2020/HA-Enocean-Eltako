// The Bus view of the Installation (Devices > Bus): the Eltako bus as it is documented, grouped by
// its master (FAM14), not by gateway. A gateway appears as the way Home Assistant reaches the bus
// (a FAM-USB by radio, an FGW14-USB on the bus). One row per module (the device on the DIN rail)
// with its channels, the address plan, the power supplies, the checks of the server, the cabinets
// with their rows, and a drawer for a module, a channel, a sender or the bus. Everything comes
// from the documentation command (installation, installation_checks, bus_types); edits go to
// installation/set and installation/remove. Its methods are added to the panel (this = the panel).

const VERSION = new URL(import.meta.url).search;
const { esc, svg, ICON } = await import(`./shared.js${VERSION}`);

const SUBS = ["list", "addresses", "supplies", "checks", "cabinets", "read"];
const LISTEN = [0, 30, 60, 120]; // seconds a reading of the bus may listen
const ADDRESSES = 126;
const RESERVE = 2 / 3; // the mark of the load bar: from here another supply is advised
const NEXT = ["", "bbv14", "fba14", "cable"];
const LEVELS = ["error", "warning", "info"];
const OFF = ["foreign", "accessory"]; // on the rail, not on the bus
const typeKey = (type) => String(type ?? "").replace(/\s+/g, "").toUpperCase();
const fmtNum = (n) => String(n).replace(".", ",");
const watts = (text) => (/^\d{1,4}([.,]\d{1,3})?$/.test(String(text ?? "").trim()) ? Number(String(text).trim().replace(",", ".")) : null);

const LIST_KEY = "enocean_eltako_bus_list"; // sorting and filters of the bus list, per browser
const LIST_DEFAULT = { sort: "address", dir: 1, f: "", role: "", place: "" };
const loadList = () => {
  try {
    const saved = JSON.parse(localStorage.getItem(LIST_KEY));
    if (saved && typeof saved === "object") return { ...LIST_DEFAULT, ...saved, dir: saved.dir === -1 ? -1 : 1 };
  } catch (err) {
    // no storage: the default
  }
  return { ...LIST_DEFAULT };
};
const saveList = (list) => {
  try {
    localStorage.setItem(LIST_KEY, JSON.stringify(list));
  } catch (err) {
    // not saved: shown for this visit
  }
};

const COLS_KEY = "enocean_eltako_bus_columns"; // the columns of the bus list, per browser
const LIST_COLUMNS = ["address", "device", "place", "ha", "senders", "feedback", "power", "supply"];
const LIST_FIXED = ["address", "device"];
const loadCols = () => {
  try {
    const saved = JSON.parse(localStorage.getItem(COLS_KEY));
    if (Array.isArray(saved)) return new Set(saved.filter((c) => LIST_COLUMNS.includes(c)));
  } catch (err) {
    // no storage: all columns
  }
  return new Set(LIST_COLUMNS);
};
const saveCols = (cols) => {
  try {
    localStorage.setItem(COLS_KEY, JSON.stringify([...cols]));
  } catch (err) {
    // not saved: shown for this visit
  }
};

export const busState = () => ({ id: "", sub: "list", list: loadList(), cols: loadCols(), drawer: null, history: [], error: "", legacyOpen: false, draft: null, dirty: false, saving: false, cabinet: "", hl: "", cab: "", arrange: false, cabEdit: false, optIn: false, seconds: 60, listening: null, left: 0 });

// the DIN rail drawn to scale in TE (one grid column is half a TE): in the panel and in the print
export const RAIL_CSS = `
  .bvr-row { display: grid; gap: 6px; border-radius: 8px; padding: 2px; }
  .bvr-row.hl { box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 45%, transparent); }
  .bvr-label { display: flex; gap: 8px; align-items: baseline; flex-wrap: wrap; font-size: calc(13px * var(--fs, 1)); }
  .bvr-label b { font-weight: 500; }
  .bvr-wrap { overflow-x: auto; padding-bottom: 4px; }
  .bvr-rail { position: relative; isolation: isolate; display: grid; grid-template-columns: repeat(var(--cols), minmax(20px, 1fr)); grid-template-rows: auto 20px; min-width: calc(var(--cols) * 20px); border-radius: 6px; background-color: var(--soft); background-image: linear-gradient(to right, var(--line) 1px, transparent 1px); background-size: calc(100% / (var(--cols) / 2)) 100%; padding-top: 6px; border: 1px solid var(--line); }
  .bvr-rail::before { content: ""; position: absolute; left: 0; right: 0; top: 46%; height: 14px; transform: translateY(-50%); background: linear-gradient(var(--line), var(--line-2, var(--line))); z-index: 0; }
  .bvr-tile { position: relative; z-index: 1; grid-row: 1; margin: 0 1px; min-height: 150px; border-radius: 5px; border: 1px solid color-mix(in srgb, var(--k) 45%, var(--line)); background: color-mix(in srgb, var(--k) 12%, var(--surface)); display: flex; flex-direction: column; align-items: center; gap: 4px; padding: 5px 2px 26px; text-align: center; overflow: hidden; color: var(--text); font: inherit; box-sizing: border-box; min-width: 0; }
  button.bvr-tile { cursor: pointer; }
  button.bvr-tile:hover { border-color: var(--k); }
  button.bvr-tile:focus-visible { outline: 2px solid var(--focus); outline-offset: 1px; }
  .bvr-tile.doc { border-style: dashed; }
  .bvr-tile.master { background: color-mix(in srgb, var(--k) 22%, var(--surface)); border-width: 2px; }
  .bvr-tile.foreign { background: repeating-linear-gradient(45deg, var(--soft) 0 6px, var(--surface) 6px 12px); border-style: dashed; border-color: var(--input-line, var(--line)); }
  .bvr-tile.hl { box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 60%, transparent); }
  .bvr-adr { font-family: ui-monospace, monospace; font-size: 11px; font-weight: 600; padding: 0 4px; border-radius: 6px; background: var(--surface); border: 1px solid var(--line); white-space: nowrap; }
  .bvr-adr.none { color: var(--warn); border-color: var(--warn-line, var(--warn)); }
  .bvr-type { writing-mode: vertical-rl; transform: rotate(180deg); font-size: 12px; font-weight: 600; flex: 1; white-space: nowrap; }
  .bvr-tile.wide .bvr-type { writing-mode: horizontal-tb; transform: none; flex: 0; padding-top: 6px; white-space: normal; overflow-wrap: anywhere; }
  .bvr-lbl { font-size: 11px; color: var(--muted); line-height: 1.2; }
  .bvr-leds { display: flex; flex-direction: column; gap: 3px; align-items: center; }
  .bvr-tile.wide .bvr-leds { flex-direction: row; }
  .bvr-led { width: 9px; height: 9px; border-radius: 50%; border: 1.5px solid var(--k); background: var(--k); box-sizing: border-box; display: inline-block; }
  .bvr-led.doc { background: transparent; border-style: dashed; }
  .bvr-led.free { background: transparent; border-color: var(--input-line, var(--line)); }
  .bvr-flag { position: absolute; top: 3px; right: 3px; width: 9px; height: 9px; border-radius: 50%; background: var(--warn); }
  .bvr-flag.bad { background: var(--bad); }
  .bvr-mtag { font-size: 10px; font-weight: 600; color: var(--on-accent, #fff); background: var(--k); border-radius: 6px; padding: 0 5px; }
  .bvr-spacer { grid-row: 1; z-index: 1; margin: 0 1px; min-height: 150px; border-radius: 4px; border: 1px dashed var(--input-line, var(--line)); background: repeating-linear-gradient(90deg, transparent 0 3px, var(--line) 3px 4px); display: grid; place-items: center; }
  .bvr-spacer span { writing-mode: vertical-rl; transform: rotate(180deg); font-size: 10px; color: var(--muted); }
  .bvr-tb { grid-row: 1; z-index: 2; justify-self: end; width: 0; border-right: 3px dashed var(--bad); margin-right: -2px; position: relative; }
  .bvr-tb span { position: absolute; bottom: 30px; left: 4px; font-size: 10px; font-weight: 600; color: var(--bad); background: var(--surface); padding: 0 3px; border-radius: 4px; white-space: nowrap; }
  .bvr-term { grid-row: 1; z-index: 2; align-self: center; justify-self: start; font-size: 10px; padding: 2px 4px; margin-left: 4px; border-radius: 4px; background: var(--surface); border: 1px solid var(--input-line, var(--line)); white-space: nowrap; }
  .bvr-band { grid-row: 2; align-self: center; height: 16px; margin: 0 1px; border-radius: 4px; font: inherit; font-size: 10px; line-height: 16px; padding: 0 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; border: 0; text-align: left; background: color-mix(in srgb, var(--sec) 22%, transparent); color: color-mix(in srgb, var(--sec) 75%, var(--text)); }
  button.bvr-band { cursor: pointer; }
  .bvr-band.bad { background: color-mix(in srgb, var(--bad) 25%, transparent); color: var(--bad); }
  .bvr-moves { grid-row: 1; align-self: end; z-index: 3; display: flex; justify-content: center; gap: 2px; padding-bottom: 4px; pointer-events: none; }
  .bvr-moves button { pointer-events: auto; }
  .bvr-moves button { width: 22px; height: 22px; padding: 0; border-radius: 50%; border: 1px solid var(--input-line, var(--line)); background: var(--surface); color: var(--text); cursor: pointer; font-size: 11px; line-height: 1; }
  .bvr-moves button:hover { border-color: var(--accent); color: var(--accent); }
  .bvr-foot { font-size: 12px; color: var(--muted); display: flex; gap: 10px; flex-wrap: wrap; }
  .bvr-legend { display: flex; gap: 12px; flex-wrap: wrap; font-size: 12px; color: var(--muted); align-items: center; }
  .bvr-legend i { display: inline-block; vertical-align: middle; margin-right: 4px; }
  [data-r="master"], [data-r="gateway"] { --k: var(--k-bus, #2f6fb5); }
  [data-r="actuator"] { --k: var(--k-aktor, #d77f1f); }
  [data-r="meter"] { --k: var(--k-sensor, #139a87); }
  [data-r="input"] { --k: var(--k-taster, #7b5cc9); }
  [data-r="supply"], [data-r="foreign"], [data-r="accessory"], [data-r="other"] { --k: var(--k-psu, #6b7b8d); }`;
const SECTION_COLORS = ["var(--k-bus)", "var(--k-aktor)", "var(--k-sensor)", "var(--k-taster)"];

export const BUS_STYLE = `
  .installation .bv-head { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 10px; }
  .installation .bv-card { border: 1px solid var(--line); border-radius: 12px; padding: 10px 14px; display: grid; gap: 4px; background: var(--surface); min-width: 0; }
  .installation .bv-card.master { border-left: 3px solid var(--k-bus); }
  .installation .bv-card.access { border-left: 3px solid var(--input-line); }
  .installation .bv-role { font-size: calc(11px * var(--fs)); text-transform: uppercase; letter-spacing: .04em; color: var(--muted); }
  .installation .bv-card b { font-weight: 500; }
  .installation .bv-bar { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
  .installation .bv-bar .grow { flex: 1 1 auto; }
  .installation button.bv-lnk { all: unset; cursor: pointer; color: var(--accent); overflow-wrap: anywhere; }
  .installation button.bv-lnk:hover { text-decoration: underline; }
  .installation button.bv-lnk:focus-visible { outline: 2px solid var(--focus); border-radius: 3px; }
  .installation button.tile { text-align: left; font: inherit; color: inherit; border-top: 0; border-right: 0; border-bottom: 0; cursor: pointer; }
  .installation .tile .bv-sub { display: block; font-size: calc(12px * var(--fs)); font-weight: 400; color: var(--muted); }
  .installation .tile.warn { border-left-color: var(--warn); background: color-mix(in srgb, var(--warn) 12%, var(--soft)); }
  .installation .tile.err { border-left-color: var(--bad); background: color-mix(in srgb, var(--bad) 12%, var(--soft)); }
  .installation .bv-cnt { font-size: calc(11px * var(--fs)); font-weight: 500; padding: 0 6px; border-radius: 8px; background: var(--bad-soft); color: var(--bad); margin-left: 4px; }
  .installation .bv-cnt.warn { background: var(--warn-soft); color: var(--warn); }
  .installation [data-r="master"], .installation [data-r="gateway"] { --k: var(--k-bus); }
  .installation [data-r="actuator"] { --k: var(--k-aktor); }
  .installation [data-r="meter"] { --k: var(--k-sensor); }
  .installation [data-r="input"] { --k: var(--k-taster); }
  .installation [data-r="supply"], .installation [data-r="foreign"], .installation [data-r="accessory"], .installation [data-r="other"] { --k: var(--k-psu); }
  .installation .itable tr.bv-mod td { background: color-mix(in srgb, var(--k) 7%, var(--surface)); border-top: 1px solid var(--line); vertical-align: top; }
  .installation .itable tr.bv-mod > td:first-child { box-shadow: inset 3px 0 0 var(--k); }
  .installation .itable tr.bv-ch > td:first-child { box-shadow: inset 3px 0 0 color-mix(in srgb, var(--k) 35%, transparent); }
  .installation .itable tr.bv-ch td { vertical-align: top; }
  .installation .itable tr.bv-unused td { color: var(--muted); font-style: italic; }
  .installation .itable tr.dup td { background: color-mix(in srgb, var(--bad) 10%, var(--surface)); }
  .installation .tag.bad { background: var(--bad-soft); color: var(--bad); }
  .installation .tag.ent { background: var(--accent-soft); color: var(--accent); font-family: ui-monospace, monospace; }
  .installation button.tag.ent:hover { text-decoration: underline; }
  .installation .bv-addr { display: grid; grid-template-columns: repeat(auto-fill, minmax(46px, 1fr)); gap: 4px; }
  .installation .bv-cell { min-height: 44px; border-radius: 6px; border: 1px solid var(--line); background: var(--soft); font-size: calc(11px * var(--fs)); display: grid; align-content: center; justify-items: center; padding: 2px; color: var(--muted); font-family: inherit; }
  .installation .bv-cell b { font-family: ui-monospace, monospace; font-size: calc(12px * var(--fs)); color: var(--text); font-weight: 600; }
  .installation button.bv-cell { cursor: pointer; background: color-mix(in srgb, var(--k) 18%, var(--surface)); border-color: color-mix(in srgb, var(--k) 45%, var(--line)); }
  .installation button.bv-cell.doc { border-style: dashed; }
  .installation button.bv-cell.dup { background: var(--bad-soft); border: 2px solid var(--bad); }
  .installation .bv-cell .t { max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: calc(10px * var(--fs)); }
  .installation .bv-secs { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 12px; }
  .installation .bv-sec { border: 1px solid var(--line); border-left: 4px solid var(--k-psu); border-radius: 12px; padding: 12px 14px; display: grid; gap: 8px; min-width: 0; }
  .installation .bv-sec.over { border-left-color: var(--bad); }
  .installation .bv-sec.reserve { border-left-color: var(--warn); }
  .installation .bv-load { position: relative; height: 12px; border-radius: 6px; background: var(--soft); border: 1px solid var(--line); margin-bottom: 14px; }
  .installation .bv-load i { display: block; height: 100%; border-radius: 6px; background: var(--accent); }
  .installation .bv-load i.reserve { background: var(--warn); }
  .installation .bv-load i.over { background: var(--bad); }
  .installation .bv-load .mark { position: absolute; top: -4px; bottom: -4px; border-left: 2px dotted var(--muted); }
  .installation .bv-load .mark span { position: absolute; top: 14px; left: -10px; font-size: calc(10px * var(--fs)); color: var(--muted); white-space: nowrap; }
  .installation .bv-checks { display: grid; gap: 8px; }
  .installation .bv-check { display: grid; grid-template-columns: 26px minmax(0, 1fr); gap: 10px; padding: 10px 12px; border-radius: 10px; border: 1px solid var(--line); background: var(--surface); }
  .installation .bv-check .ic { width: 26px; height: 26px; border-radius: 50%; display: grid; place-items: center; font-weight: 700; font-size: calc(13px * var(--fs)); }
  .installation .bv-check.error { border-color: var(--bad-line); } .installation .bv-check.error .ic { background: var(--bad-soft); color: var(--bad); }
  .installation .bv-check.warning { border-color: var(--warn-line); } .installation .bv-check.warning .ic { background: var(--warn-soft); color: var(--warn); }
  .installation .bv-check.info .ic { background: var(--accent-soft); color: var(--accent); }
  .installation .bv-check.ok .ic { background: var(--ok-soft); color: var(--ok); }
  .installation .bv-check b { font-weight: 500; }
  .installation .bv-check .chips { margin-top: 4px; }
  .installation .chip.small { min-height: 26px; padding: 0 10px; font-size: calc(12px * var(--fs)); }
  .bv-ask-scrim { position: fixed; inset: 0; background: rgba(0, 0, 0, .4); z-index: 40; display: grid; place-items: center; padding: 16px; }
  .bv-ask { background: var(--surface); color: var(--text); border: 1px solid var(--line); border-radius: 12px; box-shadow: 0 12px 40px var(--shadow-c); padding: 18px; width: min(420px, 100%); display: grid; gap: 12px; }
  .bv-ask h2 { margin: 0; font-size: calc(16px * var(--fs)); font-weight: 600; overflow-wrap: anywhere; }
  .bv-ask p { margin: 0; color: var(--muted); overflow-wrap: anywhere; }
  .bv-ask .bar { display: flex; gap: 8px; justify-content: flex-end; flex-wrap: wrap; }
  .installation .bv-scrim { position: fixed; inset: 0; background: rgba(0, 0, 0, .28); z-index: 20; }
  .installation aside.bv-drawer { position: fixed; top: 0; right: 0; bottom: 0; width: min(540px, 100vw); background: var(--surface); border-left: 1px solid var(--line); box-shadow: -8px 0 24px var(--shadow-c); z-index: 21; display: flex; flex-direction: column; color: var(--text); }
  .installation .bv-dhead { padding: 10px 14px; border-bottom: 1px solid var(--line); display: grid; gap: 6px; }
  .installation .bv-dhead .bar { display: flex; gap: 6px; align-items: center; }
  .installation .bv-dhead .grow { flex: 1; min-width: 0; }
  .installation .bv-dhead h2 { font-size: calc(18px * var(--fs)); font-weight: 500; margin: 0; overflow-wrap: anywhere; }
  .installation .bv-dtitle { display: flex; gap: 8px; align-items: baseline; flex-wrap: wrap; }
  .installation .bv-crumbs { font-size: calc(12px * var(--fs)); color: var(--muted); display: flex; flex-wrap: wrap; gap: 4px; align-items: center; }
  .installation .bv-crumbs .sep { opacity: .6; }
  .installation .bv-dbody { padding: 12px 14px 24px; overflow-y: auto; display: grid; gap: 14px; align-content: start; }
  .installation .bv-ibtn { width: 32px; height: 32px; border-radius: 16px; border: 1px solid var(--line); background: var(--surface); cursor: pointer; display: grid; place-items: center; color: var(--text); padding: 0; font: inherit; }
  .installation .bv-ibtn:hover { background: var(--soft); }
  .installation .bv-ibtn:disabled { opacity: .35; cursor: default; }
  .installation .bv-ibtn svg { width: 18px; height: 18px; }
  .installation dl.bv-kv { display: grid; grid-template-columns: max-content minmax(0, 1fr); gap: 5px 14px; margin: 0; font-size: calc(13px * var(--fs)); }
  .installation dl.bv-kv dt { color: var(--muted); }
  .installation dl.bv-kv dd { margin: 0; min-width: 0; overflow-wrap: anywhere; }
  .installation dl.bv-kv .mono, .installation .bv-chrow .mono { white-space: normal; overflow-wrap: anywhere; }
  .installation .bv-dbody { overflow-x: hidden; }
  .installation .bv-box { border: 1px solid var(--line); border-radius: 10px; padding: 10px 12px; display: grid; gap: 8px; }
  .installation .bv-box.edit { border-color: var(--accent); background: color-mix(in srgb, var(--accent) 5%, var(--surface)); }
  .installation .bv-box h3 { margin: 0; }
  .installation .bv-form { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 8px; }
  .installation .bv-form label { display: grid; gap: 3px; font-size: calc(12px * var(--fs)); color: var(--muted); min-width: 0; }
  .installation .bv-form label.wide { grid-column: 1 / -1; }
  .installation .bv-form label.check { display: flex; align-items: center; gap: 6px; color: var(--text); }
  .installation .bv-form input, .installation .bv-form select, .installation .bv-rowedit input, .installation .bv-rowedit select, .installation .bv-chedit input, .installation .bv-chedit select { font: inherit; font-size: calc(13px * var(--fs)); padding: 6px 8px; border: 1px solid var(--input-line); border-radius: 6px; background: var(--surface); color: var(--text); min-width: 0; width: 100%; box-sizing: border-box; }
  .installation .bv-form label.check input { width: auto; padding: 0; border: 0; border-radius: 0; background: none; accent-color: var(--accent); }
  .installation .bv-form input:focus, .installation .bv-form select:focus, .installation .bv-rowedit input:focus, .installation .bv-rowedit select:focus, .installation .bv-chedit input:focus, .installation .bv-chedit select:focus { outline: 2px solid var(--focus); outline-offset: 0; border-color: var(--accent); }
  .installation .bv-err { color: var(--bad); font-size: calc(12px * var(--fs)); }
  .installation .bv-chlist { display: grid; gap: 6px; }
  .installation .bv-list th:first-child, .installation .bv-list td:first-child { min-width: 150px; }
  .installation .bv-list th:nth-child(2), .installation .bv-list td:nth-child(2) { min-width: 170px; }
  .installation .bv-chrow { display: grid; grid-template-columns: 42px minmax(0, 1fr) auto; gap: 8px; align-items: start; padding: 8px 10px; border-radius: 8px; border: 1px solid var(--line); background: var(--soft); cursor: pointer; text-align: left; color: var(--text); width: 100%; font: inherit; }
  .installation .bv-chrow:hover { border-color: var(--accent); }
  .installation .bv-chrow .no { font-family: ui-monospace, monospace; font-weight: 600; font-size: calc(12px * var(--fs)); text-align: center; padding: 2px 0; border-radius: 6px; background: var(--surface); border: 1px solid var(--line); }
  .installation .bv-chrow .nm { font-weight: 500; }
  .installation .bv-chedit { display: grid; grid-template-columns: 34px minmax(0, 1.4fr) minmax(0, 1fr) minmax(0, .9fr); gap: 6px; align-items: center; }
  .installation .bv-chedit .no { font-family: ui-monospace, monospace; font-size: calc(12px * var(--fs)); color: var(--muted); }
  .installation .bv-note { font-size: calc(12px * var(--fs)); color: var(--muted); border-left: 3px solid var(--line); padding: 2px 0 2px 10px; margin: 0; }
  .installation .bv-cab { border: 1px solid var(--line); border-radius: 12px; padding: 12px 14px; display: grid; gap: 10px; }
  .installation .bv-cab.hl, .installation .bv-rowedit.hl { box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 45%, transparent); }
  .installation .bv-rowedit { display: grid; grid-template-columns: minmax(0, 1.4fr) 70px minmax(0, 1fr) 80px 32px; gap: 6px; align-items: center; border-radius: 8px; padding: 2px; }
  .installation .bv-rowuse { font-size: calc(12px * var(--fs)); color: var(--muted); display: flex; gap: 4px; flex-wrap: wrap; align-items: center; grid-column: 1 / -1; padding: 0 2px 6px; }
  .installation details.bv-legacy > summary { cursor: pointer; font-weight: 500; padding: 6px 0; }
  .installation .bv-err.top { margin: 0; }
  .installation .bv-list td.bv-a { white-space: nowrap; }
  .installation .bv-list tr.bv-ch td.bv-a { padding-left: 12px; }
  .installation .bv-bar select { font: inherit; font-size: calc(13px * var(--fs)); padding: 5px 8px; border: 1px solid var(--line); border-radius: 8px; background: var(--surface); color: inherit; max-width: 100%; }
  .installation .bv-lchips { margin: -4px 0 0; }
  .installation .bv-bar .bv-grow { flex: 1; }
  .installation .bv-list td.bv-place { min-width: 150px; }
  .installation details.bv-colmenu label:has(input:disabled) { opacity: .6; cursor: default; }
  .installation label.bv-optin { display: flex; gap: 8px; align-items: center; font-size: calc(13px * var(--fs)); }
  .installation label.bv-optin input { width: auto; margin: 0; }
  .installation details.bv-cabedit > summary { cursor: pointer; font-weight: 500; padding: 4px 0; }
  .installation .bv-cab .bv-cabhead { display: flex; gap: 10px; align-items: baseline; flex-wrap: wrap; }
  .installation .bv-cab .bv-cabhead h3 { margin: 0; }
  ${RAIL_CSS}
  @media (max-width: 860px) {
    .installation .bv-head { grid-template-columns: minmax(0, 1fr); }
  }
  @media (max-width: 560px) {
    .installation .bv-hide-s { display: none; }
    .installation .bv-chedit { grid-template-columns: 30px minmax(0, 1fr); }
    .installation .bv-rowedit { grid-template-columns: minmax(0, 1fr) 64px 32px; }
    .installation .bv-rowedit .bv-next { grid-column: 1 / -1; }
  }`;

export const busView = {
  // ---- the data, looked up ------------------------------------------------------------------

  _bv() {
    // everything the view needs, computed once per draw
    const doc = this._in.doc;
    const data = doc.installation;
    const types = doc.bus_types ?? {};
    const rows = new Map();
    data.cabinets.forEach((c, i) => c.rows.forEach((r, j) => rows.set(r.id, { cab: c, row: r, pos: [i, j] })));
    const devices = new Map();
    const manual = new Map();
    const gws = new Map();
    for (const gw of doc.gateways ?? []) {
      gws.set(gw.entry_id, gw);
      for (const d of gw.devices ?? []) devices.set(`${gw.entry_id}|${d.note_key}`, { gw, d });
      for (const m of gw.manual ?? []) manual.set(`${gw.entry_id}|${m.id}`, { gw, m });
    }
    const buses = data.buses;
    const bus = buses.find((b) => b.id === this._in.bus.id) ?? buses[0] ?? null;
    const checks = (bus && doc.installation_checks?.buses?.[bus.id]) || { items: [], supplies: { mode: "range", supplies: [], unfed: [] }, used: 0, duplicates: [] };
    const modules = bus ? data.modules.filter((m) => m.bus === bus.id) : [];
    const byId = new Map(data.modules.map((m) => [m.id, m]));
    return { doc, data, types, rows, devices, manual, gws, buses, bus, checks, modules, byId };
  },

  _bvType(v, m) {
    return v.types[typeKey(m.type)] ?? null;
  },

  _bvRole(v, m) {
    return m.role || this._bvType(v, m)?.role || "other";
  },

  _bvTe(v, m) {
    return m.te || this._bvType(v, m)?.te || 1;
  },

  _bvCount(v, m) {
    // how many addresses a module takes: the catalog's, at least its highest channel
    if (["master", "supply", "foreign", "accessory"].includes(this._bvRole(v, m))) return 0;
    const n = Math.max(this._bvType(v, m)?.addresses ?? 0, ...m.channels.map((c) => c.n), 0);
    return n || 1;
  },

  _bvRange(v, m) {
    const n = this._bvCount(v, m);
    if (m.first_address == null || !n) return null;
    return n === 1 ? `${m.first_address}` : `${m.first_address}–${m.first_address + n - 1}`;
  },

  _bvAddr(m, c) {
    return m.first_address == null ? null : m.first_address + c.n - 1;
  },

  _bvPower(v, m) {
    const own = watts(m.power);
    if (own !== null) return { w: own, from: "user" };
    const table = this._bvType(v, m)?.power;
    return table != null ? { w: table, from: "table" } : { w: null, from: "" };
  },

  _bvTitle(v, m) {
    // the type and the name a module was given; a placeholder master says it is one
    const B = this._t.inst.busv;
    const type = m.type || B.unknownType;
    if (m.placeholder) return `${type} (${B.placeholder})`;
    return m.name ? `${type} · ${m.name}` : type;
  },

  _bvSlot(v, m) {
    const te = this._bvTe(v, m);
    return te <= 1 ? fmtNum(m.slot) : `${fmtNum(m.slot)}–${fmtNum(m.slot + te - 1)}`;
  },

  _bvPlace(v, m) {
    const found = m.row ? v.rows.get(m.row) : null;
    if (!found) return "";
    return `${found.cab.name} · ${found.row.name} · ${this._t.inst.busv.slot} ${this._bvSlot(v, m)}`;
  },

  _bvChannel(v, m, c) {
    // what a channel is: a device in Home Assistant, an entry by hand, or only a name here
    const ha = c.device_key ? v.devices.get(`${c.entry_id}|${c.device_key}`) : null;
    const hand = c.manual_id ? v.manual.get(`${c.entry_id}|${c.manual_id}`) : null;
    const B = this._t.inst.busv;
    const name = c.unused ? B.free : ha?.d.name || hand?.m.name || c.name || (c.device_key ? c.device_key : B.channelN(c.n));
    return { ha, hand, name, missing: Boolean(c.device_key && !ha) };
  },

  _bvChannels(v) {
    // every channel of the bus that is not free, with its address
    return v.modules.flatMap((m) => m.channels.filter((c) => !c.unused).map((c) => ({ m, c, a: this._bvAddr(m, c) })));
  },

  _bvOrder(v, list) {
    // the bus order: cabinet, row, slot; modules without a place at the end
    const pos = (m) => v.rows.get(m.row)?.pos;
    return [...list].sort((a, b) => {
      const x = pos(a);
      const y = pos(b);
      if (!x || !y) return !x - !y || this._bvTitle(v, a).localeCompare(this._bvTitle(v, b));
      return x[0] - y[0] || x[1] - y[1] || a.slot - b.slot;
    });
  },

  _bvSupplyOf(v, m) {
    // the supply (or section) that feeds a module, from the server's load calculation
    return (v.checks.supplies?.supplies ?? []).find((s) => s.members.includes(m.id) || s.module === m.id || (s.modules ?? []).includes(m.id)) ?? null;
  },

  _bvMasterSupply(v, m) {
    // what the FAM14 itself delivers, as the server reckons it: written down, its integrated 12 W
    // (up to production week 07/22), or 0 W when the FSNT14 that came with it sits beside it
    for (const s of v.checks.supplies?.supplies ?? []) {
      const found = (s.master_supply ?? []).find((x) => x.module === m.id);
      if (found) return found;
    }
    const own = watts(m.supply_watts);
    return own != null ? { watts: own, from: "entered" } : { watts: this._bvType(v, m)?.supply ?? 12, from: "integrated" };
  },

  _bvMasterText(v, m, long = false) {
    const B = this._t.inst.busv;
    const own = this._bvMasterSupply(v, m);
    if (!own.watts) return B.masterViaFsnt;
    return long ? B.masterDelivers(fmtNum(own.watts), own.from) : B.masterSupply(fmtNum(own.watts));
  },

  _bvSupplyName(v, s) {
    const B = this._t.inst.busv;
    const m = s.module ? v.byId.get(s.module) : null;
    if (!m) return s.state === "none" ? B.noSupply : B.famSupply;
    return this._bvRole(v, m) === "master" ? B.famSupply : this._bvTitle(v, m);
  },

  _bvLinks(v, entryId, noteKey) {
    // the senders taught into a device of Home Assistant (the links of the documentation)
    const gw = v.gws.get(entryId);
    return (gw?.links ?? []).filter((l) => l.to_key === noteKey);
  },

  // ---- links ------------------------------------------------------------------------------------

  _bvL(type, id, label, cls = "bv-lnk") {
    return `<button class="${cls}" data-bv-go="${type}|${esc(id)}">${label}</button>`;
  },

  _bvHaLink(v, ha) {
    // a device of Home Assistant: its row in the Devices view, else its row in the table
    const B = this._t.inst.busv;
    const entity = ha.d.name;
    return `<button class="tag ent" data-in-goto="${esc(ha.d.key)}" title="${esc(B.openDevice)}">${esc(entity)}</button>`;
  },

  // ---- the view -----------------------------------------------------------------------------------

  _busView() {
    const v = this._bv();
    const t = this._t;
    const B = t.inst.busv;
    const state = this._in.bus;
    if (!state.id && v.bus) state.id = v.bus.id;
    if (!v.bus) {
      return `<div class="gwempty"><p>${esc(B.noBus)}</p><button class="chip" data-bv-act="bus-new">${esc(B.addBus)}</button></div>${this._bvDrawer(v)}`;
    }
    const chips = v.buses.length > 1 ? `<div class="bv-bar"><span class="isub">${esc(B.bus)}:</span>${v.buses.map((b) => `<button class="chip" data-bv-bus="${esc(b.id)}" aria-pressed="${b.id === v.bus.id}">${esc(this._bvBusName(v, b))}</button>`).join("")}</div>` : "";
    const items = v.checks.items;
    const errors = items.filter((i) => i.level === "error").length;
    const warnings = items.filter((i) => i.level === "warning").length;
    const subs = SUBS.map((s) => `<button data-bv-sub="${s}" aria-pressed="${state.sub === s}">${esc(B.subs[s])}${s === "checks" && (errors || warnings) ? `<span class="bv-cnt${errors ? "" : " warn"}">${errors || warnings}</span>` : ""}</button>`).join("");
    const body = { list: () => this._bvList(v), addresses: () => this._bvAddresses(v), supplies: () => this._bvSupplies(v), checks: () => this._bvChecksView(v), cabinets: () => this._bvCabinets(v), read: () => this._bvRead(v) }[state.sub]();
    return `${chips}${this._bvHead(v)}${this._bvTiles(v)}<div class="bv-bar"><div class="seg" role="group" aria-label="${esc(B.views)}">${subs}</div><span class="grow"></span><button class="chip" data-bv-act="module-new">${esc(B.addModule)}</button><button class="chip" data-bv-act="bus-edit" data-bv-id="${esc(v.bus.id)}">${esc(B.editBus)}</button><button class="chip" data-bv-act="print">${svg(ICON.print)}${esc(B.print)}</button></div>${body}${this._bvDrawer(v)}`;
  },

  _bvBusName(v, b) {
    const B = this._t.inst.busv;
    if (b.name) return b.name;
    const gw = b.access.map((a) => v.gws.get(a.entry_id)?.title).find(Boolean);
    return gw ? B.busOver(gw) : B.bus;
  },

  _bvHead(v) {
    const B = this._t.inst.busv;
    const master = v.byId.get(v.bus.master ?? "");
    const place = master ? this._bvPlace(v, master) : "";
    const supply = master && this._bvRole(v, master) === "master" ? ` <span class="tag kind" data-r="master">${esc(this._bvMasterText(v, master))}</span>` : "";
    const masterCard = master
      ? `<div><b>${this._bvL("module", master.id, esc(this._bvTitle(v, master)))}</b>${supply} <span class="tag">${esc(B.te(fmtNum(this._bvTe(v, master))))}</span></div><div class="isub">${place ? this._bvL("place", master.id, esc(place)) : `<span class="tag warn">${esc(B.noPlace)}</span>`} · ${esc(B.baseId)} <span class="mono">${esc(v.bus.base_id || "–")}</span> · ${esc(B.upTo(ADDRESSES))}</div>`
      : `<div><span class="tag bad">${esc(B.noMaster)}</span></div>`;
    const access = v.bus.access.map((a) => {
      const gw = v.gws.get(a.entry_id);
      const name = gw ? gw.title : B.gatewayGone;
      return `<div><b>${esc(name)}</b> <span class="isub">${esc(gw?.model_name ?? "")}</span> <span class="mono isub">${esc(gw?.base_id ?? "")}</span> <span class="tag">${esc(a.via === "wired" ? B.wired : B.radio)}</span></div>`;
    }).join("");
    const wiredOnly = v.bus.access.some((a) => a.via === "wired");
    return `<div class="bv-head"><div class="bv-card master"><span class="bv-role">${esc(B.master)}</span>${masterCard}</div><div class="bv-card access"><span class="bv-role">${esc(B.access)}</span>${access || `<div class="isub">${esc(B.noAccess)}</div>`}<div class="isub">${esc(wiredOnly ? B.wiredPath : B.radioPath)}</div></div></div>`;
  },

  _bvTiles(v) {
    const B = this._t.inst.busv;
    const devices = v.modules.filter((m) => !["master", "supply", "foreign", "accessory"].includes(this._bvRole(v, m)));
    const unplaced = devices.filter((m) => !m.row).length;
    const chs = this._bvChannels(v);
    const inHa = chs.filter((x) => x.c.device_key).length;
    const dups = v.checks.duplicates?.length ?? 0;
    const sup = v.checks.supplies?.supplies ?? [];
    const over = sup.filter((s) => s.state === "over" || s.state === "none").length;
    const reserve = sup.filter((s) => s.state === "reserve").length;
    const items = v.checks.items;
    const errors = items.filter((i) => i.level === "error").length;
    const warnings = items.filter((i) => i.level === "warning").length;
    const tile = (sub, title, value, note, cls) => `<button class="tile${cls ? ` ${cls}` : ""}" data-bv-sub="${sub}"><small>${esc(title)}</small>${value}<span class="bv-sub">${esc(note)}</span></button>`;
    return `<div class="tiles">${tile("list", B.tiles.devices, devices.length, B.tiles.unplaced(unplaced), unplaced ? "warn" : "")}${tile("list", B.tiles.channels, chs.length, B.tiles.inHa(inHa), "")}${tile("addresses", B.tiles.used, `${v.checks.used ?? 0} <span class="bv-sub" style="display:inline">${esc(B.of(ADDRESSES))}</span>`, B.tiles.dups(dups), dups ? "err" : "ok")}${tile("supplies", B.tiles.supplies, sup.length, over ? B.tiles.over(over) : reserve ? B.tiles.reserve(reserve) : B.tiles.fine, over ? "err" : reserve ? "warn" : "ok")}${tile("checks", B.tiles.checks, errors + warnings ? `${errors} · ${warnings}` : "✓", errors + warnings ? B.tiles.errWarn : B.tiles.fine, errors ? "err" : warnings ? "warn" : "ok")}</div>`;
  },

  // ---- list: module, then its channels ----------------------------------------------------------

  _bvList(v) {
    // one table: address first, then device and channel, place, Home Assistant, senders ...;
    // sorted by a click on a column head, filtered by the search and the chips; a module stays
    // together with its channels, free address ranges show between modules when sorted by address
    const t = this._t;
    const B = t.inst.busv;
    const state = this._in;
    const L = state.bus.list;
    const q = state.q.trim().toLowerCase();
    const dups = new Set(v.checks.duplicates ?? []);
    const info = (m, c) => this._bvChannel(v, m, c);
    const text = (m, c) => [m.type, m.name, this._bvPlace(v, m), this._bvRange(v, m), ...(c ? [info(m, c).name, c.feedback_id, c.function, this._bvAddr(m, c)] : [])].join(" ").toLowerCase();
    // the filters: one of the chips, a role, a cabinet or row
    const chanPass = (m, c) => {
      const a = this._bvAddr(m, c);
      if (L.f === "dup" && !(a != null && dups.has(a))) return false;
      if (L.f === "noaddr" && a != null) return false;
      if (L.f === "ha" && !c.device_key) return false;
      if (L.f === "doc" && (c.device_key || c.unused)) return false;
      return !q || text(m, c).includes(q);
    };
    const modPass = (m) => {
      if (L.role && this._bvRole(v, m) !== L.role) return false;
      if (L.place) {
        const found = m.row ? v.rows.get(m.row) : null;
        if (L.place === "none" ? found : !found || (L.place.startsWith("c:") ? found.cab.id !== L.place.slice(2) : found.row.id !== L.place.slice(2))) return false;
      }
      return true;
    };
    const channelFilter = ["dup", "ha", "doc"].includes(L.f);
    const shown = [];
    for (const m of v.modules) {
      if (!modPass(m)) continue;
      const head = !q || text(m).includes(q);
      const headOk = L.f === "noaddr" ? this._bvCount(v, m) > 0 && m.first_address == null : !channelFilter;
      const chs = m.channels.filter((c) => chanPass(m, c) || (head && headOk && !channelFilter && L.f !== "noaddr"));
      if ((head && headOk) || chs.length) shown.push({ m, chs: L.f === "noaddr" && head && headOk ? m.channels : chs });
    }
    // the order: address (none last), place (bus order), type, name; asc or desc
    const order = new Map(this._bvOrder(v, v.modules).map((m, i) => [m.id, i]));
    const key = {
      address: (m) => (m.first_address == null ? null : m.first_address),
      place: (m) => (m.row ? order.get(m.id) : null),
      type: (m) => (m.type ? m.type.toLowerCase() : null),
      name: (m) => (m.name || info(m, m.channels[0] ?? { n: 1 }).name || "").toLowerCase() || null,
    }[L.sort] ?? ((m) => m.first_address);
    shown.sort((x, y) => {
      const a = key(x.m);
      const b = key(y.m);
      if (a == null || b == null) return (a == null) - (b == null) || this._bvTitle(v, x.m).localeCompare(this._bvTitle(v, y.m));
      return (typeof a === "number" ? a - b : String(a).localeCompare(String(b), undefined, { numeric: true })) * L.dir || this._bvTitle(v, x.m).localeCompare(this._bvTitle(v, y.m));
    });
    // the columns: address and device always, the others as chosen in the column menu
    const shownCols = LIST_COLUMNS.filter((c) => LIST_FIXED.includes(c) || state.bus.cols.has(c));
    const cls = { address: "bv-a mono", place: "bv-place", senders: "bv-hide-s", feedback: "mono bv-hide-s", power: "num", supply: "bv-hide-s" };
    const cells = (row) => shownCols.map((c) => `<td${cls[c] ? ` class="${cls[c]}"` : ""}>${row[c] ?? ""}</td>`).join("");
    const chRow = (m, c) => {
      const a = this._bvAddr(m, c);
      const x = info(m, c);
      const senders = x.ha ? this._bvLinks(v, c.entry_id, c.device_key).map((l) => `<button class="tag" data-bv-go="sender|${esc(l.from_id || l.from_name)}">${esc(l.from_name || (l.source === "assigned" ? this._profile(l.role) : l.from_id))}</button>`).join("") : "";
      const ha = x.ha ? this._bvHaLink(v, x.ha) : c.unused ? "" : x.missing ? `<span class="tag warn">${esc(B.haMissing)}</span>` : `<span class="tag doc">${esc(x.hand ? B.byHand : B.documented)}</span>`;
      const addr = a != null ? `<span class="mono">${a}</span>${dups.has(a) ? ` <span class="tag bad">${esc(B.twice)}</span>` : ""}` : `<span class="tag warn">${esc(B.none)}</span>`;
      return `<tr class="bv-ch${c.unused ? " bv-unused" : ""}${a != null && dups.has(a) ? " dup" : ""}" data-r="${this._bvRole(v, m)}">${cells({ address: addr, device: `<span class="isub">${esc(B.channelShort(c.n))}</span> ${c.unused ? esc(B.free) : this._bvL("channel", `${m.id}:${c.n}`, esc(x.name))}${x.ha ? `<div class="isub mono">${esc(x.ha.d.id)}</div>` : ""}`, ha, senders: `<div class="chips">${senders}</div>`, feedback: esc(c.feedback_id || "–") })}</tr>`;
    };
    const modRow = (m) => {
      const p = this._bvPower(v, m);
      const sup = this._bvSupplyOf(v, m);
      const role = this._bvRole(v, m);
      const place = this._bvPlace(v, m);
      const power = OFF.includes(role) ? '<span class="isub">–</span>' : role === "master" ? `<span class="isub">${esc(this._bvMasterText(v, m))}</span>` : role === "supply" ? `<span class="isub">${esc(B.delivers(fmtNum(watts(m.supply_watts) ?? this._bvType(v, m)?.supply ?? 12)))}</span>` : p.w != null ? `${esc(fmtNum(p.w))} W${p.from === "user" ? ` <span class="tag">${esc(B.entered)}</span>` : ""}` : `<span class="tag warn">${esc(B.noValue)}</span>`;
      const range = this._bvRange(v, m) ?? (this._bvCount(v, m) ? `<span class="tag warn">${esc(B.none)}</span>` : "–");
      const tags = [m.placeholder ? `<span class="tag doc">${esc(B.placeholder)}</span>` : "", role === "master" ? `<span class="tag kind" data-r="master">${esc(B.roles.master)}</span>` : role === "supply" ? `<span class="tag kind" data-r="supply">${esc(B.roles.supply)}</span>` : OFF.includes(role) ? `<span class="tag doc">${esc(B.roles[role])}</span>` : ""].join("");
      return `<tr class="bv-mod" data-r="${role}" data-in-row="bv|${esc(m.id)}">${cells({ address: `<b>${range}</b>`, device: `${this._bvL("module", m.id, `<b>${esc(m.type || B.unknownType)}</b>`)} ${m.name ? esc(m.name) : ""} ${tags}<div class="isub">${esc(B.te(fmtNum(this._bvTe(v, m))))}${m.legacy_location ? ` · ${esc(B.before)} „${esc(m.legacy_location)}“` : ""}</div>`, place: place ? this._bvL("place", m.id, esc(place)) : `<span class="tag warn">${esc(B.noPlace)}</span>`, power, supply: sup ? this._bvL("supply", sup.module ?? "", esc(this._bvSupplyName(v, sup))) : '<span class="isub">–</span>' })}</tr>`;
    };
    // free address ranges between modules: sorted by address, upwards, without a filter
    const gaps = L.sort === "address" && L.dir > 0 && !q && !L.f && !L.role && !L.place;
    const free = (from, to) => `<tr class="free"><td colspan="${shownCols.length}">${esc(B.freeRange(from === to ? `${from}` : `${from}–${to}`))}</td></tr>`;
    let body = "";
    let prev = 0;
    let unaddressed = false;
    for (const { m, chs } of shown) {
      const first = m.first_address;
      if (gaps && first != null && first > prev + 1) body += free(prev + 1, first - 1);
      if (gaps && first == null && !unaddressed && this._bvCount(v, m)) {
        if (prev < ADDRESSES) body += free(prev + 1, ADDRESSES);
        body += `<tr class="free"><td colspan="${shownCols.length}"><b>${esc(B.withoutAddress)}</b></td></tr>`;
        unaddressed = true;
        prev = ADDRESSES;
      }
      body += modRow(m) + chs.map((c) => chRow(m, c)).join("");
      if (first != null) prev = Math.max(prev, first + this._bvCount(v, m) - 1);
    }
    if (gaps && !unaddressed && prev < ADDRESSES) body += free(prev + 1, ADDRESSES);
    const th = (col, label, cls = "") => `<th class="sortable${cls ? ` ${cls}` : ""}" data-bv-sort="${col}"${L.sort === col ? ` aria-sort="${L.dir > 0 ? "ascending" : "descending"}"` : ""}><span>${esc(label)}</span><i class="sarrow">${L.sort === col && L.dir < 0 ? "↓" : "↑"}</i></th>`;
    const heads = { address: th("address", B.cols.address), device: th("name", B.cols.device).replace("</th>", ` <button class="tag bv-sorttype" data-bv-sort="type"${L.sort === "type" ? ' aria-pressed="true"' : ""}>${esc(B.sortType)} ${L.sort === "type" && L.dir < 0 ? "↓" : "↑"}</button></th>`), place: th("place", B.cols.place), type: "", ha: `<th>${esc(B.cols.ha)}</th>`, senders: `<th class="bv-hide-s">${esc(B.cols.senders)}</th>`, feedback: `<th class="bv-hide-s">${esc(B.cols.feedback)}</th>`, power: `<th class="num">${esc(B.cols.power)}</th>`, supply: `<th class="bv-hide-s">${esc(B.cols.supply)}</th>` };
    const head = `<tr>${shownCols.map((c) => heads[c]).join("")}<th class="rmenu"></th></tr>`;
    const colMenu = `<details class="colmenu bv-colmenu" ${this._in.colMenu ? "open" : ""}><summary class="chip">${esc(this._t.inst.columns)}</summary><div class="items"><div class="colgroup"><button class="tag" data-bv-lcols="all">${esc(this._t.inst.colAll)}</button><button class="tag" data-bv-lcols="none">${esc(this._t.inst.colNone)}</button></div>${LIST_COLUMNS.map((c) => `<label><input type="checkbox" data-bv-lcol="${c}" ${LIST_FIXED.includes(c) ? "checked disabled" : state.bus.cols.has(c) ? "checked" : ""}>${esc(B.cols[c])}</label>`).join("")}<span class="isub">${esc(B.colsHint)}</span></div></details>`;
    const unassigned = (this._in.doc.installation_checks?.unassigned ?? []).filter((u) => v.bus.access.some((a) => a.entry_id === u.entry_id));
    const assign = unassigned.length
      ? `<div class="bv-box"><div class="bv-bar"><b>${esc(B.unassignedTitle(unassigned.length))}</b><span class="isub">${esc(B.unassignedHint)}</span></div><div class="chips">${unassigned.map((u) => {
          const found = v.devices.get(`${u.entry_id}|${u.device_key}`);
          return `<button class="chip small" data-bv-assign="${esc(u.entry_id)}|${esc(u.device_key)}">+ ${esc(found ? `${found.d.name}${found.d.model ? ` (${found.d.model})` : ""}` : u.device_key)}</button>`;
        }).join("")}</div></div>`
      : "";
    // the filter chips count what they would leave
    const all = v.modules.flatMap((m) => m.channels.map((c) => [m, c]));
    const counts = {
      "": v.modules.length,
      dup: all.filter(([m, c]) => !c.unused && this._bvAddr(m, c) != null && dups.has(this._bvAddr(m, c))).length,
      noaddr: v.modules.filter((m) => this._bvCount(v, m) && m.first_address == null).length,
      ha: all.filter(([, c]) => c.device_key).length,
      doc: all.filter(([, c]) => !c.device_key && !c.unused).length,
    };
    const chip = (f) => `<button class="chip" data-bv-lf="${f}" aria-pressed="${L.f === f}">${esc(B.listFilters[f || "all"])} <b>${counts[f]}</b></button>`;
    const roles = [...new Set(v.modules.map((m) => this._bvRole(v, m)))];
    const roleSel = `<select data-bv-lrole aria-label="${esc(B.role)}"><option value="">${esc(B.role)}: ${esc(B.listFilters.all)}</option>${roles.map((r) => `<option value="${r}"${L.role === r ? " selected" : ""}>${esc(B.roles[r] ?? r)}</option>`).join("")}</select>`;
    const places = v.data.cabinets.flatMap((c) => [[`c:${c.id}`, c.name], ...c.rows.map((r) => [`r:${r.id}`, `${c.name} · ${r.name}`])]);
    const placeSel = `<select data-bv-lplace aria-label="${esc(B.cols.place)}"><option value="">${esc(B.cols.place)}: ${esc(B.listFilters.all)}</option>${places.map(([id, n]) => `<option value="${esc(id)}"${L.place === id ? " selected" : ""}>${esc(n)}</option>`).join("")}<option value="none"${L.place === "none" ? " selected" : ""}>${esc(B.noPlace)}</option></select>`;
    const search = `<input class="isearch" data-in-search value="${esc(state.q)}" placeholder="${esc(B.search)}" aria-label="${esc(B.search)}">`;
    const filtered = L.f || L.role || L.place || q;
    return `<div class="bv-bar">${search}${roleSel}${placeSel}${filtered ? `<button class="chip text" data-bv-lreset>${esc(B.listReset)}</button>` : ""}<span class="bv-grow"></span>${colMenu}</div><div class="chips bv-lchips">${["", "dup", "noaddr", "ha", "doc"].map(chip).join("")}</div>${assign}<div class="tablewrap"><table class="itable bv-list"><thead>${head}</thead><tbody>${body ? body.replace(/<\/tr>/g, '<td class="rmenu"></td></tr>') : `<tr><td colspan="${shownCols.length + 1}" class="none">${esc(B.nothing)}</td></tr>`}</tbody></table></div><p class="bv-note">${esc(B.listNote)}</p>`;
  },

  // ---- the address plan -----------------------------------------------------------------------

  _bvAddresses(v) {
    const B = this._t.inst.busv;
    const map = new Map();
    for (const x of this._bvChannels(v)) if (x.a != null) map.set(x.a, [...(map.get(x.a) ?? []), x]);
    const cells = [];
    for (let a = 1; a <= ADDRESSES; a++) {
      const list = map.get(a);
      if (!list) {
        cells.push(`<div class="bv-cell"><b>${a}</b><span class="t">${esc(B.freeShort)}</span></div>`);
        continue;
      }
      const x = list[0];
      const doc = !x.c.device_key;
      const title = list.map((y) => `${y.m.type} ${B.channelShort(y.c.n)}: ${this._bvChannel(v, y.m, y.c).name}`).join(" / ");
      cells.push(`<button class="bv-cell${list.length > 1 ? " dup" : ""}${doc ? " doc" : ""}" data-r="${this._bvRole(v, x.m)}" data-bv-go="channel|${esc(x.m.id)}:${x.c.n}" title="${esc(title)}" aria-label="${esc(`${a}: ${title}`)}"><b>${a}</b><span class="t">${list.length > 1 ? "2×!" : esc(String(x.m.type).replace("-", ""))}</span></button>`);
    }
    return `<div class="bv-bar"><h3 style="margin:0">${esc(B.planTitle)}</h3><span class="isub">${esc(B.planSub(map.size, ADDRESSES - map.size))}</span></div><div class="bv-addr">${cells.join("")}</div><p class="bv-note">${esc(B.planNote)}</p>`;
  },

  // ---- power supplies -------------------------------------------------------------------------

  _bvSupplies(v) {
    const t = this._t;
    const B = t.inst.busv;
    const loads = v.checks.supplies ?? { mode: "range", supplies: [], unfed: [] };
    const lang = this._hass?.language || "en";
    const w = (n) => `${Number(n ?? 0).toLocaleString(lang, { maximumFractionDigits: 2 })} W`;
    const cards = loads.supplies.map((s) => {
      const pct = s.capacity ? Math.min(100, (s.load / s.capacity) * 100) : 100;
      const owner = s.module ? v.byId.get(s.module) : null;
      const feeders = (s.modules ?? (s.module ? [s.module] : [])).map((id) => v.byId.get(id)).filter(Boolean);
      const names = feeders.length ? feeders.map((m) => this._bvL("module", m.id, esc(this._bvRole(v, m) === "master" ? B.famSupply : this._bvTitle(v, m)))).join(" + ") : owner ? this._bvL("module", owner.id, esc(this._bvSupplyName(v, s))) : esc(this._bvSupplyName(v, s));
      const name = s.section ? `${esc(B.section(s.section))} · ${names}` : names;
      const members = s.members.map((id) => v.byId.get(id)).filter(Boolean).map((m) => {
        const p = this._bvPower(v, m);
        return `<tr><td>${this._bvL("module", m.id, esc(this._bvTitle(v, m)))}</td><td class="mono">${esc(this._bvRange(v, m) ?? "–")}</td><td class="num">${p.w != null ? esc(w(p.w)) : `<span class="tag warn">${esc(B.noValue)}</span>`}${p.from === "user" ? ` <span class="tag">${esc(B.entered)}</span>` : ""}</td></tr>`;
      }).join("");
      const tag = { ok: ["ok", B.state.ok], reserve: ["warn", B.state.reserve], over: ["bad", B.state.over], none: ["bad", B.noSupply] }[s.state];
      const where = s.range ? B.feedsRange(s.range.replace("-", "–")) : loads.mode === "place" ? B.feedsSection : B.feedsAll;
      return `<div class="bv-sec ${s.state}"><div class="bv-bar"><b>${name}</b><span class="tag ${tag[0]}">${esc(tag[1])}</span><span class="grow"></span><span class="isub">${esc(where)}</span></div><div class="bv-load" title="${esc(`${w(s.load)} / ${w(s.capacity)}`)}"><i class="${s.state === "ok" ? "" : s.state}" style="width:${pct}%"></i>${s.capacity ? `<span class="mark" style="left:${RESERVE * 100}%"><span>${esc(w(s.capacity * RESERVE))}</span></span>` : ""}</div><div class="bv-bar"><b>${esc(w(s.load))}</b><span class="isub">${esc(B.ofCapacity(w(s.capacity), s.capacity ? Math.round((s.load / s.capacity) * 100) : "–"))}${s.without_value.length ? ` · ${esc(B.withoutValue(s.without_value.length))}` : ""}</span></div>${members ? `<div class="tablewrap"><table class="itable"><thead><tr><th>${esc(B.cols.device)}</th><th>${esc(B.cols.address)}</th><th class="num">${esc(B.cols.power)}</th></tr></thead><tbody>${members}</tbody></table></div>` : ""}</div>`;
    }).join("");
    const unfed = loads.unfed.map((id) => v.byId.get(id)).filter(Boolean);
    const unfedBox = unfed.length ? `<div class="bv-box"><b>${esc(loads.mode === "place" ? B.unplacedConsumers : B.unfedTitle)}</b><div class="chips">${unfed.map((m) => `<button class="chip small" data-bv-go="module|${esc(m.id)}">${esc(this._bvTitle(v, m))} · ${esc(this._bvRange(v, m) ?? "–")}</button>`).join("")}</div></div>` : "";
    // the view of before: the supplies with their address ranges, per gateway, edited as they always were
    const legacy = v.bus.access.map((a) => (this._in.doc.gateways ?? []).find((g) => g.entry_id === a.entry_id)).filter(Boolean)
      .map((gw) => `<section class="gw">${this._instGwHead(gw)}${this._instBusOf(gw)}</section>`).join("");
    const legacyBox = legacy ? `<details class="bv-legacy" data-bv-legacy${this._in.bus.legacyOpen ? " open" : ""}><summary>${esc(B.legacyTitle)}</summary><p class="bv-note">${esc(B.legacyNote)}</p>${legacy}</details>` : "";
    return `<p class="bv-note">${esc(loads.mode === "place" ? B.modePlace : B.modeRange)}</p><div class="bv-secs">${cards || `<div class="none">${esc(B.nothing)}</div>`}</div>${unfedBox}${legacyBox}`;
  },

  // ---- checks ---------------------------------------------------------------------------------

  _bvTarget(v, target) {
    // a chip that jumps to what a finding is about
    const B = this._t.inst.busv;
    if (target.type === "module") {
      const m = v.byId.get(target.id);
      return m ? `<button class="chip small" data-bv-go="module|${esc(m.id)}">${esc(this._bvTitle(v, m))}</button>` : "";
    }
    if (target.type === "channel") {
      const [mid, n] = target.id.split(":");
      const m = v.byId.get(mid);
      const c = m?.channels.find((x) => String(x.n) === n);
      return c ? `<button class="chip small" data-bv-go="channel|${esc(target.id)}">${esc(`${m.type} ${B.channelShort(c.n)} · ${this._bvChannel(v, m, c).name}`)}</button>` : "";
    }
    if (target.type === "device") {
      const [entryId, key] = target.id.split("|");
      const found = v.devices.get(`${entryId}|${key}`);
      return `<button class="chip small" data-bv-assign="${esc(target.id)}">+ ${esc(found?.d.name ?? key)}</button>`;
    }
    if (target.type === "heard") return `<button class="chip small" data-bv-sub="read">${esc(B.addressN(target.id))}</button>`;
    if (target.type === "row") {
      const found = v.rows.get(target.id);
      return found ? `<button class="chip small" data-bv-go="row|${esc(target.id)}">${esc(`${found.cab.name} · ${found.row.name}`)}</button>` : "";
    }
    if (target.type === "view") return `<button class="chip small" data-bv-sub="${esc(target.id)}">${esc(B.subs[target.id] ?? target.id)}</button>`;
    if (target.type === "bus") return `<button class="chip small" data-bv-act="bus-edit" data-bv-id="${esc(target.id)}">${esc(B.editBus)}</button>`;
    return "";
  },

  _bvCheck(v, item) {
    const B = this._t.inst.busv;
    const words = B.checks[item.code] ?? { title: () => item.code, text: "" };
    const icon = { error: "!", warning: "!", info: "i", ok: "✓" }[item.level];
    const title = typeof words.title === "function" ? words.title(item.args ?? {}) : words.title;
    const targets = (item.targets ?? []).map((x) => this._bvTarget(v, x)).join("");
    return `<div class="bv-check ${item.level}"><span class="ic" aria-hidden="true">${icon}</span><div><b>${esc(title)}</b>${words.text ? `<div class="isub">${esc(words.text)}</div>` : ""}${targets ? `<div class="chips">${targets}</div>` : ""}</div></div>`;
  },

  _bvChecksView(v) {
    const B = this._t.inst.busv;
    const items = v.checks.items;
    const group = (level) => {
      const list = items.filter((i) => i.level === level);
      return list.length ? `<h3>${esc(B.levels[level])} (${list.length})</h3><div class="bv-checks">${list.map((i) => this._bvCheck(v, i)).join("")}</div>` : "";
    };
    const codes = new Set(items.map((i) => i.code));
    const passed = [["address_twice", B.passed.addresses], ["feedback_twice", B.passed.feedback], ["no_master", B.passed.master], ["supply_over", B.passed.supply]]
      .filter(([code]) => !codes.has(code) && !(code === "no_master" && codes.has("two_masters")) && !(code === "supply_over" && codes.has("section_without_supply")))
      .map(([, text]) => `<div class="bv-check ok"><span class="ic" aria-hidden="true">✓</span><div><b>${esc(text)}</b></div></div>`);
    return `${LEVELS.map(group).join("")}${passed.length ? `<h3>${esc(B.levels.ok)}</h3><div class="bv-checks">${passed.join("")}</div>` : ""}`;
  },

  // ---- cabinets and rows ------------------------------------------------------------------------

  _bvFlag(v, m) {
    // the worst finding about a module, as a dot on its tile
    const mine = this._bvMine(v, m).map((i) => i.level);
    return mine.includes("error") ? "bad" : mine.includes("warning") ? "warn" : "";
  },

  _bvSections(v) {
    // the sections of the rail by place (with a colour each); none while the address ranges decide
    const loads = v.checks.supplies ?? { mode: "range", supplies: [] };
    if (loads.mode !== "place") return [];
    return loads.supplies.map((s, i) => ({ ...s, color: SECTION_COLORS[i % SECTION_COLORS.length], ids: new Set([...s.members, ...(s.modules ?? [])]) }));
  },

  _bvRail(v, row, { edit = false, print = false } = {}) {
    // one row of a cabinet: the modules at their slots, spacers, separator bridges, the
    // terminating resistor and, below the rail, the bands of the supply sections
    const B = this._t.inst.busv;
    const lang = this._hass?.language || "en";
    const w = (n) => `${Number(n ?? 0).toLocaleString(lang, { maximumFractionDigits: 2 })} W`;
    const cols = Math.round(row.te * 2);
    const mods = v.data.modules.filter((m) => m.row === row.id && m.slot != null).sort((a, b) => a.slot - b.slot);
    const items = [];
    for (const m of mods) {
      const te = this._bvTe(v, m);
      const col = Math.round(m.slot * 2 - 1);
      const span = Math.max(1, Math.round(te * 2));
      const role = this._bvRole(v, m);
      const title = `${this._bvTitle(v, m)} · ${this._bvPlace(v, m)}`;
      if (m.spacer_before && col > 1) items.push(`<div class="bvr-spacer" style="grid-column:${col - 1} / span 1" title="${esc(B.spacerShort)}"><span>½</span></div>`);
      const wide = te >= 2 ? " wide" : "";
      const moves = edit ? `<div class="bvr-moves" style="grid-column:${col} / span ${span}"><button data-bv-move="${esc(m.id)}|-1" title="${esc(B.moveLeft)}" aria-label="${esc(`${m.type} ${B.moveLeft}`)}">◀</button><button data-bv-move="${esc(m.id)}|1" title="${esc(B.moveRight)}" aria-label="${esc(`${m.type} ${B.moveRight}`)}">▶</button></div>` : "";
      const tag = print ? "div" : "button";
      const go = print ? "" : ` data-bv-go="module|${esc(m.id)}"`;
      if (OFF.includes(role)) {
        items.push(`<${tag} class="bvr-tile foreign wide" data-r="foreign"${go} data-hl="${esc(m.id)}" style="grid-column:${col} / span ${span}" title="${esc(title)}"><span class="bvr-type">${esc(m.name || m.type || B.roles.foreign)}</span><span class="bvr-lbl">${esc(B.notOnBusTe(fmtNum(te)))}</span></${tag}>${moves}`);
      } else {
        const count = this._bvCount(v, m);
        const leds = Array.from({ length: Math.min(count, 16) }, (_, i) => {
          const c = m.channels.find((x) => x.n === i + 1);
          const cls = !c || c.unused ? "free" : c.device_key ? "" : "doc";
          return `<i class="bvr-led ${cls}" title="${esc(`${B.channelShort(i + 1)}: ${c ? this._bvChannel(v, m, c).name : B.chUnknown}`)}"></i>`;
        }).join("");
        const flag = print ? "" : this._bvFlag(v, m);
        const adr = role === "master" ? `<span class="bvr-mtag">${esc(B.masterTag)}</span>` : role === "supply" ? `<span class="bvr-adr">${esc(w(watts(m.supply_watts) ?? this._bvType(v, m)?.supply ?? 12))}</span>` : this._bvRange(v, m) ? `<span class="bvr-adr">${esc(this._bvRange(v, m))}</span>` : `<span class="bvr-adr none">${esc(B.none)}</span>`;
        const label = te >= 2 ? `<span class="bvr-lbl">${esc(role === "master" ? this._bvMasterText(v, m) : m.name || "")}</span>` : "";
        const documented = m.channels.length && !m.channels.some((c) => c.device_key) ? " doc" : "";
        items.push(`<${tag} class="bvr-tile${wide}${role === "master" ? " master" : ""}${documented}${this._in.bus.hl === m.id ? " hl" : ""}" data-r="${role}"${go} data-hl="${esc(m.id)}" style="grid-column:${col} / span ${span}" title="${esc(title)}">${flag ? `<span class="bvr-flag${flag === "bad" ? " bad" : ""}"></span>` : ""}${adr}<span class="bvr-type">${esc(m.type || B.unknownType)}</span>${label}<span class="bvr-leds">${leds}</span></${tag}>${moves}`);
      }
      if (m.separator_after) items.push(`<div class="bvr-tb" style="grid-column:${Math.min(col + span - 1, cols)} / span 1"><span>TB14</span></div>`);
      if (m.terminator) items.push(`<div class="bvr-term" style="grid-column:${Math.min(col + span, cols)} / span ${Math.min(2, cols - Math.min(col + span, cols) + 1)}">⊣ 120 Ω</div>`);
    }
    for (const s of this._bvSections(v)) {
      const inRow = mods.filter((m) => s.ids.has(m.id));
      if (!inRow.length) continue;
      const a = Math.min(...inRow.map((m) => Math.round(m.slot * 2 - 1) - (m.spacer_before ? 1 : 0)));
      const b = Math.max(...inRow.map((m) => Math.round(m.slot * 2 - 1) + Math.round(this._bvTe(v, m) * 2)));
      const feeders = (s.modules ?? []).map((id) => v.byId.get(id)).filter(Boolean).map((m) => (this._bvRole(v, m) === "master" ? "FAM14" : m.type)).join(" + ") || B.noSupply;
      const text = `${s.section} · ${feeders} · ${w(s.load)}`;
      const tag = print ? "div" : "button";
      items.push(`<${tag} class="bvr-band${s.state === "over" || s.state === "none" ? " bad" : ""}" style="--sec:${s.color};grid-column:${Math.max(a, 1)} / ${Math.min(b, cols + 1)}"${print ? "" : ` data-bv-sub="supplies"`} title="${esc(`${B.section(s.section)}: ${w(s.load)} / ${w(s.capacity)}`)}">${esc(text)}</${tag}>`);
    }
    const used = mods.reduce((n, m) => n + this._bvTe(v, m) + (m.spacer_before ? 0.5 : 0), 0);
    const foreign = mods.filter((m) => OFF.includes(this._bvRole(v, m))).length;
    const next = row.next?.kind ? `<div class="bvr-foot">↳ ${esc(B.busOn(B.next[row.next.kind], row.next.length_m))}</div>` : "";
    const cab = v.rows.get(row.id)?.cab;
    const devices = print || !cab ? "" : ` <button class="tag" data-in-rowdevices="${esc(`${cab.name} · ${row.name}`)}" title="${esc(this._t.inst.rowDevicesHint)}">→ ${esc(this._t.inst.views.all)}</button>`;
    return `<div class="bvr-row${this._in.bus.hl === row.id ? " hl" : ""}" data-bv-rail="${esc(row.id)}"><div class="bvr-label"><b>${esc(row.name)}</b><span class="isub">${esc(B.rowUse2(fmtNum(used), row.te, mods.length - foreign, foreign))}</span>${devices}</div><div class="bvr-wrap"><div class="bvr-rail" style="--cols:${cols}">${items.join("")}</div></div>${next}</div>`;
  },

  _bvLegend() {
    const B = this._t.inst.busv;
    const kinds = ["master", "actuator", "meter", "input", "supply"].map((r) => `<span data-r="${r}"><i class="bvr-led"></i>${esc(B.roles[r])}</span>`).join("");
    return `<div class="bvr-legend">${kinds}<span data-r="actuator"><i class="bvr-led doc"></i>${esc(B.documented)}</span><span><i class="bvr-led free" style="--k:var(--muted)"></i>${esc(B.free)}</span><span><i style="width:0;height:12px;border-left:3px dashed var(--bad)"></i>${esc(B.separatorShort)}</span><span><i style="width:10px;height:12px;border:1px dashed var(--input-line)"></i>${esc(B.spacerShort)}</span></div>`;
  },

  _bvCabinets(v) {
    const B = this._t.inst.busv;
    const state = this._in.bus;
    const cab = v.data.cabinets.find((c) => c.id === state.cab) ?? v.data.cabinets[0];
    const chips = v.data.cabinets.length > 1 ? v.data.cabinets.map((c) => `<button class="chip" data-bv-cabsel="${esc(c.id)}" aria-pressed="${c.id === cab?.id}">${esc(c.name)}</button>`).join("") : "";
    const editForm = (c) => {
      const rows = c.rows.map((r) => {
        const mods = this._bvOrder(v, v.data.modules.filter((m) => m.row === r.id));
        const used = mods.reduce((n, m) => n + this._bvTe(v, m) + (m.spacer_before ? 0.5 : 0), 0);
        const next = NEXT.map((k) => `<option value="${k}"${(r.next?.kind ?? "") === k ? " selected" : ""}>${esc(B.next[k || "none"])}</option>`).join("");
        return `<div class="bv-rowedit${state.hl === r.id ? " hl" : ""}" data-bv-row="${esc(r.id)}"><input data-bvr="name" value="${esc(r.name)}" aria-label="${esc(B.rowName)}" placeholder="${esc(B.rowName)}"><input data-bvr="te" type="number" min="1" max="48" step="1" value="${esc(r.te)}" aria-label="${esc(B.rowTe)}" title="${esc(B.rowTe)}"><select class="bv-next" data-bvr="kind" aria-label="${esc(B.rowNext)}">${next}</select><input class="bv-next" data-bvr="length" type="number" min="0" max="1000" step="0.5" value="${esc(r.next?.length_m ?? "")}" placeholder="${esc(B.metres)}" aria-label="${esc(B.metres)}"><button class="bv-ibtn" data-bv-rowdel="${esc(r.id)}" title="${esc(B.rowRemove)}" aria-label="${esc(B.rowRemove)}">${svg(ICON.close)}</button><div class="bv-rowuse">${esc(B.rowUse(fmtNum(used), r.te, mods.length))}</div></div>`;
      }).join("");
      return `<details class="bv-cabedit" data-bv-cabedit${state.cabEdit ? " open" : ""}><summary>${esc(B.editCabinet)}</summary><div class="bv-form"><label class="wide"><span>${esc(B.cabinetName)}</span><input data-bvc="name" value="${esc(c.name)}" autocomplete="off"></label><label class="wide"><span>${esc(B.note)}</span><input data-bvc="note" value="${esc(c.note)}" autocomplete="off"></label></div><div class="bv-bar"><b>${esc(B.rows)}</b><span class="isub">${esc(B.rowsHint)}</span></div>${rows || `<div class="isub">${esc(B.noRows)}</div>`}<div class="bv-bar"><button class="chip small" data-bv-rowadd="${esc(c.id)}">${esc(B.addRow)}</button><span class="grow"></span><button class="chip small" data-bv-cabdel="${esc(c.id)}">${esc(B.cabinetRemove)}</button><button class="chip small primary" data-bv-cabsave="${esc(c.id)}">${esc(B.save)}</button></div></details>`;
    };
    const unplaced = v.modules.filter((m) => !m.row && !m.placeholder);
    const tray = unplaced.length ? `<div class="bv-box"><b>${esc(B.withoutPlace(unplaced.length))}</b><div class="chips">${unplaced.map((m) => `<button class="chip small" data-bv-go="module|${esc(m.id)}">${esc(this._bvTitle(v, m))}${this._bvRange(v, m) ? ` · ${esc(this._bvRange(v, m))}` : ""}</button>`).join("")}</div><span class="isub">${esc(B.withoutPlaceHint)}</span></div>` : "";
    const sections = (v.checks.supplies?.mode ?? "range") === "place" ? "" : `<p class="bv-note">${esc(B.bandsLater)}</p>`;
    const card = cab
      ? `<section class="bv-cab${state.hl === cab.id ? " hl" : ""}" data-bv-cab="${esc(cab.id)}"><div class="bv-cabhead"><h3>${esc(cab.name)}</h3><span class="isub">${esc(B.cabinetSub(cab.rows.length))}</span></div>${state.error && state.cabinet === cab.id ? `<div class="bv-err top" role="alert">${esc(state.error)}</div>` : ""}${cab.rows.map((r) => this._bvRail(v, r, { edit: state.arrange })).join("") || `<div class="isub">${esc(B.noRows)}</div>`}${this._bvLegend()}${sections}${editForm(cab)}</section>`
      : "";
    const tools = cab ? `<button class="chip" data-bv-act="arrange" aria-pressed="${Boolean(state.arrange)}">${esc(state.arrange ? B.arrangeDone : B.arrange)}</button><button class="chip" data-bv-act="foreign-new">${esc(B.addForeign)}</button>` : "";
    return `<div class="bv-bar">${chips}<span class="grow"></span>${tools}<button class="chip" data-bv-act="cabinet-new">${esc(B.addCabinet)}</button></div><p class="bv-note">${esc(state.arrange ? B.arrangeHint : B.cabinetsHint)}</p>${tray}${card || `<div class="none">${esc(B.noCabinets)}</div>`}`;
  },

  // ---- the printout: rails, channel list, open checks, label strips ----------------------------

  _bvPrintPage(v) {
    const B = this._t.inst.busv;
    const lang = this._hass?.language || "en";
    const bus = v.bus;
    const master = v.byId.get(bus.master ?? "");
    const access = bus.access.map((a) => `${v.gws.get(a.entry_id)?.title ?? B.gatewayGone} (${a.via === "wired" ? B.wired : B.radio})`).join(", ");
    const save = this._in.bus.hl;
    this._in.bus.hl = "";
    const cabinets = v.data.cabinets.filter((c) => c.rows.some((r) => v.modules.some((m) => m.row === r.id))).map((c) => `<section class="cab"><h2>${esc(c.name)}</h2>${c.note ? `<p class="sub">${esc(c.note)}</p>` : ""}${c.rows.map((r) => this._bvRail(v, r, { print: true })).join("")}</section>`).join("");
    this._in.bus.hl = save;
    const rows = this._bvOrder(v, v.modules).map((m) => {
      const head = `<tr class="mod"><td>${esc(this._bvPlace(v, m) || B.noPlace)}</td><td><b>${esc(this._bvTitle(v, m))}</b></td><td class="mono">${esc(this._bvRange(v, m) ?? "–")}</td><td></td><td></td><td>${esc([m.circuit, m.fuse].filter(Boolean).join(" · "))}</td></tr>`;
      const chs = m.channels.filter((c) => !c.unused).map((c) => {
        const info = this._bvChannel(v, m, c);
        return `<tr><td class="sub">${esc(B.channelN(c.n))}</td><td>${esc(info.name)}</td><td class="mono">${esc(this._bvAddr(m, c) ?? "–")}</td><td class="mono">${esc(c.feedback_id || "–")}</td><td>${esc(info.ha ? info.ha.d.name : info.hand ? B.byHand : B.documented)}</td><td></td></tr>`;
      }).join("");
      return head + chs;
    }).join("");
    const words = (i) => {
      const w = B.checks[i.code];
      return w ? (typeof w.title === "function" ? w.title(i.args ?? {}) : w.title) : i.code;
    };
    const open = v.checks.items.filter((i) => i.level !== "info").map((i) => `<li><b>${esc(B.levels[i.level])}:</b> ${esc(words(i))}</li>`).join("");
    const strips = v.data.cabinets.flatMap((c) => c.rows.map((r) => {
      const mods = v.data.modules.filter((m) => m.row === r.id && m.slot != null).sort((a, b) => a.slot - b.slot);
      if (!mods.length) return "";
      let at = 1;
      const cells = [];
      for (const m of mods) {
        const start = m.slot - (m.spacer_before ? 0.5 : 0);
        if (start > at) cells.push(`<div class="cell gap" style="width:${(start - at) * 18}mm"></div>`);
        if (m.spacer_before) cells.push(`<div class="cell gap" style="width:9mm"></div>`);
        const names = m.channels.filter((c) => !c.unused).map((c) => `${c.n} ${this._bvChannel(v, m, c).name}`);
        cells.push(`<div class="cell" style="width:${this._bvTe(v, m) * 18}mm"><b>${esc(OFF.includes(this._bvRole(v, m)) ? m.name || m.type : m.type || "")}</b><span class="mono">${esc(this._bvRange(v, m) ?? "")}</span>${names.map((n) => `<span>${esc(n)}</span>`).join("")}</div>`);
        at = m.slot + this._bvTe(v, m);
      }
      return `<div class="strip"><div class="sub">${esc(`${c.name} · ${r.name}`)}</div><div class="cells">${cells.join("")}</div></div>`;
    })).join("");
    const tokens = "--bg:#fff;--surface:#fff;--soft:#f5f7f9;--line:#d5dbe2;--line-2:#eef0f3;--input-line:#c3cbd5;--text:#1b1f24;--muted:#5b6270;--accent:#0a6aa8;--on-accent:#fff;--warn:#8a4b00;--warn-line:#f3d19e;--bad:#a1261b;--focus:#7db8e0;--k-bus:#2f6fb5;--k-sensor:#139a87;--k-taster:#7b5cc9;--k-aktor:#d77f1f;--k-psu:#6b7b8d;--fs:1";
    return `<!doctype html><html lang="${esc(lang)}"><head><meta charset="utf-8"><title>${esc(B.printTitle(this._bvBusName(v, bus)))}</title><style>
      :root { ${tokens}; } body { font: 12px/1.4 Roboto, system-ui, sans-serif; color: var(--text); background: #fff; margin: 0; padding: 12mm; }
      h1 { font-size: 18px; margin: 0 0 4px; } h2 { font-size: 15px; margin: 16px 0 6px; } .sub { color: var(--muted); } .mono { font-family: ui-monospace, monospace; }
      table { border-collapse: collapse; width: 100%; } th, td { text-align: left; padding: 3px 6px; border-bottom: 1px solid var(--line); vertical-align: top; } tr.mod td { background: var(--soft); border-top: 1px solid var(--line); }
      .cab { break-inside: avoid; } .bvr-row { margin-bottom: 8px; break-inside: avoid; } .bvr-wrap { overflow: visible; } .bvr-rail { min-width: 0; }
      .bvr-tile { min-height: 120px; } .bvr-spacer { min-height: 120px; }
      .labels { break-before: page; } .strip { margin: 0 0 6mm; break-inside: avoid; } .cells { display: flex; flex-wrap: wrap; }
      .cell { box-sizing: border-box; height: 16mm; border: 0.3mm solid #000; padding: 1mm; overflow: hidden; display: flex; flex-direction: column; font-size: 7pt; line-height: 1.15; } .cell b { font-size: 8pt; } .cell span { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
      .cell.gap { border-style: dashed; border-color: #999; }
      @page { size: A4 landscape; margin: 10mm; } @media print { body { padding: 0; } * { -webkit-print-color-adjust: exact; print-color-adjust: exact; } }
      ${RAIL_CSS}
    </style></head><body>
      <h1>${esc(B.printTitle(this._bvBusName(v, bus)))}</h1>
      <p class="sub">${esc(B.master)}: ${esc(master ? this._bvTitle(v, master) : B.noMaster)}${bus.base_id ? ` · ${esc(B.baseId)} ${esc(bus.base_id)}` : ""} · ${esc(B.access)}: ${esc(access || "–")} · ${esc(new Date().toLocaleString(lang))}</p>
      ${cabinets ? `${cabinets}${this._bvLegend()}` : `<p class="sub">${esc(B.noCabinets)}</p>`}
      <h2>${esc(B.printChannels)}</h2><table><thead><tr><th>${esc(B.cols.place)}</th><th>${esc(B.cols.device)}</th><th>${esc(B.cols.address)}</th><th>${esc(B.cols.feedback)}</th><th>${esc(B.cols.ha)}</th><th>${esc(B.circuitFuse)}</th></tr></thead><tbody>${rows}</tbody></table>
      <h2>${esc(B.printChecks)}</h2>${open ? `<ul>${open}</ul>` : `<p class="sub">${esc(B.tiles.fine)}</p>`}
      ${strips ? `<section class="labels"><h2>${esc(B.printLabels)}</h2><p class="sub">${esc(B.printLabelsHint)}</p>${strips}</section>` : ""}
    </body></html>`;
  },

  _bvPrint() {
    const v = this._bv();
    if (!v.bus) return;
    const page = this._bvPrintPage(v);
    const win = window.open("", "_blank");
    if (!win) {
      this._download(page, "text/html", `enocean-bus-${new Date().toISOString().slice(0, 10)}.html`); // pop-ups blocked
      this._notice(this._t.doc.popupBlocked, true);
      return;
    }
    win.document.write(page);
    win.document.close();
    win.focus();
    win.print();
  },

  // ---- the drawer ---------------------------------------------------------------------------------

  _bvCrumbs(parts) {
    return `<div class="bv-crumbs">${parts.map((p, i) => (i === parts.length - 1 ? `<span>${esc(p[0])}</span>` : `${p[1] ? this._bvL(p[1], p[2], esc(p[0])) : esc(p[0])}<span class="sep">›</span>`)).join("")}</div>`;
  },

  _bvModuleCrumbs(v, m) {
    const B = this._t.inst.busv;
    const found = m.row ? v.rows.get(m.row) : null;
    const bus = v.buses.find((b) => b.id === m.bus);
    return [[bus ? this._bvBusName(v, bus) : B.bus, "view", "list"], ...(found ? [[found.cab.name, "cabinet", found.cab.id], [found.row.name, "row", found.row.id], [`${B.slot} ${this._bvSlot(v, m)}`, "place", m.id]] : [[B.noPlace, null]])];
  },

  _bvDrawer(v) {
    const state = this._in.bus;
    const d = state.drawer;
    if (!d) return "";
    const B = this._t.inst.busv;
    let html = "";
    if (d.type === "module") html = this._bvModuleDrawer(v, d.id);
    else if (d.type === "channel") html = this._bvChannelDrawer(v, d.id);
    else if (d.type === "sender") html = this._bvSenderDrawer(v, d.id);
    else if (d.type === "bus") html = this._bvBusDrawer(v, d.id);
    if (!html) return "";
    return `<div class="bv-scrim" data-bv-act="close"></div><aside class="bv-drawer" role="dialog" aria-modal="true" aria-label="${esc(B.details)}">${html}</aside>`;
  },

  _bvDHead(crumbs, title, tags) {
    const B = this._t.inst.busv;
    const back = this._in.bus.history.length;
    return `<div class="bv-dhead"><div class="bar"><button class="bv-ibtn" data-bv-act="back" title="${esc(B.back)}" aria-label="${esc(B.back)}"${back ? "" : " disabled"}>←</button><div class="grow">${crumbs}</div><button class="bv-ibtn" data-bv-act="close" title="${esc(B.close)}" aria-label="${esc(B.close)}" data-bv-focus>${svg(ICON.close)}</button></div><div class="bv-dtitle"><h2>${title}</h2>${tags}</div></div>`;
  },

  _bvMine(v, m) {
    // the findings about a module or one of its channels
    return v.checks.items.filter((i) => i.targets.some((x) => (x.type === "module" && x.id === m.id) || (x.type === "channel" && x.id.startsWith(`${m.id}:`))));
  },

  _bvModuleDrawer(v, id) {
    const t = this._t;
    const B = t.inst.busv;
    const isNew = id === "new";
    const draft = this._in.bus.draft;
    const m = draft?.key === id ? draft.module : v.byId.get(id);
    if (!m) return "";
    const role = this._bvRole(v, m);
    const p = this._bvPower(v, m);
    const s = isNew ? null : this._bvSupplyOf(v, m);
    const found = m.row ? v.rows.get(m.row) : null;
    const typeInfo = this._bvType(v, m);
    // the findings about it: a duplicate names the other channel, any other only its own channels
    const own = (x) => x.type === "channel" && x.id.startsWith(`${m.id}:`);
    const mine = isNew ? [] : this._bvMine(v, m).map((i) => {
      const pair = ["address_twice", "feedback_twice"].includes(i.code);
      const targets = i.targets.filter((x) => (pair ? !(x.type === "module" && x.id === m.id) : own(x)));
      const args = !pair && "count" in (i.args ?? {}) ? { ...i.args, count: Math.max(targets.length, 1) } : i.args;
      return this._bvCheck(v, { ...i, args, targets });
    });
    const chs = m.channels.map((c) => {
      const info = this._bvChannel(v, m, c);
      const a = this._bvAddr(m, c);
      return `<button class="bv-chrow" data-bv-go="channel|${esc(m.id)}:${c.n}"${isNew ? " disabled" : ""}><span class="no">${a ?? "–"}</span><span><span class="nm">${esc(B.channelShort(c.n))} · ${esc(info.name)}</span><div class="isub">${esc([c.function, c.feedback_id ? `${B.feedback} ${c.feedback_id}` : ""].filter(Boolean).join(" · "))}</div></span><span>${info.ha ? `<span class="tag ent">${esc(info.ha.d.name)}</span>` : c.unused ? "" : `<span class="tag doc">${esc(info.hand ? B.byHand : B.documented)}</span>`}</span></button>`;
    }).join("");
    const kv = isNew ? "" : `<dl class="bv-kv">
      <dt>${esc(B.place)}</dt><dd>${found ? `${this._bvL("cabinet", found.cab.id, esc(found.cab.name))} · ${this._bvL("row", found.row.id, esc(found.row.name))} · ${this._bvL("place", m.id, esc(`${B.slot} ${this._bvSlot(v, m)}`))}` : `<span class="tag warn">${esc(B.noPlace)}</span>${m.legacy_location ? ` <span class="isub">${esc(B.before)} „${esc(m.legacy_location)}“</span>` : ""}`}</dd>
      <dt>${esc(B.width)}</dt><dd>${esc(B.te(fmtNum(this._bvTe(v, m))))}${m.spacer_before ? ` · ${esc(B.spacerShort)}` : ""}${m.separator_after ? ` · ${esc(B.separatorShort)}` : ""}${m.terminator ? ` · ${esc(B.terminatorShort)}` : ""}</dd>
      ${this._bvCount(v, m) ? `<dt>${esc(B.addresses)}</dt><dd class="mono">${esc(this._bvRange(v, m) ?? B.none)} <span class="isub">(${esc(B.consecutive(this._bvCount(v, m)))})</span></dd>` : ""}
      ${role === "master" ? `<dt>${esc(B.baseId)}</dt><dd class="mono">${esc(v.buses.find((b) => b.id === m.bus)?.base_id || "–")}</dd>` : ""}
      <dt>${esc(B.power)}</dt><dd>${role === "master" ? esc(this._bvMasterText(v, m, true)) : role === "supply" ? esc(B.delivers(fmtNum(watts(m.supply_watts) ?? typeInfo?.supply ?? 12))) : p.w != null ? `${esc(fmtNum(p.w))} W <span class="isub">${esc(p.from === "user" ? B.entered : B.fromTable)}</span>` : `<span class="tag warn">${esc(B.noValue)}</span>`}</dd>
      <dt>${esc(B.supply)}</dt><dd>${s ? this._bvL("supply", s.module ?? "", esc(this._bvSupplyName(v, s))) : "–"}${m.legacy_range ? ` <span class="tag">${esc(B.rangeBefore(m.legacy_range.replace("-", "–")))}</span>` : ""}</dd>
      <dt>${esc(B.circuitFuse)}</dt><dd>${esc(m.circuit || "–")} · ${esc(m.fuse || "–")}</dd>
      ${m.installed ? `<dt>${esc(B.installed)}</dt><dd>${esc(m.installed)}</dd>` : ""}
      ${m.note ? `<dt>${esc(B.note)}</dt><dd>${esc(m.note)}</dd>` : ""}
    </dl>`;
    const tags = `<span class="tag kind" data-r="${role}">${esc(B.roles[role] ?? role)}</span>${m.placeholder ? `<span class="tag doc">${esc(B.placeholder)}</span>` : ""}${typeInfo?.assumed?.length ? `<span class="tag" title="${esc(B.assumedHint)}">${esc(B.assumed)}</span>` : ""}`;
    const title = isNew ? esc(B.newModule) : esc(this._bvTitle(v, m));
    const crumbs = this._bvCrumbs([...this._bvModuleCrumbs(v, m), [m.type || B.unknownType]]);
    return this._bvDHead(crumbs, title, isNew ? "" : tags) + `<div class="bv-dbody">${mine.length ? `<div class="bv-checks">${mine.join("")}</div>` : ""}${kv}${chs && !isNew ? `<div class="bv-box"><div class="bv-bar"><h3>${esc(B.channels)}</h3><span class="isub">${esc(B.channelsHint(m.channels.length))}</span></div><div class="bv-chlist">${chs}</div></div>` : ""}${this._bvModuleForm(v, m, isNew)}</div>`;
  },

  _bvModuleForm(v, m, isNew) {
    const B = this._t.inst.busv;
    const state = this._in.bus;
    const role = this._bvRole(v, m);
    const field = (name, label, value, extra = "", cls = "") => `<label class="${cls}"><span>${esc(label)}</span><input data-bvf="${name}" value="${esc(value ?? "")}" autocomplete="off" ${extra}></label>`;
    const check = (name, label, on) => `<label class="check"><input type="checkbox" data-bvf="${name}"${on ? " checked" : ""}>${esc(label)}</label>`;
    const rowOptions = `<option value="">${esc(B.noPlaceOption)}</option>${v.data.cabinets.flatMap((c) => c.rows.map((r) => `<option value="${esc(r.id)}"${r.id === m.row ? " selected" : ""}>${esc(`${c.name} · ${r.name} (${B.te(r.te)})`)}</option>`)).join("")}`;
    const types = Object.values(v.types).map((x) => `<option value="${esc(x.name)}"></option>`).join("");
    const roles = ["", "master", "supply", "actuator", "meter", "input", "gateway", "other", "accessory", "foreign"].map((r) => `<option value="${r}"${(m.role || "") === r ? " selected" : ""}>${esc(r ? B.roles[r] : B.roleAuto)}</option>`).join("");
    const buses = v.buses.length > 1 ? `<label><span>${esc(B.bus)}</span><select data-bvf="bus">${v.buses.map((b) => `<option value="${esc(b.id)}"${b.id === m.bus ? " selected" : ""}>${esc(this._bvBusName(v, b))}</option>`).join("")}</select></label>` : "";
    const count = Math.max(this._bvCount(v, m), m.channels.length ? Math.max(...m.channels.map((c) => c.n)) : 0);
    // the devices of Home Assistant on the gateways of this bus that are not a channel elsewhere
    const bus = v.buses.find((b) => b.id === m.bus) ?? v.bus;
    const taken = new Set(v.data.modules.filter((x) => x.id !== m.id).flatMap((x) => x.channels.filter((c) => c.device_key).map((c) => `${c.entry_id}|${c.device_key}`)));
    const candidates = [...v.devices.entries()].filter(([k, x]) => !x.d.virtual && !taken.has(k) && (bus?.access ?? []).some((a) => a.entry_id === x.gw.entry_id)).sort((a, b) => a[1].d.name.localeCompare(b[1].d.name));
    const channelRows = role === "master" || role === "supply" || OFF.includes(role) ? "" : Array.from({ length: Math.min(Math.max(count, 1), 16) }, (_, i) => {
      const n = i + 1;
      const c = m.channels.find((x) => x.n === n) ?? { n, device_key: null, manual_id: null, entry_id: null, name: "", function: "", feedback_id: "", unused: false };
      const value = c.unused ? "unused" : c.device_key ? `ha|${c.entry_id}|${c.device_key}` : c.manual_id ? `manual|${c.entry_id}|${c.manual_id}` : c.name || c.function ? "doc" : "";
      const own = c.device_key && !candidates.some(([k]) => k === `${c.entry_id}|${c.device_key}`) ? `<option value="ha|${esc(c.entry_id)}|${esc(c.device_key)}" selected>${esc(this._bvChannel(v, m, c).name)}</option>` : "";
      const manualOpt = c.manual_id ? `<option value="manual|${esc(c.entry_id)}|${esc(c.manual_id)}" selected>${esc(this._bvChannel(v, m, c).name)} (${esc(B.byHand)})</option>` : "";
      const options = `<option value=""${value === "" ? " selected" : ""}>${esc(B.chUnknown)}</option><option value="unused"${value === "unused" ? " selected" : ""}>${esc(B.free)}</option><option value="doc"${value === "doc" ? " selected" : ""}>${esc(B.chDocumented)}</option>${manualOpt}${own}${candidates.map(([k, x]) => `<option value="ha|${esc(k)}"${value === `ha|${k}` ? " selected" : ""}>${esc(`${x.d.name}${x.d.model ? ` (${x.d.model})` : ""}`)}</option>`).join("")}`;
      return `<div class="bv-chedit" data-bvch="${n}"><span class="no">${esc(B.channelShort(n))}</span><select data-bvc-f="link" aria-label="${esc(B.channelN(n))}">${options}</select><input data-bvc-f="name" value="${esc(c.name)}" placeholder="${esc(B.chName)}" aria-label="${esc(B.chName)}" autocomplete="off"><input data-bvc-f="feedback_id" class="mono" value="${esc(c.feedback_id)}" placeholder="${esc(B.feedback)}" aria-label="${esc(B.feedback)}" maxlength="16" autocomplete="off"></div>`;
    }).join("");
    const supplyFields = OFF.includes(role) ? "" : role === "supply" || role === "master" ? `${field("supply_watts", role === "master" ? B.masterWattsField : B.supplyWatts, m.supply_watts, `inputmode="decimal" placeholder="${esc(role === "master" ? B.masterWattsPh : fmtNum(this._bvType(v, m)?.supply ?? 12))}"`)}${role === "supply" ? field("legacy_range", B.rangeField, m.legacy_range, 'placeholder="1-126"') : ""}` : field("power", B.powerField, m.power, `inputmode="decimal" placeholder="${esc(this._bvType(v, m)?.power != null ? fmtNum(this._bvType(v, m).power) : "W")}"`);
    const addr = this._bvCount(v, m) ? field("first_address", B.firstAddress, m.first_address ?? "", `type="number" min="1" max="${ADDRESSES}" placeholder="1–${ADDRESSES}"`) : "";
    const found = m.row ? v.rows.get(m.row) : null;
    return `<div class="bv-box edit" data-bv-form="${esc(isNew ? "new" : m.id)}"><h3>${esc(isNew ? B.newModule : B.edit)}</h3><div class="bv-form">
        <label><span>${esc(B.type)}</span><input data-bvf="type" list="bv-types" value="${esc(m.type)}" autocomplete="off" placeholder="FSR14-4x"><datalist id="bv-types">${types}</datalist></label>
        ${field("name", B.name, m.name)}
        <label><span>${esc(B.role)}</span><select data-bvf="role">${roles}</select></label>
        ${buses}
        <label class="wide"><span>${esc(B.cabinetRow)}</span><select data-bvf="row">${rowOptions}</select></label>
        ${field("slot", B.slotField, m.slot ?? "", `type="number" min="1" max="48" step="0.5"`)}
        ${field("te", B.widthField, m.te ?? "", `type="number" min="0.5" max="48" step="0.5" placeholder="${esc(fmtNum(this._bvTe(v, { ...m, te: null })))}"`)}
        ${addr}
        ${supplyFields}
        ${check("spacer_before", B.spacer, m.spacer_before)}
        ${check("separator_after", B.separator, m.separator_after)}
        ${check("terminator", B.terminator, m.terminator)}
        ${field("circuit", B.circuit, m.circuit)}
        ${field("fuse", B.fuse, m.fuse)}
        ${field("installed", B.installed, m.installed, 'type="date"')}
        ${field("note", B.note, m.note, "", "wide")}
      </div>${channelRows ? `<div class="bv-bar"><b>${esc(B.channels)}</b><span class="isub">${esc(B.channelsEditHint)}</span></div><div class="bv-chlist">${channelRows}</div>` : ""}
      ${state.error ? `<div class="bv-err" role="alert">${esc(state.error)}</div>` : ""}
      <div class="bv-bar"><button class="chip primary" data-bv-act="module-save">${esc(B.save)}</button>${found ? `<button class="chip" data-bv-go="place|${esc(m.id)}">${esc(B.showInCabinet)}</button>` : ""}<span class="grow"></span>${isNew ? "" : `<button class="chip" data-bv-act="module-remove">${esc(B.remove)}</button>`}</div></div>`;
  },

  _bvChannelDrawer(v, id) {
    const B = this._t.inst.busv;
    const [mid, n] = id.split(":");
    const m = v.byId.get(mid);
    const c = m?.channels.find((x) => String(x.n) === n);
    if (!c) return "";
    const info = this._bvChannel(v, m, c);
    const a = this._bvAddr(m, c);
    const others = a == null ? [] : v.data.modules.filter((x) => x.bus === m.bus).flatMap((x) => x.channels.filter((y) => !y.unused && this._bvAddr(x, y) === a && !(x.id === m.id && y.n === c.n)).map((y) => ({ x, y })));
    const s = this._bvSupplyOf(v, m);
    const gw = info.ha?.gw ?? (c.entry_id ? v.gws.get(c.entry_id) : null);
    const links = info.ha ? this._bvLinks(v, c.entry_id, c.device_key) : [];
    const senders = links.map((l) => {
      const ha = l.source === "assigned";
      const name = l.from_name || (ha ? this._profile(l.role) : l.from_id);
      return `<button class="bv-chrow" data-bv-go="sender|${esc(l.from_id || l.from_name)}"><span class="no">${ha ? "HA" : "⌁"}</span><span><span class="nm">${esc(name)}</span><div class="isub"><span class="mono">${esc(l.from_id)}</span>${l.role && !ha ? ` · ${esc(l.role)}` : ""}${l.learn ? ` · ${esc(l.learn)}` : ""}</div></span><span class="tag">${esc(B.source[l.source] ?? l.source)}</span></button>`;
    }).join("");
    const crumbs = this._bvCrumbs([...this._bvModuleCrumbs(v, m), [m.type || B.unknownType, "module", m.id], [B.channelN(c.n)]]);
    const tags = `${others.length ? `<span class="tag bad">${esc(B.twice)}</span>` : ""}${info.ha ? "" : `<span class="tag doc">${esc(info.missing ? B.haMissing : info.hand ? B.byHand : B.documented)}</span>`}`;
    const path = B.path(gw?.title ?? "–", (v.bus?.access.find((x) => x.entry_id === gw?.entry_id)?.via ?? "radio") === "wired", a ?? "?", `${m.type} ${B.channelShort(c.n)}`);
    return this._bvDHead(crumbs, esc(info.name), tags) + `<div class="bv-dbody"><dl class="bv-kv">
      <dt>${esc(B.module)}</dt><dd>${this._bvL("module", m.id, esc(this._bvTitle(v, m)))} · ${esc(B.channelOf(c.n, this._bvCount(v, m)))}</dd>
      <dt>${esc(B.place)}</dt><dd>${m.row ? this._bvL("place", m.id, esc(this._bvPlace(v, m))) : `<span class="tag warn">${esc(B.noPlace)}</span>`}</dd>
      <dt>${esc(B.address)}</dt><dd class="mono">${a ?? esc(B.none)}${others.length ? ` · ${esc(B.alsoAt)} ${others.map(({ x, y }) => this._bvL("channel", `${x.id}:${y.n}`, esc(this._bvChannel(v, x, y).name))).join(", ")}` : ""}</dd>
      <dt>${esc(B.feedback)}</dt><dd class="mono">${esc(c.feedback_id || "–")}${this._bvFeedbackHint(v, m, c)}</dd>
      <dt>${esc(B.inHa)}</dt><dd>${info.ha ? `${this._bvHaLink(v, info.ha)} <span class="isub">${esc(info.ha.d.area ?? "")}</span>` : `<span class="tag doc">${esc(B.notInHa)}</span>`}</dd>
      ${info.ha ? `<dt>${esc(B.radioId)}</dt><dd class="mono">${esc(info.ha.d.id)} <span class="isub">${esc(B.belongsTo(info.ha.gw.title))}</span></dd>` : ""}
      ${c.function ? `<dt>${esc(B.functionField)}</dt><dd>${esc(c.function)}</dd>` : ""}
      <dt>${esc(B.supply)}</dt><dd>${s ? this._bvL("supply", s.module ?? "", esc(this._bvSupplyName(v, s))) : "–"}</dd>
      <dt>${esc(B.way)}</dt><dd class="isub">${esc(path)}</dd>
    </dl><div class="bv-box"><div class="bv-bar"><h3>${esc(B.senders)}</h3><span class="isub">${esc(B.sendersHint)}</span></div><div class="bv-chlist">${senders || `<p class="isub" style="margin:0">${esc(info.ha ? B.noSenders : B.sendersOnlyHa)}</p>`}</div></div>
    <div class="bv-bar"><button class="chip" data-bv-go="module|${esc(m.id)}">${esc(B.editModule)}</button></div></div>`;
  },

  _bvSenderDrawer(v, id) {
    // a sender (a button, Home Assistant's own ID) and every channel it is taught into
    const B = this._t.inst.busv;
    const links = [];
    for (const gw of v.gws.values()) for (const l of gw.links ?? []) if ((l.from_id || l.from_name) === id) links.push({ gw, l });
    if (!links.length) return "";
    const first = links[0].l;
    const ha = first.source === "assigned";
    const name = first.from_name || (ha ? B.haSender : id);
    const channelOf = (gw, key) => {
      for (const m of v.data.modules) for (const c of m.channels) if (c.entry_id === gw.entry_id && c.device_key === key) return { m, c };
      return null;
    };
    const rows = links.map(({ gw, l }) => {
      const found = channelOf(gw, l.to_key);
      const target = found ? this._bvL("channel", `${found.m.id}:${found.c.n}`, esc(l.to_name)) : `<button class="bv-lnk" data-in-goto="${esc(gw.devices.find((d) => d.note_key === l.to_key)?.key ?? "")}">${esc(l.to_name)}</button>`;
      return `<div class="bv-chrow" style="cursor:default"><span class="no">${found ? esc(this._bvAddr(found.m, found.c) ?? "–") : "–"}</span><span><span class="nm">${target}</span><div class="isub">${esc([found ? `${found.m.type} ${B.channelShort(found.c.n)}` : B.notOnBus, l.source === "assigned" ? this._profile(l.role) : l.role, l.learn].filter(Boolean).join(" · "))}</div></span><span class="tag">${esc(B.source[l.source] ?? l.source)}</span></div>`;
    }).join("");
    const numbers = ha ? this._bvSenderNumber(links[0].gw, first.from_id) : null;
    const crumbs = this._bvCrumbs([[v.bus ? this._bvBusName(v, v.bus) : B.bus, "view", "list"], [B.sender], [name]]);
    return this._bvDHead(crumbs, esc(name), `<span class="tag">${esc(ha ? B.haSender : B.radioSender)}</span><span class="mono">${esc(first.from_id)}</span>`) + `<div class="bv-dbody"><dl class="bv-kv"><dt>ID</dt><dd class="mono">${esc(first.from_id || "–")}</dd>${numbers != null ? `<dt>${esc(B.pool)}</dt><dd>${esc(links[0].gw.title)} · ${esc(B.number(numbers))} <button class="bv-lnk" data-in-snd="${esc(links[0].gw.entry_id)}|${numbers}">${esc(B.toSenderTab)}</button></dd>` : ""}</dl><div class="bv-box"><div class="bv-bar"><h3>${esc(B.taughtInto)}</h3><span class="isub">${esc(B.channelsCount(links.length))}</span></div><div class="bv-chlist">${rows}</div></div></div>`;
  },

  _bvSuggestFeedback(v, m, c) {
    // the FAM14 radios a channel's confirmation with its base ID plus the address (Eltako): a suggestion only
    const bus = v.buses.find((b) => b.id === m.bus);
    const a = this._bvAddr(m, c);
    if (!bus?.base_id || a == null || a < 1 || a > ADDRESSES) return null;
    const n = parseInt(bus.base_id.replace(/-/g, ""), 16) + a;
    return n.toString(16).toUpperCase().padStart(8, "0").replace(/(..)(?=.)/g, "$1-");
  },

  _bvFeedbackHint(v, m, c) {
    const B = this._t.inst.busv;
    const hint = this._bvSuggestFeedback(v, m, c);
    if (!hint) return "";
    const same = c.feedback_id && c.feedback_id.replace(/[-: ]/g, "").toUpperCase() === hint.replace(/-/g, "");
    return same ? ` <span class="tag ok">${esc(B.feedbackMatches)}</span>` : `<div class="isub">${esc(B.feedbackSuggest(hint))} <button class="chip small" data-bv-feedback="${esc(m.id)}:${c.n}|${esc(hint)}">${esc(B.take)}</button></div>`;
  },

  // ---- reading the bus (experimental): only listening, the server sends nothing -------------------

  _bvRead(v) {
    const B = this._t.inst.busv;
    const state = this._in.bus;
    const seen = this._in.doc.installation_observed?.[v.bus.id];
    const running = Boolean(state.listening);
    const options = LISTEN.map((n) => `<option value="${n}"${state.seconds === n ? " selected" : ""}>${esc(B.listenFor(n))}</option>`).join("");
    const control = `<div class="bv-box edit"><div class="bv-bar"><span class="tag warn">${esc(B.experimental)}</span><b>${esc(B.readTitle)}</b></div><p class="bv-note">${esc(B.readNote)}</p>
      <label class="bv-optin"><input type="checkbox" data-bv-optin${state.optIn ? " checked" : ""}${running ? " disabled" : ""}>${esc(B.optIn)}</label>
      <div class="bv-bar"><label class="isub">${esc(B.duration)} <select data-bv-seconds${running ? " disabled" : ""}>${options}</select></label>${running ? `<button class="chip" data-bv-act="listen-stop">${esc(B.listenStop)}</button><span class="isub" role="status">${esc(B.listening(state.left, state.heard ?? 0))}</span>` : `<button class="chip primary" data-bv-act="listen"${state.optIn ? "" : " disabled"}>${esc(B.listen)}</button>`}</div>${state.error && state.sub === "read" ? `<div class="bv-err" role="alert">${esc(state.error)}</div>` : ""}</div>`;
    if (!seen) return `${control}<p class="bv-note">${esc(B.notReadYet)}</p>`;
    const documented = new Map();
    for (const m of v.modules) for (const c of m.channels) if (!c.unused && this._bvAddr(m, c) != null) documented.set(this._bvAddr(m, c), [...(documented.get(this._bvAddr(m, c)) ?? []), { m, c }]);
    const known = new Set((this._in.doc.gateways ?? []).flatMap((g) => g.devices.flatMap((d) => [d.id, ...(d.ids ?? []).map((x) => x.id)])));
    const ago = (t) => this._t.ago(Math.max(0, Math.round(this._now() / 1000 - t)));
    const rows = Object.entries(seen.answers).map(([a, x]) => {
      const docs = documented.get(Number(a)) ?? [];
      const as = docs.length ? docs.map(({ m, c }) => this._bvL("channel", `${m.id}:${c.n}`, esc(`${m.type} ${B.channelShort(c.n)} · ${this._bvChannel(v, m, c).name}`))).join("<br>") : `<span class="tag warn">${esc(B.notDocumented)}</span> <button class="chip small" data-bv-docaddr="${esc(a)}">${esc(B.document)}</button>`;
      const inHa = known.has(x.sender) || docs.some(({ c }) => c.device_key);
      const add = inHa ? `<span class="tag ok">${esc(B.inHaShort)}</span>` : `<button class="chip small" data-bv-adddev="${esc(x.sender)}" data-bv-gw="${esc(x.gateway ?? "")}">${esc(this._t.addAsDevice)}</button>`;
      return `<tr><td class="mono">${esc(a)}</td><td class="mono">${esc(x.sender)}</td><td class="bv-hide-s">${esc(x.wired ? B.viaWire : B.viaRadio)}</td><td>${esc(B.kinds[x.kind] ?? x.kind)}</td><td class="isub">${esc(ago(x.time))}</td><td>${as}</td><td>${add}</td></tr>`;
    }).join("");
    const base = v.bus.base_id
      ? `<div class="isub">${esc(B.baseUsed(v.bus.base_id))}</div>`
      : seen.candidates.length
        ? `<div class="bv-bar"><span>${esc(B.baseCandidate(seen.candidates[0][0], seen.candidates[0][1]))}</span><button class="chip small" data-bv-takebase="${esc(seen.candidates[0][0])}">${esc(B.take)}</button></div>`
        : `<div class="isub">${esc(B.noBase)}</div>`;
    return `${control}<div class="bv-box"><div class="bv-bar"><b>${esc(B.readResult(Object.keys(seen.answers).length, seen.heard))}</b><span class="isub">${esc(B.listenFor(seen.seconds))}</span></div>${base}<div class="tablewrap"><table class="itable"><thead><tr><th>${esc(B.cols.address)}</th><th>ID</th><th class="bv-hide-s">${esc(B.heardVia)}</th><th>${esc(B.lastTelegram)}</th><th>${esc(B.when)}</th><th>${esc(B.documentedAs)}</th><th></th></tr></thead><tbody>${rows || `<tr><td colspan="7" class="none">${esc(B.nothingHeard)}</td></tr>`}</tbody></table></div></div><p class="bv-note">${esc(B.readSources)}</p>`;
  },

  async _bvListen() {
    const state = this._in.bus;
    const bus = this._bv().bus;
    if (!bus || !state.optIn || state.listening) return;
    Object.assign(state, { left: state.seconds, heard: 0, error: "" });
    const msg = { type: "enocean_eltako/installation/listen", bus_id: bus.id, seconds: state.seconds, opt_in: true };
    const done = (event) => {
      if (event.type === "progress") {
        Object.assign(state, { left: event.left, heard: event.heard });
        this._renderInstallation();
        return;
      }
      const doc = this._in.doc;
      Object.assign(doc, { installation: event.installation, installation_checks: event.checks, installation_observed: event.observed });
      this._bvStopListen();
    };
    try {
      state.listening = this._hass.connection.subscribeMessage(done, msg);
      this._renderInstallation();
      await state.listening;
    } catch (err) {
      state.listening = null;
      state.error = this._t.inst.busv.errors[err?.code] ?? this._t.inst.busv.errors.other;
      this._renderInstallation();
    }
  },

  async _bvStopListen() {
    const state = this._in.bus;
    const pending = state.listening;
    state.listening = null;
    this._renderInstallation();
    if (pending) {
      try {
        const unsubscribe = await pending;
        await unsubscribe?.();
      } catch (err) {
        // the session ended already
      }
    }
  },

  _bvSenderNumber(gw, id) {
    if (!gw.base_id || !id) return null;
    const n = parseInt(String(id).replace(/-/g, ""), 16) - parseInt(String(gw.base_id).replace(/-/g, ""), 16);
    return n >= 0 && n <= 127 ? n : null;
  },

  _bvBusDrawer(v, id) {
    const B = this._t.inst.busv;
    const state = this._in.bus;
    const isNew = id === "new";
    const bus = isNew ? { id: "", name: "", base_id: "", access: [], note: "" } : v.buses.find((b) => b.id === id);
    if (!bus) return "";
    const gws = [...v.gws.values()];
    const access = gws.map((gw) => {
      const on = bus.access.some((a) => a.entry_id === gw.entry_id);
      return `<label class="check"><input type="checkbox" data-bvb-access="${esc(gw.entry_id)}"${on ? " checked" : ""}>${esc(gw.title)}${gw.model_name && gw.model_name !== gw.title ? ` <span class="isub">${esc(gw.model_name)}</span>` : ""}</label>`;
    }).join("");
    const crumbs = this._bvCrumbs([[isNew ? B.newBus : this._bvBusName(v, bus)]]);
    return this._bvDHead(crumbs, esc(isNew ? B.newBus : this._bvBusName(v, bus)), "") + `<div class="bv-dbody"><div class="bv-box edit" data-bv-busform="${esc(bus.id)}"><div class="bv-form">
      <label><span>${esc(B.name)}</span><input data-bvb="name" value="${esc(bus.name)}" placeholder="${esc(B.busNamePh)}" autocomplete="off"></label>
      <label><span>${esc(B.baseId)}</span><input data-bvb="base_id" class="mono" value="${esc(bus.base_id)}" placeholder="FF-9A-1C-80" maxlength="11" autocomplete="off"></label>
      <label class="wide"><span>${esc(B.note)}</span><input data-bvb="note" value="${esc(bus.note)}" autocomplete="off"></label>
    </div><div class="bv-bar"><b>${esc(B.access)}</b><span class="isub">${esc(B.accessHint)}</span></div><div class="bv-form">${access}</div>
    ${state.error ? `<div class="bv-err" role="alert">${esc(state.error)}</div>` : ""}
    <div class="bv-bar"><button class="chip primary" data-bv-act="bus-save">${esc(B.save)}</button><span class="grow"></span>${isNew ? "" : `<button class="chip" data-bv-act="bus-remove">${esc(B.removeBus)}</button>`}</div></div><p class="bv-note">${esc(B.baseIdHint)}</p></div>`;
  },

  // ---- events ---------------------------------------------------------------------------------

  async _bvOpen(type, id) {
    const state = this._in.bus;
    if (!(await this._bvGuard())) return;
    if (state.drawer) state.history.push(state.drawer);
    else state.opener = this._bvTrigger ?? "";
    state.dirty = false;
    state.drawer = { type, id };
    state.error = "";
    if (state.draft && state.draft.key !== id) state.draft = null;
    this._renderInstallation();
    this.shadowRoot.querySelector("#installation [data-bv-focus]")?.focus();
  },

  async _bvGo(type, id) {
    const state = this._in.bus;
    if (["module", "channel", "sender", "bus"].includes(type)) return this._bvOpen(type, id);
    if (type === "supply") return id ? this._bvOpen("module", id) : this._bvSub("supplies");
    if (!(await this._bvGuard())) return;
    const v = this._bv();
    if (type === "view") return this._bvSub(id);
    let hl = id;
    let cab = type === "cabinet" ? id : "";
    if (type === "place") {
      hl = id; // the tile itself
      cab = v.rows.get(v.byId.get(id)?.row)?.cab.id ?? "";
    }
    if (type === "row") cab = v.rows.get(id)?.cab.id ?? "";
    if (type === "cabinet" || type === "row" || type === "place") {
      Object.assign(state, { drawer: null, history: [], dirty: false, sub: "cabinets", hl, cab: cab || state.cab });
      this._renderInstallation();
      this.shadowRoot.querySelector(`#installation [data-hl="${CSS.escape(hl)}"], #installation [data-bv-rail="${CSS.escape(hl)}"], #installation [data-bv-cab="${CSS.escape(hl)}"]`)?.scrollIntoView?.({ block: "center", inline: "center" });
      setTimeout(() => {
        if (state.hl === hl) {
          state.hl = "";
          this.shadowRoot.querySelectorAll("#installation .hl").forEach((el) => el.classList.remove("hl"));
        }
      }, 2000);
    }
  },

  async _bvSub(sub) {
    if (!(await this._bvGuard())) return;
    Object.assign(this._in.bus, { sub, drawer: null, history: [], dirty: false });
    this._renderInstallation();
  },

  async _bvClose() {
    if (!(await this._bvGuard())) return;
    const state = this._in.bus;
    Object.assign(state, { drawer: null, history: [], error: "", draft: null, dirty: false });
    this._renderInstallation();
    // back to where the drawer was opened from
    if (state.opener) this.shadowRoot.querySelector(`#installation ${state.opener}`)?.focus();
    state.opener = "";
  },

  // unsaved input in the drawer: ask before it is thrown away; true when the caller may go on
  async _bvGuard() {
    const state = this._in.bus;
    if (!state.dirty || !state.drawer) return true;
    const B = this._t.inst.busv;
    if (!(await this._bvAsk({ title: B.discardTitle, text: B.discardText, ok: B.discard, cancel: B.keepEditing }))) return false;
    state.dirty = false;
    return true;
  },

  // a small dialog of the panel in place of the browser's confirm(); resolves true on the main button
  _bvAsk({ title, text = "", ok, cancel }) {
    const root = this.shadowRoot;
    const before = root.activeElement;
    const host = document.createElement("div");
    host.className = "installation";
    host.innerHTML = `<div class="bv-ask-scrim"><div class="bv-ask" role="alertdialog" aria-modal="true" aria-label="${esc(title)}"><h2>${esc(title)}</h2>${text ? `<p>${esc(text)}</p>` : ""}<div class="bar"><button class="chip" data-ask="no">${esc(cancel)}</button><button class="chip primary" data-ask="yes">${esc(ok)}</button></div></div></div>`;
    const app = [...root.children].filter((el) => el !== host);
    app.forEach((el) => el.setAttribute?.("inert", ""));
    root.appendChild(host);
    const [no, yes] = host.querySelectorAll("button");
    no.focus();
    return new Promise((resolve) => {
      const done = (answer) => {
        host.remove();
        app.forEach((el) => el.removeAttribute?.("inert"));
        before?.focus?.();
        resolve(answer);
      };
      host.addEventListener("click", (e) => {
        const btn = e.target.closest("[data-ask]");
        if (btn) done(btn.dataset.ask === "yes");
        else if (e.target.classList.contains("bv-ask-scrim")) done(false);
      });
      host.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
          e.preventDefault();
          e.stopPropagation();
          done(false);
        } else if (e.key === "Tab") {
          e.preventDefault();
          (e.target === no ? yes : no).focus();
        }
      });
    });
  },

  _busKey(e) {
    if (!this._in?.bus?.drawer) return;
    if (e.key === "Escape") {
      e.preventDefault();
      e.stopPropagation();
      this._bvClose();
    } else if (e.key === "Tab") {
      // the drawer is modal: Tab stays inside it
      const drawer = this.shadowRoot.querySelector("#installation aside.bv-drawer");
      const items = [...(drawer?.querySelectorAll('button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), summary, a[href], [tabindex]:not([tabindex="-1"])') ?? [])].filter((el) => el.offsetParent !== null);
      if (!items.length) return;
      const at = items.indexOf(this.shadowRoot.activeElement);
      const wrap = e.shiftKey ? at <= 0 : at < 0 || at === items.length - 1;
      if (!wrap) return;
      e.preventDefault();
      items[e.shiftKey ? items.length - 1 : 0].focus();
    }
  },

  _busClick(e) {
    // true when the click was the bus view's
    const state = this._in.bus;
    if (this._in.colMenu && !e.target.closest(".colmenu")) {
      this._in.colMenu = false;
      this.shadowRoot.querySelector("#installation details.bv-colmenu")?.removeAttribute("open");
    }
    if (e.target.closest("[data-in-goto], [data-in-snd]") && state.drawer) Object.assign(state, { drawer: null, history: [], draft: null });
    const el = e.target.closest("[data-bv-go], [data-bv-sub], [data-bv-act], [data-bv-bus], [data-bv-assign], [data-bv-rowadd], [data-bv-rowdel], [data-bv-cabsave], [data-bv-cabdel], [data-bv-move], [data-bv-cabsel], [data-bv-feedback], [data-bv-takebase], [data-bv-adddev], [data-bv-docaddr], [data-bv-optin], [data-bv-sort], [data-bv-lf], [data-bv-lreset], [data-bv-lcol], [data-bv-lcols]");
    if (!el || !this.shadowRoot.getElementById("installation")?.contains(el)) {
      const legacy = e.target.closest("details.bv-legacy > summary");
      if (legacy) state.legacyOpen = !legacy.parentElement.open;
      const cabEdit = e.target.closest("details.bv-cabedit > summary");
      if (cabEdit) state.cabEdit = !cabEdit.parentElement.open;
      return false;
    }
    if (el.disabled) return true;
    // the drawer gives focus back to what opened it: the data attributes find the element again after a redraw
    this._bvTrigger = [...el.attributes].filter((a) => a.name.startsWith("data-") && a.name !== "data-bv-focus").map((a) => `[${a.name}="${CSS.escape(a.value)}"]`).join("");
    const d = el.dataset;
    if (d.bvGo) {
      const [type, ...rest] = d.bvGo.split("|");
      this._bvGo(type, rest.join("|"));
    } else if (d.bvSub) this._bvSub(d.bvSub);
    else if (d.bvBus) {
      Object.assign(state, { id: d.bvBus, drawer: null, history: [] });
      this._renderInstallation();
    } else if (d.bvLcol || d.bvLcols) {
      // the column menu stays open while columns are switched
      this._in.colMenu = true;
      if (d.bvLcols) state.cols = new Set(d.bvLcols === "all" ? LIST_COLUMNS : LIST_FIXED);
      else if (!LIST_FIXED.includes(d.bvLcol)) state.cols.has(d.bvLcol) ? state.cols.delete(d.bvLcol) : state.cols.add(d.bvLcol);
      saveCols(state.cols);
      this._renderInstallation();
    } else if (d.bvSort || "bvLf" in d || "bvLreset" in d) {
      // the list: a column head sorts (again: the other way), a chip filters, reset clears
      const L = state.list;
      if (d.bvSort) Object.assign(L, L.sort === d.bvSort ? { dir: -L.dir } : { sort: d.bvSort, dir: 1 });
      else if ("bvLf" in d) L.f = L.f === d.bvLf ? "" : d.bvLf;
      else {
        Object.assign(L, { f: "", role: "", place: "" });
        this._in.q = "";
      }
      saveList(L);
      this._renderInstallation();
    } else if (d.bvAssign) this._bvAssign(d.bvAssign);
    else if ("bvOptin" in d) {
      state.optIn = el.checked;
      this._renderInstallation();
    } else if (d.bvFeedback) this._bvTakeFeedback(d.bvFeedback);
    else if (d.bvTakebase) {
      const v = this._bv();
      this._bvCall({ type: "enocean_eltako/installation/set", kind: "bus", item: { ...v.bus, base_id: d.bvTakebase } }).then((r) => r && this._bvReload());
    } else if (d.bvAdddev) this._addDevice(d.bvAdddev, d.bvGw || undefined);
    else if (d.bvDocaddr) {
      this._bvAct("module-new", el);
      state.draft.module.first_address = Number(d.bvDocaddr);
      this._renderInstallation();
    } else if (d.bvRowadd) this._bvRowAdd(d.bvRowadd);
    else if (d.bvMove) {
      const [id, dir] = d.bvMove.split("|");
      this._bvMove(id, Number(dir));
    } else if (d.bvCabsel) {
      Object.assign(state, { cab: d.bvCabsel, error: "" });
      this._renderInstallation();
    }
    else if (d.bvRowdel) el.closest("[data-bv-row]")?.remove();
    else if (d.bvCabsave) this._bvSaveCabinet(d.bvCabsave);
    else if (d.bvCabdel) {
      const B = this._t.inst.busv;
      const name = this._bv().data.cabinets.find((c) => c.id === d.bvCabdel)?.name ?? B.cabinetName;
      this._bvAsk({ title: name, text: B.removeCabinetConfirm, ok: B.remove, cancel: B.cancel }).then((yes) => yes && this._bvRemove("cabinet", d.bvCabdel));
    }
    else this._bvAct(d.bvAct, el);
    return true;
  },

  _bvAct(act, el) {
    const state = this._in.bus;
    const v = this._bv();
    if (act === "close") this._bvClose();
    else if (act === "back") {
      this._bvGuard().then((go) => {
        if (!go) return;
        state.drawer = state.history.pop() ?? null;
        state.error = "";
        state.dirty = false;
        this._renderInstallation();
      });
    } else if (act === "module-new") {
      const blank = { id: "", bus: v.bus?.id ?? "", type: "", role: "", name: "", row: null, slot: null, te: null, spacer_before: false, separator_after: false, terminator: false, first_address: null, supply_watts: "", legacy_range: "", legacy_location: "", placeholder: false, power: "", circuit: "", fuse: "", installed: "", revision: "", note: "", channels: [] };
      this._bvGuard().then((go) => {
        if (!go) return;
        state.draft = { key: "new", module: blank };
        this._bvOpen("module", "new");
      });
    } else if (act === "module-save") this._bvSaveModule();
    else if (act === "module-remove") {
      const id = state.drawer?.id;
      const B = this._t.inst.busv;
      const m = v.byId.get(id);
      if (id) this._bvAsk({ title: m?.name || m?.type || B.module, text: B.removeConfirm, ok: B.remove, cancel: B.cancel }).then((yes) => yes && this._bvRemove("module", id));
    } else if (act === "bus-new") this._bvOpen("bus", "new");
    else if (act === "bus-edit") this._bvOpen("bus", el.dataset.bvId);
    else if (act === "bus-save") this._bvSaveBus();
    else if (act === "bus-remove") this._bvRemove("bus", state.drawer?.id);
    else if (act === "print") this._bvPrint();
    else if (act === "listen") this._bvListen();
    else if (act === "listen-stop") this._bvStopListen();
    else if (act === "arrange") {
      Object.assign(state, { arrange: !state.arrange, error: "" });
      this._renderInstallation();
    } else if (act === "foreign-new") this._bvNewForeign(v);
    else if (act === "cabinet-new") this._bvSaveCabinet("", { name: this._t.inst.busv.cabinetDefault(v.data.cabinets.length + 1), note: "", rows: [{ name: this._t.inst.busv.rowDefault(1), te: 12 }] });
  },

  _busInput(e) {
    const filter = e.target.closest?.("select[data-bv-lrole], select[data-bv-lplace]");
    if (filter) {
      const L = this._in.bus.list;
      if (filter.matches("[data-bv-lrole]")) L.role = filter.value;
      else L.place = filter.value;
      saveList(L);
      this._renderInstallation();
      return true;
    }
    const seconds = e.target.closest?.("[data-bv-seconds]");
    if (seconds) {
      this._in.bus.seconds = Number(seconds.value);
      return true;
    }
    // the type of a new module decides its channels and fields: redraw the form with what was typed
    if (e.target.closest?.("[data-bv-form], [data-bv-busform]")) this._in.bus.dirty = true;
    const input = e.target.closest("[data-bv-form] [data-bvf]");
    if (!input || !["type", "role"].includes(input.dataset.bvf) || e.type !== "change") return false;
    const state = this._in.bus;
    // a type cleared by hand keeps what it was before the list opened (the focus handler cleared it for the list)
    if (input.dataset.bvf === "type" && !input.value.trim() && input.dataset.prev) input.value = input.dataset.prev;
    const module = this._bvReadModule();
    if (!module) return true;
    state.draft = { key: state.drawer?.id ?? "new", module };
    this._renderInstallation();
    return true;
  },

  _bvReadModule() {
    // the module as the drawer's form has it
    const state = this._in.bus;
    const form = this.shadowRoot.querySelector("#installation [data-bv-form]");
    if (!form) return null;
    const v = this._bv();
    const key = form.dataset.bvForm;
    const base = state.draft?.key === key ? state.draft.module : v.byId.get(key);
    if (!base) return null;
    const val = (name) => form.querySelector(`[data-bvf="${name}"]`);
    const text = (name) => (val(name) ? val(name).value.trim() : base[name] ?? "");
    const num = (name) => (val(name) && val(name).value.trim() !== "" ? Number(val(name).value) : null);
    const module = {
      ...base,
      type: text("type"),
      name: text("name"),
      role: val("role")?.value ?? base.role,
      bus: val("bus")?.value ?? base.bus,
      row: val("row")?.value || null,
      slot: num("slot"),
      te: num("te"),
      first_address: val("first_address") ? num("first_address") : base.first_address,
      power: val("power") ? text("power") : base.power,
      supply_watts: val("supply_watts") ? text("supply_watts") : base.supply_watts,
      legacy_range: val("legacy_range") ? text("legacy_range") : base.legacy_range,
      spacer_before: Boolean(val("spacer_before")?.checked),
      separator_after: Boolean(val("separator_after")?.checked),
      terminator: Boolean(val("terminator")?.checked),
      circuit: text("circuit"),
      fuse: text("fuse"),
      installed: text("installed"),
      note: text("note"),
    };
    const rows = [...form.querySelectorAll("[data-bvch]")];
    if (rows.length) {
      module.channels = rows.map((row) => {
        const n = Number(row.dataset.bvch);
        const link = row.querySelector('[data-bvc-f="link"]').value;
        const name = row.querySelector('[data-bvc-f="name"]').value.trim();
        const feedback = row.querySelector('[data-bvc-f="feedback_id"]').value.trim();
        const old = base.channels.find((c) => c.n === n) ?? {};
        const c = { n, entry_id: null, device_key: null, manual_id: null, name, function: old.function ?? "", feedback_id: feedback, unused: link === "unused" };
        const [kind, entryId, key] = link.split("|");
        if (kind === "ha") Object.assign(c, { entry_id: entryId, device_key: key });
        if (kind === "manual") Object.assign(c, { entry_id: entryId, manual_id: key });
        return c;
      }).filter((c) => c.device_key || c.manual_id || c.unused || c.name || c.feedback_id || c.function);
    }
    if (module.row && module.slot == null) module.slot = 1;
    if (!module.row) module.slot = null;
    return module;
  },

  async _bvCall(msg) {
    const state = this._in.bus;
    // a second click while a write is on its way would create the new item twice
    const write = msg.type === "enocean_eltako/installation/set";
    if (write && state.saving) return null;
    if (write) state.saving = true;
    try {
      const result = await this._hass.callWS(msg);
      state.error = "";
      return result;
    } catch (err) {
      state.error = this._t.inst.busv.errors[err?.code] ?? this._t.inst.busv.errors.other;
      this._renderInstallation();
      return null;
    } finally {
      if (write) state.saving = false;
    }
  },

  async _bvReload() {
    // the notes follow the store (bus address, supplies): the whole documentation is read again
    this._in.bus.dirty = false;
    await this._loadInstallation();
  },

  async _bvSaveModule() {
    const state = this._in.bus;
    const module = this._bvReadModule();
    if (!module) return;
    const { id, ...item } = module;
    const result = await this._bvCall({ type: "enocean_eltako/installation/set", kind: "module", item: id ? module : item });
    if (!result) return;
    state.draft = null;
    state.drawer = { type: "module", id: result.id };
    await this._bvReload();
  },

  _bvSaveBus() {
    const form = this.shadowRoot.querySelector("#installation [data-bv-busform]");
    if (!form) return;
    const v = this._bv();
    const id = form.dataset.bvBusform;
    const old = v.buses.find((b) => b.id === id) ?? { access: [] };
    const access = [...form.querySelectorAll("[data-bvb-access]")].filter((x) => x.checked).map((x) => {
      const had = old.access.find((a) => a.entry_id === x.dataset.bvbAccess);
      const gw = v.gws.get(x.dataset.bvbAccess);
      return had ?? { entry_id: x.dataset.bvbAccess, via: ["fgw14_usb", "fam14"].includes(gw?.model) ? "wired" : "radio" };
    });
    const read = (name) => form.querySelector(`[data-bvb="${name}"]`).value.trim();
    const item = { ...old, ...(id ? { id } : {}), name: read("name"), base_id: read("base_id"), note: read("note"), access };
    this._bvCall({ type: "enocean_eltako/installation/set", kind: "bus", item }).then(async (result) => {
      if (!result) return;
      Object.assign(this._in.bus, { id: result.id, drawer: null, history: [] });
      await this._bvReload();
    });
  },

  _bvRowAdd(cabinetId) {
    const card = this.shadowRoot.querySelector(`#installation [data-bv-cab="${CSS.escape(cabinetId)}"]`);
    if (!card) return;
    const rows = card.querySelectorAll("[data-bv-row]").length;
    const B = this._t.inst.busv;
    const html = `<div class="bv-rowedit" data-bv-row=""><input data-bvr="name" value="${esc(B.rowDefault(rows + 1))}" aria-label="${esc(B.rowName)}"><input data-bvr="te" type="number" min="1" max="48" step="1" value="12" aria-label="${esc(B.rowTe)}"><select class="bv-next" data-bvr="kind" aria-label="${esc(B.rowNext)}">${NEXT.map((k) => `<option value="${k}">${esc(B.next[k || "none"])}</option>`).join("")}</select><input class="bv-next" data-bvr="length" type="number" min="0" step="0.5" placeholder="${esc(B.metres)}" aria-label="${esc(B.metres)}"><button class="bv-ibtn" data-bv-rowdel="" title="${esc(B.rowRemove)}" aria-label="${esc(B.rowRemove)}">${svg(ICON.close)}</button></div>`;
    const last = [...card.querySelectorAll("[data-bv-row]")].pop();
    if (last) last.insertAdjacentHTML("afterend", html);
    else card.querySelector("[data-bv-rowadd]")?.closest(".bv-bar")?.insertAdjacentHTML("beforebegin", html);
  },

  async _bvSaveCabinet(cabinetId, given = null) {
    const state = this._in.bus;
    let item = given;
    if (!item) {
      const card = this.shadowRoot.querySelector(`#installation [data-bv-cab="${CSS.escape(cabinetId)}"]`);
      if (!card) return;
      const v = this._bv();
      const old = v.data.cabinets.find((c) => c.id === cabinetId) ?? {};
      const rows = [...card.querySelectorAll("[data-bv-row]")].map((row) => {
        const get = (name) => row.querySelector(`[data-bvr="${name}"]`).value.trim();
        const length = get("length");
        return { ...(row.dataset.bvRow ? { id: row.dataset.bvRow } : {}), name: get("name"), te: Number(get("te")) || 12, next: { kind: get("kind"), length_m: length === "" ? null : Number(length) } };
      });
      item = { ...old, id: cabinetId, name: card.querySelector('[data-bvc="name"]').value.trim(), note: card.querySelector('[data-bvc="note"]').value.trim(), rows };
    }
    state.cabinet = cabinetId;
    const result = await this._bvCall({ type: "enocean_eltako/installation/set", kind: "cabinet", item });
    if (!result) return;
    state.cabinet = "";
    await this._bvReload();
  },

  async _bvRemove(kind, id) {
    if (!id) return;
    const state = this._in.bus;
    if (kind === "cabinet") state.cabinet = id;
    const result = await this._bvCall({ type: "enocean_eltako/installation/remove", kind, item_id: id });
    if (!result) return;
    Object.assign(state, { drawer: null, history: [], cabinet: "" });
    if (kind === "bus") state.id = "";
    await this._bvReload();
  },

  async _bvMove(id, direction) {
    // arrange: swap with the neighbour, or half a TE at the end of the row; the server checks it
    const state = this._in.bus;
    const v = this._bv();
    state.cabinet = v.rows.get(v.byId.get(id)?.row)?.cab.id ?? "";
    const result = await this._bvCall({ type: "enocean_eltako/installation/move", module_id: id, direction });
    if (!result) return;
    state.hl = id;
    await this._bvReload();
    const tile = this.shadowRoot.querySelector(`#installation [data-bv-move="${CSS.escape(id)}|${direction}"]`);
    tile?.focus();
    setTimeout(() => {
      if (state.hl === id) {
        state.hl = "";
        this.shadowRoot.querySelectorAll("#installation .bvr-tile.hl").forEach((el) => el.classList.remove("hl"));
      }
    }, 1600);
  },

  async _bvTakeFeedback(ref) {
    // the suggested feedback ID (FAM14 base ID + address) written into the channel
    const [where, hint] = ref.split("|");
    const [mid, n] = where.split(":");
    const m = this._bv().byId.get(mid);
    if (!m) return;
    const channels = m.channels.map((c) => (String(c.n) === n ? { ...c, feedback_id: hint } : c));
    const result = await this._bvCall({ type: "enocean_eltako/installation/set", kind: "module", item: { ...m, channels } });
    if (result) await this._bvReload();
  },

  _bvNewForeign(v) {
    // a device on the rail that is not on the bus (circuit breaker, RCD, terminals): the first gap of the chosen cabinet
    const state = this._in.bus;
    const cab = v.data.cabinets.find((c) => c.id === state.cab) ?? v.data.cabinets[0];
    let row = null;
    let slot = null;
    for (const r of cab?.rows ?? []) {
      const taken = v.data.modules.filter((m) => m.row === r.id && m.slot != null).map((m) => [m.slot - (m.spacer_before ? 0.5 : 0), m.slot + this._bvTe(v, m)]);
      for (let at = 1; at <= r.te; at += 0.5) if (!taken.some(([a, b]) => at < b && a < at + 1)) {
        [row, slot] = [r.id, at];
        break;
      }
      if (row) break;
    }
    const blank = { id: "", bus: v.bus?.id ?? "", type: "LS", role: "foreign", name: "", row, slot, te: 1, spacer_before: false, separator_after: false, terminator: false, first_address: null, supply_watts: "", legacy_range: "", legacy_location: "", placeholder: false, power: "", circuit: "", fuse: "", installed: "", revision: "", note: "", channels: [] };
    state.draft = { key: "new", module: blank };
    this._bvOpen("module", "new");
  },

  async _bvAssign(ref) {
    // a device of Home Assistant that looks like a bus device gets a module of its own (one channel)
    const [entryId, key] = ref.split("|");
    const v = this._bv();
    const found = v.devices.get(`${entryId}|${key}`);
    const bus = v.buses.find((b) => b.access.some((a) => a.entry_id === entryId)) ?? v.bus;
    if (!bus) return;
    const item = { bus: bus.id, type: found?.d.model ?? "", channels: [{ n: 1, entry_id: entryId, device_key: key }] };
    const result = await this._bvCall({ type: "enocean_eltako/installation/set", kind: "module", item });
    if (!result) return;
    Object.assign(this._in.bus, { drawer: { type: "module", id: result.id }, history: [] });
    await this._bvReload();
  },
};
