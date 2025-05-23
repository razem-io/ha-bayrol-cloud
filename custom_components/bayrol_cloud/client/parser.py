"""Parser utilities for Bayrol Pool API responses."""
import logging

from ..helpers import conditional_log
import re
from typing import Any, Dict, List, Optional, Tuple
from .constants import COMPATIBLE_DEVICE_MODELS, GITHUB_ISSUES_URL
from bs4 import BeautifulSoup
from datetime import datetime

_LOGGER = logging.getLogger(__name__)

def parse_login_form(html: str, debug: bool = False) -> Dict[str, str]:
    """Parse login form and extract all form fields."""
    conditional_log(_LOGGER, logging.DEBUG, "Attempting to parse login form", debug_mode=debug)
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
            conditional_log(_LOGGER, logging.DEBUG, "Found form field: %s", name, debug_mode=debug)
            
    conditional_log(_LOGGER, logging.DEBUG, "Successfully parsed login form with fields: %s", list(form_data.keys()), debug_mode=debug)
    return form_data

def check_login_error(html: str, debug: bool = False) -> bool:
    """Check if login response contains error messages."""
    conditional_log(_LOGGER, logging.DEBUG, "Checking for login errors", debug_mode=debug)
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

def parse_controllers(html: str, debug: bool = False) -> List[Dict[str, str]]:
    """Parse controllers from plants page HTML."""
    conditional_log(_LOGGER, logging.DEBUG, "Starting to parse controllers from HTML", debug_mode=debug)
    soup = BeautifulSoup(html, 'html.parser')
    controllers = []
    
    # Find all tab_row divs, each containing a separate controller
    tab_rows = soup.find_all('div', class_='tab_row')
    if not tab_rows:
        _LOGGER.error("No tab_row divs found in HTML")
        return controllers

    for tab_row in tab_rows:
        # Find the tab_1 div containing controller info
        tab_1 = tab_row.find('div', class_='tab_1')
        # Find the tab_2 div containing controller data
        tab_2 = tab_row.find('div', class_='tab_2')
        
        if not tab_1 or not tab_2:
            _LOGGER.warning("Incomplete controller data in tab_row: missing tab_1 or tab_2")
            continue
        
        # Extract controller ID from tab_2 ID or from onclick in tab_1
        cid = None
        # Try to get cid from tab_2 id attribute (format: tab_data{cid})
        if 'id' in tab_2.attrs:
            tab_id_match = re.search(r'tab_data(\d+)', tab_2.get('id', ''))
            if tab_id_match:
                cid = tab_id_match.group(1)
        
        # If we couldn't get cid from tab_2 id, try from onclick in tab_1
        if not cid:
            onclick_div = tab_1.find('div', onclick=re.compile(r'plant_settings\.php\?c=\d+'))
            if onclick_div:
                onclick = onclick_div.get('onclick', '')
                cid_match = re.search(r'c=(\d+)', onclick)
                if cid_match:
                    cid = cid_match.group(1)
        
        if not cid:
            _LOGGER.warning("Could not find controller ID in tab_row")
            continue
        
        # Extract controller name from tab_1
        name = "Pool Controller"
        p_tag = tab_1.find('p')
        if p_tag:
            name = p_tag.text.strip()
        
        # If no name in p tag, try to get from tab_info in tab_2
        if name == "Pool Controller":
            tab_info = tab_2.find('div', class_='tab_info')
            if tab_info:
                spans = tab_info.find_all('span')
                if len(spans) >= 2:
                    name = spans[1].text.strip()
        
        controllers.append({
            "cid": cid,
            "name": name
        })
        conditional_log(_LOGGER, logging.DEBUG, "Found controller: %s (CID: %s)", name, cid, debug_mode=debug)
    
    conditional_log(_LOGGER, logging.DEBUG, "Successfully parsed %d controllers", len(controllers), debug_mode=debug)
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

