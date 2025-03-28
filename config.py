from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# OpenAI API configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    raise ValueError("No OpenAI API key found. Please set OPENAI_API_KEY in .env file")
OPENAI_API_BASE = os.getenv('OPENAI_API_BASE')  # Optional, for compatible APIs

# Chat configuration
WELCOME_MESSAGE = "Hi, I'm JUST-OS! I'd be happy to answer all your questions related to Open Science!"

# # Embedding configuration
# EMBEDDING_MODEL = "text-embedding-ada-002"
# EMBEDDING_DIMENSION = 1536

EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
VECTOR_STORE = "data/interim/vs_241218_bge-small-en-v1.5"
