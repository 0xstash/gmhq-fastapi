import os
import sys
import json
import schema
import logging
import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from griptape.configs import Defaults
from griptape.events import (
    BaseEvent,
    EventBus,
    EventListener,
    FinishActionsSubtaskEvent,
    FinishPromptEvent,
    FinishTaskEvent,
    StartActionsSubtaskEvent,
    StartPromptEvent,
    StartTaskEvent,
)

from griptape.configs.drivers import (
    OpenAiDriversConfig,
    AnthropicDriversConfig,
    GoogleDriversConfig,
)
from griptape.drivers import (
    OpenAiChatPromptDriver,
    AnthropicPromptDriver,
    LocalStructureRunDriver,
)
from griptape.configs.drivers import OpenAiDriversConfig, AnthropicDriversConfig
from griptape.structures import Agent, Pipeline, Workflow
from griptape.tools import (
    WebScraperTool,
    WebSearchTool,
    PromptSummaryTool,
    StructureRunTool,
)
from extension.drivers.serper_web_search_driver.serper_web_search_driver import (
    SerperWebSearchDriver,
)
from extension.drivers.jina_web_scraper_driver.jina_web_scraper_driver import (
    JinaWebScraperDriver,
)
from griptape.rules import Rule, Ruleset
from griptape.tasks import PromptTask, ToolkitTask
from griptape.utils import Chat
from extension.tools.automation.automation_tool import create_workflow

from dotenv import load_dotenv

load_dotenv()
Defaults.drivers_config = OpenAiDriversConfig(
    prompt_driver=OpenAiChatPromptDriver(model="gpt-4o-mini", stream=True)
)

logger = logging.getLogger(Defaults.logging_config.logger_name)
logger.setLevel(logging.ERROR)


def on_event(event: BaseEvent) -> None:
    if isinstance(event, (StartActionsSubtaskEvent, FinishActionsSubtaskEvent)):
        # Create the log entry
        log_entry = f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]\n"
        log_entry += f"Event Class: {event.__class__.__name__}\n"
        log_entry += f"Task ID: {event.task_id}\n"
        log_entry += f"Timestamp: {event.timestamp}\n"

        log_entry += "\nSubtask Actions:\n"
        for action in event.subtask_actions:
            log_entry += f"Tool Name: {action.get('name')}\n"
            log_entry += f"Tool Path: {action.get('path')}\n"
            log_entry += f"Tool Input: {action.get('input')}\n"
            log_entry += "---\n"

            log_entry += f"Tool Output: {action.get('output')}\n"

        log_entry += f"{event.task_output}\n"

        log_entry += "=" * 80 + "\n"  # Separator between entries

        # Read existing content
        log_file = "test/data/event_logs.log"
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        existing_content = ""
        if os.path.exists(log_file):
            with open(log_file, "r") as f:
                existing_content = f.read()

        # Write new content at the top
        with open(log_file, "w") as f:
            f.write(log_entry + existing_content)

        # Also print to console
        print(log_entry)


EventBus.add_event_listeners(
    [
        EventListener(
            on_event,
            event_types=[
                StartTaskEvent,
                FinishTaskEvent,
                StartActionsSubtaskEvent,
                FinishActionsSubtaskEvent,
                StartPromptEvent,
                FinishPromptEvent,
            ],
        )
    ]
)


system_prompt_template = """
You are an expert form and automation creator and business process manager who is specialised in creating AI automations as well as writing prompts. 
Your job is to assist in creating forms and automations on the basis of the output of those automations.
"""

web_search_tool = WebSearchTool(
    web_search_driver=SerperWebSearchDriver(api_key=os.getenv("SERPER_API_KEY"))
)

workflow_structure_run_tool = StructureRunTool(
    description="Form and automation tool - structure to invoke when an automation/app/form creation is requested.",
    # description="Form and Automation Creator Tool - Structure to invoke when you need to create a form and a workflow",
    structure_run_driver=LocalStructureRunDriver(create_structure=create_workflow),
)

agent = Agent()

agent.add_task(
    ToolkitTask(
        generate_system_template=lambda task: f"{system_prompt_template}",
        tools=[web_search_tool, workflow_structure_run_tool],
    )
)

Chat(
    structure=agent,
    intro_text="What automation would you like to create?",
    exiting_text="Goodbye",
    logger_level=logging.INFO,
).start()
