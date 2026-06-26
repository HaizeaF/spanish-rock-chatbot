from langchain_milvus import Milvus
from langchain_huggingface.embeddings import HuggingFaceEmbeddings
from chatbot.backend.config import DB_PATH, COLLECTION_NAME, RETRIEVER_K
import os

def get_retriever():
    print("========== MILVUS DEBUG ==========")
    print("cwd:", os.getcwd())
    print("DB_PATH:", DB_PATH)
    print("exists:", os.path.exists(DB_PATH))
    print("parent:", os.path.dirname(DB_PATH))
    print("parent exists:", os.path.exists(os.path.dirname(DB_PATH)))
    print("==================================")

    vectorstore = Milvus(
        embedding_function=HuggingFaceEmbeddings(),
        collection_name=COLLECTION_NAME,
        connection_args={"uri": DB_PATH}
    )

    return vectorstore.as_retriever(search_kwargs={"k": RETRIEVER_K})