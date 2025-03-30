from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Chat configuration
WELCOME_MESSAGE = "Hi, I'm JUST-OS! I'd be happy to answer all your questions related to Open Science!"

# # Embedding configuration
# EMBEDDING_MODEL = "text-embedding-ada-002"
# EMBEDDING_DIMENSION = 1536

EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
VECTOR_STORE = "data/interim/vs_241218_bge-small-en-v1.5"
