"""Config flow for iNELS Cloud."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import InelsCloudAuthError, InelsCloudClient, InelsCloudError
from .const import CONF_ACCESS_TOKEN, CONF_PASSWORD, CONF_REFRESH_TOKEN, CONF_USERNAME, DOMAIN


class InelsCloudConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle iNELS Cloud configuration."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial setup."""
        errors: dict[str, str] = {}

        if user_input:
            session = async_get_clientsession(self.hass)
            try:
                tokens = await InelsCloudClient.async_login(
                    session,
                    user_input[CONF_USERNAME],
                    user_input[CONF_PASSWORD],
                )
            except InelsCloudAuthError:
                errors["base"] = "invalid_auth"
            except InelsCloudError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(
                    user_input[CONF_USERNAME].lower()
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_USERNAME],
                    data={
                        CONF_USERNAME: user_input[CONF_USERNAME],
                        CONF_ACCESS_TOKEN: tokens["access_token"],
                        CONF_REFRESH_TOKEN: tokens["refresh_token"],
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle reauthentication."""
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()

        if user_input:
            session = async_get_clientsession(self.hass)
            try:
                tokens = await InelsCloudClient.async_login(
                    session,
                    user_input[CONF_USERNAME],
                    user_input[CONF_PASSWORD],
                )
            except InelsCloudAuthError:
                errors["base"] = "invalid_auth"
            except InelsCloudError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    data={
                        **entry.data,
                        CONF_USERNAME: user_input[CONF_USERNAME],
                        CONF_ACCESS_TOKEN: tokens["access_token"],
                        CONF_REFRESH_TOKEN: tokens["refresh_token"],
                    },
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_USERNAME,
                        default=entry.data.get(CONF_USERNAME, ""),
                    ): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return options flow."""
        return config_entries.OptionsFlow()
