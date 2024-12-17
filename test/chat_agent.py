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
from griptape.drivers import (
    OpenAiChatPromptDriver,
    AnthropicPromptDriver,
    CoherePromptDriver,
    GooglePromptDriver,
)
from griptape.configs import Defaults
from griptape.rules import Rule, Ruleset, JsonSchemaRule
from griptape.tools import (
    DateTimeTool,
    WebScraperTool,
    WebSearchTool,
    PromptSummaryTool,
)
from drivers.serper_web_search_driver import SerperWebSearchDriver
from drivers.jina_web_scraper_driver import JinaWebScraperDriver
from griptape.loaders import WebLoader
from griptape.configs.drivers import (
    OpenAiDriversConfig,
    AnthropicDriversConfig,
    GoogleDriversConfig,
    CohereDriversConfig,
)
from dotenv import load_dotenv
from griptape.tasks import ToolkitTask, PromptTask
from griptape.utils import Chat

from pydantic import BaseModel
from schemas.output_schema import output_schema

load_dotenv()


# Defaults.drivers_config = OpenAiDriversConfig(
#     OpenAiChatPromptDriver(
#         model="gpt-4o", api_key=os.getenv("OPENAI_API_KEY"), stream=True
#     )
# )

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


structure_rules = Rule(
    """
    IMPORTANT:
    You generate responses in a structured JSON format:
{
    "stream_elements": [
        {"type": "text", "content": "explanation", "sequence_number": n},
        {"type": "artifact", ...artifact fields..., "sequence_number": n+1},
        {"type": "text", "content": "follow-up", "sequence_number": n+2}
    ],
    "has_artifacts": true/false
}

When including code/diagrams/documents, ALWAYS use artifacts. NEVER include them in text."""
)

# Artifact generation rules
artifact_rules = Rule(
    """Artifacts require:
- Unique ID
- Descriptive title
- Appropriate type (code/markdown/svg/mermaid/html/react)
- Language tag for code
- Complete implementation"""
)

web_search_tool = WebSearchTool(
    web_search_driver=SerperWebSearchDriver(api_key=os.getenv("SERPER_API_KEY"))
)

web_scraper_tool = WebScraperTool(
    web_loader=WebLoader(
        web_scraper_driver=JinaWebScraperDriver(api_key=os.getenv("JINA_API_KEY"))
    ),
    off_prompt=False,
)

agent = Agent(
    tools=[DateTimeTool(), web_search_tool, web_scraper_tool],
    rules=[
        structure_rules,
        artifact_rules,
        JsonSchemaRule(ChatResponse.model_json_schema()),
    ],
    stream=True,
)

output = agent.run("Help me solve this equation: 3x+7=16")

Chat(agent).start()


#   Rule(
#             value="""
# Format your responses in a structured format.
# You can take the response and structure it in 2 ways: 1. Text 2. Artifacts

#                    For responses containing code:
#      1. Start with a text element explaining what you will do
#      2. Create an artifact for the code with:
#         - A descriptive title
#         - Proper language tag
#         - Clear comments explaining the code
#         - The complete code implementation
#      3. End with a text element explaining the code and next steps

#      For responses containing markdown documents:
#      1. Start with a text element introducing the document
#      2. Create an artifact with:
#         - artifact_type: "markdown"
#         - language: null
#         - A descriptive title
#         - The complete markdown content
#      3. End with a text element summarizing key points

#      CRITICAL RULES:
#      - NEVER include code blocks (```) in text responses
#      - Text responses are for explanations only
#      - Each distinct code file/component must be its own artifact
#      - Code MUST be in artifacts, not in text
#      - Every response must start with a text element
#      - Artifacts must be used for code longer than 1 line
#      - NEVER include quotation marks in any response
#      - Use text/markdown artifact type for documents and memos

# """
#         ),
# is there a clever word we can play on around "work 10 times faster and 10 times better with 10 more AI coworkers by building your team" This is lame but you might get the idea, ask me questions if you don't
