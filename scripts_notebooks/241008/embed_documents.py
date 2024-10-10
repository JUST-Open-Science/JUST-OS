import json

from llama_index.core import Document, VectorStoreIndex

from llama_index.embeddings.huggingface import HuggingFaceEmbedding


from llama_index.core import (
    SimpleDirectoryReader,
    load_index_from_storage,
    VectorStoreIndex,
    StorageContext,
)
from llama_index.vector_stores.faiss import FaissVectorStore

import faiss

if __name__ == "__main__":
    with open("classified_chunks.json", encoding="utf-8") as f:
        chunks = json.load(f)
    selected_chunks = [chunk["text"] for chunk in chunks if chunk["is_useful"]]

    faiss_index = faiss.IndexFlatL2(384)

    embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")

    documents = [Document(text=chunk) for chunk in selected_chunks]

    vector_store = FaissVectorStore(faiss_index=faiss_index)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    index = VectorStoreIndex.from_documents(
        documents, storage_context=storage_context, embed_model=embed_model
    )
    index.storage_context.persist()
