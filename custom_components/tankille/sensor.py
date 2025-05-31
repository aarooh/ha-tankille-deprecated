"""Sensor platform for Tankille integration."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CURRENCY_EURO
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import TankilleDataUpdateCoordinator
from .const import (
    DOMAIN,
    ATTR_STATION_NAME,
    ATTR_STATION_BRAND,
    ATTR_STATION_CHAIN,
    ATTR_STATION_ADDRESS,
    ATTR_STATION_CITY,
    ATTR_STATION_STREET,
    ATTR_STATION_ZIPCODE,
    ATTR_STATION_UPDATED,
    ATTR_STATION_LATITUDE,
    ATTR_STATION_LONGITUDE,
    ATTR_STATION_PRICE_UPDATED,
    ATTR_STATION_PRICE_REPORTER,
    ATTR_STATION_PRICE_DELTA,
    ATTR_AVAILABLE_FUELS,
    FUEL_TYPES,
    FUEL_TYPE_NAMES,
    FUEL_TYPE_NGAS,
    FUEL_TYPE_BGAS,
    FUEL_TYPE_98_PLUS,
    FUEL_TYPE_DIESEL_PLUS,
    FUEL_TYPE_HVO,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tankille sensor based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    # Wait for the coordinator to have data
    if not coordinator.data:
        await coordinator.async_request_refresh()

    entities = []

    # Process all stations from the coordinator
    if coordinator.data:
        for station_id, station_data in coordinator.data.items():
            # Add station update sensor (automatically enabled)
            _LOGGER.debug(
                "Creating Last Updated sensor for station: %s",
                station_data.get("name", station_id),
            )
            entities.append(TankilleStationUpdateSensor(coordinator, station_id))

            for fuel_type in station_data.get("fuels", []):
                if fuel_type in FUEL_TYPES:
                    entities.append(
                        TankilleFuelPriceSensor(coordinator, station_id, fuel_type)
                    )

    _LOGGER.info(
        "Created %d entities (%d stations with Last Updated sensors)",
        len(entities),
        len([e for e in entities if isinstance(e, TankilleStationUpdateSensor)]),
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

        # Initialize station data
        self._station = (
            self.coordinator.data.get(station_id, {}) if self.coordinator.data else {}
        )

        # Set entity ID and unique ID
        self._attr_unique_id = f"{DOMAIN}_{station_id}_{fuel_type}"

        # Set entity name based on station name and fuel type
        station_name = self._station.get("name", "Unknown Station")
        fuel_name = FUEL_TYPE_NAMES.get(fuel_type, fuel_type)
        self._attr_name = f"{station_name} {fuel_name}"

        # Disable less common fuel types by default
        disabled_by_default = [
            FUEL_TYPE_NGAS,  # Natural Gas
            FUEL_TYPE_BGAS,  # Biogas
            FUEL_TYPE_98_PLUS,  # 98 Premium
            FUEL_TYPE_DIESEL_PLUS,  # Diesel Premium
            FUEL_TYPE_HVO,  # HVO Diesel
        ]

        self._attr_entity_registry_enabled_default = (
            fuel_type not in disabled_by_default
        )

        # Initialize device info
        self._init_device_info()

    def _init_device_info(self) -> None:
        """Initialize device info."""
        if not self._station:
            return

        device_updated = self._format_timestamp(self._station.get("updated"))

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.station_id)},
            name=self._station.get("name", "Unknown Station"),
            manufacturer=self._station.get("chain", "Unknown"),
            model=self._station.get("brand", "Unknown"),
            sw_version=f"Updated: {device_updated}",
        )

    def _format_timestamp(
        self, timestamp: Optional[str], format_str: str = "%Y-%m-%d %H:%M"
    ) -> str:
        """Format ISO timestamp to human readable format."""
        if not timestamp:
            return "Unknown"

        try:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            return dt.strftime(format_str)
        except (ValueError, AttributeError):
            return timestamp

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return (
            self.coordinator.last_update_success
            and self.station_id in self.coordinator.data
        )

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if not self.available:
            return None

        station = self.coordinator.data[self.station_id]

        # Find the latest price for this fuel type
        for price in station.get("price", []):
            if price.get("tag") == self.fuel_type:
                return price.get("price")

        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return the state attributes."""
        if not self.available:
            return {}

        station = self.coordinator.data[self.station_id]
        attrs = {
            ATTR_STATION_NAME: station.get("name"),
            ATTR_STATION_BRAND: station.get("brand"),
            ATTR_STATION_CHAIN: station.get("chain"),
            ATTR_AVAILABLE_FUELS: ", ".join(station.get("fuels", [])),
        }

        # Location information
        if address := station.get("address"):
            attrs.update(
                {
                    ATTR_STATION_STREET: address.get("street"),
                    ATTR_STATION_CITY: address.get("city"),
                    ATTR_STATION_ZIPCODE: address.get("zipcode"),
                    ATTR_STATION_ADDRESS: f"{address.get('street')}, {address.get('city')} {address.get('zipcode')}",
                }
            )

        # Coordinates
        if location := station.get("location"):
            if coords := location.get("coordinates"):
                if len(coords) >= 2:
                    attrs[ATTR_STATION_LONGITUDE] = coords[0]
                    attrs[ATTR_STATION_LATITUDE] = coords[1]

        # Last update time
        if updated := station.get("updated"):
            attrs[ATTR_STATION_UPDATED] = updated
            attrs["last_update_formatted"] = self._format_timestamp(
                updated, "%Y-%m-%d %H:%M:%S"
            )

        # Price specific information
        for price in station.get("price", []):
            if price.get("tag") == self.fuel_type:
                if price_updated := price.get("updated"):
                    attrs[ATTR_STATION_PRICE_UPDATED] = price_updated
                    attrs["price_update_formatted"] = self._format_timestamp(
                        price_updated, "%Y-%m-%d %H:%M:%S"
                    )

                attrs.update(
                    {
                        ATTR_STATION_PRICE_REPORTER: price.get("reporter"),
                        ATTR_STATION_PRICE_DELTA: price.get("delta"),
                    }
                )
                break

        return attrs


