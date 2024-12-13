import os
from typing import Dict, Any
import schema
from griptape.configs import Defaults
from griptape.structures import Agent
from griptape.configs.drivers import OpenAiDriversConfig
from griptape.drivers import OpenAiChatPromptDriver
from griptape.rules import Rule, Ruleset


class ArtifactAgent(Agent):
    """An Agent specialized for handling artifacts with specific schema validation."""

    def __init__(self, **kwargs):
        # Define constants
        self.VALID_LANGUAGES = [
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

        self.ARTIFACT_TYPES = {
            "code": {
                "required_fields": ["language"],
                "allowed_languages": self.VALID_LANGUAGES,
            },
            "markdown": {"required_fields": [], "allowed_languages": []},
            "svg": {"required_fields": [], "allowed_languages": ["svg"]},
            "mermaid": {"required_fields": [], "allowed_languages": ["mermaid"]},
            "html": {"required_fields": [], "allowed_languages": ["html"]},
            "react": {"required_fields": [], "allowed_languages": ["jsx", "tsx"]},
        }

        # Set up schemas and validation
        chat_response_schema = self._create_chat_response_schema()
        chat_ruleset = self._create_chat_ruleset(chat_response_schema)

        # Initialize the parent Agent class
        super().__init__(rulesets=[chat_ruleset], **kwargs)

    def _validate_artifact_type(self, artifact_dict: Dict[str, Any]) -> bool:
        artifact_type = artifact_dict.get("artifact_type")
        if artifact_type not in self.ARTIFACT_TYPES:
            raise schema.SchemaError(f"Invalid artifact type: {artifact_type}")

        required_fields = self.ARTIFACT_TYPES[artifact_type]["required_fields"]
        for field in required_fields:
            if not artifact_dict.get(field):
                raise schema.SchemaError(
                    f"Missing required field for {artifact_type}: {field}"
                )

        if "language" in artifact_dict:
            allowed_languages = self.ARTIFACT_TYPES[artifact_type]["allowed_languages"]
            if artifact_dict["language"] not in allowed_languages:
                raise schema.SchemaError(
                    f"Invalid language for {artifact_type}: {artifact_dict['language']}"
                )

        return True

    def _create_chat_response_schema(self) -> schema.Schema:
        text_response_schema = schema.Schema(
            {"type": "text", "content": str, "sequence_number": int}
        )

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
            self._validate_artifact_type,
        )

        return schema.Schema(
            {
                "stream_elements": schema.And(
                    [schema.Or(text_response_schema, artifact_response_schema)],
                    lambda elements: any(
                        elem.get("type") == "text" for elem in elements
                    ),
                    lambda elements: all(
                        elements[i]["sequence_number"] == i + 1
                        for i in range(len(elements))
                    ),
                ),
                "has_artifacts": bool,
            }
        ).json_schema("Chat Response Format")

    Defaults.drivers_config = OpenAiDriversConfig(
        OpenAiChatPromptDriver(
            model="gpt-4o-mini",
            api_key=os.getenv("OPENAI_API_KEY"),
            seed=42,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "strict": True,
                    "name": "Chat Response Format",
                    "schema": _create_chat_response_schema,
                },
            },
        )
    )

    def _create_chat_ruleset(self, chat_response_schema: schema.Schema) -> Ruleset:
        return Ruleset(
            name="Chat response ruleset",
            rules=[
                Rule(self._get_response_format_rule()),
                Rule(chat_response_schema),
            ],
        )

    def _get_response_format_rule(self) -> str:
        return """You MUST structure your responses exactly as follows:

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
       - artifact_type: "markdown"
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
    - Use markdown artifact type for documents and memos

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
                "artifact_type": "markdown",
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
