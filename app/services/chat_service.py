from datetime import datetime, timezone
from typing import List, Optional, AsyncGenerator
from app.database.mongodb import get_db
from app.models.chat import Message, Session
from app.services.openai_service import get_chat_completion, stream_chat_completion


async def get_or_create_session(session_id: str) -> Session:
    db = get_db()
    doc = await db.sessions.find_one({"session_id": session_id})
    if doc:
        return Session(**doc)
    session = Session(session_id=session_id)
    await db.sessions.insert_one(session.model_dump())
    return session


async def chat(
    session_id: str,
    user_message: str,
    system_prompt: str,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> tuple[str, List[Message], dict]:
    session = await get_or_create_session(session_id)
    session.messages.append(Message(role="user", content=user_message))

    openai_messages = [{"role": m.role, "content": m.content} for m in session.messages]
    result = await get_chat_completion(openai_messages, system_prompt, temperature, max_tokens)

    session.messages.append(Message(role="assistant", content=result["content"]))
    session.updated_at = datetime.now(timezone.utc)

    db = get_db()
    await db.sessions.update_one(
        {"session_id": session_id},
        {"$set": {"messages": [m.model_dump() for m in session.messages], "updated_at": session.updated_at}},
        upsert=True,
    )

    return result["content"], session.messages, result["usage"]


async def stream_chat(
    session_id: str,
    user_message: str,
    system_prompt: str,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> AsyncGenerator[str, None]:
    session = await get_or_create_session(session_id)
    session.messages.append(Message(role="user", content=user_message))

    openai_messages = [{"role": m.role, "content": m.content} for m in session.messages]
    full_reply = []

    async def _generate():
        async for chunk in stream_chat_completion(openai_messages, system_prompt, temperature, max_tokens):
            full_reply.append(chunk)
            yield chunk

        reply_text = "".join(full_reply)
        session.messages.append(Message(role="assistant", content=reply_text))
        session.updated_at = datetime.now(timezone.utc)
        db = get_db()
        await db.sessions.update_one(
            {"session_id": session_id},
            {"$set": {"messages": [m.model_dump() for m in session.messages], "updated_at": session.updated_at}},
            upsert=True,
        )

    return _generate()


async def get_history(session_id: str) -> List[Message]:
    session = await get_or_create_session(session_id)
    return session.messages


async def clear_session(session_id: str) -> None:
    db = get_db()
    await db.sessions.delete_one({"session_id": session_id})
