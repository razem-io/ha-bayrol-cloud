#!/usr/bin/env python3
import asyncio
import aiohttp
import argparse
import sys
import logging
from custom_components.bayrol_cloud.client.bayrol_api import BayrolPoolAPI

# Set up logging
logging.basicConfig(level=logging.DEBUG)
_LOGGER = logging.getLogger(__name__)

async def test_bayrol_api(username: str, password: str):
    """Test Bayrol Pool Access API authentication and data fetching."""
    async with aiohttp.ClientSession() as session:
        # Initialize API with credentials
        api = BayrolPoolAPI(session, username, password)

        # Test login
        print("\nTesting login...")
        if not await api.login():
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
                print(f"  {key}: {value}")

        return True

def main():
    parser = argparse.ArgumentParser(description='Test Bayrol Pool Access API')
    parser.add_argument('--username', required=True, help='Bayrol Pool Access username')
    parser.add_argument('--password', required=True, help='Bayrol Pool Access password')
    
    args = parser.parse_args()

    print("Testing Bayrol Pool Access API connection...")
    print(f"Username: {args.username}")

    result = asyncio.run(test_bayrol_api(args.username, args.password))
    
    if not result:
        print("\n❌ API test failed")
        sys.exit(1)
    else:
        print("\n✅ API test successful")
        sys.exit(0)

if __name__ == "__main__":
    main()
