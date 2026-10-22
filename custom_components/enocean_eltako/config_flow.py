"""Config flow for the EnOcean Eltako integration: one entry per gateway."""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

import probatio as vol
from homeassistant.config_entries import (
    SOURCE_HASSIO,
    SOURCE_RECONFIGURE,
    ConfigEntry,
    ConfigEntryState,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers import discovery_flow
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    SerialPortSelector,
    TextSelector,
)
from homeassistant.helpers.service_info.hassio import HassioServiceInfo
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .catalog import DeviceModel
from .const import (
    BAUDRATES,
    CONF_BASE_ID,
    CONF_BAUDRATE,
    CONF_BUS_GROUP,
    CONF_DEVICE,
    CONF_DISCOVERY,
    CONF_MESSAGE_DELAY,
    CONF_MODE,
    CONF_MODEL,
    CONF_NAME,
    CONF_PATH,
    CONF_PROXY_REPLAY,
    CONF_REPEATER,
    DEFAULT_MESSAGE_DELAY,
    DOMAIN,
    MODE_ALWAYS,
    MODE_ON_DEMAND,
    REPEATER_LEVELS,
    REPEATER_UNCHANGED,
)
from .protocol.gateway import Gateway
from .protocol.ids import format_id, is_valid_base_id, parse_id
from .protocol.models import MODELS, GatewayModel, Protocol
from .protocol.transport import Connection, SerialConnection, TcpConnection
from .proxy_status import CONF_PROXY_STATUS_PORT
from .subentry_flow import (
    SUBENTRY_FLOWS,
    DeviceForm,
)

_LOGGER = logging.getLogger(__name__)

NEW_BUS_GROUP = "new"


class CannotConnect(Exception):
    """The gateway could not be opened."""


async def probe_gateway(model: GatewayModel, connection: Connection) -> int | None:
    """Open the gateway and read its base ID if the model supports it."""
    gateway = Gateway(model.protocol, connection)
    try:
        await gateway.connect(timeout=5)
    except (OSError, TimeoutError) as err:
        raise CannotConnect(str(err)) from err
    try:
        return await gateway.read_base_id() if model.reads_base_id else None
    finally:
        await gateway.close()


def _base_part(entry: ConfigEntry) -> str:
    """The base ID of a gateway entry; a second gateway with the same ID has a "#2" suffix."""
    return (entry.unique_id or "").split("#")[0]


def _is_connected(entry: ConfigEntry) -> bool:
    """A running gateway did not move: a second one with its base ID is another gateway."""
    runtime = getattr(entry, "runtime_data", None)
    return entry.state is ConfigEntryState.LOADED and bool(runtime and runtime.gateway.connected)


