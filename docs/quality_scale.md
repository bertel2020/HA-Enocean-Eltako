# Quality scale

[Deutsch](quality_scale.de.md)

Self-assessment against the [Home Assistant integration quality scale](https://developers.home-assistant.io/docs/core/integration-quality-scale/)
(phase 5). Custom integrations are not graded by Home Assistant; this list tracks what is
done and what is left.

Status: **Bronze, Silver, Gold and Platinum complete** (self-assessment).

## Bronze

| Rule | Status | Where |
| --- | --- | --- |
| action-setup | done | services registered in `async_setup` (`services.py`) |
| appropriate-polling | done | local push; only the gateway counters poll |
| brands | done | `brand/` |
| common-modules | done | `entity.py`, `device.py`, `hub.py`, `gateway_entity.py` |
| config-flow-test-coverage | done | `tests/test_config_flow.py`, `tests/test_devices.py` |
| config-flow | done | gateway entry, device subentries, options |
| dependency-transparency | done | no requirements, own protocol layer |
| docs-actions | done | README "Actions" |
| docs-high-level-description | done | README intro |
| docs-installation-instructions | done | README "Installation" |
| docs-removal-instructions | done | README "Removal" |
| entity-event-setup | done | listeners in `async_added_to_hass` |
| entity-unique-id | done | base ID + device ID + key |
| has-entity-name | done | all entities |
| runtime-data | done | `GatewayRuntime` in `entry.runtime_data` |
| test-before-configure | done | connection test and base ID in the config flow |
| test-before-setup | done | `ConfigEntryNotReady` when the gateway does not answer |
| unique-config-entry | done | base ID as unique ID |

## Silver

| Rule | Status | Where |
| --- | --- | --- |
| action-exceptions | done | translated `HomeAssistantError` for offline gateways and positions |
| config-entry-unloading | done | `async_unload_entry` closes gateway and queue |
| docs-configuration-parameters | done | README "Gateway options and repairs" |
| docs-installation-parameters | done | README "Supported devices" and the flow texts |
| entity-unavailable | done | option per device: unavailable when silent (E5) |
| integration-owner | done | `codeowners` in the manifest |
| log-when-unavailable | done | one warning per gateway outage, info when it is back |
| parallel-updates | done | `PARALLEL_UPDATES = 0` on every platform (send queue serialises) |
| reauthentication-flow | exempt | no credentials |
| test-coverage | done | over 95 %; CI fails below 95 % (`pytest --cov=custom_components/enocean_eltako --cov-fail-under=95`) |

## Gold

| Rule | Status | Where |
| --- | --- | --- |
| devices | done | one device per gateway and per subentry, via the gateway |
| diagnostics | done | `diagnostics.py` |
| discovery | done | zeroconf (MGW-ETH), Device Proxy app (Supervisor), discovered EnOcean senders (listed under Add device) |
| discovery-update-info | done | a known MGW-ETH with a new address, or a proxied gateway on a new port, is identified by its base ID and updated without confirmation (`test_zeroconf_new_address_updates_entry`, `test_device_proxy_app_port_change_updates_entry`) |
| docs-data-update | done | local push, gateway counters every 30 s |
| docs-examples | done | blueprints |
| docs-known-limitations | done | README "Known limitations" |
| docs-supported-devices | done | `docs/devices.md` (generated) |
| docs-supported-functions | done | README, `docs/devices.md` |
| docs-troubleshooting | done | README "Troubleshooting" |
| docs-use-cases | done | README, virtual sensors, blueprints |
| dynamic-devices | done | subentries added and removed at runtime |
| entity-category | done | diagnostics and config entities |
| entity-device-class | done | where a device class exists |
| entity-disabled-by-default | done | noisy diagnostics disabled |
| entity-translations | done | `translations/` |
| exception-translations | done | `exceptions` in the translations |
| icon-translations | done | `icons.json` for every translated entity, states and actions |
| reconfiguration-flow | done | gateway and device reconfigure |
| repair-issues | done | disconnected gateway, silent device, base ID, slow bus |
| stale-devices | done | removing a subentry removes its device and releases its senders |

## Platinum

| Rule | Status | Where |
| --- | --- | --- |
| async-dependency | done | asyncio streams, `serialx` |
| inject-websession | exempt | no HTTP |
| strict-typing | done | `mypy --strict` in CI (`pyproject.toml`), Home Assistant re-exports allowed |

## Generated EEP profiles

Phase 5 generates every standard profile of the EnOcean Alliance EEP Viewer (318) and tests
them against the official test containers. For 34 profiles outside the catalog the
containers and the generic decoder disagree (several cases that the data cannot tell apart,
e.g. A5-3F-00 or the A5-20 valves, or errors in the containers); they are marked
`UNVERIFIED_PROFILES` in `tests/protocol/test_eep_official.py` until a profile is checked.
