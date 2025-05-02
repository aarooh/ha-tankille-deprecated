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
    DEFAULT_DISTANCE,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    FUEL_TYPES,
)
from .tankille_client import TankilleClient, ApiError, AuthenticationError

_LOGGER = logging.getLogger(__name__)

# Define the domain for the integration
DOMAIN = "tankille"

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
                        vol.Required(CONF_LATITUDE): cv.latitude,
                        vol.Required(CONF_LONGITUDE): cv.longitude,
                        vol.Optional(CONF_DISTANCE, default=15000): cv.positive_int,
                    }
                ),
                vol.Optional(CONF_STATION_IDS): vol.All(cv.ensure_list, [cv.string]),
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

# List of platforms to set up
PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tankille from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Get the credentials from the config entry
    email = entry.data[CONF_EMAIL]
    password = entry.data[CONF_PASSWORD]
    scan_interval = entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    client = TankilleClient()

    try:
        await client.login(email, password)
    except AuthenticationError as err:
        _LOGGER.error("Failed to authenticate with Tankille API: %s", err)
        return False
    except ApiError as err:
        _LOGGER.error("API error during authentication: %s", err)
        return False
    except Exception as err:
        _LOGGER.exception("Unexpected error during authentication: %s", err)
        return False

    coordinator = TankilleDataUpdateCoordinator(
        hass, client=client, scan_interval=timedelta(seconds=scan_interval)
    )

    # Fetch initial data
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        _LOGGER.exception("Error during initial data refresh: %s", err)
        return False

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "client": client,
    }

    await hass.config_entries.async_forward_entry_setup(entry, "sensor")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class TankilleDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Tankille data."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: TankilleClient,
        scan_interval: timedelta,
    ) -> None:
        """Initialize global Tankille data updater."""
        self.client = client
        self.stations: Dict[str, Any] = {}
        self.retry_count = 0
        self.max_retries = 3

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=scan_interval,
        )

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from Tankille API."""
        # Reset retry count if this is a scheduled update
        if self.retry_count >= self.max_retries:
            self.retry_count = 0

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

            # Get all stations
            try:
                stations = await self.client.get_stations_async()
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
                return self.stations  # Return existing data

            result = {}
            for station in stations:
                if "_id" not in station:
                    _LOGGER.warning("Station missing ID: %s", station)
                    continue  # Skip stations without ID

                result[station["_id"]] = station

            # Log some statistics about the data
            _LOGGER.debug(
                "Successfully fetched %s stations with %s total fuel prices",
                len(result),
                sum(len(station.get("price", [])) for station in result.values()),
            )

            self.stations = result
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
