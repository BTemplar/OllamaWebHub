import json
from typing import Any


def format_sse(event: str, data: dict[str, Any]) -> str:
    """
    Format a Server-Sent Events payload line.

    Args:
        event (str): SSE event name.
        data (dict[str, Any]): JSON-serializable event payload.

    Returns:
        str: Formatted SSE message block.
    """
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
