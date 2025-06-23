from openai import AsyncOpenAI
from typing import List
from app.config import settings

_client = AsyncOpenAI(api_key=settings.openai_api_key)


async def get_chat_completion(messages: List[dict], system_prompt: str) -> str:
    full_messages = [{"role": "system", "content": system_prompt}] + messages
    response = await _client.chat.completions.create(
        model=settings.openai_model,
        messages=full_messages,
    )
    return response.choices[0].message.content
