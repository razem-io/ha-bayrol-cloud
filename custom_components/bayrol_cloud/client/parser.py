"""Parser utilities for Bayrol Pool API responses."""
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from bs4 import BeautifulSoup
from datetime import datetime

_LOGGER = logging.getLogger(__name__)

def parse_login_form(html: str) -> Dict[str, str]:
    """Parse login form and extract all form fields."""
    _LOGGER.debug("Attempting to parse login form")
    soup = BeautifulSoup(html, 'html.parser')
    form = soup.find('form', {'id': 'form_login'})
    
    if not form:
        _LOGGER.error("Could not find login form in HTML response")
        return {}

    # Get all input fields from the form
    form_data = {}
    for input_field in form.find_all('input'):
        name = input_field.get('name')
        value = input_field.get('value', '')
        if name:
            form_data[name] = value
            _LOGGER.debug("Found form field: %s", name)
            
    _LOGGER.debug("Successfully parsed login form with fields: %s", list(form_data.keys()))
    return form_data

def check_login_error(html: str) -> bool:
    """Check if login response contains error messages."""
    _LOGGER.debug("Checking for login errors")
    if "Fehler" in html or "Zeit abgelaufen" in html:
        soup = BeautifulSoup(html, 'html.parser')
        error = soup.find('div', class_='error_text')
        if error:
            error_text = error.text.strip()
            _LOGGER.error("Login error: %s", error_text)
        else:
            _LOGGER.error("Generic login error detected but couldn't find specific error message")
        return True
    return False

def parse_controllers(html: str) -> List[Dict[str, str]]:
    """Parse controllers from plants page HTML."""
    _LOGGER.debug("Starting to parse controllers from HTML")
    soup = BeautifulSoup(html, 'html.parser')
    controllers = []
    
    # Find all divs that contain controller information
    controller_divs = soup.find_all('div', onclick=re.compile(r'plant_settings\.php\?c=\d+'))
    if not controller_divs:
        _LOGGER.error("No controller divs found in HTML")
        return controllers

    for div in controller_divs:
        # Extract CID from onclick attribute
        onclick = div.get('onclick', '')
        cid_match = re.search(r'c=(\d+)', onclick)
        if cid_match:
            cid = cid_match.group(1)
            
            # Try to find the controller name in nearby elements
            name_div = div.find_next('div', class_='tab_info')
            name = "Pool Controller"
            if name_div:
                spans = name_div.find_all('span')
                if len(spans) >= 2:
                    name = spans[1].text.strip()
                else:
                    _LOGGER.warning("Controller %s: Expected at least 2 spans in tab_info, found %d", 
                                  cid, len(spans))
            else:
                _LOGGER.warning("Controller %s: Could not find tab_info div", cid)
            
            controllers.append({
                "cid": cid,
                "name": name
            })
            _LOGGER.debug("Found controller: %s (CID: %s)", name, cid)
    
    _LOGGER.debug("Successfully parsed %d controllers", len(controllers))
    return controllers

class DebugInfo:
    """Class to store debug information during parsing."""
    def __init__(self):
        self.parsing_errors: List[str] = []
        self.measurements_found: List[str] = []
        self.measurements_failed: List[str] = []

    def to_dict(self) -> Dict[str, List[str]]:
        """Convert debug info to dictionary."""
        return {
            "parsing_errors": self.parsing_errors,
            "measurements_found": self.measurements_found,
            "measurements_failed": self.measurements_failed
        }

def check_device_offline(html: str) -> Optional[Dict[str, Any]]:
    """Check if the device is offline and extract offline information."""
    soup = BeautifulSoup(html, 'html.parser')
    error_div = soup.find('div', class_='tab_error')
    
    if error_div and "No connection to the controller" in error_div.text:
        # Extract the last seen time
        time_match = re.search(r'since (\d{2}\.\d{2}\.\d{2}, \d{2}:\d{2}) UTC', error_div.text)
        
        # Extract device ID
        info_div = soup.find('div', class_='tab_info')
        device_id = None
        if info_div:
            device_span = info_div.find('span')
            if device_span:
                device_id = device_span.text.strip()
        
        offline_info = {
            "status": "offline",
            "device_id": device_id,
            "last_seen": time_match.group(1) if time_match else None
        }
        
        _LOGGER.debug("Device is offline: %s", offline_info)
        return offline_info
    
    return None

def parse_pool_data(html: str) -> Dict[str, Any]:
    """Parse pool data from getdata response HTML."""
    _LOGGER.debug("Starting to parse pool data")
    soup = BeautifulSoup(html, 'html.parser')
    data = {}
    debug = DebugInfo()
    
    # First check if device is offline
    offline_info = check_device_offline(html)
    if offline_info:
        return offline_info
    
    boxes = soup.find_all("div", class_="tab_box")
    if not boxes:
        error_msg = "No tab_box divs found in HTML response"
        _LOGGER.error(error_msg)
        debug.parsing_errors.append(error_msg)
        return data
    
    measurement_map = {
        'pH': 'pH',
        'Redox': 'mV',
        'Temp.': 'T',
        'mV': 'mV',
        'T': 'T',
        'T1': 'T'
    }
    
    for box in boxes:
        span = box.find("span")
        h1 = box.find("h1")
        if span and h1:
            # Extract the label before the unit
            label_text = span.text.strip()
            label_match = re.match(r'^([^[]+)', label_text)
            if label_match:
                raw_label = label_match.group(1).replace('\xa0', ' ').strip()
                # Map the raw label to standardized key
                label = measurement_map.get(raw_label)
                if label:
                    value = h1.text.strip()
                    try:
                        data[label] = float(value)
                        # Check for both warning and alarm states
                        box_classes = box.get('class', [])
                        has_alarm = 'stat_warning' in box_classes or 'stat_alarm' in box_classes
                        data[f"{label}_alarm"] = has_alarm
                        debug.measurements_found.append(f"{label}: {value}")
                        _LOGGER.debug("Successfully parsed %s: %s (alarm: %s)", 
                                    label, value, has_alarm)
                    except ValueError:
                        error_msg = f"Failed to convert value '{value}' to float for measurement '{label}'"
                        _LOGGER.error(error_msg)
                        debug.measurements_failed.append(error_msg)
                else:
                    error_msg = f"Unknown measurement label: {raw_label}"
                    _LOGGER.warning(error_msg)
                    debug.parsing_errors.append(error_msg)
    
    if not data:
        error_msg = "No valid measurements found in response"
        _LOGGER.error(error_msg)
        debug.parsing_errors.append(error_msg)
    else:
        _LOGGER.debug("Successfully parsed pool data: %s", data)
        data["status"] = "online"
    
    # Store debug info in the logger context for Home Assistant to access
    _LOGGER.debug("Debug information: %s", debug.to_dict())
        
    return data
