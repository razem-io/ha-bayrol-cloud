"""Test script for device status page."""
import asyncio
import aiohttp
import os
from custom_components.bayrol_cloud.client.bayrol_api import BayrolPoolAPI

async def main():
    """Main function."""
    username = os.environ.get("BAYROL_USERNAME")
    password = os.environ.get("BAYROL_PASSWORD")
    if not username or not password:
        print("Please set BAYROL_USERNAME and BAYROL_PASSWORD environment variables")
        return

    async with aiohttp.ClientSession() as session:
        api = BayrolPoolAPI(session)
        # Login
        print("Logging in...")
        if not await api.login(username, password):
            print("Login failed")
            return

        # Get list of controllers
        print("\nGetting controllers...")
        controllers = await api.get_controllers()
        if not controllers:
            print("No controllers found")
            return

        # Use the first controller's ID
        cid = controllers[0]["cid"]
        print(f"Found controller with ID: {cid}")

        # Get and show parsed data
        print("\nParsed Device Status:")
        print("=" * 80)
        data = await api.get_device_status(cid)
        for sensor_id, sensor_data in data.items():
            print(f"\nSensor: {sensor_data['name']} ({sensor_id})")
            print(f"Current Status: {sensor_data['current_text']} (value: {sensor_data['current_value']})")
            print("Available Options:")
            for option in sensor_data['options']:
                print(f"  - {option['text']} (value: {option['value']})")
        print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
