"""FastAPI application entry point for the chatbot."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from chatbot.backend.rag.retriever import get_retriever
from chatbot.backend.routes import chat as chat_router
from chatbot.backend.routes import health as health_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Warm up the retriever (embeddings, vector store, reranker) on startup."""
    await get_retriever()
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(chat_router.router)
app.include_router(health_router.router)