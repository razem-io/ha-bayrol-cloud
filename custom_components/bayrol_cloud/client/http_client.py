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
    JSON_HEADERS,
)
from .parser import (
    parse_login_form,
    check_login_error,
    parse_controllers,
    parse_pool_data,
    parse_overview_page,
)
from ..helpers import conditional_log

_LOGGER = logging.getLogger(__name__)

class BayrolHttpClient:
    """HTTP client for Bayrol Pool API."""

    def __init__(self, session: aiohttp.ClientSession):
        """Initialize the HTTP client."""
        self._session = session
        self._phpsessid: Optional[str] = None
        self._debug_mode = False
        self._last_raw_html = None
        conditional_log(_LOGGER, logging.DEBUG, "BayrolHttpClient initialized with session: %s", id(session), debug_mode=self._debug_mode)

    @property
    def debug_mode(self) -> bool:
        """Get debug mode status."""
        return self._debug_mode

    @debug_mode.setter
    def debug_mode(self, value: bool) -> None:
        """Set debug mode status."""
        self._debug_mode = value
        if not value:
            self._last_raw_html = None

    @property
    def last_raw_html(self) -> Optional[str]:
        """Get last raw HTML if debug mode is enabled."""
        return self._last_raw_html if self._debug_mode else None

    def _get_headers(self, additional_headers: Dict[str, str] | None = None) -> Dict[str, str]:
        """Get headers with optional additions and session cookie if available."""
        headers = BASE_HEADERS.copy()
        
        if self._phpsessid:
            headers["Cookie"] = f"PHPSESSID={self._phpsessid}"
            
        if additional_headers:
            headers.update(additional_headers)
            
        conditional_log(_LOGGER, logging.DEBUG, "Generated headers: %s", headers, debug_mode=self._debug_mode)
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
            conditional_log(_LOGGER, logging.DEBUG, "Set-Cookie header: %s", cookie_header, debug_mode=self._debug_mode)
            match = re.search(r'PHPSESSID=([^;]+)', cookie_header)
            if match:
                return match.group(1)

        return None

    async def login(self, username: str, password: str) -> bool:
        """Login to Bayrol Pool Access."""
        try:
            # First get the login page and extract form data
            conditional_log(_LOGGER, logging.DEBUG, "Initializing session...", debug_mode=self._debug_mode)
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
            
            conditional_log(_LOGGER, logging.DEBUG, "Making initial GET request to %s", init_url, debug_mode=self._debug_mode)
            async with self._session.get(init_url, headers=init_headers, allow_redirects=True) as response:
                conditional_log(_LOGGER, logging.DEBUG, "Initial response status: %s", response.status, debug_mode=self._debug_mode)
                html = await response.text()
                
                phpsessid = self._extract_phpsessid(response)
                if not phpsessid:
                    _LOGGER.error("No PHPSESSID cookie received")
                    return False

                self._phpsessid = phpsessid
                conditional_log(_LOGGER, logging.DEBUG, "Got session ID: %s", self._phpsessid, debug_mode=self._debug_mode)

                # Extract form data and add credentials
                form_data = parse_login_form(html)
                if not form_data:
                    return False
                
                form_data['username'] = username
                form_data['password'] = password

            # Try to login with the complete form data
            conditional_log(_LOGGER, logging.DEBUG, "Attempting login POST request...", debug_mode=self._debug_mode)
            login_url = f"{BASE_URL}/m/login.php?r=reg"
            login_headers = self._get_headers(LOGIN_HEADERS)
            login_headers["Referer"] = f"{BASE_URL}/m/login.php"

            async with self._session.post(login_url, headers=login_headers, data=form_data, allow_redirects=True) as response:
                conditional_log(_LOGGER, logging.DEBUG, "Login response status: %s", response.status, debug_mode=self._debug_mode)
                content = await response.text()
                
                if check_login_error(content):
                    return False
                
                conditional_log(_LOGGER, logging.DEBUG, "Login successful", debug_mode=self._debug_mode)
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
            conditional_log(_LOGGER, logging.DEBUG, "Getting controllers from %s", url, debug_mode=self._debug_mode)
            async with self._session.get(url, headers=headers) as response:
                conditional_log(_LOGGER, logging.DEBUG, "Get controllers response status: %s", response.status, debug_mode=self._debug_mode)
                html = await response.text()
                if self._debug_mode:
                    self._last_raw_html = html
                return parse_controllers(html)

        except Exception as err:
            _LOGGER.error("Error getting controllers: %s", err, exc_info=True)
            return []

    async def get_device_status(self, cid: str) -> str:
        """Get device status page HTML for a specific controller."""
        if not self._phpsessid:
            _LOGGER.error("No session ID available. Please login first.")
            return ""

        try:
            url = f"{BASE_URL}/p/device.php?c={cid}"
            headers = self._get_headers()
            headers["Referer"] = f"{BASE_URL}/m/plants.php"

            conditional_log(_LOGGER, logging.DEBUG, "Getting device status from %s", url, debug_mode=self._debug_mode)
            async with self._session.get(url, headers=headers) as response:
                conditional_log(_LOGGER, logging.DEBUG, "Get device status response status: %s", response.status, debug_mode=self._debug_mode)
                
                if response.status != 200:
                    _LOGGER.error("Device status fetch failed with status: %s", response.status)
                    response_headers = dict(response.headers)
                    conditional_log(_LOGGER, logging.DEBUG, "Response headers: %s", response_headers, debug_mode=self._debug_mode)
                    
                    # Try to get some response content even on error
                    try:
                        error_content = await response.text()
                        error_preview = error_content[:200] + "..." if len(error_content) > 200 else error_content
                        conditional_log(_LOGGER, logging.DEBUG, "Error response content preview: %s", error_preview, debug_mode=self._debug_mode)
                    except Exception as read_err:
                        conditional_log(_LOGGER, logging.DEBUG, "Could not read error response content: %s", read_err, debug_mode=self._debug_mode)
                    
                    return ""
                
                html = await response.text()
                
                # Add detailed logging
                content_length = len(html)
                conditional_log(_LOGGER, logging.DEBUG, "Device status response content length: %d bytes", content_length, debug_mode=self._debug_mode)
                
                if content_length == 0:
                    _LOGGER.warning("Empty device status response received")
                    return ""
                    
                if content_length < 200:
                    # If very small, log the entire content
                    conditional_log(_LOGGER, logging.DEBUG, "Small device status response: %s", html, debug_mode=self._debug_mode)
                else:
                    # Log a preview of the content
                    conditional_log(_LOGGER, logging.DEBUG, "Device status response preview: %s...", html[:200], debug_mode=self._debug_mode)
                    
                    # Check for key HTML elements to help diagnose problems
                    has_html_tag = "<html" in html.lower()
                    has_body_tag = "<body" in html.lower()
                    has_tab_class = "tab_" in html
                    has_device_divs = 'class="i_x16"' in html
                    has_i_item_divs = 'class="i_item"' in html
                    
                    conditional_log(_LOGGER, logging.DEBUG,
                        "HTML structure check: html_tag=%s, body_tag=%s, tab_class=%s, device_divs=%s, i_item_divs=%s",
                        has_html_tag, has_body_tag, has_tab_class, has_device_divs, has_i_item_divs,
                        debug_mode=self._debug_mode
                    )
                
                if self._debug_mode:
                    self._last_raw_html = html
                return html

        except Exception as err:
            _LOGGER.error("Error getting device status: %s", err, exc_info=True)
            return ""

    async def get_overview_data(self) -> Dict[str, Dict[str, Any]]:
        """Get data for all controllers from the overview page.
        
        This is used as a fallback when direct access to a controller fails or requires authentication.
        """
        if not self._phpsessid:
            _LOGGER.error("No session ID available. Please login first.")
            return {}

        try:
            url = f"{BASE_URL}/p/plants.php"
            headers = self._get_headers(CONTROLLERS_HEADERS)

            conditional_log(_LOGGER, logging.DEBUG, "Getting overview data from %s", url, debug_mode=self._debug_mode)
            async with self._session.get(url, headers=headers) as response:
                conditional_log(_LOGGER, logging.DEBUG, "Get overview data response status: %s", response.status, debug_mode=self._debug_mode)
                
                if response.status != 200:
                    _LOGGER.error("Overview data fetch failed with status: %s", response.status)
                    return {}
                
                html = await response.text()
                if self._debug_mode:
                    self._last_raw_html = html
                    
                return parse_overview_page(html, debug=self._debug_mode)

        except Exception as err:
            _LOGGER.error("Error getting overview data: %s", err, exc_info=True)
            return {}

    async def get_data(self, cid: str) -> Dict[str, Any]:
        """Get pool data for a specific controller.
        
        First attempts to get data directly from the controller. If that fails or requires
        authentication, falls back to getting data from the overview page.
        """
        if not self._phpsessid:
            _LOGGER.error("No session ID available. Please login first.")
            return {}

        try:
            # First try to get data directly from the controller
            url = f"{BASE_URL}/getdata.php?cid={cid}"
            headers = self._get_headers(DATA_HEADERS)
            headers["Referer"] = f"{BASE_URL}/m/plants.php"

            conditional_log(_LOGGER, logging.DEBUG, "Getting data from %s", url, debug_mode=self._debug_mode)
            async with self._session.get(url, headers=headers) as response:
                conditional_log(_LOGGER, logging.DEBUG, "Get data response status: %s", response.status, debug_mode=self._debug_mode)
                
                if response.status != 200:
                    _LOGGER.warning("Direct data fetch failed with status: %s, falling back to overview page", response.status)
                    # Fall back to getting data from the overview page
                    overview_data = await self.get_overview_data()
                    return overview_data.get(cid, {})
                
                html = await response.text()
                if self._debug_mode:
                    self._last_raw_html = html
                
                # Try to parse the data directly
                data = parse_pool_data(html)
                
                # If parsing fails or data is empty, try falling back to the overview page
                if not data or (len(data) == 1 and "status" in data and data["status"] == "offline"):
                    conditional_log(_LOGGER, logging.DEBUG, "Direct data fetch succeeded but parsing failed, falling back to overview page", debug_mode=self._debug_mode)
                    overview_data = await self.get_overview_data()
                    if cid in overview_data:
                        return overview_data[cid]
                
                return data

        except Exception as err:
            _LOGGER.error("Error getting pool data: %s", err, exc_info=True)
            # Try fallback as a last resort
            try:
                overview_data = await self.get_overview_data()
                return overview_data.get(cid, {})
            except Exception as fallback_err:
                _LOGGER.error("Fallback to overview page also failed: %s", fallback_err, exc_info=True)
                return {}

    async def set_controller_password(self, cid: str, password: str) -> bool:
        """Set the controller password."""
        if not self._phpsessid:
            _LOGGER.error("No session ID available. Please login first.")
            return False

        try:
            url = f"{BASE_URL}/data_json.php"
            headers = self._get_headers(JSON_HEADERS)
            headers["Referer"] = f"{BASE_URL}/p/device.php?c={cid}"

            data = {
                "device": cid,
                "action": "setCode",
                "data": {
                    "code": password
                }
            }

            conditional_log(_LOGGER, logging.DEBUG, "Setting controller password...", debug_mode=self._debug_mode)
            async with self._session.post(url, headers=headers, json=data) as response:
                if response.status != 200:
                    _LOGGER.error("Failed to set controller password: %s", response.status)
                    return False

                response_text = await response.text()
                return '"error":""' in response_text

        except Exception as err:
            _LOGGER.error("Error setting controller password: %s", err, exc_info=True)
            return False

    async def get_controller_access(self, cid: str, password: str) -> bool:
        """Get access to controller settings using password."""
        if not self._phpsessid:
            _LOGGER.error("No session ID available. Please login first.")
            return False

        try:
            # First get the main device page
            conditional_log(_LOGGER, logging.DEBUG, "Accessing main device page...", debug_mode=self._debug_mode)
            main_url = f"{BASE_URL}/p/device.php?c={cid}"
            headers = self._get_headers()
            headers["Referer"] = f"{BASE_URL}/m/plants.php"
            
            async with self._session.get(main_url, headers=headers) as response:
                if response.status != 200:
                    _LOGGER.error("Failed to access main device page: %s", response.status)
                    return False
                
                conditional_log(_LOGGER, logging.DEBUG, "Successfully accessed main device page", debug_mode=self._debug_mode)

            # Now submit the device password
            url = f"{BASE_URL}/data_json.php"
            headers = self._get_headers(JSON_HEADERS)
            headers["Referer"] = main_url

            # First set the code
            set_code_data = {
                "device": cid,
                "action": "setCode",
                "data": {
                    "code": password
                }
            }

            conditional_log(_LOGGER, logging.DEBUG, "Setting controller password...", debug_mode=self._debug_mode)
            async with self._session.post(url, headers=headers, json=set_code_data) as response:
                if response.status != 200:
                    _LOGGER.error("Failed to set controller password: %s", response.status)
                    return False

                response_text = await response.text()
                if '"error":""' not in response_text:
                    _LOGGER.error("Failed to set controller password")
                    return False

                conditional_log(_LOGGER, logging.DEBUG, "Successfully set controller password", debug_mode=self._debug_mode)

            # Then get access
            get_access_data = {
                "device": cid,
                "action": "getAccess",
                "data": {
                    "code": password
                }
            }

            conditional_log(_LOGGER, logging.DEBUG, "Getting controller access...", debug_mode=self._debug_mode)
            async with self._session.post(url, headers=headers, json=get_access_data) as response:
                if response.status != 200:
                    _LOGGER.error("Failed to get controller access: %s", response.status)
                    return False

                response_text = await response.text()
                if '"data":{"access":true}' not in response_text:
                    _LOGGER.error("Controller password not accepted")
                    return False

                conditional_log(_LOGGER, logging.DEBUG, "Controller access granted", debug_mode=self._debug_mode)
                return True

        except Exception as err:
            _LOGGER.error("Error getting controller access: %s", err, exc_info=True)
            return False

    async def set_items(self, cid: str, items: list[dict]) -> bool:
        """Set controller items (settings)."""
        if not self._phpsessid:
            _LOGGER.error("No session ID available. Please login first.")
            return False

        try:
            url = f"{BASE_URL}/data_json.php"
            headers = self._get_headers(JSON_HEADERS)
            headers["Referer"] = f"{BASE_URL}/p/device.php?c={cid}"

            data = {
                "device": cid,
                "action": "setItems",
                "data": {
                    "items": items
                }
            }

            conditional_log(_LOGGER, logging.DEBUG, "Setting items: %s", items, debug_mode=self._debug_mode)
            async with self._session.post(url, headers=headers, json=data) as response:
                if response.status != 200:
                    _LOGGER.error("Failed to set items: %s", response.status)
                    return False

                response_text = await response.text()
                return '"error":""' in response_text

        except Exception as err:
            _LOGGER.error("Error setting items: %s", err, exc_info=True)
            return False
