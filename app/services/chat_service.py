from typing import List, Optional, AsyncGenerator
from app.models.chat import Message
from app.services.openai_service import get_chat_completion, stream_chat_completion
from app.services import session_service


async def chat(
    session_id: str,
    user_message: str,
    system_prompt: Optional[str],
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> tuple[str, List[Message], dict]:
    session = await session_service.get_or_create_session(session_id, system_prompt)

    await session_service.set_title_from_first_message(session_id, user_message)

    session.messages.append(Message(role="user", content=user_message))
    openai_messages = [{"role": m.role, "content": m.content} for m in session.messages]
    result = await get_chat_completion(
        openai_messages,
        system_prompt or session.system_prompt,
        temperature,
        max_tokens,
    )

    session.messages.append(Message(role="assistant", content=result["content"]))

    from datetime import datetime, timezone
    from app.database.mongodb import get_db
    db = get_db()
    await db.sessions.update_one(
        {"session_id": session_id},
        {"$set": {
            "messages": [m.model_dump() for m in session.messages],
            "updated_at": datetime.now(timezone.utc),
        }, "$inc": {"message_count": 2}},
        upsert=True,
    )

    return result["content"], session.messages, result["usage"]


async def stream_chat(
    session_id: str,
    user_message: str,
    system_prompt: Optional[str],
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> AsyncGenerator[str, None]:
    session = await session_service.get_or_create_session(session_id, system_prompt)

    await session_service.set_title_from_first_message(session_id, user_message)

    session.messages.append(Message(role="user", content=user_message))
    openai_messages = [{"role": m.role, "content": m.content} for m in session.messages]
    full_reply = []

    async def _generate():
        async for chunk in stream_chat_completion(
            openai_messages,
            system_prompt or session.system_prompt,
            temperature,
            max_tokens,
        ):
            full_reply.append(chunk)
            yield chunk

        reply_text = "".join(full_reply)
        session.messages.append(Message(role="assistant", content=reply_text))

        from datetime import datetime, timezone
        from app.database.mongodb import get_db
        db = get_db()
        await db.sessions.update_one(
            {"session_id": session_id},
            {"$set": {
                "messages": [m.model_dump() for m in session.messages],
                "updated_at": datetime.now(timezone.utc),
            }, "$inc": {"message_count": 2}},
            upsert=True,
        )

    return _generate()


async def get_history(session_id: str) -> List[Message]:
    session = await session_service.get_session(session_id)
    return session.messages
