import json
from pathlib import Path

def load_ingested_urls(path: Path) -> set[str]:
    if not path.exists():
        return set()
    
    with path.open("r", encoding="utf-8") as f:
        return set(json.load(f))
    
def save_ingested_url(path: Path, url: str) -> None:
    urls = load_ingested_urls(path)
    urls.add(url)
    
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        json.dump(sorted(urls), f, indent=2, ensure_ascii=False)
    
