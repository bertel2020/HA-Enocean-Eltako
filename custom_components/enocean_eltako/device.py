"""Runtime object of one device subentry: decodes its telegrams and sends its commands."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo

from .catalog import CATALOG, ROCKER_STATUS_PRESSED, ROCKER_STATUS_RELEASED, DeviceModel
from .const import CONF_DEVICE_ID, CONF_MODEL, CONF_PROFILE, CONF_SENDER_ID, CONF_SENDERS, DOMAIN
from .protocol.dispatcher import ReceivedTelegram
from .protocol.eep.codecs import decode_telegram
from .protocol.ids import format_id, parse_id
from .protocol.send_queue import Priority, SendResult
from .protocol.telegram import RadioTelegram, Rorg

if TYPE_CHECKING:
    from . import EnOceanEltakoConfigEntry

_LOGGER = logging.getLogger(__name__)

Listener = Callable[[dict[str, Any]], None]


class EnOceanDevice:
    def __init__(
        self, hass: HomeAssistant, entry: EnOceanEltakoConfigEntry, subentry: ConfigSubentry
    ) -> None:
        self.hass = hass
        self.entry = entry
        self.subentry = subentry
        self.model: DeviceModel = CATALOG[subentry.data[CONF_MODEL]]
        self.device_id = parse_id(subentry.data[CONF_DEVICE_ID])
        # profile -> sender ID, in catalog order (first configured = preferred)
        configured = {
            s[CONF_PROFILE]: parse_id(s[CONF_SENDER_ID])
            for s in subentry.data.get(CONF_SENDERS, ())
        }
        self.senders: dict[str, int] = {
            p.id: configured[p.id] for p in self.model.senders if p.id in configured
        }
        self.options: dict[str, Any] = dict(subentry.data)
        self.last_received: ReceivedTelegram | None = None
        self._listeners: list[Listener] = []

    @property
    def unique_prefix(self) -> str:
        return f"{self.entry.unique_id}_{format_id(self.device_id)}"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.unique_prefix)},
            name=self.subentry.title,
            manufacturer="Eltako",
            model=self.model.examples.split(",")[0] if self.model.examples else self.model.id,
            model_id=str(self.model.receive) if self.model.receive else None,
            serial_number=format_id(self.device_id),
            via_device=(DOMAIN, self.entry.entry_id),
        )

    def start(self) -> Callable[[], None]:
        dispatcher = self.entry.runtime_data.hub.dispatcher
        return dispatcher.add_listener(self.device_id, self._on_received)

    def add_listener(self, listener: Listener) -> Callable[[], None]:
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    @callback
    def _on_received(self, received: ReceivedTelegram) -> None:
        values = None
        for ref in (self.model.receive, *self.model.receive_extra):
            if ref is not None and (values := decode_telegram(ref, received.telegram)) is not None:
                break
        if values is None:
            return
        self.last_received = received
        for listener in list(self._listeners):
            listener(values)

    def has_sender(self, profile: str) -> bool:
        return profile in self.senders

    @callback
    def send(
        self,
        data: bytes,
        *,
        profile: str | None = None,
        priority: Priority = Priority.USER,
        key: str | None = None,
        confirm: bool = True,
        status: int = 0,
    ) -> None:
        """Queue a telegram from the sender ID of a profile without waiting for the actuator.

        profile None = the first configured sender. The queue waits for the actuator's status
        telegram in the background and repeats the command if it does not come; raises
        HomeAssistantError when the gateway is offline.
        """
        if not self.senders:
            raise RuntimeError(f"{self.subentry.title} has no sender")
        profile = profile or next(iter(self.senders))
        sender_id = self.senders[profile]
        rorg = self.model.sender_profile(profile).rorg
        telegram = RadioTelegram(rorg, data, sender_id, status)
        expect = (lambda t: t.sender == self.device_id) if confirm else None
        runtime = self.entry.runtime_data
        queue_key = (self.unique_prefix, key) if key else None
        if runtime.bus is not None and sender_id in runtime.bus.senders.pool:
            task = self.entry.async_create_task(
                self.hass,
                runtime.bus.group.submit(telegram, priority, key=queue_key, expect=expect),
                f"{DOMAIN} send {self.subentry.title}",
            )
            task.add_done_callback(lambda t: self._log_result(t.result()))
            return
        if not runtime.gateway.connected:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="gateway_not_connected",
                translation_placeholders={"gateway": self.entry.title},
            )
        future = runtime.queue.submit(telegram, priority, key=queue_key, expect=expect)
        future.add_done_callback(lambda f: self._log_result(f.result()))

    @callback
    def press(self, profile: str, button: bytes, *, confirm: bool = True) -> None:
        """Rocker profile: press and release, like a PTM switch."""
        self.send(button, profile=profile, status=ROCKER_STATUS_PRESSED, confirm=confirm)
        self.send(bytes(1), profile=profile, status=ROCKER_STATUS_RELEASED, confirm=False)

    def _log_result(self, result: SendResult) -> None:
        if result in (SendResult.UNCONFIRMED, SendResult.FAILED):
            _LOGGER.warning("%s: command %s", self.subentry.title, result)

    @callback
    def teach_in(self, profile: str) -> None:
        sender = self.model.sender_profile(profile)
        if sender.rorg == Rorg.RPS:
            self.press(profile, sender.teach_in, confirm=False)
        else:
            self.send(sender.teach_in, profile=profile, priority=Priority.BACKGROUND, confirm=False)