class TankilleStationUpdateSensor(CoordinatorEntity, SensorEntity):
    """Represents a station update timestamp sensor - automatically enabled for all stations."""

    def __init__(
        self,
        coordinator: TankilleDataUpdateCoordinator,
        station_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.station_id = station_id

        self._attr_unique_id = f"{DOMAIN}_{station_id}_last_updated"
        self._attr_device_class = SensorDeviceClass.TIMESTAMP

        # ALWAYS enable the Last Updated sensor by default for all stations
        self._attr_entity_registry_enabled_default = True

        # Initialize station data
        self._station = (
            self.coordinator.data.get(station_id, {}) if self.coordinator.data else {}
        )

        station_name = self._station.get("name", "Unknown Station")
        self._attr_name = f"{station_name} Last Updated"

        # Add helpful icon for the timestamp sensor
        self._attr_icon = "mdi:clock-outline"

        # Set device info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.station_id)},
            name=station_name,
        )

        _LOGGER.debug(
            "Created Last Updated sensor for station '%s' (ID: %s) - Auto-enabled: %s",
            station_name,
            station_id,
            self._attr_entity_registry_enabled_default,
        )

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return (
            self.coordinator.last_update_success
            and self.station_id in self.coordinator.data
        )

    @property
    def native_value(self) -> Optional[datetime]:
        """Return the timestamp when the station was last updated."""
        if not self.available:
            return None

        station = self.coordinator.data[self.station_id]
        if updated := station.get("updated"):
            try:
                return datetime.fromisoformat(updated.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                _LOGGER.warning(
                    "Invalid timestamp format for station %s: %s",
                    self.station_id,
                    updated,
                )
                return None
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes for the Last Updated sensor."""
        if not self.available:
            return {}

        station = self.coordinator.data[self.station_id]
        attrs = {}

        # Add formatted timestamp for easier reading
        if updated := station.get("updated"):
            try:
                dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                attrs.update(
                    {
                        "formatted_time": dt.strftime("%Y-%m-%d %H:%M:%S"),
                        "time_ago": self._time_ago(dt),
                        "raw_timestamp": updated,
                    }
                )
            except (ValueError, AttributeError):
                attrs["raw_timestamp"] = updated

        # Add station info
        attrs.update(
            {
                ATTR_STATION_NAME: station.get("name"),
                ATTR_STATION_BRAND: station.get("brand"),
                ATTR_STATION_CHAIN: station.get("chain"),
                "total_fuel_types": len(station.get("fuels", [])),
                "available_fuel_types": ", ".join(station.get("fuels", [])),
            }
        )

        return attrs

    def _time_ago(self, dt: datetime) -> str:
        """Calculate human-readable time ago string."""
        now = datetime.now(dt.tzinfo)
        diff = now - dt

        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        else:
            return "Just now"
