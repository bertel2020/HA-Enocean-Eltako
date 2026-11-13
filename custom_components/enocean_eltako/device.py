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
    CENTRAL,
    CONTROLLER,
    DIRECTION_ROCKER,
    GROUP_VIRTUAL,
    OPT_PART_OF,
    OPT_PLATFORM,
    OPT_ROCKER_OFF,
    OPT_ROCKER_ON,
    OPT_STATUS_CHANNEL,
    OPT_WALL_OFF,
    OPT_WALL_ON,
    OPT_WALL_SWITCH,
    PLATFORM_IMPULSE,
    ROCKER,
    ROCKER_CODES,
    ROCKER_STATUS_PRESSED,
    ROCKER_STATUS_RELEASED,
    DeviceModel,
    LinkedId,
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
from .notes import device_key
from .protocol.dispatcher import ReceivedTelegram
from .protocol.eep import EEPRef
from .protocol.eep.codecs import decode_telegram
from .protocol.eep.eltako import futh, shutter, switching
from .protocol.eep.eltako.commands import LEARN_UNLOCK, TEACH_OUT_REPEATS
from .protocol.eep.model import out_of_range
from .protocol.eep.std.profiles import PROFILES
from .protocol.eep.teach_in import decode_teach_in_4bs
from .protocol.eep.ute import decode_ute_request, encode_ute_response
from .protocol.ids import BROADCAST, format_id, parse_id
from .protocol.send_queue import BUS_CONFIRM_TIMEOUT, MAX_RETRIES, Priority, SendResult
from .protocol.telegram import RadioTelegram, Rorg

if TYPE_CHECKING:
    from . import EnOceanEltakoConfigEntry

_LOGGER = logging.getLogger(__name__)

Listener = Callable[[dict[str, Any]], None]
LATENCY_SAMPLES = 10  # E11: confirmation times kept per device
# commands that carry the lock bit: the sender's EEP -> (index of the command byte, its values)
LOCK_COMMANDS: dict[EEPRef, tuple[int, tuple[int, ...]]] = {
    EEPRef("A5-38-08", "eltako"): (0, (1, 2)),  # switching, dimming
    EEPRef("H5-3F-7F", "eltako"): (2, (0, 1, 2)),  # stop, up, down
}
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
class GatewayHeard:
    """How one gateway hears a device: telegrams, those without a repeater, last signal."""

    count: int = 0
    direct: int = 0
    rssi: int | None = None  # dBm of the last telegram (ESP3 gateways only)
    last: float = 0.0


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
    mismatches: int = 0  # telegrams in a row that fit none of the device's profiles ...
    mismatch_range: bool = False  # ... or whose values lie outside the profile's ranges
    commands: int = 0
    confirmed: int = 0
    heard: dict[str, GatewayHeard] = field(default_factory=dict)  # per gateway entry ID
    # E11: seconds from command to the actuator's answer (queue wait and retries included)
    latencies: deque[float] = field(default_factory=lambda: deque(maxlen=LATENCY_SAMPLES))

    @property
    def success_rate(self) -> float | None:
        return round(100 * self.confirmed / self.commands, 1) if self.commands else None


