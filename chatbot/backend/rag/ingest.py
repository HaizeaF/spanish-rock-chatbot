import asyncio
from dotenv import load_dotenv
load_dotenv()
from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_milvus import Milvus
from langchain_huggingface.embeddings import HuggingFaceEmbeddings
from chatbot.backend.config import DB_PATH, COLLECTION_NAME, CHUNK_OVERLAP, CHUNK_SIZE
from chatbot.backend.rag.wikipedia import get_article_urls_in_category_tree
from chatbot.backend.config import INGEST_STATE_PATH
from chatbot.backend.rag.ingest_state import load_ingested_urls, save_ingested_url


def _build_splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter.from_tiktoken_encoder(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)


async def ingest():
    print("Fetching article URLs from Wikipedia")
    urls = await get_article_urls_in_category_tree()

    already_ingested = load_ingested_urls(INGEST_STATE_PATH)

    new_urls = [url for url in urls if url not in already_ingested]

    print(
        f"Found {len(urls)} URLs. "
        f"{len(new_urls)} new URLs to ingest."
    )

    if not new_urls:
        print("Nothing to ingest")
        return

    splitter = _build_splitter()

    vectorstore = Milvus(
        embedding_function=HuggingFaceEmbeddings(),
        collection_name=COLLECTION_NAME,
        connection_args={"uri": DB_PATH}
    )

    total_chunks = 0
    failed = 0

    for i, url in enumerate(new_urls, start=1):
        print(f"[{i}/{len(new_urls)}] Loading {url}")
        try:
            docs = WebBaseLoader(url).load()
        except Exception as e:
            failed += 1
            print(f"[{i}/{len(new_urls)}] Failed to load {url}: {e}")
            continue

        chunks = splitter.split_documents(docs)
        if not chunks:
            print(f"[{i}/{len(new_urls)}] No chunks produced, skipping")
            continue

        try:
            await vectorstore.aadd_documents(chunks)

            total_chunks += len(chunks)

            save_ingested_url(INGEST_STATE_PATH, url)
        except Exception as e:
            failed += 1

            print(f"[{i}/{len(new_urls)}] Failed inserting {url}: {e}")
            continue

        total_chunks += len(chunks)

    print(f"Ingest finished: {total_chunks} chunks stored in {DB_PATH} ({failed} article(s) failed out of {len(new_urls)})")


if __name__ == "__main__":
    asyncio.run(ingest())