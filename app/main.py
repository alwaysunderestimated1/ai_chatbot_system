from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.config import settings
from app.database.mongodb import connect_db, close_db
from app.routes import chat


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    yield
    await close_db()


app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    lifespan=lifespan,
)

app.include_router(chat.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
