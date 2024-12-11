import os
import sys
from rich import print as rprint
from rich import print_json
import schema
import json
from typing import Dict, Any

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from griptape.configs import Defaults
from griptape.rules.json_schema_rule import JsonSchemaRule
from griptape.structures import Agent
from griptape.configs.drivers import (
    OpenAiDriversConfig,
    AnthropicDriversConfig,
    GoogleDriversConfig,
    CohereDriversConfig,
)
from griptape.drivers import (
    OpenAiChatPromptDriver,
    AnthropicPromptDriver,
    GooglePromptDriver,
    CoherePromptDriver,
)
from griptape.tools import DateTimeTool, WebSearchTool
from dotenv import load_dotenv
from artifact.artifact_agent_rules import ArtifactAgent
from drivers.serper_web_search_driver import SerperWebSearchDriver
from griptape.utils import Chat

from griptape.rules import Rule, Ruleset


load_dotenv()

# Configure the OpenAI driver
Defaults.drivers_config = OpenAiDriversConfig(
    prompt_driver=OpenAiChatPromptDriver(model="gpt-4o-mini")
)

# Defaults.drivers_config = AnthropicDriversConfig(
#     AnthropicPromptDriver(
#         model="claude-3-5-20240620", api_key=os.getenv("ANTHROPIC_API_KEY")
#     )
# )

# Defaults.drivers_config = GoogleDriversConfig(
#     GooglePromptDriver(model="gemini-pro", api_key=os.getenv("GOOGLE_API_KEY"))
# )

# Defaults.drivers_config = CohereDriversConfig(
#     api_key=os.getenv("COHERE_API_KEY"),
# )


web_search_tool = WebSearchTool(
    web_search_driver=SerperWebSearchDriver(api_key=os.getenv("SERPER_API_KEY"))
)


text_response_schema = schema.Schema(
    {"type": "text", "content": str, "sequence_number": int}
)

# This schema defines what an artifact looks like when one is needed.
artifact_response_schema = schema.Schema(
    {
        "type": "artifact",
        "id": str,
        "content": str,
        "artifact_type": str,
        "language": schema.Or(str, None),
        "title": schema.Or(str, None),
        "sequence_number": int,
    }
)

# Our main chat response schema now focuses just on the elements and whether artifacts are present.
chat_response_schema = schema.Schema(
    {
        "stream_elements": schema.And(
            [schema.Or(text_response_schema, artifact_response_schema)],
            # This ensures we always have at least one text response
            lambda elements: any(elem.get("type") == "text" for elem in elements),
            # This ensures our sequence numbers are in order
            lambda elements: all(
                elements[i]["sequence_number"] == i + 1 for i in range(len(elements))
            ),
        ),
        "has_artifacts": bool,
    }
).json_schema("Chat Response Format")


chat_ruleset = Ruleset(
    name="Chat response ruleset",
    rules=[
        Rule(
            """You MUST structure your responses exactly as follows:

            For responses containing code:
            1. Start with a text element explaining what you will do
            2. Create an artifact for the code with:
               - A descriptive title
               - Proper language tag
               - Clear comments explaining the code
               - The complete code implementation
            3. End with a text element explaining the code and next steps

            CRITICAL RULES:
            - NEVER include code blocks (```) in text responses
            - Text responses are for explanations only
            - Each distinct code file/component must be its own artifact
            - Code MUST be in artifacts, not in text
            - Every response must start with a text element
            - Artifacts must be used for code longer than 1 line

            Response Format:
            {
                "stream_elements": [
                    {
                        "type": "text",
                        "content": "Let me create a program that...",
                        "sequence_number": 1
                    },
                    {
                        "type": "artifact",
                        "id": "unique-id",
                        "content": "# Code goes here...",
                        "artifact_type": "code",
                        "language": "python",
                        "title": "Clear Title",
                        "sequence_number": 2
                    },
                    {
                        "type": "text",
                        "content": "This code demonstrates...",
                        "sequence_number": 3
                    }
                ],
                "has_artifacts": true
            }

            For simple text responses:
            {
                "stream_elements": [
                    {
                        "type": "text",
                        "content": "Your response here...",
                        "sequence_number": 1
                    }
                ],
                "has_artifacts": false
            }"""
        ),
        JsonSchemaRule(chat_response_schema),
    ],
)
agent = Agent(rulesets=[chat_ruleset], stream=True)

Chat(agent).start()