def check_device_offline(html: str, debug: bool = False) -> Optional[Dict[str, Any]]:
    """Check if the device is offline and extract offline information."""
    soup = BeautifulSoup(html, 'html.parser')
    
    # First check if we're looking at a device page for a specific controller
    # or the plants overview page with multiple controllers
    
    # Handle device page for a specific controller
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
        
        conditional_log(_LOGGER, logging.DEBUG, "Device is offline: %s", offline_info, debug_mode=debug)
        return offline_info
    
    # Handle plants overview page with potentially multiple controllers
    # Look for tab_row divs with error indications
    tab_rows = soup.find_all('div', class_='tab_row')
    for tab_row in tab_rows:
        tab_2 = tab_row.find('div', class_='tab_2')
        if tab_2:
            error_div = tab_2.find('div', class_='tab_error')
            if error_div and "No connection to the controller" in error_div.text:
                # Extract the controller ID from tab_2 id attribute
                cid = None
                if 'id' in tab_2.attrs:
                    tab_id_match = re.search(r'tab_data(\d+)', tab_2.get('id', ''))
                    if tab_id_match:
                        cid = tab_id_match.group(1)
                
                # Try to get the last seen time
                time_match = re.search(r'since (\d{2}\.\d{2}\.\d{2}, \d{2}:\d{2}) UTC', error_div.text)
                
                # Try to get device ID from tab_info
                info_div = tab_2.find('div', class_='tab_info')
                device_id = None
                if info_div:
                    device_span = info_div.find('span')
                    if device_span:
                        device_id = device_span.text.strip()
                
                offline_info = {
                    "status": "offline",
                    "cid": cid,
                    "device_id": device_id,
                    "last_seen": time_match.group(1) if time_match else None
                }
                
                conditional_log(_LOGGER, logging.DEBUG, "Controller %s is offline: %s", cid, offline_info, debug_mode=debug)
                return offline_info
    
    return None

def check_device_compatibility(device_model: str) -> bool:
    """Check if a device model is in the compatibility list."""
    return device_model in COMPATIBLE_DEVICE_MODELS

