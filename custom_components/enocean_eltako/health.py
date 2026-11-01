"""E5: repair issues for silent devices and gateways that stay disconnected or keep
dropping (a port another integration or program uses as well);
E11: bus actors that confirm slowly (FAM14 not in operating mode 5)."""

from __future__ import annotations

import statistics
import time
from collections.abc import Callable
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.event import async_track_time_interval

from .catalog import CATALOG
from .const import CONF_DEVICE, CONF_MODEL, CONF_PATH, DOMAIN
from .protocol.models import MODELS
from .protocol.telegram import Rorg

if TYPE_CHECKING:
    from . import EnOceanEltakoConfigEntry
    from .device import EnOceanDevice
    from .protocol.telegram import RadioTelegram

CHECK_INTERVAL = timedelta(minutes=1)
GATEWAY_REPAIR_AFTER = 5 * 60  # seconds
MAX_SUGGESTIONS = 3
PROFILE_MISMATCH_AFTER = 5  # telegrams in a row that fit none of a device's profiles
SLOW_CONFIRMATION = 3.0  # E11: median seconds from command to the bus actor's answer
SLOW_MIN_SAMPLES = 5
UNSTABLE_WINDOW = 10 * 60  # seconds: this many connection losses within it ...
UNSTABLE_DROPS = 3  # ... make the connection unstable
PROBE_AFTER = 10  # seconds a connection must hold before the gateway is asked for its base ID
PROBE_TIMEOUT = 5.0
OLD_DOMAIN = "eltako"  # the old integration: its serial port is in YAML, not in its entry


def device_issue_id(unique_prefix: str) -> str:
    return f"device_silent_{unique_prefix}"


def profile_issue_id(unique_prefix: str) -> str:
    return f"device_profile_mismatch_{unique_prefix}"


def gateway_issue_id(entry_id: str) -> str:
    return f"gateway_disconnected_{entry_id}"


def slow_bus_issue_id(entry_id: str) -> str:
    return f"bus_slow_confirmations_{entry_id}"


def unstable_issue_id(entry_id: str) -> str:
    return f"connection_unstable_{entry_id}"


def silent_issue_id(entry_id: str) -> str:
    return f"gateway_silent_{entry_id}"


@callback
def port_users(hass: HomeAssistant, entry: EnOceanEltakoConfigEntry) -> list[str]:
    """Other loaded config entries that name the same port, and the old eltako integration."""
    path = entry.data.get(CONF_DEVICE, {}).get(CONF_PATH)
    return [
        f"{other.title} ({other.domain})"
        for other in hass.config_entries.async_entries()
        if other.entry_id != entry.entry_id
        and other.state is ConfigEntryState.LOADED
        and (other.domain == OLD_DOMAIN or (path is not None and path in str(other.data)))
    ]


def confirmation_median(entry: EnOceanEltakoConfigEntry) -> float | None:
    """Median confirmation time of the entry's actuators, None with too few samples."""
    samples = [s for d in entry.runtime_data.devices.values() for s in d.stats.latencies]
    return statistics.median(samples) if len(samples) >= SLOW_MIN_SAMPLES else None


@callback
def async_setup_health(hass: HomeAssistant, entry: EnOceanEltakoConfigEntry) -> Callable[[], None]:
    """Start the periodic check; returns it for an immediate run."""

    @callback
    def check(_now: Any = None) -> None:
        now = time.time()
        runtime = entry.runtime_data
        for device in runtime.devices.values():
            issue_id = device_issue_id(device.unique_prefix)
            if device.check_silence(now):
                hours = (now - (device.stats.last_seen or device.started)) / 3600
                gateway = hass.config_entries.async_get_entry(device.stats.gateway or "")
                ir.async_create_issue(
                    hass,
                    DOMAIN,
                    issue_id,
                    is_fixable=False,
                    severity=ir.IssueSeverity.WARNING,
                    translation_key="device_silent",
                    translation_placeholders={
                        "name": device.subentry.title,
                        "hours": f"{hours:.1f}",
                        "gateway": gateway.title if gateway else "-",
                    },
                )
            else:
                ir.async_delete_issue(hass, DOMAIN, issue_id)
            _check_profile(hass, device)
        issue_id = gateway_issue_id(entry.entry_id)
        since = runtime.disconnected_since
        if not runtime.on_demand and since is not None and now - since > GATEWAY_REPAIR_AFTER:
            ir.async_create_issue(
                hass,
                DOMAIN,
                issue_id,
                is_fixable=False,
                severity=ir.IssueSeverity.ERROR,
                translation_key="gateway_disconnected",
                translation_placeholders={
                    "name": entry.title,
                    "connection": str(runtime.gateway.connection),
                },
            )
        else:
            ir.async_delete_issue(hass, DOMAIN, issue_id)
        _check_unstable(hass, entry, now)
        _check_silent(hass, entry)
        if runtime.bus is not None:
            _check_bus_confirmations(hass, entry)

    entry.async_on_unload(async_track_time_interval(hass, check, CHECK_INTERVAL))

    def clear() -> None:
        ir.async_delete_issue(hass, DOMAIN, gateway_issue_id(entry.entry_id))
        ir.async_delete_issue(hass, DOMAIN, slow_bus_issue_id(entry.entry_id))
        ir.async_delete_issue(hass, DOMAIN, unstable_issue_id(entry.entry_id))
        ir.async_delete_issue(hass, DOMAIN, silent_issue_id(entry.entry_id))
        for device in entry.runtime_data.devices.values():
            ir.async_delete_issue(hass, DOMAIN, device_issue_id(device.unique_prefix))
            ir.async_delete_issue(hass, DOMAIN, profile_issue_id(device.unique_prefix))

    entry.async_on_unload(clear)
    return check


