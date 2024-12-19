import os
import sys
import json
import schema
import questionary
from rich import print as rprint
from rich import print_json
import uuid
from rich.panel import Panel
from rich.markdown import Markdown
from rich.console import Group
from rich.columns import Columns

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from griptape.configs import Defaults
from griptape.configs.drivers import (
    OpenAiDriversConfig,
    CohereDriversConfig,
    AnthropicDriversConfig,
    GoogleDriversConfig,
)
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
    TextChunkEvent,
    BaseChunkEvent,
    ActionChunkEvent,
)
from griptape.drivers import (
    OpenAiChatPromptDriver,
    AnthropicImageQueryDriver,
    AnthropicPromptDriver,
    GooglePromptDriver,
    CoherePromptDriver,
)
from drivers.serper_web_search_driver import SerperWebSearchDriver
from drivers.jina_web_scraper_driver import JinaWebScraperDriver
from griptape.loaders import WebLoader
from griptape.structures import Agent, Pipeline, Workflow
from griptape.configs.defaults_config import LoggingConfig
from griptape.configs.logging import JsonFormatter
from griptape.tools import WebScraperTool, WebSearchTool, PromptSummaryTool
from griptape.rules import Rule, Ruleset
from griptape.tools import DateTimeTool, WebSearchTool
from griptape.utils import Chat, Stream
from griptape.tasks import PromptTask, ToolkitTask

from prompts.system_prompts import ARTIFACT_PROMPT, CHAT_PROMPT

import os
import sys
from dotenv import load_dotenv
import logging

load_dotenv()

Defaults.drivers_config = OpenAiDriversConfig(
    prompt_driver=OpenAiChatPromptDriver(model="gpt-4o-mini-2024-07-18", stream=True),
)

# Defaults.drivers_config = AnthropicDriversConfig(
#     prompt_driver=AnthropicPromptDriver(model="claude-3-5-sonnet-20240620", stream=True)
# )

# Defaults.drivers_config = GoogleDriversConfig(
#     prompt_driver=GooglePromptDriver(model="gemini-pro", stream=True)
# )

# Defaults.drivers_config = CohereDriversConfig(
#     prompt_driver=CoherePromptDriver(model="command-r", stream=True)
# )

logger = logging.getLogger(Defaults.logging_config.logger_name)
logger.setLevel(logging.INFO)
logger.handlers[0].setFormatter(JsonFormatter())

web_search_tool = WebSearchTool(
    web_search_driver=SerperWebSearchDriver(api_key=os.getenv("SERPER_API_KEY"))
)

web_scraper_tool = WebScraperTool(
    web_loader=WebLoader(
        web_scraper_driver=JinaWebScraperDriver(api_key=os.getenv("JINA_API_KEY"))
    ),
    off_prompt=False,
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


def select_tools():
    available_tools = {
        "Web Search": web_search_tool,
        "Web Scraper": web_scraper_tool,
        "Prompt Summary": PromptSummaryTool(),
    }

    selected = questionary.checkbox(
        "Select the tools you want to use:", choices=list(available_tools.keys())
    ).ask()

    return [available_tools[tool] for tool in selected]


selected_tools = select_tools()

chat_task = ToolkitTask(
    "{{ args[0] }}",
    generate_system_template=lambda task: f"{CHAT_PROMPT}",
    tools=selected_tools,
    id="CHAT_TASK",
)

artifact_task = PromptTask(
    """Generate an artifact based on the following output received, if you find it appropriate. Otherwise, just reply with "No artifact".
    
    Output: {{parent_outputs['CHAT_TASK']}}""",
    generate_system_template=lambda task: f"{ARTIFACT_PROMPT}",
    id="ARTIFACT_TASK",
)

tasks = []
chat_task.add_child(artifact_task)
tasks.append(chat_task)
tasks.append(artifact_task)

workflow = Workflow(tasks=[*tasks])

output = workflow.run(
    "please create a summary report of the latest financials of accenture"
)


first_output = Panel(
    str({workflow.tasks[0].output.value}),
    title="Chat Output",
    border_style="blue",
)

second_output = Panel(
    str({workflow.tasks[1].output.value}), title="Artifact Output", border_style="green"
)

rprint(f"Output of the first task: {workflow.tasks[0].output.value}")
rprint(f"Output of the second task: {workflow.tasks[1].output.value}")
rprint(Columns([first_output, second_output], equal=True, expand=True))
