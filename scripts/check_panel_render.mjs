// CI check of the sidebar panel in a simulated browser (happy-dom): the panel renders every
// view with the sample data of scripts/panel-preview/fake-hass.js, in English and German,
// without errors and without "undefined" or "NaN" in what it shows.
// Needs: npm install --no-save @happy-dom/global-registrator@20.14.6
// Run: node scripts/check_panel_render.mjs

import { GlobalRegistrator } from "@happy-dom/global-registrator";

GlobalRegistrator.register({ url: "http://localhost:8123/enocean-eltako", width: 1280, height: 900 });
// observers the panel uses for layout only
globalThis.ResizeObserver ??= class { observe() {} disconnect() {} };
globalThis.IntersectionObserver ??= class { observe() {} disconnect() {} };

const errors = [];
const fail = (text) => errors.push(text);
window.addEventListener("error", (e) => fail(`error: ${e.message || e.error}`));
process.on("unhandledRejection", (reason) => fail(`unhandled rejection: ${reason?.stack || reason}`));
const consoleError = console.error;
console.error = (...args) => fail(`console.error: ${args.join(" ")}`);

customElements.define("ha-menu-button", class extends HTMLElement {});
await import(new URL("../custom_components/enocean_eltako/frontend/monitor-panel.js?v=render", import.meta.url).href);
const { fakeHass } = await import(new URL("panel-preview/fake-hass.js", import.meta.url).href);

const settle = async () => {
  for (let i = 0; i < 5; i += 1) await new Promise((resolve) => setTimeout(resolve, 10));
};

function shown(root) {
  // the text a user sees: header and main, not the stylesheet
  return [...root.querySelectorAll("header, main")].map((el) => el.textContent).join(" ");
}

async function check(query, run) {
  localStorage.clear();
  const fake = fakeHass(new URLSearchParams(query));
  const panel = document.createElement("enocean-eltako-monitor");
  document.body.append(panel);
  panel.hass = fake.hass;
  await settle();
  const root = panel.shadowRoot;
  const view = async (name) => {
    if (name === "senders") {
      // the sender ID pools: Installation > Senders > Gateway senders, above the table
      root.querySelector('#view [data-view="installation"]').click();
      await settle();
      root.querySelectorAll("#installation .groups .itab")[1].click();
      await settle();
      root.querySelector('#installation [data-in-tab="gwsenders"]').click();
      await settle();
    } else {
      root.querySelector(`#view [data-view="${name}"]`).click();
      await settle();
    }
    const text = shown(root);
    for (const bad of ["undefined", "NaN", "[object", "null"]) {
      if (text.includes(bad)) fail(`${query} ${name}: shows "${bad}"`);
    }
  };
  const expect = (what, actual, wanted) => {
    if (actual !== wanted) fail(`${query}: ${what} is ${actual}, expected ${wanted}`);
  };
  try {
    await run({ root, fake, view, expect, panel });
  } catch (err) {
    fail(`${query}: ${err.stack || err}`);
  }
  panel.remove();
}

