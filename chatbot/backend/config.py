from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = str(BASE_DIR / "rag" / "data" / "spanish_rock.db")

# Milvus
COLLECTION_NAME = "spanish_rock"

# LLM
LLM_MODEL = "llama3"

# Graph
MAX_RETRIES = 3

# Retriever
RETRIEVER_K = 4

# Web search
WEB_SEARCH_MAX_RESULTS = 5

# Off-topic response
OFF_TOPIC_RESPONSE = "Lo siento, soy un asistente especializado en rock español. No puedo ayudarte con ese tema."

# TODO: Change to Wikipedia API
WIKIPEDIA_URLS = [
    "https://es.wikipedia.org/wiki/H%C3%A9roes_del_Silencio",
    "https://es.wikipedia.org/wiki/Fito_%26_Fitipaldis",
    "https://es.wikipedia.org/wiki/Extremoduro"
]