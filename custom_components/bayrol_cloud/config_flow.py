"""Config flow for Bayrol Pool Controller integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
import aiohttp

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD

from . import DOMAIN, CONF_CID
from .client.bayrol_api import BayrolPoolAPI
from .const import CONF_SETTINGS_PASSWORD

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_SETTINGS_PASSWORD, default="1234"): str,
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
            
            # If settings password is provided, set and validate it
            if CONF_SETTINGS_PASSWORD in data:
                _LOGGER.debug("Setting and testing settings password...")
                
                # First set the password
                if not await api.set_controller_password(controller['cid'], data[CONF_SETTINGS_PASSWORD]):
                    _LOGGER.error("Failed to set settings password")
                    raise InvalidSettingsAuth
                
                # Then verify we can get access with it
                if not await api.get_controller_access(controller['cid'], data[CONF_SETTINGS_PASSWORD]):
                    _LOGGER.error("Failed to verify settings password")
                    raise InvalidSettingsAuth
                
                _LOGGER.debug("Settings password validated successfully")

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
                    
                    # Add settings password if provided
                    if CONF_SETTINGS_PASSWORD in user_input:
                        entry_data[CONF_SETTINGS_PASSWORD] = user_input[CONF_SETTINGS_PASSWORD]
                    
                    # Set unique ID based on CID
                    await self.async_set_unique_id(f"bayrol_{controller['cid']}")
                    self._abort_if_unique_id_configured()
                    
                    title = f"{controller['name']} ({controller['cid']})"
                    return self.async_create_entry(title=title, data=entry_data)

            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except InvalidSettingsAuth:
                errors["base"] = "invalid_settings_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)

class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Bayrol Pool Controller."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage options."""
        if user_input is not None:
            # Validate the new settings password
            session = async_get_clientsession(self.hass)
            api = BayrolPoolAPI(session)

            try:
                # Login first
                if not await api.login(
                    self.config_entry.data[CONF_USERNAME],
                    self.config_entry.data[CONF_PASSWORD]
                ):
                    return self.async_abort(reason="auth_failed")

                # First set the new password
                if not await api.set_controller_password(
                    self.config_entry.data[CONF_CID],
                    user_input[CONF_SETTINGS_PASSWORD]
                ):
                    _LOGGER.error("Failed to set new settings password")
                    return self.async_show_form(
                        step_id="init",
                        data_schema=vol.Schema({
                            vol.Required(
                                CONF_SETTINGS_PASSWORD,
                                default=self.config_entry.data.get(CONF_SETTINGS_PASSWORD, "1234")
                            ): str,
                        }),
                        errors={"base": "invalid_settings_auth"},
                    )

                # Then verify we can get access with it
                if not await api.get_controller_access(
                    self.config_entry.data[CONF_CID],
                    user_input[CONF_SETTINGS_PASSWORD]
                ):
                    _LOGGER.error("Failed to verify new settings password")
                    return self.async_show_form(
                        step_id="init",
                        data_schema=vol.Schema({
                            vol.Required(
                                CONF_SETTINGS_PASSWORD,
                                default=self.config_entry.data.get(CONF_SETTINGS_PASSWORD, "1234")
                            ): str,
                        }),
                        errors={"base": "invalid_settings_auth"},
                    )

                # Update the config entry with the new settings password
                new_data = {**self.config_entry.data}
                new_data[CONF_SETTINGS_PASSWORD] = user_input[CONF_SETTINGS_PASSWORD]
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data=new_data
                )

                # Reload the integration to apply the new settings
                await self.hass.config_entries.async_reload(self.config_entry.entry_id)

                return self.async_create_entry(title="", data=user_input)

            except Exception as err:
                _LOGGER.error("Error validating settings password: %s", err)
                return self.async_show_form(
                    step_id="init",
                    data_schema=vol.Schema({
                        vol.Required(
                            CONF_SETTINGS_PASSWORD,
                            default=self.config_entry.data.get(CONF_SETTINGS_PASSWORD, "1234")
                        ): str,
                    }),
                    errors={"base": "unknown"},
                )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(
                    CONF_SETTINGS_PASSWORD,
                    default=self.config_entry.data.get(CONF_SETTINGS_PASSWORD, "1234")
                ): str,
            }),
        )

class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""

class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""

class InvalidSettingsAuth(HomeAssistantError):
    """Error to indicate there is invalid settings password."""
