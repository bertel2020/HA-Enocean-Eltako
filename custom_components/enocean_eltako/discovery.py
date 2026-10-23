"""Discovery: senders no device listens to are offered under "Add device" of the gateway.

The hub keeps the last telegram of each unknown sender (the newest MAX_DISCOVERED); the
device flow lists them as "Discovered devices". One card per gateway in
Home Assistant's "Discovered" area announces them (a config flow of its own, replaced
whenever the count changes) and is refreshed whenever the gateway loads. Senders that are
not the user's can be hidden per gateway (stored, shown again from the gateway's options).
Our own sender IDs (pools) are skipped; a gateway can switch discovery off in its options.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from homeassistant.config_entries import SOURCE_INTEGRATION_DISCOVERY
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import discovery_flow
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.storage import Store

from .const import CONF_DISCOVERY, DOMAIN
from .protocol.dispatcher import ReceivedTelegram
from .protocol.ids import format_id, parse_id

if TYPE_CHECKING:
    from . import EnOceanEltakoConfigEntry


MAX_DISCOVERED = 100
STORAGE_VERSION = 1


def _store(hass: HomeAssistant, entry_id: str) -> Store[dict[str, list[str]]]:
    return Store(hass, STORAGE_VERSION, f"{DOMAIN}.hidden.{entry_id}")


async def async_load_hidden(hass: HomeAssistant, entry: EnOceanEltakoConfigEntry) -> None:
    """Read the hidden senders of this gateway into the hub."""
    stored = await _store(hass, entry.entry_id).async_load() or {}
    entry.runtime_data.hub.hidden[entry.entry_id] = {parse_id(s) for s in stored.get("ids", [])}


async def async_set_hidden(
    hass: HomeAssistant, entry: EnOceanEltakoConfigEntry, senders: set[int]
) -> None:
    """Replace the hidden senders of this gateway and refresh the notification."""
    hub = entry.runtime_data.hub
    hub.hidden[entry.entry_id] = senders
    for sender in senders:
        hub.discovered.pop(sender, None)
    await _store(hass, entry.entry_id).async_save({"ids": sorted(format_id(s) for s in senders)})
    async_update_notification(hass, entry)


async def async_remove_hidden(hass: HomeAssistant, entry_id: str) -> None:
    await _store(hass, entry_id).async_remove()


CARD_DELAY = 5  # seconds: a burst of new senders makes one card, not one each

_TITLES = {
    "en": "{name}: {count} discovered devices",
    "de": "{name}: {count} entdeckte Geräte",
}


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
        if len(hub.discovered) > MAX_DISCOVERED:  # the oldest one goes
            hub.discovered.pop(min(hub.discovered, key=lambda s: hub.discovered[s].timestamp))
        if new:
            async_update_notification(hass, entry)

    async_update_notification(hass, entry)  # after a reload: the count is current again
    remove = hub.dispatcher.add_unknown_listener(heard)

    @callback
    def stop() -> None:
        remove()
        async_remove_card(hass, entry)

    return stop
