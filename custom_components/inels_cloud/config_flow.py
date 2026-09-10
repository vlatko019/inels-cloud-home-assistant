"""Config flow for iNELS Cloud."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import InelsCloudAuthError, InelsCloudClient, InelsCloudError
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_PASSWORD,
    CONF_REFRESH_TOKEN,
    CONF_SHUTTER_DIRECTION,
    CONF_USERNAME,
    DEFAULT_SHUTTER_DIRECTION,
    DOMAIN,
    SHUTTER_DIRECTION_NORMAL,
    SHUTTER_DIRECTION_REVERSED,
)


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
                await self.async_set_unique_id(user_input[CONF_USERNAME].lower())
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
        return InelsCloudOptionsFlow()


class InelsCloudOptionsFlow(config_entries.OptionsFlow):
    """Handle iNELS Cloud integration options."""

    def __init__(self) -> None:
        self._shutters: list[tuple[str, str]] = []
        self._directions: dict[str, str] = {}
        self._index = 0

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Prepare the shutter options flow."""
        coordinator = getattr(self.config_entry, "runtime_data", None)
        devices = getattr(coordinator, "devices", {}) if coordinator else {}
        self._shutters = [
            (key, device["dev_name"])
            for key, device in devices.items()
            if device.get("dev_type") == 21 and not device.get("read_only", False)
        ]
        self._shutters.sort(key=lambda item: item[1].lower())
        self._directions = dict(
            self.config_entry.options.get(CONF_SHUTTER_DIRECTION, {})
        )
        self._index = 0

        if not self._shutters:
            return self.async_create_entry(title="", data=dict(self.config_entry.options))

        return await self.async_step_shutter()

    async def async_step_shutter(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Configure one shutter."""
        key, name = self._shutters[self._index]
        if user_input is not None:
            self._directions[key] = user_input["direction"]
            self._index += 1
            if self._index >= len(self._shutters):
                return self.async_create_entry(
                    title="",
                    data={CONF_SHUTTER_DIRECTION: self._directions},
                )
            return await self.async_step_shutter()

        current = self._directions.get(key, DEFAULT_SHUTTER_DIRECTION)
        return self.async_show_form(
            step_id="shutter",
            description_placeholders={"shutter_name": name},
            data_schema=vol.Schema(
                {
                    vol.Required("direction", default=current): vol.In(
                        {
                            SHUTTER_DIRECTION_REVERSED: "Reversed",
                            SHUTTER_DIRECTION_NORMAL: "Normal",
                        }
                    )
                }
            ),
        )
