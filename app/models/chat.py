from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime, timezone


class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChatRequest(BaseModel):
    session_id: str
    message: str
    system_prompt: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    use_rag: bool = False
    use_tools: bool = False


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    history: List[Message]
    usage: Optional[Dict[str, int]] = None


class Session(BaseModel):
    session_id: str
    title: str = "New Conversation"
    system_prompt: str = "You are a helpful assistant."
    messages: List[Message] = []
    message_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SessionSummary(BaseModel):
    session_id: str
    title: str
    message_count: int
    created_at: datetime
    updated_at: datetime


class SessionUpdate(BaseModel):
    title: Optional[str] = None
    system_prompt: Optional[str] = None


class SessionListResponse(BaseModel):
    sessions: List[SessionSummary]
    total: int
    page: int
    page_size: int
