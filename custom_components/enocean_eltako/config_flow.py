"""Config flow for the EnOcean Eltako integration: one entry per gateway."""

from __future__ import annotations

import logging
from types import MappingProxyType
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
    ConfigSubentry,
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
from homeassistant.helpers.translation import async_get_translations

from .catalog import CATALOG, GENERIC_EEPS, DeviceModel, generic_model
from .const import (
    BAUDRATES,
    CONF_BASE_ID,
    CONF_BAUDRATE,
    CONF_BUS_GROUP,
    CONF_DEVICE,
    CONF_DEVICE_ID,
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
    SUBENTRY_DEVICE,
)
from .discovery import discovery_unique_id
from .protocol.eep import EEPRef
from .protocol.eep.teach_in import decode_teach_in_4bs
from .protocol.gateway import Gateway
from .protocol.ids import format_id, is_valid_base_id, parse_id
from .protocol.models import MODELS, GatewayModel, Protocol
from .protocol.sender_pool import SenderIdError, SenderState
from .protocol.telegram import Rorg
from .protocol.transport import Connection, SerialConnection, TcpConnection
from .proxy_status import CONF_PROXY_STATUS_PORT
from .subentry_flow import (
    SUBENTRY_FLOWS,
    DeviceForm,
    candidates,
    flatten_sections,
    receives,
    sender_owner,
    status_channel,
    subentry_unique_id,
)
from .takeover import TakeoverDevice, async_old_config, find_gateway, old_gateways, plan
from .takeover import subentry_data as takeover_data

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
        self._proxy: dict[str, Any] | None = None  # gateway announced by the EnOcean Proxy app
        self._discovery: dict[str, Any] = {}  # discovered device: gateway, ID, telegram
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
        self, model: GatewayModel, connection: TcpConnection, candidates: list[ConfigEntry]
    ) -> ConfigFlowResult | None:
        """discovery-update-info: a known gateway at a new address updates its entry.

        Reads the base ID at the announced address; when it is a configured gateway's, that
        entry gets the new address and reloads, no confirmation needed.
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
                    data_updates={CONF_DEVICE: connection.as_dict()},
                    reason="already_configured",
                )
        return None

    async def async_step_hassio(self, discovery_info: HassioServiceInfo) -> ConfigFlowResult:
        """The EnOcean Proxy app announced its gateways.

        The Supervisor keeps one message per app and service, so the app lists all gateways
        in one message; this flow takes the first unconfigured one and starts a flow of its
        own for each further one. Older app versions sent a single gateway (host + port).
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
        # a gateway of the app on another port (the app's port options changed)
        through_app = [
            e
            for e in self._async_current_entries(include_ignore=False)
            if e.data.get(CONF_DEVICE, {}).get(CONF_HOST) == host
        ]
        probe = next(
            m
            for m in MODELS.values()
            if m.reads_base_id and m.protocol == (gateway.get("protocol") or "esp2")
        )
        connection = TcpConnection(host, port)
        if (moved := await self._async_moved_gateway(probe, connection, through_app)) is not None:
            return moved
        self._proxy = {**config, **gateway}
        self._connection = TcpConnection(host, port)
        self.context["title_placeholders"] = {
            "name": f"{gateway.get('name', host)} (EnOcean Proxy)"
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

    # Discovered devices ---------------------------------------------------------------------

    async def async_step_integration_discovery(
        self, discovery_info: dict[str, Any]
    ) -> ConfigFlowResult:
        """A gateway heard a sender no device listens to."""
        device_id = parse_id(discovery_info[CONF_DEVICE_ID])
        await self.async_set_unique_id(discovery_unique_id(device_id))
        self._abort_if_unique_id_configured()
        self._discovery = discovery_info
        self.context["title_placeholders"] = {"name": format_id(device_id)}
        return await self.async_step_discovered()

    def _get_entry(self) -> ConfigEntry:
        """The gateway that heard the discovered device (DeviceForm)."""
        entry = self.hass.config_entries.async_get_entry(self._discovery["gateway"])
        assert entry is not None
        return entry

    def _discovery_abort(self) -> ConfigFlowResult | None:
        entry = self.hass.config_entries.async_get_entry(self._discovery["gateway"])
        if entry is None or getattr(entry, "runtime_data", None) is None:
            return self.async_abort(reason="gateway_not_loaded")
        device_id = self._discovery[CONF_DEVICE_ID]
        if any(s.unique_id == device_id for s in entry.subentries.values()):
            return self.async_abort(reason="already_configured")
        return None

    async def async_step_discovered(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Name the kinds that fit the heard telegram; a teach-in may settle it."""
        if (abort := self._discovery_abort()) is not None:
            return abort
        if user_input is not None:
            self._device_model = CATALOG[user_input[CONF_MODEL]]
            return await self.async_step_discovered_device()
        rorg = self._discovery["rorg"]
        data = bytes.fromhex(self._discovery["data"])
        teach_in = decode_teach_in_4bs(data) if rorg == Rorg.BS4 else None
        if teach_in is not None and teach_in.eep in GENERIC_EEPS:
            if not any(receives(m, teach_in.eep) for m in CATALOG.values()):
                self._device_model = generic_model(EEPRef(teach_in.eep, "std"))
                return await self.async_step_discovered_device()
        kinds = candidates(rorg, teach_in, data)
        if not kinds:
            return self.async_abort(reason="no_matching_kind")
        entry = self._get_entry()
        dbm = self._discovery.get("dbm")
        return self.async_show_form(
            step_id="discovered",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_MODEL, default=kinds[0]): SelectSelector(
                        SelectSelectorConfig(
                            options=kinds,
                            translation_key="device_model",
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
            description_placeholders={
                "device_id": self._discovery[CONF_DEVICE_ID],
                "gateway": entry.title,
                "eep": teach_in.eep if teach_in else f"{rorg:02X}",
                "dbm": f"{dbm} dBm" if dbm is not None else "-",
            },
        )

    async def async_step_discovered_device(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Name, senders and options as in "add device"; saved as a subentry of the gateway."""
        assert self._device_model is not None
        if (abort := self._discovery_abort()) is not None:
            return abort
        device_id = parse_id(self._discovery[CONF_DEVICE_ID])
        errors: dict[str, str] = {}
        if user_input is not None:
            data = await self._async_save(user_input, device_id, {}, errors)
            if data is not None:
                self.hass.config_entries.async_add_subentry(
                    self._get_entry(),
                    ConfigSubentry(
                        data=MappingProxyType(data),
                        subentry_type=SUBENTRY_DEVICE,
                        title=user_input[CONF_NAME],
                        unique_id=subentry_unique_id(
                            device_id, status_channel(flatten_sections(user_input))
                        ),
                    ),
                )
                return self.async_abort(reason="device_added")
        schema = {
            vol.Required(CONF_NAME): TextSelector(),
            **self._fields(self._device_model, {}, new=True),
        }
        result: ConfigFlowResult = await self._form("discovered_device", schema, user_input, errors)
        return result

    async def async_step_unignore(self, user_input: dict[str, Any]) -> ConfigFlowResult:
        """Un-ignored discovered device: offer it again when it is heard next time."""
        unique_id = user_input["unique_id"]
        if unique_id.startswith("device_"):
            from .hub import async_get_hub

            async_get_hub(self.hass).discovered.discard(parse_id(unique_id[len("device_") :]))
        return self.async_abort(reason="discovery_reset")

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
    """Settings (send spacing, discovery; bus gateways always vs on demand; ESP3 repeater)
    and the sender ID page (E3).

    No OptionsFlowWithReload: the entry's update listener reloads it on every change
    (subentries as well), and Home Assistant refuses the two together.
    """

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return self.async_show_menu(
            step_id="init", menu_options=["settings", "senders", "takeover"]
        )

    async def async_step_takeover(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Take devices over from the old eltako integration's YAML configuration."""
        entry = self.config_entry
        runtime = getattr(entry, "runtime_data", None)
        if runtime is None:
            return self.async_abort(reason="gateway_not_loaded")
        if (config := await async_old_config(self.hass)) is None:
            return self.async_abort(reason="takeover_no_config")
        try:
            base_id = parse_id(entry.data.get(CONF_BASE_ID, ""))
        except ValueError:
            base_id = -1
        if (gateway := find_gateway(config, base_id)) is None:
            found = ", ".join(str(g.get("base_id", "?")) for g in old_gateways(config)) or "-"
            return self.async_abort(
                reason="takeover_no_gateway", description_placeholders={"found": found}
            )
        existing = {s.unique_id for s in entry.subentries.values()}
        devices = plan(gateway)
        for device in devices:
            if device.model is not None and format_id(device.device_id) in existing:
                device.model, device.reason = None, "takeover_exists"
        ready = [d for d in devices if d.model is not None]
        if user_input is not None:
            chosen = set(user_input.get("devices", []))
            return await self._async_take_over(
                [d for d in ready if format_id(d.device_id) in chosen], runtime
            )
        translations = await async_get_translations(
            self.hass, self.hass.config.language, "selector", [DOMAIN]
        )

        def text(key: str, value: str) -> str:
            return translations.get(f"component.{DOMAIN}.selector.{key}.options.{value}", value)

        rows = [
            f"| {format_id(d.device_id)} | {d.name} | {d.old} | "
            + (text("device_model", d.model) if d.model else "-")
            + f" | {text('takeover_reason', d.reason) if d.reason else ''} |"
            for d in devices
        ]
        schema: dict[Any, Any] = {}
        if ready:
            schema[vol.Optional("devices", default=[format_id(d.device_id) for d in ready])] = (
                SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            SelectOptionDict(
                                value=format_id(d.device_id),
                                label=f"{d.name} ({format_id(d.device_id)})",
                            )
                            for d in ready
                        ],
                        multiple=True,
                        mode=SelectSelectorMode.LIST,
                    )
                )
            )
        return self.async_show_form(
            step_id="takeover",
            data_schema=vol.Schema(schema),
            description_placeholders={
                "base_id": format_id(base_id),
                "rows": "\n".join(rows) or "| - | - | - | - | - |",
            },
        )

    async def _async_take_over(
        self, devices: list[TakeoverDevice], runtime: Any
    ) -> ConfigFlowResult:
        """Subentries with the old sender IDs, then one reload instead of one per device."""
        if not devices:
            return self.async_abort(reason="senders_unchanged")
        entry = self.config_entry
        pool = runtime.senders.pool
        runtime.suspend_reload()
        skipped: list[str] = []
        for device in devices:
            senders: dict[str, int] = {}
            for profile, sender in device.senders.items():
                try:
                    pool.assign(sender, sender_owner(device.device_id, profile))
                except SenderIdError as err:
                    skipped.append(f"{format_id(sender)} ({device.name}): {err.reason}")
                    continue
                senders[profile] = sender
            self.hass.config_entries.async_add_subentry(
                entry,
                ConfigSubentry(
                    data=MappingProxyType(takeover_data(device, senders)),
                    subentry_type=SUBENTRY_DEVICE,
                    title=device.name,
                    unique_id=format_id(device.device_id),
                ),
            )
        await runtime.senders.async_save()
        self.hass.config_entries.async_schedule_reload(entry.entry_id)
        return self.async_abort(
            reason="takeover_done",
            description_placeholders={
                "count": str(len(devices)),
                "skipped": "\n".join(f"- {s}" for s in skipped) or "-",
            },
        )

    async def async_step_senders(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Who uses which sender ID; blocked IDs can be freed once the teach-out is done."""
        entry = self.config_entry
        runtime = getattr(entry, "runtime_data", None)
        if runtime is None:
            return self.async_abort(reason="gateway_not_loaded")
        stores = [runtime.senders] + ([runtime.bus.senders] if runtime.bus is not None else [])
        if user_input is not None:
            freed = {parse_id(text) for text in user_input.get("free", [])}
            for store in stores:
                for sender in freed & {s for s, _a in store.pool.allocations()}:
                    store.pool.confirm_teach_out(sender)
                await store.async_save()
            return self.async_abort(reason="senders_freed" if freed else "senders_unchanged")
        translations = await async_get_translations(
            self.hass, self.hass.config.language, "selector", [DOMAIN]
        )
        prefix = f"component.{DOMAIN}.selector.sender_state.options."
        titles = {
            s.unique_id: s.title
            for e in self.hass.config_entries.async_entries(DOMAIN, include_ignore=False)
            for s in e.subentries.values()
        }
        rows: list[str] = []
        blocked: list[str] = []
        free = 0
        for store in stores:
            pool = store.pool
            free += pool.free_count()
            for sender, allocation in pool.allocations():
                _kind, _sep, rest = allocation.owner.partition(":")
                device, _sep, profile = rest.rpartition(":")
                state = translations.get(prefix + allocation.state.value, allocation.state.value)
                name = titles.get(device, device or allocation.owner)
                rows.append(f"| {format_id(sender)} | {name} | {profile or '-'} | {state} |")
                if allocation.state is SenderState.BLOCKED:
                    blocked.append(format_id(sender))
        schema: dict[Any, Any] = {}
        if blocked:
            schema[vol.Optional("free", default=[])] = SelectSelector(
                SelectSelectorConfig(options=blocked, multiple=True, mode=SelectSelectorMode.LIST)
            )
        return self.async_show_form(
            step_id="senders",
            data_schema=vol.Schema(schema),
            description_placeholders={
                "free": str(free),
                "size": str(sum(store.pool.size for store in stores)),
                "rows": "\n".join(rows) or "| - | - | - | - |",
            },
        )

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
