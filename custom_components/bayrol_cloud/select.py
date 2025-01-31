"""Select platform for Bayrol Pool Controller."""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

import voluptuous as vol

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN, CONF_CID
from .const import CONF_SETTINGS_PASSWORD
from .helpers import BayrolEntity, get_device_icon

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Bayrol Pool select based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    api = hass.data[DOMAIN][entry.entry_id]["api"]
    settings_password = entry.data.get(CONF_SETTINGS_PASSWORD)

    selects = []

    # Register retry service
    async def handle_retry_access(call):
        """Handle the service call."""
        entity_id = call.data.get("entity_id")
        if entity_id:
            entity = next((select for select in selects if select.entity_id == entity_id), None)
            if entity:
                await entity.async_retry_access()

    hass.services.async_register(
        DOMAIN,
        "retry_settings_access",
        handle_retry_access,
        schema=vol.Schema({
            vol.Required("entity_id"): str,
        })
    )

    # Create selects for device status items that have multiple options
    if coordinator.data:
        device_status = coordinator.data.get("device_status", {})
        if not device_status:
            _LOGGER.warning("No device status data available - selects will be created on next update")
            async_add_entities([])  # Add empty list but allow coordinator to create entities later
            return
            
        for sensor_id, sensor_data in device_status.items():
            try:
                # Extract the item number from the full item class (e.g., "item3_153" -> "3.153")
                # This is the number from the select element, not the display element
                item_number = sensor_data["item_number"].replace("item", "").replace("_", ".")
                _LOGGER.debug("Creating select for %s with item number %s", sensor_data["name"], item_number)
                
                selects.append(
                    BayrolSettingSelect(
                        coordinator,
                        api,
                        entry,
                        sensor_id,
                        item_number,
                        sensor_data["name"],
                        sensor_data["options"],
                        settings_password,
                    )
                )
            except Exception as err:
                _LOGGER.error("Error creating select for %s: %s", sensor_id, err)

    async_add_entities(selects)

