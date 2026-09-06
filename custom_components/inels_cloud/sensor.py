"""Sensor platform for iNELS Cloud."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEV_TYPE_THERMOSTAT, DOMAIN
from .coordinator import InelsCloudCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up iNELS sensors."""
    coordinator: InelsCloudCoordinator = entry.runtime_data
    entities: list[SensorEntity] = []

    for key, device in coordinator.devices.items():
        if device.get("dev_type") != DEV_TYPE_THERMOSTAT:
            continue
        entities.extend(
            [
                InelsCloudTemperature(coordinator, key),
                InelsCloudHumidity(coordinator, key),
            ]
        )

    async_add_entities(entities)


class InelsCloudSensorBase(CoordinatorEntity[InelsCloudCoordinator], SensorEntity):
    """Base iNELS sensor."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: InelsCloudCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._key = key
        device = coordinator.devices[key]
        self._attr_unique_id = f"{DOMAIN}_{key.replace(':', '_')}_{self.__class__.__name__.lower()}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, key)},
            name=device["dev_name"],
            manufacturer="iNELS",
            model=f"ELAN-RF device type {device['dev_type']}",
        )

    @property
    def _state(self) -> dict[str, Any]:
        return self.coordinator.devices[self._key].get("state", {})

    @property
    def available(self) -> bool:
        return self._state.get("rssi") != "UNKNOWN"


class InelsCloudTemperature(InelsCloudSensorBase):
    """Temperature sensor."""

    _attr_name = "Temperature"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    @property
    def native_value(self) -> float | None:
        value = self._state.get("temperature")
        return None if value is None or value == 2550 else value / 100


class InelsCloudHumidity(InelsCloudSensorBase):
    """Humidity sensor."""

    _attr_name = "Humidity"
    _attr_device_class = SensorDeviceClass.HUMIDITY
    _attr_native_unit_of_measurement = PERCENTAGE

    @property
    def native_value(self) -> int | None:
        value = self._state.get("humidity")
        return None if value is None else int(value)
