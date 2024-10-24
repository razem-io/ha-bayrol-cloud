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

from .api import BayrolPoolAPI

_LOGGER = logging.getLogger(__name__)

DOMAIN = "bayrol_pool"
CONF_CID = "cid"

PLATFORMS: list[Platform] = [Platform.SENSOR]

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

SCAN_INTERVAL = timedelta(minutes=5)

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Bayrol Pool component."""
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Bayrol Pool from a config entry."""
    session = async_get_clientsession(hass)
    api = BayrolPoolAPI(
        session=session,
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
    )

    async def async_update_data():
        """Fetch data from API."""
        try:
            async with async_timeout.timeout(30):
                if not await api.login():
                    raise UpdateFailed("Failed to login to Bayrol Pool Access")
                
                data = await api.get_data(entry.data[CONF_CID])
                if not data:
                    raise UpdateFailed("Failed to get data from Bayrol Pool Access")
                
                return data
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}")

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=async_update_data,
        update_interval=SCAN_INTERVAL,
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
