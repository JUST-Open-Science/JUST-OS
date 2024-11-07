import os

import gradio as gr
import yaml
from dotenv import load_dotenv
from llama_index.indices.managed.bge_m3 import BGEM3Index
from openai import OpenAI

load_dotenv()



# Load config from YAML file
with open("config.yaml", "r") as config_file:
    CONFIG = yaml.safe_load(config_file)


def context_from_nodes(nodes):
    return "\n\n".join(
        f"### Context item {idx}\n{node.text}"
        for idx, node in enumerate(nodes, start=1)
    )


class RagWrapper:

    def __init__(self, client, system_prompt, retriever):
        self.client = client
        self.system_prompt = system_prompt
        self.retriever = retriever

        self.prompt_template = """
Context items are below:
```
{context_items}
```
Given the context information, answer the query.
Do not base your answer on information outside of the provided context. If the provided context does not contain any relevant information, reply with something along the lines of "Sorry, I can't help you with that."
In your answer, don't mention term like 'context' or 'context item' when referring to the items above. Example: rather than "Based on the provided context ...", say "Based on my knowledge ...".
Query: {query}
    """

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
                yield partial_message


if __name__ == "__main__":
    client = OpenAI(
        api_key=os.getenv("LITELLM_PROXY_API_KEY"), base_url=CONFIG["base_url"]
    )
    system_prompt = "You are JUST-OS, a useful assistant for all things Open Science."

    index = BGEM3Index.load_from_disk(
        "data/processed/storage_m3", weights_for_different_modes=[1.0, 0.3, 0.0]
    )

    rag_wrapper = RagWrapper(client, system_prompt, index.as_retriever())

    description = """
NB: this is a rough development version.

The bot is only using parts of the documents listed [here](https://docs.google.com/document/d/1RF-yJG7b_4D-wGnvDu86t8kHXTkvKJrd09HiNnXgNX4/edit).

You can not have \"multi-turn\" conversations with the bot yet, each message you sent is treated as the start of a new conversation.
"""

    gr.ChatInterface(
        rag_wrapper.predict,
        title="JUST-OS",
        examples=[
            "What is preregistration and why is it important?",
            "Where can I preregister my research?",
            "How does open science reshape the future of interdisciplinary and collaborative research?",
        ],
        description=description,
    ).queue().launch(show_api=False, server_port=CONFIG["server_port"])
