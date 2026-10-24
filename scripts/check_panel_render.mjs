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
    fake.push({ time: new Date().toISOString(), dir: "rx", sender: "05-10-A2-B3", rorg: "F6", data: "50", status: "30", dbm: -60, device: "Licht Diele", device_key: "sub1" });
    await settle();
    expect("telegram rows after a new one", root.querySelectorAll("tr.row").length, 5);
    root.querySelector("tr.row").click();
    await settle();
    expect("open details", root.querySelectorAll("tr.detail-row").length, 1);
    // an open telegram holds new ones back; closing it lets them in
    fake.push({ time: new Date().toISOString(), dir: "rx", sender: "05-10-A2-B3", rorg: "F6", data: "70", status: "30", dbm: -61, device: "Licht Diele", device_key: "sub1" });
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
    root.getElementById("weakHint").click();
    await settle();
    expect("weak-signal devices", root.querySelectorAll(".dev").length, 1);
    expect("weak status chip pressed", root.querySelector('#devStatus [data-status="weak"]').getAttribute("aria-pressed"), "true");
    root.querySelector('#devStatus [data-status=""]').click();
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
    const sidText = root.getElementById("sidText");
    sidText.value = "ba";
    sidText.dispatchEvent(new Event("input"));
    expect("search without a match", root.querySelectorAll(".sid-row").length, 0);
    root.querySelector("[data-sid-reset]").click();
    expect("search reset", root.querySelectorAll(".sid-row").length, 2);
    sidText.value = "ff-b7-44-85"; // an ID finds only itself
    sidText.dispatchEvent(new Event("input"));
    expect("search by ID", root.querySelectorAll(".sid-row").length, 1);
    sidText.value = "";
    sidText.dispatchEvent(new Event("input"));
    root.querySelector('[data-sid-state="assigned"]').click();
    expect("assigned only", root.querySelectorAll(".sid-row.blocked").length + root.querySelectorAll(".sid-row").length, 1);
    expect("free all hidden without blocked rows", root.getElementById("sidFreeAll").hidden, true);
    root.querySelector('[data-sid-state=""]').click();
    expect("free all shown", root.getElementById("sidFreeAll").hidden, false);
    root.getElementById("sidFreeAll").click();
    expect("free all asks first", !!root.querySelector(".confirm [data-free-confirm]"), true);
    root.querySelector("[data-free-cancel]").click();
    expect("pool tiles", root.querySelectorAll(".ptile").length, 5); // the sample pool has IDs used elsewhere
    expect("blocked note", !!root.querySelector(".pnote"), true);
    root.querySelector('.map button[data-tile="FF-B7-44-81"]').click();
    await settle();
    expect("chosen square is read out", root.querySelector(".pread").textContent.includes("Licht Diele"), true);
    expect("chosen square marked", root.querySelectorAll(".map button.sel").length, 1);
    root.querySelector('.map button[data-tile="FF-B7-44-81"]').click();
    await settle();
    expect("square unchosen", root.querySelectorAll(".map button.sel").length, 0);
    root.querySelector(".sid-name[data-dev-panel]").click();
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
    expect("takeover devices to pick", root.querySelectorAll(".takeover .pickrow").length, 2);
    expect("set-up devices link to step 2", !!tk('.counts [data-tk-tab="carry"]'), true);
    await click('.stepbar [data-tk-tab="carry"]');
    expect("carry options as cards, one each", root.querySelectorAll(".takeover .optcard").length, 6);
    expect("carry options off at first", root.querySelectorAll(".takeover [data-tk-carry]:checked").length, 0);
    expect("preview: one block per device", root.querySelectorAll(".takeover .devblock").length, 2);
    expect("preview: no values before an option is chosen", root.querySelectorAll(".takeover .devhead .chip-s.val").length, 0);
    await click('[data-tk-carry="area"]');
    await click('[data-tk-carry="labels"]');
    expect("preview: the chosen values of each device", root.querySelectorAll(".takeover .devhead .chip-s.val").length, 4);
    await click("[data-tk-open]");
    expect("preview opened: old -> new IDs", root.querySelectorAll(".takeover .ent").length, 2);
    expect("preview opened: the device's own values", !!tk(".olddl"), true);
    await click('[data-tk-expand="all"]');
    expect("preview: all opened", root.querySelectorAll(".takeover .ent").length, 4);
    expect("nothing taken over before the confirmation", fake.sent.some((m) => m.type === "enocean_eltako/takeover/run"), false);
    expect("already set up devices: carry over later is offered", !!tk("[data-tk-later-run]:not([disabled])"), true);
    await click("[data-tk-later-run]");
    expect("carried over later", fake.sent.some((m) => m.type === "enocean_eltako/takeover/carry" && m.carry.join() === "area,labels"), true);
    await click('.stepbar [data-tk-tab="select"]');
    expect("back keeps the selection", root.querySelectorAll(".takeover [data-tk-pick]:checked").length, 2);
    await click('.stepbar [data-tk-tab="carry"]');
    await click("[data-tk-confirm]");
    expect("takeover sends the chosen options", fake.sent.some((m) => m.type === "enocean_eltako/takeover/run" && m.carry.join() === "area,labels"), true);
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
    expect("label chip on a row", root.querySelector('.dev[data-dev="sub1"] .labels').textContent.trim(), "Battery");
    root.querySelector('[data-sel-act="area"]').click();
    await settle();
    root.getElementById("pickArea").value = "bad";
    root.getElementById("pickForm").requestSubmit();
    await settle();
    const updates = (key) => fake.sent.filter((m) => m.type === "config/device_registry/update" && key in m);
    expect("area set for both", updates("area_id").length, 2);
    expect("area shows in the row", root.querySelector('.dev[data-dev="sub2"] .c-area').textContent.trim(), "Bad");
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
