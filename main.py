from typing import Optional
from pydantic import BaseModel
import uuid
from dotenv import load_dotenv
import os

from griptape.structures import Agent, Pipeline, Workflow
from griptape.tools import WebScraperTool, WebSearchTool, DateTimeTool
from griptape.configs import Defaults
from griptape.configs.drivers import (
    OpenAiDriversConfig,
    AnthropicDriversConfig,
    GoogleDriversConfig,
)
from griptape.drivers import OpenAiChatPromptDriver, AnthropicPromptDriver
from griptape.drivers import GriptapeCloudConversationMemoryDriver
from griptape.structures.structure import ConversationMemory
from griptape.utils import Chat

from fastapi import FastAPI

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

app = FastAPI()


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    conversation_id: str


Defaults.drivers_config = OpenAiDriversConfig(
    OpenAiChatPromptDriver(model="gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))
)

# Initialize Griptape Cloud conversation memory
cloud_memory = GriptapeCloudConversationMemoryDriver(
    api_key=os.getenv("GRIPTAPE_CLOUD_API_KEY"), alias=str(uuid.uuid4())
)

agent = Agent(
    conversation_memory=ConversationMemory(conversation_memory_driver=cloud_memory),
    stream=True,
    tools=[DateTimeTool()],
)


@app.post("/chat")
async def chat(request: ChatRequest) -> ChatResponse:
    conversation_id = request.conversation_id or str(uuid.uuid4())
    response = agent.run(request.message)
    chat_response = response.output_task.output.value

    return ChatResponse(response=str(chat_response), conversation_id=conversation_id)


@app.get("/")
async def root():
    return {"message": "Welcome to the GMHQ Jungle"}


# Utility functions


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Optional[str] = None):
    return {"item_id": item_id, "q": q}
