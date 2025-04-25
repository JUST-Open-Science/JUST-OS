import json
import logging

logger = logging.getLogger(__name__)


class QueryProcessor:
    def __init__(self, client, config):
        self.client = client
        self.config = config

    def rephrase_query(self, query, chat_history):
        prompt = "Given the following dialogue history:\n"
        for message in chat_history:
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
            messages=history_openai_format,
            model=self.config["general_model"],
            temperature=self.config.get("temperature_general", 0.3),
            tools=tools,
            tool_choice=tool_choice,
        )

        reformulated = json.loads(
            response.choices[0].message.tool_calls[0].function.arguments
        )["reformulated_query"]

        return reformulated
