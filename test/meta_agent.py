import os
import sys
import json
import schema
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from griptape.configs import Defaults
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
