from typing import Optional, List
from pydantic import BaseModel, model_validator, Field
import uuid
from dotenv import load_dotenv
import os
import logging
from enum import Enum
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Union, Literal
import sys
from rich import print as rprint


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from griptape.utils import Chat
from griptape.configs import Defaults
from griptape.rules import JsonSchemaRule
from griptape.configs.logging import JsonFormatter
from griptape.artifacts import TextArtifact, ListArtifact
from griptape.structures import Agent, Pipeline
from griptape.tools import DateTimeTool, WebSearchTool
from griptape.configs import Defaults
from griptape.configs.drivers import OpenAiDriversConfig
from griptape.drivers import (
    OpenAiChatPromptDriver,
    GriptapeCloudConversationMemoryDriver,
    GoogleWebSearchDriver,
)
from griptape.structures.structure import ConversationMemory
from griptape.events import (
    BaseEvent,
    EventBus,
    EventListener,
    FinishActionsSubtaskEvent,
    StartActionsSubtaskEvent,
    BaseActionsSubtaskEvent,
    BaseTaskEvent,
    BaseChunkEvent,
    TextChunkEvent,
    ActionChunkEvent,
    StartTaskEvent,
    FinishTaskEvent,
)
from griptape.tasks import ToolkitTask, PromptTask
from griptape.rules import JsonSchemaRule
from rich import print as rprint
from fastapi import FastAPI

load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Ensure there is at least one handler
if not logger.handlers:
    # Create a default stream handler if no handlers are present
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(JsonFormatter())
    logger.addHandler(stream_handler)
else:
    # Set formatter for the existing handler
    logger.handlers[0].setFormatter(JsonFormatter())

app = FastAPI()

# Global variable to store the latest conversation_id
latest_conversation_id = None


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = Field(
        default=None,
        description="Unique identifier for the conversation. If not provided a new one will be generated.",
        example="123e4567-e89b-12d3-a456-426614174000",
    )

    @model_validator(mode="before")
    def handle_conversation_id(cls, values):
        global latest_conversation_id
        if not values.get("conversation_id"):
            if latest_conversation_id is None:
                latest_conversation_id = str(uuid.uuid4())
            values["conversation_id"] = latest_conversation_id
        return values


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


Defaults.drivers_config = OpenAiDriversConfig(
    OpenAiChatPromptDriver(model="gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))
)

web_search_tool = WebSearchTool(
    web_search_driver=GoogleWebSearchDriver(
        api_key=os.environ["GOOGLE_API_KEY"],
        search_id=os.environ["GOOGLE_API_SEARCH_ID"],
        results_count=5,
        language="en",
        country="us",
    ),
)

logger = logging.getLogger(Defaults.logging_config.logger_name)
logger.setLevel(logging.INFO)
logger.handlers[0].setFormatter(JsonFormatter())

# Set up a file handler for logging with write mode to reset the file each time
file_handler = logging.FileHandler("test/data/event_logs.log", mode="w")
file_handler.setFormatter(JsonFormatter())
logger.addHandler(file_handler)

# Initialize the agent without conversation memory


@app.post("/api/chat")
async def chat(request: ChatRequest) -> ChatResponse:
    global latest_conversation_id

    # Initialize the pipeline
    pipeline = Pipeline()

    # First task uses the agent with tools
    task_1 = ToolkitTask(
        "{{args[0]}}",
        tools=[DateTimeTool(), web_search_tool],
        id="CHAT_TASK",
        prompt_driver=OpenAiChatPromptDriver(model="gpt-4o-mini", stream=True),
    )

    # Second task formats the response according to the schema
    task_2 = PromptTask(
        input="""
        Format the following response in a structured format.
        You can take the response and structure it in 2 ways: 1. Text 2. Artifacts

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
        - Use text/markdown artifact type for documents and memos

        Response:
        {{parent_output}}
        """,
        rules=[JsonSchemaRule(ChatResponse.model_json_schema())],
    )

    pipeline.add_tasks(task_1, task_2)

    # Use existing conversation_id or create a new one
    conversation_id = request.conversation_id or str(uuid.uuid4())
    latest_conversation_id = conversation_id

    # Create or retrieve the conversation memory driver
    cloud_memory = GriptapeCloudConversationMemoryDriver(
        api_key=os.getenv("GRIPTAPE_CLOUD_API_KEY"), alias=latest_conversation_id
    )

    pipeline.conversation_memory = ConversationMemory(
        conversation_memory_driver=cloud_memory
    )

    # Run the pipeline with the user's message
    response = pipeline.run(request.message)

    # Extract the formatted response
    formatted_response = response.output_task.output.value

    try:
        # If the response is a string that contains JSON
        if isinstance(formatted_response, str):
            try:
                # Try to parse it as JSON first
                import json

                parsed_response = json.loads(formatted_response)
                return ChatResponse.model_validate(parsed_response)
            except json.JSONDecodeError:
                # If it's not JSON, treat it as plain text
                return ChatResponse(
                    stream_elements=[
                        TextResponse(
                            type="text", content=formatted_response, sequence_number=1
                        )
                    ],
                    has_artifacts=False,
                )
        else:
            # If it's already a dict/object
            return ChatResponse.model_validate(formatted_response)

    except Exception as e:
        logger.error(f"Error processing response: {e}")
        # Fallback to simple text response
        return ChatResponse(
            stream_elements=[
                TextResponse(
                    type="text", content=str(formatted_response), sequence_number=1
                )
            ],
            has_artifacts=False,
        )

    finally:
        logger.info(f"Response processed, conversation_id: {latest_conversation_id}")


@app.get("/")
async def root():
    return {"message": "Welcome to the GMHQ Jungle"}
