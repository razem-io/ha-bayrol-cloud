#!/usr/bin/env python3
import asyncio
import aiohttp
import sys
import logging
import os
from custom_components.bayrol_cloud.client.bayrol_api import BayrolPoolAPI

# Set up logging
logging.basicConfig(level=logging.DEBUG)
_LOGGER = logging.getLogger(__name__)

async def test_bayrol_api(username: str, password: str):
    """Test Bayrol Pool Access API authentication and data fetching."""
    async with aiohttp.ClientSession() as session:
        # Initialize API with debug mode
        api = BayrolPoolAPI(session)
        api.debug_mode = True

        # Test login
        print("\nTesting login...")
        if not await api.login(username, password):
            print("❌ Login failed")
            return False
        
        print("✅ Login successful")

        # Get list of controllers
        print("\nDiscovering controllers...")
        controllers = await api.get_controllers()
        if not controllers:
            print("❌ No controllers found")
            return False
        
        print(f"✅ Found {len(controllers)} controller(s)")
        
        # Test data fetch for each controller
        for controller in controllers:
            print(f"\nTesting controller: {controller['name']} (CID: {controller['cid']})...")
            
            data = await api.get_data(controller['cid'])
            if not data:
                print("❌ No data found")
                continue
            
            print("✅ Data fetch successful")
            print("\nCurrent values:")
            for key, value in data.items():
                if key != "debug_raw_html":  # Print all values except raw HTML
                    print(f"  {key}: {value}")
            
            # Print raw HTML for debugging
            if "debug_raw_html" in data:
                print("\nRaw HTML response:")
                print(data["debug_raw_html"])

        return True

def main():
    # Get credentials from environment variables
    username = os.environ.get('BAYROL_USERNAME')
    password = os.environ.get('BAYROL_PASSWORD')

    if not username or not password:
        print("❌ Error: Environment variables BAYROL_USERNAME and BAYROL_PASSWORD must be set")
        sys.exit(1)

    print("Testing Bayrol Pool Access API connection...")
    print(f"Username: {username}")

    result = asyncio.run(test_bayrol_api(username, password))
    
    if not result:
        print("\n❌ API test failed")
        sys.exit(1)
    else:
        print("\n✅ API test successful")
        sys.exit(0)

if __name__ == "__main__":
    main()
