import json
from pathlib import Path

import faiss
import pandas as pd
from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.faiss import FaissVectorStore

from llama_index.core import Settings

if __name__ == "__main__":
    Settings.chunk_size = 350
    datadir = Path("data")

    identifier_column = "JUST-OS internal identifier"

    forrt_data = (
        pd.read_excel(datadir.joinpath("raw/forrt_db.xlsx"))
        .dropna(subset=identifier_column)
        .set_index(identifier_column)
    )

    markdown_files = datadir.joinpath("processed/markdown").glob("*.md")
    excluded_metadata_keys = set(forrt_data.columns).difference(("Title",))

    documents = [
        Document(
            text=mdf.read_text(encoding="utf-8"),
            metadata=json.loads(forrt_data.loc[int(mdf.stem)].to_json()),
            text_template="{content}",
            excluded_llm_metadata_keys=excluded_metadata_keys,
            excluded_embed_metadata_keys=excluded_metadata_keys,
        )
        for mdf in markdown_files
    ]

    faiss_index = faiss.IndexFlatL2(384)

    embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")

    vector_store = FaissVectorStore(faiss_index=faiss_index)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    index = VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context,
        embed_model=embed_model,
        show_progress=True,
    )
    index.storage_context.persist("data/interim/vs_241218_bge-small-en-v1.5")
