import asyncio
from langchain_milvus import Milvus
from langchain_huggingface.embeddings import HuggingFaceEmbeddings
from chatbot.backend.config import DB_PATH, COLLECTION_NAME, RETRIEVER_K

_retriever = None
_lock = asyncio.Lock()

def _build_retriever():
    vectorstore = Milvus(
        embedding_function=HuggingFaceEmbeddings(),
        collection_name=COLLECTION_NAME,
        connection_args={"uri": DB_PATH}
    )

    return vectorstore.as_retriever(search_kwargs={"k": RETRIEVER_K})

async def get_retriever():
    global _retriever
    async with _lock:
        if _retriever is None:
            _retriever = await asyncio.to_thread(_build_retriever)
    
    return _retriever