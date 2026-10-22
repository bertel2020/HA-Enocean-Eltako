"""Sidebar panel "EnOcean": the live telegram monitor (Phase 4), admins only.

A plain web component (frontend/monitor-panel.js, no build step) served from the
integration; it reads the websocket API in websocket.py. It loads its parts (shared.js,
texts.js, takeover.js) with its own query string. The URL carries a hash of all panel files,
so browsers load a new version of every part after an update.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from homeassistant.components import panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

STATIC_URL = "/enocean_eltako_static"
PANEL_PATH = "enocean-eltako"
PANEL_FILE = Path(__file__).parent / "frontend" / "monitor-panel.js"


def _version() -> str:
    """Hash of all panel files: a change in any part gives a new URL."""
    digest = hashlib.sha256()
    for path in sorted(PANEL_FILE.parent.glob("*.js")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()[:8]


async def async_register_panel(hass: HomeAssistant) -> None:
    """Register once per start; skipped without the frontend (e.g. in tests)."""
    if hass.http is None or "frontend" not in hass.config.components:
        return
    version = await hass.async_add_executor_job(_version)
    await hass.http.async_register_static_paths(
        [StaticPathConfig(STATIC_URL, str(PANEL_FILE.parent), cache_headers=False)]
    )
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_PATH,
        webcomponent_name="enocean-eltako-monitor",
        sidebar_title="EnOcean",
        sidebar_icon="mdi:radio-tower",
        module_url=f"{STATIC_URL}/monitor-panel.js?v={version}",
        require_admin=True,
    )
