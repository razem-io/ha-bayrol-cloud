"""Sensor platform for Bayrol Pool Controller."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from . import DOMAIN, CONF_CID
from .helpers import BayrolEntity, get_device_icon

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Bayrol Pool sensor based on a config entry."""
    from homeassistant.components.sensor import (
        SensorEntity,
        SensorDeviceClass,
        SensorStateClass,
    )

    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    cid = entry.data[CONF_CID]
    device_name = entry.data.get("device_name", "Pool Controller")

    sensors = [
        BayrolPoolSensor(
            coordinator,
            entry,
            "pH",
            f"bayrol_cloud_{cid}_ph",
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
            f"bayrol_cloud_{cid}_redox",
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
            f"bayrol_cloud_{cid}_temperature",
            "Temperature",
            UnitOfTemperature.CELSIUS,
            "mdi:thermometer",
            SensorStateClass.MEASUREMENT,
            SensorDeviceClass.TEMPERATURE,
        ),
        BayrolPoolStatusSensor(
            coordinator,
            entry,
            f"bayrol_cloud_{cid}_status",
            "Status",
        ),
    ]

    async_add_entities(sensors)

class BayrolPoolSensor(BayrolEntity, SensorEntity):
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
        super().__init__(coordinator, entry, key, name)
        self.entity_id = f"sensor.{entity_id}"
        self._key = key
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon  # Override the auto-generated icon
        self._attr_state_class = state_class
        self._attr_device_class = device_class

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        return self.coordinator.data.get(self._key)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        attrs = {}
        alarm_key = f"{self._key}_alarm"
        if self.coordinator.data and alarm_key in self.coordinator.data:
            attrs["alarm"] = self.coordinator.data[alarm_key]
        return attrs

class BayrolPoolStatusSensor(BayrolEntity, SensorEntity):
    """Representation of a Bayrol Pool status sensor."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        entry: ConfigEntry,
        entity_id: str,
        name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, "status", name)
        self.entity_id = f"sensor.{entity_id}"
        self._attr_icon = "mdi:connection"  # Override the auto-generated icon

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("status", "unknown")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        attrs = {}
        if self.coordinator.data and self.coordinator.data.get("status") == "offline":
            attrs["last_seen"] = self.coordinator.data.get("last_seen")
            attrs["device_id"] = self.coordinator.data.get("device_id")
        return attrs
