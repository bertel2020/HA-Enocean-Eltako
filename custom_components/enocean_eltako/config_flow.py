"""Config flow for the EnOcean Eltako integration: one entry per gateway."""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

import voluptuous as vol
from homeassistant.config_entries import (
    SOURCE_RECONFIGURE,
    SOURCE_ZEROCONF,
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers.selector import (
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
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .const import (
    BAUDRATES,
    CONF_BASE_ID,
    CONF_BAUDRATE,
    CONF_BUS_GROUP,
    CONF_DEVICE,
    CONF_MESSAGE_DELAY,
    CONF_MODE,
    CONF_MODEL,
    CONF_NAME,
    CONF_PATH,
    DEFAULT_MESSAGE_DELAY,
    DOMAIN,
    MODE_ALWAYS,
    MODE_ON_DEMAND,
)
from .protocol.gateway import Gateway
from .protocol.ids import format_id, is_valid_base_id, parse_id
from .protocol.models import MODELS, GatewayModel
from .protocol.transport import Connection, SerialConnection, TcpConnection
from .subentry_flow import SUBENTRY_FLOWS

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


class EnOceanEltakoConfigFlow(ConfigFlow, domain=DOMAIN):
    """Add a gateway: model, connection, connection test, base ID."""

    VERSION = 1
    MINOR_VERSION = 2  # 1.2: device subentries list their senders (schema 2)

    def __init__(self) -> None:
        self._model: GatewayModel | None = None
        self._connection: Connection | None = None
        self._base_id = 0
        self._data: dict[str, Any] = {}
        self._options: dict[str, Any] = {}
        self._suggested: dict[str, Any] = {}  # reconfigure: the current connection

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
        self._model = model
        self._connection = TcpConnection(host, port)
        self.context["title_placeholders"] = {"name": f"{model.name} ({host})"}
        return await self.async_step_zeroconf_confirm()

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
        await self.async_set_unique_id(format_id(base_id), raise_on_progress=False)
        if self.source == SOURCE_RECONFIGURE:
            self._abort_if_unique_id_mismatch(reason="wrong_gateway")
            return self._async_update_connection()
        # a rediscovered gateway with a new address updates its entry
        updates = (
            {CONF_DEVICE: self._connection.as_dict()}
            if self.source == SOURCE_ZEROCONF and self._connection is not None
            else None
        )
        self._abort_if_unique_id_configured(updates=updates)
        self._base_id = base_id
        if self._model.bus:
            return await self.async_step_bus_group()
        return self._async_create_entry()

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


class EnOceanEltakoOptionsFlow(OptionsFlowWithReload):
    """Runtime options: send spacing and, for bus gateways, always vs on demand."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
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
        if MODELS[self.config_entry.data[CONF_MODEL]].bus:
            schema[vol.Required(CONF_MODE, default=MODE_ALWAYS)] = SelectSelector(
                SelectSelectorConfig(
                    options=[MODE_ALWAYS, MODE_ON_DEMAND],
                    translation_key=CONF_MODE,
                    mode=SelectSelectorMode.LIST,
                )
            )
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(schema), self.config_entry.options
            ),
        )
