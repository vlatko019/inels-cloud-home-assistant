"""iNELS Cloud WebSocket client."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

import aiohttp

from .const import WEBSOCKET_URL

_LOGGER = logging.getLogger(__name__)


class InelsCloudWebSocket:
    """Maintain the iNELS Cloud push connection."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        token_getter: Callable[[], Awaitable[str]],
        event_callback: Callable[[dict[str, Any]], Awaitable[None]],
    ) -> None:
        self._session = session
        self._token_getter = token_getter
        self._event_callback = event_callback
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()

    async def async_start(self) -> None:
        """Start the reconnecting WebSocket task."""
        self._stop.clear()
        self._task = asyncio.create_task(
            self._run(), name="inels-cloud-websocket"
        )

    async def async_stop(self) -> None:
        """Stop the WebSocket task."""
        self._stop.set()
        if self._task:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None

    async def _run(self) -> None:
        """Connect, authenticate and receive events."""
        delay = 2
        while not self._stop.is_set():
            try:
                token = await self._token_getter()
                async with self._session.ws_connect(
                    WEBSOCKET_URL,
                    heartbeat=30,
                    receive_timeout=90,
                ) as ws:
                    await ws.send_json(
                        {"service": "jwt_auth", "jwt": token}
                    )
                    _LOGGER.debug("iNELS Cloud WebSocket connected")
                    delay = 2

                    async for message in ws:
                        if message.type == aiohttp.WSMsgType.TEXT:
                            try:
                                payload = json.loads(message.data)
                            except json.JSONDecodeError:
                                _LOGGER.debug(
                                    "Ignoring non-JSON WebSocket message"
                                )
                                continue
                            if isinstance(payload, dict):
                                await self._event_callback(payload)
                        elif message.type in (
                            aiohttp.WSMsgType.ERROR,
                            aiohttp.WSMsgType.CLOSED,
                        ):
                            break
            except asyncio.CancelledError:
                raise
            except Exception as err:
                _LOGGER.warning(
                    "iNELS Cloud WebSocket disconnected: %s; retrying",
                    err,
                )

            if not self._stop.is_set():
                await asyncio.sleep(delay)
                delay = min(delay * 2, 60)
