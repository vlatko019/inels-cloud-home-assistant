"""Async API client for iNELS Cloud."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

import aiohttp

from .const import (
    API_BASE,
    COMMAND_PATH,
    DEVICES_PATH,
    LOGIN_PATH,
    ORIGIN,
    REFRESH_PATH,
)

_LOGGER = logging.getLogger(__name__)


class InelsCloudError(Exception):
    """Base iNELS Cloud error."""


class InelsCloudAuthError(InelsCloudError):
    """Authentication error."""


class InelsCloudClient:
    """Small client for the iNELS Cloud HTTP API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        access_token: str | None = None,
        refresh_token: str | None = None,
        username: str | None = None,
        password: str | None = None,
        token_update_callback: Callable[[str, str], Awaitable[None]] | None = None,
    ) -> None:
        self._session = session
        self.access_token = access_token
        self.refresh_token = refresh_token
        self._username = username
        self._password = password
        self._token_update_callback = token_update_callback
        self._expires_at = self._jwt_exp(access_token) if access_token else 0.0
        self._refresh_lock = asyncio.Lock()

    @staticmethod
    def _jwt_exp(token: str | None) -> float:
        """Read exp from a JWT without requiring a JWT package."""
        if not token:
            return 0.0
        try:
            payload = token.split(".")[1]
            payload += "=" * (-len(payload) % 4)
            data = json.loads(base64.urlsafe_b64decode(payload).decode())
            return float(data["exp"])
        except (ValueError, KeyError, IndexError, json.JSONDecodeError):
            return 0.0

    @property
    def token_expires_at(self) -> float:
        """Return access token expiry."""
        return self._expires_at

    @classmethod
    async def async_login(
        cls,
        session: aiohttp.ClientSession,
        username: str,
        password: str,
    ) -> dict[str, Any]:
        """Log in to iNELS Cloud."""
        async with session.post(
            f"{API_BASE}{LOGIN_PATH}",
            json={"username": username, "password": password, "origin": ORIGIN},
        ) as response:
            if response.status in (401, 403):
                raise InelsCloudAuthError("Invalid username or password")
            if response.status >= 400:
                raise InelsCloudError(
                    f"Login failed with HTTP {response.status}"
                )
            data = await response.json()
        if not data.get("access_token") or not data.get("refresh_token"):
            raise InelsCloudError("Login response did not contain tokens")
        return data

    async def _store_tokens(self, data: dict[str, Any]) -> None:
        """Update in-memory tokens and persist rotated credentials."""
        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        if not access_token or not refresh_token:
            raise InelsCloudError("Authentication response did not contain tokens")
        self.access_token = access_token
        self.refresh_token = refresh_token
        self._expires_at = self._jwt_exp(access_token)
        if self._token_update_callback:
            await self._token_update_callback(access_token, refresh_token)

    async def _async_login_and_update_tokens(self) -> None:
        """Fall back to a fresh login when refresh credentials are rejected."""
        if not self._username or not self._password:
            raise InelsCloudAuthError(
                "Refresh token rejected and no saved credentials are available"
            )
        data = await self.async_login(self._session, self._username, self._password)
        await self._store_tokens(data)

    async def _refresh(self) -> None:
        """Refresh tokens, falling back to a fresh login if refresh is rejected."""
        async with self._refresh_lock:
            if self.access_token and self._expires_at > time.time() + 60:
                return
            if not self.refresh_token:
                await self._async_login_and_update_tokens()
                return

            headers = {}
            if self.access_token:
                headers["Authorization"] = f"Bearer {self.access_token}"
            rejected = False
            async with self._session.post(
                f"{API_BASE}{REFRESH_PATH}",
                params={"refresh_token": self.refresh_token},
                headers=headers,
            ) as response:
                if response.status in (401, 403):
                    rejected = True
                elif response.status >= 400:
                    raise InelsCloudError(
                        f"Token refresh failed with HTTP {response.status}"
                    )
                else:
                    data = await response.json()

            if rejected:
                _LOGGER.warning(
                    "iNELS Cloud rejected the refresh token; trying a fresh login"
                )
                await self._async_login_and_update_tokens()
                return
            await self._store_tokens(data)

    async def ensure_token(self) -> str:
        """Return a valid access token."""
        if not self.access_token or self._expires_at <= time.time() + 60:
            await self._refresh()
        if not self.access_token:
            raise InelsCloudAuthError("No access token available")
        return self.access_token

    async def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> Any:
        """Make an authenticated HTTP request, refreshing once on 401."""
        token = await self.ensure_token()
        headers = dict(kwargs.pop("headers", {}))
        headers["Authorization"] = f"Bearer {token}"

        async with self._session.request(
            method, f"{API_BASE}{path}", headers=headers, **kwargs
        ) as response:
            if response.status == 401:
                self._expires_at = 0
                token = await self._refresh()
                headers["Authorization"] = f"Bearer {self.access_token}"
                async with self._session.request(
                    method, f"{API_BASE}{path}", headers=headers, **kwargs
                ) as retry:
                    if retry.status in (401, 403):
                        raise InelsCloudAuthError("Authentication rejected")
                    if retry.status >= 400:
                        raise InelsCloudError(
                            f"HTTP {retry.status} from {path}"
                        )
                    return await retry.json(content_type=None)

            if response.status >= 400:
                raise InelsCloudError(f"HTTP {response.status} from {path}")
            return await response.json(content_type=None)

    async def async_get_devices(self) -> dict[str, Any]:
        """Return all project devices."""
        return await self._request("GET", DEVICES_PATH)

    async def async_send_command(
        self,
        *,
        mac: str,
        tech: str,
        dev_id: int,
        dev_type: int,
        fce: str,
        value: int,
    ) -> Any:
        """Send a device command."""
        return await self._request(
            "POST",
            COMMAND_PATH,
            json={
                "mac": mac,
                "tech": tech,
                "fce": fce,
                "value": value,
                "dev_id": dev_id,
                "dev_type": dev_type,
            },
        )
