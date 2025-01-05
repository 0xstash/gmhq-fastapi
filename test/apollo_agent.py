import os
import sys
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from griptape.structures import Agent
from griptape.tools import PromptSummaryTool
from griptape.drivers import OpenAiChatPromptDriver
from griptape.configs import Defaults
from griptape.configs.drivers import OpenAiDriversConfig
from extension.tools.apollo.apollo_tool import ApolloClient
from extension.drivers.serper_web_search_driver.serper_web_search_driver import (
    SerperWebSearchDriver,
)
from griptape.tools import WebScraperTool, WebSearchTool, DateTimeTool
from dotenv import load_dotenv
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


load_dotenv()
Defaults.drivers_config = OpenAiDriversConfig(
    prompt_driver=OpenAiChatPromptDriver(model="gpt-4o-mini")
)

apollo_tool = ApolloClient(api_key=os.getenv("APOLLO_API_KEY"))
web_search_tool = WebSearchTool(
    web_search_driver=SerperWebSearchDriver(api_key=os.getenv("SERPER_API_KEY"))
)


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
agent = Agent(tools=[apollo_tool, web_search_tool, DateTimeTool()])
agent.run(
    """
find me account executives who work at Salesforce in New york    """
)
