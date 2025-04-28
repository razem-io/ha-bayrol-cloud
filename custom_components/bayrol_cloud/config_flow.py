"""Config flow for Bayrol Pool Controller integration."""
from __future__ import annotations

import logging

from .helpers import conditional_log
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
from .const import (
    CONF_SETTINGS_PASSWORD,
    MIN_REFRESH_INTERVAL,
    DEFAULT_REFRESH_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_SETTINGS_PASSWORD): str,
        vol.Optional("refresh_interval", default=DEFAULT_REFRESH_INTERVAL): vol.All(
            vol.Coerce(int),
            vol.Range(min=MIN_REFRESH_INTERVAL)
        ),
    }
)

async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""

    conditional_log(_LOGGER, logging.DEBUG, "Starting validation of input", debug_mode=False)

    # Get shared session
    session = async_get_clientsession(hass)
    
    # Initialize API without credentials (like test_api.py)
    api = BayrolPoolAPI(session)

    try:
        # Test login (passing credentials directly like test_api.py)
        conditional_log(_LOGGER, logging.DEBUG, "Testing login...", debug_mode=False)
        if not await api.login(data[CONF_USERNAME], data[CONF_PASSWORD]):
            _LOGGER.error("Login failed")
            raise InvalidAuth
        
        conditional_log(_LOGGER, logging.DEBUG, "Login successful", debug_mode=False)

        # Get list of controllers
        conditional_log(_LOGGER, logging.DEBUG, "Discovering controllers...", debug_mode=False)
        controllers = await api.get_controllers()
        if not controllers:
            _LOGGER.error("No controllers found")
            raise CannotConnect
        
        conditional_log(_LOGGER, logging.DEBUG, f"Found {len(controllers)} controller(s)", debug_mode=False)
        
        # Test data fetch for each controller (like test_api.py)
        for controller in controllers:
            conditional_log(_LOGGER, logging.DEBUG, f"Testing controller: {controller['name']} (CID: {controller['cid']})", debug_mode=False)
            
            controller_data = await api.get_data(controller['cid'])
            if not controller_data:
                _LOGGER.error("No data found for controller")
                raise CannotConnect
            
            conditional_log(_LOGGER, logging.DEBUG, "Data fetch successful", debug_mode=False)
            conditional_log(_LOGGER, logging.DEBUG, "Current values: %s", controller_data, debug_mode=False)
            
            # If settings password is provided, try to validate it
            if CONF_SETTINGS_PASSWORD in data and data[CONF_SETTINGS_PASSWORD]:
                conditional_log(_LOGGER, logging.DEBUG, "Testing settings password...", debug_mode=False)
                
                # Try to get access first
                access_granted = await api.get_controller_access(controller['cid'], data[CONF_SETTINGS_PASSWORD])
                
                if not access_granted:
                    _LOGGER.warning("Settings password validation failed")
                    data[CONF_SETTINGS_PASSWORD] = None  # Clear invalid password
                    errors["settings_password"] = "invalid_settings_auth"
                    return {
                        "controllers": controllers,
                        "username": data[CONF_USERNAME],
                        "password": data[CONF_PASSWORD]
                    }

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
            # Get the new settings password
            settings_password = user_input.get(CONF_SETTINGS_PASSWORD)
            
            if settings_password:
                session = async_get_clientsession(self.hass)
                api = BayrolPoolAPI(session)

                try:
                    # Login first
                    if not await api.login(
                        self.config_entry.data[CONF_USERNAME],
                        self.config_entry.data[CONF_PASSWORD]
                    ):
                        return self.async_abort(reason="auth_failed")

                    # Try to get access
                    access_granted = await api.get_controller_access(
                        self.config_entry.data[CONF_CID],
                        settings_password
                    )
                    
                    if not access_granted:
                        _LOGGER.warning("Settings password validation failed")
                        settings_password = None  # Clear invalid password
                        return self.async_show_form(
                            step_id="init",
                            data_schema=vol.Schema({
                                vol.Optional(
                                    CONF_SETTINGS_PASSWORD,
                                    description={"suggested_value": None}
                                ): str,
                            }),
                            errors={"settings_password": "invalid_settings_auth"},
                            description_placeholders={
                                "error_detail": "Invalid settings password - settings will be read-only"
                            }
                        )

                except Exception as err:
                    _LOGGER.error("Error validating settings password: %s", err)
                    settings_password = None
            
            user_input[CONF_SETTINGS_PASSWORD] = settings_password

            # Validate refresh interval
            refresh_interval = user_input.get("refresh_interval", DEFAULT_REFRESH_INTERVAL)
            if refresh_interval < MIN_REFRESH_INTERVAL:
                refresh_interval = MIN_REFRESH_INTERVAL

            # Update the config entry with the new settings
            new_data = {**self.config_entry.data}
            new_data[CONF_SETTINGS_PASSWORD] = user_input.get(CONF_SETTINGS_PASSWORD)
            new_data["refresh_interval"] = refresh_interval
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data=new_data
            )

            # Reload the integration to apply the new settings
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)

            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_SETTINGS_PASSWORD,
                    description={"suggested_value": self.config_entry.data.get(CONF_SETTINGS_PASSWORD)}
                ): str,
                vol.Optional(
                    "refresh_interval",
                    default=self.config_entry.data.get("refresh_interval", DEFAULT_REFRESH_INTERVAL)
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=MIN_REFRESH_INTERVAL)
                ),
            }),
        )

class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""

class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""

class InvalidSettingsAuth(HomeAssistantError):
    """Error to indicate there is invalid settings password."""
