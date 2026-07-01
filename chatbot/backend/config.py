import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Paths
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = str(BASE_DIR / "rag" / "data" / "spanish_rock.db")
INGEST_STATE_PATH = BASE_DIR / "rag" / "data" / "ingested_urls.json"

# Milvus
COLLECTION_NAME = "spanish_rock"

# LLM
LLM_MODEL = "llama3"

# Graph
MAX_RETRIES = 3

# Chunk config
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 100

# Retriever
RETRIEVER_K = 12

# Web search
WEB_SEARCH_MAX_RESULTS = 3

# Necessary relevant docs
MIN_DOCS_FOR_GENERATION = 4

# Off-topic response
OFF_TOPIC_RESPONSE = "Lo siento, soy un asistente especializado en rock español. No puedo ayudarte con ese tema."

# Wikipedia
WIKI_ROOT_CATEGORY = "Categoría:Grupos_de_rock_de_España"
WIKI_MAX_CATEGORY_DEPTH = 5
WIKI_USER_AGENT = os.getenv("WIKI_USER_AGENT")

if not WIKI_USER_AGENT:
    raise RuntimeError("WIKI_USER_AGENT not defined in .env.")