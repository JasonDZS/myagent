"""Outbound message channels for per-connection single-writer sending.

This module provides a small abstraction that ensures all messages for a
single WebSocket connection are sent by exactly one writer coroutine. It
prevents concurrent websocket.send() calls and offers a natural place to
add backpressure policies later (queue limits, coalescing, etc.).
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from websockets.server import WebSocketServerProtocol

from .utils import is_websocket_closed
from myagent.logger import logger


class OutboundChannel:
    """Per-connection outbound channel with a single writer task."""

    def __init__(
        self,
        websocket: WebSocketServerProtocol,
        *,
        maxsize: int = 1000,
        coalesce_window_ms: int = 75,
        coalesce_events: set[str] | None = None,
        name: str | None = None,
    ) -> None:
        self.websocket = websocket
        self.queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=maxsize)
        self._writer_task: asyncio.Task | None = None
        self._closed = False
        self.name = name or "outbound"
        self._coalesce_window = max(0, int(coalesce_window_ms)) / 1000.0
        self._coalesce_events = coalesce_events or {"agent.partial_answer", "agent.llm_message"}
        self._coalesce_buffers: dict[tuple[str, str], dict[str, Any]] = {}
        self._coalesce_task: asyncio.Task | None = None

    def start(self) -> None:
        if self._writer_task is None or self._writer_task.done():
            self._writer_task = asyncio.create_task(self._writer(), name=f"{self.name}-writer")

    async def enqueue(self, event: dict[str, Any]) -> None:
        """Enqueue an event for sending.

        This call will await when the queue is full, applying natural
        backpressure to producers. This avoids unbounded memory growth and
        prevents concurrent websocket.send().
        """
        if self._closed:
            return
        try:
            # Optional coalescing for high-frequency partial events
            evt_type = str(event.get("event", ""))
            session_id = str(event.get("session_id", ""))
            if self._coalesce_window > 0 and evt_type in self._coalesce_events and session_id:
                key = (evt_type, session_id)
                self._coalesce_buffers[key] = event
                if self._coalesce_task is None or self._coalesce_task.done():
                    self._coalesce_task = asyncio.create_task(self._flush_coalesced_after_delay())
                return

            await self.queue.put(event)
        except Exception as e:
            logger.debug(f"Failed to enqueue outbound event: {e}")

    async def close(self) -> None:
        self._closed = True
        # Cancel writer task
        if self._writer_task is not None:
            self._writer_task.cancel()
            try:
                await self._writer_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.debug(f"Error awaiting writer task close: {e}")
        # Cancel coalescer and drain buffers
        if self._coalesce_task is not None:
            self._coalesce_task.cancel()
            try:
                await self._coalesce_task
            except asyncio.CancelledError:
                pass
        self._coalesce_buffers.clear()
        # Drain queue best-effort
        try:
            while not self.queue.empty():
                self.queue.get_nowait()
                self.queue.task_done()
        except Exception:
            pass

    async def _writer(self) -> None:
        """Single writer that sends all events on this connection."""
        try:
            while not self._closed:
                event = await self.queue.get()
                try:
                    if is_websocket_closed(self.websocket):
                        logger.debug("WebSocket closed; dropping outbound event")
                    else:
                        await self.websocket.send(json.dumps(event))
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    # Log and continue; upstream may decide to close the connection later
                    logger.error(f"Outbound send failed: {e}")
                finally:
                    try:
                        self.queue.task_done()
                    except Exception:
                        pass
        except asyncio.CancelledError:
            # Normal shutdown path
            pass
        except Exception as e:
            logger.debug(f"Outbound writer stopped with error: {e}")

    async def _flush_coalesced_after_delay(self) -> None:
        try:
            await asyncio.sleep(self._coalesce_window)
            if self._closed:
                return
            # Move buffered latest partials to the queue
            to_flush = list(self._coalesce_buffers.values())
            self._coalesce_buffers.clear()
            for ev in to_flush:
                try:
                    await self.queue.put(ev)
                except Exception as e:
                    logger.debug(f"Failed to flush coalesced event: {e}")
        except asyncio.CancelledError:
            pass
        finally:
            self._coalesce_task = None
