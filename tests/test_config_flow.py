"""Gateway config flow."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.enocean_eltako.config_flow import CannotConnect
from custom_components.enocean_eltako.const import DOMAIN
from custom_components.enocean_eltako.protocol.models import Protocol

from .fake_gateway import FakeGateway

pytestmark = pytest.mark.usefixtures("socket_enabled")

PREFIX = {"entity_prefix", "gateway_number", "rename_entities"}  # gateway prefix in entity IDs

PORT = "/dev/serial/by-id/usb-EnOcean_FAM-USB"


@pytest.fixture(autouse=True)
def no_setup():
    with patch("custom_components.enocean_eltako.async_setup_entry", return_value=True) as m:
        yield m


@pytest.fixture
async def fake_esp2():
    server = await FakeGateway(Protocol.ESP2).start()
    yield server
    await server.stop()


async def _start(hass: HomeAssistant, model: str):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    return await hass.config_entries.flow.async_configure(result["flow_id"], {"model": model})


async def _name(hass: HomeAssistant, result, name: str | None = None):
    """Last step: keep the suggested gateway name or enter one."""
    assert result["step_id"] == "name"
    default = next(iter(result["data_schema"].schema)).default()
    return await hass.config_entries.flow.async_configure(
        result["flow_id"], {"name": name or default}
    )


async def test_fam_usb_via_ser2net_reads_base_id(hass: HomeAssistant, fake_esp2) -> None:
    result = await _start(hass, "fam_usb")
    assert result["type"] is FlowResultType.MENU
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "tcp"}
    )
    assert result["step_id"] == "tcp"
    assert result["description_placeholders"]["baudrate"] == "9600"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"host": "127.0.0.1", "port": fake_esp2.port}
    )
    result = await _name(hass, result)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Eltako FAM-USB"
    assert result["data"] == {
        "model": "fam_usb",
        "device": {"type": "tcp", "host": "127.0.0.1", "port": fake_esp2.port},
        "base_id": "FF-B7-44-80",
    }
    assert result["result"].unique_id == "FF-B7-44-80"


async def test_fam_usb_serial(hass: HomeAssistant, fake_esp2) -> None:
    result = await _start(hass, "fam_usb")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "serial"}
    )
    assert result["step_id"] == "serial"
    assert "baudrate" not in result["data_schema"].schema  # fixed by the model
    assert result["data_schema"].schema["path"].selector_type == "serial_port"
    with patch(
        "custom_components.enocean_eltako.config_flow.probe_gateway", return_value=0xFFB74480
    ) as probe:
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"path": PORT})
    result = await _name(hass, result)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["device"] == {
        "type": "serial",
        "path": PORT,
        "baudrate": 9600,
    }
    assert str(probe.call_args.args[1]) == f"{PORT} @ 9600"


async def test_generic_esp2_asks_for_baudrate(hass: HomeAssistant) -> None:
    result = await _start(hass, "esp2")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "serial"}
    )
    assert "baudrate" in result["data_schema"].schema


async def test_cannot_connect_shows_error(hass: HomeAssistant) -> None:
    server = await FakeGateway(Protocol.ESP2).start()
    port = server.port
    await server.stop()
    result = await _start(hass, "fam_usb")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "tcp"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"host": "127.0.0.1", "port": port}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_base_id_entered_when_gateway_is_silent(hass: HomeAssistant, fake_esp2) -> None:
    fake_esp2.base_id = None
    result = await _start(hass, "fgw14_usb")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "tcp"}
    )
    with patch(
        "custom_components.enocean_eltako.protocol.gateway.Gateway.read_base_id", return_value=None
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"host": "127.0.0.1", "port": fake_esp2.port}
        )
    assert result["step_id"] == "base_id"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"base_id": "FF-AA-80-01"}
    )
    assert result["errors"] == {"base_id": "invalid_base_id"}
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"base_id": "ff:aa:80:00"}
    )
    result = await _name(hass, result)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["base_id"] == "FF-AA-80-00"
    assert result["data"]["device"]["type"] == "tcp"


async def test_network_gateway_esp3_skips_menu(hass: HomeAssistant) -> None:
    server = await FakeGateway(Protocol.ESP3, base_id=0xFF8A1B00).start()
    try:
        result = await _start(hass, "mgw_eth")
        assert result["step_id"] == "network"
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"host": "127.0.0.1", "port": server.port}
        )
    finally:
        await server.stop()
    result = await _name(hass, result)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "PioTek MGW-ETH"


async def test_duplicate_base_id_needs_confirmation(hass: HomeAssistant, fake_esp2) -> None:
    MockConfigEntry(domain=DOMAIN, unique_id="FF-B7-44-80", title="Funk 1").add_to_hass(hass)
    result = await _start(hass, "fam_usb")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "tcp"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"host": "127.0.0.1", "port": fake_esp2.port}
    )
    assert result["step_id"] == "same_base_id"
    assert result["description_placeholders"] == {"base_id": "FF-B7-44-80", "gateways": "Funk 1"}
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    result = await _name(hass, result)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == "FF-B7-44-80#2"


async def test_fam14_joins_bus_group_of_fgw14_on_demand(hass: HomeAssistant, fake_esp2) -> None:
    MockConfigEntry(
        domain=DOMAIN,
        title="Eltako FGW14-USB FF-AA-80-00",
        unique_id="FF-AA-80-00",
        data={"model": "fgw14_usb", "bus_group": "b1"},
    ).add_to_hass(hass)
    result = await _start(hass, "fam14")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "tcp"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"host": "127.0.0.1", "port": fake_esp2.port}
    )
    assert result["step_id"] == "base_id"  # FAM14 does not report it over ESP2
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"base_id": "FF-80-80-00"}
    )
    assert result["step_id"] == "bus_group"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"bus_group": "b1"})
    result = await _name(hass, result)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["bus_group"] == "b1"
    assert result["options"] == {"message_delay": 10, "mode": "on_demand"}


async def test_first_bus_gateway_creates_new_group(hass: HomeAssistant, fake_esp2) -> None:
    result = await _start(hass, "fam14")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "tcp"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"host": "127.0.0.1", "port": fake_esp2.port}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"base_id": "FF-80-80-00"}
    )
    result = await _name(hass, result)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert len(result["data"]["bus_group"]) == 8
    assert result["options"]["mode"] == "always"


async def test_options_flow(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"model": "fam14", "bus_group": "b1"},
        options={"message_delay": 10, "mode": "always"},
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["step_id"] == "settings"  # no menu: sender IDs and takeover are in the panel
    assert set(result["data_schema"].schema) == {"message_delay", "discovery", "mode", *PREFIX}
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"message_delay": 25.0, "discovery": False, "mode": "on_demand"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {
        "message_delay": 25,
        "discovery": False,
        "mode": "on_demand",
        "entity_prefix": False,
        "gateway_number": 1,
    }


async def test_options_flow_radio_gateway_has_no_mode(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, data={"model": "fam_usb"})
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert set(result["data_schema"].schema) == {"message_delay", "discovery", *PREFIX}


def _zeroconf(host: str, port: int):
    from ipaddress import ip_address

    from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

    return ZeroconfServiceInfo(
        ip_address=ip_address(host),
        ip_addresses=[ip_address(host)],
        port=port,
        hostname="mgw.local.",
        type="_bsc-sc-socket._tcp.local.",
        name="MGW._bsc-sc-socket._tcp.local.",
        properties={},
    )


async def test_zeroconf_discovers_mgw(hass: HomeAssistant) -> None:
    server = await FakeGateway(Protocol.ESP3, base_id=0xFF8A1B00).start()
    try:
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_ZEROCONF},
            data=_zeroconf("127.0.0.1", server.port),
        )
        assert result["step_id"] == "zeroconf_confirm"
        assert result["description_placeholders"]["connection"] == f"127.0.0.1:{server.port}"
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    finally:
        await server.stop()
    result = await _name(hass, result)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "PioTek MGW-ETH"
    assert result["result"].unique_id == "FF-8A-1B-00"
    assert result["data"]["model"] == "mgw_eth"


async def test_zeroconf_known_host_aborts(hass: HomeAssistant) -> None:
    MockConfigEntry(
        domain=DOMAIN,
        unique_id="FF-8A-1B-00",
        data={"model": "mgw_eth", "device": {"type": "tcp", "host": "127.0.0.1", "port": 5100}},
    ).add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=_zeroconf("127.0.0.1", 5100),
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_zeroconf_gateway_behind_the_proxy_aborts(hass: HomeAssistant) -> None:
    """An MGW-ETH the Device Proxy app holds is not offered again on its own address."""
    MockConfigEntry(
        domain=DOMAIN,
        unique_id="FF-8A-1B-00",
        data={"model": "mgw_eth", "device": {"type": "tcp", "host": "proxy-host", "port": 9100}},
        options={"proxy_replay": True},
    ).add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=_zeroconf("192.168.1.50", 5100),
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_zeroconf_new_address_updates_entry(hass: HomeAssistant) -> None:
    server = await FakeGateway(Protocol.ESP3, base_id=0xFF8A1B00).start()
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="FF-8A-1B-00",
        data={"model": "mgw_eth", "device": {"type": "tcp", "host": "192.0.2.7", "port": 5100}},
    )
    entry.add_to_hass(hass)
    try:
        # discovery-update-info: no confirmation, the base ID identifies the gateway
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_ZEROCONF},
            data=_zeroconf("127.0.0.1", server.port),
        )
    finally:
        await server.stop()
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert entry.data["device"] == {"type": "tcp", "host": "127.0.0.1", "port": server.port}


async def test_zeroconf_confirm_cannot_connect(hass: HomeAssistant) -> None:
    server = await FakeGateway(Protocol.ESP3).start()
    port = server.port
    await server.stop()
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=_zeroconf("127.0.0.1", port),
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["step_id"] == "zeroconf_confirm"
    assert result["errors"] == {"base": "cannot_connect"}


async def test_gateway_gets_the_entered_name(hass: HomeAssistant, fake_esp2) -> None:
    result = await _start(hass, "fam_usb")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "tcp"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"host": "127.0.0.1", "port": fake_esp2.port}
    )
    assert result["description_placeholders"]["base_id"] == "FF-B7-44-80"
    result = await _name(hass, result, "  Funk Erdgeschoss ")
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Funk Erdgeschoss"


def _configured(port: int, base_id: str = "FF-B7-44-80", model: str = "fam_usb") -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title="Funk",
        unique_id=base_id,
        version=1,
        minor_version=2,
        data={
            "model": model,
            "device": {"type": "tcp", "host": "10.0.0.9", "port": port},
            "base_id": base_id,
        },
    )


async def _reconfigure(hass: HomeAssistant, entry: MockConfigEntry, model: str | None = None):
    """Start the reconfigure flow and answer its model step (default: keep the model)."""
    result = await entry.start_reconfigure_flow(hass)
    assert result["step_id"] == "reconfigure"
    return await hass.config_entries.flow.async_configure(
        result["flow_id"], {"model": model or entry.data["model"]}
    )


async def test_reconfigure_changes_the_connection(hass: HomeAssistant, fake_esp2) -> None:
    entry = _configured(4000)
    entry.add_to_hass(hass)
    result = await _reconfigure(hass, entry)
    assert result["type"] is FlowResultType.MENU
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "tcp"}
    )
    host = next(k for k in result["data_schema"].schema if k == "host")
    assert host.description["suggested_value"] == "10.0.0.9"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"host": "127.0.0.1", "port": fake_esp2.port}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data["device"] == {"type": "tcp", "host": "127.0.0.1", "port": fake_esp2.port}
    assert entry.title == "Funk"


async def test_reconfigure_refuses_another_gateway(hass: HomeAssistant, fake_esp2) -> None:
    entry = _configured(4000, base_id="FF-80-00-00")
    entry.add_to_hass(hass)
    result = await _reconfigure(hass, entry)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "tcp"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"host": "127.0.0.1", "port": fake_esp2.port}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "wrong_gateway"
    assert entry.data["device"]["port"] == 4000


async def test_reconfigure_swaps_usb_for_a_network_gateway(hass: HomeAssistant, fake_esp2) -> None:
    """FAM-USB replaced by a network gateway of the same base ID: model and connection change."""
    entry = _configured(4000)
    entry.add_to_hass(hass)
    with patch(
        "custom_components.enocean_eltako.config_flow.probe_gateway",
        AsyncMock(return_value=0xFFB74480),
    ):
        result = await _reconfigure(hass, entry, "mgw_eth")
        assert result["step_id"] == "network"
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"host": "10.0.0.50", "port": 5100}
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data["model"] == "mgw_eth"
    assert entry.data["device"] == {"type": "tcp", "host": "10.0.0.50", "port": 5100}
    assert entry.data["base_id"] == "FF-B7-44-80"
    assert entry.unique_id == "FF-B7-44-80"


async def test_reconfigure_model_change_refuses_another_base_id(hass: HomeAssistant) -> None:
    entry = _configured(4000)
    entry.add_to_hass(hass)
    with patch(
        "custom_components.enocean_eltako.config_flow.probe_gateway",
        AsyncMock(return_value=0xFF800000),
    ):
        result = await _reconfigure(hass, entry, "mgw_eth")
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"host": "10.0.0.50", "port": 5100}
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "wrong_gateway"
    assert entry.data["model"] == "fam_usb"
    assert entry.data["device"]["port"] == 4000


async def test_reconfigure_offers_only_models_of_the_same_kind(hass: HomeAssistant) -> None:
    entry = _configured(4000)
    entry.add_to_hass(hass)
    result = await entry.start_reconfigure_flow(hass)
    selector = next(iter(result["data_schema"].schema.values()))
    options = selector.config["options"]
    assert "mgw_eth" in options and "fam_usb" in options
    assert "fam14" not in options and "fgw14_usb" not in options


async def test_reconfigure_fam14_keeps_its_base_id(hass: HomeAssistant, fake_esp2) -> None:
    entry = _configured(4000, base_id="FF-AA-00-00", model="fam14")
    entry.add_to_hass(hass)
    result = await _reconfigure(hass, entry)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "tcp"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"host": "127.0.0.1", "port": fake_esp2.port}
    )
    assert result["reason"] == "reconfigure_successful"
    assert entry.data["base_id"] == "FF-AA-00-00"


async def test_device_proxy_app_discovery(hass: HomeAssistant) -> None:
    """Phase 6: the Device Proxy app announces a gateway; replay is switched on."""
    from homeassistant.helpers.service_info.hassio import HassioServiceInfo

    server = await FakeGateway(Protocol.ESP2).start()
    info = HassioServiceInfo(
        config={
            "host": "127.0.0.1",
            "replay": True,
            "app": "device_proxy",
            "gateways": [{"name": "FAM-USB", "port": server.port, "protocol": "esp2"}],
        },
        name="Device Proxy",
        slug="abc_device_proxy",
        uuid="1234",
    )
    try:
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_HASSIO}, data=info
        )
        assert result["step_id"] == "proxy_confirm"
        (marker, selector), *_ = result["data_schema"].schema.items()
        assert "fam_usb" in selector.config["options"]
        assert "mgw_eth" not in selector.config["options"]  # ESP2 models only
        assert marker.default() == "fam_usb"  # guessed from the gateway's name
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"model": "fam_usb"}
        )
    finally:
        await server.stop()
    result = await _name(hass, result)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["device"] == {"type": "tcp", "host": "127.0.0.1", "port": server.port}
    assert result["options"]["proxy_replay"] is True

    again = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_HASSIO}, data=info
    )
    assert again["reason"] == "already_configured"


@pytest.mark.parametrize(
    ("status", "asks"),
    [
        ({"gateways": [{"port": 0, "base_id": "FF-B7-44-80"}]}, False),  # the app knows it
        ({"gateways": [{"port": 0, "base_id": None}]}, True),  # the app does not: ask
        ({"gateways": []}, True),
    ],
)
async def test_device_proxy_app_base_id_from_status(
    hass: HomeAssistant, aioclient_mock, status: dict, asks: bool
) -> None:
    """A gateway that does not answer the base ID read: the app's status has it."""
    from homeassistant.helpers.service_info.hassio import HassioServiceInfo

    server = await FakeGateway(Protocol.ESP2, base_id=None).start()
    for gateway in status["gateways"]:
        gateway["port"] = server.port
    aioclient_mock.get("http://127.0.0.1:9199/api/status", json=status)
    info = HassioServiceInfo(
        config={
            "host": "127.0.0.1",
            "status_port": 9199,
            "replay": True,
            "gateways": [{"name": "FAM-USB", "port": server.port, "protocol": "esp2"}],
        },
        name="Device Proxy",
        slug="abc_device_proxy",
        uuid="1234",
    )
    try:
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_HASSIO}, data=info
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"model": "fam_usb"}
        )
    finally:
        await server.stop()
    assert result["step_id"] == ("base_id" if asks else "name")


