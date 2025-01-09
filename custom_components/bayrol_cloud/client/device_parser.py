"""Parser for device status page."""
import logging
from typing import Dict, Any, List
from bs4 import BeautifulSoup
from .select_parser import parse_select_options

_LOGGER = logging.getLogger(__name__)

def parse_device_status(html: str) -> Dict[str, Any]:
    """Parse device status page HTML."""
    _LOGGER.debug("Starting to parse device status")
    soup = BeautifulSoup(html, 'html.parser')
    data = {}

    # Find all device divs (ones with i_x16 class)
    device_divs = soup.find_all('div', class_='i_x16')
    
    for device_div in device_divs:
        # Get device name and clean it for sensor ID
        name = device_div.text.strip()
        sensor_id = name.lower().replace(' ', '_').replace('(', '').replace(')', '')
        
        # Get the parent i_item div to extract its item number (e.g. item4_27)
        device_item = device_div.find_parent('div', class_='i_item')
        if not device_item:
            continue
            
        item_class = device_item.get('class', [])
        item_number = next((c for c in item_class if c.startswith('item')), None)
        if not item_number:
            continue
            
        # Find the corresponding mode div (next sibling with i_item class)
        mode_item = device_item.find_next_sibling('div', class_='i_item')
        if not mode_item:
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
        
        _LOGGER.debug("Found device status: %s = %s (value: %s)", 
                     sensor_id, selected_text, selected_value)
        _LOGGER.debug("Available options for %s: %s", 
                     sensor_id, [opt['text'] for opt in options])

    _LOGGER.debug("Parsed device status: %s", data)
    return data
