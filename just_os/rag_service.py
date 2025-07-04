import logging

from llama_index.core import StorageContext, load_index_from_storage
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.faiss import FaissVectorStore

from just_os.chat_manager import ChatManager
from just_os.qualle import Qualle

logger = logging.getLogger(__name__)


def create_rag_service(config, chat_manager: ChatManager) -> Qualle:
    """
    Create a RAG service (Qualle) instance with the necessary components.

    Args:
        config: Configuration dictionary containing necessary parameters
        chat_manager: Chat manager instance for handling conversation history

    Returns:
        Qualle: The initialized RAG service instance
    """
    logger.debug("Initializing RAG components")

    # Initialize embedding model
    embed_model = HuggingFaceEmbedding(model_name=config["EMBEDDING_MODEL"])

    # Initialize vector store and retriever
    persist_dir = config["VECTOR_STORE"]
    vector_store = FaissVectorStore.from_persist_dir(persist_dir)
    storage_context = StorageContext.from_defaults(
        vector_store=vector_store, persist_dir=persist_dir
    )

    index = load_index_from_storage(
        storage_context=storage_context, embed_model=embed_model
    )

    retriever = index.as_retriever(similarity_top_k=config["RETRIEVER_TOP_K"])

    # Create and return the Qualle instance
    rag_service = Qualle(config, chat_manager, embed_model, retriever)
    logger.debug("Created new Qualle instance")

    return rag_service
