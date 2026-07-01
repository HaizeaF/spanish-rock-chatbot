import asyncio
import wikipediaapi
from chatbot.backend.config import WIKI_USER_AGENT, WIKI_MAX_CATEGORY_DEPTH, WIKI_ROOT_CATEGORY
from dataclasses import dataclass, field
from urllib.parse import quote


@dataclass
class CrawlState:
    wiki: wikipediaapi.AsyncWikipedia
    max_depth: int
    visited_categories: set[str] = field(default_factory=set)
    article_urls: set[str] = field(default_factory=set)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


def _get_wiki_client() -> wikipediaapi.AsyncWikipedia:
    return wikipediaapi.AsyncWikipedia(user_agent=WIKI_USER_AGENT, language="es")


def _title_to_url(title: str) -> str:
    return f"https://es.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}"


async def _walk_category(state: CrawlState, category_title: str, depth: int) -> None:
    if depth > state.max_depth:
        print(f"{'  ' * depth}Skipping '{category_title}' (max depth {state.max_depth} reached)")
        return

    async with state.lock:
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

    async with state.lock:
        state.article_urls.update(_title_to_url(title) for title in new_articles)

    await asyncio.gather(*[_walk_category(state, sub, depth + 1) for sub in subcategories])


async def get_article_urls_in_category_tree(
    root_category: str = WIKI_ROOT_CATEGORY,
    max_depth: int = WIKI_MAX_CATEGORY_DEPTH,
) -> list[str]:
    print(f"Starting crawl from root category '{root_category}' (max depth {max_depth})")
    state = CrawlState(wiki=_get_wiki_client(), max_depth=max_depth)
    await _walk_category(state, root_category, depth=0)
    print(f"Crawl finished: {len(state.article_urls)} unique articles found across {len(state.visited_categories)} categories")
    return sorted(state.article_urls)