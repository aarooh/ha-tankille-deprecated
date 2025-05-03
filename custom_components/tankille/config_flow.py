"""Config flow for Tankille integration."""
from __future__ import annotations
import logging
from typing import Any
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_DISTANCE,
    CONF_LOCATION_LAT,
    CONF_LOCATION_LON,
    CONF_DISTANCE,
    CONF_USE_LOCATION_FILTER,
    CONF_STATION_IDS,
)
from .tankille_client import ApiError, AuthenticationError, TankilleClient

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
    }
)

async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    client = TankilleClient()
    try:
        await client.login(data[CONF_EMAIL], data[CONF_PASSWORD])
    except AuthenticationError as err:
        raise InvalidAuth from err
    except ApiError as err:
        raise CannotConnect from err
    
    # Return info that you want to store in the config entry.
    return {"title": f"Tankille ({data[CONF_EMAIL]})"}

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tankille."""
    
    VERSION = 1
    
    def __init__(self):
        """Initialize the config flow."""
        self._data = {}
        self._client = None
        
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
                self._data = user_input
                
                # Check if we already have an entry for this email
                await self.async_set_unique_id(user_input[CONF_EMAIL])
                self._abort_if_unique_id_configured()
                
                # Move to location configuration step
                return await self.async_step_location()
                
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

    async def async_step_location(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle location configuration step."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            self._data.update(user_input)
            
            if user_input.get(CONF_USE_LOCATION_FILTER):
                # Continue to configure location parameters
                return await self.async_step_location_params()
            else:
                # Skip location filtering, complete setup
                return self.async_create_entry(
                    title=f"Tankille ({self._data[CONF_EMAIL]})",
                    data=self._data
                )
        
        # Ask if the user wants to use location filtering
        schema = vol.Schema({
            vol.Required(CONF_USE_LOCATION_FILTER, default=True): bool,
        })
        
        return self.async_show_form(
            step_id="location",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "info": "Would you like to filter stations by location? This is recommended to avoid creating too many sensors."
            }
        )

    async def async_step_location_params(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle location parameters step."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            self._data.update(user_input)
            
            # Validate the coordinates and distance
            try:
                lat = float(user_input[CONF_LOCATION_LAT])
                lon = float(user_input[CONF_LOCATION_LON])
                distance = int(user_input[CONF_DISTANCE])
                
                if not (-90 <= lat <= 90):
                    errors["base"] = "invalid_latitude"
                elif not (-180 <= lon <= 180):
                    errors["base"] = "invalid_longitude"
                elif not (1000 <= distance <= 50000):
                    errors["base"] = "invalid_distance"
                else:
                    # Complete the setup
                    return self.async_create_entry(
                        title=f"Tankille ({self._data[CONF_EMAIL]})",
                        data=self._data
                    )
            except ValueError:
                errors["base"] = "invalid_input"
        
        # Get default location from Home Assistant if available
        default_lat = self.hass.config.latitude
        default_lon = self.hass.config.longitude
        
        schema = vol.Schema({
            vol.Required(CONF_LOCATION_LAT, default=default_lat): cv.string,
            vol.Required(CONF_LOCATION_LON, default=default_lon): cv.string,
            vol.Required(CONF_DISTANCE, default=10000): vol.All(
                vol.Coerce(int),
                vol.Range(min=1000, max=50000)
            ),
        })
        
        return self.async_show_form(
            step_id="location_params",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "info": "Enter your location coordinates and search radius. Recommended distance: 2-15 km (2000-15000 meters)."
            }
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)

class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Tankille integration."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = {
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=self.config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ): int,
        }

        if self.config_entry.data.get(CONF_USE_LOCATION_FILTER):
            options.update({
                vol.Optional(
                    CONF_LOCATION_LAT,
                    default=self.config_entry.data.get(CONF_LOCATION_LAT),
                ): cv.string,
                vol.Optional(
                    CONF_LOCATION_LON,
                    default=self.config_entry.data.get(CONF_LOCATION_LON),
                ): cv.string,
                vol.Optional(
                    CONF_DISTANCE,
                    default=self.config_entry.data.get(CONF_DISTANCE, DEFAULT_DISTANCE),
                ): vol.All(vol.Coerce(int), vol.Range(min=1000, max=50000)),
            })

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(options),
        )

class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""

class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""