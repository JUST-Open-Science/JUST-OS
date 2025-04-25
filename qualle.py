import logging
import os

from openai import OpenAI

import reference_processor
from openscholar import generation_instance_prompts_w_references, system_prompt
from query_processor import QueryProcessor

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class Qualle:
    def __init__(self, config, chat_manager, embed_model, retriever):
        self.config = config
        self.chat_manager = chat_manager
        self.system_prompt = system_prompt
        self.prompt_template = generation_instance_prompts_w_references
        self._embed_model = embed_model
        self._retriever = retriever

        # Initialize OpenAI client
        self.client = OpenAI(
            api_key=os.getenv("RUGLLM_API_KEY"), base_url=self.config["base_url"]
        )

        # Initialize query processor
        self.query_processor = QueryProcessor(self.client, config)

    def post_process_response(self, raw_response: str) -> str:
        response = raw_response
        if "[Response_Start]" in response:
            response = response.split("[Response_Start]", 1)[1]
        if "[Response_End]" in response:
            response = response.split("[Response_End]")[0]
        return response

    def get_response(self, query, chat_id):
        logger.debug("Starting response generation for chat_id: %s", chat_id)
        conversation_history = self.chat_manager.get_history(chat_id)
        logger.debug("Retrieved conversation history for chat_id: %s", chat_id)

        if len(conversation_history):
            yield {"status": "in-progress", "message": "Reformulating question"}
            query = self.query_processor.rephrase_query(query, conversation_history)

        yield {"status": "in-progress", "message": "Finding relevant sources"}
        logger.debug("Retrieving relevant nodes for query")
        nodes = self._retriever.retrieve(query)
        context = reference_processor.context_from_nodes(nodes)
        prompt = self.prompt_template.format(context_items=context, query=query)

        history_openai_format = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt},
        ]

        yield {"status": "in-progress", "message": "Generating response"}

        response = self.client.chat.completions.create(
            messages=history_openai_format,
            model=self.config["citation_model"],
            temperature=self.config.get("temperature", 0.3),
        )

        message = response.choices[0].message.content
        processed_message = self.post_process_response(message)
        html_message, used_refs = reference_processor.process_markdown_with_references(
            processed_message, nodes
        )

        self.chat_manager.add_message(chat_id, {"role": "user", "content": query})
        self.chat_manager.add_message(
            chat_id, {"role": "assistant", "content": processed_message}
        )

        yield {
            "status": "complete",
            "message": html_message,
            "metadata": {
                "sources": reference_processor.references_from_nodes(nodes, used_refs)
            },
        }