class EnOceanEltakoConfigFlow(DeviceForm, ConfigFlow, domain=DOMAIN):
    """Add a gateway: model, connection, connection test, base ID. Also confirms
    discovered devices (discovery.py) and adds them to the gateway that heard them."""

    VERSION = 1
    MINOR_VERSION = 3  # 1.2: senders listed (schema 2); 1.3: rocker buttons explicit (schema 3)

    def __init__(self) -> None:
        self._model: GatewayModel | None = None
        self._connection: Connection | None = None
        self._base_id = 0
        self._same_base_id_ok = False  # the user confirmed a second gateway with this base ID
        self._data: dict[str, Any] = {}
        self._options: dict[str, Any] = {}
        self._suggested: dict[str, Any] = {}  # reconfigure: the current connection
        self._proxy: dict[str, Any] | None = None  # gateway announced by a proxy app
        self._proxy_app = "EnOcean Proxy"  # its name: Device Proxy or EnOcean Proxy
        self._device_model: DeviceModel | None = None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self._model = MODELS[user_input[CONF_MODEL]]
            if self._model.usb:
                return await self.async_step_connection()
            return await self.async_step_tcp()
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_MODEL): SelectSelector(
                        SelectSelectorConfig(
                            options=list(MODELS),
                            translation_key=CONF_MODEL,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change how the gateway is reached (port, ser2net host); it must stay the same gateway."""
        entry = self._get_reconfigure_entry()
        self._model = MODELS[entry.data[CONF_MODEL]]
        device = entry.data[CONF_DEVICE]
        if device.get("type") == "serial":
            self._suggested = {CONF_PATH: device["path"], CONF_BAUDRATE: str(device["baudrate"])}
        else:
            self._suggested = {CONF_HOST: device["host"], CONF_PORT: device["port"]}
        if self._model.usb:
            return await self.async_step_connection()
        return await self.async_step_tcp()

    async def async_step_zeroconf(self, discovery_info: ZeroconfServiceInfo) -> ConfigFlowResult:
        """A PioTek MGW-ETH announced itself (_bsc-sc-socket._tcp)."""
        model = MODELS["mgw_eth"]
        host = discovery_info.host
        port = discovery_info.port or model.default_port or 0
        for entry in self._async_current_entries(include_ignore=False):
            device = entry.data.get(CONF_DEVICE, {})
            if device.get("type") == "tcp" and device.get(CONF_HOST) == host:
                return self.async_abort(reason="already_configured")
        # until the base ID is known, the host identifies the discovery (and its "ignore")
        await self.async_set_unique_id(f"zeroconf_{host}")
        self._abort_if_unique_id_configured()
        connection = TcpConnection(host, port)
        known = [
            e
            for e in self._async_current_entries(include_ignore=False)
            if e.data.get(CONF_MODEL) == model.key
        ]
        if (moved := await self._async_moved_gateway(model, connection, known)) is not None:
            return moved
        self._model = model
        self._connection = connection
        self.context["title_placeholders"] = {"name": f"{model.name} ({host})"}
        return await self.async_step_zeroconf_confirm()

    async def _async_moved_gateway(
        self,
        model: GatewayModel,
        connection: TcpConnection,
        candidates: list[ConfigEntry],
        data_updates: dict[str, Any] | None = None,
    ) -> ConfigFlowResult | None:
        """discovery-update-info: a known gateway at a new address updates its entry.

        Reads the base ID at the announced address; when it is a configured gateway's, that
        entry gets the new address (and data_updates) and reloads, no confirmation needed.
        """
        if not candidates or not model.reads_base_id:
            return None
        try:
            base_id = await probe_gateway(model, connection)
        except (CannotConnect, TimeoutError):
            return None
        if base_id is None or not is_valid_base_id(base_id):
            return None
        for entry in candidates:
            if _base_part(entry) == format_id(base_id) and not _is_connected(entry):
                _LOGGER.info("%s moved to %s", entry.title, connection)
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={CONF_DEVICE: connection.as_dict(), **(data_updates or {})},
                    reason="already_configured",
                )
        return None

    async def async_step_hassio(self, discovery_info: HassioServiceInfo) -> ConfigFlowResult:
        """A proxy app announced its gateways: the Device Proxy or the older EnOcean Proxy.

        The Supervisor keeps one message per app and service, so the app lists all gateways
        in one message; this flow takes the first unconfigured one and starts a flow of its
        own for each further one. Older app versions sent a single gateway (host + port).
        A gateway that was set up through a proxy app before and now comes from another one
        (moving from the EnOcean Proxy to the Device Proxy) keeps its entry: it is found by
        its base ID and gets the new address.
        """
        config = dict(discovery_info.config)
        if "gateways" in config:
            gateways = [dict(g) for g in config.pop("gateways")]
        else:
            gateways = [{k: config.pop(k) for k in ("name", "port", "protocol") if k in config}]
        host = str(config["host"])
        configured = {
            (
                entry.data.get(CONF_DEVICE, {}).get(CONF_HOST),
                entry.data.get(CONF_DEVICE, {}).get(CONF_PORT),
            )
            for entry in self._async_current_entries(include_ignore=False)
        }
        gateways = [g for g in gateways if (host, int(g["port"])) not in configured]
        if not gateways:
            return self.async_abort(reason="already_configured")
        for extra in gateways[1:]:
            discovery_flow.async_create_flow(
                self.hass,
                DOMAIN,
                {"source": SOURCE_HASSIO},
                HassioServiceInfo(
                    config={**config, "gateways": [extra]},
                    name=discovery_info.name,
                    slug=discovery_info.slug,
                    uuid=discovery_info.uuid,
                ),
            )
        gateway = gateways[0]
        port = int(gateway["port"])
        await self.async_set_unique_id(f"proxy_{host}_{port}")
        self._abort_if_unique_id_configured()
        # a gateway of the app on another port (the app's port options changed), or one
        # that came through another proxy app before (moved to the Device Proxy)
        through_app = [
            e
            for e in self._async_current_entries(include_ignore=False)
            if e.data.get(CONF_DEVICE, {}).get(CONF_HOST) == host
            or e.options.get(CONF_PROXY_REPLAY)
            or CONF_PROXY_STATUS_PORT in e.data
        ]
        probe = next(
            m
            for m in MODELS.values()
            if m.reads_base_id and m.protocol == (gateway.get("protocol") or "esp2")
        )
        connection = TcpConnection(host, port)
        updates = (
            {CONF_PROXY_STATUS_PORT: int(config["status_port"])}
            if config.get("status_port")
            else {}
        )
        moved = await self._async_moved_gateway(probe, connection, through_app, updates)
        if moved is not None:
            return moved
        self._proxy = {**config, **gateway}
        self._connection = TcpConnection(host, port)
        self._proxy_app = "Device Proxy" if config.get("app") == "device_proxy" else "EnOcean Proxy"
        self.context["title_placeholders"] = {
            "name": f"{gateway.get('name', host)} ({self._proxy_app})"
        }
        return await self.async_step_proxy_confirm()

    async def async_step_proxy_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Which gateway model sits behind the proxy (its protocol narrows the choice)."""
        assert self._proxy is not None and self._connection is not None
        errors: dict[str, str] = {}
        if user_input is not None:
            self._model = MODELS[user_input[CONF_MODEL]]
            result = await self._async_test_connection(errors)
            if result is not None:
                return result
        protocol = Protocol.ESP3 if self._proxy.get("protocol") == "esp3" else Protocol.ESP2
        models = [key for key, model in MODELS.items() if model.protocol is protocol]
        name = str(self._proxy.get("name", "")).lower().replace("-", "").replace(" ", "")
        guess = next((k for k in models if k.replace("_", "") in name), models[0])
        return self.async_show_form(
            step_id="proxy_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_MODEL, default=guess): SelectSelector(
                        SelectSelectorConfig(
                            options=models,
                            translation_key=CONF_MODEL,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
            errors=errors,
            description_placeholders={
                "name": str(self._proxy.get("name", "")),
                "connection": str(self._connection),
                "app": self._proxy_app,
            },
        )

    async def async_step_zeroconf_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        assert self._model is not None and self._connection is not None
        errors: dict[str, str] = {}
        if user_input is not None:
            result = await self._async_test_connection(errors)
            if result is not None:
                return result
        return self.async_show_form(
            step_id="zeroconf_confirm",
            errors=errors,
            description_placeholders={
                "model": self._model.name,
                "connection": str(self._connection),
            },
        )

    async def async_step_connection(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """USB gateways: direct or via ser2net."""
        return self.async_show_menu(step_id="connection", menu_options=["serial", "tcp"])

    async def async_step_serial(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        assert self._model is not None
        errors: dict[str, str] = {}
        if user_input is not None:
            baudrate = self._model.baudrate or int(user_input[CONF_BAUDRATE])
            self._connection = SerialConnection(user_input[CONF_PATH], baudrate)
            result = await self._async_test_connection(errors)
            if result is not None:
                return result
        schema: dict[Any, Any] = {vol.Required(CONF_PATH): SerialPortSelector()}
        if self._model.baudrate is None:
            schema[vol.Required(CONF_BAUDRATE, default="57600")] = SelectSelector(
                SelectSelectorConfig(options=[str(b) for b in BAUDRATES])
            )
        return self.async_show_form(
            step_id="serial",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(schema), user_input or self._suggested
            ),
            errors=errors,
            description_placeholders={"model": self._model.name},
        )

    async def async_step_tcp(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        assert self._model is not None
        errors: dict[str, str] = {}
        if user_input is not None:
            self._connection = TcpConnection(user_input[CONF_HOST], int(user_input[CONF_PORT]))
            result = await self._async_test_connection(errors)
            if result is not None:
                return result
        port_key = (
            vol.Required(CONF_PORT, default=self._model.default_port)
            if self._model.default_port
            else vol.Required(CONF_PORT)
        )
        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): TextSelector(),
                port_key: NumberSelector(
                    NumberSelectorConfig(min=1, max=65535, mode=NumberSelectorMode.BOX)
                ),
            }
        )
        baudrate = self._model.baudrate or 57600
        return self.async_show_form(
            step_id="tcp" if self._model.usb else "network",
            data_schema=self.add_suggested_values_to_schema(schema, user_input or self._suggested),
            errors=errors,
            description_placeholders={"model": self._model.name, "baudrate": str(baudrate)},
        )

    async def async_step_network(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Network gateways (MGW-ETH, Symcon) use the TCP step under their own wording."""
        return await self.async_step_tcp(user_input)

    async def async_step_base_id(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        assert self._model is not None
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                base_id = parse_id(user_input[CONF_BASE_ID])
            except ValueError:
                base_id = None
            if base_id is not None and is_valid_base_id(base_id):
                return await self._async_create(base_id)
            errors[CONF_BASE_ID] = "invalid_base_id"
        return self.async_show_form(
            step_id="base_id",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema({vol.Required(CONF_BASE_ID): TextSelector()}), user_input
            ),
            errors=errors,
            description_placeholders={"model": self._model.name},
        )

    async def _async_test_connection(self, errors: dict[str, str]) -> ConfigFlowResult | None:
        assert self._model is not None and self._connection is not None
        try:
            base_id = await probe_gateway(self._model, self._connection)
        except CannotConnect as err:
            _LOGGER.debug("Cannot connect to %s: %s", self._connection, err)
            errors["base"] = "cannot_connect"
            return None
        if base_id is not None and is_valid_base_id(base_id):
            return await self._async_create(base_id)
        if self.source == SOURCE_RECONFIGURE:  # FAM14 or silent: keep the stored base ID
            return self._async_update_connection()
        if base_id is not None:
            _LOGGER.warning("%s reported an invalid base ID %s", self._model.name, hex(base_id))
        return await self.async_step_base_id()

    async def _async_create(self, base_id: int) -> ConfigFlowResult:
        assert self._model is not None
        if self.source == SOURCE_RECONFIGURE:
            if _base_part(self._get_reconfigure_entry()) != format_id(base_id):
                return self.async_abort(reason="wrong_gateway")
            return self._async_update_connection()
        self._base_id = base_id
        same = [
            e
            for e in self._async_current_entries(include_ignore=False)
            if _base_part(e) == format_id(base_id)
        ]
        if same and not self._same_base_id_ok:
            return await self.async_step_same_base_id()
        # a second gateway with the same base ID gets "<base ID>#2", "#3" ...
        taken = {e.unique_id for e in self._async_current_entries()}
        unique_id, number = format_id(base_id), 2
        while unique_id in taken:
            unique_id = f"{format_id(base_id)}#{number}"
            number += 1
        await self.async_set_unique_id(unique_id, raise_on_progress=False)
        self._abort_if_unique_id_configured()
        if self._model.bus:
            return await self.async_step_bus_group()
        return self._async_create_entry()

    async def async_step_same_base_id(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Another gateway already has this base ID: add this one anyway (e.g. a second radio)."""
        if user_input is not None:
            self._same_base_id_ok = True
            return await self._async_create(self._base_id)
        others = ", ".join(
            e.title
            for e in self._async_current_entries(include_ignore=False)
            if _base_part(e) == format_id(self._base_id)
        )
        return self.async_show_form(
            step_id="same_base_id",
            data_schema=vol.Schema({}),
            description_placeholders={"base_id": format_id(self._base_id), "gateways": others},
        )

    @callback
    def _async_update_connection(self) -> ConfigFlowResult:
        assert self._connection is not None
        return self.async_update_reload_and_abort(
            self._get_reconfigure_entry(), data_updates={CONF_DEVICE: self._connection.as_dict()}
        )

    async def async_step_bus_group(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Bus gateways: on the same RS485 bus as an existing one?"""
        groups = self._bus_groups()
        if user_input is None and groups:
            options = [
                SelectOptionDict(value=key, label=", ".join(titles))
                for key, titles in groups.items()
            ]
            options.append(SelectOptionDict(value=NEW_BUS_GROUP, label=NEW_BUS_GROUP))
            return self.async_show_form(
                step_id="bus_group",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_BUS_GROUP, default=next(iter(groups))): SelectSelector(
                            SelectSelectorConfig(
                                options=options,
                                translation_key=CONF_BUS_GROUP,
                                mode=SelectSelectorMode.LIST,
                            )
                        )
                    }
                ),
            )
        choice = (user_input or {}).get(CONF_BUS_GROUP, NEW_BUS_GROUP)
        if choice == NEW_BUS_GROUP:
            return self._async_create_entry(bus_group=uuid4().hex[:8], joins_group=False)
        return self._async_create_entry(bus_group=choice, joins_group=True)

    def _bus_groups(self) -> dict[str, list[str]]:
        groups: dict[str, list[str]] = {}
        for entry in self._async_current_entries(include_ignore=False):
            if group := entry.data.get(CONF_BUS_GROUP):
                groups.setdefault(group, []).append(entry.title)
        return groups

    @callback
    def _async_create_entry(
        self, bus_group: str | None = None, joins_group: bool = False
    ) -> ConfigFlowResult:
        assert self._model is not None and self._connection is not None
        self._data = {
            CONF_MODEL: self._model.key,
            CONF_DEVICE: self._connection.as_dict(),
            CONF_BASE_ID: format_id(self._base_id),
        }
        self._options = {CONF_MESSAGE_DELAY: DEFAULT_MESSAGE_DELAY}
        if self._proxy is not None and self._proxy.get("replay"):
            self._options[CONF_PROXY_REPLAY] = True  # telegrams missed during restarts
        if self._proxy is not None and self._proxy.get("status_port"):
            self._data[CONF_PROXY_STATUS_PORT] = int(self._proxy["status_port"])
        if bus_group is not None:
            self._data[CONF_BUS_GROUP] = bus_group
            # A FAM14 next to another bus gateway is only needed for failover and import.
            on_demand = self._model.key == "fam14" and joins_group
            self._options[CONF_MODE] = MODE_ON_DEMAND if on_demand else MODE_ALWAYS
        return self._async_show_name()

    def _model_name(self) -> str:
        assert self._model is not None
        return self._model.name

    @callback
    def _async_show_name(self) -> ConfigFlowResult:
        return self.async_show_form(
            step_id="name",
            data_schema=vol.Schema(
                {vol.Required(CONF_NAME, default=self._model_name()): TextSelector()}
            ),
            description_placeholders={"base_id": format_id(self._base_id)},
        )

    async def async_step_name(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Last step: the gateway's name, shown on the integration page and its device."""
        if user_input is None:
            return self._async_show_name()
        return self.async_create_entry(
            title=user_input[CONF_NAME].strip() or self._model_name(),
            data=self._data,
            options=self._options,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> EnOceanEltakoOptionsFlow:
        return EnOceanEltakoOptionsFlow()

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        return dict(SUBENTRY_FLOWS)


class EnOceanEltakoOptionsFlow(OptionsFlow):
    """Settings (send spacing, discovery; bus gateways always vs on demand; ESP3 repeater).

    Sender IDs and the takeover from the old eltako integration live in the panel.

    No OptionsFlowWithReload: the entry's update listener reloads it on every change
    (subentries as well), and Home Assistant refuses the two together.
    """

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self.async_step_settings()

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(
                data={**user_input, CONF_MESSAGE_DELAY: int(user_input[CONF_MESSAGE_DELAY])}
            )
        schema: dict[Any, Any] = {
            vol.Required(CONF_MESSAGE_DELAY, default=DEFAULT_MESSAGE_DELAY): NumberSelector(
                NumberSelectorConfig(
                    min=0, max=1000, step=1, unit_of_measurement="ms", mode=NumberSelectorMode.BOX
                )
            )
        }
        schema[vol.Required(CONF_DISCOVERY, default=True)] = BooleanSelector()
        if self.config_entry.data.get(CONF_DEVICE, {}).get("type") == "tcp":
            schema[vol.Required(CONF_PROXY_REPLAY, default=False)] = BooleanSelector()
        if MODELS[self.config_entry.data[CONF_MODEL]].bus:
            schema[vol.Required(CONF_MODE, default=MODE_ALWAYS)] = SelectSelector(
                SelectSelectorConfig(
                    options=[MODE_ALWAYS, MODE_ON_DEMAND],
                    translation_key=CONF_MODE,
                    mode=SelectSelectorMode.LIST,
                )
            )
        if MODELS[self.config_entry.data[CONF_MODEL]].protocol is Protocol.ESP3:
            schema[vol.Required(CONF_REPEATER, default=REPEATER_UNCHANGED)] = SelectSelector(
                SelectSelectorConfig(
                    options=[REPEATER_UNCHANGED, *REPEATER_LEVELS],
                    translation_key=CONF_REPEATER,
                    mode=SelectSelectorMode.LIST,
                )
            )
        return self.async_show_form(
            step_id="settings",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(schema), self.config_entry.options
            ),
        )
