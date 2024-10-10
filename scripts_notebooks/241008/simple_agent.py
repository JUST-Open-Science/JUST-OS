from llama_index.core import VectorStoreIndex, load_index_from_storage, StorageContext
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.faiss import FaissVectorStore
from openai import Client

from tqdm import tqdm


MODEL = "mistralai/Mistral-Nemo-Instruct-2407"

if __name__ == "__main__":
    client = Client(base_url="http://localhost:8000/v1", api_key="EMPTY")

    embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")

    vector_store = FaissVectorStore.from_persist_dir("./storage")
    storage_context = StorageContext.from_defaults(
        vector_store=vector_store, persist_dir="./storage"
    )
    index = load_index_from_storage(
        storage_context=storage_context, embed_model=embed_model
    )

    retriever = index.as_retriever(similarity_top_k=3)
    nodes = retriever.retrieve("What is preregistration and why is it important?")

    prompt_template = """
Context items are below:
```
{context_items}
```
Given the context information and not prior knowledge, answer the query.
Query: {query}
    """

    context = "\n\n".join(
        f"### Context item {idx}\n{node.text}"
        for idx, node in enumerate(nodes, start=1)
    )

    queries = [
        "What is preregistration and why is it important?",
        "How do I preregister my longitudinal research?",
        "How do I preregister qualitative research?",
        "Where can I preregister my research?",
        "How is preregistration different from registered report?",
        "How is preregistration different from a registered clinical trial?",
        "Will people find my preregistration?",
        "What is open access and what are advantages and disadvantages?",
        "How can I make sure nobody misuses my openly available data?",
        "What are the best platforms and tools for sharing research data openly?",
        "How does open access publishing impact the dissemination and citation of research?",
        "What are the legal and ethical considerations in sharing human subject data?",
        "How does open science reshape the future of interdisciplinary and collaborative research?",
    ]

    for query in tqdm(queries):
        prompt = prompt_template.format(context_items=context, query=query)

        response = client.chat.completions.create(
            model=MODEL, messages=[{"role": "user", "content": prompt}], temperature=0.3
        )
        print("-QUERY----------------------------")
        print(query)
        print("-PROMPT---------------------------")
        print(prompt)
        print("-RESPONSE-------------------------")
        print(response.choices[0].message.content)

