"""Parser for device status page."""
import logging
import re
from typing import Dict, Any, List
from bs4 import BeautifulSoup
from .select_parser import parse_select_options
from ..helpers import conditional_log

_LOGGER = logging.getLogger(__name__)

def parse_device_status(html: str, debug: bool = False) -> Dict[str, Any]:
    """Parse device status page HTML."""
    if not html:
        conditional_log(_LOGGER, logging.DEBUG, "Empty HTML provided for device status parsing", debug_mode=debug)
        return {}
        
    try:
        html_length = len(html)
        conditional_log(_LOGGER, logging.DEBUG, "Starting to parse device status (HTML length: %d bytes)", html_length, debug_mode=debug)
        
        # Create a snippet for debugging that won't overwhelm logs
        html_snippet = html[:200] + "..." if len(html) > 200 else html
        conditional_log(_LOGGER, logging.DEBUG, "HTML snippet: %s", html_snippet, debug_mode=debug)
        
        soup = BeautifulSoup(html, 'html.parser')
        data = {}

        # First determine if we're dealing with a page with tabs (multiple controllers)
        tab_rows = soup.find_all('div', class_='tab_row')
        
        if tab_rows:
            conditional_log(_LOGGER, logging.DEBUG, "Found tab_row structure (%d tab rows) - this is the standard layout with or without multiple controllers", len(tab_rows), debug_mode=debug)
            # Process each controller tab separately
            for tab_index, tab_row in enumerate(tab_rows):
                tab_prefix = f"tab_{tab_index + 1}_"
                
                # Find the tab_2 div containing the actual data
                tab_2 = tab_row.find('div', class_='tab_2')
                if not tab_2:
                    _LOGGER.warning(f"Tab row {tab_index + 1} missing tab_2 div")
                    continue
                    
                # Extract controller ID from tab_2 id attribute
                cid = None
                if 'id' in tab_2.attrs:
                    tab_id_match = re.search(r'tab_data(\d+)', tab_2.get('id', ''))
                    if tab_id_match:
                        cid = tab_id_match.group(1)
                
                # Find all device divs in this tab (ones with i_x16 class)
                device_divs = tab_2.find_all('div', class_='i_x16')
                
                # Process devices in this controller tab
                process_device_divs(device_divs, data, tab_prefix, debug=debug)
        # Check if we have a content_m div which contains the device controls
        content_m = soup.find('div', id='content_m')
        if content_m:
            conditional_log(_LOGGER, logging.DEBUG, "Found content_m div - attempting to parse device controls", debug_mode=debug)
            # This div contains the controller device controls
            i_items = content_m.find_all('div', class_='i_item')
            if i_items:
                conditional_log(_LOGGER, logging.DEBUG, "Found %d i_item divs in content_m", len(i_items), debug_mode=debug)
                
                # Process the controller items
                process_controller_items(i_items, data, debug=debug)
                
                if data:
                    return data
        
        # If we didn't find content_m or couldn't process it, try the regular approach
        if not data:
            # Regular single controller page - find all device divs directly
            conditional_log(_LOGGER, logging.DEBUG, "No tab_row structure found - assuming single controller page", debug_mode=debug)
            device_divs = soup.find_all('div', class_='i_x16')
            if not device_divs:
                _LOGGER.warning("No device divs (class='i_x16') found in HTML. HTML structure may have changed.")
                conditional_log(_LOGGER, logging.DEBUG, "Page title: %s", soup.title.string if soup.title else "No title", debug_mode=debug)
                # Look for other common classes to help diagnose
                other_classes = [
                    ('i_item', len(soup.find_all('div', class_='i_item'))),
                    ('tab_info', len(soup.find_all('div', class_='tab_info'))),
                    ('tab_box', len(soup.find_all('div', class_='tab_box'))),
                ]
                conditional_log(_LOGGER, logging.DEBUG, "Found other elements: %s", other_classes, debug_mode=debug)
                if debug:
                    conditional_log(_LOGGER, logging.DEBUG, "Raw HTML when no device divs found:\n%s", html, debug_mode=debug)
                return {}
                
            conditional_log(_LOGGER, logging.DEBUG, "Found %d device divs", len(device_divs), debug_mode=debug)
            process_device_divs(device_divs, data, debug=debug)
        
        if not data:
            _LOGGER.warning("Device status parsing resulted in empty data")
            if debug:
                conditional_log(_LOGGER, logging.DEBUG, "Raw HTML that failed parsing:\n%s", html, debug_mode=debug)
            return {}
            
        conditional_log(_LOGGER, logging.DEBUG, "Parsed device status: %s", data, debug_mode=debug)
        return data
    except Exception as e:
        _LOGGER.warning("Error parsing device status HTML: %s", str(e))
        if debug:
            conditional_log(_LOGGER, logging.DEBUG, "Raw HTML that caused exception:\n%s", html, debug_mode=debug)
        return {}

