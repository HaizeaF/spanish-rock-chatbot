from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage
from chatbot.backend.graph.graph import build_graph
from contextlib import asynccontextmanager
from chatbot.backend.rag.retriever import get_retriever

graph = build_graph()

@asynccontextmanager
async def lifespan(app: FastAPI):
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

class MessageRequest(BaseModel):
    question: str
    history: list[dict] = []

class MessageResponse(BaseModel):
    agent_response: str

def _parse_history(history: list[dict]) -> list:
    messages = []
    for msg in history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))
    
    return messages

@app.post("/chat", response_model=MessageResponse)
async def chat(request: MessageRequest) -> MessageResponse:
    result = await graph.ainvoke({
        "question": request.question,
        "standalone_question": "",
        "history": _parse_history(request.history),
        "documents": [],
        "generation": "",
        "web_searched": False
    })

    return MessageResponse(agent_response=result["generation"])

@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}