from typing import List
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langchain_core.documents import Document

class GraphState(TypedDict):
    question: str
    standalone_question: str
    keywords: str
    generation: str
    documents: List[Document]
    history: List[BaseMessage]
    web_searched: bool