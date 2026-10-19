"""Cover platform for iNELS Cloud shutters."""

from __future__ import annotations

from typing import Any

from homeassistant.components.cover import (
    ATTR_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
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
    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.SET_POSITION
    )

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
        """Return the logical position, or None when the device has no reading."""
        raw_position = self._device.get("state", {}).get("os")
        if raw_position is None:
            return None
        try:
            position = int(raw_position)
        except (TypeError, ValueError):
            return None
        if position == 255:
            return None
        position = max(0, min(100, position))
        return 100 - position if self._reversed else position

    @staticmethod
    def _state_flag(value: Any) -> bool | None:
        """Parse a cloud state flag, preserving missing or unknown values."""
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value) if value in (0, 1) else None
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "on", "yes"}:
                return True
            if normalized in {"0", "false", "off", "no"}:
                return False
        return None

    @property
    def is_opening(self) -> bool | None:
        """Return whether the motor is moving toward logical open."""
        state = self._device.get("state", {})
        motor_on = self._state_flag(state.get("motor_on"))
        if motor_on is not True:
            return motor_on
        moving_down = self._state_flag(state.get("direction_down"))
        if moving_down is None:
            return None
        # The cloud's direction_down flag maps opposite to the initial assumption.
        return not moving_down if self._reversed else moving_down

    @property
    def is_closing(self) -> bool | None:
        """Return whether the motor is moving toward logical closed."""
        state = self._device.get("state", {})
        motor_on = self._state_flag(state.get("motor_on"))
        if motor_on is not True:
            return motor_on
        moving_down = self._state_flag(state.get("direction_down"))
        if moving_down is None:
            return None
        return moving_down if self._reversed else not moving_down

    @property
    def is_closed(self) -> bool | None:
        """Return closed only when the position is known."""
        position = self.current_cover_position
        return position == 0 if position is not None else None

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Set shutter position."""
        position = max(0, min(100, int(kwargs[ATTR_POSITION])))
        api_position = 100 - position if self._reversed else position
        await self.coordinator.async_send_command(
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
