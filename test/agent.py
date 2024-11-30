from dotenv import load_dotenv
import os
import logging
import uuid

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
    FinishPromptEvent,
    FinishTaskEvent,
    StartActionsSubtaskEvent,
    BaseActionsSubtaskEvent,
    StartPromptEvent,
    StartTaskEvent,
)

from rich import print as rprint, print_json

load_dotenv()

Defaults.drivers_config = OpenAiDriversConfig(
    OpenAiChatPromptDriver(model="gpt-4o-mini")
)

logger = logging.getLogger(Defaults.logging_config.logger_name)
logger.setLevel(logging.INFO)
logger.handlers[0].setFormatter(JsonFormatter())

# Set up a file handler for logging with write mode to reset the file each time
file_handler = logging.FileHandler("test/data/event_logs.log", mode="w")
file_handler.setFormatter(JsonFormatter())
logger.addHandler(file_handler)

# Initialize a set to keep track of logged subtask IDs
logged_subtask_ids = set()


def on_event(event: BaseEvent) -> None:
    if isinstance(
        event,
        [
            StartActionsSubtaskEvent,
            FinishActionsSubtaskEvent,
            BaseActionsSubtaskEvent,
        ],
    ):
        # Always generate a new unique subtask ID
        subtask_id = str(uuid.uuid4())
        actions = getattr(event, "actions", None)
        response = getattr(event, "response", None)

        # Log the subtask ID, actions dictionary, and response
        logger.info(f"Subtask ID: {subtask_id}")
        logger.info(f"Actions: {actions}")
        logger.info(f"Response: {response}")
        logger.info("-" * 40)  # Divider line
        # Add the subtask ID to the set
        logged_subtask_ids.add(subtask_id)

        # Print actions at the end of the task if they are not None
        if isinstance(event, FinishActionsSubtaskEvent) and actions is not None:
            rprint(f"Actions handled: {actions}")
    else:
        logger.info(f"Event: {event.__class__.__name__}")


EventBus.add_event_listeners(
    [
        EventListener(
            on_event,
            event_types=[
                FinishActionsSubtaskEvent,
                # FinishPromptEvent,
                # FinishTaskEvent,
                StartActionsSubtaskEvent,
                # StartPromptEvent,
                # StartTaskEvent,
            ],
        )
    ]
)
agent = Agent(tools=[DateTimeTool()])


output = agent.run("What is today's date?")
rprint(f"Output of the task: {output.output_task.output.value}")
