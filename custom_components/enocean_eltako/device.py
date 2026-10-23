"""Runtime object of one device subentry: decodes its telegrams and sends its commands."""

from __future__ import annotations

import logging
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo

from .catalog import (
    DIRECTION_ROCKER,
    GROUP_VIRTUAL,
    OPT_ROCKER_OFF,
    OPT_ROCKER_ON,
    OPT_STATUS_CHANNEL,
    OPT_WALL_OFF,
    OPT_WALL_ON,
    OPT_WALL_SWITCH,
    ROCKER,
    ROCKER_CODES,
    ROCKER_STATUS_PRESSED,
    ROCKER_STATUS_RELEASED,
    DeviceModel,
    model_for,
)
from .const import (
    CONF_DEVICE_ID,
    CONF_MODEL_NAME,
    CONF_PROFILE,
    CONF_SENDER_ID,
    CONF_SENDERS,
    DOMAIN,
)
from .protocol.dispatcher import ReceivedTelegram
from .protocol.eep import EEPRef
from .protocol.eep.codecs import decode_telegram
from .protocol.eep.eltako import switching
from .protocol.eep.ute import decode_ute_request, encode_ute_response
from .protocol.ids import BROADCAST, format_id, parse_id
from .protocol.send_queue import Priority, SendResult
from .protocol.telegram import RadioTelegram, Rorg

if TYPE_CHECKING:
    from . import EnOceanEltakoConfigEntry

_LOGGER = logging.getLogger(__name__)

Listener = Callable[[dict[str, Any]], None]
LATENCY_SAMPLES = 10  # E11: confirmation times kept per device
UTE_WINDOW = 60.0  # seconds a teach-in button waits for the actuator's UTE query


WALL_SWITCH_EEP = EEPRef("F6-02-01", "std")
ROCKER_BUTTONS = ("a1", "a0", "b1", "b0")  # F6-02-01 R1 values 0...3


def wall_switch_state(
    r1: int, on_button: str, off_button: str, current: bool | None
) -> bool | None:
    """On/off a wall switch press stands for; one button for both toggles."""
    button = ROCKER_BUTTONS[r1] if 0 <= r1 < len(ROCKER_BUTTONS) else None
    if button is None:
        return None
    if on_button == off_button:
        return not current if button == on_button else None
    if button == on_button:
        return True
    if button == off_button:
        return False
    return None


@dataclass
class RadioStats:
    """E5/I7: when and how well the device was heard, and how its commands fared."""

    last_seen: float | None = None  # time.time()
    gateway: str | None = None  # entry ID of the gateway that heard it last
    rssi: int | None = None  # dBm (ESP3 gateways only)
    rssi_min: int | None = None
    rssi_max: int | None = None
    repeat_count: int | None = None  # status bits 0...3
    telegrams: int = 0
    commands: int = 0
    confirmed: int = 0
    # E11: seconds from command to the actuator's answer (queue wait and retries included)
    latencies: deque[float] = field(default_factory=lambda: deque(maxlen=LATENCY_SAMPLES))

    @property
    def success_rate(self) -> float | None:
        return round(100 * self.confirmed / self.commands, 1) if self.commands else None


