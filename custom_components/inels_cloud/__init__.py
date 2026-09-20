"""The iNELS Cloud integration."""

from __future__ import annotations

import logging
from typing import Any

from aiohttp import ClientSession
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import InelsCloudAuthError, InelsCloudClient
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_REFRESH_TOKEN,
    PLATFORMS,
)
from .coordinator import InelsCloudCoordinator
from .websocket import InelsCloudWebSocket

_LOGGER = logging.getLogger(__name__)


async def _update_tokens(
    hass: HomeAssistant,
    entry: ConfigEntry,
    access_token: str,
    refresh_token: str,
) -> None:
    """Persist rotated authentication tokens."""
    hass.config_entries.async_update_entry(
        entry,
        data={
            **entry.data,
            CONF_ACCESS_TOKEN: access_token,
            CONF_REFRESH_TOKEN: refresh_token,
        },
    )


async def _async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the integration when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up iNELS Cloud from a config entry."""
    session: ClientSession = async_get_clientsession(hass)

    async def token_callback(access_token: str, refresh_token: str) -> None:
        await _update_tokens(hass, entry, access_token, refresh_token)

    api = InelsCloudClient(
        session,
        access_token=entry.data.get(CONF_ACCESS_TOKEN),
        refresh_token=entry.data.get(CONF_REFRESH_TOKEN),
        token_update_callback=token_callback,
    )

    # Force authentication and initial discovery during setup.
    coordinator = InelsCloudCoordinator(hass, api, None)  # type: ignore[arg-type]

    try:
        await coordinator.async_config_entry_first_refresh()
    except InelsCloudAuthError as err:
        _LOGGER.warning("Authentication failed for iNELS Cloud config entry %s: %s", entry.title, err)
        raise ConfigEntryAuthFailed("iNELS Cloud authentication expired. Please re-authenticate.") from err

    websocket = InelsCloudWebSocket(
        session,
        api.ensure_token,
        coordinator.handle_event,
    )

    coordinator.websocket = websocket
    await websocket.async_start()

    entry.runtime_data = coordinator
    options_snapshot = dict(entry.options)

    async def options_listener(hass: HomeAssistant, updated_entry: ConfigEntry) -> None:
        if updated_entry.options == options_snapshot:
            return
        await _async_update_options(hass, updated_entry)

    entry.async_on_unload(entry.add_update_listener(options_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an iNELS Cloud config entry."""
    coordinator: InelsCloudCoordinator = entry.runtime_data
    await coordinator.websocket.async_stop()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
