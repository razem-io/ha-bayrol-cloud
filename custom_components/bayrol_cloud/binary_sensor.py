"""Binary sensor platform for Bayrol Pool Controller."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
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
    """Set up Bayrol Pool binary sensors based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    cid = entry.data[CONF_CID]
    device_name = entry.data.get("device_name", "Pool Controller")

    sensors = [
        BayrolAlarmSensor(
            coordinator,
            entry,
            "pH",
            f"bayrol_cloud_{cid}_ph_alarm",
            "pH Alarm",
        ),
        BayrolAlarmSensor(
            coordinator,
            entry,
            "mV",
            f"bayrol_cloud_{cid}_redox_alarm",
            "Redox Alarm",
        ),
        BayrolAlarmSensor(
            coordinator,
            entry,
            "T",
            f"bayrol_cloud_{cid}_temperature_alarm",
            "Temperature Alarm",
        ),
    ]

    async_add_entities(sensors)

class BayrolAlarmSensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of a Bayrol Pool alarm sensor."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        entry: ConfigEntry,
        key: str,
        entity_id: str,
        name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._key = key
        self.entity_id = f"binary_sensor.{entity_id}"
        device_name = entry.data.get("device_name", "Pool Controller")
        self._attr_name = f"{device_name} {name}"
        self._attr_unique_id = f"bayrol_cloud_{entry.data[CONF_CID]}_{key}_alarm"
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM
        self._attr_icon = "mdi:alarm-light"

        # Device info
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"bayrol_cloud_{entry.data[CONF_CID]}")},
            "name": f"{device_name} ({entry.data[CONF_CID]})",
            "manufacturer": "Bayrol",
            "model": device_name,
        }

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        if not self.coordinator.data:
            return None
            
        alarm_key = f"{self._key}_alarm"
        # When alarm_key is True, it means there's a warning/problem
        # This matches the binary sensor's PROBLEM device class:
        # True = Problem, False = OK
        return self.coordinator.data.get(alarm_key, False)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not super().available or self.coordinator.data is None:
            return False
        
        # If device is offline, mark sensors as unavailable
        if self.coordinator.data.get("status") == "offline":
            return False
            
        alarm_key = f"{self._key}_alarm"
        return alarm_key in self.coordinator.data