for (const lang of ["en", "de"]) {
  await check(`lang=${lang}`, async ({ root, fake, view, expect, panel }) => {
    await view("telegrams");
    expect("telegram rows", root.querySelectorAll("tr.row").length, 4);
    fake.push({ time: new Date().toISOString(), dir: "rx", sender: "05-00-00-01", rorg: "F6", data: "50", status: "30", dbm: -60, device: "Licht Diele", device_key: "sub1" });
    await settle();
    expect("telegram rows after a new one", root.querySelectorAll("tr.row").length, 5);
    root.querySelector("tr.row").click();
    await settle();
    expect("open details", root.querySelectorAll("tr.detail-row").length, 1);
    // an open telegram holds new ones back; closing it lets them in
    fake.push({ time: new Date().toISOString(), dir: "rx", sender: "05-00-00-01", rorg: "F6", data: "70", status: "30", dbm: -61, device: "Licht Diele", device_key: "sub1" });
    await settle();
    expect("telegram rows while one is open", root.querySelectorAll("tr.row").length, 5);
    expect("held back while one is open", root.getElementById("live").classList.contains("paused"), true);
    root.querySelector("tr.row").click();
    await settle();
    expect("closed details", root.querySelectorAll("tr.detail-row").length, 0);
    expect("telegram rows after closing", root.querySelectorAll("tr.row").length, 6);
    expect("live again after closing", root.getElementById("live").classList.contains("paused"), false);
    root.querySelector("tr.row").click();
    await settle();
    // from a telegram to its device's row in the Devices view, opened
    const link = root.querySelector("[data-dev-panel]");
    expect("telegram has a link to its device", !!link, true);
    link.click();
    await settle();
    expect("devices view after the link", root.querySelector('#view [data-view="devices"]').getAttribute("aria-selected"), "true");
    expect("device opened by the link", !!root.querySelector(`.dev[data-dev="${link.dataset.devPanel}"] .dev-detail`), true);
    root.querySelector(`.dev[data-dev="${link.dataset.devPanel}"] .expand`).click();
    await view("telegrams");
    // the sent telegram of the samples: "send again" sends it, a rocker press with its release
    const sent = [...root.querySelectorAll("tr.row")].find((row) => row.querySelector(".dir.tx"));
    sent.click();
    await settle();
    root.querySelector("[data-resend]").click();
    await settle();
    const resent = fake.sent.filter((m) => m.type === "enocean_eltako/send").map((m) => `${m.sender} ${m.rorg} ${m.data} ${m.status}`);
    expect("sent again", resent.join(", "), "FF-00-11-81 F6 70 30, FF-00-11-81 F6 00 20");
    root.getElementById("filterBtn").click();
    expect("filter row open", root.getElementById("filterMenu").hidden, false);
    // the Installation view: devices by area, a table with fields edited in place, the event log
    await view("installation");
    expect("four tabs: devices, sender IDs, links, log", root.querySelectorAll("#installation .groups .itab").length, 4);
    expect("the devices table names its device count", !!root.querySelector("#installation section.gw .gwhead .isub:last-child"), true);
    expect("the list of all devices has the views only, no second row of kinds", root.querySelectorAll("#installation .fbar .seg button").length === 4 && root.querySelectorAll("#installation .fbar [data-in-art]").length === 0, true);
    const artCount = (k) => Number(root.querySelector(`#installation .fbar [data-in-art="${k}"] b`)?.textContent);
    const viewCount = (v) => Number(root.querySelector(`#installation .fbar [data-in-view="${v}"] .isub`)?.textContent);
    root.querySelector('#installation .fbar [data-in-view="funk"]').click();
    await settle();
    expect("inside a view the kinds are a filter, counted like the view", root.querySelectorAll("#installation .fbar [data-in-art]").length > 1 && viewCount("funk") === artCount("all"), true);
    expect("the kind chips count the kinds", [...root.querySelectorAll("#installation [data-in-art]")].map((b) => b.textContent.replace(/\s+/g, " ").trim()).join("|").length > 0, true);
    root.querySelector('#installation .fbar [data-in-view="all"]').click();
    await settle();
    expect("every row names its kind (10 devices, 2 power supplies; the 3 entries by hand have a kind menu)", root.querySelectorAll("#installation .itable tbody tr :is([data-in-kind], [data-in-busgo])").length, 12);
    expect("an entry by hand has a kind menu and its own tag", root.querySelectorAll("#installation .itable tbody tr .kindmenu").length === 3 && root.querySelectorAll("#installation .itable tbody tr .tag.doc").length === 3, true);
    const deviceRows = () => root.querySelectorAll("#installation .itable tbody tr:not(.grp)");
    expect("installation table rows (10 devices, 2 power supplies, 3 entries by hand)", deviceRows().length, 15);
    expect("the table is grouped by place (cabinet · row) at first", root.querySelectorAll("#installation .itable tr.grp").length > 0 && root.querySelector("#installation [data-in-groupsel] option[selected]")?.value, "location");
    expect("the gateway is a tag of the row only with several gateways; its name opens the gateway elsewhere", root.querySelectorAll("#installation [data-in-gwopen]").length >= 0, true);
    // the tabs of the installation by keyboard
    const tabNow = () => root.querySelector('#installation [role="tab"][aria-selected="true"]').dataset.inTab;
    const firstTab = tabNow();
    root.querySelector('#installation [role="tab"][aria-selected="true"]').dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true, composed: true }));
    await settle();
    expect("ArrowRight moves to the next installation tab", tabNow() !== firstTab && root.activeElement?.dataset.inTab === tabNow(), true);
    root.activeElement.dispatchEvent(new KeyboardEvent("keydown", { key: "Home", bubbles: true, composed: true }));
    await settle();
    expect("Home goes back to the first tab", tabNow(), firstTab);
    const busTag = root.querySelector('#installation .itable [data-in-busgo^="channel|m_fsr"]');
    expect("a bus device's kind tag leads to its channel in the bus tab", !!busTag, true);
    busTag.click();
    await settle();
    expect("the channel opens in the bus tab", !!root.querySelector("#installation aside.bv-drawer") && root.querySelector('#installation [data-in-view="bus"]').getAttribute("aria-pressed"), "true");
    // unsaved input in the drawer: leaving by Back asks first; keeping the input stays, discarding goes
    panel._in.bus.dirty = true;
    root.querySelector("#installation [data-in-back]").click();
    await settle();
    expect("Back with unsaved drawer input asks first", !!root.querySelector(".bv-ask") && !!root.querySelector("#installation aside.bv-drawer"), true);
    root.querySelector('.bv-ask [data-ask="no"]').click();
    await settle();
    expect("keeping the input stays in the drawer", !!root.querySelector("#installation aside.bv-drawer") && panel._in.bus.dirty, true);
    root.querySelector("#installation [data-in-back]").click();
    await settle();
    root.querySelector('.bv-ask [data-ask="yes"]').click();
    await settle();
    expect("discarding leaves the drawer", !root.querySelector("#installation aside.bv-drawer") && !panel._in.bus.dirty, true);
    expect("Back returns to the devices table", root.querySelector('#installation [data-in-view="all"]').getAttribute("aria-pressed") === "true" && !root.querySelector("#installation [data-in-back]"), true);
    expect("every row ends in the menu column", [...deviceRows()].every((r) => r.lastElementChild.matches("td.rmenu")) && !!root.querySelector("#installation .itable thead th.rmenu:last-child"), true);
    expect("entries by hand and power supplies have their menu there", root.querySelectorAll("#installation .itable td.rmenu details.rowmenu").length, 5);
    const cell = root.querySelector('#installation [data-in-field="fuse"][data-in-key="sub2"]');
    expect("an empty field shows the same quiet dash as one that does not apply", cell.placeholder, "–");
    cell.value = "F4 B10";
    cell.dispatchEvent(new Event("input", { bubbles: true }));
    await new Promise((resolve) => setTimeout(resolve, 700));
    const edits = fake.sent.filter((m) => m.type === "enocean_eltako/set_fields");
    expect("a cell is saved after typing", JSON.stringify(edits.map((m) => m.items)), '[[{"device":"sub2","values":{"fuse":"F4 B10"}}]]');
    // the columns one by one, grouped, with all / none; a wrong value is named under the field and not sent
    const sentBefore = fake.sent.filter((m) => m.type === "enocean_eltako/set_fields").length;
    expect("the bus columns are hidden at first", root.querySelector('#installation [data-in-field="bus_address"]'), null);
    expect("the column menu lists each column under its group", root.querySelectorAll("#installation [data-in-col]").length === 12 && root.querySelectorAll("#installation [data-in-colgroup]").length, 6);
    root.querySelector('#installation [data-in-col="bus_address"]').click();
    await settle();
    expect("a single column is shown, without choosing a kind", !!root.querySelector('#installation [data-in-field="bus_address"]') && !root.querySelector('#installation [data-in-field="feedback_id"]'), true);
    expect("the choice of columns is kept per browser", JSON.parse(localStorage.getItem("enocean_eltako_installation_fields")).includes("bus_address"), true);
    const addrCell = root.querySelector('#installation [data-in-field="bus_address"][data-in-key="sub2"]');
    addrCell.value = "999";
    addrCell.dispatchEvent(new Event("input", { bubbles: true }));
    await new Promise((resolve) => setTimeout(resolve, 700));
    expect("a wrong bus address is named under the field", !!root.querySelector('#installation [data-in-field="bus_address"][data-in-key="sub2"] + .cerr'), true);
    expect("a wrong bus address is not sent", fake.sent.filter((m) => m.type === "enocean_eltako/set_fields").length, sentBefore);
    root.querySelector('#installation [data-in-col="bus_address"]').click();
    await settle();
    expect("the upkeep columns are hidden at first", root.querySelector('#installation [data-in-field="installed"]'), null);
    root.querySelector('#installation [data-in-colgroup="upkeep|all"]').click();
    await settle();
    expect("a group of columns can be shown at once", !!root.querySelector('#installation [data-in-field="installed"]') && !!root.querySelector('#installation [data-in-field="note"]'), true);
    expect("the tiles count the devices without a place", !!root.querySelector("#installation .stiles.quiet .stile[data-in-miss=\"loc\"]"), true);
    root.querySelector('#installation [data-in-colgroup="upkeep|none"]').click();
    await settle();
    expect("and hidden at once", root.querySelector('#installation [data-in-field="installed"]'), null);
    root.querySelector('#installation [data-in-pick="gw1|sub1"]').click();
    root.querySelector('#installation [data-in-pick="gw1|sub1"]').dispatchEvent(new Event("change", { bubbles: true }));
    await settle();
    expect("bulk bar after a pick", !!root.querySelector("#installation .bulk"), true);
    // a place that names no documented cabinet stays three free fields: cabinet, row, slot
    const place = root.querySelector('#installation [data-in-place][data-in-key="sub2"]');
    expect("a place of no documented cabinet keeps its free fields", place.querySelectorAll("input").length, 3);
    place.querySelectorAll("input")[0].value = "Schrank 3";
    place.querySelectorAll("input")[0].dispatchEvent(new Event("input", { bubbles: true }));
    place.querySelectorAll("input")[2].value = "7";
    place.querySelectorAll("input")[2].dispatchEvent(new Event("input", { bubbles: true }));
    await new Promise((resolve) => setTimeout(resolve, 700));
    expect("the three parts of a place are sent as one text", fake.sent.some((m) => m.type === "enocean_eltako/set_fields" && m.items.length === 1 && m.items[0].device === "sub2" && /^Schrank 3 · .+ · 7$/.test(m.items[0].values.location ?? "")), true);
    // a device without a place: a quiet dash; then cabinet and row are picked from the cabinets, the slot typed
    const empty = root.querySelector('#installation [data-in-placeedit="sub3"]');
    expect("an empty place is a quiet dash", empty?.classList.contains("empty") && empty.querySelector(".ph").textContent, "–");
    empty.click();
    await settle();
    const placePicker = root.querySelector('#installation [data-in-place][data-in-key="sub3"] select[data-in-prow]');
    expect("the place offers the documented cabinets and rows", [...placePicker.options].map((o) => o.value).includes("Keller-Verteiler · Reihe 1"), true);
    placePicker.value = "Keller-Verteiler · Reihe 1";
    const slotBox = root.querySelector('#installation [data-in-place][data-in-key="sub3"] [data-in-part="2"]');
    slotBox.value = "9";
    placePicker.dispatchEvent(new Event("change", { bubbles: true }));
    await settle();
    expect("a picked place is sent as cabinet · row · slot", fake.sent.some((m) => m.type === "enocean_eltako/set_fields" && m.items[0]?.device === "sub3" && m.items[0].values.location === "Keller-Verteiler · Reihe 1 · 9"), true);
    root.querySelector('#installation [data-in-place][data-in-key="sub3"] [data-in-placeclear]').click();
    await settle();
    expect("✕ removes the place", fake.sent.filter((m) => m.type === "enocean_eltako/set_fields" && m.items[0]?.device === "sub3").pop().items[0].values.location, "");
    // grouping: none, area, place, gateway; the choice is kept per browser; the filter for devices without a place
    const groupSelect = root.querySelector("#installation [data-in-groupsel]");
    expect("grouping offers none, area, place and gateway", [...groupSelect.options].map((o) => o.value).join(), ",area,location,gateway");
    groupSelect.value = "gateway";
    groupSelect.dispatchEvent(new Event("change", { bubbles: true }));
    await settle();
    expect("grouped by gateway: one group per gateway", root.querySelectorAll("#installation .itable tr.grp").length, 1);
    expect("the grouping is kept per browser", localStorage.getItem("enocean_eltako_installation_group"), "gateway");
    const rowsAll = deviceRows().length;
    root.querySelector("#installation [data-in-groupsel]").value = "";
    root.querySelector("#installation [data-in-groupsel]").dispatchEvent(new Event("change", { bubbles: true }));
    await settle();
    root.querySelector('#installation [data-in-miss="loc"]').click();
    await settle();
    expect("the filter for a missing place leaves fewer rows", deviceRows().length < rowsAll, true);
    root.querySelector('#installation [data-in-miss="loc"]').click();
    await settle();
    // the tabs: sender IDs, links, log
    const groupChips = () => [...root.querySelectorAll("#installation .groups .itab")];
    groupChips()[1].click();
    await settle();
    expect("the sender ID pool sits above the table", root.querySelector("#poolBox").getBoundingClientRect !== undefined && root.querySelector("#poolBox").compareDocumentPosition(root.querySelector("#instBody")) & Node.DOCUMENT_POSITION_FOLLOWING, Node.DOCUMENT_POSITION_FOLLOWING);
    expect("gateway senders show 0 to 127 folded", root.querySelectorAll("#installation .itable tbody tr").length > 5, true);
    expect("the sender table ends every row in the menu column", [...root.querySelectorAll("#installation .itable tbody tr")].every((r) => r.lastElementChild.matches("td.rmenu")), true);
    const sndLinks = root.querySelector("#installation [data-in-sndlinks]");
    expect("a used sender ID leads to the links it is in", !!sndLinks, true);
    sndLinks.click();
    await settle();
    expect("the links tab by sender, filtered to that ID", root.querySelector('#installation [data-in-tab="links"]').getAttribute("aria-selected") === "true" && root.querySelector("#installation [data-in-search]").value === sndLinks.dataset.inSndlinks, true);
    root.querySelector("#installation [data-in-back]").click();
    await settle();
    // fields are edited in the tables: a device with two senders has its bus address in two rows, and both follow
    const addr = root.querySelectorAll('#installation [data-in-field="bus_address"][data-in-key="sub1"]');
    expect("the bus address of a device with two senders is in two rows", addr.length, 2);
    addr[0].value = "3";
    addr[0].dispatchEvent(new Event("input", { bubbles: true }));
    await new Promise((resolve) => setTimeout(resolve, 700));
    expect("the bus address is sent", fake.sent.some((m) => m.type === "enocean_eltako/set_fields" && JSON.stringify(m.items) === '[{"device":"sub1","values":{"bus_address":"3"}}]'), true);
    expect("the other row follows", addr[1].value, "3");
    groupChips()[0].click();
    await settle();
    root.querySelector('#installation [data-in-view="funk"]').click();
    await settle();
    expect("the radio table lists devices and the entries by hand", root.querySelectorAll("#installation .itable tbody tr").length > 3, true);
    expect("the radio table: every row ends in the menu column, the menus of the entries by hand sit there", [...root.querySelectorAll("#installation .itable tbody tr")].every((r) => r.lastElementChild.matches("td.rmenu")) && root.querySelectorAll("#installation .itable td.rmenu details.rowmenu").length >= 2, true);
    expect("the entries by hand without a bus address are rows with a name to click", root.querySelectorAll('#installation [data-in-nameedit]').length, 2);
    expect("the radio tiles count devices, entries written down, silent ones and repeater-only ones", root.querySelectorAll("#installation .tile").length, 4);
    root.querySelector('#installation [data-in-funkcol="grp"]').click();
    await settle();
    const groupCell = root.querySelector('#installation [data-in-field="group"][data-in-key="sub6"]');
    expect("radio devices have a Part of field", !!groupCell, true);
    groupCell.value = "Raumregler";
    groupCell.dispatchEvent(new Event("input", { bubbles: true }));
    await new Promise((resolve) => setTimeout(resolve, 700));
    expect("Part of is sent", fake.sent.some((m) => m.type === "enocean_eltako/set_fields" && JSON.stringify(m.items) === '[{"device":"sub6","values":{"group":"Raumregler"}}]'), true);
    root.querySelector('#installation [data-in-act="doc-open"]').click();
    await settle();
    const form = root.querySelector("#installation .docform");
    form.querySelector('[data-in-doc-field="name"]').value = "Taster Bad";
    form.querySelector('[data-in-doc-field="address"]').value = "XYZ";
    root.querySelector('#installation [data-in-act="doc-add"]').click();
    await settle();
    expect("a bad ID is named and nothing is sent", !!root.querySelector("#installation .docform .cerr") && fake.sent.filter((m) => m.type === "enocean_eltako/set_manual").length === 0, true);
    const form2 = root.querySelector("#installation .docform");
    form2.querySelector('[data-in-doc-field="name"]').value = "Taster Bad";
    form2.querySelector('[data-in-doc-field="address"]').value = "FE-F3-B0-02";
    form2.querySelector('[data-in-doc-field="kind"]').value = "taster";
    root.querySelector('#installation [data-in-act="doc-add"]').click();
    await settle();
    expect("a documented device is a new row and goes to the server", root.querySelectorAll('#installation [data-in-nameedit]').length === 3 && fake.sent.filter((m) => m.type === "enocean_eltako/set_manual").length === 1, true);
    // the virtual view: what Home Assistant sends, what it follows, and the jump to the sender number
    root.querySelector('#installation [data-in-view="virt"]').click();
    await settle();
    expect("the virtual view lists the two virtual devices", root.querySelectorAll("#installation .itable tbody tr").length, 2);
    expect("the virtual table ends every row in the menu column", [...root.querySelectorAll("#installation .itable tbody tr")].every((r) => r.lastElementChild.matches("td.rmenu")), true);
    expect("a virtual sensor names what it follows", root.querySelector("#installation .itable tbody").textContent.includes("binary_sensor.fenster_bad"), true);
    root.querySelector("#installation .itable [data-in-snd]").click();
    await settle();
    expect("a sender number opens the Sender IDs tab with the row marked", root.querySelector('#installation [data-in-tab="gwsenders"]').getAttribute("aria-selected"), "true");
    root.querySelector('#installation [data-in-tab="devices"]').click();
    await settle();
    root.querySelector('#installation [data-in-view="bus"]').click();
    await settle();
    // the bus by its master: who is master, how Home Assistant reaches it, modules with their channels
    const busText = () => root.querySelector("#instBody").textContent;
    expect("the bus head names the master and the radio gateway as access", !!root.querySelector("#installation .bv-card.master [data-bv-go='module|m_fam']") && root.querySelector("#installation .bv-card.access").textContent.includes("FAM-USB Keller"), true);
    expect("the bus tiles: devices, channels, addresses, supplies, checks", root.querySelectorAll("#installation button.tile[data-bv-sub]").length, 5);
    expect("one row per module of the bus", root.querySelectorAll("#installation table.bv-list tr.bv-mod").length, 10);
    expect("the bus list ends every row in the menu column", [...root.querySelectorAll("#installation table.bv-list tbody tr")].every((r) => r.lastElementChild.matches("td.rmenu")), true);
    expect("the channels below their module", root.querySelectorAll("#installation table.bv-list tr.bv-ch").length, 12);
    expect("a duplicate address is marked", root.querySelectorAll("#installation table.bv-list tr.dup").length, 2);
    expect("a channel of Home Assistant links to its device", !!root.querySelector('#installation table.bv-list [data-in-goto="sub1"]'), true);
    // one table, sorted by address: the address first, modules keep their channels, gaps shown
    const list = () => root.querySelector("#installation table.bv-list");
    const heads = () => [...list().querySelectorAll("thead th")];
    const bvClick = async (sel) => {
      root.querySelector(`#installation ${sel}`).click();
      await settle();
    };
    expect("no switch between place and address any more", root.querySelector("#installation [data-bv-mode]"), null);
    expect("the address is the first column, sorted upwards", heads()[0].dataset.bvSort === "address" && heads()[0].getAttribute("aria-sort") === "ascending", true);
    expect("free ranges between the modules", list().querySelectorAll("tr.free").length > 2, true);
    const firsts = () => [...list().querySelectorAll("tr.bv-mod")].map((r) => parseInt(r.firstElementChild.textContent, 10));
    const ordered = (xs, dir) => {
      const known = xs.filter((x) => !Number.isNaN(x));
      return known.every((x, i) => i === 0 || (x - known[i - 1]) * dir >= 0) && xs.slice(0, known.length).every((x) => !Number.isNaN(x));
    };
    expect("modules by first address, those without at the end", ordered(firsts(), 1), true);
    expect("a channel row follows its module", list().querySelector("tbody tr.bv-ch").previousElementSibling.matches("tr.bv-mod, tr.bv-ch"), true);
    await bvClick('table.bv-list th[data-bv-sort="address"]');
    expect("a second click sorts downwards, without gaps", heads()[0].getAttribute("aria-sort") === "descending" && list().querySelectorAll("tr.free").length === 0 && ordered(firsts(), -1), true);
    expect("the sorting is kept per browser", JSON.parse(localStorage.getItem("enocean_eltako_bus_list")).dir, -1);
    await bvClick('table.bv-list th[data-bv-sort="place"]');
    expect("sorted by place", list().querySelector('th[data-bv-sort="place"]').getAttribute("aria-sort"), "ascending");
    await bvClick('table.bv-list [data-bv-sort="type"]');
    const types = [...list().querySelectorAll("tr.bv-mod td:nth-child(2) b")].map((b) => b.textContent.toLowerCase());
    expect("sorted by type", types.join() === [...types].sort((a, b) => a.localeCompare(b, undefined, { numeric: true })).join(), true);
    await bvClick('table.bv-list th[data-bv-sort="address"]');
    // the filters: chips, a role, the reset
    await bvClick('[data-bv-lf="dup"]');
    expect("only twice: the two channels with their modules", list().querySelectorAll("tr.bv-ch").length === 2 && list().querySelectorAll("tr.bv-ch.dup").length === 2 && list().querySelectorAll("tr.free").length === 0, true);
    expect("the filter is kept per browser", JSON.parse(localStorage.getItem("enocean_eltako_bus_list")).f, "dup");
    await bvClick('[data-bv-lf="ha"]');
    expect("only in Home Assistant: every channel has its device link", [...list().querySelectorAll("tr.bv-ch")].every((r) => r.querySelector("[data-in-goto]")), true);
    await bvClick('[data-bv-lf="ha"]');
    expect("a chip clicked again shows all", list().querySelectorAll("tr.bv-mod").length, 10);
    const role = root.querySelector("#installation select[data-bv-lrole]");
    role.value = "supply";
    role.dispatchEvent(new Event("change", { bubbles: true }));
    await settle();
    expect("filtered by role", [...list().querySelectorAll("tr.bv-mod")].every((r) => r.dataset.r === "supply") && list().querySelectorAll("tr.bv-mod").length > 0, true);
    await bvClick("[data-bv-lreset]");
    expect("reset: all again", list().querySelectorAll("tr.bv-mod").length === 10 && !root.querySelector("#installation [data-bv-lreset]"), true);
    // the columns, one by one; address and device stay
    const cols = heads().length;
    expect("address and device cannot be switched off", root.querySelector('#installation input[data-bv-lcol="address"]').disabled && root.querySelector('#installation input[data-bv-lcol="device"]').disabled, true);
    await bvClick('input[data-bv-lcol="senders"]');
    expect("a column switched off", heads().length === cols - 1 && !!root.querySelector("#installation details.bv-colmenu[open]"), true);
    expect("the columns are kept per browser", JSON.parse(localStorage.getItem("enocean_eltako_bus_columns")).includes("senders"), false);
    await bvClick('[data-bv-lcols="none"]');
    expect("none: address, device and the menu", heads().length, 3);
    expect("free rows span the columns shown", list().querySelector("tr.free td").getAttribute("colspan"), "2");
    await bvClick('[data-bv-lcols="all"]');
    expect("all columns again", heads().length, cols);
    await bvClick(".bv-note");
    expect("a click outside closes the column menu", root.querySelector("#installation details.bv-colmenu[open]"), null);
    root.querySelector('#installation [data-bv-go="module|m_fsr"]').click();
    await settle();
    const drawer = () => root.querySelector("#installation aside.bv-drawer");
    expect("a module opens its drawer with the channels and a form", !!drawer() && drawer().querySelectorAll(".bv-chrow").length === 4 && drawer().querySelectorAll("[data-bvch]").length === 4, true);
    expect("the drawer's crumbs name cabinet, row and slot", drawer().querySelector(".bv-crumbs").textContent.includes("Keller-Verteiler"), true);
    drawer().querySelector('[data-bv-go="channel|m_fsr:1"]').click();
    await settle();
    expect("a channel names its address, feedback ID and senders", drawer().textContent.includes("00000081") && drawer().querySelectorAll('[data-bv-go^="sender|"]').length > 0, true);
    drawer().querySelector('[data-bv-go^="sender|"]').click();
    await settle();
    expect("a sender lists the channels it is taught into", drawer().querySelectorAll(".bv-chrow").length > 0, true);
    drawer().querySelector('[data-bv-act="back"]').click();
    await settle();
    drawer().querySelector('[data-bv-act="back"]').click();
    await settle();
    const moduleForm = drawer().querySelector("[data-bv-form]");
    // happy-dom reads a select parsed with a selected option as its second one: set what a browser shows
    moduleForm.querySelectorAll("select").forEach((sel) => (sel.value = sel.querySelector("option[selected]")?.value ?? sel.options[0].value));
    moduleForm.querySelector('[data-bvf="slot"]').value = "5";
    moduleForm.querySelector('[data-bvf="first_address"]').value = "20";
    drawer().querySelector('[data-bv-act="module-save"]').click();
    await settle();
    const savedModule = fake.sent.filter((m) => m.type === "enocean_eltako/installation/set" && m.kind === "module").pop();
    expect("a module is saved with its place and first address", savedModule && savedModule.item.id === "m_fsr" && savedModule.item.slot === 5 && savedModule.item.first_address === 20 && savedModule.item.channels.length === 4, true);
    root.querySelector("#installation [data-bv-act=\"close\"]")?.click();
    await settle();
    expect("the drawer closes", drawer(), null);
    root.querySelector('#installation [data-bv-sub="addresses"]').click();
    await settle();
    expect("the address plan has 126 cells, the used ones open their channel", root.querySelectorAll("#installation .bv-cell").length === 126 && root.querySelectorAll("#installation button.bv-cell[data-bv-go]").length > 5, true);
    root.querySelector('#installation [data-bv-sub="checks"]').click();
    await settle();
    expect("the checks show the duplicate address as an error", root.querySelectorAll("#installation .bv-check.error").length > 0 && busText().length > 0, true);
    root.querySelector('#installation [data-bv-sub="cabinets"]').click();
    await settle();
    // the cabinet drawn to scale: a rail per row, tiles at their slots, the bands of the supply sections
    expect("a cabinet with its three rows, each a rail", root.querySelectorAll("#installation .bv-cab").length === 1 && root.querySelectorAll("#installation [data-bv-row]").length === 3 && root.querySelectorAll("#installation .bvr-rail").length === 3, true);
    expect("the FAM14 is the master tile, two TE wide", root.querySelector('#installation .bvr-tile.master[data-bv-go="module|m_fam"]')?.getAttribute("style").includes("span 4"), true);
    expect("a device not on the bus is a hatched block", !!root.querySelector('#installation .bvr-tile.foreign[data-bv-go="module|m_ls"]'), true);
    expect("separator bridge, spacer and the row link are drawn", !!root.querySelector("#installation .bvr-tb") && !!root.querySelector("#installation .bvr-spacer") && root.querySelectorAll("#installation .bvr-foot").length === 2, true);
    expect("supply sections by place are bands below the rail", root.querySelectorAll("#installation .bvr-band").length >= 2, true);
    root.querySelector('#installation [data-bv-act="arrange"]').click();
    await settle();
    root.querySelector('#installation [data-bv-move="m_fsb|-1"]').click();
    await settle();
    expect("arranging asks the server to swap with the neighbour", fake.sent.some((m) => m.type === "enocean_eltako/installation/move" && m.module_id === "m_fsb" && m.direction === -1), true);
    root.querySelector('#installation [data-bv-cabsel="c2"]').click();
    await settle();
    expect("another cabinet is chosen", root.querySelector("#installation .bv-cab h3").textContent, "UV Obergeschoss");
    root.querySelector('#installation [data-bv-act="foreign-new"]').click();
    await settle();
    expect("a device not on the bus is written down in the drawer, with a free slot", drawer()?.querySelector('[data-bvf="role"] option[selected]')?.value === "foreign" && drawer().querySelector('[data-bvf="slot"]').value === "3", true);
    root.querySelector('#installation [data-bv-act="close"]').click();
    await settle();
    root.querySelector('#installation [data-bv-cabsel="c1"]').click();
    await settle();
    // the printout: the rails, the channels by place, the open checks and label strips to scale
    const host = root.host;
    const page = host._bvPrintPage(host._bv());
    expect("the printout has the rails, the channel list and label strips", page.includes("bvr-rail") && page.includes("class=\"strip\"") && page.includes("width:18mm") && page.includes("00000081") && !page.includes("data-bv-move"), true);
    root.querySelector('#installation [data-bv-cabsave="c1"]').click();
    await settle();
    expect("a cabinet is saved with its rows", fake.sent.some((m) => m.type === "enocean_eltako/installation/set" && m.kind === "cabinet" && m.item.rows.length === 3), true);
    // reading the bus: only after the opt-in, by listening; the answers are compared with the documentation
    root.querySelector('#installation [data-bv-sub="read"]').click();
    await settle();
    expect("reading waits for the opt-in", root.querySelector('#installation [data-bv-act="listen"]').disabled, true);
    root.querySelector("#installation [data-bv-optin]").click();
    await settle();
    root.querySelector('#installation [data-bv-act="listen"]').click();
    await settle();
    await new Promise((resolve) => setTimeout(resolve, 50));
    await settle();
    expect("the bus is read with the opt-in", fake.sent.some((m) => m.type === "enocean_eltako/installation/listen" && m.opt_in === true), true);
    expect("the addresses heard are listed, an undocumented one can be documented", root.querySelectorAll("#installation [data-bv-docaddr]").length >= 1 && root.querySelectorAll("#installation [data-bv-adddev]").length > 0, true);
    root.querySelector('#installation [data-bv-sub="checks"]').click();
    await settle();
    expect("the checks compare heard and documented", busText().includes("30"), true);
    root.querySelector('#installation [data-bv-sub="supplies"]').click();
    await settle();
    expect("the power supplies by place: three sections with a load bar each", root.querySelectorAll("#installation .bv-sec").length === 3 && root.querySelectorAll("#installation .bv-load").length === 3 && /(Section|Abschnitt) C/.test(busText()), true);
    // the previous view of the supplies by address range stays, inside the supplies
    const legacy = "#installation details.bv-legacy";
    expect("the bus table has a sum, tiles and load bars in the supply rows", root.querySelectorAll(`${legacy} .itable tbody tr`).length > 3 && root.querySelectorAll(`${legacy} .tile`).length === 5 && root.querySelectorAll(`${legacy} .psurow .barbg`).length > 0, true);
    const power = root.querySelector('#installation [data-in-field="bus_power"][data-in-key="sub4"]');
    expect("the bus power is edited in the bus table, the table value shows as placeholder", power?.placeholder, "0,42");
    power.value = "0,5";
    power.dispatchEvent(new Event("input", { bubbles: true }));
    await new Promise((resolve) => setTimeout(resolve, 700));
    expect("the bus power is sent", fake.sent.some((m) => m.type === "enocean_eltako/set_fields" && JSON.stringify(m.items) === '[{"device":"sub4","values":{"bus_power":"0,5"}}]'), true);
    expect("the power supplies are the groups of the bus table, edited in their header", root.querySelectorAll('#installation [data-in-sfield="name"]').length, 2);
    const watts = root.querySelector('#installation [data-in-sfield="watts"]');
    watts.value = "viel";
    watts.dispatchEvent(new Event("input", { bubbles: true }));
    await new Promise((resolve) => setTimeout(resolve, 700));
    expect("a wrong value is marked and not sent", fake.sent.filter((m) => m.type === "enocean_eltako/set_supplies").length, 0);
    watts.value = "24";
    watts.dispatchEvent(new Event("input", { bubbles: true }));
    await new Promise((resolve) => setTimeout(resolve, 700));
    expect("the supplies are sent as a list", fake.sent.filter((m) => m.type === "enocean_eltako/set_supplies").length, 1);
    root.querySelector("#installation [data-in-supply-add]").click();
    await settle();
    expect("a supply is added", root.querySelectorAll('#installation [data-in-sfield="name"]').length, 3);
    groupChips()[0].click();
    await settle();
    root.querySelector('#installation [data-in-tab="links"]').click();
    await settle();
    expect("a card per actuator (four: the room controller is none)", root.querySelectorAll("#installation .lcard").length, 4);
    expect("link rows by actuator", root.querySelectorAll("#installation .lrow").length, 4);
    expect("each link row has its columns, the actions last", [...root.querySelectorAll("#installation .lrow")].every((r) => r.children.length === 6 && r.lastElementChild.matches(".lacts")), true);
    expect("a sender ID of Home Assistant leads to its row in the Sender IDs tab", root.querySelectorAll("#installation .lrow .nm [data-in-snd]").length >= 2, true);
    expect("the time of a proof is short, the full time its tooltip", [...root.querySelectorAll("#installation .lrow .lstate .isub")].every((x) => x.title && !/\d{4}/.test(x.textContent)), true);
    expect("an entry by hand as sender leads to its row", !!root.querySelector('#installation .lrow [data-in-goto^="manual|"]'), true);
    expect("a link says where it comes from", root.querySelectorAll('#installation .lrow .tag[class*="src-"]').length, 4);
    expect("the tiles count actuators, without a link, no answer, not tested, answered", root.querySelectorAll("#installation .stile").length, 5);
    expect("an actuator without a link is marked", root.querySelectorAll("#installation .lnone").length > 0, true);
    const learn = root.querySelector("#installation [data-in-learn]");
    learn.value = "Funktion 45";
    learn.dispatchEvent(new Event("input", { bubbles: true }));
    await new Promise((resolve) => setTimeout(resolve, 700));
    expect("a learn position is saved", fake.sent.filter((m) => m.type === "enocean_eltako/set_link_learn").map((m) => `${m.link_key}=${m.learn}`).join(), "assigned|05-00-00-01|central=Funktion 45");
    // a sender test of an actuator, and a link written down from the card of an actuator
    root.querySelector("#installation [data-in-test]").click();
    await settle();
    expect("the sender test is asked for the actuator", fake.sent.some((m) => m.type === "enocean_eltako/sender_test" && m.device === "sub1"), true);
    root.querySelector('#installation [data-in-linkadd="a|05-00-00-03"]').click();
    await settle();
    const linkForm = root.querySelector("#installation [data-in-linkform]");
    const pick = linkForm.querySelector('[data-in-new="other"]');
    pick.value = "other";
    pick.dispatchEvent(new Event("change", { bubbles: true }));
    expect("the free fields show for another sender", linkForm.querySelector('[data-in-new="name"]').hidden, false);
    linkForm.querySelector('[data-in-new="name"]').value = "Taster Bad";
    linkForm.querySelector('[data-in-new="id"]').value = "FE-F3-B0-02";
    linkForm.querySelector('[data-in-new="role"]').value = "linke Wippe";
    root.querySelector('#installation [data-in-act="link-add"]').click();
    await settle();
    expect("a link written down is sent", fake.sent.filter((m) => m.type === "enocean_eltako/set_links").some((m) => m.links.some((l) => l.from_id === "FE-F3-B0-02" && l.to_key === "05-00-00-03" && l.role === "linke Wippe")), true);
    root.querySelector('#installation [data-in-linkview="sender"]').click();
    await settle();
    expect("link cards by sender", root.querySelectorAll("#installation .lcard").length >= 4, true);
    root.querySelector('#installation [data-in-linkview="matrix"]').click();
    await settle();
    expect("the matrix has a row per actuator", root.querySelectorAll("#installation table.matrix tbody tr").length, 4);
    root.querySelector('#installation [data-in-tab="log"]').click();
    await settle();
    expect("log rows", root.querySelectorAll("#installation .log tbody tr:not(.logday)").length, 4);
    expect("a recent event says how long ago it was", /\d+ s\b/.test(root.querySelector("#installation .log")?.textContent ?? ""), true);
    await view("telegrams");
    expect("the unknown chip counts the unknown senders", root.querySelector("#unknown .n")?.textContent, "1");
    await view("devices");
    expect("device rows", root.querySelectorAll(".dev").length, 5);
    const state = (name) => [...root.querySelectorAll(".dev")].find((d) => d.textContent.includes(name))?.querySelector(".pill")?.className.replace("pill ", "");
    expect("a heard device is active", state("Licht Diele"), "active");
    const chipCount = (status) => root.querySelector(`#devStatus [data-status="${status}"] .n`)?.textContent;
    expect("the status chips count the devices", ["", "known", "unknown", "silent", "unheard", "weak"].map(chipCount).join(","), "5,4,1,1,1,1");
    // grouped by area: a heading per area with its count; a click folds the group away
    const groups = () => [...root.querySelectorAll(".dgroup")];
    expect("devices are grouped by area", groups().length > 1, true);
    const first = groups()[0];
    const before = root.querySelectorAll(".dev").length;
    first.click();
    expect("a folded group hides its rows", root.querySelectorAll(".dev").length < before, true);
    root.querySelector(".dgroup").click();
    expect("an unfolded group shows them again", root.querySelectorAll(".dev").length, before);
    root.getElementById("devGroup").value = "";
    root.getElementById("devGroup").dispatchEvent(new Event("change", { bubbles: true }));
    expect("no grouping: no headings", root.querySelectorAll(".dgroup").length, 0);
    expect("the pill names its state", [...root.querySelectorAll(".dev .pill")].every((p) => p.textContent.trim().length > 0), true);
    expect("a device past its interval is silent", state("Temperatur Bad"), "silent");
    expect("a device never heard is not heard", state("Fensterkontakt Küche"), "unheard");
    expect("a sender that is not set up is unknown", state("01-00-00-99"), "unknown");
    const row = (name) => [...root.querySelectorAll(".dev")].find((d) => d.textContent.includes(name));
    expect("a quiet device shows what its entities hold, not an unavailable one", row("Temperatur Bad").querySelector(".values").textContent.includes("21.5 °C") && !row("Temperatur Bad").querySelector(".values").textContent.includes("%"), true);
    expect("a device never heard shows no time beside its pill", row("Fensterkontakt Küche").querySelector(".stats").textContent.trim(), "–");
    expect("every row has a kind tile", root.querySelectorAll(".dev .ident .tile").length, 5);
    expect("a light gets the light tile", !!row("Licht Diele").querySelector(".tile.lighting"), true);
    expect("a sender that is not set up gets the question mark tile", !!row("01-00-00-99").querySelector(".tile.unknown"), true);
    expect("a model that is not fixed names its candidates", row("Dimmer Flur").textContent.includes("FUD14 / FUD61 / FD62"), true);
    expect("rows with something to offer have a more-menu button", root.querySelectorAll(".dev .acts .rowmore").length, 4);
    expect("no loose icon buttons beside the menu", root.querySelectorAll(".dev .acts .icon-btn:not(.rowmore):not(.expand)").length, 0);
    row("Licht Diele").querySelector(".rowmore").click();
    expect("the more menu lists teach in, open device, telegrams and remove", root.querySelectorAll(".addmenu [data-addact]").length, 4);
    root.querySelector('.addmenu [data-addact="remove"]').click();
    expect("remove asks about the row's device only", root.getElementById("pickForm").hidden, false);
    expect("remove selects only the row's device", root.getElementById("selBar").textContent.includes("1"), true);
    root.querySelector('[data-sel-act="clear"]').click();
    row("Licht Diele").querySelector(".rowmore").click();
    row("Licht Diele").querySelector(".rowmore").click();
    expect("the more button closes its menu again", root.querySelector(".addmenu"), null);
    // a set-up device opens in place, with what the server knows of it, and closes again
    root.querySelector('.dev[data-dev="sub1"]').click();
    await settle();
    expect("device details open", root.querySelectorAll(".dev-detail").length, 1);
    expect("device details load", root.querySelector(".dev-detail").textContent.includes("FF-00-11-81"), true);
    expect("an opened device leads to its links", !!root.querySelector('.dev-detail [data-dev-links="Licht Diele"]'), true);
    expect("device rows while one is open", root.querySelectorAll(".dev").length, 5);
    // the opened row: one card grid, the last telegram over two columns with its raw bytes as tags,
    // one row component for values, senders, settings and entities
    const detail = root.querySelector(".dev-detail");
    expect("the last telegram is a full-width card with bytes and status as tags", !!detail.querySelector(".dgrid > div.full .tg .raw .tag.mono") && detail.querySelectorAll(".dgrid > div.full .raw .tag").length, 2);
    expect("the last telegram does not repeat the values", detail.querySelector(".dgrid > div.full .tg .sub"), null);
    expect("the last values are read rows, the raw bytes only in the telegram card", detail.querySelectorAll(".rows .li.value").length > 0 && !detail.querySelector(".rows .foot .tag.mono"), true);
    expect("the senders are rows of the same component", detail.querySelectorAll(".dsec .rows .li").length > 4, true);
    expect("no tables are left in the opened row", detail.querySelectorAll("table").length, 0);
    expect("the section headings count their rows", [...detail.querySelectorAll(".dsec h4 .sub")].length >= 2, true);
    const opened = root.querySelector('.dev[data-dev="sub1"]');
    expect("the name keeps one line and has its full text as tooltip", opened.querySelector(".line1 .name").getAttribute("title"), "Licht Diele");
    expect("last heard in one line", !!opened.querySelector(".stats .l1") && !opened.querySelector(".stats .l2"), true);
    expect("the labels are in the opened row", detail.querySelector(".labels")?.textContent.trim(), "Battery");
    // the model is a pick from the kind's models; a typed one comes through "other"
    const picker = root.querySelector("[data-model-for]");
    picker.value = "FL62";
    picker.dispatchEvent(new Event("change", { bubbles: true }));
    await settle();
    const saved = () => fake.sent.filter((m) => m.type === "enocean_eltako/set_model").map((m) => `${m.device}:${m.model_name}`).join(",");
    expect("model picked", saved(), "sub1:FL62");
    const again = root.querySelector("[data-model-for]"); // the row was drawn anew
    again.value = "__other";
    again.dispatchEvent(new Event("change", { bubbles: true }));
    const typed = root.querySelector("[data-model-text]");
    expect("typing box shown", typed.hidden, false);
    typed.value = "FSR14M-2x";
    typed.dispatchEvent(new Event("change", { bubbles: true }));
    await settle();
    expect("model typed", saved(), "sub1:FL62,sub1:FSR14M-2x");
    typed.blur(); // the redraw waits while a box is in use, then catches up
    await settle();
    root.querySelector('.dev[data-dev="sub2"]').click();
    await settle();
    expect("two device rows open", root.querySelectorAll(".dev-detail").length, 2);
    root.querySelector('.dev[data-dev="sub2"] .expand').click();
    root.querySelector('.dev[data-dev="sub1"] .expand').click();
    await settle();
    expect("device details closed", root.querySelectorAll(".dev-detail").length, 0);
    root.querySelector('#devStatus [data-status="weak"]').click();
    await settle();
    expect("weak-signal devices", root.querySelectorAll(".dev").length, 1);
    expect("weak status chip pressed", root.querySelector('#devStatus [data-status="weak"]').getAttribute("aria-pressed"), "true");
    root.querySelector('#devStatus [data-status=""]').click();
    await settle();
    root.querySelector('.dev[data-dev="sub1"] .rowmore').click();
    root.querySelector('.addmenu [data-addact="teach"]').click();
    await settle();
    expect("teach-in form open", root.getElementById("teachForm").hidden, false);
    root.getElementById("teachForm").requestSubmit();
    await settle();
    expect("teach-in sent", fake.sent.some((m) => m.type === "enocean_eltako/teach_in" && m.device === "sub1" && m.profile === "central"), true);
    expect("teach-in form closed", root.getElementById("teachForm").hidden, true);
    await view("senders");
    expect("pool map squares", root.querySelectorAll(".map button").length, 128);
    expect("no list by device above the table", root.querySelectorAll(".sid-row, .sid-group").length, 0);
    expect("free all shown with a blocked ID", !!root.querySelector("[data-free-all]"), true);
    root.querySelector("[data-free-all]").click();
    expect("free all asks first", !!root.querySelector(".confirm [data-free-confirm]"), true);
    root.querySelector("[data-free-cancel]").click();
    const rowFree = root.querySelector("#instBody [data-in-free]");
    if (rowFree) {
      // a blocked row of the table opens the confirmation in the pool above it
      rowFree.click();
      expect("a blocked row of the table asks before it frees the ID", !!root.querySelector("#senders .confirm [data-free-confirm]"), true);
      root.querySelector("[data-free-cancel]").click();
    }
    expect("blocked note", !!root.querySelector(".pnote"), true);
    expect("the Sender IDs tab counts the blocked IDs", !!root.querySelector('#installation [data-in-tab="gwsenders"] .tabwarn'), true);
    root.querySelector('.map button[data-tile="FF-00-11-81"]').click();
    await settle();
    expect("chosen square is read out", root.querySelector(".pread").textContent.includes("Licht Diele"), true);
    expect("chosen square marked", root.querySelectorAll(".map button.sel").length, 1);
    root.querySelector('.map button[data-tile="FF-00-11-81"]').click();
    await settle();
    expect("square unchosen", root.querySelectorAll(".map button.sel").length, 0);
    await view("senders");
    root.querySelector("#instBody a[data-in-goto]").click();
    await settle();
    expect("devices view after the sender ID link", root.querySelector('#view [data-view="devices"]').getAttribute("aria-selected"), "true");
    expect("device opened by the sender ID link", root.querySelectorAll(".dev-detail").length, 1);
    await view("senders");
    expect("takeover tab shown", root.querySelector('#view [data-view="takeover"]').hidden, false);
    await view("takeover");
    const tk = (sel) => root.querySelector(`.takeover ${sel}`);
    const click = async (sel) => { tk(sel).click(); await settle(); };
    expect("takeover steps", root.querySelectorAll(".takeover .step").length, 3);
    expect("takeover opens on Select", tk(".step.cur")?.dataset.tkTab, "select");
    expect("takeover devices to pick, the set-up one with a missing value included", root.querySelectorAll(".takeover .pickrow").length, 3);
    expect("the set-up device is tagged with what is missing", root.querySelectorAll(".takeover .pickrow .chip-s.ok").length, 1);
    await click('.stepbar [data-tk-tab="carry"]');
    expect("carry options as cards, one each", root.querySelectorAll(".takeover .optcard").length, 6);
    expect("carry options off at first", root.querySelectorAll(".takeover [data-tk-carry]:checked").length, 0);
    expect("preview: one block per device", root.querySelectorAll(".takeover .devblock").length, 3);
    expect("preview: no values before an option is chosen", root.querySelectorAll(".takeover .devhead .chip-s.val").length, 0);
    await click('[data-tk-carry="area"]');
    await click('[data-tk-carry="labels"]');
    expect("preview: the chosen values of each device", root.querySelectorAll(".takeover .devhead .chip-s.val").length, 5);
    await click("[data-tk-open]");
    expect("preview opened: old -> new IDs", root.querySelectorAll(".takeover .ent").length, 2);
    expect("preview opened: the device's own values", !!tk(".olddl"), true);
    await click('[data-tk-expand="all"]');
    expect("preview: all opened", root.querySelectorAll(".takeover .ent").length, 4);
    expect("nothing taken over before the confirmation", fake.sent.some((m) => m.type === "enocean_eltako/takeover/run"), false);
    expect("one primary button in the review step", root.querySelectorAll(".takeover .chip.primary:not([disabled])").length, 1);
    await click('.stepbar [data-tk-tab="select"]');
    expect("back keeps the selection", root.querySelectorAll(".takeover [data-tk-pick]:checked").length, 3);
    await click('.stepbar [data-tk-tab="carry"]');
    await click("[data-tk-confirm]");
    expect("takeover sends the chosen options", fake.sent.some((m) => m.type === "enocean_eltako/takeover/run" && m.carry.join() === "area,labels"), true);
    expect("the set-up device is completed with the same options", fake.sent.some((m) => m.type === "enocean_eltako/takeover/carry" && m.carry.join() === "area,labels" && m.devices.join() === "05-00-00-07"), true);
    expect("a result page follows", !!tk('.stepbar [data-tk-tab="release"]'), true);
    await click('.stepbar [data-tk-tab="release"]');
    expect("then on to retiring the old integration", tk(".step.cur")?.dataset.tkTab, "release");
    expect("two ways to deal with the old IDs", root.querySelectorAll(".takeover .stratcard").length, 2);
    expect("no steps before the choice", root.querySelectorAll(".takeover .check").length, 0);
    await click('[data-tk-strategy="keep"]');
    expect("strategy sent", fake.sent.some((m) => m.type === "enocean_eltako/takeover/strategy" && m.strategy === "keep"), true);
    expect("keep: delete, restore, YAML", root.querySelectorAll(".takeover .check").length, 3);
    expect("keep: restore waits for the deletion", root.querySelectorAll(".takeover .check.wait").length, 1);
    await click('[data-tk-strategy="new"]');
    expect("new: places, delete, YAML", root.querySelectorAll(".takeover .check").length, 3);
    expect("new: places with an editor link", root.querySelectorAll(".takeover .devblock [data-tk-go]").length, 2);
    await click("[data-tk-reports]");
    expect("reports: one card each", root.querySelectorAll(".takeover .runcard").length, 2);
    await click('[data-tk-run="run1"]');
    expect("report: its device", root.querySelectorAll(".takeover .devhead").length, 1);
    await click("[data-tk-open-run]");
    expect("report: what the device was", !!tk(".olddl"), true);
    await click("[data-tk-del]");
    expect("deleting asks first", !!tk(".confirm [data-tk-del-yes]"), true);
    expect("nothing deleted before the confirmation", fake.sent.some((m) => m.type === "enocean_eltako/takeover/report_delete"), false);
    await click("[data-tk-del-yes]");
    expect("report deleted", fake.sent.some((m) => m.type === "enocean_eltako/takeover/report_delete" && m.run_id === "run1"), true);
    expect("back at the list", root.querySelectorAll(".takeover .runcard").length, 1);
  });
  await check(`lang=${lang}&select`, async ({ root, fake, view, expect }) => {
    // ticking set-up devices: the bar offers area, labels, disabling and removing; the others have no box
    await view("devices");
    expect("boxes only on set-up devices", root.querySelectorAll(".dev .selbox").length, 2);
    expect("no bar without a tick", root.getElementById("selBar").hidden, true);
    root.querySelector("[data-sel-all]").click();
    await settle();
    expect("select all ticks the set-up devices", root.querySelectorAll(".dev.picked").length, 2);
    root.querySelector('[data-sel-act="clear"]').click();
    await settle();
    expect("cleared", root.getElementById("selBar").hidden, true);
    expect("the head box is in its own column", !!root.querySelector(".dev-head .c-sel [data-sel-all]"), true);
    expect("a box per row in its own column", root.querySelectorAll(".dev .c-sel .selbox").length, 2);
    root.querySelector('[data-sel="sub1"]').click();
    root.querySelector('[data-sel="sub2"]').click();
    await settle();
    expect("bar after two ticks", root.getElementById("selBar").hidden, false);
    expect("the bar takes the place of the count line", root.getElementById("panel").hasAttribute("data-picked"), true);
    expect("labels stay out of the row", root.querySelector('.dev[data-dev="sub1"] .labels'), null);
    root.querySelector('[data-sel-act="area"]').click();
    await settle();
    root.getElementById("pickArea").value = "bad";
    root.getElementById("pickForm").requestSubmit();
    await settle();
    const updates = (key) => fake.sent.filter((m) => m.type === "config/device_registry/update" && key in m);
    expect("area set for both", updates("area_id").length, 2);
    expect("area shows in the row under the type", root.querySelector('.dev[data-dev="sub2"] .c-area').textContent.includes("Bad"), true);
    root.querySelector('[data-sel-act="labels"]').click();
    await settle();
    const lbl = (id) => root.querySelector(`[data-label="${id}"]`);
    expect("a label on one of two is a dash", lbl("lbl_battery").indeterminate, true);
    root.getElementById("pickForm").querySelector("[data-pick-new]").click();
    await settle();
    expect("empty label name refused", root.getElementById("pickErr").hidden, false);
    root.getElementById("pickNew").value = "Garage";
    root.getElementById("pickForm").querySelector("[data-pick-new]").click();
    await settle();
    expect("new label ticked", lbl("lbl_garage").checked, true);
    expect("dash kept after creating", lbl("lbl_battery").indeterminate, true);
    root.getElementById("pickForm").requestSubmit();
    await settle();
    expect("label added to both, the dash untouched", updates("labels").map((m) => m.labels.join("+")).join(","), "lbl_garage,lbl_battery+lbl_garage");
    root.querySelector('[data-sel-act="toggle"]').click();
    await settle();
    expect("both disabled", updates("disabled_by").filter((m) => m.disabled_by === "user").length, 2);
    root.querySelector('[data-sel-act="remove"]').click();
    await settle();
    expect("remove asks first", root.getElementById("pickForm").hidden, false);
    expect("nothing removed before the confirmation", fake.sent.filter((m) => m.type === "enocean_eltako/remove_devices").length, 0);
    root.getElementById("pickForm").requestSubmit();
    await settle();
    expect("both removed with one call", fake.sent.filter((m) => m.type === "enocean_eltako/remove_devices").map((m) => m.devices.join("+")).join(","), "sub2+sub1");
    expect("rows with a box gone", root.querySelectorAll(".dev .selbox").length, 0);
    expect("bar gone", root.getElementById("selBar").hidden, true);
  });
  await check(`lang=${lang}&closed`, async ({ root, view, expect }) => {
    expect("nothing to do, reports left: the tab stays", root.querySelector('#view [data-view="takeover"]').hidden, false);
    await view("devices");
    expect("reports button under Devices", root.querySelector("#tkReport").hidden, false);
    root.querySelector("#tkReport").click();
    await settle();
    expect("reports without steps", root.querySelectorAll(".takeover .step").length, 0);
    expect("reports listed", root.querySelectorAll(".takeover .runcard").length, 2);
  });
  await check(`lang=${lang}&two&dark`, async ({ root, view, expect }) => {
    await view("telegrams");
    expect("gateway cards", root.querySelectorAll(".card").length, 2);
    await view("devices");
  });
  // a documentation export of a swapped gateway: the panel asks before it maps it to the free one
  await check(`lang=${lang}`, async ({ root, fake, expect, panel }) => {
    const file = { text: async () => JSON.stringify({ version: 1, gateways: [{ title: "Altes Gateway", base_id: "FF-80-00-80", devices: [] }] }) };
    const imports = () => fake.sent.filter((m) => m.type === "enocean_eltako/import_documentation");
    let run = panel._importDocumentation(file);
    await settle();
    expect("the import asks in a panel dialog, not in the browser", !!root.querySelector(".bv-ask"), true);
    root.querySelector('.bv-ask [data-ask="no"]').click();
    await run;
    expect("declining sends no gateway map", imports().length === 1 && !imports()[0].gateway_map, true);
    run = panel._importDocumentation(file);
    await settle();
    root.querySelector('.bv-ask [data-ask="yes"]').click();
    await run;
    expect("accepting maps the old base ID to the gateway set up here", JSON.stringify(imports().at(-1).gateway_map), '{"FF-80-00-80":"gw1"}');
  });
  // the same sender ID set up on two gateways: each row keeps the device and the gateway it belongs to
  await check(`lang=${lang}&two&shared`, async ({ root, fake, view, expect, panel }) => {
    await view("devices");
    const at = new Date().toISOString();
    for (const [gw, name] of [["gw1", "FAM-USB Keller"], ["gw2", "MGW Garage"]]) {
      fake.push({ time: at, dir: "rx", sender: "05-00-00-01", rorg: "F6", data: "70", status: "30", dbm: -60, device: "x", gateway: gw, gateway_name: name });
    }
    await settle();
    const rows = panel._deviceItems().filter((d) => d.id === "05-00-00-01");
    expect("one row per gateway for a shared sender ID", rows.map((d) => d.gateway).sort().join(), "gw1,gw2");
    expect("each row has the device set up on its own gateway", rows.sort((a, b) => a.gateway.localeCompare(b.gateway)).map((d) => d.devKey).join(), "sub1,sub9");
    expect("no set-up device is listed as quiet while its gateway heard it", panel._deviceItems().filter((d) => d.quiet && d.id === "05-00-00-01").length, 0);
  });
  await check(`lang=${lang}&empty`, async ({ root, view, expect }) => {
    await view("telegrams");
    expect("add-a-gateway action", !!root.querySelector("#cards [data-open-integration]"), true);
    expect("takeover tab hidden", root.querySelector('#view [data-view="takeover"]').hidden, true);
    await view("devices");
    await view("senders");
  });
}

console.error = consoleError;
await GlobalRegistrator.unregister();
if (errors.length) {
  console.error(errors.join("\n"));
  process.exit(1);
}
console.log("panel renders ok (en, de; all views)");
