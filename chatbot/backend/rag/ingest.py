import asyncio
import httpx
import bs4
from dotenv import load_dotenv
load_dotenv()
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_milvus import Milvus
from langchain_huggingface.embeddings import HuggingFaceEmbeddings
from chatbot.backend.config import DB_PATH, COLLECTION_NAME, EMBEDDING_MODEL_NAME, CHUNK_OVERLAP, CHUNK_SIZE, WIKI_USER_AGENT
from chatbot.backend.rag.wikipedia import get_article_urls_in_category_tree
from chatbot.backend.config import INGEST_STATE_PATH
from chatbot.backend.rag.ingest_state import load_ingested_urls, save_ingested_url


def _build_splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter.from_tiktoken_encoder(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)

def _table_to_text(table: bs4.Tag) -> str:
    rows = []
    for row in table.find_all("tr"):
        cells = [cell.get_text(strip=True) for cell in row.find_all(["th", "td"])]
        if any(cells):
            rows.append(" | ".join(cells))
    return "\n".join(rows)

async def _fetch_page_text(client: httpx.AsyncClient, url: str) -> tuple[str, str]:
    response = await client.get(url)
    response.raise_for_status()

    soup = bs4.BeautifulSoup(response.text, "html.parser")

    title_tag = soup.find("title")
    title = (title_tag.get_text().replace(" - Wikipedia, la enciclopedia libre", "") if title_tag else "No Title").strip()

    content_div = soup.find("div", id="mw-content-text")

    if not content_div:
        return title, ""
    
    for table in content_div.find_all("table"):
        table_text = _table_to_text(table)
        table.replace_with(bs4.NavigableString(table_text))

    for tag in content_div.find_all(["script", "style", "sup"]):
        tag.decompose()

    for tag in content_div.find_all(attrs={"aria-labelledby": ["Notas","Referencias","Bibliografía","Enlaces_externos"]}):
        tag.decompose()

    return title, content_div.get_text(separator="\n", strip=True)

async def ingest() -> None:
    print("Fetching article URLs from Wikipedia")
    urls = await get_article_urls_in_category_tree()

    already_ingested = load_ingested_urls(INGEST_STATE_PATH)

    new_urls = [url for url in urls if url not in already_ingested]

    print(f"Found {len(urls)} URLs. {len(new_urls)} new URLs to ingest.")

    if not new_urls:
        print("Nothing to ingest")
        return

    splitter = _build_splitter()

    vectorstore = Milvus(
        embedding_function=HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME), 
        collection_name=COLLECTION_NAME, 
        connection_args={"uri": DB_PATH}
    )

    total_chunks = 0
    failed = 0

    async with httpx.AsyncClient(headers={"User-Agent": WIKI_USER_AGENT}, follow_redirects=True, timeout=30) as client:
        for i, url in enumerate(new_urls, start=1):
            print(f"[{i}/{len(new_urls)}] Loading {url}")
            try:
                title, text = await _fetch_page_text(client, url)
            except Exception as e:
                failed += 1
                print(f"[{i}/{len(new_urls)}] Failed to load {url}: {e}")
                continue


            doc = Document(page_content=text, metadata={"source": url, "title": title})
            chunks = splitter.split_documents([doc])
            if not chunks:
                print(f"[{i}/{len(new_urls)}] No chunks produced, skipping")
                continue

            try:
                await vectorstore.aadd_documents(chunks)
                save_ingested_url(INGEST_STATE_PATH, url)

                total_chunks += len(chunks)
                print(f"[{i}/{len(new_urls)}] Inserted {len(chunks)} chunks. Total: {total_chunks}")
            except Exception as e:
                failed += 1

                print(f"[{i}/{len(new_urls)}] Failed inserting {url}: {e}")
                continue

    print(f"Ingest finished: {total_chunks} chunks stored in {DB_PATH} ({failed} article(s) failed out of {len(new_urls)})")


if __name__ == "__main__":
    asyncio.run(ingest())