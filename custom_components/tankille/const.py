"""Constants for the Tankille integration."""

DOMAIN = "tankille"

# Configuration
CONF_LOCATION = "location"
CONF_LOCATION_LAT = "lat"
CONF_LOCATION_LON = "lon"
CONF_DISTANCE = "distance"
CONF_STATION_ID = "station_id"
CONF_STATION_IDS = "station_ids"
CONF_USE_LOCATION_FILTER = "use_location_filter"
CONF_IGNORED_CHAINS = "ignored_chains"
CONF_FUELS = "fuels"
CONF_STATION_NAMES = "station_names"

# Defaults
DEFAULT_SCAN_INTERVAL = 3600  # 60 minutes
DEFAULT_DISTANCE = 5000  # 5km

# Station attributes
ATTR_STATION_NAME = "station_name"
ATTR_STATION_BRAND = "brand"
ATTR_STATION_CHAIN = "chain"
ATTR_STATION_ADDRESS = "address"
ATTR_STATION_CITY = "city"
ATTR_STATION_STREET = "street"
ATTR_STATION_ZIPCODE = "zipcode"
ATTR_STATION_UPDATED = "updated"
ATTR_STATION_LATITUDE = "latitude"
ATTR_STATION_LONGITUDE = "longitude"
ATTR_STATION_PRICE_UPDATED = "price_updated"
ATTR_STATION_PRICE_REPORTER = "price_reporter"
ATTR_STATION_PRICE_DELTA = "price_delta"
ATTR_AVAILABLE_FUELS = "available_fuels"

# Fuel types
FUEL_TYPE_95 = "95"
FUEL_TYPE_98 = "98"
FUEL_TYPE_98_PLUS = "98+"
FUEL_TYPE_DIESEL = "dsl"
FUEL_TYPE_DIESEL_PLUS = "dsl+"
FUEL_TYPE_NGAS = "ngas"
FUEL_TYPE_BGAS = "bgas"
FUEL_TYPE_E85 = "85"
FUEL_TYPE_HVO = "hvo"

FUEL_TYPES = [
    FUEL_TYPE_95,
    FUEL_TYPE_98,
    FUEL_TYPE_98_PLUS,
    FUEL_TYPE_DIESEL,
    FUEL_TYPE_DIESEL_PLUS,
    FUEL_TYPE_NGAS,
    FUEL_TYPE_BGAS,
    FUEL_TYPE_E85,
    FUEL_TYPE_HVO,
]

# Friendly fuel type names
FUEL_TYPE_NAMES = {
    FUEL_TYPE_95: "95E10",
    FUEL_TYPE_98: "98E5",
    FUEL_TYPE_98_PLUS: "98 Premium",
    FUEL_TYPE_DIESEL: "Diesel",
    FUEL_TYPE_DIESEL_PLUS: "Diesel Premium",
    FUEL_TYPE_NGAS: "Natural Gas",
    FUEL_TYPE_BGAS: "Biogas",
    FUEL_TYPE_E85: "E85",
    FUEL_TYPE_HVO: "HVO Diesel",
}

# Default fuel types
DEFAULT_FUEL_TYPES = [FUEL_TYPE_95, FUEL_TYPE_98, FUEL_TYPE_DIESEL]

# Common gas station chains for filtering
COMMON_CHAINS = ["Neste", "St1", "ABC", "Teboil", "Shell", "Esso", "SEO"]
