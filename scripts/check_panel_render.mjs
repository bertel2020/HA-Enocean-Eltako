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
    expect("telegram rows", root.querySelectorAll("tr.row").length, 3);
    fake.push({ time: new Date().toISOString(), dir: "rx", sender: "05-10-A2-B3", rorg: "F6", data: "50", status: "30", dbm: -60, device: "Licht Diele" });
    await settle();
    expect("telegram rows after a new one", root.querySelectorAll("tr.row").length, 4);
    root.querySelector("tr.row").click();
    await settle();
    expect("open details", root.querySelectorAll("tr.detail-row").length, 1);
    root.getElementById("filterBtn").click();
    expect("filter row open", root.getElementById("filterMenu").hidden, false);
    await view("devices");
    expect("device rows", root.querySelectorAll(".dev").length, 4);
    await view("senders");
    expect("pool map squares", root.querySelectorAll(".map button").length, 128);
    expect("sender ID rows", root.querySelectorAll(".sid-row").length, 2);
    expect("takeover tab shown", root.querySelector('#view [data-view="takeover"]').hidden, false);
    await view("takeover");
    expect("takeover steps", root.querySelectorAll(".takeover .step").length, 3);
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