def parse_overview_page(html: str, debug: bool = False) -> Dict[str, Dict[str, Any]]:
    """Parse pool data from the overview page HTML.
    
    Returns a dict with controller ID as key and device data as value.
    Used as a fallback when direct access is not available or fails.
    """
    conditional_log(_LOGGER, logging.DEBUG, "Starting to parse overview page", debug_mode=debug)
    soup = BeautifulSoup(html, 'html.parser')
    results = {}
    
    # Find all tab_row divs, each containing a separate controller
    tab_rows = soup.find_all('div', class_='tab_row')
    if not tab_rows:
        _LOGGER.error("No tab_row divs found in HTML")
        return results

    for tab_row in tab_rows:
        # Find the tab_1 div containing controller info
        tab_1 = tab_row.find('div', class_='tab_1')
        # Find the tab_2 div containing controller data
        tab_2 = tab_row.find('div', class_='tab_2')
        
        if not tab_1 or not tab_2:
            _LOGGER.warning("Incomplete controller data in tab_row: missing tab_1 or tab_2")
            continue
        
        # Extract controller ID from tab_1 onclick attribute
        cid = None
        onclick_div = tab_1.find('div', onclick=re.compile(r'plant_settings\.php\?c=\d+'))
        if onclick_div:
            onclick = onclick_div.get('onclick', '')
            cid_match = re.search(r'c=(\d+)', onclick)
            if cid_match:
                cid = cid_match.group(1)
        
        # If we couldn't get cid from tab_1, try from tab_2 id attribute
        if not cid and 'id' in tab_2.attrs:
            tab_id_match = re.search(r'tab_data(\d+)', tab_2.get('id', ''))
            if tab_id_match:
                cid = tab_id_match.group(1)
                
        if not cid:
            _LOGGER.warning("Could not find controller ID in tab_row")
            continue
            
        # Extract device name from tab_1
        name = "Pool Controller"
        p_tag = tab_1.find('p')
        if p_tag:
            name = p_tag.text.strip()
        
        # Parse measurements from tab_2
        data = {}
        
        # Extract device model and version from tab_info
        device_model = None
        device_version = None
        tab_info = tab_2.find('div', class_='tab_info')
        if tab_info:
            spans = tab_info.find_all('span')
            if len(spans) >= 2:
                device_id = spans[0].text.strip() if spans[0] else None
                device_model = spans[1].text.strip() if spans[1] else None
                device_version = spans[2].text.strip() if len(spans) > 2 and spans[2] else None
                
                data["device_id"] = device_id
                data["device_model"] = device_model
                data["device_version"] = device_version
                
                # Check compatibility
                if device_model and not check_device_compatibility(device_model):
                    _LOGGER.warning(
                        "Device model '%s' is not in the compatibility list but was successfully parsed. "
                        "Please consider opening an issue at %s to get this device added.",
                        device_model, GITHUB_ISSUES_URL
                    )
        
        # Extract measurement values
        tab_boxes = tab_2.find_all('div', class_='tab_box')
        measurement_map = {
            'pH': 'pH',
            'Redox': 'mV',
            'mV': 'mV',
            'Cl': 'Cl',
            'Salz': 'Salt',
            'T': 'T',
            'T1': 'T'
        }
        
        for box in tab_boxes:
            span = box.find('span')
            h1 = box.find('h1')
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
                            conditional_log(_LOGGER, logging.DEBUG, "Successfully parsed %s: %s (alarm: %s)", 
                                        label, value, has_alarm, debug_mode=debug)
                        except ValueError:
                            _LOGGER.error("Failed to convert value '%s' to float for measurement '%s'", value, label)
                    else:
                        conditional_log(_LOGGER, logging.DEBUG, "Unknown measurement label: %s", raw_label, debug_mode=debug)
        
        if data:
            data["status"] = "online"
            data["name"] = name
            results[cid] = data
            conditional_log(_LOGGER, logging.DEBUG, "Successfully parsed controller %s data: %s", cid, data, debug_mode=debug)
            
    if not results:
        _LOGGER.warning("No controller data found in overview page")
        
    return results

def parse_pool_data(html: str, debug: bool = False) -> Dict[str, Any]:
    """Parse pool data from getdata response HTML."""
    conditional_log(_LOGGER, logging.DEBUG, "Starting to parse pool data", debug_mode=debug)
    soup = BeautifulSoup(html, 'html.parser')
    data = {}
    debug = DebugInfo()
    
    # First check if device is offline
    offline_info = check_device_offline(html, debug=debug)
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
        'Cl': 'Cl',
        'Salz': 'Salt',
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
                        conditional_log(_LOGGER, logging.DEBUG, "Successfully parsed %s: %s (alarm: %s)", 
                                    label, value, has_alarm, debug_mode=debug)
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
        conditional_log(_LOGGER, logging.DEBUG, "Successfully parsed pool data: %s", data, debug_mode=debug)
        data["status"] = "online"
    
    # Store debug info in the logger context for Home Assistant to access
    conditional_log(_LOGGER, logging.DEBUG, "Debug information: %s", debug.to_dict(), debug_mode=debug)
        
    return data

def get_available_measurements(data: Dict[str, Any]) -> List[str]:
    """Extract available measurement keys from parsed data.
    
    Returns a list of measurement keys that have actual values in the data.
    This excludes alarm keys, status, and device info.
    """
    if not data or not isinstance(data, dict):
        return []
    
    # Define keys that are not measurements
    non_measurement_keys = {
        'status', 'name', 'device_id', 'device_model', 'device_version', 'last_seen'
    }
    
    measurements = []
    for key, value in data.items():
        # Skip non-measurement keys and alarm keys
        if key in non_measurement_keys or key.endswith('_alarm'):
            continue
        
        # Only include keys that have numeric values
        if isinstance(value, (int, float)):
            measurements.append(key)
    
    return measurements
