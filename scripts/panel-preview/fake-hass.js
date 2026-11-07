// A stand-in for Home Assistant: the hass object the panel gets, with sample gateways,
// telegrams, sender pools and takeover data. Used by the preview page (index.html) and by the
// CI render check (scripts/check_panel_render.mjs).
//
// Options (query string of the preview page): lang=en|de, dark, primary (own primary colour),
// two (a second gateway), hide (an unknown sender hidden from discovery), skew=<s> (server clock
// ahead of the browser), empty (no gateways and no telegrams), open=<view>[:<device key>|gateway|menu]
// (a view, with a device's details or the gateway's details opened; for screenshots).

// the takeover view: two devices to take over, one already set up and still in use
const none = { automation: [], script: [], scene: [], dashboard: [] };
const takeoverDevices = [
  { id: "05-00-00-01", name: "Licht Diele", old: "light A5-38-08", ready: true, area: "Flur", labels: ["Licht"], carry: ["area", "labels", "voice"], used: 2,
    details: { area: "Flur", labels: ["Licht"], name: null },
    entities: [{ old: "light.eltako_05000001", new: "light.licht_diele", voice: { conversation: true, "cloud.alexa": false } }, { old: "sensor.eltako_05000001_id", new: "sensor.licht_diele_enocean_id" }],
    places: ["automation:Flur Bewegung", "dashboard:Übersicht"] },
  { id: "05-00-00-02", name: "Rollladen Süd", old: "cover G5-3F-7F", ready: true, area: "Wohnzimmer", labels: ["Beschattung"], carry: ["area", "labels", "names", "icons"], used: 0,
    details: { area: "Wohnzimmer", labels: [], name: "Südfenster" },
    entities: [{ old: "cover.eltako_05000002", new: "cover.rollladen_sud", labels: ["Beschattung"], icon: "mdi:blinds" }, { old: "sensor.eltako_05000002_power", new: null, name: "Leistung Süd" }], places: [] },
  { id: "05-00-00-07", name: "Zwischenstecker", old: "switch M5-38-08", ready: false, reason: "takeover_exists", area: "Küche", labels: [], carry: ["area"], used: 1 },
];
const takeoverRows = [
  { device: "Zwischenstecker", id: "05-00-00-07", area: "Küche", taken: true, primary: true, old: "switch.eltako_05000007", new: "switch.zwischenstecker", restored: false,
    usage: { ...none, automation: [{ name: "Kaffee aus", path: "/config/automation/edit/1" }], dashboard: [{ name: "Küche", path: "/lovelace" }] } },
  { device: "Zwischenstecker", id: "05-00-00-07", area: "Küche", taken: true, primary: false, old: "sensor.eltako_05000007_id", new: "sensor.zwischenstecker_enocean_id", restored: false, usage: none },
];
// what the integration keeps per device set up, in one report per takeover
const takeoverStored = {
  "05-00-00-07": { name: "Zwischenstecker", taken_at: "2026-10-12T09:30:00+00:00", carried: ["area", "labels"],
    old: { config: "switch M5-38-08", name: "Zwischenstecker", senders: ["FF-00-11-B2"], device_name: "Kaffeemaschine", area: "Küche", labels: ["Morgens"],
      details: { area: "Küche", labels: ["Morgens"], name: "Kaffeemaschine", entities: [{ old: "switch.eltako_05000007", icon: "mdi:coffee", voice: { "cloud.alexa": true } }] } } },
};
const makeRuns = () => [
  { id: "run1", entry_id: "gw1", gateway: "FAM-USB Keller", at: "2026-10-12T09:30:00+00:00", manual: false, carry: ["area", "labels"], devices: 1, entities: 2, restored: 0 },
  { id: "run0", entry_id: "gw1", gateway: "FAM-USB Keller", at: null, manual: true, carry: [], devices: 3, entities: 5, restored: 5 },
];

