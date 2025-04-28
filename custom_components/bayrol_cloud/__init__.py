"""The Bayrol Pool Controller integration."""
from __future__ import annotations

import logging
import aiohttp
import async_timeout
import voluptuous as vol
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_USERNAME,
    CONF_PASSWORD,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .client.bayrol_api import BayrolPoolAPI
from .client.device_parser import parse_device_status
from .const import DEFAULT_REFRESH_INTERVAL
from .helpers import conditional_log

_LOGGER = logging.getLogger(__name__)

DOMAIN = "bayrol_cloud"
CONF_CID = "cid"

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH, Platform.BINARY_SENSOR, Platform.SELECT]

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_USERNAME): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
                vol.Required(CONF_CID): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Bayrol Pool component."""
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Bayrol Pool from a config entry."""
    conditional_log(_LOGGER, logging.DEBUG, "Setting up Bayrol Pool integration", debug_mode=False)
    
    # Create API instance
    session = async_get_clientsession(hass)
    api = BayrolPoolAPI(session)

    # Initial login to establish session
    try:
        conditional_log(_LOGGER, logging.DEBUG, "Performing initial login after setup/restart...", debug_mode=api.debug_mode)
        login_success = False
        retry_count = 0
        max_retries = 3

        while not login_success and retry_count < max_retries:
            try:
                if await api.login(entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD]):
                    login_success = True
                    conditional_log(_LOGGER, logging.DEBUG, "Initial login successful", debug_mode=api.debug_mode)
                    break
                else:
                    _LOGGER.warning("Login attempt %d failed, retrying...", retry_count + 1)
            except Exception as err:
                _LOGGER.warning("Login attempt %d failed with error: %s", retry_count + 1, err)
            retry_count += 1

        if not login_success:
            _LOGGER.error("Failed to perform initial login after %d attempts", max_retries)
            return False

        # Verify we can get data
        conditional_log(_LOGGER, logging.DEBUG, "Verifying data access...", debug_mode=api.debug_mode)
        data = await api.get_data(entry.data[CONF_CID])
        if not data:
            _LOGGER.error("Failed to get initial data")
            return False
        conditional_log(_LOGGER, logging.DEBUG, "Initial data fetch successful: %s", data, debug_mode=api.debug_mode)

    except Exception as err:
        _LOGGER.error("Error during initial setup: %s", err)
        return False

    async def async_update_data():
        """Fetch data from API."""
        try:
            async with async_timeout.timeout(30):
                retry_count = 0
                max_retries = 3
                last_error = None

                while retry_count < max_retries:
                    try:
                        # Always try to get data first
                        conditional_log(_LOGGER, logging.DEBUG, "Attempting to fetch data (attempt %d)...", retry_count + 1, debug_mode=api.debug_mode)
                        data = await api.get_data(entry.data[CONF_CID])
                        
                        if data:
                            # Get and parse device status data
                            try:
                                device_status = await api.get_device_status(entry.data[CONF_CID], raw=True)
                                if device_status:
                                        parsed_status = parse_device_status(device_status, debug=api.debug_mode)
                                        if parsed_status:
                                            data["device_status"] = parsed_status
                                            conditional_log(_LOGGER, logging.DEBUG, "Device status parsed successfully: %s", parsed_status, debug_mode=api.debug_mode)
                                        else:
                                            html_length = len(device_status) if device_status else 0
                                            html_type = type(device_status).__name__
                                            _LOGGER.warning("Failed to parse device status data (length: %d bytes, type: %s)", html_length, html_type)
                            except Exception as err:
                                _LOGGER.warning("Error getting device status: %s", err)
                            
                            conditional_log(_LOGGER, logging.DEBUG, "Data fetch successful: %s", data, debug_mode=api.debug_mode)
                            return data
                        
                        # If data fetch failed, try logging in again
                        conditional_log(_LOGGER, logging.DEBUG, "Data fetch failed, attempting login...", debug_mode=api.debug_mode)
                        if await api.login(entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD]):
                            # Try getting data again after successful login
                            data = await api.get_data(entry.data[CONF_CID])
                            if data:
                                # Get and parse device status data
                                try:
                                    device_status = await api.get_device_status(entry.data[CONF_CID], raw=True)
                                    if device_status:
                                        parsed_status = parse_device_status(device_status, debug=api.debug_mode)
                                        if parsed_status:
                                            # Compare with previous device status to see what changed
                                            if coordinator.data and "device_status" in coordinator.data:
                                                old_status = coordinator.data["device_status"]
                                                for device_id, new_state in parsed_status.items():
                                                    if device_id in old_status:
                                                        old_state = old_status[device_id]
                                                        if old_state.get("current_value") != new_state.get("current_value"):
                                                            conditional_log(_LOGGER, logging.DEBUG,
                                                                "Device %s state changed: %s -> %s",
                                                                device_id,
                                                                old_state.get("current_text"),
                                                                new_state.get("current_text"),
                                                                debug_mode=api.debug_mode
                                                            )
                                            
                                            data["device_status"] = parsed_status
                                            conditional_log(_LOGGER, logging.DEBUG, "Device status parsed successfully: %s", parsed_status, debug_mode=api.debug_mode)
                                        else:
                                            html_length = len(device_status) if device_status else 0
                                            html_type = type(device_status).__name__
                                            _LOGGER.warning("Failed to parse device status data (length: %d bytes, type: %s)", html_length, html_type)
                                except Exception as err:
                                    _LOGGER.warning("Error getting device status: %s", err)
                                
                                conditional_log(_LOGGER, logging.DEBUG, "Data fetch successful: %s", data, debug_mode=api.debug_mode)
                                return data
                    
                    except Exception as err:
                        last_error = err
                        _LOGGER.warning(
                            "Error during update attempt %d: %s", 
                            retry_count + 1, 
                            err
                        )
                    
                    retry_count += 1

                # If we get here, all retries failed
                raise UpdateFailed(
                    f"Failed to get data after {max_retries} attempts. Last error: {last_error}"
                )

        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}")

    # Get refresh interval from config entry or use default
    refresh_interval = entry.data.get("refresh_interval", DEFAULT_REFRESH_INTERVAL)
    
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=async_update_data,
        update_interval=timedelta(seconds=refresh_interval),
    )

    # Do first refresh to verify everything works
    await coordinator.async_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "api": api,  # Store API instance to maintain session
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    conditional_log(_LOGGER, logging.DEBUG, "Bayrol Pool integration setup completed successfully", debug_mode=api.debug_mode)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
