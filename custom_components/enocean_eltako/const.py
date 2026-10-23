"""Constants for the EnOcean Eltako integration."""

from typing import Final

DOMAIN: Final = "enocean_eltako"

CONF_MODEL: Final = "model"
CONF_EEP: Final = "eep"  # device added by EEP: its "A5-04-02:std" reference
CONF_CUSTOM: Final = "custom"  # I8: id of the user's device definition
CONF_MODEL_NAME: Final = "model_name"  # the device's type as the user picked it, display only
# Connection dict under "device": HA's usb integration finds the port at ("device", "path")
# and shows which entry uses it.
CONF_DEVICE: Final = "device"
CONF_BASE_ID: Final = "base_id"
CONF_PATH: Final = "path"
CONF_BAUDRATE: Final = "baudrate"

BAUDRATES: Final = (9600, 57600, 115200)
CONF_BUS_GROUP: Final = "bus_group"
CONF_MODE: Final = "mode"
CONF_REPEATER: Final = "repeater"  # ESP3 gateways: unchanged | off | 1 | 2
REPEATER_UNCHANGED: Final = "unchanged"
REPEATER_LEVELS: Final = {"off": 0, "1": 1, "2": 2}
CONF_MESSAGE_DELAY: Final = "message_delay"  # milliseconds between telegrams
CONF_DISCOVERY: Final = "discovery"  # offer unknown senders as discovered devices
CONF_PROXY_REPLAY: Final = "proxy_replay"  # TCP gateway is the Device Proxy app: replay
# telegrams missed while HA was away, each with its reception time
PROXY_REPLAY_REQUEST: Final = b"EOPX REPLAY TS\n"
CONF_ENTITY_PREFIX: Final = "entity_prefix"  # new entity IDs start with eno_gw<number>
CONF_GATEWAY_NUMBER: Final = "gateway_number"
CONF_RENAME_ENTITIES: Final = "rename_entities"  # form only: rename existing entities now

MODE_ALWAYS: Final = "always"
MODE_ON_DEMAND: Final = "on_demand"  # bus gateway connected only for failover / import
DEFAULT_MESSAGE_DELAY: Final = 10

SUBENTRY_DEVICE: Final = "device"
CONF_DEVICE_ID: Final = "device_id"
CONF_SENDER_ID: Final = "sender_id"
CONF_SENDERS: Final = "senders"  # [{"profile": "controller", "sender_id": "FF-B7-44-81"}, ...]
CONF_PROFILE: Final = "profile"
CONF_NAME: Final = "name"
SUBENTRY_SCHEMA: Final = 5  # version of the device subentry data (subentries have none)
