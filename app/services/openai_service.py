from openai import AsyncOpenAI, APIStatusError, APIConnectionError, RateLimitError
from typing import List, AsyncGenerator
from app.config import settings

_client = AsyncOpenAI(api_key=settings.openai_api_key)


def _build_messages(messages: List[dict], system_prompt: str) -> List[dict]:
    return [{"role": "system", "content": system_prompt}] + messages


async def get_chat_completion(
    messages: List[dict],
    system_prompt: str,
    temperature: float = None,
    max_tokens: int = None,
) -> dict:
    """Returns {"content": str, "usage": dict}."""
    kwargs = {
        "model": settings.openai_model,
        "messages": _build_messages(messages, system_prompt),
        "temperature": temperature if temperature is not None else settings.openai_temperature,
        "max_tokens": max_tokens if max_tokens is not None else settings.openai_max_tokens,
    }
    try:
        response = await _client.chat.completions.create(**kwargs)
    except RateLimitError as e:
        raise ValueError(f"OpenAI rate limit reached: {e}") from e
    except APIConnectionError as e:
        raise ValueError(f"Could not connect to OpenAI: {e}") from e
    except APIStatusError as e:
        raise ValueError(f"OpenAI API error {e.status_code}: {e.message}") from e

    return {
        "content": response.choices[0].message.content,
        "usage": {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        },
        "finish_reason": response.choices[0].finish_reason,
    }


async def stream_chat_completion(
    messages: List[dict],
    system_prompt: str,
    temperature: float = None,
    max_tokens: int = None,
) -> AsyncGenerator[str, None]:
    """Yields text chunks as they arrive from the API."""
    kwargs = {
        "model": settings.openai_model,
        "messages": _build_messages(messages, system_prompt),
        "temperature": temperature if temperature is not None else settings.openai_temperature,
        "max_tokens": max_tokens if max_tokens is not None else settings.openai_max_tokens,
        "stream": True,
    }
    try:
        async with _client.chat.completions.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield text
    except RateLimitError as e:
        raise ValueError(f"OpenAI rate limit reached: {e}") from e
    except APIConnectionError as e:
        raise ValueError(f"Could not connect to OpenAI: {e}") from e
    except APIStatusError as e:
        raise ValueError(f"OpenAI API error {e.status_code}: {e.message}") from e
