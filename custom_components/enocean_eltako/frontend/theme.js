// Look of the panel: three colour schemes (each light and dark), three font sizes, and the choice
// between Home Assistant's mode, light and dark. The palette is set as custom properties on the
// panel element, so no part of the panel needs light-dark().

// [light, dark] per token; the token --line-2 is "line fine", --tag-bg is the same as --neutral-soft
export const SCHEMES = {
  ocean: {
    bg: ["#f4f6f9", "#0f1216"], surface: ["#ffffff", "#1b1f24"], soft: ["#f5f7f9", "#22272e"],
    line: ["#e1e5ea", "#2d333b"], "line-2": ["#eef0f3", "#262c33"], "input-line": ["#c3cbd5", "#3a424c"],
    text: ["#1b1f24", "#e6e9ed"], muted: ["#5b6270", "#9aa4b1"],
    accent: ["#0a6aa8", "#5bb2ea"], "accent-hover": ["#07507f", "#8ccaf2"], "accent-soft": ["#eaf3fa", "#16324a"],
    "on-accent": ["#ffffff", "#0b1a26"], "neutral-soft": ["#eef1f4", "#2a3038"], "tag-text": ["#3a414c", "#c5ccd5"],
  },
  forest: {
    bg: ["#f3f7f5", "#0e1513"], surface: ["#ffffff", "#1a2220"], soft: ["#f4f8f6", "#202a27"],
    line: ["#dce5e1", "#2b3733"], "line-2": ["#eaf0ed", "#24302c"], "input-line": ["#bccac4", "#394845"],
    text: ["#1a201e", "#e4ebe8"], muted: ["#566360", "#98a8a2"],
    accent: ["#0f7a6b", "#5fd0be"], "accent-hover": ["#0a5a4f", "#8fe0d2"], "accent-soft": ["#e4f3f0", "#123430"],
    "on-accent": ["#ffffff", "#08201c"], "neutral-soft": ["#ecf1ef", "#26312e"], "tag-text": ["#36423e", "#c3d0cb"],
  },
  graphite: {
    bg: ["#f5f4f2", "#141414"], surface: ["#ffffff", "#1f1f1e"], soft: ["#f6f5f3", "#262625"],
    line: ["#e4e2de", "#33322f"], "line-2": ["#eeedea", "#2a2a28"], "input-line": ["#cbc8c2", "#45433f"],
    text: ["#1c1b19", "#ebeae7"], muted: ["#5c5853", "#a9a59f"],
    accent: ["#2f3a48", "#d4dae2"], "accent-hover": ["#1b232d", "#f0f3f6"], "accent-soft": ["#eceff3", "#2c3139"],
    "on-accent": ["#ffffff", "#141820"], "neutral-soft": ["#efeeeb", "#2c2c2a"], "tag-text": ["#3d3a36", "#cfccc6"],
  },
};

// the same in every scheme
const COMMON = {
  ok: ["#1e6b34", "#7fd49a"], "ok-soft": ["#e6f4ea", "#173a24"],
  warn: ["#8a4b00", "#f2c27a"], "warn-soft": ["#fff1de", "#3a2a12"], "warn-line": ["#f3d19e", "#6b4a1c"],
  bad: ["#a1261b", "#f2a29a"], "bad-soft": ["#fdecea", "#3d1c19"], "bad-line": ["#f2b8b5", "#6e2f2a"],
  "code-bg": ["#14181d", "#0b0e11"], "code-text": ["#d7dee6", "#d7dee6"],
  focus: ["#7db8e0", "#7db8e0"], "shadow-c": ["rgba(16, 24, 40, .06)", "rgba(0, 0, 0, .4)"],
};

// base font size in px; every size in the panel is a multiple of it (14 px = factor 1)
export const SIZES = { small: 12.6, normal: 14, large: 16 };
export const MODES = ["auto", "light", "dark"];
export const DEFAULTS = { scheme: "ocean", mode: "auto", size: "normal" };

/** A stored choice made valid: unknown values fall back to the defaults. */
export function cleanPrefs(raw) {
  const p = raw && typeof raw === "object" ? raw : {};
  return {
    scheme: p.scheme in SCHEMES ? p.scheme : DEFAULTS.scheme,
    mode: MODES.includes(p.mode) ? p.mode : DEFAULTS.mode,
    size: p.size in SIZES ? p.size : DEFAULTS.size,
  };
}

/** Whether the panel is dark: the choice, or Home Assistant's mode (the system setting outside HA). */
export function isDark(prefs, haDark) {
  if (prefs.mode !== "auto") return prefs.mode === "dark";
  if (typeof haDark === "boolean") return haDark;
  return !!globalThis.matchMedia?.("(prefers-color-scheme: dark)").matches;
}

/** The custom properties of a choice: {"--bg": "#f4f6f9", ..., "--fs": 1}. */
export function tokens(prefs, dark) {
  const i = dark ? 1 : 0;
  const out = {};
  for (const [name, pair] of Object.entries({ ...SCHEMES[prefs.scheme], ...COMMON })) out[`--${name}`] = pair[i];
  out["--tag-bg"] = out["--neutral-soft"];
  out["--fs"] = String(+(SIZES[prefs.size] / SIZES.normal).toFixed(3));
  return out;
}

/** Sets the palette and the size factor on the panel element. */
export function applyAppearance(host, prefs, haDark) {
  const dark = isDark(prefs, haDark);
  for (const [name, value] of Object.entries(tokens(prefs, dark))) host.style.setProperty(name, value);
  host.style.colorScheme = dark ? "dark" : "light";
  host.toggleAttribute("dark", dark);
}
