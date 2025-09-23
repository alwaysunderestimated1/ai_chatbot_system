from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import uuid


class DocumentChunk(BaseModel):
    chunk_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    doc_id: str
    content: str
    embedding: List[float]
    chunk_index: int
    metadata: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Document(BaseModel):
    doc_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    chunk_count: int = 0
    metadata: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DocumentSummary(BaseModel):
    doc_id: str
    filename: str
    chunk_count: int
    created_at: datetime


class IngestRequest(BaseModel):
    filename: str
    content: str
    chunk_size: int = 500
    metadata: Optional[Dict[str, Any]] = {}


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


class SearchResult(BaseModel):
    chunk_id: str
    doc_id: str
    filename: str
    content: str
    score: float
    chunk_index: int
