[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

# Bayrol Cloud Integration for Home Assistant

⚠️ **BETA STATUS**: This integration is currently in beta. Please report any issues you encounter.

This is a Home Assistant Custom Component for the Bayrol Cloud. It currently allows you to monitor your pool's pH, Redox (ORP), and temperature values directly in Home Assistant.

It currently only supports the German Bayrol Cloud services (https://www.bayrol-poolaccess.de), because I do not have access to others yet. If you can help with other Bayrol Cloud instances, open an issue. PRs are always welcome.

## Tested Devices

Currently tested with:
- BAYROL PoolRelax 3

Have a different Bayrol device? Please [open an issue](https://github.com/razem-io/ha-bayrol-cloud/issues) to help expand device support! When opening an issue, please include:
- Your device model
- HTML response of https://www.bayrol-poolaccess.de/webview/getdata.php?cid=<your-cid>
- Any specific features or parameters your device supports

## Features

- Monitors pool water parameters:
  - pH Level
  - Redox/ORP (mV)
  - Temperature
- Automatic data updates every 5 minutes
- Easy configuration through the Home Assistant UI
- Automatic discovery of all your pool controllers
- Support for multiple pool controllers

## Installation

### HACS (Recommended)

1. Make sure you have [HACS](https://hacs.xyz/) installed
2. Add this repository as a custom repository in HACS:
   - Click on HACS in the sidebar
   - Click on "Integrations"
   - Click the three dots in the top right corner
   - Select "Custom repositories"
   - Add `https://github.com/razem-io/ha-bayrol-cloud` as the repository URL
   - Select "Integration" as the category
3. Click "Install"
4. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/bayrol_cloud` directory to your Home Assistant's `custom_components` directory
2. Restart Home Assistant

## Configuration

1. Go to Settings -> Devices & Services
2. Click "Add Integration"
3. Search for "Bayrol Cloud"
4. Enter your credentials:
   - Username (Email address used for Bayrol Pool Access)
   - Password

The integration will automatically discover and add all pool controllers configured in your Bayrol Cloud account.

## Sensors

For each controller (where `CID` is your Controller ID), the integration provides:

- `sensor.bayrol_cloud_CID_ph`: Current pH level
- `sensor.bayrol_cloud_CID_redox`: Current Redox/ORP value in mV
- `sensor.bayrol_cloud_CID_temperature`: Current water temperature in °C

Each controller will appear as a separate device in Home Assistant with its own set of sensors.

## Development

### Prerequisites

- Python 3.9 or higher
- Home Assistant development environment
- SSH access to your Home Assistant instance
- `rsync` installed on your development machine

### Development Installation Script

A development installation script (`dev-install.sh`) is provided to easily update the integration on your Home Assistant instance during development.

The script can be run in several ways:

1. Using default settings (root@homeassistant.local):
   ```bash
   ./dev-install.sh
   ```

2. Specifying custom user and host:
   ```bash
   ./dev-install.sh -u admin -h 192.168.1.100
   ```

3. View help and available options:
   ```bash
   ./dev-install.sh --help
   ```
   
The script will:
- Sync the integration files to your Home Assistant instance
- Restart Home Assistant to apply changes
- Wait for Home Assistant to come back online

### Testing

A test script (`test_api.py`) is provided to verify the API connection before deploying to Home Assistant:

```bash
python test_api.py --username your@email.com --password yourpassword --cid yourcid
```

This will test:
- Authentication with Bayrol Cloud Access
- Data fetching for your pool controller
- Parsing of sensor values

## Troubleshooting

If you encounter any issues:

1. Check that your credentials are correct
2. Ensure your Bayrol Cloud Access account is active and working
3. Check the Home Assistant logs for any error messages
4. Try running the test script to verify API connectivity

## Support

For bugs, feature requests, or to add support for new devices, please [open an issue](https://github.com/razem-io/ha-bayrol-cloud/issues) on GitHub.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
