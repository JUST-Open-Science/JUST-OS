import logging
from typing import Dict, Any, Optional

from llama_index.core import StorageContext, load_index_from_storage
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.faiss import FaissVectorStore

from config.settings import get_config
from just_os.chat_manager import ChatManager
from just_os.qualle import Qualle

logger = logging.getLogger(__name__)

# Singleton instance for the RAG service
_rag_service_instance: Optional[Qualle] = None


def create_embedding_model(config: Dict[str, Any]):
    """
    Create and initialize the embedding model.

    Args:
        config: Configuration dictionary

    Returns:
        The initialized embedding model
    """
    try:
        return HuggingFaceEmbedding(model_name=config["EMBEDDING_MODEL"])
    except Exception as e:
        logger.error(f"Failed to initialize embedding model: {str(e)}")
        raise


def create_retriever(config: Dict[str, Any], embed_model):
    """
    Create and initialize the retriever component.

    Args:
        config: Configuration dictionary
        embed_model: The embedding model to use

    Returns:
        The initialized retriever
    """
    try:
        persist_dir = config["VECTOR_STORE"]
        vector_store = FaissVectorStore.from_persist_dir(persist_dir)
        storage_context = StorageContext.from_defaults(
            vector_store=vector_store, persist_dir=persist_dir
        )

        index = load_index_from_storage(
            storage_context=storage_context, embed_model=embed_model
        )

        return index.as_retriever(similarity_top_k=config["RETRIEVER_TOP_K"])
    except Exception as e:
        logger.error(f"Failed to initialize retriever: {str(e)}")
        raise


def create_rag_service(
    config: Optional[Dict[str, Any]] = None, chat_manager: Optional[ChatManager] = None
) -> Qualle:
    """
    Create a RAG service (Qualle) instance with the necessary components.
    Uses a singleton pattern to avoid creating multiple instances.

    Args:
        config: Configuration dictionary. If None, uses the default config.
        chat_manager: Chat manager instance. If None, creates a new instance.

    Returns:
        Qualle: The initialized RAG service instance
    """
    global _rag_service_instance

    # Return existing instance if available
    if _rag_service_instance is not None:
        return _rag_service_instance

    logger.debug("Initializing RAG components")

    # Use default config if not provided
    if config is None:
        config = get_config()

    # Create chat manager if not provided
    if chat_manager is None:
        chat_manager = ChatManager()

    try:
        # Initialize embedding model
        embed_model = create_embedding_model(config)

        # Initialize retriever
        retriever = create_retriever(config, embed_model)

        # Create and store the Qualle instance
        _rag_service_instance = Qualle(config, chat_manager, embed_model, retriever)
        logger.debug("Created new Qualle instance")

        return _rag_service_instance
    except Exception as e:
        logger.error(f"Failed to create RAG service: {str(e)}")
        raise
