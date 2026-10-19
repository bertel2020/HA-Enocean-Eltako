"""Runtime object of one device subentry: decodes its telegrams and sends its commands."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo

from .catalog import CATALOG, DeviceModel
from .const import CONF_DEVICE_ID, CONF_MODEL, CONF_SENDER_ID, DOMAIN
from .protocol.dispatcher import ReceivedTelegram
from .protocol.eep.codecs import decode_telegram
from .protocol.ids import format_id, parse_id
from .protocol.send_queue import Priority, SendResult
from .protocol.telegram import RadioTelegram

if TYPE_CHECKING:
    from . import EnOceanEltakoConfigEntry

_LOGGER = logging.getLogger(__name__)

Listener = Callable[[dict[str, Any]], None]


class EnOceanDevice:
    def __init__(self, entry: EnOceanEltakoConfigEntry, subentry: ConfigSubentry) -> None:
        self.entry = entry
        self.subentry = subentry
        self.model: DeviceModel = CATALOG[subentry.data[CONF_MODEL]]
        self.device_id = parse_id(subentry.data[CONF_DEVICE_ID])
        sender = subentry.data.get(CONF_SENDER_ID)
        self.sender_id = parse_id(sender) if sender else None
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
        if self.model.receive is None:
            return
        values = decode_telegram(self.model.receive, received.telegram)
        if values is None:
            return
        self.last_received = received
        for listener in list(self._listeners):
            listener(values)

    @callback
    def send(
        self,
        data: bytes,
        *,
        priority: Priority = Priority.USER,
        key: str | None = None,
        confirm: bool = True,
        status: int = 0,
    ) -> None:
        """Queue a telegram from this device's sender ID without waiting for the actuator.

        The queue waits for the status telegram in the background and repeats the command
        if it does not come; raises HomeAssistantError when the gateway is offline.
        """
        if self.sender_id is None or self.model.send_rorg is None:
            raise RuntimeError(f"{self.subentry.title} has no sender")
        telegram = RadioTelegram(self.model.send_rorg, data, self.sender_id, status)
        expect = (lambda t: t.sender == self.device_id) if confirm else None
        runtime = self.entry.runtime_data
        queue_key = (self.unique_prefix, key) if key else None
        if runtime.bus is not None and self.sender_id in runtime.bus.senders.pool:
            task = self.entry.async_create_task(
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

    def _log_result(self, result: SendResult) -> None:
        if result in (SendResult.UNCONFIRMED, SendResult.FAILED):
            _LOGGER.warning("%s: command %s", self.subentry.title, result)

    @callback
    def teach_in(self) -> None:
        assert self.model.teach_in is not None
        self.send(self.model.teach_in, priority=Priority.BACKGROUND, confirm=False)
