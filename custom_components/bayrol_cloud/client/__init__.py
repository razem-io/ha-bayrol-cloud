"""Bayrol Pool API client package."""
import logging
from typing import Any, Dict, Optional

import aiohttp

from .http_client import BayrolHttpClient

_LOGGER = logging.getLogger(__name__)

class BayrolPoolAPI:
    """Bayrol Pool API client."""

    def __init__(self, session: aiohttp.ClientSession, username: str | None = None, password: str | None = None):
        """Initialize the API client."""
        self._username = username
        self._password = password
        self._client = BayrolHttpClient(session)

    async def login(self, username: str | None = None, password: str | None = None) -> bool:
        """Login to Bayrol Pool Access."""
        if username:
            self._username = username
        if password:
            self._password = password

        if not self._username or not self._password:
            _LOGGER.error("Username and password are required")
            return False

        return await self._client.login(self._username, self._password)

    async def get_controllers(self) -> list[dict[str, str]]:
        """Get list of controllers from plants page."""
        return await self._client.get_controllers()

    async def get_data(self, cid: str) -> Dict[str, Any]:
        """Get pool data for a specific controller."""
        return await self._client.get_data(cid)
