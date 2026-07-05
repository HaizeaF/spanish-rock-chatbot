"""Shared state definition for the chatbot conversational graph."""

from typing import List
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langchain_core.documents import Document

class GraphState(TypedDict):
    """State passed between nodes of the conversational graph.
 
    Attributes:
        question: The raw question as typed by the user.
        standalone_question: The question rewritten to be self-contained.
        keywords: The keyword query used for retrieval.
        generation: The answer produced by the assistant.
        documents: The documents currently available as context.
        history: The prior conversation messages.
        web_searched: Whether a web search has already been attempted this turn.
    """
    question: str
    standalone_question: str
    keywords: str
    generation: str
    documents: List[Document]
    history: List[BaseMessage]
    web_searched: bool