@pytest.mark.parametrize(
    ("announced", "asks"),
    [("fgw14_usb", False), ("mgw_eth", True), ("nope", True)],  # other protocol, unknown: ask
)
async def test_device_proxy_app_model_announced(
    hass: HomeAssistant, announced: str, asks: bool
) -> None:
    """A model in the announcement skips the question; one that does not fit is ignored."""
    from homeassistant.helpers.service_info.hassio import HassioServiceInfo

    server = await FakeGateway(Protocol.ESP2).start()
    info = HassioServiceInfo(
        config={
            "host": "127.0.0.1",
            "replay": True,
            "gateways": [
                {"name": "Bus", "port": server.port, "protocol": "esp2", "model": announced}
            ],
        },
        name="Device Proxy",
        slug="abc_device_proxy",
        uuid="1234",
    )
    try:
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_HASSIO}, data=info
        )
    finally:
        await server.stop()
    if asks:
        assert result["step_id"] == "proxy_confirm"
    else:
        assert result.get("step_id") != "proxy_confirm"
        assert result["step_id"] == "name"  # the model is set, on to the name


@pytest.mark.parametrize(
    "config",
    [
        {"gateways": [{"port": 9001}]},  # no host
        {"host": "127.0.0.1", "gateways": [{"name": "x"}]},  # no port
        {"host": "127.0.0.1", "gateways": [{"port": "x"}]},
        {"host": "127.0.0.1", "gateways": [{"port": 9001, "protocol": "esp9"}]},
    ],
)
async def test_device_proxy_app_discovery_malformed(hass: HomeAssistant, config: dict) -> None:
    from homeassistant.helpers.service_info.hassio import HassioServiceInfo

    info = HassioServiceInfo(config=config, name="Device Proxy", slug="abc", uuid="1")
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_HASSIO}, data=info
    )
    assert result["reason"] == "invalid_discovery_info"


