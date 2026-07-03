import asyncio
import os
import shutil
from dotenv import load_dotenv
load_dotenv()
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface.embeddings import HuggingFaceEmbeddings
from chatbot.backend.config import CHROMA_PATH, EMBEDDING_MODEL_NAME, CHUNK_OVERLAP, CHUNK_SIZE
from chatbot.backend.rag.wikipedia import get_article_documents_in_category_tree

def _split_text(documents: list[Document]) -> list[Document]:
    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)

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
    if os.path.exists(CHROMA_PATH):
        shutil.rmtree(CHROMA_PATH)

    print("Fetching article documents from Wikipedia")
    documents = await get_article_documents_in_category_tree()

    chunks = _split_text(documents)
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
    
    await Chroma.afrom_documents(chunks, embeddings, persist_directory=CHROMA_PATH)

    print(f"Saved {len(chunks)} chunks to {CHROMA_PATH}.")

if __name__ == "__main__":
    asyncio.run(ingest())