class BayrolSettingSelect(BayrolEntity, SelectEntity):
    """Representation of a Bayrol setting select."""

    def __init__(
        self,
        coordinator,
        api: Any,
        entry: ConfigEntry,
        sensor_id: str,
        item_number: str,
        name: str,
        options: list[dict],
        settings_password: str,
    ) -> None:
        """Initialize the select."""
        super().__init__(coordinator, entry, sensor_id, name)
        self._attr_entity_category = EntityCategory.CONFIG
        self._api = api
        self._cid = entry.data["cid"]
        self._settings_password = settings_password
        self._item_number = item_number
        self._options = options
        self._access_failed = False
        self._last_error = None
        
        # Map option values to their text representations
        self._value_to_text = {str(opt["value"]): opt["text"] for opt in options}
        self._text_to_value = {opt["text"]: opt["value"] for opt in options}
        
        # Set up the options list (texts)
        self._attr_options = list(self._text_to_value.keys())

    @property
    def assumed_state(self) -> bool:
        """Return True if unable to access real state of the entity."""
        return True  # Allow changing state back to previous values
        
    @property
    def should_poll(self) -> bool:
        """Return True if entity has to be polled for state."""
        return False  # We don't poll since we use the coordinator

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Return if the entity should be enabled when first added."""
        return True

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not self.coordinator.data:
            return False
        device_status = self.coordinator.data.get("device_status", {})
        return bool(device_status.get(self._sensor_id))

    @property
    def extra_state_attributes(self) -> dict:
        """Return entity specific state attributes."""
        attrs = {}
        if not self._settings_password:
            attrs["settings_access"] = "disabled"
            attrs["settings_message"] = "Settings password not configured"
            attrs["settings_state"] = "read_only"
        elif self._access_failed:
            attrs["settings_access"] = "error"
            attrs["settings_message"] = f"Access denied: {self._last_error or 'Invalid password'}"
            attrs["settings_state"] = "error"
            attrs["can_retry"] = True
        else:
            attrs["settings_access"] = "enabled"
            attrs["settings_message"] = "Settings access enabled"
            attrs["settings_state"] = "read_write"
        return attrs

    async def async_retry_access(self) -> None:
        """Service to retry settings access."""
        self._access_failed = False
        self._last_error = None
        self.async_write_ha_state()
        
    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()
        
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        try:
            if self.coordinator.data:
                device_status = self.coordinator.data.get("device_status", {})
                device_data = device_status.get(self._sensor_id)
                if device_data:
                    current_value = str(device_data.get("current_value"))
                    current_option = self._value_to_text.get(current_value)
                    _LOGGER.debug(
                        "%s: State updated by coordinator: value=%s, option=%s, available=%s",
                        self._attr_name,
                        current_value,
                        current_option,
                        self.available
                    )
                else:
                    _LOGGER.debug("%s: No device data in update", self._attr_name)
                
            # Always write state to ensure entity stays registered
            self.async_write_ha_state()
        except Exception as err:
            _LOGGER.error("Error handling coordinator update for %s: %s", self._attr_name, err)
            # Still write state to keep entity alive
            self.async_write_ha_state()

    @property
    def current_option(self) -> str | None:
        """Return the current option."""
        try:
            if not self.coordinator.data:
                _LOGGER.debug("%s: No coordinator data", self._attr_name)
                return None
                
            device_status = self.coordinator.data.get("device_status", {})
            if not device_status:
                _LOGGER.debug("%s: No device status data", self._attr_name)
                return None
                
            device_data = device_status.get(self._sensor_id)
            if not device_data:
                _LOGGER.debug("%s: No device data", self._attr_name)
                return None
                
            current_value = str(device_data.get("current_value"))
            current_option = self._value_to_text.get(current_value)
            _LOGGER.debug("%s: Current value: %s, Current option: %s, Available options: %s", 
                         self._attr_name, current_value, current_option, self._attr_options)
            return current_option
            
        except Exception as err:
            _LOGGER.error("Error getting current option for %s: %s", self._attr_name, err)
            return None

    @property
    def disabled(self) -> bool:
        """Return if entity should be disabled."""
        return not self._settings_password or self._access_failed

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        _LOGGER.debug(
            "%s: async_select_option called with option: %s (current option: %s)",
            self._attr_name,
            option,
            self.current_option
        )

        # Check if settings password is configured
        if not self._settings_password:
            _LOGGER.warning(
                "%s: Cannot change setting - no settings password configured. "
                "Configure password in integration options to enable changes.",
                self._attr_name
            )
            self.hass.components.persistent_notification.create(
                f"Cannot change {self._attr_name} - settings password not configured. "
                "Configure password in integration options to enable changes.",
                title="Bayrol Pool Settings",
                notification_id=f"bayrol_settings_{self._attr_name}"
            )
            return

        # Don't retry if access previously failed
        if self._access_failed:
            _LOGGER.warning(
                "%s: Cannot change setting - access previously denied. "
                "Use the retry button or update password in integration options.",
                self._attr_name
            )
            self.hass.components.persistent_notification.create(
                f"Cannot change {self._attr_name} - settings password not accepted. "
                "Use the retry button or update password in integration options.",
                title="Bayrol Pool Settings",
                notification_id=f"bayrol_settings_{self._attr_name}"
            )
            return

        try:
            # Get access using the settings password
            _LOGGER.debug("Getting controller access for %s...", self._attr_name)
            access_granted = await self._api.get_controller_access(self._cid, self._settings_password)
            
            if not access_granted:
                self._access_failed = True
                self._last_error = "Invalid password"
                self.async_write_ha_state()
                _LOGGER.warning(
                    "%s: Cannot change setting - settings password not accepted. "
                    "Use the retry button or update password in integration options.",
                    self._attr_name
                )
                return

            _LOGGER.debug("Controller access granted for %s", self._attr_name)

            # Get the value to set from our mapping
            value = self._text_to_value[option]
            
            # Create value list with 1 at the position corresponding to the selected value
            # For example, for Filterpumpe setting to Eco (value 1):
            # [0, 1, 0, 0, 0]
            value_list = [0] * len(self._options)  # Create list of zeros with length equal to number of options
            value_list[value] = 1  # Set 1 at the position corresponding to the selected value
            
            items = [{
                "topic": self._item_number,
                "name": "Betriebsart",  # Operating mode
                "value": value_list,
                "valid": 1,
                "cmd": 0
            }]

            _LOGGER.debug(
                "Setting %s to %s (value: %s, list: %s)",
                self._attr_name,
                option,
                value,
                value_list
            )

            # Set the items
            if not await self._api.set_items(self._cid, items):
                _LOGGER.error("Failed to set %s value", self._attr_name)
                self.hass.components.persistent_notification.create(
                    f"Failed to set {self._attr_name} value. Please try again.",
                    title="Bayrol Pool Settings",
                    notification_id=f"bayrol_settings_{self._attr_name}"
                )
                return

            _LOGGER.debug("Successfully set %s value", self._attr_name)

            # Wait a bit before starting verification
            _LOGGER.debug("%s: Waiting 2 seconds before starting verification...", self._attr_name)
            await asyncio.sleep(2)

            # Try for up to 10 seconds to verify the change
            _LOGGER.debug("%s: Verifying change (will retry for 10 seconds)...", self._attr_name)
            for retry in range(10):
                # Get the device status page directly to verify
                http_client = self._api._client
                device_url = f"https://www.bayrol-poolaccess.de/webview/p/device.php?c={self._cid}"
                headers = http_client._get_headers()
                
                async with http_client._session.get(device_url, headers=headers) as response:
                    if response.status == 200:
                        html = await response.text()
                        # Look for our select element
                        select_match = re.search(f'item{self._item_number.replace(".", "_")}.*?<select.*?>(.*?)</select>', html, re.DOTALL)
                        if select_match:
                            select_html = select_match.group(1)
                            _LOGGER.debug(
                                "%s: Attempt %d - Current HTML: %s",
                                self._attr_name,
                                retry + 1,
                                select_html
                            )
                            
                            # Check if either the value or text indicates the change
                            value_changed = f'value="{value}" selected' in select_html
                            text_changed = f'>{option}<' in select_html
                            
                            if value_changed or text_changed:
                                _LOGGER.debug("%s: Verified change (value_changed=%s, text_changed=%s)", 
                                            self._attr_name, value_changed, text_changed)
                                # Now refresh coordinator to update all entities
                                await self.coordinator.async_request_refresh()
                                return
                    
                    _LOGGER.debug("%s: Not yet set to %s, waiting 1 second...", self._attr_name, option)
                    await asyncio.sleep(1)
            
            _LOGGER.warning("%s: Failed to verify change to %s after 10 seconds", self._attr_name, option)
            self.hass.components.persistent_notification.create(
                f"Failed to verify {self._attr_name} change to {option}. The change may not have been applied.",
                title="Bayrol Pool Settings",
                notification_id=f"bayrol_settings_{self._attr_name}"
            )

        except Exception as err:
            _LOGGER.error(
                "Error setting %s value: %s",
                self._attr_name,
                err
            )
