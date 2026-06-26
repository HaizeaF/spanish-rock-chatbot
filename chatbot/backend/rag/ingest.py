import os
import shutil
from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_milvus import Milvus
from langchain_huggingface.embeddings import HuggingFaceEmbeddings
from chatbot.backend.config import DB_PATH, COLLECTION_NAME, WIKIPEDIA_URLS

def ingest():
    if os.path.exists(DB_PATH):
        shutil.rmtree(DB_PATH)
    
    docs = [WebBaseLoader(url).load() for url in WIKIPEDIA_URLS]
    docs_list = [item for sublist in docs for item in sublist]

    splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=500,
        chunk_overlap=50
    )
    chunks = splitter.split_documents(docs_list)

    Milvus.from_documents(
        documents=chunks,
        collection_name=COLLECTION_NAME,
        embedding=HuggingFaceEmbeddings(),
        connection_args={"uri": DB_PATH}
    )
    print(f"Ingested {len(chunks)} chunks into {DB_PATH}")

if __name__ == "__main__":
    ingest()