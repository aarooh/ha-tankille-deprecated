# Tankille

![Tankille Logo](https://raw.githubusercontent.com/yourusername/tankille-homeassistant/main/images/tankille_logo.png)

## What is Tankille?

Tankille is a Home Assistant integration that provides fuel price data for gas stations in Finland. It connects to the Tankille API to retrieve real-time fuel prices and station details.

## Key Features

- 🚗 **Real-time fuel prices** for stations across Finland
- 📊 **Multi-fuel tracking** (95E10, 98E5, Diesel, etc.)
- 📍 **Location-based filtering** to find stations near you
- 📱 **Automation support** for price alerts
- 🔍 **Detailed station information** including address and coordinates
- Fully asynchronous operations using `aiohttp`

## Screenshot

![Dashboard Example](https://raw.githubusercontent.com/yourusername/tankille-homeassistant/main/images/dashboard_example.png)

## Quick Setup

1. Install this integration through HACS
2. Add the integration in Home Assistant
3. Enter your Tankille account email and password
4. Enjoy real-time fuel price data in your dashboards!

## Authentication

This integration requires a valid Tankille account:

1. If you don't have a Tankille account, create one at [tankille.fi](https://tankille.fi)
2. Use the same email and password you use for the Tankille mobile app
3. The integration securely stores your authentication tokens and refreshes them automatically

## Example Use Cases

- Monitor fuel prices at your favorite stations
- Get notifications when prices drop below a certain level
- Find the cheapest fuel in your area
- Track price trends over time

## Available Fuel Types

- 95E10 (95)
- 98E5 (98)
- 98 Premium (98+)
- Diesel (dsl)
- Diesel Premium (dsl+)
- Natural Gas (ngas)
- Biogas (bgas)
- E85 ethanol blend (85)
- HVO Diesel (hvo)

## Troubleshooting Common Issues

### Authentication Problems
- **Login fails**: Verify your email and password are correct
- **"No stations found"**: Check if your Tankille account has access to station data
- **Connection errors**: Ensure Home Assistant can connect to the internet

### Data Issues
- **Missing prices**: Only available fuel types at each station are shown
- **Outdated information**: Adjust the scan interval for more frequent updates
- **Incorrect location**: Check the coordinates in your configuration

### Need More Help?

If you have any questions or need assistance, please:
- Check the full [documentation](https://github.com/yourusername/tankille-homeassistant) for detailed troubleshooting
- Enable debug logging: Add `custom_components.tankille: debug` to your logger configuration
- Open an [issue](https://github.com/yourusername/tankille-homeassistant/issues) on GitHub