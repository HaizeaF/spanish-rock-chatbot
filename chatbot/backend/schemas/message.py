from pydantic import BaseModel

class MessageRequest(BaseModel):
    """Request payload for the /chat endpoint."""
    question: str
    history: list[dict] = []

class MessageResponse(BaseModel):
    """Response payload for the /chat endpoint."""
    agent_response: str