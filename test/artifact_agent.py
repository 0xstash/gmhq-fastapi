import os
import sys

# Add the project root directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import os
import logging
import uuid

from griptape.utils import Chat
from griptape.configs.logging import JsonFormatter
from griptape.structures import Agent
from griptape.tools import DateTimeTool, OpenWeatherTool
from tools.artifact_tool.tool import ArtifactGenerationTool
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
    FinishPromptEvent,
    FinishTaskEvent,
    StartActionsSubtaskEvent,
    BaseActionsSubtaskEvent,
    StartPromptEvent,
    StartTaskEvent,
)

from rich import print as rprint, print_json
from dotenv import load_dotenv

load_dotenv()

Defaults.drivers_config = OpenAiDriversConfig(
    OpenAiChatPromptDriver(model="gpt-4o-mini")
)

agent = Agent(tools=[ArtifactGenerationTool(), DateTimeTool()])
agent.run("Write a short story with a dramatic twist regarding today")