def process_controller_items(i_items, data, prefix='', debug=False):
    """Process controller items from content_m div.
    
    Args:
        i_items: List of i_item divs 
        data: Dictionary to store device data in
        prefix: Optional prefix for sensor IDs
        debug: Whether debug logging is enabled
    """
    # First pass: identify device divs
    device_map = {}
    current_device = None
    current_device_div = None
    
    for i in range(len(i_items)):
        item = i_items[i]
        item_classes = item.get('class', [])
        item_number = next((c for c in item_classes if c.startswith('item')), None)
        if not item_number:
            continue
            
        # Find device div with i_x16 class
        device_div = item.find('div', class_='i_x16')
        if device_div:
            # This is a device div
            device_name = device_div.text.strip()
            device_id = device_name.lower().replace(' ', '_').replace('(', '').replace(')', '')
            current_device = device_id
            current_device_div = device_div
            device_map[i] = {"device_id": device_id, "device_name": device_name, "item_number": item_number}
    
    # Second pass: find the control div that follows each device div and process it
    for i in range(len(i_items)):
        if i in device_map:
            # This is a device div, skip as we've already processed it
            continue
            
        item = i_items[i]
        # Look for the operation mode div with a select that follows a device div
        select = item.find('select', class_='i_x7')
        if not select:
            continue
            
        # Find the div containing the operation mode name (Betriebsart)
        operation_div = item.find('div', class_='i_x9')
        if not operation_div:
            continue
            
        # Get the operation name
        operation_name = operation_div.text.strip()
        
        # Find the device this control belongs to by looking for the last device before this control
        associated_device = None
        for device_idx in sorted(device_map.keys(), reverse=True):
            if device_idx < i:
                associated_device = device_map[device_idx]
                break
                
        if not associated_device:
            # Couldn't find an associated device, use operation name only
            conditional_log(_LOGGER, logging.DEBUG, "No associated device found for control at index %d", i, debug_mode=debug)
            continue
            
        # Create a unique ID using the device ID
        device_id = associated_device["device_id"]
        device_name = associated_device["device_name"]
        
        # Get item class for the control
        item_classes = item.get('class', [])
        item_number = next((c for c in item_classes if c.startswith('item')), None)
        if not item_number:
            continue
            
        # Parse options using our tested select parser
        options, selected_value, selected_text = parse_select_options(str(select))
        
        # Just use the device ID as the sensor ID without the operation name
        # This will prevent duplicate entities with "betriebsart" suffix
        sensor_id = device_id
        # Add prefix if specified
        if prefix:
            sensor_id = f"{prefix}{sensor_id}"
            
        # Store the sensor data
        data[sensor_id] = {
            'name': device_name,
            'operation_name': operation_name,
            'item_number': item_number,
            'options': options,
            'current_value': selected_value,
            'current_text': selected_text
        }
        
        conditional_log(_LOGGER, logging.DEBUG, "Found controller item: %s %s = %s (value: %s)", 
                    device_name, operation_name, selected_text, selected_value, debug_mode=debug)
        conditional_log(_LOGGER, logging.DEBUG, "Available options for %s: %s", 
                    sensor_id, [opt['text'] for opt in options], debug_mode=debug)

def process_device_divs(device_divs, data, prefix='', debug=False):
    """Process device divs to extract select options.
    
    Args:
        device_divs: List of device divs with class 'i_x16'
        data: Dictionary to store device data in
        prefix: Optional prefix for sensor IDs (e.g., 'tab_1_'). 
               This is used to create unique IDs when handling multiple controllers,
               even though tab_row structure is present for single controller as well.
        debug: Whether debug logging is enabled
    """
    for device_div in device_divs:
        # Get device name and clean it for sensor ID
        name = device_div.text.strip()
        sensor_id = name.lower().replace(' ', '_').replace('(', '').replace(')', '')
        
        # Add prefix if specified (creates unique IDs for multiple controller scenarios)
        if prefix:
            original_id = sensor_id
            sensor_id = f"{prefix}{original_id}"
            conditional_log(_LOGGER, logging.DEBUG, "Using prefixed ID %s (original: %s) for controller distinction", 
                         sensor_id, original_id, debug_mode=debug)
        
        # Find the corresponding mode div (next sibling with i_item class)
        mode_item = device_div.find_parent('div', class_='i_item').find_next_sibling('div', class_='i_item')
        if not mode_item:
            continue
            
        # Get the item number from the mode div (e.g. item3_153)
        item_class = mode_item.get('class', [])
        item_number = next((c for c in item_class if c.startswith('item')), None)
        if not item_number:
            continue
            
        # Get the select element with operating modes
        select = mode_item.find('select', class_='i_x7')
        if not select:
            continue
            
        # Parse options using our tested select parser
        options, selected_value, selected_text = parse_select_options(str(select))
        
        # Store the sensor data
        data[sensor_id] = {
            'name': name,
            'item_number': item_number,
            'options': options,
            'current_value': selected_value,
            'current_text': selected_text
        }
        
        conditional_log(_LOGGER, logging.DEBUG, "Found device status: %s = %s (value: %s)", 
                    sensor_id, selected_text, selected_value, debug_mode=debug)
        conditional_log(_LOGGER, logging.DEBUG, "Available options for %s: %s", 
                    sensor_id, [opt['text'] for opt in options], debug_mode=debug)
