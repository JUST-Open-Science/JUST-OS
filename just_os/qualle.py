import html
import json
import logging
import os
import re
from typing import Dict, List, Any, Optional, Generator, Union, Tuple

import markdown
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI
from openai.types.chat import ChatCompletion

from config.settings import get_config
from just_os.chat_manager import ChatManager
from just_os.openscholar import generation_instance_prompts_w_references, system_prompt

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Constants for metadata keys
CREATOR_KEY = "creators"
TIMESTAMP_KEY = "timestamp"
TITLE_KEY = "title"
URL_DOI_KEY = "link_to_resource"

# Default response for non-Open Science questions
NON_OS_RESPONSE = "Sorry, I'm only able to answer questions related to Open Science."


class OpenAIClientManager:
    """
    Manages OpenAI client creation and API calls.
    Provides error handling and retry logic.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the OpenAI client manager.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.api_key = os.getenv("RUGLLM_API_KEY")
        if not self.api_key:
            logger.warning("RUGLLM_API_KEY environment variable not set")
            
        self.client = self._create_client()
        
    def _create_client(self) -> Optional[OpenAI]:
        """
        Create an OpenAI client instance.
        
        Returns:
            OpenAI client or None if initialization fails
        """
        try:
            return OpenAI(
                api_key=self.api_key,
                base_url=self.config["BASE_URL"]
            )
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {str(e)}")
            return None
            
    def create_chat_completion(self, 
                              model: str, 
                              messages: List[Dict[str, str]], 
                              temperature: float = 0.3,
                              tools: Optional[List[Dict[str, Any]]] = None,
                              tool_choice: Optional[Dict[str, Any]] = None) -> Optional[ChatCompletion]:
        """
        Create a chat completion with error handling.
        
        Args:
            model: Model name to use
            messages: List of message dictionaries
            temperature: Sampling temperature
            tools: Optional list of tools
            tool_choice: Optional tool choice
            
        Returns:
            ChatCompletion or None if the request fails
        """
        if not self.client:
            logger.error("OpenAI client not initialized")
            return None
            
        try:
            kwargs = {
                "model": model,
                "messages": messages,
                "temperature": temperature
            }
            
            if tools:
                kwargs["tools"] = tools
                
            if tool_choice:
                kwargs["tool_choice"] = tool_choice
                
            return self.client.chat.completions.create(**kwargs)
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            return None


class ReferenceProcessor:
    """
    Handles processing of references in markdown text.
    """
    
    @staticmethod
    def process_markdown_with_references(markdown_text: str, references_nodes: List[Any]) -> Tuple[str, List[int]]:
        """
        Convert markdown to HTML and add clickable references with tooltips.
        
        Args:
            markdown_text: Markdown text with references
            references_nodes: List of reference nodes
            
        Returns:
            Tuple of (HTML text with clickable references, list of used reference indices)
        """
        try:
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
                        ref_mapping[ref_idx] = len(used_refs_ordered)  # New number is position + 1

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

                        if old_ref_num in ref_mapping and old_ref_num < len(references_nodes):
                            new_ref_num = ref_mapping[old_ref_num]
                            ref_node = references_nodes[old_ref_num]

                            # Create reference data
                            reference_data = {
                                "title": ref_node.metadata.get(TITLE_KEY, "Unknown Title"),
                                "authors": ref_node.metadata.get(CREATOR_KEY, "Unknown Author"),
                                "year": ref_node.metadata.get(TIMESTAMP_KEY, "Unknown Year"),
                                "url": ref_node.metadata.get(URL_DOI_KEY, "#"),
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
        except Exception as e:
            logger.error(f"Error processing references: {str(e)}")
            # Return original markdown as HTML if processing fails
            return markdown.markdown(markdown_text), []

    @staticmethod
    def references_from_nodes(nodes: List[Any], used_refs_ordered: Optional[List[int]] = None) -> str:
        """
        Generate reference list from nodes.

        Args:
            nodes: List of reference nodes
            used_refs_ordered: Optional list of reference indices in order of appearance.
                              If None, all references will be included in original order.
                              
        Returns:
            Formatted reference list as a string
        """
        try:
            if not used_refs_ordered:
                return "\n".join(
                    f"[{idx + 1}] {node.metadata.get(CREATOR_KEY, 'Unknown Author')} "
                    f"({node.metadata.get(TIMESTAMP_KEY, 'Unknown Year')}). "
                    f"{node.metadata.get(TITLE_KEY, 'Unknown Title')}. "
                    f"{node.metadata.get(URL_DOI_KEY, '#')}"
                    for idx, node in enumerate(nodes)
                )

            return "\n".join(
                f"[{idx + 1}] {nodes[ref_idx].metadata.get(CREATOR_KEY, 'Unknown Author')} "
                f"({nodes[ref_idx].metadata.get(TIMESTAMP_KEY, 'Unknown Year')}). "
                f"{nodes[ref_idx].metadata.get(TITLE_KEY, 'Unknown Title')}. "
                f"{nodes[ref_idx].metadata.get(URL_DOI_KEY, '#')}"
                for idx, ref_idx in enumerate(used_refs_ordered)
                if ref_idx < len(nodes)
            )
        except Exception as e:
            logger.error(f"Error generating references: {str(e)}")
            return "References could not be generated due to an error."


class Qualle:
    """
    Main RAG service implementation that handles queries and responses.
    """
    
    def __init__(self, config: Dict[str, Any], chat_manager: ChatManager, embed_model, retriever):
        """
        Initialize the Qualle RAG service.
        
        Args:
            config: Configuration dictionary
            chat_manager: Chat manager instance
            embed_model: Embedding model
            retriever: Retriever component
        """
        self.config = config
        self.chat_manager = chat_manager
        self.system_prompt = system_prompt
        self.prompt_template = generation_instance_prompts_w_references
        self._embed_model = embed_model
        self._retriever = retriever

        # Get model names from config
        self.general_model = config["GENERAL_MODEL"]
        self.citation_model = config["CITATION_MODEL"]

        # Initialize OpenAI client manager
        self.client_manager = OpenAIClientManager(config)
        
        # Initialize reference processor
        self.reference_processor = ReferenceProcessor()
        
        logger.debug("Qualle service initialized")

    def context_from_nodes(self, nodes: List[Any]) -> str:
        """
        Format context from retrieved nodes.
        
        Args:
            nodes: List of retrieved nodes
            
        Returns:
            Formatted context string
        """
        try:
            return "\n".join(
                f"[{idx}] Title: {node.metadata.get(TITLE_KEY, 'Unknown Title')} "
                f"Text: {' '.join(node.text.split())}"
                for idx, node in enumerate(nodes)
            )
        except Exception as e:
            logger.error(f"Error formatting context: {str(e)}")
            return ""

    def post_process_response(self, raw_response: str) -> str:
        """
        Extract the actual response from the raw LLM output.
        
        Args:
            raw_response: Raw response from the LLM
            
        Returns:
            Processed response
        """
        try:
            response = raw_response
            if "[Response_Start]" in response:
                response = response.split("[Response_Start]", 1)[1]
            if "[Response_End]" in response:
                response = response.split("[Response_End]")[0]
            return response
        except Exception as e:
            logger.error(f"Error post-processing response: {str(e)}")
            return raw_response

    def classify_query(self, query: str) -> bool:
        """
        Classify whether a query is about Open Science.
        
        Args:
            query: User query
            
        Returns:
            True if the query is about Open Science, False otherwise
        """
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

        response = self.client_manager.create_chat_completion(
            model=self.general_model,
            messages=history_openai_format,
            temperature=self.config.get("TEMPERATURE_GENERAL", 0.3),
            tools=tools,
            tool_choice=tool_choice,
        )
        
        if not response or not response.choices:
            logger.error("Failed to classify query")
            return False

        try:
            concerns_open_science = json.loads(
                response.choices[0].message.tool_calls[0].function.arguments
            )["concerns_open_science"]
            return concerns_open_science
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            logger.error(f"Error parsing classification response: {str(e)}")
            return False

    def rephrase_query(self, query: str, chat_id: str) -> str:
        """
        Rephrase a query based on conversation history.
        
        Args:
            query: User query
            chat_id: Chat session ID
            
        Returns:
            Rephrased query
        """
        # Get conversation history
        conversation_history = self.chat_manager.get_history(chat_id)
        
        # Build prompt
        prompt = "Given the following dialogue history:\n"
        for message in conversation_history:
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

        response = self.client_manager.create_chat_completion(
            model=self.general_model,
            messages=history_openai_format,
            temperature=self.config.get("TEMPERATURE_GENERAL", 0.3),
            tools=tools,
            tool_choice=tool_choice,
        )
        
        if not response or not response.choices:
            logger.warning("Failed to rephrase query, using original")
            return query

        try:
            reformulated = json.loads(
                response.choices[0].message.tool_calls[0].function.arguments
            )["reformulated_query"]
            return reformulated
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            logger.error(f"Error parsing reformulation response: {str(e)}")
            return query

    def get_response(self, query: str, chat_id: str) -> Generator[Dict[str, Any], None, None]:
        """
        Generate a response to a user query.
        
        Args:
            query: User query
            chat_id: Chat session ID
            
        Yields:
            Response chunks as dictionaries
        """
        logger.debug("Starting response generation for chat_id: %s", chat_id)
        
        try:
            # Get conversation history
            conversation_history = self.chat_manager.get_history(chat_id)
            logger.debug("Retrieved conversation history for chat_id: %s", chat_id)

            # Rephrase query if there's conversation history
            if conversation_history:
                yield {"status": "in-progress", "message": "Reformulating question"}
                query = self.rephrase_query(query, chat_id)
                logger.debug(f"Rephrased query: {query}")

            # Classify query
            yield {"status": "in-progress", "message": "Classifying question"}
            concerns_open_science = self.classify_query(query)
            logger.debug(f"Query classification: {concerns_open_science}")
            
            # Process Open Science queries
            if concerns_open_science:
                # Retrieve relevant sources
                yield {"status": "in-progress", "message": "Finding relevant sources"}
                logger.debug("Retrieving relevant nodes for query")
                nodes = self._retriever.retrieve(query)
                
                if not nodes:
                    logger.warning("No relevant nodes found for query")
                    self.chat_manager.add_message(chat_id, {"role": "user", "content": query})
                    self.chat_manager.add_message(
                        chat_id, 
                        {"role": "assistant", "content": "I couldn't find any relevant information about that topic in Open Science."}
                    )
                    yield {
                        "status": "complete",
                        "message": markdown.markdown("I couldn't find any relevant information about that topic in Open Science."),
                    }
                    return
                
                # Format context and prompt
                context = self.context_from_nodes(nodes)
                prompt = self.prompt_template.format(context_items=context, query=query)

                # Prepare messages for the LLM
                history_openai_format = [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt},
                ]

                # Generate response
                yield {"status": "in-progress", "message": "Generating response"}
                response = self.client_manager.create_chat_completion(
                    model=self.citation_model,
                    messages=history_openai_format,
                    temperature=self.config.get("TEMPERATURE", 0.3),
                )
                
                if not response or not response.choices:
                    logger.error("Failed to generate response")
                    self.chat_manager.add_message(chat_id, {"role": "user", "content": query})
                    self.chat_manager.add_message(
                        chat_id, 
                        {"role": "assistant", "content": "I'm sorry, I encountered an error while generating a response."}
                    )
                    yield {
                        "status": "complete",
                        "message": markdown.markdown("I'm sorry, I encountered an error while generating a response."),
                    }
                    return

                # Process response
                message = response.choices[0].message.content
                processed_message = self.post_process_response(message)
                html_message, used_refs = self.reference_processor.process_markdown_with_references(
                    processed_message, nodes
                )

                # Save conversation history
                self.chat_manager.add_message(chat_id, {"role": "user", "content": query})
                self.chat_manager.add_message(
                    chat_id, {"role": "assistant", "content": processed_message}
                )

                # Return final response
                yield {
                    "status": "complete",
                    "message": html_message,
                    "metadata": {"sources": self.reference_processor.references_from_nodes(nodes, used_refs)},
                }
            else:
                # Handle non-Open Science queries
                self.chat_manager.add_message(chat_id, {"role": "user", "content": query})
                self.chat_manager.add_message(
                    chat_id, {"role": "assistant", "content": NON_OS_RESPONSE}
                )

                yield {
                    "status": "complete",
                    "message": markdown.markdown(NON_OS_RESPONSE),
                }
        except Exception as e:
            logger.error(f"Error in get_response: {str(e)}")
            yield {
                "status": "error",
                "message": markdown.markdown("An unexpected error occurred while processing your request."),
            }
