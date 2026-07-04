import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Paths
BASE_DIR: Path = Path(__file__).resolve().parent
CHROMA_PATH: str = str(BASE_DIR / "rag" / "data" / "chroma")

# LLM
LLM_MODEL: str = "llama3"

# Graph
MAX_RETRIES: int = 3

# Chunk config
CHUNK_SIZE: int = 800
CHUNK_OVERLAP: int = 80

# Retriever
RETRIEVER_K: int = 30

# Embedding model
EMBEDDING_MODEL_NAME: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Reranker
SIMILARITY_WEIGHT: float = 0.5
RERANKER_MODEL_NAME: str = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
RERANKER_TOP_N: int = 4

# Web search
WEB_SEARCH_MAX_RESULTS: int = 3

# Defined responses
FALLBACK_RESPONSE: str = "Lo siento, no tengo información suficiente para responder. También puedes intentar formular la pregunta de otra manera."
OFF_TOPIC_RESPONSE: str = "Lo siento, soy un asistente especializado en rock español. No puedo ayudarte con ese tema."

# Wikipedia
WIKI_ROOT_CATEGORIES: list[str] = ["Categoría:Grupos_de_rock_de_España", "Categoría:Músicos_de_rock_de_España"]
WIKI_MAX_CATEGORY_DEPTH: int = 5
WIKI_USER_AGENT: str = os.getenv("WIKI_USER_AGENT")

if not WIKI_USER_AGENT:
    raise RuntimeError("WIKI_USER_AGENT not defined in .env.")