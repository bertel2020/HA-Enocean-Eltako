"""Status of the EnOcean Proxy app for gateways reached through it (panel "EnOcean").

The app serves a read-only status on STATUS_PORT inside the Supervisor network; the
integration polls it every POLL_INTERVAL and keeps the part about its own gateway (matched
by TCP port): app version, other programs connected, air time against the 1 % duty cycle,
replayed telegrams, a program that currently has the gateway alone.

An app older than MIN_VERSION raises a repair issue: it lacks what this integration expects
(0.5.2: one discovery message listing every gateway).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import timedelta
from typing import TYPE_CHECKING, Any

import aiohttp
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_interval

from .const import CONF_DEVICE, CONF_PROXY_REPLAY, DOMAIN

if TYPE_CHECKING:
    from . import EnOceanEltakoConfigEntry

_LOGGER = logging.getLogger(__name__)

CONF_PROXY_STATUS_PORT = "proxy_status_port"
DEFAULT_STATUS_PORT = 9199
POLL_INTERVAL = timedelta(seconds=15)
TIMEOUT = aiohttp.ClientTimeout(total=5)
MIN_VERSION = "0.5.2"


def parse_version(version: str | None) -> tuple[int, ...] | None:
    """(0, 5, 2) from "0.5.2"; None for a missing or local build version ("dev")."""
    try:
        return tuple(int(part) for part in (version or "").split("."))
    except ValueError:
        return None


def outdated(version: str | None) -> bool:
    parsed = parse_version(version)
    return parsed is not None and parsed < tuple(int(p) for p in MIN_VERSION.split("."))


@callback
def async_check_version(
    hass: HomeAssistant, entry: EnOceanEltakoConfigEntry, version: str | None
) -> None:
    """Raise or clear the "update the EnOcean Proxy app" issue of this gateway."""
    issue_id = f"proxy_outdated_{entry.entry_id}"
    if version is None:  # unknown (not reachable or local build): leave the issue as it is
        return
    if outdated(version):
        ir.async_create_issue(
            hass,
            DOMAIN,
            issue_id,
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="proxy_outdated",
            translation_placeholders={
                "gateway": entry.title,
                "version": version,
                "minimum": MIN_VERSION,
            },
        )
    else:
        ir.async_delete_issue(hass, DOMAIN, issue_id)


def summarize(status: dict[str, Any], port: int) -> dict[str, Any] | None:
    """The part of the app's status about the gateway on this port."""
    gateway = next((g for g in status.get("gateways", []) if g.get("port") == port), None)
    if gateway is None:
        return None
    duty = gateway.get("duty_cycle", {})
    stats = gateway.get("stats", {})
    return {
        "version": status.get("version") or None,
        "name": gateway.get("name"),
        "connected": bool(gateway.get("connected")),
        "programs": len(gateway.get("clients", [])),
        "duty_of_limit": duty.get("of_limit"),
        "telegrams_sent": duty.get("telegrams"),
        "replayed": stats.get("replayed"),
        "exclusive_peer": gateway.get("exclusive_peer"),
    }


@callback
def async_setup_proxy_status(
    hass: HomeAssistant, entry: EnOceanEltakoConfigEntry
) -> Callable[[], None] | None:
    """Poll the app's status for a gateway set up through it; None for other gateways."""
    device = entry.data.get(CONF_DEVICE, {})
    if device.get("type") != "tcp" or not entry.options.get(CONF_PROXY_REPLAY):
        return None
    host, port = device["host"], int(device["port"])
    url = f"http://{host}:{entry.data.get(CONF_PROXY_STATUS_PORT, DEFAULT_STATUS_PORT)}/api/status"
    session = async_get_clientsession(hass)

    async def poll(_now: Any = None) -> None:
        runtime = entry.runtime_data
        try:
            async with session.get(url, timeout=TIMEOUT) as response:
                response.raise_for_status()
                runtime.proxy = summarize(await response.json(), port)
            if runtime.proxy is not None:
                async_check_version(hass, entry, runtime.proxy["version"])
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            if runtime.proxy is not None:
                _LOGGER.debug("EnOcean Proxy status from %s unavailable: %s", url, err)
            runtime.proxy = None

    @callback
    def schedule(_now: Any = None) -> None:
        entry.async_create_background_task(hass, poll(), f"enocean_eltako proxy status {host}")

    schedule()
    return async_track_time_interval(hass, schedule, POLL_INTERVAL)
