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

VALID_LANGUAGES = [
    "python",
    "javascript",
    "typescript",
    "java",
    "c",
    "cpp",
    "csharp",
    "go",
    "rust",
    "swift",
    "kotlin",
    "ruby",
    "php",
    "bash",
    "powershell",
    "sql",
    "r",
    "matlab",
    "scala",
    "perl",
    "html",
    "css",
]

# Define the artifact types and their requirements
ARTIFACT_TYPES = {
    "code": {"required_fields": ["language"], "allowed_languages": VALID_LANGUAGES},
    "text/markdown": {"required_fields": [], "allowed_languages": []},
    "svg": {"required_fields": [], "allowed_languages": ["svg"]},
    "mermaid": {"required_fields": [], "allowed_languages": ["mermaid"]},
    "html": {"required_fields": [], "allowed_languages": ["html"]},
    "react": {"required_fields": [], "allowed_languages": ["jsx", "tsx"]},
}

text_response_schema = schema.Schema(
    {"type": "text", "content": str, "sequence_number": int}
)


def validate_artifact_type(artifact_dict):
    artifact_type = artifact_dict.get("artifact_type")
    if artifact_type not in ARTIFACT_TYPES:
        raise schema.SchemaError(f"Invalid artifact type: {artifact_type}")

    # Validate required fields
    required_fields = ARTIFACT_TYPES[artifact_type]["required_fields"]
    for field in required_fields:
        if not artifact_dict.get(field):
            raise schema.SchemaError(
                f"Missing required field for {artifact_type}: {field}"
            )

    # Validate language if present
    if "language" in artifact_dict:
        allowed_languages = ARTIFACT_TYPES[artifact_type]["allowed_languages"]
        if artifact_dict["language"] not in allowed_languages:
            raise schema.SchemaError(
                f"Invalid language for {artifact_type}: {artifact_dict['language']}"
            )

    return True


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
        schema.Optional("metadata"): dict,
    },
    validate_artifact_type,
)

# Our main chat response schema now focuses just on the elements and whether artifacts are present.
chat_response_schema = schema.Schema(
    {
        "stream_elements": schema.And(
            [schema.Or(text_response_schema, artifact_response_schema)],
            lambda elements: any(elem.get("type") == "text" for elem in elements),
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

    For responses containing markdown documents:
    1. Start with a text element introducing the document
    2. Create an artifact with:
       - artifact_type: "text/markdown"
       - language: null
       - A descriptive title
       - The complete markdown content
    3. End with a text element summarizing key points

    CRITICAL RULES:
    - NEVER include code blocks (```) in text responses
    - Text responses are for explanations only
    - Each distinct code file/component must be its own artifact
    - Code MUST be in artifacts, not in text
    - Every response must start with a text element
    - Artifacts must be used for code longer than 1 line
    - NEVER include quotation marks in any response
    - Use text/markdown artifact type for documents and memos

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
                "artifact_type": "text/markdown",
                "language": null,
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
