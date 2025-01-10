"""API client for Bayrol Pool Controller."""
from typing import Dict, Any
import re

import aiohttp

from .http_client import BayrolHttpClient
from .device_parser import parse_device_status

class BayrolPoolAPI:
    """API client for Bayrol Pool Controller."""

    def __init__(self, session: aiohttp.ClientSession):
        """Initialize the API client."""
        self._client = BayrolHttpClient(session)

    @property
    def debug_mode(self) -> bool:
        """Get debug mode status."""
        return self._client.debug_mode

    @debug_mode.setter
    def debug_mode(self, value: bool) -> None:
        """Set debug mode status."""
        self._client.debug_mode = value

    @property
    def last_raw_html(self) -> str | None:
        """Get last raw HTML if debug mode is enabled."""
        raw_html = self._client.last_raw_html
        if raw_html:
            # Replace CIDs in URLs and onclick handlers
            raw_html = re.sub(r'(?:device\.php\?c=|c=)(\d+)', r'device.php?c=XXXXX', raw_html)
        return raw_html

    async def login(self, username: str, password: str) -> bool:
        """Login to Bayrol Pool Access."""
        return await self._client.login(username, password)

    async def get_controllers(self) -> list[dict[str, str]]:
        """Get list of controllers."""
        return await self._client.get_controllers()

    async def get_device_status(self, cid: str, raw: bool = False) -> Dict[str, Any] | str:
        """Get device status for a specific controller.
        
        Args:
            cid: Controller ID
            raw: If True, returns raw HTML instead of parsed data
        
        Returns:
            Dict of parsed status data, or raw HTML if raw=True
        """
        html = await self._client.get_device_status(cid)
        if raw:
            return html
        return parse_device_status(html)

    async def get_data(self, cid: str) -> Dict[str, Any]:
        """Get pool data for a specific controller."""
        data = await self._client.get_data(cid)
        if self.debug_mode:
            data["debug_raw_html"] = self.last_raw_html
        return data

    async def set_controller_password(self, cid: str, password: str) -> bool:
        """Set the controller password.
        
        Args:
            cid: Controller ID
            password: Password to set for controller settings access
            
        Returns:
            True if password was set successfully, False otherwise
        """
        return await self._client.set_controller_password(cid, password)

    async def get_controller_access(self, cid: str, password: str) -> bool:
        """Get access to controller settings using password.
        
        Args:
            cid: Controller ID
            password: Password to use for controller settings access
            
        Returns:
            True if access was granted, False otherwise
        """
        return await self._client.get_controller_access(cid, password)

    async def set_items(self, cid: str, items: list[dict]) -> bool:
        """Set controller items (settings).
        
        Args:
            cid: Controller ID
            items: List of items to set, each item being a dict with:
                  - topic: The item topic (e.g. "3.153" for alarm relay mode)
                  - name: Item name
                  - value: List of values (e.g. [1, 0] for on/off)
                  - valid: Validation flag (usually 1)
                  - cmd: Command flag (usually 0)
            
        Returns:
            True if items were set successfully, False otherwise
        """
        return await self._client.set_items(cid, items)
