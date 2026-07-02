import asyncio
from langchain_milvus import Milvus
from langchain_huggingface.embeddings import HuggingFaceEmbeddings
from chatbot.backend.config import DB_PATH, COLLECTION_NAME, RETRIEVER_K, EMBEDDING_MODEL_NAME

_retriever = None
_lock = asyncio.Lock()

async def get_retriever():
    global _retriever
    async with _lock:
        if _retriever is None:
            vectorstore = Milvus(
                embedding_function=HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME), 
                collection_name=COLLECTION_NAME, 
                connection_args={"uri": DB_PATH}
            )
            _retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": RETRIEVER_K})
    
    return _retriever