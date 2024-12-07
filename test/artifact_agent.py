import os
import sys

# Add the project root directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import os
import logging
import uuid
import schema
import json

from griptape.utils import Chat
from griptape.rules import Rule, Ruleset
from griptape.configs.logging import JsonFormatter
from griptape.structures import Agent
from griptape.tools import DateTimeTool, OpenWeatherTool
from tools.artifact_tool.tool import ArtifactGenerationTool
from griptape.configs import Defaults
from griptape.configs.drivers import OpenAiDriversConfig
from griptape.drivers import OpenAiChatPromptDriver
from griptape.drivers import GriptapeCloudConversationMemoryDriver
from griptape.structures.structure import ConversationMemory
from griptape.rules.json_schema_rule import JsonSchemaRule
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

from pydantic import BaseModel
from rich import print as rprint, print_json
from dotenv import load_dotenv

load_dotenv()

Defaults.drivers_config = OpenAiDriversConfig(
    OpenAiChatPromptDriver(model="gpt-4o-mini")
)


class Response(BaseModel):
    start_response: str
    artifact: str
    end_response: str


response_ruleset = Ruleset(
    name="Response ruleset", rules=[Rule("""Use the start_response""")]
)

agent = Agent(
    rules=[
        Rule(
            """
            Use artifacts to display the output of the user's request.
            """
        ),
        JsonSchemaRule(Response.model_json_schema()),
    ]
)

agent.run("What is the sentiment of this message?: 'I am so happy!'")
