# rag_service.py
import os
from llama_index.core import StorageContext, load_index_from_storage
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.faiss import FaissVectorStore
from openai import OpenAI
from openscholar import generation_instance_prompts_w_references, system_prompt
from chat_manager import ChatManager

from bs4 import BeautifulSoup
import re

import markdown

from threading import Lock

import json
import html

import logging

logging.basicConfig(
    # level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


CREATOR_KEY = "Provider/Creators"
TIMESTAMP_KEY = "Timestamp"
TITLE_KEY = "Title"
URL_DOI_KEY = (
    "URL/DOI (please check DOI by collating DOI at the end of https://doi.org/ )"
)


class Qualle:
    _init_lock = Lock()
    _retrieve_lock = Lock()
    _retriever = None
    _embed_model = None

    @classmethod
    def initialize(cls, config):
        """Initialize the static components once"""
        with cls._init_lock:
            if cls._retriever is None:
                logger.debug("Initializing static components")
                cls._embed_model = HuggingFaceEmbedding(
                    model_name=config["embedding_model"]
                )
                persist_dir = config["vector_store"]
                vector_store = FaissVectorStore.from_persist_dir(persist_dir)
                storage_context = StorageContext.from_defaults(
                    vector_store=vector_store, persist_dir=persist_dir
                )
                index = load_index_from_storage(
                    storage_context=storage_context, embed_model=cls._embed_model
                )
                cls._retriever = index.as_retriever(similarity_top_k=5)

    def __init__(self, config, chat_manager: ChatManager):
        # Initialize static components
        Qualle.initialize(config)

        self.config = config
        self.client = OpenAI(
            api_key=os.getenv("RUGLLM_API_KEY"), base_url=self.config["base_url"]
        )
        self.system_prompt = system_prompt
        self.prompt_template = generation_instance_prompts_w_references
        self.chat_manager = chat_manager

    def _init_client(self):
        return

    def context_from_nodes(self, nodes):
        return "\n".join(
            f"[{idx}] Title: {node.metadata[TITLE_KEY]} Text: {' '.join(node.text.split())}"
            for idx, node in enumerate(nodes)
        )

    def process_markdown_with_references(self, markdown_text, references_nodes):
        """Convert markdown to HTML and add clickable references with tooltips"""
        # First convert markdown to HTML
        html_text = markdown.markdown(markdown_text)
        
        # Parse the HTML
        soup = BeautifulSoup(html_text, 'html.parser')
        
        # Find all reference patterns like [1], [2], etc.
        reference_pattern = r'\[(\d+)\]'
        
        # Get all text nodes
        text_nodes = soup.find_all(text=True)
        
        for text in text_nodes:
            if re.search(reference_pattern, text):
                new_text = text
                for match in re.finditer(reference_pattern, text):
                    ref_num = match.group(1)
                    ref_idx = int(ref_num)
                    
                    if ref_idx < len(references_nodes):
                        # Get reference details
                        ref_node = references_nodes[ref_idx]
                        
                        # Create reference data
                        reference_data = {
                            "title": ref_node.metadata[TITLE_KEY],
                            "authors": ref_node.metadata[CREATOR_KEY],
                            "year": ref_node.metadata[TIMESTAMP_KEY],
                            "url": ref_node.metadata[URL_DOI_KEY],
                            "text": html.escape(ref_node.text),
                        }

                        # Create JSON string and escape special characters for HTML safety
                        data_string = json.dumps(reference_data, ensure_ascii=True, 
                                               separators=(',', ':'))
                        # HTML escape the entire data string for safe attribute insertion
                        escaped_data_string = html.escape(data_string, quote=True)
                        
                        # Create the reference link with data attributes
                        reference_html = (
                            f'<a href="#" class="reference-link" '
                            f'data-reference="{escaped_data_string}">'
                            f'[{ref_num}]'
                            f'</a>'
                        )

                        logger.debug(f"[{ref_num}]: {ref_node.text}")
                        logger.debug(f"[{ref_num}]: {data_string}")
                        
                        new_text = new_text.replace(match.group(0), reference_html)
                
                # Replace the text node with the new HTML
                text.replace_with(BeautifulSoup(new_text, 'html.parser'))
        
        return str(soup)

    def references_from_nodes(self, nodes):
        return "\n".join(
            f"[{idx}] {node.metadata[CREATOR_KEY]} ({node.metadata[TIMESTAMP_KEY]}). "
            f"{node.metadata[TITLE_KEY]}. {node.metadata[URL_DOI_KEY]}"
            for idx, node in enumerate(nodes)
        )

    def post_process_response(self, raw_response: str) -> str:
        response = raw_response
        if "[Response_Start]" in response:
            response = response.split("[Response_Start]", 1)[1]
        if "[Response_End]" in response:
            response = response.split("[Response_End]")[0]
        return response

    def rephrase_query(self, query, chat_id):
        prompt = "Given the following dialogue history:\n"
        for message in self.chat_manager.get_history(chat_id):
            prompt += f"Role: {message['role']}\nContent: {message['content']}\n"
        prompt += f"""

You should reformulate a new question by the user in such a way that it makes sense in isolation.
As an example, if a user follows up a question about open science with a question like "Does it also have disadvantages?",
a proper reformulation would be "Does Open Science also have disadvantages?"
Now reformulate the following question such that it makes sense in isolation:\n{query}"""

        history_openai_format = [
            {"role": "user", "content": prompt},
        ]

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "structure_output",
                    "description": "Send structured output back to the user",
                    "strict": True,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "reformulated_query": {"type": "string"},
                        },
                        "required": ["reformulated_query"],
                        "additionalProperties": False,
                    },
                    "additionalProperties": False,
                },
            }
        ]
        tool_choice = {"type": "function", "function": {"name": "structure_output"}}

        response = self.client.chat.completions.create(
            model=self.config["general_model"],
            messages=history_openai_format,
            temperature=self.config.get("temperature_general", 0.3),
            tools=tools,
            tool_choice=tool_choice,
        )

        reformulated = json.loads(
            response.choices[0].message.tool_calls[0].function.arguments
        )["reformulated_query"]

        print(reformulated)

        return reformulated

    def get_response(self, query, chat_id):
        logger.debug("Starting response generation for chat_id: %s", chat_id)
        conversation_history = self.chat_manager.get_history(chat_id)
        logger.debug("Retrieved conversation history for chat_id: %s", chat_id)

        if len(conversation_history):
            yield {"status": "in-progress", "message": "Reformulating question"}
            query = self.rephrase_query(query, chat_id)

        yield {"status": "in-progress", "message": "Finding relevant sources"}
        logger.debug("Retrieving relevant nodes for query")
        with self._retrieve_lock:
            nodes = self._retriever.retrieve(query)
        context = self.context_from_nodes(nodes)
        prompt = self.prompt_template.format(context_items=context, query=query)

        history_openai_format = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt},
        ]

        yield {"status": "in-progress", "message": "Generating response"}

        response = self.client.chat.completions.create(
            model=self.config["citation_model"],
            messages=history_openai_format,
            temperature=self.config.get("temperature", 0.3),
        )

        message = response.choices[0].message.content
        processed_message = self.post_process_response(message)
        html_message = self.process_markdown_with_references(processed_message, nodes)

        self.chat_manager.add_message(chat_id, {"role": "user", "content": query})
        self.chat_manager.add_message(
            chat_id, {"role": "assistant", "content": processed_message}
        )

        yield {
            "status": "complete",
            "message": html_message,
            "metadata": {"sources": self.references_from_nodes(nodes)},
        }
