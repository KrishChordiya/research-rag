from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.api.routes import upload, chat, session
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import engine, Base
from app.core.logger import log
from app.core.config import settings
from app.models import *


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Starting up RAG API and initializing database...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    log.info("Shutting down RAG API...")


app = FastAPI(title="Advanced RAG API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOW_CORS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(upload.router, prefix="/api/v1", tags=["Documents"])
app.include_router(chat.router, prefix="/api/v1", tags=["Chat"])
app.include_router(session.router, prefix="/api/v1", tags=["Sessions"])
