"""HTTP client for Bayrol Pool API."""
import logging
import re
from typing import Optional, Dict, Any

import aiohttp

from .constants import (
    BASE_URL,
    BASE_HEADERS,
    LOGIN_HEADERS,
    CONTROLLERS_HEADERS,
    DATA_HEADERS,
)
from .parser import (
    parse_login_form,
    check_login_error,
    parse_controllers,
    parse_pool_data,
)

_LOGGER = logging.getLogger(__name__)

class BayrolHttpClient:
    """HTTP client for Bayrol Pool API."""

    def __init__(self, session: aiohttp.ClientSession):
        """Initialize the HTTP client."""
        self._session = session
        self._phpsessid: Optional[str] = None
        _LOGGER.debug("BayrolHttpClient initialized with session: %s", id(session))

    def _get_headers(self, additional_headers: Dict[str, str] | None = None) -> Dict[str, str]:
        """Get headers with optional additions and session cookie if available."""
        headers = BASE_HEADERS.copy()
        
        if self._phpsessid:
            headers["Cookie"] = f"PHPSESSID={self._phpsessid}"
            
        if additional_headers:
            headers.update(additional_headers)
            
        _LOGGER.debug("Generated headers: %s", headers)
        return headers

    def _extract_phpsessid(self, response: aiohttp.ClientResponse) -> Optional[str]:
        """Extract PHPSESSID from response cookies or headers."""
        # Try to get PHPSESSID from cookies
        cookies = response.cookies
        for cookie in cookies.values():
            if cookie.key == 'PHPSESSID':
                return cookie.value

        # If no PHPSESSID in cookies, try to get it from Set-Cookie header
        if 'Set-Cookie' in response.headers:
            cookie_header = response.headers['Set-Cookie']
            _LOGGER.debug("Set-Cookie header: %s", cookie_header)
            match = re.search(r'PHPSESSID=([^;]+)', cookie_header)
            if match:
                return match.group(1)

        return None

    async def login(self, username: str, password: str) -> bool:
        """Login to Bayrol Pool Access."""
        try:
            # First get the login page and extract form data
            _LOGGER.debug("Initializing session...")
            init_url = f"{BASE_URL}/m/login.php"
            
            # Clear any existing cookies
            self._session.cookie_jar.clear()
            self._phpsessid = None
            
            init_headers = self._get_headers({
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/png,image/svg+xml,*/*;q=0.8",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
            })
            
            _LOGGER.debug("Making initial GET request to %s", init_url)
            async with self._session.get(init_url, headers=init_headers, allow_redirects=True) as response:
                _LOGGER.debug("Initial response status: %s", response.status)
                html = await response.text()
                
                phpsessid = self._extract_phpsessid(response)
                if not phpsessid:
                    _LOGGER.error("No PHPSESSID cookie received")
                    return False

                self._phpsessid = phpsessid
                _LOGGER.debug("Got session ID: %s", self._phpsessid)

                # Extract form data and add credentials
                form_data = parse_login_form(html)
                if not form_data:
                    return False
                
                form_data['username'] = username
                form_data['password'] = password

            # Try to login with the complete form data
            _LOGGER.debug("Attempting login POST request...")
            login_url = f"{BASE_URL}/m/login.php?r=reg"
            login_headers = self._get_headers(LOGIN_HEADERS)
            login_headers["Referer"] = f"{BASE_URL}/m/login.php"

            async with self._session.post(login_url, headers=login_headers, data=form_data, allow_redirects=True) as response:
                _LOGGER.debug("Login response status: %s", response.status)
                content = await response.text()
                
                if check_login_error(content):
                    return False
                
                _LOGGER.debug("Login successful")
                return True

        except Exception as err:
            _LOGGER.error("Error logging in to Bayrol Pool Access: %s", err, exc_info=True)
            return False

    async def get_controllers(self) -> list[dict[str, str]]:
        """Get list of controllers from plants page."""
        if not self._phpsessid:
            _LOGGER.error("No session ID available. Please login first.")
            return []

        url = f"{BASE_URL}/m/plants.php"
        headers = self._get_headers(CONTROLLERS_HEADERS)

        try:
            _LOGGER.debug("Getting controllers from %s", url)
            async with self._session.get(url, headers=headers) as response:
                _LOGGER.debug("Get controllers response status: %s", response.status)
                html = await response.text()
                return parse_controllers(html)

        except Exception as err:
            _LOGGER.error("Error getting controllers: %s", err, exc_info=True)
            return []

    async def get_data(self, cid: str) -> Dict[str, Any]:
        """Get pool data for a specific controller."""
        if not self._phpsessid:
            _LOGGER.error("No session ID available. Please login first.")
            return {}

        try:
            url = f"{BASE_URL}/getdata.php?cid={cid}"
            headers = self._get_headers(DATA_HEADERS)
            headers["Referer"] = f"{BASE_URL}/m/plants.php"

            _LOGGER.debug("Getting data from %s", url)
            async with self._session.get(url, headers=headers) as response:
                _LOGGER.debug("Get data response status: %s", response.status)
                
                if response.status != 200:
                    _LOGGER.error("Data fetch failed with status: %s", response.status)
                    return {}
                
                html = await response.text()
                return parse_pool_data(html)

        except Exception as err:
            _LOGGER.error("Error getting pool data: %s", err, exc_info=True)
            return {}
