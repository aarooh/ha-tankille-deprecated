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
    CONF_IGNORED_CHAINS,
    CONF_FUELS,
    CONF_STATION_NAMES,
    FUEL_TYPES,
    FUEL_TYPE_NAMES,
    DEFAULT_FUEL_TYPES,
    COMMON_CHAINS,
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

                # Process fuel types - convert list to comma-separated string
                if CONF_FUELS in user_input and isinstance(
                    user_input[CONF_FUELS], list
                ):
                    user_input[CONF_FUELS] = ",".join(user_input[CONF_FUELS])

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
        default_ignored_chains = ""
        default_fuels = DEFAULT_FUEL_TYPES  # Default to most common fuel types
        default_station_names = ""

        STEP_USER_DATA_SCHEMA = vol.Schema(
            {
                vol.Required(CONF_EMAIL): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
                vol.Optional(CONF_USE_LOCATION_FILTER, default=True): bool,
                vol.Optional(CONF_LOCATION_LAT, default=str(default_lat)): str,
                vol.Optional(CONF_LOCATION_LON, default=str(default_lon)): str,
                vol.Optional(CONF_DISTANCE, default=DEFAULT_DISTANCE): vol.All(
                    vol.Coerce(int), vol.Range(min=1000, max=50000)
                ),
                vol.Optional(CONF_IGNORED_CHAINS, default=default_ignored_chains): str,
                vol.Optional(CONF_STATION_NAMES, default=default_station_names): str,
                vol.Optional(CONF_FUELS, default=default_fuels): cv.multi_select(
                    {
                        fuel_code: f"{FUEL_TYPE_NAMES[fuel_code]} ({fuel_code})"
                        for fuel_code in FUEL_TYPES
                    }
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders={
                "info": "Configure Tankille integration. Location filtering is strongly recommended to avoid creating hundreds of sensors.\n\nTip: Use 2-5 km radius in cities, 10-15 km in rural areas.\n\nYou can ignore specific gas station chains (e.g., 'Neste, ABC'), add specific stations by name (e.g., 'Shell Vantaa, Neste Espoo') even if outside radius, and select which fuel types to monitor."
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> OptionsFlowHandler:
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle an options flow for Tankille."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
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

                # Process fuel types - convert list to comma-separated string
                if CONF_FUELS in user_input and isinstance(
                    user_input[CONF_FUELS], list
                ):
                    user_input[CONF_FUELS] = ",".join(user_input[CONF_FUELS])

                if not errors:
                    # Store options in the options field, not data
                    return self.async_create_entry(title="", data=user_input)

            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception in options flow")
                errors["base"] = "unknown"

        # Get current values from options OR data (fallback for backward compatibility)
        def get_current_value(key, default):
            # Check options first, then data
            return self.config_entry.options.get(key, 
                   self.config_entry.data.get(key, default))

        current_scan_interval = get_current_value(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        current_use_location_filter = get_current_value(CONF_USE_LOCATION_FILTER, True)
        current_lat = get_current_value(
            CONF_LOCATION_LAT, str(self.hass.config.latitude)
        )
        current_lon = get_current_value(
            CONF_LOCATION_LON, str(self.hass.config.longitude)
        )
        current_distance = get_current_value(CONF_DISTANCE, DEFAULT_DISTANCE)
        current_ignored_chains = get_current_value(CONF_IGNORED_CHAINS, "")
        current_station_names = get_current_value(CONF_STATION_NAMES, "")

        # Handle fuel types - convert from comma-separated string to list
        current_fuels_str = get_current_value(CONF_FUELS, ",".join(DEFAULT_FUEL_TYPES))
        if isinstance(current_fuels_str, str):
            current_fuels = [
                f.strip() for f in current_fuels_str.split(",") if f.strip()
            ]
        else:
            current_fuels = current_fuels_str or DEFAULT_FUEL_TYPES

        OPTIONS_SCHEMA = vol.Schema(
            {
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=current_scan_interval,
                ): int,
                vol.Optional(
                    CONF_USE_LOCATION_FILTER,
                    default=current_use_location_filter,
                ): bool,
                vol.Optional(
                    CONF_LOCATION_LAT,
                    default=current_lat,
                ): str,
                vol.Optional(
                    CONF_LOCATION_LON,
                    default=current_lon,
                ): str,
                vol.Optional(
                    CONF_DISTANCE,
                    default=current_distance,
                ): vol.All(vol.Coerce(int), vol.Range(min=1000, max=50000)),
                vol.Optional(
                    CONF_IGNORED_CHAINS,
                    default=current_ignored_chains,
                ): str,
                vol.Optional(
                    CONF_STATION_NAMES,
                    default=current_station_names,
                ): str,
                vol.Optional(
                    CONF_FUELS,
                    default=current_fuels,
                ): cv.multi_select(
                    {
                        fuel_code: f"{FUEL_TYPE_NAMES[fuel_code]} ({fuel_code})"
                        for fuel_code in FUEL_TYPES
                    }
                ),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=OPTIONS_SCHEMA,
            errors=errors,
            description_placeholders={
                "info": "Update Tankille integration settings.\n\n• Station Names: Comma-separated list of station names to include even if outside location filter (e.g., 'Shell Vantaa, Neste Espoo')\n• Ignored Chains: Comma-separated list of gas station chains to ignore (e.g., 'Neste, ABC, St1')\n• Fuel Types: Select which fuel types to monitor\n• Location: Adjust search area for nearby stations"
            },
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""