async def test_device_proxy_app_discovers_all_gateways(hass: HomeAssistant) -> None:
    """One app message lists every gateway; each unconfigured one gets its own flow."""
    from homeassistant.helpers.service_info.hassio import HassioServiceInfo

    MockConfigEntry(
        domain=DOMAIN,
        data={"device": {"type": "tcp", "host": "abc-device-proxy", "port": 9100}},
    ).add_to_hass(hass)
    info = HassioServiceInfo(
        config={
            "host": "abc-device-proxy",
            "status_port": 9199,
            "replay": True,
            "gateways": [
                {"name": "FAM", "port": 9100, "protocol": "esp2"},
                {"name": "MGW-LAN", "port": 9101, "protocol": "esp3"},
                {"name": "USB 300", "port": 9102, "protocol": "esp3"},
            ],
        },
        name="Device Proxy",
        slug="abc_device_proxy",
        uuid="1234",
    )
    with patch(
        "custom_components.enocean_eltako.config_flow.probe_gateway",
        side_effect=CannotConnect("no such host"),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_HASSIO}, data=info
        )
        await hass.async_block_till_done()
    assert result["step_id"] == "proxy_confirm"
    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert sorted(f["context"]["unique_id"] for f in flows) == [
        "proxy_abc-device-proxy_9101",
        "proxy_abc-device-proxy_9102",
    ]
    names = sorted(f["context"]["title_placeholders"]["name"] for f in flows)
    assert names == ["MGW-LAN (Device Proxy)", "USB 300 (Device Proxy)"]


