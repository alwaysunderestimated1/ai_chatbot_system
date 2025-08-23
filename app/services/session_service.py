from datetime import datetime, timezone
from typing import Optional
from app.database.mongodb import get_db
from app.models.chat import Session, SessionSummary, SessionListResponse


def _make_title(first_message: str) -> str:
    title = first_message.strip().replace("\n", " ")
    return title[:60] + "…" if len(title) > 60 else title


async def get_session(session_id: str) -> Session:
    db = get_db()
    doc = await db.sessions.find_one({"session_id": session_id})
    if not doc:
        raise KeyError(f"Session '{session_id}' not found.")
    return Session(**doc)


async def get_or_create_session(session_id: str, system_prompt: Optional[str] = None) -> Session:
    db = get_db()
    doc = await db.sessions.find_one({"session_id": session_id})
    if doc:
        return Session(**doc)
    session = Session(
        session_id=session_id,
        system_prompt=system_prompt or "You are a helpful assistant.",
    )
    await db.sessions.insert_one(session.model_dump())
    return session


async def set_title_from_first_message(session_id: str, message: str) -> None:
    db = get_db()
    await db.sessions.update_one(
        {"session_id": session_id, "message_count": 0},
        {"$set": {"title": _make_title(message)}},
    )


async def increment_message_count(session_id: str, by: int = 2) -> None:
    db = get_db()
    await db.sessions.update_one(
        {"session_id": session_id},
        {"$inc": {"message_count": by}, "$set": {"updated_at": datetime.now(timezone.utc)}},
    )


async def list_sessions(page: int = 1, page_size: int = 20) -> SessionListResponse:
    db = get_db()
    skip = (page - 1) * page_size
    total = await db.sessions.count_documents({})
    cursor = db.sessions.find(
        {},
        {"session_id": 1, "title": 1, "message_count": 1, "created_at": 1, "updated_at": 1},
    ).sort("updated_at", -1).skip(skip).limit(page_size)
    docs = await cursor.to_list(length=page_size)
    sessions = [SessionSummary(**doc) for doc in docs]
    return SessionListResponse(sessions=sessions, total=total, page=page, page_size=page_size)


async def update_session(session_id: str, title: Optional[str], system_prompt: Optional[str]) -> Session:
    db = get_db()
    updates: dict = {"updated_at": datetime.now(timezone.utc)}
    if title is not None:
        updates["title"] = title
    if system_prompt is not None:
        updates["system_prompt"] = system_prompt
    result = await db.sessions.find_one_and_update(
        {"session_id": session_id},
        {"$set": updates},
        return_document=True,
    )
    if not result:
        raise KeyError(f"Session '{session_id}' not found.")
    return Session(**result)


async def delete_session(session_id: str) -> None:
    db = get_db()
    result = await db.sessions.delete_one({"session_id": session_id})
    if result.deleted_count == 0:
        raise KeyError(f"Session '{session_id}' not found.")
