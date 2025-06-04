"""
Tankille integration for Home Assistant.

This integration allows you to track fuel prices from stations in Finland.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional

import voluptuous as vol

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    UnitOfVolume,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    CONF_DISTANCE,
    CONF_LOCATION,
    CONF_LOCATION_LAT,
    CONF_LOCATION_LON,
    CONF_STATION_ID,
    CONF_STATION_IDS,
    CONF_USE_LOCATION_FILTER,
    CONF_IGNORED_CHAINS,
    CONF_FUELS,
    CONF_STATION_NAMES,
    DEFAULT_DISTANCE,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    FUEL_TYPES,
)
from .tankille_client import TankilleClient, ApiError, AuthenticationError

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = ["sensor"]

# Define the configuration schema for YAML setup
CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_EMAIL): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
                vol.Optional(
                    CONF_SCAN_INTERVAL, default=timedelta(minutes=30)
                ): cv.time_period,
                vol.Optional(CONF_LOCATION): vol.Schema(
                    {
                        vol.Required("lat"): cv.latitude,
                        vol.Required("lon"): cv.longitude,
                        vol.Optional(CONF_DISTANCE, default=15000): cv.positive_int,
                    }
                ),
                vol.Optional(CONF_STATION_IDS): vol.All(cv.ensure_list, [cv.string]),
                vol.Optional(CONF_IGNORED_CHAINS): cv.string,
                vol.Optional(CONF_FUELS): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Tankille component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tankille from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Get the credentials from the config entry
    email = entry.data[CONF_EMAIL]
    password = entry.data[CONF_PASSWORD]
    scan_interval = entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    client = TankilleClient()

    try:
        # Force login to ensure fresh tokens
        await client.login(email, password, force=True)
        _LOGGER.info("Successfully authenticated with Tankille API")
    except AuthenticationError as err:
        _LOGGER.error("Failed to authenticate with Tankille API: %s", err)
        if "Already logged in" in str(err):
            # This is not really an error, just try to proceed
            _LOGGER.info("Using existing authentication token")
        else:
            return False
    except ApiError as err:
        _LOGGER.error("API error during authentication: %s", err)
        return False
    except Exception as err:
        _LOGGER.exception("Unexpected error during authentication: %s", err)
        return False

    coordinator = TankilleDataUpdateCoordinator(
        hass,
        client=client,
        scan_interval=timedelta(seconds=scan_interval),
        config_entry=entry,
    )

    # Fetch initial data
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        _LOGGER.exception("Error during initial data refresh: %s", err)
        # Clean up the client session before returning
        if client.session and not client.session.closed:
            await client.session.close()
        return False

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "client": client,
    }

    # Set up listeners for options updates
    entry.async_on_unload(entry.add_update_listener(async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update without full reload."""
    _LOGGER.debug("Configuration options updated, managing entities dynamically")
    
    coordinator: TankilleDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    
    # Update the coordinator's config entry reference
    coordinator.config_entry = entry
    
    # Handle entity management directly without reload
    from .sensor import handle_config_update
    await handle_config_update(hass, entry, coordinator)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Get the client and close its session
        client = hass.data[DOMAIN][entry.entry_id]["client"]
        if client.session and not client.session.closed:
            await client.session.close()

        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class TankilleDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Tankille data."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: TankilleClient,
        scan_interval: timedelta,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize global Tankille data updater."""
        self.client = client
        self.config_entry = config_entry
        self.retry_count = 0
        self.max_retries = 3

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=scan_interval,
        )

    def get_config_value(self, key: str, default=None):
        """Get configuration value from options (preferred) or data (fallback)."""
        return self.config_entry.options.get(key, self.config_entry.data.get(key, default))

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from Tankille API."""
        # Reset retry count if this is a scheduled update
        if self.retry_count >= self.max_retries:
            self.retry_count = 0

        # Get current configuration values
        use_location_filter = self.get_config_value(CONF_USE_LOCATION_FILTER, False)
        lat = self.get_config_value(CONF_LOCATION_LAT)
        lon = self.get_config_value(CONF_LOCATION_LON)
        distance = self.get_config_value(CONF_DISTANCE, DEFAULT_DISTANCE)
        station_names_str = self.get_config_value(CONF_STATION_NAMES, "")

        # Parse station names
        station_names = [
            name.strip() for name in station_names_str.split(",") if name.strip()
        ] if station_names_str else []

        # Log current configuration for debugging
        _LOGGER.debug(
            "Tankille coordinator updating with location filter: %s, station names: %s, ignored chains: %s, fuels: %s",
            use_location_filter,
            station_names,
            self.get_config_value(CONF_IGNORED_CHAINS, "None"),
            self.get_config_value(CONF_FUELS, "Default"),
        )

        try:
            # First check if we need to refresh authentication
            if not self.client.token:
                _LOGGER.info("No authentication token, attempting to refresh login")
                try:
                    await self.client._auth_async()
                    _LOGGER.info("Successfully refreshed authentication token")
                except (AuthenticationError, ApiError) as err:
                    _LOGGER.error("Failed to refresh authentication: %s", err)
                    raise UpdateFailed(f"Authentication error: {err}")

            # Get stations based on configuration
            try:
                stations = []
                stations_by_location = []
                stations_by_name = []

                # Get stations by location if location filter is enabled
                if use_location_filter and lat and lon:
                    _LOGGER.info(
                        "Fetching stations within %s meters of %.6f, %.6f",
                        distance,
                        float(lat),
                        float(lon),
                    )
                    stations_by_location = await self.client.get_stations_by_location(
                        float(lat), float(lon), int(distance)
                    )
                    stations.extend(stations_by_location)
                elif not station_names:
                    # If no location filter and no station names, get all stations
                    _LOGGER.info("Fetching all stations")
                    stations = await self.client.get_stations()

                # Get additional stations by name if specified
                if station_names:
                    _LOGGER.info("Fetching stations by names: %s", station_names)
                    stations_by_name = await self.client.find_stations_by_name(station_names)
                    
                    # Combine stations, avoiding duplicates
                    existing_station_ids = {station.get("_id") for station in stations}
                    for station in stations_by_name:
                        if station.get("_id") not in existing_station_ids:
                            stations.append(station)

                _LOGGER.info(
                    "Found %d stations total (%d by location, %d by name)",
                    len(stations),
                    len(stations_by_location),
                    len([s for s in stations_by_name if s.get("_id") not in {st.get("_id") for st in stations_by_location}])
                )

            except asyncio.TimeoutError:
                self.retry_count += 1
                _LOGGER.warning(
                    "Timeout while fetching stations (attempt %s of %s)",
                    self.retry_count,
                    self.max_retries,
                )
                if self.retry_count < self.max_retries:
                    # Wait before retry (exponential backoff)
                    await asyncio.sleep(2**self.retry_count)
                    return await self._async_update_data()
                raise UpdateFailed("Repeated timeouts while fetching station data")

            # Process stations
            if not stations:
                _LOGGER.warning("No stations returned from API")
                return {}  # Return empty dict instead of None

            result = {}
            for station in stations:
                if "_id" not in station:
                    _LOGGER.warning("Station missing ID: %s", station)
                    continue  # Skip stations without ID

                result[station["_id"]] = station

            # Log some statistics about the data
            _LOGGER.info(
                "Successfully fetched %s stations with %s total fuel prices",
                len(result),
                sum(len(station.get("price", [])) for station in result.values()),
            )

            self.retry_count = 0  # Reset retry count on success
            return result

        except AuthenticationError as err:
            _LOGGER.error("Authentication error during data update: %s", err)
            # Try to re-authenticate once
            try:
                _LOGGER.info("Attempting to refresh authentication token")
                await self.client._auth_async()
                _LOGGER.info("Re-authentication successful, retrying data update")
                return await self._async_update_data()
            except Exception as auth_err:
                _LOGGER.error("Failed to re-authenticate: %s", auth_err)
                raise UpdateFailed(f"Authentication failed: {err}")

        except ApiError as err:
            self.retry_count += 1
            _LOGGER.error(
                "API error during data update (attempt %s of %s): %s",
                self.retry_count,
                self.max_retries,
                err,
            )

            if self.retry_count < self.max_retries:
                # Wait before retry (exponential backoff)
                await asyncio.sleep(2**self.retry_count)
                return await self._async_update_data()

            raise UpdateFailed(f"Repeated API errors: {err}")

        except Exception as err:
            _LOGGER.exception("Unexpected error during data update: %s", err)
            raise UpdateFailed(f"Unexpected error: {err}")