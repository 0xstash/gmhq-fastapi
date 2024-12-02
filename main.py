from typing import Optional, List
from pydantic import BaseModel, model_validator, Field
import uuid
from dotenv import load_dotenv
import os
import logging

from griptape.utils import Chat
from griptape.configs.logging import JsonFormatter
from griptape.artifacts import TextArtifact, ListArtifact
from griptape.structures import Agent
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


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    actions: List[dict] = Field(default_factory=list)


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

    event_logs = []

    agent = Agent(
        stream=True,
        tools=[DateTimeTool(), web_search_tool],
    )

    def on_event(event: BaseEvent) -> None:
        if isinstance(event, BaseActionsSubtaskEvent):
            rprint(f"BaseActionsSubtaskEvent name: {event.__class__.__name__}")
            event_log = {
                "event_name": event.__class__.__name__,
                "event_details": {
                    "substask_actions": [
                        {
                            "tag": action.get("tag"),
                            "name": action.get("name"),
                            "path": action.get("path"),
                            "input": action.get("input", {}).get("values", {}),
                        }
                        for action in event.subtask_actions
                    ],
                    "subtask_thought": event.subtask_thought,
                    "task_output": str(event.task_output),
                },
            }

            event_logs.append(event_log)

            task_name = event.__class__.__name__
            actions = getattr(event, "actions", None)
            response = getattr(event, "response", None)

            # Log the subtask ID, actions dictionary, and response
            logger.info(f"Event or task name: {task_name}")
            logger.info(f"Actions: {actions}")
            logger.info(f"Response: {response}")
            logger.info("-" * 40)  # Divider line
            # Add the subtask ID to the set

    EventBus.add_event_listeners(
        [
            EventListener(
                on_event,
                event_types=[
                    BaseEvent,
                    BaseActionsSubtaskEvent,
                    StartTaskEvent,
                    FinishTaskEvent,
                    TextChunkEvent,
                    ActionChunkEvent,
                ],
            )
        ]
    )

    # Log the incoming conversation_id
    logger.info(f"Received conversation_id: {request.conversation_id}")

    # Use existing conversation_id or create a new one
    conversation_id = request.conversation_id or str(uuid.uuid4())

    # Update the global latest_conversation_id
    latest_conversation_id = conversation_id

    # Create or retrieve the conversation memory driver
    cloud_memory = GriptapeCloudConversationMemoryDriver(
        api_key=os.getenv("GRIPTAPE_CLOUD_API_KEY"), alias=latest_conversation_id
    )

    # Assign the conversation memory to the agent
    agent.conversation_memory = ConversationMemory(
        conversation_memory_driver=cloud_memory
    )

    response = agent.run(request.message)
    chat_response = response.output_task.output.value

    # Log the response and conversation_id
    logger.info(f"Response: {chat_response}, conversation_id: {latest_conversation_id}")

    return ChatResponse(
        response=str(chat_response),
        conversation_id=latest_conversation_id,
        actions=event_logs,
    )


@app.get("/")
async def root():
    return {"message": "Welcome to the GMHQ Jungle"}
