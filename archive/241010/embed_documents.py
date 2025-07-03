import json

import faiss
from llama_index.core import Document, StorageContext, VectorStoreIndex, Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.faiss import FaissVectorStore

from llama_index.indices.managed.bge_m3 import BGEM3Index


Settings.chunk_size = 8192

if __name__ == "__main__":
    with open("../data/classified_chunks.json", encoding="utf-8") as f:
        chunks = json.load(f)
    selected_chunks = [chunk["text"] for chunk in chunks if chunk["is_useful"]]

    documents = [Document(text=chunk) for chunk in selected_chunks]

    index = BGEM3Index.from_documents(documents)

    index.persist("storage_m3")
