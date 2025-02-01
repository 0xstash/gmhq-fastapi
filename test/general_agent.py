import os
import sys
from rich import print as rprint
from rich import print_json
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from griptape.structures import Agent
from griptape.configs import Defaults
from griptape.configs.drivers import (
    OpenAiDriversConfig,
    GoogleDriversConfig,
    AnthropicDriversConfig,
)
from griptape.drivers import (
    OpenAiChatPromptDriver,
    AnthropicPromptDriver,
    GooglePromptDriver,
)
from griptape.tools import DateTimeTool, WebSearchTool, WebScraperTool
from dotenv import load_dotenv
from artifact.artifact_agent import ArtifactAgent
from griptape.utils import Chat
from griptape.rules import Rule, Ruleset
from griptape.loaders import WebLoader


load_dotenv()

# Configure the OpenAI driver
# Defaults.drivers_config = OpenAiDriversConfig(
#     prompt_driver=OpenAiChatPromptDriver(model="gpt-4o-mini")
# )

Defaults.drivers_config = GoogleDriversConfig(
    prompt_driver=GooglePromptDriver(
        model="gemini-1.5-flash", api_key=os.getenv("GOOGLE_API_KEY")
    )
)

# agent = ArtifactAgent(tools=[DateTimeTool()], stream=True)
agent = Agent()

Chat(structure=agent, logger_level=logging.INFO, processing_text="thinking...").start()
