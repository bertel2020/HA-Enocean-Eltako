"""Discovery: senders no device listens to are offered under "Add device" of the gateway.

The hub keeps the last telegram of each unknown sender (the newest MAX_DISCOVERED); the
device flow lists them as "Discovered devices". One notification per gateway announces new
ones and is refreshed whenever the gateway loads. Senders that are not the user's can be
hidden per gateway (stored, shown again from the gateway's options). Our own sender IDs
(pools) are skipped; a gateway can switch discovery off in its options.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant, callback
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


@callback
def async_update_notification(hass: HomeAssistant, entry: EnOceanEltakoConfigEntry) -> None:
    """Name the number of discovered senders; no notification when there are none."""
    notification_id = f"{DOMAIN}_discovered_{entry.entry_id}"
    if count := len(pending(entry)):
        persistent_notification.async_create(
            hass,
            _MESSAGES.get(hass.config.language, _MESSAGES["en"]).format(count=count),
            title=entry.title,
            notification_id=notification_id,
        )
    else:
        persistent_notification.async_dismiss(hass, notification_id)


_MESSAGES = {
    "en": 'Discovered devices: {count}. Add them under "Add device" of this gateway.',
    "de": "Entdeckte Geräte: {count}. Füge sie beim Gateway unter „Gerät hinzufügen“ hinzu.",
}


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
    return hub.dispatcher.add_unknown_listener(heard)
