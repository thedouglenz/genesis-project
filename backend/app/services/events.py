import asyncio
import json
from collections.abc import AsyncGenerator

_event_bus: dict[str, asyncio.Queue] = {}


async def emit(conversation_id: str, data: dict) -> None:
    """Put an event on the conversation's queue, creating it if needed."""
    if conversation_id not in _event_bus:
        _event_bus[conversation_id] = asyncio.Queue()
    await _event_bus[conversation_id].put(data)


async def subscribe(conversation_id: str, timeout: float = 300.0) -> AsyncGenerator[str, None]:
    """Yield SSE-formatted events from the conversation queue."""
    if conversation_id not in _event_bus:
        _event_bus[conversation_id] = asyncio.Queue()
    queue = _event_bus[conversation_id]

    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=timeout)
            except asyncio.TimeoutError:
                break
            yield json.dumps(event)
            if event.get("step") == "done":
                break
    finally:
        cleanup(conversation_id)


def cleanup(conversation_id: str) -> None:
    """Remove the conversation's queue."""
    _event_bus.pop(conversation_id, None)
