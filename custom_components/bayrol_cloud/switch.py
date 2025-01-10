from __future__ import annotations

from datetime import datetime
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN, CONF_CID
from .client.bayrol_api import BayrolPoolAPI

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Bayrol Pool switch based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    api: BayrolPoolAPI = hass.data[DOMAIN][entry.entry_id]["api"]
    cid = entry.data[CONF_CID]
    device_name = entry.data.get("device_name", "Pool Controller")

    async_add_entities([
        BayrolDebugSwitch(coordinator, entry, api),
    ])

class BayrolDebugSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a Bayrol Pool debug switch."""

    def __init__(self, coordinator, entry, api: BayrolPoolAPI):
        """Initialize the switch."""
        super().__init__(coordinator)
        self._cid = entry.data[CONF_CID]
        self._api = api
        device_name = entry.data.get("device_name", "Pool Controller")
        self._version = "0.1.4"  # Version from manifest.json
        self._last_updated = None
        
        # Set both entity_id and unique_id with the same format as sensors
        self.entity_id = f"switch.bayrol_cloud_{self._cid}_debug"
        self._attr_name = f"{device_name} Debug Mode"
        self._attr_unique_id = f"bayrol_cloud_{self._cid}_debug"
        self._attr_icon = "mdi:bug"

        # Device info
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"bayrol_cloud_{self._cid}")},
            "name": f"{device_name} ({self._cid})",
            "manufacturer": "Bayrol",
            "model": device_name,
        }

    @property
    def is_on(self) -> bool:
        """Return true if debug mode is on."""
        return self._api.debug_mode

    @property
    def extra_state_attributes(self):
        """Return debug data when available."""
        attributes = {
            "version": self._version,
        }
        
        if self._last_updated:
            attributes["last_updated"] = self._last_updated
            
        if self.is_on and self.coordinator.data and "debug_raw_html" in self.coordinator.data:
            attributes["debug_raw_html"] = self.coordinator.data["debug_raw_html"]
            self._last_updated = datetime.now().isoformat()
            attributes["last_updated"] = self._last_updated
            
        return attributes

    async def async_turn_on(self, **kwargs) -> None:
        """Turn on debug mode."""
        self._api.debug_mode = True
        self._last_updated = datetime.now().isoformat()
        self.async_write_ha_state()
        # Force an immediate data refresh to get debug data
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off debug mode."""
        self._api.debug_mode = False
        self.async_write_ha_state()
        # Force a refresh to clear debug data
        await self.coordinator.async_request_refresh()
