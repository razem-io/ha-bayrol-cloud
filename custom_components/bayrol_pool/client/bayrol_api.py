"""Standalone API client for Bayrol Pool Access."""
import logging
import re
from typing import Any, Dict

import aiohttp
from bs4 import BeautifulSoup

# Set up logging
_LOGGER = logging.getLogger(__name__)

class BayrolPoolAPI:
    """Bayrol Pool API client."""

    BASE_URL = "https://www.bayrol-poolaccess.de/webview"
    
    # Common headers used in all requests
    BASE_HEADERS = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:131.0) Gecko/20100101 Firefox/131.0",
        "Accept-Language": "de,en-US;q=0.7,en;q=0.3",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Connection": "keep-alive",
        "Sec-Fetch-User": "?1",
    }

    def __init__(self, session: aiohttp.ClientSession, username: str | None = None, password: str | None = None):
        """Initialize the API client."""
        self._session = session
        self._username = username
        self._password = password
        self._phpsessid = None

    def _get_headers(self, additional_headers: Dict[str, str] | None = None) -> Dict[str, str]:
        """Get headers with optional additions and session cookie if available."""
        headers = self.BASE_HEADERS.copy()
        
        if self._phpsessid:
            headers["Cookie"] = f"PHPSESSID={self._phpsessid}"
            
        if additional_headers:
            headers.update(additional_headers)
            
        return headers

    async def login(self, username: str | None = None, password: str | None = None) -> bool:
        """Login to Bayrol Pool Access."""
        if username:
            self._username = username
        if password:
            self._password = password

        if not self._username or not self._password:
            _LOGGER.error("Username and password are required")
            return False

        try:
            # First get the login page and extract form data
            _LOGGER.debug("Initializing session...")
            init_url = f"{self.BASE_URL}/m/login.php"
            
            init_headers = self._get_headers({
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/png,image/svg+xml,*/*;q=0.8",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
            })
            
            async with self._session.get(init_url, headers=init_headers) as response:
                html = await response.text()
                
                # Get all cookies from the response
                cookies = response.cookies
                _LOGGER.debug("Received cookies: %s", cookies)
                
                # Try to get PHPSESSID from cookies
                phpsessid = None
                for cookie in cookies.values():
                    if cookie.key == 'PHPSESSID':
                        phpsessid = cookie.value
                        break
                
                # If no PHPSESSID in cookies, try to get it from Set-Cookie header
                if not phpsessid and 'Set-Cookie' in response.headers:
                    cookie_header = response.headers['Set-Cookie']
                    _LOGGER.debug("Set-Cookie header: %s", cookie_header)
                    match = re.search(r'PHPSESSID=([^;]+)', cookie_header)
                    if match:
                        phpsessid = match.group(1)

                if not phpsessid:
                    _LOGGER.error("No PHPSESSID cookie received. Response headers: %s", response.headers)
                    _LOGGER.debug("Response content: %s", html[:500])  # Log first 500 chars of response
                    return False

                self._phpsessid = phpsessid
                _LOGGER.debug("Got session ID: %s", self._phpsessid)

                # Extract all form fields
                soup = BeautifulSoup(html, 'html.parser')
                form = soup.find('form', {'id': 'form_login'})
                
                if not form:
                    _LOGGER.error("Could not find login form")
                    return False

                # Get all input fields from the form
                form_data = {}
                for input_field in form.find_all('input'):
                    name = input_field.get('name')
                    value = input_field.get('value', '')
                    if name:
                        form_data[name] = value

                # Update with our credentials
                form_data['username'] = self._username
                form_data['password'] = self._password
                
                _LOGGER.debug("Form fields: %s", list(form_data.keys()))

            # Try to login with the complete form data
            _LOGGER.debug("Attempting login...")
            login_url = f"{self.BASE_URL}/m/login.php?r=reg"
            
            login_headers = self._get_headers({
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/png,image/svg+xml,*/*;q=0.8",
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": "https://www.bayrol-poolaccess.de",
                "Referer": f"{self.BASE_URL}/m/login.php",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
            })

            async with self._session.post(login_url, headers=login_headers, data=form_data, allow_redirects=True) as response:
                content = await response.text()
                
                # Check if we're logged in by looking for typical error messages
                if "Fehler" in content or "Zeit abgelaufen" in content:
                    soup = BeautifulSoup(content, 'html.parser')
                    error = soup.find('div', class_='error_text')
                    if error:
                        error_text = error.text.strip()
                        _LOGGER.error("Login error: %s", error_text)
                    return False
                
                return True

        except Exception as err:
            _LOGGER.error("Error logging in to Bayrol Pool Access: %s", err, exc_info=True)
            return False

    async def get_controllers(self) -> list[dict[str, str]]:
        """Get list of controllers from plants page."""
        if not self._phpsessid:
            _LOGGER.error("No session ID available. Please login first.")
            return []

        url = f"{self.BASE_URL}/m/plants.php"
        headers = self._get_headers({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/png,image/svg+xml,*/*;q=0.8",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
        })

        try:
            async with self._session.get(url, headers=headers) as response:
                html = await response.text()
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

        except Exception as err:
            _LOGGER.error("Error getting controllers: %s", err, exc_info=True)
            return []

    async def get_data(self, cid: str) -> dict[str, Any]:
        """Get pool data for a specific controller."""
        if not self._phpsessid:
            _LOGGER.error("No session ID available. Please login first.")
            return {}

        try:
            url = f"{self.BASE_URL}/getdata.php?cid={cid}"
            headers = self._get_headers({
                "Accept": "*/*",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": f"{self.BASE_URL}/m/plants.php",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
            })

            async with self._session.get(url, headers=headers) as response:
                if response.status != 200:
                    _LOGGER.error("Data fetch failed with status: %s", response.status)
                    return {}
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Extract values from the HTML response
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

        except Exception as err:
            _LOGGER.error("Error getting pool data: %s", err, exc_info=True)
            return {}
