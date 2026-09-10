"""Sensor platform for iNELS Cloud."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_SHUTTER_DIRECTION,
    DEFAULT_SHUTTER_DIRECTION,
    DEV_TYPE_SHUTTER,
    DEV_TYPE_THERMOSTAT,
    DOMAIN,
)
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
        if device.get("dev_type") == DEV_TYPE_THERMOSTAT:
            entities.extend(
                [
                    InelsCloudTemperature(coordinator, key),
                    InelsCloudHumidity(coordinator, key),
                ]
            )
        elif device.get("dev_type") == DEV_TYPE_SHUTTER:
            entities.append(InelsCloudShutterPosition(coordinator, entry, key))

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
        # dev_type 30 can legitimately report rssi=UNKNOWN while still
        # providing valid temperature/humidity data. Presence in the
        # coordinator is therefore a better availability signal here.
        return self._key in self.coordinator.devices


class InelsCloudTemperature(InelsCloudSensorBase):
    """Temperature sensor."""

    _attr_name = "Temperature"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    @property
    def native_value(self) -> float | None:
        value = self._state.get("temperature")
        return None if value is None else value / 100


class InelsCloudHumidity(InelsCloudSensorBase):
    """Humidity sensor."""

    _attr_name = "Humidity"
    _attr_device_class = SensorDeviceClass.HUMIDITY
    _attr_native_unit_of_measurement = PERCENTAGE

    @property
    def native_value(self) -> int | None:
        value = self._state.get("humidity")
        return None if value is None else int(value)


class InelsCloudShutterPosition(InelsCloudSensorBase):
    """Logical shutter position sensor for history/statistics."""

    _attr_name = "Position"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: InelsCloudCoordinator,
        entry: ConfigEntry,
        key: str,
    ) -> None:
        self._entry = entry
        super().__init__(coordinator, key)
        self._attr_unique_id = f"{DOMAIN}_{key.replace(':', '_')}_position"

    @property
    def _reversed(self) -> bool:
        """Return whether this shutter uses reversed direction."""
        directions = self._entry.options.get(CONF_SHUTTER_DIRECTION, {})
        return directions.get(self._key, DEFAULT_SHUTTER_DIRECTION) == "reversed"

    @property
    def native_value(self) -> int | None:
        value = self._state.get("os")
        if value is None or value == 255:
            return None
        position = max(0, min(100, int(value)))
        return 100 - position if self._reversed else position
