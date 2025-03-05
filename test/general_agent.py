import os
import sys
from rich import print as rprint
from rich import print_json
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from extension.drivers.serper_web_search_driver.serper_web_search_driver import (
    SerperWebSearchDriver,
)
from extension.drivers.jina_web_scraper_driver.jina_web_scraper_driver import (
    JinaWebScraperDriver,
)
from griptape.structures import Agent
from griptape.configs.logging import JsonFormatter
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

# Defaults.drivers_config = GoogleDriversConfig(
#     prompt_driver=GooglePromptDriver(
#         model="gemini-1.5-pro", api_key=os.getenv("GOOGLE_API_KEY")
#     )
# )

logger = logging.getLogger(Defaults.logging_config.logger_name)
logger.setLevel(logging.INFO)
logger.handlers[0].setFormatter(JsonFormatter())

Defaults.drivers_config = AnthropicDriversConfig(
    prompt_driver=AnthropicPromptDriver(model="claude-3-5-sonnet-20240620")
)

Defaults.drivers_config = OpenAiDriversConfig(
    prompt_driver=OpenAiChatPromptDriver(model="chatgpt-4o-latest")
)

# agent = ArtifactAgent(tools=[DateTimeTool()], stream=True)

web_search_tool = WebSearchTool(
    web_search_driver=SerperWebSearchDriver(api_key=os.getenv("SERPER_API_KEY"))
)
web_scraper_tool = WebScraperTool(
    web_loader=WebLoader(
        web_scraper_driver=JinaWebScraperDriver(api_key=os.getenv("JINA_API_KEY"))
    ),
    off_prompt=False,
)

# agent = Agent(prompt_driver=OpenAiChatPromptDriver(model="o3-mini"))

agent = Agent(
    prompt_driver=OpenAiChatPromptDriver(
        api_key=os.getenv("TOGETHER_API_KEY"),
        base_url=os.getenv("TOGETHER_BASE_URL"),
        model="deepseek-ai/DeepSeek-R1",
    )
)

Chat(structure=agent, logger_level=logging.INFO, processing_text="thinking...").start()
