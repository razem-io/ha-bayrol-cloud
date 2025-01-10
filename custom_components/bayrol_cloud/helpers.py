"""Helper functions and base classes for Bayrol Pool Controller integration."""
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

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

def get_device_info(entry: ConfigEntry) -> dict[str, Any]:
    """Get device info dictionary."""
    device_name = entry.data.get("device_name", "Pool Controller")
    return {
        "identifiers": {(DOMAIN, f"bayrol_cloud_{entry.data['cid']}")},
        "name": f"{device_name} ({entry.data['cid']})",
        "manufacturer": "Bayrol",
        "model": device_name,
    }

class BayrolEntity(CoordinatorEntity):
    """Base class for Bayrol entities."""

    def __init__(self, coordinator, entry: ConfigEntry, sensor_id: str, name: str) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        device_name = entry.data.get("device_name", "Pool Controller")
        self._sensor_id = sensor_id
        self._attr_name = f"{device_name} {name}"
        self._attr_unique_id = f"bayrol_cloud_{entry.data['cid']}_{sensor_id}"
        self._attr_icon = get_device_icon(name)
        self._attr_device_info = get_device_info(entry)

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self.async_write_ha_state()  # Write initial state
        
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        _LOGGER.debug("%s: Handling coordinator update", self._attr_name)
        self.async_write_ha_state()
        
    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not super().available or self.coordinator.data is None:
            _LOGGER.debug("%s: Not available (super: %s, data: %s)", 
                         self._attr_name, super().available, self.coordinator.data is not None)
            return False
        
        # If device is offline, mark entity as unavailable
        if self.coordinator.data.get("status") == "offline":
            _LOGGER.debug("%s: Device offline", self._attr_name)
            return False

        # For status sensor, only check coordinator data exists
        if self._sensor_id == "status":
            return True
            
        # For measurement sensors (pH, mV, T), check if data exists
        if self._sensor_id in ["pH", "mV", "T"]:
            available = self._sensor_id in self.coordinator.data
            _LOGGER.debug("%s: Measurement sensor available: %s", self._attr_name, available)
            return available
            
        # For device status entities, check if data exists
        if "device_status" in self.coordinator.data:
            available = self._sensor_id in self.coordinator.data["device_status"]
            _LOGGER.debug("%s: Device status available: %s", self._attr_name, available)
            return available
            
        _LOGGER.debug("%s: No device status data", self._attr_name)
        return False
