"""Sensor platform for Tankille integration."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, CURRENCY_EURO
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    CONF_STATION_IDS,
    CONF_LOCATION,
    CONF_DISTANCE,
    CONF_LATITUDE,
    CONF_LONGITUDE,
)
from .coordinator import TankilleDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Define sensor types
SENSOR_TYPES: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="95 E10",
        name="95 E10 Price",
        icon="mdi:gas-station",
        native_unit_of_measurement=CURRENCY_EURO,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="98 E5",
        name="98 E5 Price",
        icon="mdi:gas-station",
        native_unit_of_measurement=CURRENCY_EURO,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="Diesel",
        name="Diesel Price",
        icon="mdi:gas-station",
        native_unit_of_measurement=CURRENCY_EURO,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # Add other fuel types if needed
)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: Optional[DiscoveryInfoType] = None,
) -> None:
    """Set up the Tankille sensor platform."""
    if discovery_info is None:
        return

    coordinator = hass.data[DOMAIN]["coordinator"]
    client = hass.data[DOMAIN]["client"]
    config = discovery_info["config"]

    entities = []

    # If location is provided, get stations by location
    if CONF_LOCATION in config:
        location_config = config[CONF_LOCATION]
        lat = location_config[CONF_LOCATION_LAT]
        lon = location_config[CONF_LOCATION_LON]
        distance = location_config.get(CONF_DISTANCE)

        try:
            stations = await client.get_stations_by_location_async(lat, lon, distance)
            for station in stations:
                for fuel_type in station["fuels"]:
                    if fuel_type in FUEL_TYPES:
                        entities.append(
                            TankilleFuelPriceSensor(
                                coordinator, station["_id"], fuel_type
                            )
                        )
        except Exception as err:
            _LOGGER.error("Error fetching stations by location: %s", err)

    # Add specific station IDs if provided
    for station_id in config.get(CONF_STATION_IDS, []):
        try:
            station = await client.get_station_async(station_id)
            for fuel_type in station["fuels"]:
                if fuel_type in FUEL_TYPES:
                    entities.append(
                        TankilleFuelPriceSensor(coordinator, station_id, fuel_type)
                    )
        except Exception as err:
            _LOGGER.error("Error fetching station %s: %s", station_id, err)

    async_add_entities(entities, True)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tankille sensor based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities = []

    # Process all stations from the coordinator
    for station_id, station_data in coordinator.stations.items():
        for fuel_type in station_data["fuels"]:
            if fuel_type in FUEL_TYPES:
                entities.append(
                    TankilleFuelPriceSensor(coordinator, station_id, fuel_type)
                )

    async_add_entities(entities, True)


class TankilleFuelPriceSensor(CoordinatorEntity, SensorEntity):
    """Represents a fuel price sensor from Tankille."""

    def __init__(
        self,
        coordinator: TankilleDataUpdateCoordinator,
        station_id: str,
        fuel_type: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.station_id = station_id
        self.fuel_type = fuel_type
        self._attr_native_unit_of_measurement = CURRENCY_EURO
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_state_class = SensorStateClass.MEASUREMENT

        # Initialize to get station data for the first time
        self._station = self.coordinator.stations.get(station_id, {})

        # Set entity ID and unique ID
        self._attr_unique_id = f"{DOMAIN}_{station_id}_{fuel_type}"

        # Set entity name based on station name and fuel type
        station_name = self._station.get("name", "Unknown Station")
        fuel_name = FUEL_TYPE_NAMES.get(fuel_type, fuel_type)
        self._attr_name = f"{station_name} {fuel_name}"

        # Initialize device info
        self._init_device_info()

    def _init_device_info(self) -> None:
        """Initialize device info."""
        if not self._station:
            return

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.station_id)},
            name=self._station.get("name", "Unknown Station"),
            manufacturer=self._station.get("chain", "Unknown"),
            model=self._station.get("brand", "Unknown"),
        )

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        if not self.coordinator.last_update_success:
            return False

        # Make sure the station exists in the coordinator data
        if self.station_id not in self.coordinator.stations:
            return False

        return True

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if not self.available:
            return None

        station = self.coordinator.stations[self.station_id]

        # Find the latest price for this fuel type
        for price in station.get("price", []):
            if price.get("tag") == self.fuel_type:
                return price.get("price")

        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return the state attributes."""
        attrs = {}

        if not self.available:
            return attrs

        station = self.coordinator.stations[self.station_id]

        # Basic station info
        attrs[ATTR_STATION_NAME] = station.get("name")
        attrs[ATTR_STATION_BRAND] = station.get("brand")
        attrs[ATTR_STATION_CHAIN] = station.get("chain")
        attrs[ATTR_AVAILABLE_FUELS] = ", ".join(station.get("fuels", []))

        # Location information
        if "address" in station:
            address = station["address"]
            attrs[ATTR_STATION_STREET] = address.get("street")
            attrs[ATTR_STATION_CITY] = address.get("city")
            attrs[ATTR_STATION_ZIPCODE] = address.get("zipcode")
            attrs[ATTR_STATION_ADDRESS] = (
                f"{address.get('street')}, {address.get('city')} {address.get('zipcode')}"
            )

        # Coordinates
        if "location" in station and "coordinates" in station["location"]:
            coords = station["location"]["coordinates"]
            if len(coords) >= 2:
                attrs[ATTR_STATION_LONGITUDE] = coords[0]
                attrs[ATTR_STATION_LATITUDE] = coords[1]

        # Last update time
        if "updated" in station:
            attrs[ATTR_STATION_UPDATED] = station["updated"]

        # Price specific information
        for price in station.get("price", []):
            if price.get("tag") == self.fuel_type:
                attrs[ATTR_STATION_PRICE_UPDATED] = price.get("updated")
                attrs[ATTR_STATION_PRICE_REPORTER] = price.get("reporter")
                attrs[ATTR_STATION_PRICE_DELTA] = price.get("delta")
                break

        return attrs
