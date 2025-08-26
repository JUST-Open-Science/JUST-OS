import os
from typing import Dict, Any

# Default configuration values
DEFAULT_CONFIG: Dict[str, Any] = {
    # Chunking settings
    "CHUNK_SIZE": 350,
    # LLM settings
    "BASE_URL": "https://llm.hpc.rug.nl/",
    "RUGLLM_API_KEY": os.getenv("RUGLLM_API_KEY"),
    "CITATION_MODEL": "openscholar",
    "GENERAL_MODEL": "default-chat",
    "EMBEDDING_MODEL": "BAAI/bge-small-en-v1.5",
    "RERANK_MODEL": "bge-reranker-large",
    # Temperature settings
    "TEMPERATURE": 0.3,
    "TEMPERATURE_GENERAL": 0.15,
    # Vector store settings
    "VECTOR_STORE": "data/processed/vs_250703_bge-small-en-v1.5",
    "RETRIEVER_TOP_K": 20,
    # RANKING SETTINGS
    "MIN_RELEVANCE": 0.1,
    "MAX_CHUNKS": 7,
    # Redis settings
    "REDIS_HOST": "redis",
    "REDIS_PORT": 6379,
    "REDIS_DB": 0,
    # Rate limiting configuration
    "RATE_LIMIT_MINUTE": 10,  # Number of requests allowed per minute per user/IP
    "RATE_LIMIT_HOUR": 50,  # Number of requests allowed per hour per user/IP
    "RATE_LIMIT_DAY": 200,  # Number of requests allowed per day per user/IP
    # Chat settings
    "MESSAGE_TTL": 3600,  # 1 hour in seconds
    # Google Drive settings
    "CREDENTIALS_FILE": "credentials.json",
    "GDRIVE_FOLDER_ID": "1EqOxpkb-ksYjRmvSHl1XjULlcPxZINdD",
    "URL_JUST_OS_DB": "https://drive.google.com/uc?id=1eMiimpcwcnVJT6k4PQ9xfz3Udvsejo6V",
    "GDRIVE_AUTENTICATION_SERVER_PORT": 41813,
}

# Override defaults with environment variables
for key in DEFAULT_CONFIG:
    if os.environ.get(key):
        # Convert to appropriate type based on default value
        default_value = DEFAULT_CONFIG[key]
        if isinstance(default_value, int):
            DEFAULT_CONFIG[key] = int(os.environ.get(key))
        elif isinstance(default_value, float):
            DEFAULT_CONFIG[key] = float(os.environ.get(key))
        elif isinstance(default_value, bool):
            DEFAULT_CONFIG[key] = os.environ.get(key).lower() in ("true", "yes", "1")
        else:
            DEFAULT_CONFIG[key] = os.environ.get(key)

# Export all configuration values to module level for backward compatibility
for key, value in DEFAULT_CONFIG.items():
    globals()[key] = value


def get_config() -> Dict[str, Any]:
    """Return the current configuration as a dictionary."""
    return {k: v for k, v in DEFAULT_CONFIG.items()}
