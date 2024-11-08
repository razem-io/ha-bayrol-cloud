"""Parser utilities for Bayrol Pool API responses."""
import logging
import re
from typing import Any, Dict, List
from bs4 import BeautifulSoup

_LOGGER = logging.getLogger(__name__)

def parse_login_form(html: str) -> Dict[str, str]:
    """Parse login form and extract all form fields."""
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
            
    return form_data

def check_login_error(html: str) -> bool:
    """Check if login response contains error messages."""
    if "Fehler" in html or "Zeit abgelaufen" in html:
        soup = BeautifulSoup(html, 'html.parser')
        error = soup.find('div', class_='error_text')
        if error:
            error_text = error.text.strip()
            _LOGGER.error("Login error: %s", error_text)
        return True
    return False

def parse_controllers(html: str) -> List[Dict[str, str]]:
    """Parse controllers from plants page HTML."""
    soup = BeautifulSoup(html, 'html.parser')
    controllers = []
    
    # Find all divs that contain controller information
    for div in soup.find_all('div', onclick=re.compile(r'plant_settings\.php\?c=\d+')):
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
            
            controllers.append({
                "cid": cid,
                "name": name
            })
    
    return controllers

def parse_pool_data(html: str) -> Dict[str, Any]:
    """Parse pool data from getdata response HTML."""
    soup = BeautifulSoup(html, 'html.parser')
    data = {}
    
    boxes = soup.find_all("div", class_="tab_box")
    
    for box in boxes:
        span = box.find("span")
        h1 = box.find("h1")
        if span and h1:
            label = span.text.strip().split()[0]  # Get first word (pH, mV, T)
            value = h1.text.strip()
            try:
                data[label] = float(value)
            except ValueError:
                _LOGGER.warning("Could not convert value to float: %s", value)
    
    if not data:
        _LOGGER.error("No data found in response: %s", html)
        
    return data
