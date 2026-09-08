"""Coordinator and runtime state for iNELS Cloud."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import InelsCloudAuthError, InelsCloudClient, InelsCloudError
from .const import DOMAIN
from .websocket import InelsCloudWebSocket

_LOGGER = logging.getLogger(__name__)


class InelsCloudCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Keep iNELS device state synchronized."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: InelsCloudClient,
        websocket: InelsCloudWebSocket,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=None,
        )
        self.api = api
        self.websocket = websocket
        self.devices: dict[str, dict[str, Any]] = {}

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        """Fetch devices from the cloud."""
        try:
            response = await self.api.async_get_devices()
        except InelsCloudAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except InelsCloudError as err:
            raise UpdateFailed(str(err)) from err

        parsed: dict[str, dict[str, Any]] = {}
        for project in response.get("project", []):
            mac = project.get("mac")
            tech = project.get("tech")
            for device in project.get("devices", []):
                uid = device.get("address", {}).get("uid")
                if mac is None or tech is None or uid is None:
                    continue
                key = self.device_key(mac, tech, int(uid))
                parsed[key] = {
                    "mac": mac,
                    "tech": tech,
                    "uid": int(uid),
                    **device,
                }

        self.devices = parsed
        return parsed

    @staticmethod
    def device_key(mac: str, tech: str, uid: int) -> str:
        """Build a stable device key."""
        return f"{tech}:{mac}:{uid}"

    @callback
    def handle_event(self, event: dict[str, Any]) -> None:
        """Apply a WebSocket event to the matching device."""
        if event.get("action") != "event":
            return

        mac = event.get("mac")
        tech = event.get("tech")
        uid = event.get("eui")
        if not mac or not tech or uid is None:
            return

        key = self.device_key(mac, tech, int(uid))
        current = self.devices.get(key)
        if current is None:
            # Unknown event: trigger a full discovery refresh.
            self.hass.async_create_task(self.async_request_refresh())
            return

        current.setdefault("state", {}).update(
            {
                key: value
                for key, value in event.items()
                if key not in {
                    "dev",
                    "eui",
                    "mac",
                    "tech",
                    "init",
                    "action",
                    "bulk",
                }
            }
        )
        
        self.async_set_updated_data(self.devices)