@callback
def _check_profile(hass: HomeAssistant, device: EnOceanDevice) -> None:
    """A device whose telegrams keep not fitting its profile was most likely set up wrongly."""
    issue_id = profile_issue_id(device.unique_prefix)
    telegram = device.last_telegram
    if (
        device.stats.mismatches < PROFILE_MISMATCH_AFTER
        or telegram is None
        or not device.model.receive
    ):
        ir.async_delete_issue(hass, DOMAIN, issue_id)
        return
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key="device_profile_range"
        if device.stats.mismatch_range
        else "device_profile_mismatch",
        translation_placeholders={
            "name": device.subentry.title,
            "profile": str(device.model.receive),
            "rorg": f"{telegram.rorg:02X}",
            "count": str(device.stats.mismatches),
            "suggestions": _suggestions(device, telegram),
        },
    )


def _suggestions(device: EnOceanDevice, telegram: RadioTelegram) -> str:
    """Devices whose telegrams look like this one, from the add-device suggestions."""
    from .protocol.eep.teach_in import decode_teach_in_4bs  # noqa: PLC0415
    from .subentry_flow import candidates  # noqa: PLC0415 - the flow imports a lot

    teach_in = decode_teach_in_4bs(telegram.data) if telegram.rorg == Rorg.BS4 else None
    names = []
    for kind in candidates(telegram.rorg, teach_in, telegram.data):
        model = CATALOG.get(kind)
        if model is None or model.id == device.model.id:
            continue
        names.append((model.example_list or (model.id,))[0])
    return ", ".join(dict.fromkeys(names[:MAX_SUGGESTIONS])) or "-"


def _check_silent(hass: HomeAssistant, entry: EnOceanEltakoConfigEntry) -> None:
    """A connected gateway that does not answer: many network gateways (MGW-ETH) serve only
    one client and accept further connections without ever answering them. Asks for the
    base ID once per connection, and again while the issue stands, so it clears itself."""
    runtime = entry.runtime_data
    gateway = runtime.gateway
    issue_id = silent_issue_id(entry.entry_id)
    if not MODELS[entry.data[CONF_MODEL]].reads_base_id or runtime.on_demand:
        return
    if not gateway.connected:
        ir.async_delete_issue(hass, DOMAIN, issue_id)  # the outage repair applies
        return
    if runtime.probing or time.monotonic() - gateway.connected_at < PROBE_AFTER:
        return
    stands = ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is not None
    if runtime.probed_connection == gateway.connected_at and not stands:
        return
    runtime.probing = True
    entry.async_create_background_task(
        hass, _probe(hass, entry, gateway.connected_at), f"{DOMAIN} gateway probe"
    )


async def _probe(hass: HomeAssistant, entry: EnOceanEltakoConfigEntry, connection: float) -> None:
    runtime = entry.runtime_data
    try:
        answer = await runtime.gateway.read_base_id(PROBE_TIMEOUT)
    except (ConnectionError, OSError):
        return  # dropped meanwhile: the connection checks take over
    finally:
        runtime.probing = False
    runtime.probed_connection = connection
    async_set_silent(hass, entry, answer is None)


@callback
def async_set_silent(hass: HomeAssistant, entry: EnOceanEltakoConfigEntry, silent: bool) -> None:
    """Raise or clear the "connected but does not answer" repair."""
    issue_id = silent_issue_id(entry.entry_id)
    if not silent:
        ir.async_delete_issue(hass, DOMAIN, issue_id)
        return
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=False,
        severity=ir.IssueSeverity.ERROR,
        translation_key="gateway_silent",
        translation_placeholders={
            "name": entry.title,
            "connection": str(entry.runtime_data.gateway.connection),
        },
    )


@callback
def _check_unstable(hass: HomeAssistant, entry: EnOceanEltakoConfigEntry, now: float) -> None:
    """A connection that keeps dropping, typically a port another program opens as well;
    the outage issue never comes since every reconnect succeeds for a while."""
    issue_id = unstable_issue_id(entry.entry_id)
    drops = [t for t in entry.runtime_data.drops if now - t < UNSTABLE_WINDOW]
    if len(drops) < UNSTABLE_DROPS:
        ir.async_delete_issue(hass, DOMAIN, issue_id)
        return
    users = port_users(hass, entry)
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=False,
        severity=ir.IssueSeverity.ERROR,
        translation_key="connection_unstable_users" if users else "connection_unstable",
        translation_placeholders={
            "name": entry.title,
            "connection": str(entry.runtime_data.gateway.connection),
            "drops": str(len(drops)),
            "minutes": str(UNSTABLE_WINDOW // 60),
            "users": ", ".join(users),
        },
    )


@callback
def _check_bus_confirmations(hass: HomeAssistant, entry: EnOceanEltakoConfigEntry) -> None:
    """E11: bus actors answering after more than 3 s (median) point to the FAM14's mode.

    Eltako: only in operating mode 5, with a device list made by PCT14, does the FAM14 pass
    the actuators' confirmations on right away.
    """
    median = confirmation_median(entry)
    if median is None:
        return
    issue_id = slow_bus_issue_id(entry.entry_id)
    if median <= SLOW_CONFIRMATION:
        ir.async_delete_issue(hass, DOMAIN, issue_id)
        return
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key="bus_slow_confirmations",
        translation_placeholders={"name": entry.title, "seconds": f"{median:.1f}"},
    )
