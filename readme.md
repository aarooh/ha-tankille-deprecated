# Tankille for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/aarooh/hacs-tankille.svg)](https://github.com/aarooh/hacs-tankille/releases)
[![GitHub License](https://img.shields.io/github/license/aarooh/hacs-tankille.svg)](https://github.com/aarooh/hacs-tankille/blob/main/LICENSE)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2023.1+-blue.svg)](https://www.home-assistant.io/)
[![GitHub Issues](https://img.shields.io/github/issues/aarooh/hacs-tankille.svg)](https://github.com/aarooh/hacs-tankille/issues)
[![Validate](https://github.com/aarooh/hacs-tankille/actions/workflows/validate.yml/badge.svg)](https://github.com/aarooh/hacs-tankille/actions/workflows/validate.yml)

![logo](https://github.com/user-attachments/assets/11296282-7ed7-4c5c-af5a-cc0a3dfdd898)

Home Assistant integration that provides **real-time fuel price data** from Tankille API for gas stations across Finland. Monitor fuel prices, set up price alerts, and find the cheapest fuel near you!

## 🌟 Features

- **🚗 Real-time fuel prices** for stations across Finland
- **📊 Multiple fuel types** (95E10, 98E5, Diesel, Natural Gas, etc.)
- **⛽ Selective fuel type monitoring** - Choose which fuel types to track
- **🚫 Gas station chain filtering** - Ignore specific chains (Neste, ABC, St1, etc.)
- **📍 Location-based filtering** to find stations near you
- **📱 Smart automation support** for price alerts and notifications
- **🔍 Detailed station information** including address, coordinates, and last update times
- **📈 Last updated sensors** automatically enabled for all stations
- **⚙️ Configurable after setup** - Change all settings without recreating the integration

## 🏠 Compatibility

- **Home Assistant**: 2023.1 or newer
- **HACS**: Any version
- **Python**: 3.10+ (handled by Home Assistant)

## 📦 Installation

### Option 1: HACS (Recommended)

1. **Add Custom Repository**:
   - Open HACS in your Home Assistant instance
   - Go to **Integrations** → **⋮** (menu) → **Custom repositories**
   - Add URL: `https://github.com/aarooh/hacs-tankille`
   - Category: **Integration**
   - Click **Add**

2. **Install Integration**:
   - Search for "**Tankille**" in HACS
   - Click **Download**
   - **Restart Home Assistant**

3. **Add Integration**:
   - Go to **Settings** → **Devices & Services** → **Add Integration**
   - Search for "**Tankille**" and select it

### Option 2: Manual Installation

1. Download the latest release from the [releases page](https://github.com/aarooh/hacs-tankille/releases)
2. Extract and copy the `custom_components/tankille` directory to your Home Assistant installation's `custom_components` directory
3. Restart Home Assistant
4. Add the integration via Settings → Devices & Services → Add Integration

## ⚙️ Configuration

### Initial Setup

1. **Navigate to Integration Setup**:
   - Settings → Devices & Services → Add Integration
   - Search for "Tankille"

![01-add-integration](https://github.com/user-attachments/assets/266cf3fe-bed0-49c8-9c6c-60397f21e656)

2. **Enter Credentials and Configure Filtering**:
   - **Email**: Your Tankille account email
   - **Password**: Your Tankille account password
   - **Update Interval**: How often to check for price updates (default: 60 minutes)
   - **Location Filtering**: Configure latitude, longitude, and search radius
   - **🆕 Ignored Gas Station Chains**: Comma-separated list (e.g., "Neste, ABC, St1")
   - **🆕 Fuel Types**: Select which fuel types to monitor

![02-login-and-location-setup](https://github.com/user-attachments/assets/62ade903-91e6-4ef9-9a78-d2b0974e8b0b)


> **💡 Pro Tips**: 
> - Always use location filtering to avoid creating hundreds of sensors!
> - Use 2-5 km radius in cities, 10-15 km in rural areas
> - Select only fuel types you actually use to reduce sensor count

### 🆕 Reconfigure After Setup

You can modify **all settings** after initial setup:

1. Go to **Settings** → **Devices & Services**
2. Find your Tankille integration
3. Click **Configure**
4. Modify any settings (location, ignored chains, fuel types, etc.)
5. Integration automatically reloads with new settings

### Supported Fuel Types

| Fuel Code | Display Name | Default Enabled |
|-----------|-------------|----------------|
| `95` | 95E10 | ✅ |
| `98` | 98E5 | ✅ |
| `98+` | 98 Premium | ❌ |
| `dsl` | Diesel | ✅ |
| `dsl+` | Diesel Premium | ❌ |
| `ngas` | Natural Gas | ❌ |
| `bgas` | Biogas | ❌ |
| `85` | E85 | ❌ |
| `hvo` | HVO Diesel | ❌ |

*Note: Less common fuel types are disabled by default but can be enabled during setup or in options.*

### 🆕 Gas Station Chain Filtering

Filter out unwanted gas stations by entering chain names:

**Examples:**
- `"Neste"` - Filters all Neste stations (Neste, Neste Express, Neste Automat)
- `"ABC, K-Market"` - Filters ABC and K-Market stations  
- `"Shell, St1, Teboil"` - Filters multiple chains
- `"Express"` - Filters all Express stations regardless of parent company

**How it works:**
- Checks station **name**, **brand**, and **chain** fields
- Uses partial matching (substring search)
- Case insensitive matching
- Comma-separated list for multiple chains

## 🚀 Dashboard Examples

### Comprehensive Fuel Price Dashboard

Create a complete fuel monitoring setup with these four complementary cards:

![dashboard-hero](https://github.com/user-attachments/assets/66074884-81b1-4061-969c-40f8fc5709aa)


#### 1. Main Fuel Prices Overview
```yaml
type: vertical-stack
cards:
  - type: custom:mushroom-title-card
    title: ⛽ Local Fuel Prices
    subtitle: Real-time prices from Tankille
  - type: entities
    title: 95E10 Gasoline Prices
    show_header_toggle: false
    entities:
      - entity: sensor.neste_vantaa_myyrmaki_95e10
        name: 🟢 Neste Vantaa Myyrmäki
        secondary_info: last-updated
      - entity: sensor.st1_helsinki_konala_95e10
        name: 🔵 ST1 Helsinki Konala
        secondary_info: last-updated
      - entity: sensor.abc_s_market_konala_helsinki_95e10
        name: 🔴 ABC S-market Konala
        secondary_info: last-updated
      - entity: sensor.teboil_helsinki_konala_95e10
        name: 🟡 Teboil Helsinki Konala
        secondary_info: last-updated
    state_color: true
```

#### 2. Station Details Card
```yaml
type: entities
title: 🏪 Station Details - Neste Vantaa Myyrmäki
show_header_toggle: false
entities:
  - entity: sensor.neste_vantaa_myyrmaki_last_updated
    name: 🕐 Last Updated
    icon: mdi:clock-outline
  - type: divider
  - entity: sensor.neste_vantaa_myyrmaki_95e10
    name: ⛽ 95E10
    icon: mdi:gas-station
  - entity: sensor.neste_vantaa_myyrmaki_98e5
    name: ⛽ 98E5
    icon: mdi:gas-station-outline
  - entity: sensor.neste_vantaa_myyrmaki_diesel
    name: ⛽ Diesel
    icon: mdi:truck
  - type: divider
  - type: attribute
    entity: sensor.neste_vantaa_myyrmaki_95e10
    attribute: address
    name: 📍 Address
  - type: attribute
    entity: sensor.neste_vantaa_myyrmaki_95e10
    attribute: available_fuels
    name: ⛽ Available Fuels
```

#### 3. Visual Price Comparison Gauges
```yaml
type: grid
columns: 2
square: false
cards:
  - type: gauge
    entity: sensor.neste_vantaa_myyrmaki_95e10
    name: Neste Myyrmäki 95E10
    min: 1.6
    max: 2.2
    needle: true
    severity:
      green: 0
      yellow: 1.85
      red: 2
  - type: gauge
    entity: sensor.st1_helsinki_konala_95e10
    name: ST1 Konala 95E10
    min: 1.6
    max: 2.2
    needle: true
    severity:
      green: 0
      yellow: 1.85
      red: 2
```

#### 4. Interactive Station Map
```yaml
type: map
entities:
  - entity: sensor.neste_vantaa_myyrmaki_95e10
  - entity: sensor.st1_helsinki_konala_95e10
  - entity: sensor.abc_s_market_konala_helsinki_95e10
  - entity: sensor.teboil_helsinki_konala_95e10
  - entity: sensor.gasum_vantaa_kivisto_95e10
  - entity: sensor.neste_espoo_karakallio_95e10
  - entity: sensor.st1_espoo_leppavaara_diesel
hours_to_show: 24
title: 🗺️ Nearby Fuel Stations
aspect_ratio: "16:9"
theme_mode: auto
```

### Simple Price Alert Automation

```yaml
automation:
  - alias: "⛽ Fuel Price Alert"
    description: "Notify when 95E10 drops below €1.80"
    trigger:
      - platform: numeric_state
        entity_id: sensor.neste_vantaa_myyrmaki_95e10
        below: 1.80
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "⛽ Cheap Fuel Alert!"
          message: "95E10 at Neste Vantaa Myyrmäki is now €{{ states('sensor.neste_vantaa_myyrmaki_95e10') }}/L"
```

## 🔧 Authentication

### Account Setup

1. **Create Account**: If you don't have one, register at [tankille.fi](https://tankille.fi)
2. **Mobile App**: Ensure you can log in with the same credentials in the Tankille mobile app
3. **Integration**: Use the same email/password in the Home Assistant integration

### Authentication Features

- **Automatic token refresh**: No need to re-enter credentials
- **Secure storage**: Tokens are encrypted and stored locally
- **Error recovery**: Automatic re-authentication on token expiry
- **Debug logging**: Enable for troubleshooting authentication issues

## 🔍 Entity Details

![entities-overview](https://github.com/user-attachments/assets/1b0cd4ac-4a14-4846-a49e-ae896efb9f65)


*Overview of Tankille sensors in Home Assistant showing all fuel price entities*

### Fuel Price Sensors

Each fuel price sensor provides:

**State**: Current fuel price in Euros (€)

**Attributes**:
- `station_name`: Station name (e.g., "Neste Myyrmäki")
- `brand`: Station brand (e.g., "Neste")
- `chain`: Station chain (e.g., "Neste Oy")
- `address`: Full address string
- `latitude`/`longitude`: GPS coordinates
- `available_fuels`: List of all fuel types at station
- `price_updated`: When this fuel price was last updated
- `price_reporter`: Who reported the price
- `last_update_formatted`: Human-readable update time

![entity-details](https://github.com/user-attachments/assets/ee6b1662-013e-4445-a538-3bfd9618f3f2)


*Detailed view of a single fuel price sensor showing all available attributes*

### Station Last Updated Sensors

**Automatically enabled** for all stations:

**State**: Timestamp when station data was last updated

**Attributes**:
- `formatted_time`: Human-readable timestamp
- `time_ago`: Relative time (e.g., "2 hours ago")
- `total_fuel_types`: Number of fuel types available
- `available_fuel_types`: List of fuel types

## 🛠️ Troubleshooting

### Common Issues

#### ❌ Authentication Problems

**Issue**: Login fails with correct credentials
```yaml
# Solutions:
1. Verify credentials work in Tankille mobile app
2. Check Home Assistant logs for specific error
3. Try removing and re-adding the integration
4. Enable debug logging (see below)
```

**Issue**: "No stations found"
```yaml
# Solutions:
1. Verify your Tankille account has access to station data
2. Check location filtering settings
3. Try increasing search radius
4. Disable location filtering temporarily
```

#### 🌐 Connection Issues

**Issue**: "Cannot connect to Tankille API"
```yaml
# Solutions:
1. Check internet connectivity from HA
2. Verify api.tankille.fi is accessible
3. Check for firewall blocking HTTPS requests
4. Review HA network configuration
```

#### 📊 Data Issues

**Issue**: Missing or outdated prices
```yaml
# Solutions:
1. Check if data is available in Tankille mobile app
2. Adjust scan interval (minimum 30 minutes recommended)
3. Verify station is still operational
4. Check entity states in Developer Tools
```

#### 🆕 Filtering Issues

**Issue**: Stations not being filtered correctly
```yaml
# Solutions:
1. Check spelling of chain names in ignored list
2. Use partial names (e.g., "Neste" instead of "Neste Express")
3. Check logs for debug messages about filtered stations
4. Verify station names in entity attributes
```

**Issue**: Too many fuel type sensors
```yaml
# Solutions:
1. Reconfigure integration and select fewer fuel types
2. Disable unwanted sensors in entity registry
3. Use ignored chains to filter out unwanted stations
```

### Debug Logging

Add to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.tankille: debug
    custom_components.tankille.tankille_client: debug
```

### Advanced Debugging

1. **Check Entity Registry**: 
   - Developer Tools → States
   - Filter by `sensor.` and search for your station names

2. **Review Integration Logs**:
   - Settings → System → Logs
   - Search for "tankille"

3. **Test API Connectivity**:
   ```bash
   # From HA container/host
   curl -I https://api.tankille.fi
   ```

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

1. **🐛 Report Bugs**: Use the [issue tracker](https://github.com/aarooh/hacs-tankille/issues)
2. **💡 Suggest Features**: Open a feature request issue
3. **🔧 Submit PRs**: Fork, create feature branch, submit pull request
4. **📖 Improve Docs**: Help improve documentation and examples

### Development Setup

```bash
# Clone repository
git clone https://github.com/aarooh/hacs-tankille.git

# Create development environment
cd hacs-tankille
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# For Windows:
# In Command Prompt (cmd.exe): .venv\Scripts\activate.bat
# In PowerShell: .venv\Scripts\Activate.ps1
# In Git Bash / MinGW: source .venv/Scripts/activate

# Install dependencies
pip install -r requirements.txt
```

## 📋 Roadmap

### Planned Features

- **📈 Price trend analysis** (7-day, 30-day changes)
- **🗺️ Route-based recommendations** 
- **🎯 Advanced price alerts** with trend analysis
- **📊 Enhanced dashboard cards** with charts
- **🤖 Predictive analytics** for price forecasting

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Tankille Team**: For providing the fuel price API
- **Home Assistant Community**: For integration development guidance  
- **HACS**: For making custom integrations easily accessible
- **Contributors**: Everyone who has helped improve this integration

## 📞 Support

- **🐛 Issues**: [GitHub Issues](https://github.com/aarooh/hacs-tankille/issues)
- **💬 Discussions**: [GitHub Discussions](https://github.com/aarooh/hacs-tankille/discussions)
- **📖 Documentation**: [Integration Docs](https://github.com/aarooh/hacs-tankille)
- **🏠 Home Assistant**: [Community Forum](https://community.home-assistant.io/)

---

## 📝 Changelog

### Version 0.2.0 - Enhanced Filtering & Configuration

#### 🆕 **New Features**
- **Fuel Type Selection**: Choose specific fuel types during setup and in options
  - Multi-select UI with checkboxes for all available fuel types
  - Defaults to most common types (95E10, 98E5, Diesel, E85)
  - Only creates sensors for selected fuel types
- **Enhanced Gas Station Chain Filtering**: 
  - Now filters by station **name**, **brand**, and **chain** fields
  - Uses intelligent partial matching (e.g., "Neste" matches "Neste Express")
  - More intuitive filtering based on what users actually see
- **Complete Options Flow**: 
  - Modify ALL settings after initial setup without recreating integration
  - Change location, ignored chains, fuel types, scan interval, etc.
  - Integration automatically reloads when settings change

#### 🔧 **Improvements**
- **Better User Experience**: Clear descriptions and examples in configuration UI
- **Reduced Sensor Count**: Fuel type filtering prevents creation of unwanted sensors
- **Smarter Filtering Logic**: Modular `is_station_ignored()` function with comprehensive matching
- **Enhanced Logging**: Better debug information for troubleshooting filtering issues
- **Backward Compatibility**: Existing setups continue working with sensible defaults

#### 🐛 **Bug Fixes**
- Improved handling of empty or invalid filter configurations
- Better error handling in options flow validation

#### 📖 **Documentation**
- Updated README with detailed filtering examples
- Added troubleshooting section for filtering issues

### Version 0.1.0 - Initial Release

#### 🆕 **Initial Features**
- Real-time fuel price monitoring from Tankille API
- Location-based station filtering
- Multiple fuel type support
- Last updated sensors for all stations
- Comprehensive station information and attributes
- Authentication with token refresh
- HACS integration support

---

<p align="center">
  <strong>⭐ If this integration is helpful, please consider giving it a star on GitHub! ⭐</strong>
</p>