// the Eltako bus as documented (Installation > Devices > Bus): the installation store with the
// checks the server computed for it (made with installation_checks.py) and the catalog of the series 14
const BUS_TYPES = {"FAM14": {"name": "FAM14", "role": "master", "te": 2, "addresses": 0, "power": 0.8, "supply": 12.0, "assumed": []}, "FTS14KS": {"name": "FTS14KS", "role": "master", "te": 2, "addresses": 0, "power": 0.4, "supply": 8.0, "assumed": []}, "FSNT14-12V/12W": {"name": "FSNT14-12V/12W", "role": "supply", "te": 1, "addresses": 0, "power": null, "supply": 12.0, "assumed": []}, "FSR14-4X": {"name": "FSR14-4x", "role": "actuator", "te": 1, "addresses": 4, "power": 0.7, "supply": null, "assumed": []}, "FSR14-2X": {"name": "FSR14-2x", "role": "actuator", "te": 1, "addresses": 2, "power": 0.14, "supply": null, "assumed": []}, "FSR14M-2X": {"name": "FSR14M-2x", "role": "actuator", "te": null, "addresses": 2, "power": 0.14, "supply": null, "assumed": ["addresses"]}, "FSR14SSR": {"name": "FSR14SSR", "role": "actuator", "te": 1, "addresses": 2, "power": 0.4, "supply": null, "assumed": []}, "F4SR14-LED": {"name": "F4SR14-LED", "role": "actuator", "te": 2, "addresses": 4, "power": 1.0, "supply": null, "assumed": []}, "FMS14": {"name": "FMS14", "role": "actuator", "te": 1, "addresses": null, "power": 0.63, "supply": null, "assumed": []}, "FMZ14": {"name": "FMZ14", "role": "actuator", "te": 1, "addresses": 1, "power": 0.4, "supply": null, "assumed": []}, "FTN14": {"name": "FTN14", "role": "actuator", "te": 1, "addresses": 1, "power": 0.14, "supply": null, "assumed": []}, "FSB14": {"name": "FSB14", "role": "actuator", "te": 1, "addresses": 2, "power": 0.42, "supply": null, "assumed": []}, "F2L14": {"name": "F2L14", "role": "actuator", "te": 1, "addresses": null, "power": 0.14, "supply": null, "assumed": []}, "FZK14": {"name": "FZK14", "role": "actuator", "te": null, "addresses": null, "power": 0.14, "supply": null, "assumed": []}, "FUD14": {"name": "FUD14", "role": "actuator", "te": 1, "addresses": 1, "power": 0.2, "supply": null, "assumed": []}, "FUD14/800W": {"name": "FUD14/800W", "role": "actuator", "te": 2, "addresses": 1, "power": 0.2, "supply": null, "assumed": []}, "FLUD14": {"name": "FLUD14", "role": "other", "te": 1, "addresses": null, "power": null, "supply": null, "assumed": []}, "FSG14/1-10V": {"name": "FSG14/1-10V", "role": "actuator", "te": 1, "addresses": 1, "power": 0.2, "supply": null, "assumed": []}, "FDG14": {"name": "FDG14", "role": "gateway", "te": 2, "addresses": 16, "power": 0.4, "supply": null, "assumed": []}, "FD2G14": {"name": "FD2G14", "role": "gateway", "te": null, "addresses": null, "power": 0.5, "supply": null, "assumed": []}, "FRGBW14": {"name": "FRGBW14", "role": "actuator", "te": null, "addresses": null, "power": 0.1, "supply": null, "assumed": []}, "FHK14": {"name": "FHK14", "role": "actuator", "te": 1, "addresses": null, "power": 0.42, "supply": null, "assumed": []}, "F4HK14": {"name": "F4HK14", "role": "actuator", "te": 1, "addresses": 4, "power": 0.7, "supply": null, "assumed": []}, "FAE14SSR": {"name": "FAE14SSR", "role": "actuator", "te": 1, "addresses": 2, "power": 0.4, "supply": null, "assumed": []}, "FAE14LPR": {"name": "FAE14LPR", "role": "actuator", "te": 1, "addresses": 2, "power": 0.42, "supply": null, "assumed": []}, "FFR14": {"name": "FFR14", "role": "actuator", "te": null, "addresses": null, "power": 0.63, "supply": null, "assumed": []}, "FSU14": {"name": "FSU14", "role": "actuator", "te": 1, "addresses": 8, "power": 0.14, "supply": null, "assumed": []}, "FMSR14": {"name": "FMSR14", "role": "input", "te": 1, "addresses": 5, "power": 0.1, "supply": null, "assumed": []}, "F3Z14D": {"name": "F3Z14D", "role": "meter", "te": 1, "addresses": 3, "power": 0.1, "supply": null, "assumed": []}, "FWZ14-65A": {"name": "FWZ14-65A", "role": "meter", "te": 1, "addresses": 1, "power": 0.1, "supply": null, "assumed": ["addresses"]}, "FWZ14": {"name": "FWZ14", "role": "meter", "te": 1, "addresses": 1, "power": 0.1, "supply": null, "assumed": ["addresses"]}, "DSZ14DRS-3X80A": {"name": "DSZ14DRS-3x80A", "role": "meter", "te": 4, "addresses": null, "power": null, "supply": null, "assumed": []}, "DSZ14WDRS-3X5A": {"name": "DSZ14WDRS-3x5A", "role": "meter", "te": 4, "addresses": null, "power": null, "supply": null, "assumed": []}, "FSDG14": {"name": "FSDG14", "role": "meter", "te": 1, "addresses": 2, "power": 0.4, "supply": null, "assumed": []}, "FGW14": {"name": "FGW14", "role": "gateway", "te": 1, "addresses": 1, "power": 0.5, "supply": null, "assumed": []}, "FGW14-USB": {"name": "FGW14-USB", "role": "gateway", "te": 1, "addresses": 1, "power": 0.3, "supply": null, "assumed": []}, "BGW14": {"name": "BGW14", "role": "gateway", "te": 1, "addresses": null, "power": 0.3, "supply": null, "assumed": []}, "FWG14MS": {"name": "FWG14MS", "role": "gateway", "te": 1, "addresses": null, "power": 0.3, "supply": null, "assumed": []}, "FGSM14": {"name": "FGSM14", "role": "gateway", "te": null, "addresses": null, "power": 0.2, "supply": null, "assumed": []}, "FPLG14": {"name": "FPLG14", "role": "gateway", "te": null, "addresses": null, "power": 0.4, "supply": null, "assumed": []}, "FPLT14": {"name": "FPLT14", "role": "gateway", "te": null, "addresses": null, "power": 0.4, "supply": null, "assumed": []}, "FSM14-UC": {"name": "FSM14-UC", "role": "input", "te": 1, "addresses": null, "power": 0.1, "supply": null, "assumed": []}, "FRP14": {"name": "FRP14", "role": "other", "te": 1, "addresses": null, "power": 0.5, "supply": null, "assumed": []}, "FTD14": {"name": "FTD14", "role": "other", "te": 1, "addresses": null, "power": 0.53, "supply": null, "assumed": []}, "FTS14EM": {"name": "FTS14EM", "role": "input", "te": 2, "addresses": 0, "power": 0.13, "supply": null, "assumed": []}, "FTS14TG": {"name": "FTS14TG", "role": "input", "te": 2.5, "addresses": 1, "power": 0.42, "supply": null, "assumed": []}, "FTS14FA": {"name": "FTS14FA", "role": "input", "te": 1, "addresses": null, "power": 0.5, "supply": null, "assumed": []}, "FTS14GBZ": {"name": "FTS14GBZ", "role": "input", "te": null, "addresses": null, "power": 0.1, "supply": null, "assumed": []}, "FBA14": {"name": "FBA14", "role": "accessory", "te": 1, "addresses": 0, "power": null, "supply": null, "assumed": []}, "STE14": {"name": "STE14", "role": "accessory", "te": 1, "addresses": 0, "power": null, "supply": null, "assumed": []}, "DS14": {"name": "DS14", "role": "accessory", "te": 0.5, "addresses": 0, "power": null, "supply": null, "assumed": []}, "GBA14": {"name": "GBA14", "role": "accessory", "te": 1, "addresses": 0, "power": null, "supply": null, "assumed": []}};
const OBSERVED = {"b1": {"seconds": 60, "heard": 14, "base_id": "FF-00-22-80", "candidates": [["FF-00-22-80", 5]], "answers": {"1": {"sender": "FF-00-22-81", "gateway": "gw1", "wired": false, "rorg": "F6", "data": "70", "time": 0, "kind": "on"}, "2": {"sender": "FF-00-22-82", "gateway": "gw1", "wired": false, "rorg": "F6", "data": "50", "time": 0, "kind": "off"}, "9": {"sender": "FF-00-22-89", "gateway": "gw1", "wired": false, "rorg": "F6", "data": "01", "time": 0, "kind": "up"}, "11": {"sender": "FF-00-22-8B", "gateway": "gw1", "wired": false, "rorg": "A5", "data": "02320009", "time": 0, "kind": "4bs"}, "30": {"sender": "FF-00-22-9E", "gateway": "gw1", "wired": false, "rorg": "F6", "data": "70", "time": 0, "kind": "on"}}}};
const OBSERVED_CHECKS = {"buses": {"b1": {"items": [{"level": "error", "code": "address_twice", "args": {"address": 2}, "targets": [{"type": "channel", "id": "m_fsr:2"}, {"type": "channel", "id": "m_ftn:1"}]}, {"level": "info", "code": "gaps", "args": {"ranges": ["4-8", "10", "15-19"], "highest": 21}, "targets": [{"type": "view", "id": "addresses"}]}, {"level": "info", "code": "documented_only", "args": {"count": 6}, "targets": [{"type": "channel", "id": "m_fsr:3"}, {"type": "channel", "id": "m_f3z:2"}, {"type": "channel", "id": "m_f3z:3"}, {"type": "channel", "id": "m_ftn:1"}, {"type": "channel", "id": "m_fsr4:1"}, {"type": "channel", "id": "m_fsr4:2"}]}, {"level": "warning", "code": "heard_undocumented", "args": {"count": 1, "addresses": ["30"], "assumed": true}, "targets": [{"type": "heard", "id": "30"}]}, {"level": "info", "code": "documented_silent", "args": {"count": 6, "assumed": true}, "targets": [{"type": "channel", "id": "m_fsr:3"}, {"type": "channel", "id": "m_f3z:1"}, {"type": "channel", "id": "m_f3z:2"}, {"type": "channel", "id": "m_f3z:3"}, {"type": "channel", "id": "m_fsr4:1"}, {"type": "channel", "id": "m_fsr4:2"}]}], "supplies": {"mode": "place", "supplies": [{"module": "m_fam", "modules": ["m_fam"], "range": null, "capacity": 12.0, "load": 1.92, "state": "ok", "members": ["m_fam", "m_fsr", "m_fsb"], "without_value": [], "master_supply": [{"module": "m_fam", "watts": 12.0, "from": "integrated"}], "section": "A"}, {"module": "m_s1", "modules": ["m_s1"], "range": null, "capacity": 12.0, "load": 0.44, "state": "ok", "members": ["m_fud", "m_f3z", "m_ftn"], "without_value": [], "master_supply": [], "section": "B"}, {"module": "m_s2", "modules": ["m_s2"], "range": null, "capacity": 12.0, "load": 0.7, "state": "ok", "members": ["m_fsr4"], "without_value": [], "master_supply": [], "section": "C"}], "unfed": []}, "used": 10, "duplicates": [2]}}, "unassigned": []};
const INSTALLATION = {"installation": {"buses": [{"id": "b1", "name": "Hausbus", "master": "m_fam", "base_id": "FF-00-22-80", "access": [{"entry_id": "gw1", "via": "radio"}], "bus_group": null, "note": ""}], "cabinets": [{"id": "c1", "name": "Keller-Verteiler", "area_id": null, "note": "", "rows": [{"id": "r1", "name": "Reihe 1", "te": 12, "next": {"kind": "bbv14", "length_m": null}}, {"id": "r2", "name": "Reihe 2", "te": 12, "next": {"kind": "cable", "length_m": 14.0}}, {"id": "r3", "name": "Reihe 3", "te": 12, "next": {"kind": "", "length_m": null}}]}, {"id": "c2", "name": "UV Obergeschoss", "area_id": null, "note": "", "rows": [{"id": "r4", "name": "Reihe 1", "te": 12, "next": {"kind": "", "length_m": null}}]}], "modules": [{"id": "m_fam", "bus": "b1", "type": "FAM14", "role": "", "name": "", "row": "r1", "slot": 1.0, "te": null, "spacer_before": false, "separator_after": false, "terminator": false, "first_address": null, "supply_watts": "", "legacy_range": "", "legacy_location": "", "origin": null, "supply_id": null, "placeholder": false, "power": "", "circuit": "Steuerung", "fuse": "F12 B10", "installed": "2026-09-28", "revision": "", "note": "", "channels": []}, {"id": "m_fsr", "bus": "b1", "type": "FSR14-4x", "role": "", "name": "Licht EG 1", "row": "r1", "slot": 3.0, "te": null, "spacer_before": false, "separator_after": false, "terminator": false, "first_address": 1, "supply_watts": "", "legacy_range": "", "legacy_location": "", "origin": null, "supply_id": null, "placeholder": false, "power": "", "circuit": "", "fuse": "F3 B16", "installed": "", "revision": "", "note": "", "channels": [{"n": 1, "entry_id": "gw1", "device_key": "05-00-00-01", "manual_id": null, "name": "", "function": "", "feedback_id": "00000081", "unused": false}, {"n": 2, "entry_id": "gw1", "device_key": "05-00-00-03", "manual_id": null, "name": "", "function": "", "feedback_id": "00000082", "unused": false}, {"n": 3, "entry_id": null, "device_key": null, "manual_id": null, "name": "Licht Kellertreppe", "function": "Licht", "feedback_id": "00000083", "unused": false}, {"n": 4, "entry_id": null, "device_key": null, "manual_id": null, "name": "", "function": "", "feedback_id": "", "unused": true}]}, {"id": "m_fsb", "bus": "b1", "type": "FSB14", "role": "", "name": "Rollläden EG", "row": "r1", "slot": 4.0, "te": null, "spacer_before": false, "separator_after": true, "terminator": false, "first_address": 9, "supply_watts": "", "legacy_range": "", "legacy_location": "", "origin": null, "supply_id": null, "placeholder": false, "power": "", "circuit": "", "fuse": "", "installed": "", "revision": "", "note": "", "channels": [{"n": 1, "entry_id": "gw1", "device_key": "05-00-00-04", "manual_id": null, "name": "", "function": "", "feedback_id": "00000181", "unused": false}]}, {"id": "m_s1", "bus": "b1", "type": "FSNT14-12V", "role": "supply", "name": "", "row": "r1", "slot": 5.0, "te": null, "spacer_before": false, "separator_after": false, "terminator": false, "first_address": null, "supply_watts": "12", "legacy_range": "1-8", "legacy_location": "", "origin": "gw1", "supply_id": "s1", "placeholder": false, "power": "", "circuit": "", "fuse": "", "installed": "", "revision": "", "note": "", "channels": []}, {"id": "m_s2", "bus": "b1", "type": "FSNT14-12V", "role": "supply", "name": "", "row": "r4", "slot": 1.0, "te": null, "spacer_before": false, "separator_after": false, "terminator": false, "first_address": null, "supply_watts": "12", "legacy_range": "9-126", "legacy_location": "", "origin": "gw1", "supply_id": "s2", "placeholder": false, "power": "", "circuit": "", "fuse": "", "installed": "", "revision": "", "note": "", "channels": []}, {"id": "m_fud", "bus": "b1", "type": "FUD14", "role": "", "name": "", "row": "r1", "slot": 7.5, "te": null, "spacer_before": true, "separator_after": false, "terminator": false, "first_address": 11, "supply_watts": "", "legacy_range": "", "legacy_location": "", "origin": null, "supply_id": null, "placeholder": false, "power": "", "circuit": "", "fuse": "", "installed": "", "revision": "", "note": "", "channels": [{"n": 1, "entry_id": "gw1", "device_key": "05-00-00-02", "manual_id": null, "name": "", "function": "", "feedback_id": "", "unused": false}]}, {"id": "m_f3z", "bus": "b1", "type": "F3Z14D", "role": "", "name": "", "row": "r2", "slot": 1.0, "te": null, "spacer_before": false, "separator_after": false, "terminator": false, "first_address": 12, "supply_watts": "", "legacy_range": "", "legacy_location": "", "origin": "gw1", "supply_id": null, "placeholder": false, "power": "", "circuit": "", "fuse": "", "installed": "", "revision": "", "note": "", "channels": [{"n": 1, "entry_id": "gw1", "device_key": null, "manual_id": "m3", "name": "F3Z14D", "function": "Stromzähler Haus", "feedback_id": "00008C0C", "unused": false}, {"n": 2, "entry_id": null, "device_key": null, "manual_id": null, "name": "Stromzähler Haus L2", "function": "", "feedback_id": "00008C0D", "unused": false}, {"n": 3, "entry_id": null, "device_key": null, "manual_id": null, "name": "Stromzähler Haus L3", "function": "", "feedback_id": "00008C0E", "unused": false}]}, {"id": "m_ftn", "bus": "b1", "type": "FTN14", "role": "", "name": "Treppenlicht", "row": "r2", "slot": 2.0, "te": null, "spacer_before": false, "separator_after": false, "terminator": false, "first_address": 2, "supply_watts": "", "legacy_range": "", "legacy_location": "", "origin": null, "supply_id": null, "placeholder": false, "power": "", "circuit": "", "fuse": "", "installed": "", "revision": "", "note": "", "channels": [{"n": 1, "entry_id": null, "device_key": null, "manual_id": null, "name": "Treppenlicht Keller", "function": "Licht (Zeit)", "feedback_id": "", "unused": false}]}, {"id": "m_ls", "bus": "b1", "type": "LS", "role": "foreign", "name": "LS B16 F1–F6", "row": "r3", "slot": 1.0, "te": 6.0, "spacer_before": false, "separator_after": false, "terminator": false, "first_address": null, "supply_watts": "", "legacy_range": "", "legacy_location": "", "origin": null, "supply_id": null, "placeholder": false, "power": "", "circuit": "", "fuse": "", "installed": "", "revision": "", "note": "", "channels": []}, {"id": "m_fsr4", "bus": "b1", "type": "FSR14-4x", "role": "", "name": "Licht OG", "row": "r4", "slot": 2.0, "te": null, "spacer_before": false, "separator_after": false, "terminator": true, "first_address": 20, "supply_watts": "", "legacy_range": "", "legacy_location": "", "origin": null, "supply_id": null, "placeholder": false, "power": "", "circuit": "", "fuse": "", "installed": "", "revision": "", "note": "", "channels": [{"n": 1, "entry_id": null, "device_key": null, "manual_id": null, "name": "Licht Kind 1", "function": "", "feedback_id": "", "unused": false}, {"n": 2, "entry_id": null, "device_key": null, "manual_id": null, "name": "Licht Kind 2", "function": "", "feedback_id": "", "unused": false}]}]}, "checks": {"buses": {"b1": {"items": [{"level": "error", "code": "address_twice", "args": {"address": 2}, "targets": [{"type": "channel", "id": "m_fsr:2"}, {"type": "channel", "id": "m_ftn:1"}]}, {"level": "info", "code": "gaps", "args": {"ranges": ["4-8", "10", "15-19"], "highest": 21}, "targets": [{"type": "view", "id": "addresses"}]}, {"level": "info", "code": "documented_only", "args": {"count": 6}, "targets": [{"type": "channel", "id": "m_fsr:3"}, {"type": "channel", "id": "m_f3z:2"}, {"type": "channel", "id": "m_f3z:3"}, {"type": "channel", "id": "m_ftn:1"}, {"type": "channel", "id": "m_fsr4:1"}, {"type": "channel", "id": "m_fsr4:2"}]}], "supplies": {"mode": "place", "supplies": [{"module": "m_fam", "modules": ["m_fam"], "range": null, "capacity": 12.0, "load": 1.92, "state": "ok", "members": ["m_fam", "m_fsr", "m_fsb"], "without_value": [], "master_supply": [{"module": "m_fam", "watts": 12.0, "from": "integrated"}], "section": "A"}, {"module": "m_s1", "modules": ["m_s1"], "range": null, "capacity": 12.0, "load": 0.44, "state": "ok", "members": ["m_fud", "m_f3z", "m_ftn"], "without_value": [], "master_supply": [], "section": "B"}, {"module": "m_s2", "modules": ["m_s2"], "range": null, "capacity": 12.0, "load": 0.7, "state": "ok", "members": ["m_fsr4"], "without_value": [], "master_supply": [], "section": "C"}], "unfed": []}, "used": 10, "duplicates": [2]}}, "unassigned": []}};

