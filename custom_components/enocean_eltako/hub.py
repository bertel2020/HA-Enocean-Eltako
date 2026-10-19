"""Shared state of all gateway entries: the central dispatcher."""

from __future__ import annotations

from dataclasses import dataclass, field

from homeassistant.core import HomeAssistant
from homeassistant.util.hass_dict import HassKey

from .const import DOMAIN
from .protocol.dispatcher import Dispatcher


@dataclass
class Hub:
    """One per Home Assistant instance; every gateway entry feeds its dispatcher."""

    dispatcher: Dispatcher = field(default_factory=Dispatcher)


DATA_HUB: HassKey[Hub] = HassKey(DOMAIN)


def async_get_hub(hass: HomeAssistant) -> Hub:
    if (hub := hass.data.get(DATA_HUB)) is None:
        hub = hass.data[DATA_HUB] = Hub()
    return hub
