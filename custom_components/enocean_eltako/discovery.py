"""Discovery: senders no device listens to are offered under "Add device" of the gateway.

The hub keeps the last telegram of each unknown sender (the newest MAX_DISCOVERED); the
device flow lists them as "Discovered devices". One card per gateway in
Home Assistant's "Discovered" area announces them (a config flow of its own, replaced
whenever the count changes) and is refreshed whenever the gateway loads. Senders that are
not the user's can be hidden per gateway (stored, shown again from the gateway's options).
Our own sender IDs (pools) are skipped; a gateway can switch discovery off in its options.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import SOURCE_INTEGRATION_DISCOVERY
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import discovery_flow
from homeassistant.helpers.event import async_call_later, async_track_time_interval
from homeassistant.helpers.selector import SelectOptionDict
from homeassistant.helpers.storage import Store

from .const import CONF_DISCOVERY, CONF_FORGET_DAYS, DEFAULT_FORGET_DAYS, DOMAIN
from .protocol.dispatcher import ReceivedTelegram
from .protocol.eep.teach_in import decode_teach_in_4bs
from .protocol.ids import format_id, parse_id
from .protocol.telegram import RadioTelegram, Rorg

if TYPE_CHECKING:
    from . import EnOceanEltakoConfigEntry


MAX_DISCOVERED = 100
FORGET_CHECK = timedelta(hours=6)  # how often unknown senders gone quiet for too long are dropped
STORAGE_VERSION = 1


def _store(hass: HomeAssistant, entry_id: str) -> Store[dict[str, list[str]]]:
    return Store(hass, STORAGE_VERSION, f"{DOMAIN}.hidden.{entry_id}")


async def async_load_hidden(hass: HomeAssistant, entry: EnOceanEltakoConfigEntry) -> None:
    """Read the hidden senders of this gateway into the hub."""
    stored = await _store(hass, entry.entry_id).async_load() or {}
    entry.runtime_data.hub.hidden[entry.entry_id] = {parse_id(s) for s in stored.get("ids", [])}


async def async_set_hidden(
    hass: HomeAssistant,
    entry: EnOceanEltakoConfigEntry,
    senders: set[int],
    refresh: bool = True,
) -> None:
    """Replace the hidden senders of this gateway and refresh the notification."""
    hub = entry.runtime_data.hub
    hub.hidden[entry.entry_id] = senders
    for sender in senders:
        hub.discovered.pop(sender, None)
    await _store(hass, entry.entry_id).async_save({"ids": sorted(format_id(s) for s in senders)})
    if refresh:
        async_update_notification(hass, entry)


async def async_remove_hidden(hass: HomeAssistant, entry_id: str) -> None:
    await _store(hass, entry_id).async_remove()


CARD_DELAY = 5  # seconds: a burst of new senders makes one card, not one each

_TITLES = {
    "en": "{name}: {count} discovered devices",
    "de": "{name}: {count} entdeckte Geräte",
}


_KINDS = {
    "en": {0xF6: "rockers", 0xD5: "contacts", 0xA5: "sensors", 0xD2: "VLD devices"},
    "de": {0xF6: "Taster", 0xD5: "Kontakte", 0xA5: "Sensoren", 0xD2: "VLD-Geräte"},
}


def kind_name(hass: HomeAssistant, rorg: int) -> str:
    """The telegram type in words: "sensors", "Taster" (language of the instance)."""
    return _KINDS.get(hass.config.language, _KINDS["en"]).get(rorg, "RORG")


def sender_options(
    hass: HomeAssistant, entry: EnOceanEltakoConfigEntry
) -> tuple[dict[str, ReceivedTelegram], list[SelectOptionDict]]:
    """The pending senders, strongest signal first (devices close by are usually the user's)."""
    ordered = sorted(
        pending(entry),
        key=lambda t: t.telegram.dbm if t.telegram.dbm is not None else -999,
        reverse=True,
    )
    heard = {format_id(t.sender): t for t in ordered}
    options = []
    for sender_id, t in heard.items():
        data = t.telegram.data
        teach_in = decode_teach_in_4bs(data) if t.telegram.rorg == Rorg.BS4 else None
        dbm = f"{t.telegram.dbm} dBm" if t.telegram.dbm is not None else "- dBm"
        kind = f"{kind_name(hass, t.telegram.rorg)} ({t.telegram.rorg:02X})"
        label = f"{sender_id} · {teach_in.eep if teach_in else kind} · {dbm}"
        options.append(SelectOptionDict(value=sender_id, label=label))
    return heard, options


def card_unique_id(entry: EnOceanEltakoConfigEntry) -> str:
    return f"discovered_{entry.entry_id}"


def card_title(hass: HomeAssistant, entry: EnOceanEltakoConfigEntry, count: int) -> str:
    return _TITLES.get(hass.config.language, _TITLES["en"]).format(name=entry.title, count=count)


@callback
def async_update_notification(hass: HomeAssistant, entry: EnOceanEltakoConfigEntry) -> None:
    """Refresh the gateway's discovery card shortly (bursts of senders are taken together)."""
    hub = entry.runtime_data.hub
    if (cancel := hub.card_timer.pop(entry.entry_id, None)) is not None:
        cancel()

    @callback
    def refresh(_now: object) -> None:
        hub.card_timer.pop(entry.entry_id, None)
        async_refresh_card(hass, entry)

    hub.card_timer[entry.entry_id] = async_call_later(hass, CARD_DELAY, refresh)


@callback
def async_refresh_card(hass: HomeAssistant, entry: EnOceanEltakoConfigEntry) -> None:
    """One card in "Discovered" with the number of senders; none when there are none."""
    count = len(pending(entry))
    unique_id = card_unique_id(entry)
    flows = [
        flow
        for flow in hass.config_entries.flow.async_progress_by_handler(DOMAIN)
        if flow["context"].get("unique_id") == unique_id
    ]
    title = card_title(hass, entry, count)
    if count and any(
        f["context"].get("title_placeholders", {}).get("name") == title for f in flows
    ):
        return  # the card says the right number already
    for flow in flows:
        hass.config_entries.flow.async_abort(flow["flow_id"])
    if count:
        discovery_flow.async_create_flow(
            hass,
            DOMAIN,
            {"source": SOURCE_INTEGRATION_DISCOVERY},
            {"entry_id": entry.entry_id},
        )


@callback
def async_remove_card(hass: HomeAssistant, entry: EnOceanEltakoConfigEntry) -> None:
    """The gateway unloads: its card and a pending refresh go."""
    hub = entry.runtime_data.hub
    if (cancel := hub.card_timer.pop(entry.entry_id, None)) is not None:
        cancel()
    for flow in hass.config_entries.flow.async_progress_by_handler(DOMAIN):
        if flow["context"].get("unique_id") == card_unique_id(entry):
            hass.config_entries.flow.async_abort(flow["flow_id"])


def _configured(entry: EnOceanEltakoConfigEntry) -> set[str]:
    return {s.unique_id.split("_")[0] for s in entry.subentries.values() if s.unique_id}


@callback
def async_forget_unknown(
    hass: HomeAssistant, entry: EnOceanEltakoConfigEntry, days: float | None
) -> int:
    """Drop the unknown senders not heard for `days` (None: all of them); returns how many.

    They are kept across restarts (the notes store); this is the only thing that removes them,
    apart from the hub's cap. A sender that is heard again is simply listed again.
    """
    hub = entry.runtime_data.hub
    notes = hub.notes.get(entry.entry_id)
    cutoff = None if days is None else time.time() - days * 86400
    configured = _configured(entry)
    gone: set[str] = set()
    if notes is not None:
        gone = {
            sender
            for sender, values in notes.heard.items()
            if cutoff is None or values["last"] < cutoff
        }
        notes.forget_heard(gone, configured)
    for sender, t in list(hub.discovered.items()):
        if t.gateway == entry.entry_id and (cutoff is None or t.timestamp < cutoff):
            del hub.discovered[sender]
            gone.add(format_id(sender))
    if gone:
        async_update_notification(hass, entry)
    return len(gone)


def stored_unknown(entry: EnOceanEltakoConfigEntry) -> list[dict[str, Any]]:
    """The unknown senders heard (also before a restart), for the panel's device list."""
    hub = entry.runtime_data.hub
    notes = hub.notes.get(entry.entry_id)
    if notes is None:
        return []
    configured = _configured(entry)
    hidden = {format_id(s) for s in hub.hidden.get(entry.entry_id, ())}
    rows = []
    for sender, values in notes.heard.items():
        if sender in configured or sender in hidden or hub.senders.in_pool(parse_id(sender)):
            continue
        last = notes.last.get(sender, {})
        rows.append(
            {
                "id": sender,
                "rorg": values["rorg"],
                "dbm": values["dbm"],
                "last": values["last"],
                "data": last.get("data", ""),
            }
        )
    return sorted(rows, key=lambda r: r["last"], reverse=True)


def pending(entry: EnOceanEltakoConfigEntry) -> list[ReceivedTelegram]:
    """Unknown senders this gateway heard that are not set up as devices (newest first)."""
    hub = entry.runtime_data.hub
    configured = {s.unique_id.split("_")[0] for s in entry.subentries.values() if s.unique_id}
    hidden = hub.hidden.get(entry.entry_id, set())
    heard = [
        t
        for t in hub.discovered.values()
        if t.gateway == entry.entry_id
        and t.sender not in hidden
        and format_id(t.sender) not in configured
    ]
    return sorted(heard, key=lambda t: t.timestamp, reverse=True)


@callback
def async_setup_discovery(
    hass: HomeAssistant, entry: EnOceanEltakoConfigEntry
) -> Callable[[], None]:
    """Remember each unknown sender this gateway hears; tell when a new one shows up."""
    hub = entry.runtime_data.hub

    @callback
    def heard(received: ReceivedTelegram) -> None:
        sender = received.sender
        if (
            received.gateway != entry.entry_id
            or not entry.options.get(CONF_DISCOVERY, True)
            or sender in hub.hidden.get(entry.entry_id, ())
            or hub.senders.in_pool(sender)
        ):
            return
        new = sender not in hub.discovered
        hub.discovered[sender] = received
        if (notes := hub.notes.get(entry.entry_id)) is not None:
            notes.remember_last(
                format_id(sender),
                received.gateway,
                received.telegram.rorg,
                received.telegram.data,
                received.telegram.status,
                received.telegram.dbm,
                received.timestamp,
            )
            notes.remember_heard(
                format_id(sender),
                f"{received.telegram.rorg:02X}",
                received.telegram.dbm,
                received.timestamp,
            )
        if len(hub.discovered) > MAX_DISCOVERED:  # the oldest one goes
            hub.discovered.pop(min(hub.discovered, key=lambda s: hub.discovered[s].timestamp))
        if new:
            async_update_notification(hass, entry)

    notes = hub.notes.get(entry.entry_id)
    if notes is not None and entry.options.get(CONF_DISCOVERY, True):
        configured = _configured(entry)
        hidden = hub.hidden.get(entry.entry_id, set())
        for sender_text, saved in notes.last.items():  # senders heard before the restart
            if sender_text not in notes.heard or sender_text in configured:
                continue
            sender = parse_id(sender_text)
            if sender in hub.discovered or sender in hidden or hub.senders.in_pool(sender):
                continue
            hub.discovered[sender] = ReceivedTelegram(
                RadioTelegram(
                    int(saved["rorg"], 16),
                    bytes.fromhex(saved["data"]),
                    sender,
                    saved["status"],
                    dbm=saved["dbm"],
                ),
                entry.entry_id,
                saved["time"],
                sender,
            )

    @callback
    def forget(_now: object = None) -> None:
        if days := entry.options.get(CONF_FORGET_DAYS, DEFAULT_FORGET_DAYS):
            async_forget_unknown(hass, entry, days)

    forget()
    async_update_notification(hass, entry)  # after a reload: the count is current again
    remove = hub.dispatcher.add_unknown_listener(heard)
    remove_timer = async_track_time_interval(hass, forget, FORGET_CHECK)

    @callback
    def stop() -> None:
        remove()
        remove_timer()
        async_remove_card(hass, entry)

    return stop
