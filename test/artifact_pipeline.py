import os
import sys
import json
import schema

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from griptape.configs import Defaults
from griptape.configs.drivers import (
    OpenAiDriversConfig,
    CohereDriversConfig,
    AnthropicDriversConfig,
    GoogleDriversConfig,
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
from griptape.tools import WebScraperTool, WebSearchTool
from griptape.rules import Rule, Ruleset
from griptape.tools import DateTimeTool, WebSearchTool
from griptape.utils import Chat
from griptape.tasks import PromptTask, ToolkitTask

import os
import sys
from dotenv import load_dotenv

load_dotenv()

Defaults.drivers_config = OpenAiDriversConfig(
    OpenAiChatPromptDriver(model="gpt-4o-mini", stream=True),
)

# Defaults.drivers_config = AnthropicDriversConfig(
#     AnthropicPromptDriver(model="claude-3-5-sonnet-20240620", stream=True)
# )

# Defaults.drivers_config = GoogleDriversConfig(
#     GooglePromptDriver(model="gemini-pro", stream=True)
# )

# Defaults.drivers_config = CohereDriversConfig(
#     CoherePromptDriver(model="command-r", stream=True)
# )


chat_prompt_template = """
You are an AI agent platform called GodmodeHQ, an AI agent specialized in business use cases that can generate interactive visual artifacts to enhance responses. 
Artifacts are mini-applications for visualizing and interacting with information when plain text isn't sufficient.

"""

artifact_prompt_template = 


chat_task = ToolkitTask(
    generate_system_template=lambda task: f"""
   {chat_prompt_template}"""
)

artifact_task = PromptTask()
