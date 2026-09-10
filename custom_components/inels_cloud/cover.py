"""Cover platform for iNELS Cloud shutters."""

from __future__ import annotations

from typing import Any

from homeassistant.components.cover import (
    ATTR_POSITION,
    CoverDeviceClass,
    CoverEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_SHUTTER_DIRECTION, DEFAULT_SHUTTER_DIRECTION, DEV_TYPE_SHUTTER, DOMAIN
from .coordinator import InelsCloudCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up shutter covers."""
    coordinator: InelsCloudCoordinator = entry.runtime_data
    entities = [
        InelsCloudCover(coordinator, entry, key)
        for key, device in coordinator.devices.items()
        if device.get("dev_type") == DEV_TYPE_SHUTTER
        and not device.get("read_only", False)
    ]
    async_add_entities(entities)


class InelsCloudCover(CoordinatorEntity[InelsCloudCoordinator], CoverEntity):
    """An iNELS Cloud shutter."""

    _attr_device_class = CoverDeviceClass.SHUTTER
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: InelsCloudCoordinator,
        entry: ConfigEntry,
        key: str,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._key = key
        self._attr_unique_id = f"{DOMAIN}_{key.replace(':', '_')}"
        device = coordinator.devices[key]
        self._attr_name = device["dev_name"]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, key)},
            name=device["dev_name"],
            manufacturer="iNELS",
            model=f"ELAN-RF device type {device['dev_type']}",
        )

    @property
    def _device(self) -> dict[str, Any]:
        return self.coordinator.devices[self._key]

    @property
    def _reversed(self) -> bool:
        """Return whether this shutter uses reversed direction."""
        directions = self._entry.options.get(CONF_SHUTTER_DIRECTION, {})
        return directions.get(self._key, DEFAULT_SHUTTER_DIRECTION) == "reversed"

    @property
    def current_cover_position(self) -> int | None:
        position = self._device.get("state", {}).get("os")
        if position is None or position == 255:
            return None
        position = max(0, min(100, int(position)))
        return 100 - position if self._reversed else position

    @property
    def is_closed(self) -> bool:
        position = self.current_cover_position
        return position == 0 if position is not None else False

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Set shutter position."""
        position = max(0, min(100, int(kwargs[ATTR_POSITION])))
        api_position = 100 - position if self._reversed else position
        await self.coordinator.api.async_send_command(
            mac=self._device["mac"],
            tech=self._device["tech"],
            dev_id=self._device["uid"],
            dev_type=self._device["dev_type"],
            fce="os",
            value=api_position,
        )
        # Optimistic state until the WebSocket event arrives.
        self._device.setdefault("state", {})["os"] = api_position
        self.async_write_ha_state()

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the shutter fully."""
        await self.async_set_cover_position(position=100)

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the shutter fully."""
        await self.async_set_cover_position(position=0)

    @property
    def available(self) -> bool:
        """Return whether the cloud reports the device as online."""
        return self._device.get("state", {}).get("rssi") != "UNKNOWN"
