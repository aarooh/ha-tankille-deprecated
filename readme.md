# Tankille for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/aarooh/hacs-tankille.svg)](https://github.com/aarooh/hacs-tankille/releases)
[![GitHub License](https://img.shields.io/github/license/aarooh/hacs-tankille.svg)](https://github.com/aarooh/hacs-tankille/blob/main/LICENSE)

A Home Assistant integration that provides fuel price data from Tankille API for gas stations in Finland.

## Features

- Creates sensors for each fuel type at each station
- Provides detailed station information (name, address, coordinates, etc.)
- Tracks price changes over time
- Allows filtering stations by location
- Fully asynchronous operations using `aiohttp`
- Stores authentication tokens for reliable operation

## Supported Fuel Types

- 95E10 (95)
- 98E5 (98)
- 98 Premium (98+)
- Diesel (dsl)
- Diesel Premium (dsl+)
- Natural Gas (ngas)
- Biogas (bgas)
- E85 ethanol blend (85)
- HVO Diesel (hvo)

## Installation

### HACS (Recommended)

1. Make sure [HACS](https://hacs.xyz/) is installed in your Home Assistant instance
2. Add this repository as a custom repository in HACS:
   - Go to HACS → Integrations → ⋮ (top right) → Custom repositories
   - Add the URL `https://github.com/aarooh/hacs-tankille` with category "Integration"
3. Click "Tankille" in the list of integrations
4. Click "Download"
5. Restart Home Assistant
6. Go to "Configuration" → "Devices & Services" → "Add Integration" and search for "Tankille"

### Manual Installation

1. Download the latest release from the [releases page](https://github.com/aarooh/hacs-tankille/releases)
2. Unzip the release and copy the `custom_components/tankille` directory to your Home Assistant installation's `custom_components` directory
3. Restart Home Assistant
4. Go to "Configuration" → "Devices & Services" → "Add Integration" and search for "Tankille"

## Configuration

Configuration is done via the Home Assistant UI:

1. Go to "Configuration" → "Devices & Services" → "Add Integration" and search for "Tankille".
2. Enter your Tankille account email and password.
3. Optionally, configure location filtering (latitude, longitude, distance) and specific station IDs.
4. Adjust the scanning interval if desired (default is 30 minutes).

## Authentication

This integration requires a valid Tankille account:

1. If you don't have a Tankille account, create one at [tankille.fi](https://tankille.fi)
2. Use the same email and password you use for the Tankille mobile app
3. The integration securely stores your authentication tokens and refreshes them automatically

### Authentication Troubleshooting

- **"Invalid authentication"**: Double-check your email and password
- **"Failed to connect"**: Check your internet connection and verify the Tankille service is operational
- **No data showing up**: Verify your account has access to station data in the Tankille app
- **Authentication token errors**: The integration will automatically try to refresh tokens, but you may need to remove and re-add the integration if problems persist

## Usage Examples

### Track the Cheapest Fuel Prices in Your Area

Create a card that displays the cheapest 95E10 fuel near your location.

```yaml
type: entities
title: Cheapest 95E10 Fuel
entities:
  - entity: sensor.abc_station_95e10
  - entity: sensor.neste_station_95e10
  - entity: sensor.shell_station_95e10
  - entity: sensor.st1_station_95e10
state_color: true
```

### Create Price Alerts

Set up an automation to notify you when fuel prices drop below a certain level:

```yaml
automation:
  - alias: "Notify when 95E10 price drops"
    trigger:
      - platform: numeric_state
        entity_id: sensor.neste_station_95e10
        below: 1.85
    action:
      - service: notify.mobile_app
        data:
          title: "Fuel Price Alert"
          message: "95E10 at Neste is now €{{ states('sensor.neste_station_95e10') }}"
```

## Lovelace Card Examples

### Example Station Card

```yaml
type: vertical-stack
cards:
  - type: gauge
    entity: sensor.neste_station_95e10
    name: Neste 95E10
    min: 1.5
    max: 2.5
    severity:
      green: 0
      yellow: 1.9
      red: 2.1
  - type: map
    entities:
      - entity: sensor.neste_station_95e10
    hours_to_show: 24
    title: Station Location
```

## Troubleshooting

### General Issues

- **Integration not appearing**: Verify the integration is correctly installed and Home Assistant has been restarted
- **No data in sensors**: Check if data is available in the Tankille app for the same stations
- **Incorrect prices**: The data is only as current as reported to the Tankille service
- **High resource usage**: Try increasing the scan interval to reduce API calls

### Authentication Issues

- **Failed authentication**: Verify your credentials and internet connection
- **"No stations found"**: Check your account permissions in the Tankille app
- **"API error"**: The Tankille API may be experiencing issues - try again later
- **Intermittent connection issues**: The integration includes an automatic retry mechanism, but persistent network problems may require troubleshooting your network

### API Connection Issues

- **Timeout errors**: The integration will retry failed connections with exponential backoff, but persistent timeout issues indicate network problems
- **"Unable to connect to Tankille API"**: Verify your network allows connections to api.tankille.fi
- **Repeated authentication failures**: Try removing and re-adding the integration

### Entity Specific Issues

- **Missing fuel types**: The integration only creates sensors for fuel types available at each station
- **Incorrect station names**: Station information comes directly from the Tankille API
- **Location filtering not working**: Verify your coordinates are correct and the distance value is appropriate

### Debugging

For more detailed troubleshooting, you can enable debug logging for the integration:

1. Add the following to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.tankille: debug
```

2. Restart Home Assistant
3. Check the logs for detailed information about API calls, data updates, and errors

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- This integration uses the Tankille API which provides fuel price data for stations in Finland
- Thanks to all contributors who have helped improve this integration

## Future TODO

Here are some potential ideas for future enhancements:

- **Price Trend Analysis:** Add attributes or separate sensors showing price trends (e.g., 7-day change, lowest price in the last X days).
- **Price Drop Notifications:** Allow users to configure notifications if a fuel price at a specific station drops below a certain threshold.
- **Map Integration:** Explore displaying stations on a map card within Home Assistant.
- **Fuel Type Filtering:** Allow users to select only the fuel types they are interested in during configuration to reduce the number of sensors created.
- **Favorite Stations Comparison:** Add functionality to easily compare prices across a user-defined list of favorite stations.
- **Historical Data:** Leverage the Home Assistant recorder component to store and potentially visualize historical price data (e.g., using ApexCharts card).
- **Configurable Station Update Intervals:** Allow different update frequencies for specific high-interest stations versus general background updates.
- **UI Configuration for Station Selection:** Instead of relying solely on location radius, allow users to pick specific stations from a list during setup or via options flow.