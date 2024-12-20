import os

import gradio as gr
import yaml
from dotenv import load_dotenv
from llama_index.core import StorageContext, load_index_from_storage
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.faiss import FaissVectorStore
from openai import OpenAI

from openscholar import generation_instance_prompts_w_references, system_prompt

load_dotenv()


# Load config from YAML file
with open("config.yaml", "r") as config_file:
    CONFIG = yaml.safe_load(config_file)


def context_from_nodes(nodes):
    return "\n".join(
        f"[{idx}] Title: {node.metadata['Title']} Text: {' '.join(node.text.split())}"
        for idx, node in enumerate(nodes)
    )


def references_from_nodes(nodes):
    return "\n".join(
        f"[{idx}] {node.metadata['Provider/Creators']} ({node.metadata['Timestamp']}). {node.metadata['Title']}. {node.metadata['URL/DOI (please check DOI by collating DOI at the end of https://doi.org/ )']}"
        for idx, node in enumerate(nodes)
    )


def post_process_response(raw_response: str) -> str:
    response = raw_response
    if "[Response_Start]" in response:
        response = response.split("[Response_Start]", 1)[1]
    if "[Response_End]" in response:
        response = response.split("[Response_End]")[0]
    return response

class RagWrapper:
    def __init__(self, client, system_prompt, retriever):
        self.client = client
        self.system_prompt = system_prompt
        self.retriever = retriever

        self.prompt_template = generation_instance_prompts_w_references

    def predict(self, query, history):
        nodes = self.retriever.retrieve(query)
        context = context_from_nodes(nodes)
        prompt = self.prompt_template.format(context_items=context, query=query)

        history_openai_format = []
        history_openai_format.append({"role": "system", "content": self.system_prompt})
        history_openai_format.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=CONFIG["model"],
            messages=history_openai_format,
            temperature=CONFIG.get("temperature", 0.3),
            stream=True,
        )

        partial_message = ""
        for chunk in response:
            if chunk.choices[0].delta.content is not None:
                partial_message = partial_message + chunk.choices[0].delta.content
                yield post_process_response(partial_message)

        yield post_process_response(partial_message) + "\n\n" + references_from_nodes(nodes)


if __name__ == "__main__":
    client = OpenAI(
        api_key=os.getenv("RUGLLM_API_KEY"), base_url=CONFIG["base_url"]
    )

    embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")

    persist_dir = "data/interim/vs_241218_bge-small-en-v1.5"
    vector_store = FaissVectorStore.from_persist_dir(persist_dir)
    storage_context = StorageContext.from_defaults(
        vector_store=vector_store, persist_dir=persist_dir
    )
    index = load_index_from_storage(
        storage_context=storage_context, embed_model=embed_model
    )

    rag_wrapper = RagWrapper(
        client, system_prompt, index.as_retriever(similarity_top_k=7)
    )
    system_prompt = (
        "You are a helpful AI assistant for scientific literature review. "
        "Please carefully follow user's instruction and help them to understand the most recent papers."
    )

    embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")

    persist_dir = "data/interim/vs_241218_bge-small-en-v1.5"
    vector_store = FaissVectorStore.from_persist_dir(persist_dir)
    storage_context = StorageContext.from_defaults(
        vector_store=vector_store, persist_dir=persist_dir
    )
    index = load_index_from_storage(
        storage_context=storage_context, embed_model=embed_model
    )

    rag_wrapper = RagWrapper(
        client, system_prompt, index.as_retriever(similarity_top_k=7)
    )

    gr.ChatInterface(
        rag_wrapper.predict,
        title="JUST-OS",
        examples=[
            "What is preregistration and why is it important?",
            "Where can I preregister my research?",
            "How does open science reshape the future of interdisciplinary and collaborative research?",
        ],
    ).queue().launch(show_api=False, server_port=CONFIG["server_port"])
