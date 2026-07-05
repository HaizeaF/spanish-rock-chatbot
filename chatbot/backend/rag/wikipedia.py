"""Recursive crawler that collects Wikipedia articles from a set of root categories."""

import asyncio
import wikipediaapi
from chatbot.backend.config import WIKI_USER_AGENT, WIKI_MAX_CATEGORY_DEPTH, WIKI_ROOT_CATEGORIES
from langchain_core.documents import Document
from dataclasses import dataclass, field
from urllib.parse import quote

@dataclass
class CrawlState:
    """Mutable state shared across the recursive category crawl."""
    wiki: wikipediaapi.AsyncWikipedia
    max_depth: int
    visited_categories: set[str] = field(default_factory=set)
    article_documents: dict[str, Document] = field(default_factory=dict)
    
def _get_wiki_client() -> wikipediaapi.AsyncWikipedia:
    """Create an async Spanish Wikipedia API client."""
    return wikipediaapi.AsyncWikipedia(user_agent=WIKI_USER_AGENT, language="es")

def _title_to_url(title: str) -> str:
    """Build the Spanish Wikipedia URL for an article title."""
    return f"https://es.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}"

async def _title_to_document(wiki: wikipediaapi.AsyncWikipedia, title: str) -> Document:
    """Fetch an article's full text and wrap it as a LangChain Document."""
    page = wiki.page(title)
    text = await page.text
    return Document(page_content=text, metadata={"title": title, "url": _title_to_url(title)})

async def _walk_category(state: CrawlState, category_title: str, depth: int, lock: asyncio.Lock) -> None:
    """Recursively visit a category, collecting its articles and its subcategories."""
    if depth > state.max_depth:
        print(f"{'  ' * depth}Skipping '{category_title}' (max depth {state.max_depth} reached)")
        return

    async with lock:
        if category_title in state.visited_categories:
            print(f"{'  ' * depth}Skipping '{category_title}' (already visited)")
            return

        print(f"{'  ' * depth}Visiting category '{category_title}' (depth {depth})")
        state.visited_categories.add(category_title)

    page = state.wiki.page(category_title)
    members = await page.categorymembers

    subcategories = [title for title, member in members.items() if member.ns == wikipediaapi.Namespace.CATEGORY]
    new_articles = [title for title, member in members.items() if member.ns == wikipediaapi.Namespace.MAIN]

    print(
        f"{'  ' * depth}  -> Found {len(new_articles)} article(s) and "
        f"{len(subcategories)} subcategory(ies) in '{category_title}'"
    )

    async with lock:
        documents = await asyncio.gather(*[_title_to_document(state.wiki, title) for title in new_articles])

        for i, doc in enumerate(documents, start=1):
            state.article_documents[doc.metadata["url"]] = doc
            print(f"[{i}/{len(documents)}] {doc.metadata['url']}")

    await asyncio.gather(*[_walk_category(state, sub, depth + 1, lock) for sub in subcategories])


async def get_article_documents_in_categories(root_categories: list[str] = WIKI_ROOT_CATEGORIES,max_depth: int = WIKI_MAX_CATEGORY_DEPTH) -> list[Document]:
    """Crawl the given categories and return all unique articles found as Documents."""
    print(f"Starting crawl from root categories: '{root_categories}' (max depth {max_depth})")

    state = CrawlState(wiki=_get_wiki_client(), max_depth=max_depth)
    lock = asyncio.Lock()
    await asyncio.gather(*[_walk_category(state, category, 0, lock) for category in root_categories])

    print(f"Crawl finished: {len(state.article_documents)} unique articles found across {len(state.visited_categories)} categories")

    return list(state.article_documents.values())