"""Constants for the EnOcean Eltako integration."""

from typing import Final

DOMAIN: Final = "enocean_eltako"

CONF_MODEL: Final = "model"
CONF_CONNECTION: Final = "connection"
CONF_BASE_ID: Final = "base_id"
CONF_PATH: Final = "path"
CONF_BAUDRATE: Final = "baudrate"

BAUDRATES: Final = (9600, 57600, 115200)
