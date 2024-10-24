"""Sensor platform for Bayrol Pool Controller."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfTemperature,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from . import DOMAIN, CONF_CID

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Bayrol Pool sensor based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    cid = entry.data[CONF_CID]
    device_name = entry.data.get("device_name", "Pool Controller")

    sensors = [
        BayrolPoolSensor(
            coordinator,
            entry,
            "pH",
            f"bayrol_{cid}_ph",
            "pH",
            None,
            "pH",
            SensorStateClass.MEASUREMENT,
            None,
        ),
        BayrolPoolSensor(
            coordinator,
            entry,
            "mV",
            f"bayrol_{cid}_redox",
            "Redox",
            "mV",
            "mdi:flash",
            SensorStateClass.MEASUREMENT,
            None,
        ),
        BayrolPoolSensor(
            coordinator,
            entry,
            "T",
            f"bayrol_{cid}_temperature",
            "Temperature",
            UnitOfTemperature.CELSIUS,
            "mdi:thermometer",
            SensorStateClass.MEASUREMENT,
            SensorDeviceClass.TEMPERATURE,
        ),
    ]

    async_add_entities(sensors)

class BayrolPoolSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Bayrol Pool sensor."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        entry: ConfigEntry,
        key: str,
        entity_id: str,
        name: str,
        unit: str | None,
        icon: str,
        state_class: str | None,
        device_class: str | None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._key = key
        self.entity_id = f"sensor.{entity_id}"
        device_name = entry.data.get("device_name", "Pool Controller")
        self._attr_name = f"{device_name} {name}"
        self._attr_unique_id = f"bayrol_{entry.data[CONF_CID]}_{key}"
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_state_class = state_class
        self._attr_device_class = device_class

        # Device info
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"bayrol_{entry.data[CONF_CID]}")},
            "name": f"{device_name} ({entry.data[CONF_CID]})",
            "manufacturer": "Bayrol",
            "model": device_name,
        }

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        return self.coordinator.data.get(self._key)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            super().available
            and self.coordinator.data is not None
            and self._key in self.coordinator.data
        )
