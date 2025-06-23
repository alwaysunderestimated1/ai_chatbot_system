from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone


class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChatRequest(BaseModel):
    session_id: str
    message: str
    system_prompt: Optional[str] = "You are a helpful assistant."


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    history: List[Message]


class Session(BaseModel):
    session_id: str
    messages: List[Message] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
