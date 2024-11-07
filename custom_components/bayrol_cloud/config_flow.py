"""Config flow for Bayrol Pool Controller integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
import aiohttp

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD

from . import DOMAIN, CONF_CID
from .api import BayrolPoolAPI

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)

async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""

    _LOGGER.debug("Starting validation of input")

    # Get shared session
    session = async_get_clientsession(hass)
    
    # Initialize API without credentials (like test_api.py)
    api = BayrolPoolAPI(session)

    try:
        # Test login (passing credentials directly like test_api.py)
        _LOGGER.debug("Testing login...")
        if not await api.login(data[CONF_USERNAME], data[CONF_PASSWORD]):
            _LOGGER.error("Login failed")
            raise InvalidAuth
        
        _LOGGER.debug("Login successful")

        # Get list of controllers
        _LOGGER.debug("Discovering controllers...")
        controllers = await api.get_controllers()
        if not controllers:
            _LOGGER.error("No controllers found")
            raise CannotConnect
        
        _LOGGER.debug(f"Found {len(controllers)} controller(s)")
        
        # Test data fetch for each controller (like test_api.py)
        for controller in controllers:
            _LOGGER.debug(f"Testing controller: {controller['name']} (CID: {controller['cid']})...")
            
            controller_data = await api.get_data(controller['cid'])
            if not controller_data:
                _LOGGER.error("No data found for controller")
                raise CannotConnect
            
            _LOGGER.debug("Data fetch successful")
            _LOGGER.debug("Current values: %s", controller_data)

        return {
            "controllers": controllers,
            "username": data[CONF_USERNAME],
            "password": data[CONF_PASSWORD]
        }

    except aiohttp.ClientError as err:
        _LOGGER.error("Error connecting to Bayrol Pool Access: %s", err)
        raise CannotConnect
    except Exception as err:
        _LOGGER.error("Unexpected error: %s", err)
        raise CannotConnect

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Bayrol Pool Controller."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
                
                # Create an entry for each controller
                for controller in info["controllers"]:
                    entry_data = {
                        CONF_USERNAME: info["username"],
                        CONF_PASSWORD: info["password"],
                        CONF_CID: controller["cid"],
                        "device_name": controller["name"]
                    }
                    
                    # Set unique ID based on CID
                    await self.async_set_unique_id(f"bayrol_{controller['cid']}")
                    self._abort_if_unique_id_configured()
                    
                    title = f"{controller['name']} ({controller['cid']})"
                    return self.async_create_entry(title=title, data=entry_data)

            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""

class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
