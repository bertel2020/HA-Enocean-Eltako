"""Constants for the EnOcean Eltako integration."""

from typing import Final

DOMAIN: Final = "enocean_eltako"

CONF_MODEL: Final = "model"
CONF_EEP: Final = "eep"  # device added by EEP: its "A5-04-02:std" reference
# Connection dict under "device": HA's usb integration finds the port at ("device", "path")
# and shows which entry uses it.
CONF_DEVICE: Final = "device"
CONF_BASE_ID: Final = "base_id"
CONF_PATH: Final = "path"
CONF_BAUDRATE: Final = "baudrate"

BAUDRATES: Final = (9600, 57600, 115200)
CONF_BUS_GROUP: Final = "bus_group"
CONF_MODE: Final = "mode"
CONF_MESSAGE_DELAY: Final = "message_delay"  # milliseconds between telegrams

MODE_ALWAYS: Final = "always"
MODE_ON_DEMAND: Final = "on_demand"  # bus gateway connected only for failover / import
DEFAULT_MESSAGE_DELAY: Final = 10

SUBENTRY_DEVICE: Final = "device"
SUBENTRY_IMPORT: Final = "import"  # one-time import of the old eltako YAML
CONF_DEVICE_ID: Final = "device_id"
CONF_SENDER_ID: Final = "sender_id"
CONF_SENDERS: Final = "senders"  # [{"profile": "controller", "sender_id": "FF-B7-44-81"}, ...]
CONF_PROFILE: Final = "profile"
CONF_NAME: Final = "name"
SUBENTRY_SCHEMA: Final = 2  # version of the device subentry data (subentries have none)
