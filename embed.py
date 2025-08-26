import re
from datetime import datetime
from pathlib import Path

import faiss
import pandas as pd
from llama_index.core import Document, Settings, StorageContext, VectorStoreIndex
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.faiss import FaissVectorStore

from config import settings as justos_settings

REFERENCE_PATTERN = re.compile(r"\[(\d+)\]")


def cleanup_markdown(text):
    return REFERENCE_PATTERN.sub("", text)


if __name__ == "__main__":
    Settings.chunk_size = justos_settings.CHUNK_SIZE
    datadir = Path("data")

    metadata = pd.read_csv(justos_settings.URL_JUST_OS_DB).set_index("doi_hash")

    markdown_files = list(datadir.joinpath("processed/markdown").glob("**/*.md"))
    excluded_metadata_keys = set(metadata.columns).difference(("title",))

    documents = [
        Document(
            text=cleanup_markdown(mdf.read_text(encoding="utf-8")),
            metadata=metadata.loc[mdf.stem].to_dict(),
            text_template="{content}",
            excluded_llm_metadata_keys=excluded_metadata_keys,
            excluded_embed_metadata_keys=excluded_metadata_keys,
        )
        for mdf in markdown_files
        if mdf.stem in metadata.index
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

    index.storage_context.persist(
        f"data/processed/vs_latest_{justos_settings.EMBEDDING_MODEL.split('/')[-1]}"
    )
