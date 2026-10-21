"""Where entity IDs are used: automations, scripts, scenes and dashboards.

Used by the takeover view to show what still refers to an entity of the old integration.
Automations, scripts and scenes come from the helpers Home Assistant's own search uses;
dashboards are searched as text, so YAML dashboards are found only when they can be loaded.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable, Iterable

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

KINDS = ("automation", "script", "scene", "dashboard")

type Usage = dict[str, list[str]]


def _names(hass: HomeAssistant, entity_ids: Iterable[str]) -> list[str]:
    names = []
    for entity_id in entity_ids:
        state = hass.states.get(entity_id)
        names.append(state.name if state is not None else entity_id)
    return sorted(names)


def _helper(hass: HomeAssistant, domain: str, function: str) -> Callable[[str], list[str]]:
    """automation.automations_with_entity and its siblings; none when the domain is not loaded."""
    try:
        module = __import__(f"homeassistant.components.{domain}", fromlist=[function])
        find = getattr(module, function)
    except (ImportError, AttributeError):
        return lambda _entity_id: []

    def search(entity_id: str) -> list[str]:
        try:
            return _names(hass, find(hass, entity_id))
        except (KeyError, AttributeError):  # the component is not set up
            return []

    return search


async def _dashboards(hass: HomeAssistant) -> list[tuple[str, str]]:
    """Title and text of each dashboard that can be loaded."""
    try:
        from homeassistant.components.lovelace.const import LOVELACE_DATA
    except ImportError:
        return []
    data = hass.data.get(LOVELACE_DATA)
    if data is None:
        return []
    found = []
    for url_path, dashboard in data.dashboards.items():
        try:
            config = await dashboard.async_load(False)
        except Exception:  # not loadable (YAML error, none stored yet): nothing to search
            continue
        title = (getattr(dashboard, "config", None) or {}).get("title") or url_path or "Overview"
        found.append((str(title), json.dumps(config, ensure_ascii=False)))
    return found


async def async_usage(hass: HomeAssistant, entity_ids: Iterable[str]) -> dict[str, Usage]:
    """For each entity ID the names of the automations, scripts, scenes and dashboards using it."""
    searches = {
        "automation": _helper(hass, "automation", "automations_with_entity"),
        "script": _helper(hass, "script", "scripts_with_entity"),
        "scene": _helper(hass, "scene", "scenes_with_entity"),
    }
    dashboards = await _dashboards(hass)
    result: dict[str, Usage] = {}
    for entity_id in entity_ids:
        usage: Usage = {kind: search(entity_id) for kind, search in searches.items()}
        pattern = re.compile(rf"(?<![\w.]){re.escape(entity_id)}(?!\w)")
        usage["dashboard"] = sorted(title for title, text in dashboards if pattern.search(text))
        result[entity_id] = usage
    return result
