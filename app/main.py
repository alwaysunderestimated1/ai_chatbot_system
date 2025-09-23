from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.config import settings
from app.database.mongodb import connect_db, close_db, get_db
from app.routes import chat, sessions, documents


async def create_indexes():
    db = get_db()
    await db.sessions.create_index("session_id", unique=True)
    await db.sessions.create_index("updated_at")
    await db.documents.create_index("doc_id", unique=True)
    await db.document_chunks.create_index("doc_id")
    await db.document_chunks.create_index("chunk_id", unique=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    await create_indexes()
    yield
    await close_db()


app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    lifespan=lifespan,
)

app.include_router(chat.router)
app.include_router(sessions.router)
app.include_router(documents.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
