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

from .const import (
    DOMAIN,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_DISTANCE,
    CONF_LOCATION_LAT,
    CONF_LOCATION_LON,
    CONF_DISTANCE,
    CONF_USE_LOCATION_FILTER,
)
from .tankille_client import ApiError, AuthenticationError, TankilleClient

_LOGGER = logging.getLogger(__name__)

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
    
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            try:
                # Validate login credentials first
                info = await validate_input(self.hass, user_input)
                
                # Validate location data if location filtering is enabled
                if user_input.get(CONF_USE_LOCATION_FILTER):
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
                    except ValueError:
                        errors["base"] = "invalid_input"
                
                if not errors:
                    # Check if we already have an entry for this email
                    await self.async_set_unique_id(user_input[CONF_EMAIL])
                    self._abort_if_unique_id_configured()
                    
                    return self.async_create_entry(title=info["title"], data=user_input)
                
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
        
        # Get default location from Home Assistant if available
        default_lat = self.hass.config.latitude
        default_lon = self.hass.config.longitude
        
        STEP_USER_DATA_SCHEMA = vol.Schema(
            {
                vol.Required(CONF_EMAIL): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
                vol.Optional(CONF_USE_LOCATION_FILTER, default=True): bool,
                vol.Optional(CONF_LOCATION_LAT, default=str(default_lat)): str,
                vol.Optional(CONF_LOCATION_LON, default=str(default_lon)): str,
                vol.Optional(CONF_DISTANCE, default=DEFAULT_DISTANCE): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=1000, max=50000)
                ),
            }
        )
        
        return self.async_show_form(
            step_id="user", 
            data_schema=STEP_USER_DATA_SCHEMA, 
            errors=errors,
            description_placeholders={
                "info": "Configure Tankille integration. Location filtering is recommended to avoid creating too many sensors (2-15 km range recommended).",
                "current_lat": str(default_lat),
                "current_lon": str(default_lon),
                "location_info": f"Default location: {default_lat:.6f}, {default_lon:.6f}"
            }
        )

class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""

class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""