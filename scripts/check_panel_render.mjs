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
process.on("unhandledRejection", (reason) => fail(`unhandled rejection: ${reason?.message || reason}`));
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
    root.querySelector(`#view [data-view="${name}"]`).click();
    await settle();
    const text = shown(root);
    for (const bad of ["undefined", "NaN", "[object", "null"]) {
      if (text.includes(bad)) fail(`${query} ${name}: shows "${bad}"`);
    }
  };
  const expect = (what, actual, wanted) => {
    if (actual !== wanted) fail(`${query}: ${what} is ${actual}, expected ${wanted}`);
  };
  try {
    await run({ root, fake, view, expect });
  } catch (err) {
    fail(`${query}: ${err.stack || err}`);
  }
  panel.remove();
}

for (const lang of ["en", "de"]) {
  await check(`lang=${lang}`, async ({ root, fake, view, expect }) => {
    await view("telegrams");
    expect("telegram rows", root.querySelectorAll("tr.row").length, 4);
    fake.push({ time: new Date().toISOString(), dir: "rx", sender: "05-10-A2-B3", rorg: "F6", data: "50", status: "30", dbm: -60, device: "Licht Diele" });
    await settle();
    expect("telegram rows after a new one", root.querySelectorAll("tr.row").length, 5);
    root.querySelector("tr.row").click();
    await settle();
    expect("open details", root.querySelectorAll("tr.detail-row").length, 1);
    // an open telegram holds new ones back; closing it lets them in
    fake.push({ time: new Date().toISOString(), dir: "rx", sender: "05-10-A2-B3", rorg: "F6", data: "70", status: "30", dbm: -61, device: "Licht Diele" });
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
    // the sent telegram of the samples: "send again" sends it, a rocker press with its release
    const sent = [...root.querySelectorAll("tr.row")].find((row) => row.querySelector(".dir.tx"));
    sent.click();
    await settle();
    root.querySelector("[data-resend]").click();
    await settle();
    const resent = fake.sent.filter((m) => m.type === "enocean_eltako/send").map((m) => `${m.sender} ${m.rorg} ${m.data} ${m.status}`);
    expect("sent again", resent.join(", "), "FF-B7-44-81 F6 70 30, FF-B7-44-81 F6 00 20");
    root.getElementById("filterBtn").click();
    expect("filter row open", root.getElementById("filterMenu").hidden, false);
    await view("devices");
    expect("device rows", root.querySelectorAll(".dev").length, 5);
    // a set-up device opens in place, with what the server knows of it, and closes again
    root.querySelector('.dev[data-dev="sub1"]').click();
    await settle();
    expect("device details open", root.querySelectorAll(".dev-detail").length, 1);
    expect("device details load", root.querySelector(".dev-detail").textContent.includes("FF-B7-44-81"), true);
    expect("device rows while one is open", root.querySelectorAll(".dev").length, 5);
    root.querySelector('.dev[data-dev="sub2"]').click();
    await settle();
    expect("two device rows open", root.querySelectorAll(".dev-detail").length, 2);
    root.querySelector('.dev[data-dev="sub2"] .expand').click();
    root.querySelector('.dev[data-dev="sub1"] .expand').click();
    await settle();
    expect("device details closed", root.querySelectorAll(".dev-detail").length, 0);
    root.getElementById("weakHint").click();
    await settle();
    expect("weak-signal devices", root.querySelectorAll(".dev").length, 1);
    root.querySelector('[data-unset="devStatus"]').click();
    await settle();
    root.querySelector("[data-teach]").click();
    await settle();
    expect("teach-in form open", root.getElementById("teachForm").hidden, false);
    root.getElementById("teachForm").requestSubmit();
    await settle();
    expect("teach-in sent", fake.sent.some((m) => m.type === "enocean_eltako/teach_in" && m.device === "sub1" && m.profile === "central"), true);
    expect("teach-in form closed", root.getElementById("teachForm").hidden, true);
    await view("senders");
    expect("pool map squares", root.querySelectorAll(".map button").length, 128);
    expect("sender ID rows", root.querySelectorAll(".sid-row").length, 2);
    expect("takeover tab shown", root.querySelector('#view [data-view="takeover"]').hidden, false);
    await view("takeover");
    const tk = (sel) => root.querySelector(`.takeover ${sel}`);
    const click = async (sel) => { tk(sel).click(); await settle(); };
    expect("takeover steps", root.querySelectorAll(".takeover .step").length, 4);
    expect("takeover opens on Select", tk(".step.cur")?.dataset.tkTab, "select");
    expect("takeover devices to pick", root.querySelectorAll(".takeover .pickrow").length, 2);
    expect("set-up devices link to the overview", !!tk('.counts [data-tk-tab="switch"]'), true);
    await click('.stepbar [data-tk-tab="carry"]');
    expect("carry options as cards, one each", root.querySelectorAll(".takeover .optcard").length, 6);
    expect("carry options off at first", root.querySelectorAll(".takeover [data-tk-carry]:checked").length, 0);
    expect("preview: old -> new IDs", root.querySelectorAll(".takeover .idtable tbody tr").length, 4);
    await click('[data-tk-carry="area"]');
    expect("nothing taken over before the confirmation", fake.sent.some((m) => m.type === "enocean_eltako/takeover/run"), false);
    await click('.stepbar [data-tk-tab="select"]');
    expect("back keeps the selection", root.querySelectorAll(".takeover [data-tk-pick]:checked").length, 2);
    await click('.stepbar [data-tk-tab="carry"]');
    await click("[data-tk-confirm]");
    expect("takeover sends the chosen options", fake.sent.some((m) => m.type === "enocean_eltako/takeover/run" && m.carry.join() === "area"), true);
    expect("then on to Switch over, by place", tk(".step.cur")?.dataset.tkTab + tk('[data-tk-mview][aria-pressed="true"]')?.dataset.tkMview, "switchplace");
    expect("places with an editor link", root.querySelectorAll(".takeover .devblock [data-tk-go]").length, 2);
    await click('[data-tk-mview="device"]');
    expect("by device: one device", root.querySelectorAll(".takeover .devhead").length, 1);
    expect("by device: what is missing", root.querySelectorAll(".takeover .chip-s.avail").length, 2);
    await click("[data-tk-open]");
    expect("details from the old integration", !!tk(".olddl"), true);
    expect("by device: entities opened", root.querySelectorAll(".takeover .ent").length, 2);
    await click("[data-tk-later]");
    await click("[data-tk-later-run]");
    expect("carried over later", fake.sent.some((m) => m.type === "enocean_eltako/takeover/carry" && m.carry.join() === "area"), true);
    await click('[data-tk-mview="report"]');
    expect("report as a table", root.querySelectorAll(".takeover .idtable tbody tr").length, 2);
    await click('.stepbar [data-tk-tab="cleanup"]');
    expect("clean up: the checklist", root.querySelectorAll(".takeover .check").length, 6);
    await click("[data-tk-finish]");
    expect("finishing closes the takeover", fake.sent.some((m) => m.type === "enocean_eltako/takeover/close"), true);
  });
  await check(`lang=${lang}&closed`, async ({ root, view, expect }) => {
    expect("finished: no takeover tab", root.querySelector('#view [data-view="takeover"]').hidden, true);
    await view("devices");
    expect("report button under Devices", root.querySelector("#tkReport").hidden, false);
    root.querySelector("#tkReport").click();
    await settle();
    expect("report without steps", root.querySelectorAll(".takeover .step").length, 0);
    expect("report opens as the table", root.querySelectorAll(".takeover .idtable tbody tr").length, 2);
  });
  await check(`lang=${lang}&two&dark`, async ({ root, view, expect }) => {
    await view("telegrams");
    expect("gateway cards", root.querySelectorAll(".card").length, 2);
    await view("devices");
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