const device = (o) => ({ signal: null, follows: [], category: "lighting", group: "", bus_address: "", feedback_id: "", bus_power: "", eep_extra: [], virtual: false, wall_switch: null, senders: [], model: null, area: null, location: "", circuit: "", fuse: "", installed: "", revision: "", power: "", note: "", note_key: o.id, ...o });

export function fakeHass(params = new URLSearchParams()) {
  const takeoverRuns = makeRuns();
  const bus = JSON.parse(JSON.stringify(INSTALLATION)); // edits of the bus view change this copy
  const now = Date.now() / 1000;
  const empty = params.has("empty");
  const english = params.get("lang") === "en"; // sample notes in the language of the page
  const gateway = {
    entry_id: "gw1", title: "FAM-USB Keller", model: "Eltako FAM-USB", base_id: "FF-00-11-80", loaded: true, connected: true,
    on_demand: false, connection: "tcp 127.0.0.1:9100", per_minute: 4, last_telegram: now - 3, queue: 0, unconfirmed: 0,
    devices: 3, free_senders: 120, senders: [{ id: "FF-00-11-81", device: "Licht Diele", profile: "central" }], hidden: params.has("hide") ? ["01-00-00-99"] : [],
    server_time: now + Number(params.get("skew") || 0), disconnected_since: null, proxy: null, via_proxy: false,
    note: english ? "Basement, right of the meter" : "Keller, rechts neben dem Zähler", orphan_notes: 0, supplies: [{ id: "s1", name: "FSNT14-12V", watts: "12", first: "1", last: "8" }, { id: "s2", name: "FSNT14-12V", watts: "12", first: "9", last: "126" }],
    manual: english
      ? [{ id: "m1", name: "Hallway button left", address: "00-00-00-11", function: "taught in directly to Licht Diele" }, { id: "m2", name: "Motion sensor basement", address: "00-00-00-12", function: "FBH65, belongs to another system" }, { id: "m3", name: "F3Z14D", address: "", function: "Stromzähler Haus", bus_address: "12", feedback_id: "00008C0C", bus_power: "", bus_power_table: null }]
      : [{ id: "m1", name: "Taster Flur links", address: "00-00-00-11", function: "direkt auf Licht Diele eingelernt" }, { id: "m2", name: "Bewegungsmelder Keller", address: "00-00-00-12", function: "FBH65, von einem anderen System" }, { id: "m3", name: "F3Z14D", address: "", function: "Stromzähler Haus", bus_address: "12", feedback_id: "00008C0C", bus_power: "", bus_power_table: null }],
    radio_devices: [
      { id: "05-00-00-01", device: "Licht Diele", category: "lighting", last_seen: now - 30, silent: false, ha_device: "dev123", area: "Flur", entities: 3, eep: "M5-38-08:eltako", model: "FSR14-4x", models: [], labels: ["lbl_battery"], disabled: false,
        key: "sub1", teach: [{ profile: "central", id: "FF-00-11-81", ute: false }, { profile: "rocker", id: "FF-00-11-83", ute: false }] },
      { id: "05-00-00-02", device: "Dimmer Flur", category: "lighting", last_seen: now - 90, silent: false, ha_device: "dev124", area: "Flur", entities: 1, eep: "A5-38-08:eltako", model: "", models: ["FUD14", "FUD61", "FD62"], key: "sub2", teach: [], labels: [], disabled: false },
      { id: "05-00-00-06", device: "Temperatur Bad", category: "sensors", last_seen: now - 200000, silent: true, ha_device: "dev456", area: "Bad", entities: 2, entity_ids: ["sensor.temperatur_bad_temperatur", "sensor.temperatur_bad_feuchte"], eep: "A5-02-05" },
      { id: "05-00-00-05", device: "Fensterkontakt Küche", category: "sensors", last_seen: null, silent: false, area: "Küche", entities: 1, eep: "D5-00-01" },
    ],
  };
  const labels = [{ label_id: "lbl_battery", name: "Battery" }, { label_id: "lbl_window", name: "Window" }];
  const gateways = empty ? [] : [gateway];
  if (params.has("two") && !empty) {
    gateways.push({ ...gateway, entry_id: "gw2", title: "MGW Garage", base_id: "FF-00-33-80", radio_devices: params.has("shared") ? [{ id: "05-00-00-01", device: "Licht Garage", category: "lighting", last_seen: now - 10, silent: false, eep: "M5-38-08:eltako", key: "sub9", teach: [] }] : [], connected: false, disconnected_since: now - 4000 });
  }
  const at = (s) => new Date(Date.now() - s * 1000).toISOString();
  const history = empty ? [] : [
    { time: at(50), dir: "tx", sender: "FF-00-11-81", rorg: "F6", data: "70", status: "30", destination: "FF-FF-FF-FF", dbm: null, gateway: "gw1", gateway_name: "FAM-USB Keller", device: "Licht Diele", device_key: "sub1", profile: "central" },
    { time: at(49.8), dir: "rx", sender: "05-00-00-01", rorg: "F6", data: "70", status: "30", destination: "FF-FF-FF-FF", dbm: -62, gateway: "gw1", gateway_name: "FAM-USB Keller", device: "Licht Diele", ha_device: "dev123", device_key: "sub1", eep: "M5-38-08:eltako", model: "FSR14-4x", fields: [{ label: "on", value: true }] },
    { time: at(30), dir: "rx", sender: "05-00-00-02", rorg: "A5", data: "0264A808", status: "00", destination: "FF-FF-FF-FF", dbm: -70, gateway: "gw1", gateway_name: "FAM-USB Keller", device: "Dimmer Flur", ha_device: "dev124", device_key: "sub2", eep: "A5-38-08:eltako", models: ["FUD14", "FUD61", "FD62"], fields: [{ label: "dim", value: 50 }] },
    { time: at(20), dir: "rx", sender: "01-00-00-99", rorg: "A5", data: "0064A808", status: "00", destination: "FF-FF-FF-FF", dbm: -88, gateway: "gw1", gateway_name: "FAM-USB Keller", candidates: ["A5-02-05", "A5-10-06"] },
  ];
  const pool = {
    id: "gw1", kind: "radio", title: "FAM-USB Keller", size: 128, free: 119, first: 0xff001180, unavailable: [0xff001190, 0xff001191],
    start: "FF-00-11-80", end: "FF-00-11-FF", next_free: "FF-00-11-82",
    rows: [
      { id: "FF-00-11-81", decimal: 0xff001181, device: "Licht Diele", ref: "05-00-00-01", profile: "central", state: "assigned" },
      { id: "FF-00-11-85", decimal: 0xff001185, device: null, ref: "abc", profile: "central", state: "blocked" },
    ],
  };
  const listeners = {};
  const sent = []; // websocket commands the panel sent (send, teach-in ...), for the checks
  let push = () => {};
  const hass = {
    language: params.get("lang") || "de",
    locale: { language: params.get("lang") || "de", number_format: "language", time_format: "language", time_zone: "local" },
    config: { time_zone: "Europe/Berlin" },
    states: {
      "sensor.temperatur_bad_temperatur": { entity_id: "sensor.temperatur_bad_temperatur", state: "21.5", attributes: { unit_of_measurement: "°C", friendly_name: "Temperatur Bad Temperatur" } },
      "sensor.temperatur_bad_feuchte": { entity_id: "sensor.temperatur_bad_feuchte", state: "unavailable", attributes: { unit_of_measurement: "%", friendly_name: "Temperatur Bad Feuchte" } },
    },
    themes: { darkMode: params.has("dark"), theme: "default" },
    connection: {
      connected: true,
      addEventListener: (event, callback) => (listeners[event] = callback),
      removeEventListener: () => {},
      subscribeMessage: (callback, msg) => {
        if (msg?.type === "enocean_eltako/installation/listen") {
          // reading the bus: a progress event, then what was heard (sample data, the time is now)
          sent.push(msg);
          const answers = Object.fromEntries(Object.entries(OBSERVED.b1.answers).map(([a, x]) => [a, { ...x, time: Date.now() / 1000 - 5 }]));
          setTimeout(() => callback({ type: "progress", left: 0, heard: 14 }), 5);
          setTimeout(() => {
            bus.observed = { b1: { ...OBSERVED.b1, seconds: msg.seconds, answers } };
            bus.checks = OBSERVED_CHECKS;
            callback({ type: "done", installation: bus.installation, checks: bus.checks, observed: bus.observed, types: BUS_TYPES });
          }, 10);
          return Promise.resolve(() => {});
        }
        for (const row of history) callback({ ...row, history: true });
        push = callback;
        return Promise.resolve(() => {});
      },
    },
    callWS: async (msg) => {
      sent.push(msg);
      switch (msg.type) {
        case "enocean_eltako/gateways":
          return gateways;
        case "enocean_eltako/device_details": {
          const actuator = msg.device === "sub1";
          return {
            key: msg.device, entry_id: msg.entry_id, gateway_name: "FAM-USB Keller", category: "lighting",
            model: actuator ? "FSR14-4x" : "", model_name: actuator ? "FSR14-4x" : "", models: ["FSR14-4x", "FSR61NP-230V", "FL62"],
            eep: actuator ? "M5-38-08:eltako" : "A5-38-08:eltako", eep_extra: [],
            last_telegrams: [{ sender: "01-00-00-98", gateway: msg.entry_id, rorg: "A5", data: "0080B40D", status: 0, dbm: -77, time: Date.now() / 1000 - 960, fields: [{ label: "Temperature", value: 3.7, unit: "°C" }, { label: "Humidity", value: 70.8, unit: "%" }] }],
            signal: { rssi: -62, min: -78, max: -55 }, repeat: 0,
            heard_by: actuator ? { gateways: [{ entry_id: msg.entry_id, name: "FAM-USB Keller", count: 900, direct: 880, rssi: -62, last: 0 }, { entry_id: "gw2", name: "MGW-ETH Dach", count: 384, direct: 0, rssi: -81, last: 0 }], best: msg.entry_id, repeater_only: false } : { gateways: [{ entry_id: msg.entry_id, name: "FAM-USB Keller", count: 12, direct: 0, rssi: -84, last: 0 }], best: null, repeater_only: true },
            sender_test: actuator, note: actuator ? (english ? "Cabinet 2, slot 4, fuse F3" : "Schrank 2, Platz 4, Sicherung F3") : "",
            telegrams: 1284, interval: null, silent: false,
            senders: actuator ? [{ profile: "central", id: "FF-00-11-81", ute: false }, { profile: "rocker", id: "FF-00-11-83", ute: false }] : [],
            commands: actuator ? { sent: 86, confirmed: 84, rate: 97.7, latency_avg: 1.4, latency_max: 3.1 } : null,
            settings: actuator ? { platform: "light", invert: false, status_request: true } : {},
            entities: [{ name: "Licht", entity_id: "light.licht_diele", state: "on", unit: null }, { name: "Signalstärke", entity_id: "sensor.licht_diele_signal", state: "-62", unit: "dBm" }],
          };
        }
        case "config/area_registry/list":
          return [{ area_id: "flur", name: "Flur" }, { area_id: "bad", name: "Bad" }];
        case "config/label_registry/list":
          return labels;
        case "config/label_registry/create": {
          const label = { label_id: `lbl_${msg.name.toLowerCase()}`, name: msg.name };
          labels.push(label);
          return label;
        }
        case "config/device_registry/update": {
          const device = gateway.radio_devices.find((d) => d.ha_device === msg.device_id);
          if ("area_id" in msg) device.area = msg.area_id === "bad" ? "Bad" : msg.area_id === "flur" ? "Flur" : null;
          if ("labels" in msg) device.labels = msg.labels;
          if ("disabled_by" in msg) device.disabled = msg.disabled_by !== null;
          return {};
        }
        case "enocean_eltako/remove_devices":
          gateway.radio_devices = gateway.radio_devices.filter((d) => !msg.devices.includes(d.key));
          return { removed: msg.devices.length };
        case "enocean_eltako/set_model":
          return { model_name: msg.model_name };
        case "enocean_eltako/takeover/status":
          return { available: !empty && !params.has("closed"), reports: empty ? 0 : takeoverRuns.length };
        case "enocean_eltako/documentation":
          return {
            version: 3, generated: new Date().toISOString(), installation: empty ? { buses: [], cabinets: [], modules: [] } : bus.installation, installation_checks: empty ? { buses: {}, unassigned: [] } : bus.checks, installation_observed: bus.observed ?? {}, bus_types: BUS_TYPES,
            gateways: empty ? [] : [{
              entry_id: "gw1", title: "FAM-USB Keller", model: "fam_usb", model_name: "Eltako FAM-USB", base_id: "FF-00-11-80", hidden_senders: [],
              note: gateway.note, manual: gateway.manual, supplies: gateway.supplies, heard: [], orphan_notes: 0,
              devices: [
                device({ name: "Licht Diele", key: "sub1", id: "05-00-00-01", eep: "M5-38-08:eltako", area: "Flur", model: "FSR14-4x", bus_address: "1", feedback_id: "00000081", group: english ? "Light hallway" : "Licht Flur", bus_power_table: 0.7, location: english ? "Cabinet 2, row 1, slot 4" : "Schrank 2, Reihe 1, Platz 4", fuse: "F3 B16", installed: "2026-10-01", power: english ? "mains" : "Netz",
                  wall_switch: { id: "05-00-00-A1", on: "a0", off: "a1" }, senders: [{ profile: "central", id: "FF-00-11-81", ute: false, test: "confirmed" }, { profile: "rocker", id: "FF-00-11-83", ute: false, test: "unconfirmed" }] }),
                device({ name: "Licht Küche", key: "sub8", id: "05-00-00-03", eep: "M5-38-08:eltako", area: "Küche", model: "FSR14-4x", bus_address: "2", feedback_id: "00000082", group: english ? "Light hallway" : "Licht Flur", bus_power_table: 0.7 }),
                device({ name: "Dimmer Flur", key: "sub2", id: "05-00-00-02", eep: "A5-38-08:eltako", area: "Flur", model: "FUD14", location: english ? "Cabinet 2, row 1, slot 5" : "Schrank 2, Reihe 1, Platz 5", senders: [] }),
                device({ name: "Fensterkontakt Küche", key: "sub3", id: "05-00-00-05", eep: "D5-00-01:std", area: "Küche", category: "sensors", signal: { last: now - 7200, rssi: -68, repeater_only: false }, power: "CR2032", note: english ? "battery changed 03/2026" : "Batterie gewechselt 03/2026" }),
                device({ name: "Rollladen Bad", key: "sub4", id: "05-00-00-04", eep: "M5-3F-7F:eltako", area: "Bad", category: "covers", model: "FSB14", bus_address: "9", feedback_id: "00000181", bus_power_table: 0.42, wall_switch: { id: "FE-00-00-04", on: "a0", off: "b0" }, senders: [{ profile: "central", id: "FF-00-11-A4", ute: false, test: null }] }),
                device({ name: "Taster Haustür", key: "sub5", id: "FE-00-00-01", eep: "F6-02-01:std", area: "Flur", category: "buttons", signal: { last: now - 3 * 86400, rssi: -77, repeater_only: false }, model: "F4T55E", location: english ? "Hallway" : "Flur EG" }),
                device({ name: "Raumregler Temperatur", key: "sub6", id: "FE-00-00-02", eep: "A5-10-06:eltako", signal: { last: now - 10 * 86400, rssi: -84, repeater_only: true }, eep_extra: ["A5-04-01:std"], category: "climate", model: "FUTH55D", group: english ? "Room controller living room" : "Raumregler Wohnzimmer", location: english ? "Living room" : "Wohnzimmer" }),
                device({ name: "Raumregler Taste", key: "sub7", id: "FE-00-00-03", eep: "F6-02-01:std", category: "sensors", model: "FUTH55D", group: english ? "Room controller living room" : "Raumregler Wohnzimmer" }),
                device({ name: "HA Fenster Bad", key: "sub9", id: "FF-00-11-8A", eep: "D5-00-01:std", category: "virtual", virtual: true, model: "Virtual window contact", follows: ["binary_sensor.fenster_bad"] }),
                device({ name: "HA Taster Szene Abend", key: "sub10", id: "FF-00-11-8B", eep: "F6-02-01:std", category: "virtual", model: "Virtual button" }),
              ],
              pools: [{ id: "radio:gw1", kind: "radio", start: "FF-00-11-81", end: "FF-00-11-FF", senders: [{ id: "FF-00-11-81", device: "Licht Diele", ref: "05-00-00-01", profile: "central", state: "assigned" }, { id: "FF-00-11-C1", device: "Licht Diele", ref: "05-00-00-01", profile: "rocker", state: "assigned" }, { id: "FF-00-11-A4", device: "Rollladen Bad", ref: "05-00-00-04", profile: "central", state: "assigned" }, { id: "FF-00-11-85", device: null, ref: "abc", profile: "central", state: "blocked" }, { id: "FF-00-11-8A", device: "HA Fenster Bad", ref: "FF-00-11-8A", profile: "contact", state: "assigned" }, { id: "FF-00-11-8B", device: "HA Taster Szene Abend", ref: "FF-00-11-8B", profile: "rocker", state: "assigned" }] }],
              links: [
                { key: "assigned|05-00-00-01|central", source: "assigned", from_kind: "ha", from_id: "FF-00-11-81", from_name: "", to_key: "05-00-00-01", to_id: "05-00-00-01", to_name: "Licht Diele", role: "central", learn: "", status: "confirmed", teach_in: "2026-10-26T09:14:00+00:00", tested: "2026-10-26T09:15:00+00:00" },
                { key: "assigned|05-00-00-01|rocker", source: "assigned", from_kind: "ha", from_id: "FF-00-11-83", from_name: "", to_key: "05-00-00-01", to_id: "05-00-00-01", to_name: "Licht Diele", role: "rocker", learn: "", status: "no_answer", teach_in: null, tested: "2026-10-26T09:15:00+00:00" },
                { key: "declared|05-00-00-01|05-00-00-A1", source: "declared", from_kind: "wall", from_id: "05-00-00-A1", from_name: "", to_key: "05-00-00-01", to_id: "05-00-00-01", to_name: "Licht Diele", role: "a0 / a1", learn: "", status: "declared", teach_in: null, tested: null },
                { key: "entered|k1", id: "k1", source: "entered", from_kind: "entered", from_id: "00-00-00-11", from_name: english ? "Hallway button left" : "Taster Flur links", to_key: "05-00-00-01", to_id: "05-00-00-01", to_name: "Licht Diele", role: "rocker", learn: english ? "function 0" : "Funktion 0", status: "entered", teach_in: null, tested: null },
              ],
              log: [
                { time: "2026-10-26T09:12:00+00:00", kind: "device_added", device: "05-00-00-01", detail: "Licht Diele" },
                { time: "2026-10-26T09:14:00+00:00", kind: "teach_in", device: "05-00-00-01", detail: "Licht Diele: central" },
                { time: "2026-10-26T09:15:00+00:00", kind: "sender_test", device: "05-00-00-01", detail: "Licht Diele: central=confirmed, rocker=unconfirmed" },
                // a recent event: the log writes its age in words ("30 s ago") instead of a time of day
                { time: new Date(Date.now() - 30000).toISOString().slice(0, 19) + "+00:00", kind: "teach_in", device: "05-00-00-01", detail: "Licht Diele: rocker" },
              ],
            }],
          };
        case "enocean_eltako/installation/set": {
          const list = { module: "modules", cabinet: "cabinets", bus: "buses" }[msg.kind];
          const item = { ...msg.item, id: msg.item.id || `${msg.kind}${bus.installation[list].length + 1}` };
          if (msg.kind === "cabinet") item.rows = (item.rows ?? []).map((r, i) => ({ next: { kind: "", length_m: null }, ...r, id: r.id || `${item.id}r${i + 1}` }));
          const at = bus.installation[list].findIndex((x) => x.id === item.id);
          if (at >= 0) bus.installation[list][at] = { ...bus.installation[list][at], ...item };
          else bus.installation[list].push(item);
          return { id: item.id, installation: bus.installation, checks: bus.checks, types: BUS_TYPES };
        }
        case "enocean_eltako/installation/move":
          return { installation: bus.installation, checks: bus.checks, types: BUS_TYPES };
        case "enocean_eltako/installation/remove": {
          const list = { module: "modules", cabinet: "cabinets", bus: "buses" }[msg.kind];
          bus.installation[list] = bus.installation[list].filter((x) => x.id !== msg.item_id);
          return { installation: bus.installation, checks: bus.checks, types: BUS_TYPES };
        }
        case "enocean_eltako/set_links":
        case "enocean_eltako/set_link_learn":
          return {};
        case "enocean_eltako/set_supplies":
          gateway.supplies = msg.supplies;
          return {};
        case "enocean_eltako/import_documentation":
          // a gateway of the file is matched when the call maps its base ID to a gateway set up here
          return { gateways: msg.doc.gateways.map((g) => ({ title: g.title, base_id: g.base_id, matched: !!msg.gateway_map?.[g.base_id], notes: 0, manual: 0 })) };
        case "enocean_eltako/set_fields":
          return { saved: msg.items.length, rejected: [] };
        case "enocean_eltako/sender_pools":
          return empty ? [] : [pool];
        case "enocean_eltako/sender_pools/free_all":
          return { freed: msg.senders.length };
        case "enocean_eltako/takeover/preview":
          return { devices: takeoverDevices, old_active: true };
        case "enocean_eltako/takeover/mapping":
          return { rows: takeoverRows, devices: takeoverStored, missing: { "05-00-00-07": ["area", "names"] }, old_active: true, old_entities: true, strategy: params.get("strategy") };
        case "enocean_eltako/takeover/restore":
          return { restored: 2, blocked: 0, in_use: 0 };
        case "enocean_eltako/takeover/strategy":
          return {};
        case "enocean_eltako/takeover/reports":
          return takeoverRuns;
        case "enocean_eltako/takeover/report":
          return { ...takeoverRuns.find((r) => r.id === msg.run_id), rows: takeoverRows, devices: takeoverStored, totals: {} };
        case "enocean_eltako/takeover/report_delete":
          takeoverRuns.splice(takeoverRuns.findIndex((r) => r.id === msg.run_id), 1);
          return {};
        case "enocean_eltako/takeover/run":
        case "enocean_eltako/takeover/carry":
          return { count: 1, carried: 1, skipped: [] };
        case "enocean_eltako/send":
          return { result: "sent" };
        case "enocean_eltako/teach_in":
          return { ute: false, window: 0 };
        default:
          throw { code: "unknown_command", message: msg.type };
      }
    },
  };
  // a new telegram as the server would send it
  return { hass, sent, listeners, push: (row) => push({ gateway: "gw1", gateway_name: "FAM-USB Keller", destination: "FF-FF-FF-FF", ...row }) };
}
