from typing import Optional, List
from pydantic import BaseModel, model_validator, Field
import uuid
from dotenv import load_dotenv
import os
import logging

from griptape.utils import Chat
from griptape.configs.logging import JsonFormatter
from griptape.structures import Agent
from griptape.tools import DateTimeTool
from griptape.configs import Defaults
from griptape.configs.drivers import OpenAiDriversConfig
from griptape.drivers import OpenAiChatPromptDriver
from griptape.drivers import GriptapeCloudConversationMemoryDriver
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
)

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

# Initialize the agent without conversation memory
agent = Agent(
    stream=True,
    tools=[DateTimeTool()],
)


@app.post("/api/chat")
async def chat(request: ChatRequest) -> ChatResponse:
    global latest_conversation_id

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

    EventBus.add_event_listeners(
        [
            EventListener(
                lambda e: print(str(e), end="", flush=True),
                event_types=[TextChunkEvent],
            ),
            EventListener(
                lambda e: print(str(e), end="", flush=True),
                event_types=[ActionChunkEvent],
            ),
        ]
    )

    response = agent.run(request.message)
    chat_response = response.output_task.output.value

    # Log the response and conversation_id
    logger.info(f"Response: {chat_response}, conversation_id: {latest_conversation_id}")

    return ChatResponse(
        response=str(chat_response),
        conversation_id=latest_conversation_id,
    )


@app.get("/")
async def root():
    return {"message": "Welcome to the GMHQ Jungle"}
