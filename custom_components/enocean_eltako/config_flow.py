"""Config flow for the EnOcean Eltako integration."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import DOMAIN


class EnOceanEltakoConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for one gateway."""

    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Gateway setup is implemented in phase 1; until then the flow stops here."""
        return self.async_abort(reason="not_implemented")
