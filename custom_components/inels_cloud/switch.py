"""Switch platform for iNELS Cloud."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEV_TYPE_SWITCH, DOMAIN
from .coordinator import InelsCloudCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up iNELS switches."""
    coordinator: InelsCloudCoordinator = entry.runtime_data
    async_add_entities(
        InelsCloudSwitch(coordinator, key)
        for key, device in coordinator.devices.items()
        if device.get("dev_type") == DEV_TYPE_SWITCH
        and not device.get("read_only", False)
    )


class InelsCloudSwitch(CoordinatorEntity[InelsCloudCoordinator], SwitchEntity):
    """An iNELS Cloud on/off device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: InelsCloudCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._key = key
        device = coordinator.devices[key]
        self._attr_unique_id = f"{DOMAIN}_{key.replace(':', '_')}"
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
    def is_on(self) -> bool:
        return bool(self._device.get("state", {}).get("on"))

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on."""
        await self.coordinator.api.async_send_command(
            mac=self._device["mac"],
            tech=self._device["tech"],
            dev_id=self._device["uid"],
            dev_type=self._device["dev_type"],
            fce="on",
            value=1,
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off."""
        await self.coordinator.api.async_send_command(
            mac=self._device["mac"],
            tech=self._device["tech"],
            dev_id=self._device["uid"],
            dev_type=self._device["dev_type"],
            fce="on",
            value=0,
        )
