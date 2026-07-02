import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Paths
BASE_DIR: Path = Path(__file__).resolve().parent
DB_PATH: str = str(BASE_DIR / "rag" / "data" / "spanish_rock.db")
INGEST_STATE_PATH: Path = BASE_DIR / "rag" / "data" / "ingested_urls.json"

# Milvus
COLLECTION_NAME: str = "spanish_rock"

# LLM
LLM_MODEL: str = "llama3"

# Graph
MAX_RETRIES: int = 3

# Chunk config
CHUNK_SIZE: int = 500
CHUNK_OVERLAP: int = 50

# Retriever
RETRIEVER_K: int = 4

# Embedding model
EMBEDDING_MODEL_NAME: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Web search
WEB_SEARCH_MAX_RESULTS: int = 3

# Defined responses
FALLBACK_RESPONSE: str = "Lo siento, no tengo informacion suficiente para responder."
OFF_TOPIC_RESPONSE: str = "Lo siento, soy un asistente especializado en rock español. No puedo ayudarte con ese tema."

# Wikipedia
WIKI_ROOT_CATEGORIES: list[str] = ["Categoría:Grupos_de_rock_de_España", "Categoría:Músicos_de_rock_de_España"]
WIKI_MAX_CATEGORY_DEPTH: int = 5
WIKI_USER_AGENT: str = os.getenv("WIKI_USER_AGENT")

if not WIKI_USER_AGENT:
    raise RuntimeError("WIKI_USER_AGENT not defined in .env.")