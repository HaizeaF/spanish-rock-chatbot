import os
import shutil
import asyncio
from dotenv import load_dotenv
load_dotenv()
from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_milvus import Milvus
from langchain_huggingface.embeddings import HuggingFaceEmbeddings
from chatbot.backend.config import DB_PATH, COLLECTION_NAME, WIKIPEDIA_URLS, CHUNK_OVERLAP, CHUNK_SIZE

async def _milvus_ingest(chunks):
    await Milvus.afrom_documents(
        documents=chunks,
        collection_name=COLLECTION_NAME,
        embedding=HuggingFaceEmbeddings(),
        connection_args={"uri": DB_PATH}
    )

async def ingest():
    if os.path.exists(DB_PATH):
        shutil.rmtree(DB_PATH)

    docs_list = []
    for url in WIKIPEDIA_URLS:
        docs_list.extend(WebBaseLoader(url).load())

    splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP
    )
    chunks = splitter.split_documents(docs_list)
    await _milvus_ingest(chunks)
    print(f"Ingested {len(chunks)} chunks into {DB_PATH}")

if __name__ == "__main__":
    asyncio.run(ingest())