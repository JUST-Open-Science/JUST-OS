from config import settings as justos_settings

from pathlib import Path

import faiss
import pandas as pd
from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.faiss import FaissVectorStore

from llama_index.core import Settings

from datetime import datetime

if __name__ == "__main__":
    Settings.chunk_size = justos_settings.CHUNK_SIZE
    datadir = Path("data")

    # identifier_column = "JUST-OS internal identifier"
    metadata = pd.read_csv(datadir / "processed" / "just-os_db.csv").set_index(
        "doi_hash"
    )

    markdown_files = list(datadir.joinpath("processed/markdown").glob("**/*.md"))
    excluded_metadata_keys = set(metadata.columns).difference(("title",))

    documents = [
        Document(
            text=mdf.read_text(encoding="utf-8"),
            metadata=metadata.loc[mdf.stem].to_dict(),
            text_template="{content}",
            excluded_llm_metadata_keys=excluded_metadata_keys,
            excluded_embed_metadata_keys=excluded_metadata_keys,
        )
        for mdf in markdown_files
    ]

    embed_model = HuggingFaceEmbedding(model_name=justos_settings.EMBEDDING_MODEL)
    probe = embed_model.get_text_embedding("Why is the sky blue?")
    faiss_index = faiss.IndexFlatL2(len(probe))

    vector_store = FaissVectorStore(faiss_index=faiss_index)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    index = VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context,
        embed_model=embed_model,
        show_progress=True,
    )
    index.storage_context.persist(
        f"data/processed/vs_{datetime.now().strftime('%y%m%d')}_{justos_settings.EMBEDDING_MODEL.split('/')[-1]}"
    )

