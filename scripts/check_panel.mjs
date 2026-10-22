// CI check of the sidebar panel (custom_components/enocean_eltako/frontend), no browser needed:
// every file loads (syntax, imports between the parts, names used at load time) and the
// English and German texts have the same keys. Run: node scripts/check_panel.mjs

import { fileURLToPath } from "node:url";

// just enough of a browser for the files to load
globalThis.HTMLElement = class {};
const defined = [];
globalThis.customElements = { define: (name) => defined.push(name) };

const frontend = new URL("../custom_components/enocean_eltako/frontend/", import.meta.url);
const errors = [];

await import(new URL("monitor-panel.js?v=check", frontend).href);
if (!defined.includes("enocean-eltako-monitor")) errors.push("monitor-panel.js defines no enocean-eltako-monitor");

// the panel picks the language at run time: a key missing in one of them shows as undefined
const { TEXT } = await import(new URL("texts.js?v=check", frontend).href);
function compare(a, b, path) {
  for (const key of new Set([...Object.keys(a), ...Object.keys(b)])) {
    const where = path ? `${path}.${key}` : key;
    if (!(key in a)) errors.push(`texts.js: ${where} missing in en`);
    else if (!(key in b)) errors.push(`texts.js: ${where} missing in de`);
    else if (typeof a[key] !== typeof b[key] || Array.isArray(a[key]) !== Array.isArray(b[key])) errors.push(`texts.js: ${where} differs in type`);
    else if (Array.isArray(a[key]) && a[key].length !== b[key].length) errors.push(`texts.js: ${where} differs in length`);
    else if (typeof a[key] === "object") compare(a[key], b[key], where);
  }
}
compare(TEXT.en, TEXT.de, "");

if (errors.length) {
  console.error(errors.join("\n"));
  process.exit(1);
}
console.log(`panel ok (${fileURLToPath(frontend)})`);