def _reports(telegram: RadioTelegram, target_on: bool | None) -> bool:
    """False for a switching status that reports the other relay state than the one asked for."""
    if target_on is None or telegram.rorg != Rorg.RPS or not telegram.data:
        return True
    state = switching.STATUS_CODES.get(telegram.data[0])
    return state is None or state[1] == target_on


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
        self.thermostat: Any = None  # the ThermostatController of a switching actuator channel
        self._ute_profile: str | None = None  # VLD: profile whose teach-in is armed ...
        self._ute_until = 0.0  # ... until this time.monotonic()
        self.last_values: dict[str, Any] = {}  # the last decoded values of the device's channel
        self.wall_state: bool | None = None  # I4: last known on/off, for a toggling button
        self.state_heard = False  # a status telegram of the actuator itself has arrived
        self.locked = False  # commands carry the lock bit: the actuator ignores its pushbuttons
        # a device sending from several IDs (FUTH): the ID it listens to -> what that ID means
        self.linked: dict[int, LinkedId] = {
            (self.device_id + link.offset) & 0xFFFFFFFF: link for link in self.model.linked
        }

    @property
    def radio_ids(self) -> tuple[int, ...]:
        """The IDs the device sends from: its own, or the linked ones of a multi-ID device."""
        return tuple(self.linked) or (self.device_id,)

    def owns(self, sender: int) -> bool:
        return sender in self.linked if self.linked else sender == self.device_id

    def receive_refs(self, sender: int) -> tuple[EEPRef, ...]:
        """The profiles a telegram of this sender ID may be decoded with."""
        if (link := self.linked.get(sender)) is not None:
            return (link.eep,)
        return tuple(r for r in (self.model.receive, *self.model.receive_extra) if r is not None)

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
    def part_of(self) -> EnOceanDevice | None:
        """The device this one hangs under (a meter on the load of an actuator), if set and
        still there."""
        target = self.entry.runtime_data.devices.get(self.options.get(OPT_PART_OF) or "")
        return None if target is self else target

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
        # a device under another one is linked after the platforms are set up (the registry ID
        # of the other may not exist yet): __init__._async_link_devices
        if self.part_of is None and (gateway := self.entry.runtime_data.gateway_device_id):
            info["via_device_id"] = gateway
        return info

    def start(self) -> Callable[[], None]:
        dispatcher = self.entry.runtime_data.hub.dispatcher
        removers = [
            remove
            for radio_id in self.radio_ids
            for remove in (
                dispatcher.add_listener(radio_id, self._on_received),
                dispatcher.add_heard_listener(radio_id, self._on_heard),
            )
        ]
        remove_wall = None
        if wall_switch := self.options.get(OPT_WALL_SWITCH):
            remove_wall = dispatcher.add_listener(parse_id(wall_switch), self._on_wall_switch)

        def remove_all() -> None:
            for remove in removers:
                remove()
            if remove_wall is not None:
                remove_wall()

        return remove_all

    @callback
    def _on_heard(self, received: ReceivedTelegram) -> None:
        heard = self.stats.heard.setdefault(received.gateway, GatewayHeard())
        heard.count += 1
        heard.direct += received.telegram.status & 0x0F == 0
        if received.telegram.dbm is not None:
            heard.rssi = received.telegram.dbm
        heard.last = received.timestamp
        if (notes := self.entry.runtime_data.hub.notes.get(self.entry.entry_id)) is not None:
            telegram = received.telegram
            notes.remember_last(
                format_id(received.sender),
                received.gateway,
                telegram.rorg,
                telegram.data,
                telegram.status,
                telegram.dbm,
                received.timestamp,
            )
            notes.touch_signal(
                device_key(self.subentry),
                received.gateway,
                {
                    "count": heard.count,
                    "direct": heard.direct,
                    "rssi": heard.rssi,
                    "last": heard.last,
                },
            )

    def seed_signal(self, saved: dict[str, dict[str, Any]]) -> None:
        """Take over how the gateways heard this device before the restart."""
        for gateway, values in saved.items():
            self.stats.heard.setdefault(
                gateway,
                GatewayHeard(
                    count=int(values.get("count", 0)),
                    direct=int(values.get("direct", 0)),
                    rssi=values.get("rssi"),
                    last=float(values.get("last", 0)),
                ),
            )
        # the last time any gateway heard it is also when the device was last seen
        if self.stats.last_seen is None and self.stats.heard:
            gateway, heard = max(self.stats.heard.items(), key=lambda item: item[1].last)
            if heard.last > 0:
                self.stats.last_seen = heard.last
                self.stats.gateway = self.stats.gateway or gateway

    @callback
    def _on_wall_switch(self, received: ReceivedTelegram) -> None:
        """I4: a press on the wall switch teached into the actuator sets the assumed state."""
        values = decode_telegram(WALL_SWITCH_EEP, received.telegram)
        if values is None or values.get("EB") != 1 or "R1" not in values or values.get("NU") == 0:
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
        values, matched = None, None
        for ref in self.receive_refs(received.sender):
            if (values := decode_telegram(ref, received.telegram)) is not None:
                matched = ref
                break
        self._count_mismatch(received.telegram, values, matched)
        if values is not None and (link := self.linked.get(received.sender)):
            values = futh.interpret(link.role, values)  # what this ID means
        if values is None or values.get("channel", self.channel) != self.channel:
            return
        self.last_received = received
        self.last_values = values
        if "on" in values:
            self.wall_state = bool(values["on"])
            self.state_heard = True
        for listener in list(self._listeners):
            listener(values)

    def _count_mismatch(
        self, telegram: RadioTelegram, values: dict[str, Any] | None, matched: EEPRef | None
    ) -> None:
        """Count telegrams in a row that fit none of the profiles or whose values lie outside
        the ranges of a standard profile (a repair after a few)."""
        if values is not None:
            profile = PROFILES.get(matched.eep) if matched and matched.variant == "std" else None
            if profile is not None and out_of_range(profile, telegram.data, telegram.status):
                self.stats.mismatches += 1
                self.stats.mismatch_range = True
            else:
                self.stats.mismatches = 0
        elif self.model.receive is not None and not (
            telegram.rorg == Rorg.BS4 and decode_teach_in_4bs(telegram.data) is not None
        ):  # a teach-in telegram is not a mismatch
            self.stats.mismatches += 1
            self.stats.mismatch_range = False

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
        target_on: bool | None = None,
    ) -> None:
        """Queue a telegram from the sender ID of a profile without waiting for the actuator.

        target_on: the relay state the command asks for. A switching status that reports the
        other state (the late answer to an earlier, replaced command) does not confirm it.

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
        data = self._with_lock(data, profile)
        # a run command or an impulse that is repeated moves the cover / the door again
        retries = 0 if self.model.kind == "cover" or self.impulse else MAX_RETRIES
        sender_id = self.senders[profile]
        rorg = rorg or self.model.sender_profile(profile).rorg
        telegram = RadioTelegram(rorg, data, sender_id, status, destination)
        expect = (
            (
                lambda t: (
                    t.sender == self.device_id and self.own_channel(t) and _reports(t, target_on)
                )
            )
            if confirm
            else None
        )
        runtime = self.entry.runtime_data
        queue_key = (self.unique_prefix, key) if key else None
        started = time.monotonic()
        if runtime.bus is not None and sender_id in runtime.bus.senders.pool:
            task = self.entry.async_create_task(
                self.hass,
                runtime.bus.group.submit(
                    telegram,
                    priority,
                    key=queue_key,
                    expect=expect,
                    timeout=BUS_CONFIRM_TIMEOUT,
                    retries=retries,
                ),
                f"{DOMAIN} send {self.subentry.title}",
            )
            task.add_done_callback(
                lambda t: None if t.cancelled() else self._log_result(t.result(), started)
            )
            if confirm:
                self.stats.commands += 1
            return
        if not runtime.gateway.connected:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="gateway_not_connected",
                translation_placeholders={"gateway": self.entry.title},
            )
        future = runtime.queue.submit(
            telegram, priority, key=queue_key, expect=expect, retries=retries
        )
        future.add_done_callback(lambda f: self._log_result(f.result(), started))
        if confirm:
            self.stats.commands += 1

    @property
    def impulse(self) -> bool:
        """A switching actuator used as a button (garage door drive): one pulse per press, never
        repeated, and no state of its own (the relay falls back by itself)."""
        return self.model.kind == "switch" and self.options.get(OPT_PLATFORM) == PLATFORM_IMPULSE

    def sender_test_error(self) -> str | None:
        """Why the senders cannot be tested (a code for the panel), None when they can: only
        switching actuators and dimmers with a known state, as the test repeats that state.
        Covers are not tested: every command moves them or interrupts a run."""
        if self.model.kind not in ("switch", "dimmer") or not self.senders:
            return "unsupported"
        if (
            not self.state_heard
            or self.wall_state is None
            or (
                self.model.kind == "dimmer"
                and self.wall_state
                and "brightness" not in self.last_values
            )
        ):
            return "state_unknown"
        return None

    async def async_test_senders(self) -> list[dict[str, str]]:
        """Send the actuator's current state through each sender in turn: harmless, and an
        answer shows that the actuator knows that sender. No answer is not proof of the opposite
        (the command may have arrived at an actuator that stays silent)."""
        state = bool(self.wall_state)
        results = []
        for profile_id, sender_id in self.senders.items():
            profile = self.model.sender_profile(profile_id)
            if self.model.kind == "dimmer":
                # the brightness it has now (command 2 sets it exactly); a rocker press or a
                # switch-on command would go to the stored brightness and could change it
                result = (
                    await self._test_telegram(
                        profile,
                        sender_id,
                        switching.encode_dim(self.last_values.get("brightness", 0), on=state),
                    )
                    if profile_id == CENTRAL.id
                    else "skipped"
                )
            elif profile.switch_fn is not None:
                result = await self._test_telegram(profile, sender_id, profile.switch_fn(state))
            elif profile_id == ROCKER.id and self.options.get(
                OPT_ROCKER_ON, self.model.rocker_buttons[0]
            ) != self.options.get(
                OPT_ROCKER_OFF, self.model.rocker_buttons[1]
            ):  # a rocker that toggles would change the state
                result = await self._test_telegram(
                    profile, sender_id, self.rocker_button(state), ROCKER_STATUS_PRESSED
                )
                self.send(
                    bytes(1), profile=profile_id, status=ROCKER_STATUS_RELEASED, confirm=False
                )
            else:
                result = "skipped"
            results.append(
                {"profile": profile_id, "id": format_id(sender_id), "result": str(result)}
            )
        notes = self.entry.runtime_data.hub.notes[self.entry.entry_id]
        summary = {r["profile"]: r["result"] for r in results}
        notes.set_test(device_key(self.subentry), summary)
        notes.add_log(
            "sender_test",
            device_key(self.subentry),
            f"{self.subentry.title}: {', '.join(f'{p}={r}' for p, r in summary.items())}",
        )
        return results

    async def _test_telegram(
        self, profile: Any, sender_id: int, data: bytes, status: int = 0
    ) -> SendResult | str:
        telegram = RadioTelegram(profile.rorg, data, sender_id, status, BROADCAST)
        expect = lambda t: t.sender == self.device_id and self.own_channel(t)  # noqa: E731
        runtime = self.entry.runtime_data
        if runtime.bus is not None and sender_id in runtime.bus.senders.pool:
            return await runtime.bus.group.submit(telegram, Priority.BACKGROUND, expect=expect)
        return await runtime.queue.submit(telegram, Priority.BACKGROUND, expect=expect)

    @callback
    def press(
        self, profile: str, button: bytes, *, confirm: bool = True, target_on: bool | None = None
    ) -> None:
        """Rocker profile: press and release, like a PTM switch."""
        self.send(
            button,
            profile=profile,
            status=ROCKER_STATUS_PRESSED,
            confirm=confirm,
            target_on=target_on,
        )
        self.send(bytes(1), profile=profile, status=ROCKER_STATUS_RELEASED, confirm=False)

    def rocker_button(self, on: bool) -> bytes:
        """The rocker sender's press for on / up or off / down (the chosen buttons)."""
        if on:
            return bytes(
                [ROCKER_CODES[self.options.get(OPT_ROCKER_ON, self.model.rocker_buttons[0])]]
            )
        return bytes([ROCKER_CODES[self.options.get(OPT_ROCKER_OFF, self.model.rocker_buttons[1])]])

    def _log_result(self, result: SendResult, started: float) -> None:
        if result == SendResult.CONFIRMED:
            self.stats.confirmed += 1
            self.stats.latencies.append(time.monotonic() - started)
            self._notify_stats()
        elif result in (SendResult.UNCONFIRMED, SendResult.FAILED):
            _LOGGER.warning("%s: command %s", self.subentry.title, result)

    @callback
    def teach_in(self, profile: str) -> None:
        self.entry.runtime_data.hub.notes[self.entry.entry_id].add_log(
            "teach_in", device_key(self.subentry), f"{self.subentry.title}: {profile}", profile
        )
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

    @property
    def lockable(self) -> bool:
        """Switching actuators, dimmers and shutters with a central command or controller
        sender can lock their pushbuttons (DB0.2, Eltako "Inhalte der Eltako-Funktelegramme")."""
        return self.model.kind in ("switch", "dimmer", "cover") and any(
            self.model.sender_profile(p).eep in LOCK_COMMANDS for p in self.senders
        )

    def _with_lock(self, data: bytes, profile: str) -> bytes:
        """The command with DB0.2 set while the device is locked; status requests, learn
        telegrams and everything of other profiles stay as they are."""
        if not self.locked or len(data) != 4 or not data[3] & 0x08 or data[3] & 0x20:
            return data
        index = LOCK_COMMANDS.get(self.model.sender_profile(profile).eep)
        if index is None or data[index[0]] not in index[1]:
            return data
        return data[:3] + bytes([data[3] | 0x04])

    @callback
    def apply_lock(self) -> None:
        """Tell the actuator the new lock state: its current state again, now with or without
        the lock bit. A shutter gets a stop (it halts a run in progress)."""
        if self.model.kind == "cover":
            self.send(shutter.encode_command(shutter.STOP), profile=CONTROLLER.id, confirm=False)
            return
        if self.wall_state is None:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="lock_state_unknown",
                translation_placeholders={"device": self.subentry.title},
            )
        on = bool(self.wall_state)
        if self.model.kind == "dimmer":
            data = switching.encode_dim(self.last_values.get("brightness", 0), on=on)
        else:
            data = switching.encode_switch(on)
        self.send(data, profile=CENTRAL.id, key="switch", confirm=False)

    @callback
    def unlock_learning(self, profile: str, times: int = 1) -> None:
        """Series 62 actuators (FL62, FR62, FD62, FJ62): unlock the learn mode with DB0.5 set.
        Three times within two seconds the actuator forgets the sender ID (teach-out)."""
        _LOGGER.info("%s: learn mode telegram x%d (%s)", self.subentry.title, times, profile)
        for _ in range(times):
            self.send(LEARN_UNLOCK, profile=profile, priority=Priority.USER, confirm=False)

    @callback
    def teach_out(self, profile: str) -> None:
        self.unlock_learning(profile, TEACH_OUT_REPEATS)

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
