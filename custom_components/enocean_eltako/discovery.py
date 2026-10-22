"""Discovery: senders no device listens to are offered under "Add device" of the gateway.

The hub keeps the last telegram of each unknown sender; the device flow lists them as
"Discovered devices". One notification per gateway announces new ones. Our own sender IDs
(pools) are skipped; a gateway can switch discovery off in its options.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant, callback

from .const import CONF_DISCOVERY, DOMAIN
from .protocol.dispatcher import ReceivedTelegram

if TYPE_CHECKING:
    from . import EnOceanEltakoConfigEntry


_MESSAGES = {
    "en": 'Discovered devices: {count}. Add them under "Add device" of this gateway.',
    "de": "Entdeckte Geräte: {count}. Füge sie beim Gateway unter „Gerät hinzufügen“ hinzu.",
}


def pending(entry: EnOceanEltakoConfigEntry) -> list[ReceivedTelegram]:
    """Unknown senders this gateway heard that are not set up as devices (newest first)."""
    from .protocol.ids import format_id

    configured = {s.unique_id.split("_")[0] for s in entry.subentries.values() if s.unique_id}
    heard = [
        t
        for t in entry.runtime_data.hub.discovered.values()
        if t.gateway == entry.entry_id and format_id(t.sender) not in configured
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
            or hub.senders.in_pool(sender)
        ):
            return
        new = sender not in hub.discovered
        hub.discovered[sender] = received
        if new:
            persistent_notification.async_create(
                hass,
                _MESSAGES.get(hass.config.language, _MESSAGES["en"]).format(
                    count=len(pending(entry))
                ),
                title=entry.title,
                notification_id=f"{DOMAIN}_discovered_{entry.entry_id}",
            )

    return hub.dispatcher.add_unknown_listener(heard)
