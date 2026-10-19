"""Constants for the EnOcean Eltako integration."""

from typing import Final

DOMAIN: Final = "enocean_eltako"

CONF_MODEL: Final = "model"
# Connection dict under "device": HA's usb integration finds the port at ("device", "path")
# and shows which entry uses it.
CONF_DEVICE: Final = "device"
CONF_BASE_ID: Final = "base_id"
CONF_PATH: Final = "path"
CONF_BAUDRATE: Final = "baudrate"

BAUDRATES: Final = (9600, 57600, 115200)
