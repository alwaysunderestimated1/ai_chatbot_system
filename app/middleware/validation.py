import time
from fastapi import HTTPException

MAX_MESSAGE_LENGTH = 4000
_rate_store: dict[str, list[float]] = {}


def validate_message(message: str) -> None:
    if not message or not message.strip():
        raise HTTPException(status_code=422, detail="Message cannot be empty.")
    if len(message) > MAX_MESSAGE_LENGTH:
        raise HTTPException(
            status_code=422,
            detail=f"Message too long. Maximum {MAX_MESSAGE_LENGTH} characters allowed.",
        )


def check_rate_limit(session_id: str, max_requests: int = 20, window_seconds: int = 60) -> None:
    now = time.time()
    cutoff = now - window_seconds
    timestamps = [t for t in _rate_store.get(session_id, []) if t > cutoff]
    if len(timestamps) >= max_requests:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Max {max_requests} messages per {window_seconds}s per session.",
        )
    timestamps.append(now)
    _rate_store[session_id] = timestamps
