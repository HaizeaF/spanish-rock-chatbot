from typing import List
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage

class GraphState(TypedDict):
    question: str
    generation: str
    is_web_search: bool
    documents: List[str]
    history: List[BaseMessage]
    retries: int