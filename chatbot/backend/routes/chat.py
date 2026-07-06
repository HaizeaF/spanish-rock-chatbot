"""Chat endpoint: runs a conversational turn through the graph."""
from langchain_core.messages import HumanMessage, AIMessage
from chatbot.backend.schemas.message import MessageRequest, MessageResponse
from fastapi import APIRouter
from chatbot.backend.services.graph_service import build_graph

router = APIRouter()
graph = build_graph()

def _parse_history(history: list[dict]) -> list:
    """Convert plain dict history entries into LangChain message objects."""
    messages = []
    for msg in history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))
    
    return messages

@router.post("/chat", response_model=MessageResponse)
async def chat(request: MessageRequest) -> MessageResponse:
    """Run a single conversational turn through the chatbot graph."""
    result = await graph.ainvoke({
        "question": request.question,
        "standalone_question": "",
        "keywords": "",
        "history": _parse_history(request.history),
        "documents": [],
        "generation": "",
        "web_searched": False
    })

    return MessageResponse(agent_response=result["generation"])