class EnOceanDevice:
    def __init__(
        self, hass: HomeAssistant, entry: EnOceanEltakoConfigEntry, subentry: ConfigSubentry
    ) -> None:
        self.hass = hass
        self.entry = entry
        self.subentry = subentry
        self.model: DeviceModel = model_for(subentry.data)
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
        self.last_received: ReceivedTelegram | None = None  # last one decoded
        self.last_telegram: RadioTelegram | None = None  # last one heard
        self.stats = RadioStats()
        self.started = time.time()
        self.silent = False  # E5: no telegram for 3x the expected interval
        self._listeners: list[Listener] = []
        self._replay_listeners: list[Callable[[], None]] = []
        self.replaying = False  # a Device Proxy replay is being fed in
        self._stat_listeners: list[Callable[[], None]] = []
        self.cover_entity: Any = None  # set by the cover entity (calibrate button, accuracy)
        self.virtual: Any = None  # I9: VirtualSensor of a virtual sensor device
        self._ute_profile: str | None = None  # VLD: profile whose teach-in is armed ...
        self._ute_until = 0.0  # ... until this time.monotonic()
        self.wall_state: bool | None = None  # I4: last known on/off, for a toggling button

    @property
    def channel(self) -> int:
        """1, or 2 for the second channel of a two-channel actuator sharing the ID."""
        return 2 if str(self.options.get(OPT_STATUS_CHANNEL, "1")) == "2" else 1

    @property
    def unique_prefix(self) -> str:
        """Device identity: entry and ID, plus the channel beyond the first."""
        prefix = f"{self.entry.unique_id}_{format_id(self.device_id)}"
        return prefix if self.channel == 1 else f"{prefix}_{self.channel}"

    @property
    def entity_prefix(self) -> str:
        return f"{self.entry.unique_id}_{format_id(self.device_id)}_{self.channel}"

    def own_channel(self, telegram: RadioTelegram) -> bool:
        """False for a status telegram of the other channel of a shared actuator ID."""
        if OPT_STATUS_CHANNEL not in self.model.options:
            return True  # e.g. heating actuators report modes with the same codes
        if telegram.rorg != Rorg.RPS or not telegram.data:
            return True
        return switching.STATUS_CODES.get(telegram.data[0], (self.channel,))[0] == self.channel

    @property
    def _model_name(self) -> str:
        return self.model.receive.eep if self.model.receive else self.model.id

    @property
    def _model_label(self) -> str:
        if self.model.group == GROUP_VIRTUAL:  # it sends as a profile, it is no Eltako model
            return f"{self.model.senders[0].eep}"
        if chosen := str(self.options.get(CONF_MODEL_NAME) or "").strip():
            return chosen
        examples = self.model.example_list
        if not examples:
            return self._model_name
        # one example is the type; with several the EEP does not tell which one it is
        return examples[0] if len(examples) == 1 else ""

    @property
    def _registry_model(self) -> str:
        """Model as the device page lists it: the type; the EEP (with variant) is the model ID
        the page shows next to it, so it only stands here when there is no type."""
        label = self._model_label
        if self.model.receive is None or label:
            return label
        return self.model.receive.eep

    @property
    def device_info(self) -> DeviceInfo:
        info = DeviceInfo(
            identifiers={(DOMAIN, self.unique_prefix)},
            name=self.subentry.title,
            manufacturer=self.model.manufacturer,
            model=self._registry_model,
            # the EEP stands once: as the model when there is no type, else as the model ID
            model_id=str(self.model.receive) if self.model.receive and self._model_label else None,
            serial_number=format_id(self.device_id),
        )
        if (gateway := self.entry.runtime_data.gateway_device_id) is not None:
            info["via_device_id"] = gateway
        return info

    def start(self) -> Callable[[], None]:
        dispatcher = self.entry.runtime_data.hub.dispatcher
        remove = dispatcher.add_listener(self.device_id, self._on_received)
        if not (wall_switch := self.options.get(OPT_WALL_SWITCH)):
            return remove
        remove_wall = dispatcher.add_listener(parse_id(wall_switch), self._on_wall_switch)

        def remove_both() -> None:
            remove()
            remove_wall()

        return remove_both

    @callback
    def _on_wall_switch(self, received: ReceivedTelegram) -> None:
        """I4: a press on the wall switch teached into the actuator sets the assumed state."""
        values = decode_telegram(WALL_SWITCH_EEP, received.telegram)
        if values is None or values.get("EB") != 1 or "R1" not in values:
            return
        on = wall_switch_state(
            values["R1"],
            self.options.get(OPT_WALL_ON, "a0"),
            self.options.get(OPT_WALL_OFF, "a1"),
            self.wall_state,
        )
        if on is None:
            return
        self.wall_state = on
        for listener in list(self._listeners):
            listener({"on": on, "assumed": True})

    def add_listener(self, listener: Listener) -> Callable[[], None]:
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    def add_replay_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Called once a replay has been fed in (entities that wait for its end)."""
        self._replay_listeners.append(listener)
        return lambda: self._replay_listeners.remove(listener)

    def end_replay(self) -> None:
        self.replaying = False
        for listener in list(self._replay_listeners):
            listener()

    def add_stats_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        self._stat_listeners.append(listener)
        return lambda: self._stat_listeners.remove(listener)

    @property
    def silence_limit(self) -> float | None:
        """Seconds after which the device counts as silent (3x its interval)."""
        return 3 * self.model.interval if self.model.interval else None

    def check_silence(self, now: float) -> bool:
        """Update and return the silent flag."""
        limit = self.silence_limit
        reference = self.stats.last_seen or self.started
        silent = limit is not None and now - reference > limit
        if silent != self.silent:
            self.silent = silent
            self._notify_stats()
        return silent

    def _notify_stats(self) -> None:
        for listener in list(self._stat_listeners):
            listener()

    def _record(self, received: ReceivedTelegram) -> None:
        stats, telegram = self.stats, received.telegram
        stats.last_seen = received.timestamp
        self.last_telegram = telegram
        stats.gateway = received.gateway
        stats.telegrams += 1
        stats.repeat_count = telegram.status & 0x0F
        if telegram.dbm is not None:
            stats.rssi = telegram.dbm
            stats.rssi_min = min(stats.rssi_min or telegram.dbm, telegram.dbm)
            stats.rssi_max = max(stats.rssi_max or telegram.dbm, telegram.dbm)
        self.silent = False
        self._notify_stats()

    @callback
    def _on_received(self, received: ReceivedTelegram) -> None:
        self._record(received)
        if received.telegram.rorg == Rorg.UTE:
            self._answer_ute(received.telegram)
            return
        values = None
        for ref in (self.model.receive, *self.model.receive_extra):
            if ref is not None and (values := decode_telegram(ref, received.telegram)) is not None:
                break
        if values is None or values.get("channel", self.channel) != self.channel:
            return
        self.last_received = received
        if "on" in values:
            self.wall_state = bool(values["on"])
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
        destination: int = BROADCAST,
        rorg: int | None = None,
    ) -> None:
        """Queue a telegram from the sender ID of a profile without waiting for the actuator.

        profile None = the first configured sender. The queue waits for the actuator's status
        telegram in the background and repeats the command if it does not come; raises
        HomeAssistantError when the gateway is offline.
        """
        profile = profile or next(iter(self.senders), None)
        if profile not in self.senders:  # a receive-only device, or none for this command
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="device_no_sender",
                translation_placeholders={"device": self.subentry.title},
            )
        sender_id = self.senders[profile]
        rorg = rorg or self.model.sender_profile(profile).rorg
        telegram = RadioTelegram(rorg, data, sender_id, status, destination)
        expect = (lambda t: t.sender == self.device_id and self.own_channel(t)) if confirm else None
        runtime = self.entry.runtime_data
        queue_key = (self.unique_prefix, key) if key else None
        started = time.monotonic()
        if runtime.bus is not None and sender_id in runtime.bus.senders.pool:
            task = self.entry.async_create_task(
                self.hass,
                runtime.bus.group.submit(telegram, priority, key=queue_key, expect=expect),
                f"{DOMAIN} send {self.subentry.title}",
            )
            task.add_done_callback(lambda t: self._log_result(t.result(), started))
            if confirm:
                self.stats.commands += 1
            return
        if not runtime.gateway.connected:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="gateway_not_connected",
                translation_placeholders={"gateway": self.entry.title},
            )
        future = runtime.queue.submit(telegram, priority, key=queue_key, expect=expect)
        future.add_done_callback(lambda f: self._log_result(f.result(), started))
        if confirm:
            self.stats.commands += 1

    @callback
    def press(self, profile: str, button: bytes, *, confirm: bool = True) -> None:
        """Rocker profile: press and release, like a PTM switch."""
        self.send(button, profile=profile, status=ROCKER_STATUS_PRESSED, confirm=confirm)
        self.send(bytes(1), profile=profile, status=ROCKER_STATUS_RELEASED, confirm=False)

    def rocker_button(self, on: bool) -> bytes:
        """The rocker sender's press for on / up or off / down (the chosen buttons)."""
        if on:
            return bytes([ROCKER_CODES[self.options.get(OPT_ROCKER_ON, "a0")]])
        return bytes([ROCKER_CODES[self.options.get(OPT_ROCKER_OFF, "a1")]])

    def _log_result(self, result: SendResult, started: float) -> None:
        if result == SendResult.CONFIRMED:
            self.stats.confirmed += 1
            self.stats.latencies.append(time.monotonic() - started)
            self._notify_stats()
        elif result in (SendResult.UNCONFIRMED, SendResult.FAILED):
            _LOGGER.warning("%s: command %s", self.subentry.title, result)

    @callback
    def teach_in(self, profile: str) -> None:
        sender = self.model.sender_profile(profile)
        if not sender.teach_in:  # UTE: answer the actuator's query within the window
            self._ute_profile = profile
            self._ute_until = time.monotonic() + UTE_WINDOW
            _LOGGER.info(
                "%s: waiting %d s for the actuator's teach-in query",
                self.subentry.title,
                UTE_WINDOW,
            )
            return
        if profile in (ROCKER.id, DIRECTION_ROCKER.id):  # taught in with its "on" button
            self.press(profile, self.rocker_button(True), confirm=False)
        elif sender.rorg == Rorg.RPS:
            self.press(profile, sender.teach_in, confirm=False)
        else:
            self.send(sender.teach_in, profile=profile, priority=Priority.BACKGROUND, confirm=False)

    @callback
    def _answer_ute(self, telegram: RadioTelegram) -> None:
        """VLD actuator in learn mode: accept its UTE query, addressed to it, while armed."""
        request = decode_ute_request(telegram.data)
        if request is None or not request.response_expected:
            return
        if self._ute_profile is None or time.monotonic() > self._ute_until:
            _LOGGER.debug("%s: UTE query ignored (teach-in not armed)", self.subentry.title)
            return
        profile, self._ute_profile = self._ute_profile, None
        self.send(
            encode_ute_response(request),
            profile=profile,
            priority=Priority.SAFETY,
            confirm=False,
            destination=telegram.sender,
            rorg=Rorg.UTE,
        )
        _LOGGER.info("%s: UTE %s answered", self.subentry.title, request.eep)
