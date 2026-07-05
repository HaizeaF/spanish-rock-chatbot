"""Ingestion pipeline: crawl Wikipedia, split into chunks and index them in Chroma."""

import asyncio
import os
import shutil
from dotenv import load_dotenv
load_dotenv()
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface.embeddings import HuggingFaceEmbeddings
from chatbot.backend.config.config import Config
from chatbot.backend.rag.wikipedia import get_article_documents_in_categories

def _split_text(documents: list[Document]) -> list[Document]:
    """Split articles into overlapping chunks and prepend the article title to each."""
    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(chunk_size=Config.CHUNK_SIZE, chunk_overlap=Config.CHUNK_OVERLAP)

    chunks = text_splitter.split_documents(documents)
    enriched_chunks = []

    for chunk in chunks:
        title = chunk.metadata["title"]

        enriched_chunks.append(
            Document(
                page_content=f"Título: {title}\n\n{chunk.page_content}",
                metadata=chunk.metadata,
            )
        )

    print(f"Splitted into {len(enriched_chunks)} chunks.")

    return enriched_chunks

async def ingest() -> None:
    """Rebuild the vector store from scratch using freshly crawled Wikipedia articles."""
    if os.path.exists(Config.CHROMA_PATH):
        shutil.rmtree(Config.CHROMA_PATH)

    print("Fetching article documents from Wikipedia")
    documents = await get_article_documents_in_categories()

    chunks = _split_text(documents)
    embeddings = HuggingFaceEmbeddings(model_name=Config.EMBEDDING_MODEL_NAME)
    
    await Chroma.afrom_documents(chunks, embeddings, persist_directory=Config.CHROMA_PATH)

    print(f"Saved {len(chunks)} chunks to {Config.CHROMA_PATH}.")

if __name__ == "__main__":
    asyncio.run(ingest())