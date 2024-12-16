from pydantic import BaseModel, Field, validator
from typing import List, Optional, Union, Literal
from enum import Enum
import sys
from rich import print as rprint
import os
from rich import print_json
import json
import schema

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from griptape.structures import Agent, Pipeline
from griptape.drivers import OpenAiChatPromptDriver, AnthropicPromptDriver
from griptape.configs import Defaults
from griptape.rules import Rule, Ruleset, JsonSchemaRule
from griptape.tools import DateTimeTool, WebScraperTool, WebSearchTool
from drivers.serper_web_search_driver import SerperWebSearchDriver
from drivers.jina_web_scraper_driver import JinaWebScraperDriver
from griptape.loaders import WebLoader
from griptape.configs.drivers import OpenAiDriversConfig, AnthropicDriversConfig
from dotenv import load_dotenv
from griptape.tasks import ToolkitTask, PromptTask
from griptape.utils import Chat

from pydantic import BaseModel
from schemas.output_schema import output_schema

load_dotenv()


Defaults.drivers_config = OpenAiDriversConfig(
    OpenAiChatPromptDriver(
        model="gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"), stream=True
    )
)


# Define valid languages as an enum
class ValidLanguage(str, Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    C = "c"
    CPP = "cpp"
    CSHARP = "csharp"
    GO = "go"
    RUST = "rust"
    SWIFT = "swift"
    KOTLIN = "kotlin"
    RUBY = "ruby"
    PHP = "php"
    BASH = "bash"
    POWERSHELL = "powershell"
    SQL = "sql"
    R = "r"
    MATLAB = "matlab"
    SCALA = "scala"
    PERL = "perl"
    HTML = "html"
    CSS = "css"


# Define artifact types
class ArtifactType(str, Enum):
    CODE = "code"
    MARKDOWN = "markdown"
    SVG = "svg"
    MERMAID = "mermaid"
    HTML = "html"
    REACT = "react"
    TEXT = "plaintext"


class TextResponse(BaseModel):
    type: Literal["text"]
    content: str
    sequence_number: int


class ArtifactResponse(BaseModel):
    type: Literal["artifact"]
    id: str
    content: str
    artifact_type: ArtifactType
    language: Optional[str] = None
    title: Optional[str] = None
    sequence_number: int
    metadata: Optional[dict] = None

    @validator("language")
    def validate_language(cls, v, values):
        artifact_type = values.get("artifact_type")
        if artifact_type == ArtifactType.CODE:
            if not v:
                raise ValueError("Language is required for code artifacts")
            if v not in [lang.value for lang in ValidLanguage]:
                raise ValueError(f"Invalid language: {v}")
        elif artifact_type == ArtifactType.SVG:
            if v and v != "svg":
                raise ValueError("SVG artifacts only accept 'svg' as language")
        elif artifact_type == ArtifactType.MERMAID:
            if v and v != "mermaid":
                raise ValueError("Mermaid artifacts only accept 'mermaid' as language")
        elif artifact_type == ArtifactType.HTML:
            if v and v != "html":
                raise ValueError("HTML artifacts only accept 'html' as language")
        elif artifact_type == ArtifactType.REACT:
            if v and v not in ["jsx", "tsx"]:
                raise ValueError(
                    "React artifacts only accept 'jsx' or 'tsx' as language"
                )
        return v


class ChatResponse(BaseModel):
    stream_elements: List[Union[TextResponse, ArtifactResponse]]
    has_artifacts: bool

    @validator("stream_elements")
    def validate_elements(cls, v):
        # Ensure at least one text element exists
        if not any(elem.type == "text" for elem in v):
            raise ValueError("At least one text element is required")

        # Validate sequence numbers are sequential
        if len(v) > 1:
            for i in range(len(v) - 1):
                current = v[i].sequence_number
                next_num = v[i + 1].sequence_number
                if next_num != current + 1:
                    raise ValueError(
                        f"Sequence numbers must be sequential. Found {current} followed by {next_num}"
                    )

        return v

    @validator("has_artifacts")
    def validate_has_artifacts(cls, v, values):
        if "stream_elements" in values:
            actual_has_artifacts = any(
                isinstance(elem, ArtifactResponse) for elem in values["stream_elements"]
            )
            if v != actual_has_artifacts:
                raise ValueError(
                    "has_artifacts must accurately reflect the presence of artifacts"
                )
        return v


pipeline = Pipeline()


task_1 = ToolkitTask(
    "{{args[0]}}",
    tools=[DateTimeTool()],
    id="CHAT_TASK",
    prompt_driver=OpenAiChatPromptDriver(model="gpt-4o-mini", stream=True),
)
task_2 = PromptTask(
    input="""
    Format the following response in a structured format.
#                   You can take the response and structure it in 2 ways: 1. Text 2. Artifacts

#                   For responses containing code:
#     1. Start with a text element explaining what you will do
#     2. Create an artifact for the code with:
#        - A descriptive title
#        - Proper language tag
#        - Clear comments explaining the code
#        - The complete code implementation
#     3. End with a text element explaining the code and next steps

#     For responses containing markdown documents:
#     1. Start with a text element introducing the document
#     2. Create an artifact with:
#        - artifact_type: "markdown"
#        - language: null
#        - A descriptive title
#        - The complete markdown content
#     3. End with a text element summarizing key points

#     CRITICAL RULES:
#     - NEVER include code blocks (```) in text responses
#     - Text responses are for explanations only
#     - Each distinct code file/component must be its own artifact
#     - Code MUST be in artifacts, not in text
#     - Every response must start with a text element
#     - Artifacts must be used for code longer than 1 line
#     - NEVER include quotation marks in any response
#     - Use text/markdown artifact type for documents and memos

Response:
{{parent_output}}
""",
    rules=[JsonSchemaRule(ChatResponse.model_json_schema())],
)

pipeline.add_tasks(task_1, task_2)

output = pipeline.run("what is today's date?")

# Chat(pipeline).start()

# print("JSON output for mert: ")
# print("----------------------")
# print_json(output.output_task.output.value)
# try:
#     ChatResponse.model_validate_json(output.output_task.output.value)
#     print("Validation: ✅")
# except Exception as e:
#     print(f"Validation: ❌: ({str(e)})")

# task_2 = PromptTask(
#     input="""
# You are an AI assistant tasked with generating responses in a specific structured format. Your goal is to process user requests and provide responses that strictly adhere to the given format requirements. Here are your instructions:

# 1. You will receive a user request in the following format:
# <user_request>
# {{ parent_output }}
# </user_request>

# 2. Process the user request and generate an appropriate response. Your response must follow these strict guidelines:

# a) For responses containing code:
#    - Start with a text element explaining what you will do
#    - Create an artifact for the code with:
#      * A descriptive title
#      * Proper language tag
#      * Clear comments explaining the code
#      * The complete code implementation
#    - End with a text element explaining the code and next steps

# b) For responses containing markdown documents:
#    - Start with a text element introducing the document
#    - Create an artifact with:
#      * artifact_type: "text/markdown"
#      * language: null
#      * A descriptive title
#      * The complete markdown content
#    - End with a text element summarizing key points

# 3. Always follow these critical rules:
#    - NEVER include code blocks (```) in text responses
#    - Text responses are for explanations only
#    - Each distinct code file/component must be its own artifact
#    - Code MUST be in artifacts, not in text
#    - Every response must start with a text element
#    - Artifacts must be used for code longer than 1 line
#    - NEVER include quotation marks in any response
#    - Use text/markdown artifact type for documents and memos

# 4. Your response must be structured exactly as follows:

# For responses with artifacts:
# {
#     "stream_elements": [
#         {
#             "type": "text",
#             "content": "Your explanation here...",
#             "sequence_number": 1
#         },
#         {
#             "type": "artifact",
#             "id": "unique-id",
#             "content": "Your code or markdown content here...",
#             "artifact_type": "text/x-python",
#             "language": "python",
#             "title": "Clear Title",
#             "sequence_number": 2
#         },
#         {
#             "type": "text",
#             "content": "Your follow-up explanation here...",
#             "sequence_number": 3
#         }
#     ],
#     "has_artifacts": true
# }

# For simple text responses:
# {
#     "stream_elements": [
#         {
#             "type": "text",
#             "content": "Your response here...",
#             "sequence_number": 1
#         }
#     ],
#     "has_artifacts": false
# }

# 5. Examples of correct response structures:

# Example 1 (with code):
# {
#     "stream_elements": [
#         {
#             "type": "text",
#             "content": "Let me create a Python function that calculates the factorial of a number.",
#             "sequence_number": 1
#         },
#         {
#             "type": "artifact",
#             "id": "factorial-function",
#             "content": "def factorial(n):\n    # Base case: factorial of 0 or 1 is 1\n    if n == 0 or n == 1:\n        return 1\n    # Recursive case: n! = n * (n-1)!\n    else:\n        return n * factorial(n-1)",
#             "artifact_type": "text/x-python",
#             "language": "python",
#             "title": "Factorial Function",
#             "sequence_number": 2
#         },
#         {
#             "type": "text",
#             "content": "This function uses recursion to calculate the factorial. It handles the base cases (0! and 1!) and uses the recursive formula for other numbers.",
#             "sequence_number": 3
#         }
#     ],
#     "has_artifacts": true
# }

# Example 2 (with markdown):
# {
#     "stream_elements": [
#         {
#             "type": "text",
#             "content": "I'll create a markdown document explaining the benefits of regular exercise.",
#             "sequence_number": 1
#         },
#         {
#             "type": "artifact",
#             "id": "exercise-benefits",
#             "content": "# Benefits of Regular Exercise\n\n1. **Improved cardiovascular health**\n   - Strengthens the heart\n   - Lowers blood pressure\n\n2. **Weight management**\n   - Burns calories\n   - Boosts metabolism\n\n3. **Mental health benefits**\n   - Reduces stress and anxiety\n   - Improves mood and self-esteem\n\n4. **Increased energy and stamina**\n   - Enhances overall endurance\n   - Improves sleep quality",
#             "artifact_type": "text/markdown",
#             "language": null,
#             "title": "Benefits of Regular Exercise",
#             "sequence_number": 2
#         },
#         {
#             "type": "text",
#             "content": "This markdown document outlines four key benefits of regular exercise: improved cardiovascular health, weight management, mental health benefits, and increased energy and stamina.",
#             "sequence_number": 3
#         }
#     ],
#     "has_artifacts": true
# }

# Remember to always start with a text element, use artifacts for code and markdown content, and follow the specified format exactly. Process the user request and generate your response accordingly.
# """,
#     id="EXTRACTION_TASK",
#     prompt_driver=OpenAiChatPromptDriver(model="gpt-4o-mini", stream=True),
# )


# task_2 = PromptTask(
#     input="""Format the following response in a structured format.
#                   You can take the response and structure it in 2 ways: 1. Text 2. Artifacts

#                   For responses containing code:
#     1. Start with a text element explaining what you will do
#     2. Create an artifact for the code with:
#        - A descriptive title
#        - Proper language tag
#        - Clear comments explaining the code
#        - The complete code implementation
#     3. End with a text element explaining the code and next steps

#     For responses containing markdown documents:
#     1. Start with a text element introducing the document
#     2. Create an artifact with:
#        - artifact_type: "markdown"
#        - language: null
#        - A descriptive title
#        - The complete markdown content
#     3. End with a text element summarizing key points

#     CRITICAL RULES:
#     - NEVER include code blocks (```) in text responses
#     - Text responses are for explanations only
#     - Each distinct code file/component must be its own artifact
#     - Code MUST be in artifacts, not in text
#     - Every response must start with a text element
#     - Artifacts must be used for code longer than 1 line
#     - NEVER include quotation marks in any response
#     - Use text/markdown artifact type for documents and memos

#     Response: {{ parent_output }}
#         """,
#     prompt_driver=OpenAiChatPromptDriver(
#         model="gpt-4o-mini",
#         stream=True,
#         temperature=0.1,
#         seed=42,
#         response_format={
#             "type": "json_schema",
#             "json_schema": {"strict": True, "name": "Output", "schema": output_schema},
#         },
#     ),
# )
