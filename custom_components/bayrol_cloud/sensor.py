"""Sensor platform for Bayrol Pool Controller."""
from __future__ import annotations

from typing import Any

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

    def get_device_icon(name: str) -> str:
        """Get the appropriate icon based on device name."""
        name_lower = name.lower()
        
        if "pumpe" in name_lower or "pump" in name_lower:
            return "mdi:pump"
        elif "flockmatic" in name_lower:
            return "mdi:water"
        elif "alarm" in name_lower:
            return "mdi:alarm-light"
        elif "ph" in name_lower:
            return "mdi:ph"
        elif "redox" in name_lower or "rx" in name_lower:
            return "mdi:flash"
        elif "temp" in name_lower:
            return "mdi:thermometer"
        elif "chlor" in name_lower or "cl" in name_lower:
            return "mdi:molecule"
        elif "filter" in name_lower:
            return "mdi:air-filter"
        elif "heizung" in name_lower or "heat" in name_lower:
            return "mdi:radiator"
        elif "licht" in name_lower or "light" in name_lower:
            return "mdi:lightbulb"
        elif "schaltausgang" in name_lower or "output" in name_lower:
            return "mdi:electric-switch-closed"
        else:
            return "mdi:electric-switch"  # Default icon

    # Add device status sensors dynamically based on what's found in the data
    if coordinator.data and "device_status" in coordinator.data:
        for sensor_id, sensor_data in coordinator.data["device_status"].items():
            sensors.append(
                BayrolDeviceStatusSensor(
                    coordinator,
                    entry,
                    sensor_id,
                    f"bayrol_cloud_{cid}_{sensor_id}",
                    sensor_data["name"],
                    get_device_icon(sensor_data["name"]),
                )
            )

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
        self._attr_unique_id = f"bayrol_cloud_{entry.data[CONF_CID]}_{key}"
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_state_class = state_class
        self._attr_device_class = device_class

        # Device info
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"bayrol_cloud_{entry.data[CONF_CID]}")},
            "name": f"{device_name} ({entry.data[CONF_CID]})",
            "manufacturer": "Bayrol",
            "model": device_name,
        }

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

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not super().available or self.coordinator.data is None:
            return False
        
        # If device is offline, mark sensors as unavailable
        if self.coordinator.data.get("status") == "offline":
            return False
            
        return self._key in self.coordinator.data

class BayrolPoolStatusSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Bayrol Pool status sensor."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        entry: ConfigEntry,
        entity_id: str,
        name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_id = f"sensor.{entity_id}"
        device_name = entry.data.get("device_name", "Pool Controller")
        self._attr_name = f"{device_name} {name}"
        self._attr_unique_id = f"bayrol_cloud_{entry.data[CONF_CID]}_status"
        self._attr_icon = "mdi:connection"

        # Device info
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"bayrol_cloud_{entry.data[CONF_CID]}")},
            "name": f"{device_name} ({entry.data[CONF_CID]})",
            "manufacturer": "Bayrol",
            "model": device_name,
        }

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

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return super().available and self.coordinator.data is not None

class BayrolDeviceStatusSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Bayrol device status sensor."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        entry: ConfigEntry,
        key: str,
        entity_id: str,
        name: str,
        icon: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._key = key
        self.entity_id = f"sensor.{entity_id}"
        device_name = entry.data.get("device_name", "Pool Controller")
        self._attr_name = f"{device_name} {name}"
        self._attr_unique_id = f"bayrol_cloud_{entry.data[CONF_CID]}_{key}"
        self._attr_icon = icon

        # Device info
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"bayrol_cloud_{entry.data[CONF_CID]}")},
            "name": f"{device_name} ({entry.data[CONF_CID]})",
            "manufacturer": "Bayrol",
            "model": device_name,
        }

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        if not self.coordinator.data or "device_status" not in self.coordinator.data:
            return None
            
        device_data = self.coordinator.data["device_status"].get(self._key)
        if not device_data:
            return None
            
        return device_data.get("current_text")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        attrs = {}
        
        if (self.coordinator.data and 
            "device_status" in self.coordinator.data and 
            self._key in self.coordinator.data["device_status"]):
            
            device_data = self.coordinator.data["device_status"][self._key]
            
            # Add current value
            if "current_value" in device_data:
                attrs["value"] = device_data["current_value"]
            
            # Add available options
            if "options" in device_data:
                attrs["available_options"] = [
                    {"text": opt["text"], "value": opt["value"]}
                    for opt in device_data["options"]
                ]
                
            # Add item number for reference
            if "item_number" in device_data:
                attrs["item_number"] = device_data["item_number"]
        
        return attrs

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not super().available or self.coordinator.data is None:
            return False
        
        # If device is offline, mark sensors as unavailable
        if self.coordinator.data.get("status") == "offline":
            return False
            
        return (
            "device_status" in self.coordinator.data and
            self._key in self.coordinator.data["device_status"]
        )
