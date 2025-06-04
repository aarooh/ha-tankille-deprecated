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
from homeassistant.helpers.entity_platform import AddEntitiesCallback, async_get_current_platform
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator
from homeassistant.helpers import entity_registry as er

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
    CONF_IGNORED_CHAINS,
    CONF_FUELS,
    DEFAULT_FUEL_TYPES,
)
from .tankille_client import TankilleClient

_LOGGER = logging.getLogger(__name__)

# Global reference to the add_entities callback for dynamic entity management
_add_entities_callback = None


def is_station_ignored(
    station_name: str, station_brand: str, station_chain: str, ignored_chains: list[str]
) -> bool:
    """
    Check if station should be ignored based on name, brand, or chain.

    Uses partial matching (substring search) to catch variations like:
    - "Neste" matches "Neste Express", "Neste Automat"
    - "ABC" matches "ABC S-market", "ABC Automat"
    - "Shell" matches "Shell Express", "Shell Select"

    Args:
        station_name: Station name (e.g., "Neste Vantaa Myyrmäki")
        station_brand: Station brand (e.g., "Neste")
        station_chain: Station chain (e.g., "Neste Oy")
        ignored_chains: List of lowercase chain names to ignore

    Returns:
        True if station should be ignored, False otherwise
    """
    if not ignored_chains:
        return False

    station_name_lower = station_name.lower()
    station_brand_lower = station_brand.lower()
    station_chain_lower = station_chain.lower()

    for ignored in ignored_chains:
        if (
            ignored in station_name_lower
            or ignored in station_brand_lower
            or ignored in station_chain_lower
        ):
            return True

    return False


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tankille sensor entries."""
    global _add_entities_callback
    _add_entities_callback = async_add_entities
    
    client: TankilleClient = hass.data[DOMAIN][config_entry.entry_id]["client"]
    coordinator: TankilleDataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ]["coordinator"]

    # Helper function to get config values (options take precedence over data)
    def get_config_value(key: str, default=None):
        """Get configuration value from options (preferred) or data (fallback)."""
        return config_entry.options.get(key, config_entry.data.get(key, default))

    _LOGGER.info("Starting Tankille sensor setup")

    # Get current configuration
    ignored_chains_str = get_config_value(CONF_IGNORED_CHAINS, "")
    ignored_chains = [
        chain.strip().lower()
        for chain in ignored_chains_str.split(",")
        if chain.strip()
    ]

    selected_fuels_config = get_config_value(CONF_FUELS, ",".join(DEFAULT_FUEL_TYPES))
    if isinstance(selected_fuels_config, str):
        selected_fuels = [f.strip() for f in selected_fuels_config.split(",") if f.strip()]
    elif isinstance(selected_fuels_config, list):
        selected_fuels = selected_fuels_config
    else:
        selected_fuels = DEFAULT_FUEL_TYPES

    _LOGGER.info(
        "Configuration: ignored_chains=%s, selected_fuels=%s",
        ignored_chains,
        selected_fuels,
    )

    # Ensure we have station data
    all_stations_data = coordinator.data
    if not all_stations_data:
        _LOGGER.warning("No station data available, requesting refresh...")
        await coordinator.async_request_refresh()
        all_stations_data = coordinator.data
        if not all_stations_data:
            _LOGGER.error("Still no station data after refresh, aborting setup")
            return

    # Create entities based on current configuration
    entities_to_add: list[SensorEntity] = []
    stations_processed = 0
    stations_ignored = 0
    fuel_sensors_created = 0

    for station_id, station_data in all_stations_data.items():
        station_name = station_data.get("name", "Unknown Station")
        station_brand = station_data.get("brand", "")
        station_chain = station_data.get("chain", "")

        # Check if station should be ignored
        if is_station_ignored(station_name, station_brand, station_chain, ignored_chains):
            _LOGGER.debug(
                "Ignoring station '%s' (brand: %s, chain: %s)",
                station_name,
                station_brand,
                station_chain,
            )
            stations_ignored += 1
            continue

        stations_processed += 1

        # Add station update sensor
        entities_to_add.append(TankilleStationUpdateSensor(coordinator, station_id))

        # Add fuel price sensors for selected fuel types
        station_fuel_count = 0
        available_fuels = station_data.get("fuels", [])
        
        for fuel_type_code in available_fuels:
            if fuel_type_code in FUEL_TYPES and fuel_type_code in selected_fuels:
                entities_to_add.append(
                    TankilleFuelPriceSensor(coordinator, station_id, fuel_type_code)
                )
                station_fuel_count += 1
                fuel_sensors_created += 1

        _LOGGER.debug(
            "Station '%s': %d fuel sensors (available: %s, selected: %s)",
            station_name,
            station_fuel_count,
            available_fuels,
            selected_fuels,
        )

    # Add all the entities
    total_entities = len(entities_to_add)
    
    _LOGGER.info(
        "Setup complete: %d stations processed, %d ignored, creating %d entities",
        stations_processed,
        stations_ignored,
        total_entities,
    )

    if entities_to_add:
        async_add_entities(entities_to_add, True)
        _LOGGER.info("Successfully added %d entities", total_entities)
    else:
        _LOGGER.info("No entities to add")


async def handle_config_update(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    coordinator: TankilleDataUpdateCoordinator,
) -> None:
    """Handle configuration updates by managing entities dynamically."""
    global _add_entities_callback
    
    # Helper function to get config values (options take precedence over data)
    def get_config_value(key: str, default=None):
        """Get configuration value from options (preferred) or data (fallback)."""
        return config_entry.options.get(key, config_entry.data.get(key, default))

    _LOGGER.info("Handling configuration update")

    # Step 1: Clean up obsolete entities
    entity_registry = er.async_get(hass)
    existing_entities = er.async_entries_for_config_entry(
        entity_registry, config_entry.entry_id
    )
    
    # Get current configuration
    ignored_chains_str = get_config_value(CONF_IGNORED_CHAINS, "")
    ignored_chains = [
        chain.strip().lower()
        for chain in ignored_chains_str.split(",")
        if chain.strip()
    ]

    selected_fuels_config = get_config_value(CONF_FUELS, ",".join(DEFAULT_FUEL_TYPES))
    if isinstance(selected_fuels_config, str):
        selected_fuels = [f.strip() for f in selected_fuels_config.split(",") if f.strip()]
    elif isinstance(selected_fuels_config, list):
        selected_fuels = selected_fuels_config
    else:
        selected_fuels = DEFAULT_FUEL_TYPES

    entities_to_remove = []
    existing_unique_ids = set()
    
    for entity_entry in existing_entities:
        unique_id = entity_entry.unique_id
        existing_unique_ids.add(unique_id)
        should_remove = False
        
        # Parse the unique_id to get station_id and fuel_type
        if unique_id.startswith(f"{DOMAIN}_"):
            parts = unique_id[len(f"{DOMAIN}_"):].split("_")
            if len(parts) >= 2:
                station_id = parts[0]
                
                # Get station data
                station_data = coordinator.data.get(station_id) if coordinator.data else None
                if not station_data:
                    # Station no longer exists
                    should_remove = True
                else:
                    station_name = station_data.get("name", "")
                    station_brand = station_data.get("brand", "")
                    station_chain = station_data.get("chain", "")
                    
                    # Check if station is now ignored
                    if is_station_ignored(station_name, station_brand, station_chain, ignored_chains):
                        should_remove = True
                    # Check if this is a fuel sensor (not the last_updated sensor)
                    elif unique_id.endswith("_last_updated"):
                        # This is a last_updated sensor - keep it as long as station isn't ignored
                        pass
                    elif len(parts) >= 3:
                        # This is a fuel sensor - check if fuel type is still selected
                        fuel_type = parts[-1]
                        if fuel_type not in selected_fuels:
                            should_remove = True
        
        if should_remove:
            entities_to_remove.append(entity_entry)
    
    # Remove obsolete entities
    if entities_to_remove:
        _LOGGER.info("Removing %d obsolete entities due to configuration changes", len(entities_to_remove))
        for entity_entry in entities_to_remove:
            _LOGGER.debug(
                "Removing obsolete entity: %s (%s)",
                entity_entry.entity_id,
                entity_entry.unique_id,
            )
            entity_registry.async_remove_entity(entity_entry.entity_id)
            existing_unique_ids.discard(entity_entry.unique_id)

    # Step 2: Create new entities that don't exist yet
    if not coordinator.data:
        _LOGGER.warning("No station data available for creating new entities")
        return

    new_entities_to_add = []
    
    for station_id, station_data in coordinator.data.items():
        station_name = station_data.get("name", "Unknown Station")
        station_brand = station_data.get("brand", "")
        station_chain = station_data.get("chain", "")

        # Check if station should be ignored
        if is_station_ignored(station_name, station_brand, station_chain, ignored_chains):
            continue

        # Add station update sensor if it doesn't exist
        update_sensor_id = f"{DOMAIN}_{station_id}_last_updated"
        if update_sensor_id not in existing_unique_ids:
            new_entities_to_add.append(TankilleStationUpdateSensor(coordinator, station_id))

        # Add fuel price sensors for selected fuel types
        available_fuels = station_data.get("fuels", [])
        
        for fuel_type_code in available_fuels:
            if fuel_type_code in FUEL_TYPES and fuel_type_code in selected_fuels:
                fuel_sensor_id = f"{DOMAIN}_{station_id}_{fuel_type_code}"
                if fuel_sensor_id not in existing_unique_ids:
                    new_entities_to_add.append(
                        TankilleFuelPriceSensor(coordinator, station_id, fuel_type_code)
                    )

    # Add new entities
    if new_entities_to_add and _add_entities_callback:
        _LOGGER.info("Adding %d new entities due to configuration changes", len(new_entities_to_add))
        _add_entities_callback(new_entities_to_add, True)
    elif new_entities_to_add:
        _LOGGER.warning("Cannot add new entities - no callback available")
    else:
        _LOGGER.info("No new entities needed")


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

        # Disable less common fuel types by default, but keep enabled if explicitly selected
        disabled_by_default = [
            FUEL_TYPE_NGAS,  # Natural Gas
            FUEL_TYPE_BGAS,  # Biogas
            FUEL_TYPE_98_PLUS,  # 98 Premium
            FUEL_TYPE_DIESEL_PLUS,  # Diesel Premium
            FUEL_TYPE_HVO,  # HVO Diesel
        ]

        # If fuel type was explicitly selected in config, enable it regardless
        # Ensure we read from options if available, falling back to data
        config_fuels_str = coordinator.config_entry.options.get(
            CONF_FUELS, coordinator.config_entry.data.get(CONF_FUELS, "")
        )
        if isinstance(config_fuels_str, str):
            config_fuels = [f.strip() for f in config_fuels_str.split(",") if f.strip()]
        else:
            config_fuels = config_fuels_str or []

        self._attr_entity_registry_enabled_default = (
            fuel_type not in disabled_by_default or fuel_type in config_fuels
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
