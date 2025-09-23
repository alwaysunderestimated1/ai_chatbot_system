import json
from openai import AsyncOpenAI, APIStatusError, APIConnectionError, RateLimitError
from typing import List, AsyncGenerator, Optional
from app.config import settings
from app.services.tool_service import TOOL_DEFINITIONS, execute_tool

_client = AsyncOpenAI(api_key=settings.openai_api_key)

MAX_TOOL_ROUNDS = 5


def _build_messages(messages: List[dict], system_prompt: str) -> List[dict]:
    return [{"role": "system", "content": system_prompt}] + messages


def _handle_error(e: Exception) -> None:
    if isinstance(e, RateLimitError):
        raise ValueError(f"OpenAI rate limit reached: {e}") from e
    if isinstance(e, APIConnectionError):
        raise ValueError(f"Could not connect to OpenAI: {e}") from e
    if isinstance(e, APIStatusError):
        raise ValueError(f"OpenAI API error {e.status_code}: {e.message}") from e
    raise e


async def get_chat_completion(
    messages: List[dict],
    system_prompt: str,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> dict:
    """Standard completion. Returns {content, usage, finish_reason}."""
    try:
        response = await _client.chat.completions.create(
            model=settings.openai_model,
            messages=_build_messages(messages, system_prompt),
            temperature=temperature if temperature is not None else settings.openai_temperature,
            max_tokens=max_tokens if max_tokens is not None else settings.openai_max_tokens,
        )
    except Exception as e:
        _handle_error(e)

    return {
        "content": response.choices[0].message.content,
        "usage": {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        },
        "finish_reason": response.choices[0].finish_reason,
    }


async def get_chat_completion_with_tools(
    messages: List[dict],
    system_prompt: str,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> dict:
    """Completion with tool-calling loop. Executes tools and feeds results back until done."""
    full_messages = _build_messages(messages, system_prompt)
    total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    try:
        for _ in range(MAX_TOOL_ROUNDS):
            response = await _client.chat.completions.create(
                model=settings.openai_model,
                messages=full_messages,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
                temperature=temperature if temperature is not None else settings.openai_temperature,
                max_tokens=max_tokens if max_tokens is not None else settings.openai_max_tokens,
            )

            for key in total_usage:
                total_usage[key] += getattr(response.usage, key, 0)

            choice = response.choices[0]

            if choice.finish_reason != "tool_calls":
                return {
                    "content": choice.message.content,
                    "usage": total_usage,
                    "finish_reason": choice.finish_reason,
                }

            # Append assistant message with tool_calls
            assistant_msg: dict = {"role": "assistant", "content": choice.message.content}
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in choice.message.tool_calls
            ]
            full_messages.append(assistant_msg)

            # Execute each tool and append results
            for tc in choice.message.tool_calls:
                args = json.loads(tc.function.arguments)
                result = await execute_tool(tc.function.name, args)
                full_messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

    except Exception as e:
        _handle_error(e)

    return {
        "content": "Tool call limit reached without a final response.",
        "usage": total_usage,
        "finish_reason": "tool_limit",
    }


async def stream_chat_completion(
    messages: List[dict],
    system_prompt: str,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> AsyncGenerator[str, None]:
    """Yields text chunks as they arrive."""
    try:
        async with _client.chat.completions.stream(
            model=settings.openai_model,
            messages=_build_messages(messages, system_prompt),
            temperature=temperature if temperature is not None else settings.openai_temperature,
            max_tokens=max_tokens if max_tokens is not None else settings.openai_max_tokens,
        ) as stream:
            async for text in stream.text_stream:
                yield text
    except Exception as e:
        _handle_error(e)
