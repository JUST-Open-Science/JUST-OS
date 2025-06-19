import html
import json
import logging
import os
import re

import markdown
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI

from just_os.chat_manager import ChatManager
from just_os.openscholar import generation_instance_prompts_w_references, system_prompt

load_dotenv()

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

NON_OS_RESPONSE = "Sorry, I'm only able to answer questions related to Open Science."


class Qualle:
    def __init__(self, config, chat_manager: ChatManager, embed_model, retriever):
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
        soup = BeautifulSoup(html_text, "html.parser")

        # Find all reference patterns like [1], [2], etc.
        reference_pattern = r"\[(\d+)\]"

        # Get all text nodes and track references in order of appearance
        text_nodes = soup.find_all(text=True)
        used_refs_ordered = []  # Will store refs in order of appearance
        ref_mapping = {}  # Maps old ref numbers to new ones

        # First pass - collect references in order of appearance
        for text in text_nodes:
            for match in re.finditer(reference_pattern, text):
                ref_idx = int(match.group(1))
                if ref_idx < len(references_nodes) and ref_idx not in ref_mapping:
                    used_refs_ordered.append(ref_idx)
                    ref_mapping[ref_idx] = len(
                        used_refs_ordered
                    )  # New number is position + 1

        logger.debug(f"Text: {markdown_text}")
        logger.debug(f"Used refs: {used_refs_ordered}")
        logger.debug(f"Mapping: {ref_mapping}")

        # Second pass - replace references with new numbers
        for text in text_nodes:
            if re.search(reference_pattern, text):
                # Get all matches first to determine their positions
                matches = list(re.finditer(reference_pattern, text))
                # Process the string from right to left to maintain correct positions
                new_text = text

                for match in reversed(matches):
                    old_ref_num = int(match.group(1))
                    start, end = match.span()

                    if old_ref_num in ref_mapping:
                        new_ref_num = ref_mapping[old_ref_num]
                        ref_node = references_nodes[old_ref_num]

                        # Create reference data
                        reference_data = {
                            "title": ref_node.metadata[TITLE_KEY],
                            "authors": ref_node.metadata[CREATOR_KEY],
                            "year": ref_node.metadata[TIMESTAMP_KEY],
                            "url": ref_node.metadata[URL_DOI_KEY],
                            "text": html.escape(ref_node.text),
                        }

                        # Create JSON string and escape special characters for HTML safety
                        data_string = json.dumps(
                            reference_data, ensure_ascii=True, separators=(",", ":")
                        )
                        # HTML escape the entire data string for safe attribute insertion
                        escaped_data_string = html.escape(data_string, quote=True)

                        # Create the reference link with data attributes using new number
                        reference_html = (
                            f'<a href="#" class="reference-link" '
                            f'data-reference="{escaped_data_string}">'
                            f"[{new_ref_num}]"
                            f"</a>"
                        )

                        # Replace this specific reference
                        new_text = new_text[:start] + reference_html + new_text[end:]

                # Replace the text node with the new HTML
                text.replace_with(BeautifulSoup(new_text, "html.parser"))

        return str(soup), used_refs_ordered

    def references_from_nodes(self, nodes, used_refs_ordered=None):
        """Generate reference list from nodes.

        Args:
            nodes: List of reference nodes
            used_refs_ordered: Optional list of reference indices in order of appearance.
                             If None, all references will be included in original order.
        """
        if not used_refs_ordered:
            return "\n".join(
                f"[{idx + 1}] {node.metadata[CREATOR_KEY]} ({node.metadata[TIMESTAMP_KEY]}). "
                f"{node.metadata[TITLE_KEY]}. {node.metadata[URL_DOI_KEY]}"
                for idx, node in enumerate(nodes)
            )

        return "\n".join(
            f"[{idx + 1}] {nodes[ref_idx].metadata[CREATOR_KEY]} ({nodes[ref_idx].metadata[TIMESTAMP_KEY]}). "
            f"{nodes[ref_idx].metadata[TITLE_KEY]}. {nodes[ref_idx].metadata[URL_DOI_KEY]}"
            for idx, ref_idx in enumerate(used_refs_ordered)
        )

    def post_process_response(self, raw_response: str) -> str:
        response = raw_response
        if "[Response_Start]" in response:
            response = response.split("[Response_Start]", 1)[1]
        if "[Response_End]" in response:
            response = response.split("[Response_End]")[0]
        return response

    def classify_query(self, query):
        prompt = f"""You are an Open Science expert.
Classify whether the following query is about Open Science:
"{query}"
Return your answer as a valid JSON object with a single boolean entry "concerns_open_science"
"""

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
                            "concerns_open_science": {"type": "boolean"},
                        },
                        "required": ["concerns_open_science"],
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

        concerns_open_science = json.loads(
            response.choices[0].message.tool_calls[0].function.arguments
        )["concerns_open_science"]

        return concerns_open_science

    def rephrase_query(self, query, chat_id):
        prompt = "Given the following dialogue history:\n"
        for message in self.chat_manager.get_history(chat_id):
            prompt += f"Role: {message['role']}\nContent: {message['content']}\n"
        prompt += f"""

You should reformulate a new question by the user in such a way that it makes sense in isolation.
As an example, if a user follows up a question about open science with a question like "Does it also have disadvantages?",
a proper reformulation would be "Does Open Science also have disadvantages?"
If the question is not related to open science, return the original question.
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

        return reformulated

    def get_response(self, query, chat_id):
        logger.debug("Starting response generation for chat_id: %s", chat_id)
        conversation_history = self.chat_manager.get_history(chat_id)
        logger.debug("Retrieved conversation history for chat_id: %s", chat_id)

        if len(conversation_history):
            yield {"status": "in-progress", "message": "Reformulating question"}
            query = self.rephrase_query(query, chat_id)

        yield {"status": "in-progress", "message": "Classifying question"}
        concerns_open_science = self.classify_query(query)
        if concerns_open_science:
            yield {"status": "in-progress", "message": "Finding relevant sources"}
            logger.debug("Retrieving relevant nodes for query")
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
            html_message, used_refs = self.process_markdown_with_references(
                processed_message, nodes
            )

            self.chat_manager.add_message(chat_id, {"role": "user", "content": query})
            self.chat_manager.add_message(
                chat_id, {"role": "assistant", "content": processed_message}
            )

            yield {
                "status": "complete",
                "message": html_message,
                "metadata": {"sources": self.references_from_nodes(nodes, used_refs)},
            }
        else:
            self.chat_manager.add_message(chat_id, {"role": "user", "content": query})
            self.chat_manager.add_message(
                chat_id, {"role": "assistant", "content": NON_OS_RESPONSE}
            )

            yield {
                "status": "complete",
                "message": markdown.markdown(NON_OS_RESPONSE),
            }
