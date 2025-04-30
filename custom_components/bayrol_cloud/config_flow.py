"""Config flow for Bayrol Pool Controller integration."""
from __future__ import annotations

import logging

from .helpers import conditional_log
from typing import Any, Dict, List, Optional

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
        vol.Optional("refresh_interval", default=DEFAULT_REFRESH_INTERVAL): vol.All(
            vol.Coerce(int),
            vol.Range(min=MIN_REFRESH_INTERVAL)
        ),
    }
)

STEP_CONTROLLER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CID): str,
    }
)

STEP_CONTROLLER_SETTINGS_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_SETTINGS_PASSWORD): str,
    }
)

async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""

    conditional_log(_LOGGER, logging.DEBUG, "Starting validation of input", debug_mode=False)

    # Get shared session
    session = async_get_clientsession(hass)
    
    # Initialize API without credentials
    api = BayrolPoolAPI(session)

    try:
        # Test login
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


async def validate_controller(hass: HomeAssistant, data: dict[str, Any], cid: str) -> dict[str, Any]:
    """Validate specific controller by ID."""
    
    conditional_log(_LOGGER, logging.DEBUG, f"Validating controller with ID {cid}", debug_mode=False)
    
    # Get shared session
    session = async_get_clientsession(hass)
    
    # Initialize API
    api = BayrolPoolAPI(session)
    
    try:
        # Test login
        if not await api.login(data[CONF_USERNAME], data[CONF_PASSWORD]):
            _LOGGER.error("Login failed")
            raise InvalidAuth
            
        # Test if we can access the controller
        controller_data = await api.get_data(cid)
        if not controller_data:
            _LOGGER.error(f"No data found for controller ID {cid}")
            raise CannotConnect
            
        # Get controllers list to find the name
        controllers = await api.get_controllers()
        
        # Try to find matching controller in the list
        controller_name = None
        for controller in controllers:
            if controller['cid'] == cid:
                controller_name = controller['name']
                break
                
        # If not found in the list, use a generic name
        if not controller_name:
            controller_name = f"Pool Controller ({cid})"
            
        return {
            "name": controller_name,
            "cid": cid
        }
            
    except aiohttp.ClientError as err:
        _LOGGER.error(f"Error connecting to controller {cid}: {err}")
        raise CannotConnect
    except Exception as err:
        _LOGGER.error(f"Unexpected error validating controller {cid}: {err}")
        raise CannotConnect


