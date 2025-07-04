CHUNK_SIZE = 350

BASE_URL = "https://llm.hpc.rug.nl/"
CITATION_MODEL = "openscholar"
GENERAL_MODEL = "default-chat"
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"

VECTOR_STORE = "data/processed/vs_250703_bge-small-en-v1.5"

RETRIEVER_TOP_K = 7

# Rate limiting configuration
RATE_LIMIT_MINUTE = 10  # Number of requests allowed per minute per user/IP
RATE_LIMIT_HOUR = 50    # Number of requests allowed per hour per user/IP
RATE_LIMIT_DAY = 200    # Number of requests allowed per day per user/IP
