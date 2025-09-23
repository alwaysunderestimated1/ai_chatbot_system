from datetime import datetime, timezone
from typing import List, Optional, AsyncGenerator

from app.database.mongodb import get_db
from app.middleware.validation import validate_message, check_rate_limit
from app.models.chat import Message
from app.services import session_service, rag_service
from app.services.openai_service import (
    get_chat_completion,
    get_chat_completion_with_tools,
    stream_chat_completion,
)


async def _persist_messages(session_id: str, messages: List[Message]) -> None:
    db = get_db()
    await db.sessions.update_one(
        {"session_id": session_id},
        {
            "$set": {
                "messages": [m.model_dump() for m in messages],
                "updated_at": datetime.now(timezone.utc),
            },
            "$inc": {"message_count": 2},
        },
        upsert=True,
    )


async def chat(
    session_id: str,
    user_message: str,
    system_prompt: Optional[str],
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    use_rag: bool = False,
    use_tools: bool = False,
) -> tuple[str, List[Message], dict]:
    validate_message(user_message)
    check_rate_limit(session_id)

    session = await session_service.get_or_create_session(session_id, system_prompt)
    await session_service.set_title_from_first_message(session_id, user_message)

    effective_system_prompt = system_prompt or session.system_prompt

    if use_rag:
        context = await rag_service.build_rag_context(user_message)
        if context:
            effective_system_prompt = f"{effective_system_prompt}\n\n{context}"

    session.messages.append(Message(role="user", content=user_message))
    openai_messages = [{"role": m.role, "content": m.content} for m in session.messages]

    if use_tools:
        result = await get_chat_completion_with_tools(
            openai_messages, effective_system_prompt, temperature, max_tokens
        )
    else:
        result = await get_chat_completion(
            openai_messages, effective_system_prompt, temperature, max_tokens
        )

    session.messages.append(Message(role="assistant", content=result["content"]))
    await _persist_messages(session_id, session.messages)

    return result["content"], session.messages, result["usage"]


async def stream_chat(
    session_id: str,
    user_message: str,
    system_prompt: Optional[str],
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    use_rag: bool = False,
) -> AsyncGenerator[str, None]:
    validate_message(user_message)
    check_rate_limit(session_id)

    session = await session_service.get_or_create_session(session_id, system_prompt)
    await session_service.set_title_from_first_message(session_id, user_message)

    effective_system_prompt = system_prompt or session.system_prompt

    if use_rag:
        context = await rag_service.build_rag_context(user_message)
        if context:
            effective_system_prompt = f"{effective_system_prompt}\n\n{context}"

    session.messages.append(Message(role="user", content=user_message))
    openai_messages = [{"role": m.role, "content": m.content} for m in session.messages]
    full_reply: List[str] = []

    async def _generate():
        async for chunk in stream_chat_completion(
            openai_messages, effective_system_prompt, temperature, max_tokens
        ):
            full_reply.append(chunk)
            yield chunk

        session.messages.append(Message(role="assistant", content="".join(full_reply)))
        await _persist_messages(session_id, session.messages)

    return _generate()


async def get_history(session_id: str) -> List[Message]:
    session = await session_service.get_session(session_id)
    return session.messages