async def validate_controller_password(hass: HomeAssistant, data: dict[str, Any], cid: str, password: str) -> bool:
    """Validate settings password for a specific controller."""
    
    if not password:
        return True  # No password provided, nothing to validate
        
    conditional_log(_LOGGER, logging.DEBUG, f"Validating settings password for controller {cid}", debug_mode=False)
    
    # Get shared session
    session = async_get_clientsession(hass)
    
    # Initialize API
    api = BayrolPoolAPI(session)
    
    try:
        # Login first
        if not await api.login(data[CONF_USERNAME], data[CONF_PASSWORD]):
            _LOGGER.error("Login failed")
            raise InvalidAuth
            
        # Try to get access with the password
        access_granted = await api.get_controller_access(cid, password)
        
        if not access_granted:
            _LOGGER.warning(f"Settings password validation failed for controller {cid}")
            return False
            
        return True
        
    except Exception as err:
        _LOGGER.error(f"Error validating settings password for controller {cid}: {err}")
        return False

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Bayrol Pool Controller."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._credentials: Dict[str, Any] = {}
        self._controllers: List[Dict[str, str]] = []
        self._current_controller: Dict[str, str] = {}
        self._discovered_controllers: List[Dict[str, str]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Store credentials and refresh interval for use in later steps
                self._credentials = {
                    CONF_USERNAME: user_input[CONF_USERNAME],
                    CONF_PASSWORD: user_input[CONF_PASSWORD],
                    "refresh_interval": user_input.get("refresh_interval", DEFAULT_REFRESH_INTERVAL)
                }
                
                # Validate the credentials and get the list of controllers
                info = await validate_input(self.hass, self._credentials)
                self._discovered_controllers = info["controllers"]
                
                # Store controller info for next step
                if self._discovered_controllers:
                    # Show the menu to either select a discovered controller or add a new one
                    return await self.async_step_select_controller()
                else:
                    # No controllers found - go directly to manual entry
                    return await self.async_step_controller()
                    
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
        
    async def async_step_select_controller(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle controller selection."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            if user_input.get("controller_action") == "manual":
                # User chose to manually add a controller by ID
                return await self.async_step_controller()
            else:
                # User selected a discovered controller
                controller_index = int(user_input["controller_action"])
                if 0 <= controller_index < len(self._discovered_controllers):
                    self._current_controller = self._discovered_controllers[controller_index]
                    # Move to settings password step for this controller
                    return await self.async_step_controller_settings()
                else:
                    errors["base"] = "invalid_controller_selection"
        
        # Build the options for controller selection
        controller_options = {}
        for i, controller in enumerate(self._discovered_controllers):
            controller_options[str(i)] = f"{controller['name']} (ID: {controller['cid']})"
        
        # Add option for manual entry
        controller_options["manual"] = "Add controller by ID"
        
        return self.async_show_form(
            step_id="select_controller",
            data_schema=vol.Schema({
                vol.Required("controller_action"): vol.In(controller_options)
            }),
            errors=errors,
        )
        
    async def async_step_controller(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle manual controller ID entry."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            try:
                cid = user_input[CONF_CID]
                
                # Check if this controller is already configured
                await self.async_set_unique_id(f"bayrol_{cid}")
                self._abort_if_unique_id_configured()
                
                # Validate that the controller exists and is accessible
                controller_info = await validate_controller(self.hass, self._credentials, cid)
                
                # Store controller info for the next step
                self._current_controller = controller_info
                
                # Move to settings password step
                return await self.async_step_controller_settings()
                
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception as err:
                _LOGGER.exception("Error adding controller: %s", err)
                errors["base"] = "unknown"
                
        return self.async_show_form(
            step_id="controller",
            data_schema=STEP_CONTROLLER_SCHEMA,
            errors=errors
        )
        
    async def async_step_controller_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle settings password entry for a specific controller."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            try:
                settings_password = user_input.get(CONF_SETTINGS_PASSWORD)
                
                # If a password was provided, validate it
                if settings_password:
                    password_valid = await validate_controller_password(
                        self.hass,
                        self._credentials,
                        self._current_controller["cid"],
                        settings_password
                    )
                    
                    if not password_valid:
                        errors[CONF_SETTINGS_PASSWORD] = "invalid_settings_auth"
                        # Keep the password field empty on error
                        user_input[CONF_SETTINGS_PASSWORD] = None
                
                # If no errors, create the entry
                if not errors:
                    # Create entry data with credentials, controller info, and settings password
                    entry_data = {
                        CONF_USERNAME: self._credentials[CONF_USERNAME],
                        CONF_PASSWORD: self._credentials[CONF_PASSWORD],
                        CONF_CID: self._current_controller["cid"],
                        "device_name": self._current_controller["name"],
                        "refresh_interval": self._credentials.get("refresh_interval", DEFAULT_REFRESH_INTERVAL)
                    }
                    
                    # Add settings password if provided and valid
                    if settings_password and not errors:
                        entry_data[CONF_SETTINGS_PASSWORD] = settings_password
                    
                    title = f"{self._current_controller['name']} ({self._current_controller['cid']})"
                    return self.async_create_entry(title=title, data=entry_data)
                
            except Exception as err:
                _LOGGER.exception("Error setting up controller: %s", err)
                errors["base"] = "unknown"
        
        return self.async_show_form(
            step_id="controller_settings",
            data_schema=STEP_CONTROLLER_SETTINGS_SCHEMA,
            errors=errors,
            description_placeholders={
                "controller_name": self._current_controller.get("name", "Unknown Controller"),
                "controller_id": self._current_controller.get("cid", "Unknown ID")
            }
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)
        
    async def async_step_import(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle import from configuration.yaml."""
        return await self.async_step_user(user_input)

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
