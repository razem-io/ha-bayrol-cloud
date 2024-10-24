"""Standalone API client for Bayrol Pool Access."""
import logging
import re
from typing import Any

import aiohttp
from bs4 import BeautifulSoup

# Set up logging
logging.basicConfig(level=logging.DEBUG)
_LOGGER = logging.getLogger(__name__)

class BayrolPoolAPI:
    """Bayrol Pool API client."""

    def __init__(self, session: aiohttp.ClientSession, username: str | None = None, password: str | None = None):
        """Initialize the API client."""
        self._session = session
        self._username = username
        self._password = password
        self._phpsessid = None

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
            init_url = "https://www.bayrol-poolaccess.de/webview/m/login.php"
            init_headers = {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:131.0) Gecko/20100101 Firefox/131.0",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/png,image/svg+xml,*/*;q=0.8",
                "Accept-Language": "de,en-US;q=0.7,en;q=0.3",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "TE": "trailers"
            }
            
            async with self._session.get(init_url, headers=init_headers) as response:
                html = await response.text()
                
                # Get all cookies from the response
                cookies = response.cookies
                _LOGGER.debug("Received cookies: %s", cookies)
                
                phpsessid = None
                for cookie in cookies.values():
                    if cookie.key == 'PHPSESSID':
                        phpsessid = cookie.value
                        break
                
                if not phpsessid:
                    _LOGGER.error("No PHPSESSID cookie received. Cookies: %s", cookies)
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
            login_url = "https://www.bayrol-poolaccess.de/webview/m/login.php?r=reg"
            headers = {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:131.0) Gecko/20100101 Firefox/131.0",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/png,image/svg+xml,*/*;q=0.8",
                "Accept-Language": "de,en-US;q=0.7,en;q=0.3",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": "https://www.bayrol-poolaccess.de",
                "Connection": "keep-alive",
                "Referer": "https://www.bayrol-poolaccess.de/webview/m/login.php",
                "Cookie": f"PHPSESSID={self._phpsessid}",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-User": "?1",
                "TE": "trailers"
            }

            async with self._session.post(login_url, headers=headers, data=form_data, allow_redirects=True) as response:
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

        url = "https://www.bayrol-poolaccess.de/webview/m/plants.php"
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:131.0) Gecko/20100101 Firefox/131.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/png,image/svg+xml,*/*;q=0.8",
            "Accept-Language": "de,en-US;q=0.7,en;q=0.3",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Connection": "keep-alive",
            "Cookie": f"PHPSESSID={self._phpsessid}",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
        }

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
            url = f"https://www.bayrol-poolaccess.de/webview/getdata.php?cid={cid}"
            headers = {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:131.0) Gecko/20100101 Firefox/131.0",
                "Accept": "*/*",
                "Accept-Language": "de,en-US;q=0.7,en;q=0.3",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "X-Requested-With": "XMLHttpRequest",
                "Connection": "keep-alive",
                "Referer": "https://www.bayrol-poolaccess.de/webview/m/plants.php",
                "Cookie": f"PHPSESSID={self._phpsessid}",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "TE": "trailers"
            }

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
