"""Gateway config flow."""

from unittest.mock import patch

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.enocean_eltako.const import DOMAIN
from custom_components.enocean_eltako.protocol.models import Protocol

from .fake_gateway import FakeGateway

pytestmark = pytest.mark.usefixtures("socket_enabled")

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
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Eltako FAM-USB FF-B7-44-80"
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
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "PioTek MGW-ETH FF-8A-1B-00"


async def test_duplicate_base_id_aborts(hass: HomeAssistant, fake_esp2) -> None:
    MockConfigEntry(domain=DOMAIN, unique_id="FF-B7-44-80").add_to_hass(hass)
    result = await _start(hass, "fam_usb")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "tcp"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"host": "127.0.0.1", "port": fake_esp2.port}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


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
    assert set(result["data_schema"].schema) == {"message_delay", "mode"}
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"message_delay": 25.0, "mode": "on_demand"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {"message_delay": 25, "mode": "on_demand"}


async def test_options_flow_radio_gateway_has_no_mode(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, data={"model": "fam_usb"})
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert set(result["data_schema"].schema) == {"message_delay"}
