#!/usr/bin/env python3
import asyncio
import aiohttp
import sys
import logging
import os
import hashlib
import re
from custom_components.bayrol_cloud.client.bayrol_api import BayrolPoolAPI
from custom_components.bayrol_cloud.client.http_client import BayrolHttpClient

# Set up logging
logging.basicConfig(level=logging.DEBUG)
_LOGGER = logging.getLogger(__name__)

async def test_settings_page(username: str, password: str, cid: str, page: str, device_password: str = "1234"):
    """Test accessing a specific settings page."""
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

        # First get the main device page
        print(f"\nAccessing main device page for CID {cid}...")
        http_client = api._client
        
        try:
            # Get the main device page first
            main_url = f"https://www.bayrol-poolaccess.de/webview/p/device.php?c={cid}"
            headers = http_client._get_headers()
            headers["Referer"] = "https://www.bayrol-poolaccess.de/m/plants.php"
            
            async with session.get(main_url, headers=headers) as response:
                if response.status != 200:
                    print(f"❌ Failed to access main device page: {response.status}")
                    return False
                
                main_html = await response.text()
                print("✅ Successfully accessed main device page")
            
            # Submit the device password
            print(f"\nSubmitting device password...")
            password_url = f"https://www.bayrol-poolaccess.de/webview/p/device.php?c={cid}"
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            
            # Submit the device password using JSON request
            print(f"\nSubmitting device password...")
            password_url = f"https://www.bayrol-poolaccess.de/webview/data_json.php"
            headers.update({
                "Content-Type": "application/json; charset=utf-8",
                "Referer": main_url,
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "X-Requested-With": "XMLHttpRequest"
            })
            
            # First set the code
            print("\nSetting device password...")
            set_code_data = {
                "device": cid,
                "action": "setCode",
                "data": {
                    "code": device_password
                }
            }
            
            async with session.post(password_url, headers=headers, json=set_code_data) as response:
                if response.status != 200:
                    print(f"❌ Failed to set device password: {response.status}")
                    return False
                
                response_text = await response.text()
                print("\nSet code response:")
                print(response_text)
                
                # Check if response indicates success
                if '"error":""' not in response_text:
                    print("❌ Failed to set device password")
                    return False
            
            # Then get access
            print("\nGetting access...")
            get_access_data = {
                "device": cid,
                "action": "getAccess",
                "data": {
                    "code": device_password
                }
            }
            
            async with session.post(password_url, headers=headers, json=get_access_data) as response:
                if response.status != 200:
                    print(f"❌ Failed to get access: {response.status}")
                    return False
                
                response_text = await response.text()
                print("\nGet access response:")
                print(response_text)
                
                # Check if response indicates success
                if '"data":{"access":true}' not in response_text:
                    print("❌ Device password not accepted")
                    return False
                
                print("✅ Device password accepted")
            
            # Now access the specific settings page
            print(f"\nAccessing settings page {page}...")
            settings_url = f"https://www.bayrol-poolaccess.de/webview/p/device.php?c={cid}&p={page}"
            headers["Referer"] = main_url
            
            async with session.get(settings_url, headers=headers) as response:
                if response.status != 200:
                    print(f"❌ Failed to access settings page: {response.status}")
                    return False
                
                html = await response.text()
                print("✅ Successfully accessed settings page")
                print("\nRaw HTML response:")
                print(html)
                
                # Now let's toggle the alarm relay setting
                print("\nToggling alarm relay (OUT4) setting...")
                
                # First get the current value from the HTML
                # Look for the alarm relay select element
                alarm_relay_match = re.search(r'item3_153.*?<select.*?>(.*?)</select>', html, re.DOTALL)
                if not alarm_relay_match:
                    print("❌ Could not find alarm relay settings in HTML")
                    return False
                
                select_html = alarm_relay_match.group(1)
                current_value = "1"  # Default to Aus
                if 'value="0" selected' in select_html:
                    current_value = "0"  # Currently Auto
                
                # Toggle the value
                new_value = "0" if current_value == "1" else "1"
                new_value_text = "Auto" if new_value == "0" else "Aus"
                print(f"Current value: {'Auto' if current_value == '0' else 'Aus'}")
                print(f"New value: {new_value_text}")
                
                # Prepare the setItems request
                set_items_data = {
                    "device": cid,
                    "action": "setItems",
                    "data": {
                        "items": [{
                            "topic": "3.153",  # Topic for alarm relay mode
                            "name": "Betriebsart",
                            # Create value list with 1 at the position corresponding to the selected value
                            # For example, for OUT4:
                            # Auto (value 0): [1, 0]
                            # Aus (value 1): [0, 1]
                            "value": [0] * 2,  # Create list of zeros with length equal to number of options
                            "valid": 1,
                            "cmd": 0
                        }]
                    }
                }
                # Set 1 at the position corresponding to the selected value
                set_items_data["data"]["items"][0]["value"][int(new_value)] = 1
                print(set_items_data)
                print("\nSending setItems request...")
                async with session.post(password_url, headers=headers, json=set_items_data) as response:
                    if response.status != 200:
                        print(f"❌ Failed to set items: {response.status}")
                        return False
                    
                    response_text = await response.text()
                    print("\nSet items response:")
                    print(response_text)
                    
                    if '"error":""' not in response_text:
                        print("❌ Failed to set items")
                        return False
                    
                    print("✅ Successfully toggled alarm relay setting")
                    
                    # Try for up to 10 seconds to verify the change
                    print("\nVerifying change (will retry for 10 seconds)...")
                    for retry in range(10):
                        # Get the page to check current state
                        async with session.get(settings_url, headers=headers) as verify_response:
                            verify_html = await verify_response.text()
                            verify_match = re.search(r'item3_153.*?<select.*?>(.*?)</select>', verify_html, re.DOTALL)
                            if verify_match:
                                verify_select = verify_match.group(1)
                                print(f"\nAttempt {retry + 1} - Current OUT4 HTML:")
                                print(verify_select)
                                
                                # Check if either the value or text indicates the change
                                value_changed = f'value="{new_value}" selected' in verify_select
                                text_changed = f'>{new_value_text}<' in verify_select
                                
                                if value_changed or text_changed:
                                    print(f"✅ Verified OUT4 change (value_changed={value_changed}, text_changed={text_changed})")
                                    return True
                                else:
                                    print(f"❌ OUT4 change not yet visible (attempt {retry + 1}/10), waiting 1 second...")
                                    await asyncio.sleep(1)
                    
                    print("❌ Failed to verify change after 10 seconds")
                    return False

        except Exception as err:
            print(f"❌ Error accessing settings page: {err}")
            return False

def main():
    # Get credentials from environment variables
    username = os.environ.get('BAYROL_USERNAME')
    password = os.environ.get('BAYROL_PASSWORD')

    if not username or not password:
        print("❌ Error: Environment variables BAYROL_USERNAME and BAYROL_PASSWORD must be set")
        sys.exit(1)

    # Settings page parameters
    cid = "39516"
    page = "switching"  # Main switching page to see all outputs
    device_password = "1234"  # Default device password

    print("Testing Bayrol Pool Access settings page...")
    print(f"Username: {username}")
    print(f"CID: {cid}")
    print(f"Page: {page}")
    print(f"Device Password: {device_password}")

    result = asyncio.run(test_settings_page(username, password, cid, page, device_password))
    
    if not result:
        print("\n❌ Settings page test failed")
        sys.exit(1)
    else:
        print("\n✅ Settings page test successful")
        sys.exit(0)

if __name__ == "__main__":
    main()