async def test_device_proxy_app_port_change_updates_entry(hass: HomeAssistant) -> None:
    """discovery-update-info: the app moved a gateway to another port."""
    from homeassistant.helpers.service_info.hassio import HassioServiceInfo

    server = await FakeGateway(Protocol.ESP2).start()
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="FF-B7-44-80",
        data={"model": "fam_usb", "device": {"type": "tcp", "host": "127.0.0.1", "port": 1}},
    )
    entry.add_to_hass(hass)
    info = HassioServiceInfo(
        config={
            "host": "127.0.0.1",
            "replay": True,
            "gateways": [{"name": "FAM", "port": server.port, "protocol": "esp2"}],
        },
        name="Device Proxy",
        slug="abc_device_proxy",
        uuid="1234",
    )
    try:
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_HASSIO}, data=info
        )
    finally:
        await server.stop()
    assert result["reason"] == "already_configured"
    assert entry.data["device"]["port"] == server.port


async def test_device_proxy_under_a_new_address_keeps_the_entry(hass: HomeAssistant) -> None:
    """A gateway set up through the Device Proxy comes back under another address (the app
    installed again, from another repository): the entry is found by the base ID and gets
    the new address, no new gateway is offered."""
    from homeassistant.helpers.service_info.hassio import HassioServiceInfo

    server = await FakeGateway(Protocol.ESP2).start()
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="FF-B7-44-80",
        data={
            "model": "fam_usb",
            "device": {"type": "tcp", "host": "abc-device-proxy", "port": 9100},
            "proxy_status_port": 9199,
        },
        options={"proxy_replay": True},
    )
    entry.add_to_hass(hass)
    info = HassioServiceInfo(
        config={
            "host": "127.0.0.1",
            "status_port": 9299,
            "replay": True,
            "app": "device_proxy",
            "gateways": [{"name": "FAM-USB", "port": server.port, "protocol": "esp2"}],
        },
        name="Device Proxy",
        slug="def_device_proxy",
        uuid="5678",
    )
    try:
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_HASSIO}, data=info
        )
    finally:
        await server.stop()
    assert result["reason"] == "already_configured"
    assert entry.data["device"] == {"type": "tcp", "host": "127.0.0.1", "port": server.port}
    assert entry.data["proxy_status_port"] == 9299


async def test_a_new_gateway_of_the_device_proxy(hass: HomeAssistant) -> None:
    from homeassistant.helpers.service_info.hassio import HassioServiceInfo

    info = HassioServiceInfo(
        config={
            "host": "abc-device-proxy",
            "status_port": 9199,
            "replay": True,
            "app": "device_proxy",
            "gateways": [{"name": "MGW", "port": 9101, "protocol": "esp3"}],
        },
        name="Device Proxy",
        slug="abc_device_proxy",
        uuid="5678",
    )
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_HASSIO}, data=info
    )
    assert result["step_id"] == "proxy_confirm"
    (flow,) = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert flow["context"]["title_placeholders"]["name"] == "MGW (Device Proxy)"
