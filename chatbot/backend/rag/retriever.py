from langchain_milvus import Milvus
from langchain_huggingface.embeddings import HuggingFaceEmbeddings
from chatbot.backend.config import DB_PATH, COLLECTION_NAME, RETRIEVER_K
import os

def get_retriever():
    vectorstore = Milvus(
        embedding_function=HuggingFaceEmbeddings(),
        collection_name=COLLECTION_NAME,
        connection_args={"uri": DB_PATH}
    )

    return vectorstore.as_retriever(search_kwargs={"k": RETRIEVER_K})