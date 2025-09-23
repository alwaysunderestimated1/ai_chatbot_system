import numpy as np
import tiktoken
from openai import AsyncOpenAI
from app.config import settings
from app.models.document import Document, DocumentChunk, DocumentSummary, SearchResult

_client = AsyncOpenAI(api_key=settings.openai_api_key)
_tokenizer = tiktoken.get_encoding("cl100k_base")

EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_CHUNK_SIZE = 500  # tokens
CHUNK_OVERLAP = 50        # tokens


def _chunk_text(text: str, chunk_size: int = DEFAULT_CHUNK_SIZE) -> list[str]:
    tokens = _tokenizer.encode(text)
    chunks = []
    start = 0
    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        chunks.append(_tokenizer.decode(tokens[start:end]))
        start += chunk_size - CHUNK_OVERLAP
    return chunks


async def _embed(texts: list[str]) -> list[list[float]]:
    response = await _client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    return [item.embedding for item in response.data]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    va, vb = np.array(a), np.array(b)
    norm = np.linalg.norm(va) * np.linalg.norm(vb)
    return float(np.dot(va, vb) / norm) if norm else 0.0


async def ingest_document(
    filename: str, content: str, chunk_size: int = DEFAULT_CHUNK_SIZE, metadata: dict = {}
) -> Document:
    from app.database.mongodb import get_db
    db = get_db()

    doc = Document(filename=filename, metadata=metadata)
    chunk_texts = _chunk_text(content, chunk_size=chunk_size)
    embeddings = await _embed(chunk_texts)

    chunks = [
        DocumentChunk(
            doc_id=doc.doc_id,
            content=chunk_texts[i],
            embedding=embeddings[i],
            chunk_index=i,
            metadata=metadata,
        )
        for i in range(len(chunk_texts))
    ]
    doc.chunk_count = len(chunks)

    await db.documents.insert_one(doc.model_dump())
    if chunks:
        await db.document_chunks.insert_many([c.model_dump() for c in chunks])

    return doc


async def retrieve(query: str, top_k: int = 5) -> list[SearchResult]:
    from app.database.mongodb import get_db
    db = get_db()

    [query_embedding] = await _embed([query])

    chunks = await db.document_chunks.find(
        {}, {"chunk_id": 1, "doc_id": 1, "content": 1, "embedding": 1, "chunk_index": 1}
    ).to_list(length=None)

    if not chunks:
        return []

    doc_ids = list({c["doc_id"] for c in chunks})
    docs = await db.documents.find(
        {"doc_id": {"$in": doc_ids}}, {"doc_id": 1, "filename": 1}
    ).to_list(length=None)
    doc_map = {d["doc_id"]: d["filename"] for d in docs}

    scored = sorted(
        [
            SearchResult(
                chunk_id=c["chunk_id"],
                doc_id=c["doc_id"],
                filename=doc_map.get(c["doc_id"], "unknown"),
                content=c["content"],
                score=_cosine_similarity(query_embedding, c["embedding"]),
                chunk_index=c["chunk_index"],
            )
            for c in chunks
        ],
        key=lambda r: r.score,
        reverse=True,
    )
    return scored[:top_k]


async def build_rag_context(query: str, top_k: int = 5) -> str:
    results = await retrieve(query, top_k=top_k)
    if not results:
        return ""
    parts = [f"[Source: {r.filename}, chunk {r.chunk_index}]\n{r.content}" for r in results]
    return "Relevant context from knowledge base:\n\n" + "\n\n---\n\n".join(parts)


async def list_documents() -> list[DocumentSummary]:
    from app.database.mongodb import get_db
    db = get_db()
    docs = await db.documents.find(
        {}, {"doc_id": 1, "filename": 1, "chunk_count": 1, "created_at": 1}
    ).to_list(length=None)
    return [DocumentSummary(**d) for d in docs]


async def delete_document(doc_id: str) -> None:
    from app.database.mongodb import get_db
    db = get_db()
    result = await db.documents.delete_one({"doc_id": doc_id})
    if result.deleted_count == 0:
        raise KeyError(f"Document '{doc_id}' not found.")
    await db.document_chunks.delete_many({"doc_id": doc_id})
