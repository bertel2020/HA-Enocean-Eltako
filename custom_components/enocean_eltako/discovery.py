"""Discovery: a sender no device listens to shows up as a discovered device card.

Each unknown sender starts one integration_discovery flow (unique ID "device_<ID>"), so the
card names the ID and the receiving gateway and offers the kinds that fit. HA's "Ignore"
stores the ID as an ignored entry, so it never shows again. Our own sender IDs (pools) are
skipped; a gateway can switch discovery off in its options.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import SOURCE_INTEGRATION_DISCOVERY
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import discovery_flow

from .const import CONF_DISCOVERY, DOMAIN
from .protocol.dispatcher import ReceivedTelegram
from .protocol.ids import format_id

if TYPE_CHECKING:
    from . import EnOceanEltakoConfigEntry

DISCOVERY_PREFIX = "device_"


def discovery_unique_id(device_id: int) -> str:
    return f"{DISCOVERY_PREFIX}{format_id(device_id)}"


@callback
def async_setup_discovery(
    hass: HomeAssistant, entry: EnOceanEltakoConfigEntry
) -> Callable[[], None]:
    """Start a discovery flow for each unknown sender this gateway hears (once per run)."""
    hub = entry.runtime_data.hub

    @callback
    def heard(received: ReceivedTelegram) -> None:
        sender = received.sender
        if (
            received.gateway != entry.entry_id
            or not entry.options.get(CONF_DISCOVERY, True)
            or sender in hub.discovered
            or hub.senders.in_pool(sender)
        ):
            return
        hub.discovered.add(sender)
        telegram = received.telegram
        data: dict[str, Any] = {
            "gateway": entry.entry_id,
            "device_id": format_id(sender),
            "rorg": telegram.rorg,
            "data": telegram.data.hex(),
            "dbm": telegram.dbm,
        }
        discovery_flow.async_create_flow(
            hass, DOMAIN, {"source": SOURCE_INTEGRATION_DISCOVERY}, data
        )

    return hub.dispatcher.add_unknown_listener(heard)


@callback
def async_abort_configured(hass: HomeAssistant, entry: EnOceanEltakoConfigEntry) -> None:
    """Drop discovery cards of senders that were added as devices in the meantime."""
    configured = {f"{DISCOVERY_PREFIX}{s.unique_id}" for s in entry.subentries.values()}
    for flow in hass.config_entries.flow.async_progress_by_handler(
        DOMAIN, include_uninitialized=True
    ):
        if flow["context"].get("unique_id") in configured:
            hass.config_entries.flow.async_abort(flow["flow_id"])
