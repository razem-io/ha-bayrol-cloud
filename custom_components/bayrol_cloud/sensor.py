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
from .client.parser import get_available_measurements

_LOGGER = logging.getLogger(__name__)

# Measurement configurations with backward-compatible entity IDs
MEASUREMENT_CONFIG = {
    "pH": {
        "entity_suffix": "ph",
        "name": "pH",
        "unit": None,
        "icon": "pH",
        "device_class": None,
    },
    "mV": {
        "entity_suffix": "redox",
        "name": "Redox",
        "unit": "mV",
        "icon": "mdi:flash",
        "device_class": None,
    },
    "Cl": {
        "entity_suffix": "chlorine",
        "name": "Chlorine",
        "unit": "mg/l",
        "icon": "mdi:bottle-tonic",
        "device_class": None,
    },
    "Salt": {
        "entity_suffix": "salt",
        "name": "Salt",
        "unit": "g/l",
        "icon": "mdi:shaker-outline",
        "device_class": None,
    },
    "T": {
        "entity_suffix": "temperature",
        "name": "Temperature",
        "unit": UnitOfTemperature.CELSIUS,
        "icon": "mdi:thermometer",
        "device_class": "temperature",
    },
}

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

    sensors = []
    
    # Always add the status sensor
    sensors.append(
        BayrolPoolStatusSensor(
            coordinator,
            entry,
            f"bayrol_cloud_{cid}_status",
            "Status",
        )
    )
    
    # Get available measurements from the coordinator data
    available_measurements = []
    if coordinator.data:
        available_measurements = get_available_measurements(coordinator.data)
        _LOGGER.debug("Available measurements for device %s: %s", cid, available_measurements)
    else:
        _LOGGER.warning("No coordinator data available during sensor setup for device %s", cid)
        # Fallback: create all possible sensors for backward compatibility
        available_measurements = list(MEASUREMENT_CONFIG.keys())
        _LOGGER.info("Using fallback measurements for device %s: %s", cid, available_measurements)
    
    # Create sensors for available measurements
    for measurement_key in available_measurements:
        if measurement_key in MEASUREMENT_CONFIG:
            config = MEASUREMENT_CONFIG[measurement_key]
            
            # Map device class string to enum if needed
            device_class = None
            if config["device_class"] == "temperature":
                device_class = SensorDeviceClass.TEMPERATURE
            
            sensor = BayrolPoolSensor(
                coordinator,
                entry,
                measurement_key,
                f"bayrol_cloud_{cid}_{config['entity_suffix']}",
                config["name"],
                config["unit"],
                config["icon"],
                SensorStateClass.MEASUREMENT,
                device_class,
            )
            sensors.append(sensor)
            _LOGGER.debug(
                "Created %s sensor for device %s (entity_id: %s)",
                config["name"],
                cid,
                f"sensor.bayrol_cloud_{cid}_{config['entity_suffix']}"
            )
        else:
            _LOGGER.warning(
                "Unknown measurement '%s' found for device %s - no sensor configuration available",
                measurement_key,
                cid
            )
    
    if not sensors:
        _LOGGER.error("No sensors could be created for device %s", cid)
        return
    
    _LOGGER.info(
        "Creating %d sensors for device %s: %s",
        len(sensors),
        cid,
        [sensor._attr_name for sensor in sensors]
    )

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
