"""Gateway models: each fixes the serial protocol (ESP2/ESP3) and its defaults."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Protocol(StrEnum):
    ESP2 = "esp2"
    ESP3 = "esp3"


@dataclass(frozen=True, slots=True)
class GatewayModel:
    key: str
    name: str
    protocol: Protocol
    baudrate: int | None  # None: user chooses (generic models)
    usb: bool  # USB device; reachable via ser2net too
    default_port: int | None = None  # TCP port of network gateways
    reads_base_id: bool = True


MODELS: dict[str, GatewayModel] = {
    m.key: m
    for m in (
        GatewayModel("fam_usb", "Eltako FAM-USB", Protocol.ESP2, 9600, usb=True),
        GatewayModel("fgw14_usb", "Eltako FGW14-USB", Protocol.ESP2, 57600, usb=True),
        GatewayModel(
            "mgw_eth", "PioTek MGW-ETH", Protocol.ESP3, None, usb=False, default_port=5100
        ),
        GatewayModel(
            "symcon_lan",
            "Symcon EnOcean LAN Gateway",
            Protocol.ESP3,
            None,
            usb=False,
            default_port=5000,
        ),
        GatewayModel("esp3", "Generic ESP3", Protocol.ESP3, 57600, usb=True),
        GatewayModel("esp2", "Generic ESP2", Protocol.ESP2, None, usb=True),
    )
}
